"""DELTARUNE Chapter 6: obj_plat_follower (GML-to-Python port).

Source: supplied Create/Step attachments and Destroy, Alarm 1, End Step,
Animation End (Other 7), User Event 0 (Other 10), Draw and Pre Draw events.

A GameMaker object is NOT a standalone sprite: it requires obj_plat_entity's
inherited Create/Step behavior, an instance registry, a collision system,
asset handles, and scheduled events. This class preserves the supplied logic
and calls explicit engine adapters for those operations. Register with the
object manager; do not instantiate without an engine in production.

The GML's numeric `state` belongs to the follower; `engine` is the Python
adapter. Numeric GML sentinel -4 and resource IDs are intentionally retained.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

MISSING = object()
NOONE = -4


def approach(value, goal, amount):
    return min(value + amount, goal) if value < goal else max(value - amount, goal)


def clamp(value, lower, upper):
    return min(max(value, lower), upper)


def lerp(a, b, t):
    return a + (b - a) * t


def sign(x):
    return (x > 0) - (x < 0)


def distance(x1, y1, x2, y2):
    return math.hypot(x2-x1, y2-y1)


def direction(x1, y1, x2, y2):
    return (math.degrees(math.atan2(y1-y2, x2-x1)) % 360)


def lengthdir(r, direction_degrees):
    angle = math.radians(direction_degrees)
    return (r * math.cos(angle), -r * math.sin(angle))


@dataclass(frozen=True)
class PlatformFollowerPhysics:
    density: float = 0.5
    restitution: float = 0.1
    group: int = 1
    linear_damping: float = 0.1
    angular_damping: float = 0.1
    friction: float = 0.2
    is_awake: bool = True
    is_kinematic: bool = False


class PlatFollower:
    object_name = "obj_plat_follower"
    parent_object = "obj_plat_entity"
    parent_object_name = parent_object
    sprite_index_default = None
    mask_index_default = "spr_kris_plat_idle"
    visible_default = True
    solid_default = False
    persistent_default = False
    uses_physics = False
    collision_shape = "box"
    physics_metadata = PlatformFollowerPhysics()

    # The original preset uses resource indices, not portable sprite names.
    SUSIE_SPRITES = dict(spr_idle=8058, spr_run=1191, spr_halt=8258,
                         spr_turn=1609, spr_jump=7026, spr_fall=6017,
                         spr_land=1186, spr_climb=3157)
    RALSEI_SPRITES = dict(spr_idle=4382, spr_run=3905, spr_halt=4792,
                          spr_turn=8370, spr_jump=7448, spr_fall=6473,
                          spr_land=6359, spr_climb=5773)

    def __init__(self, engine, x=0, y=0, *, parent_create=None,
                 parent_step=None, parent_end_step=None):
        self.engine = engine
        self.x = x
        self.y = y
        self.xprevious = x
        self.yprevious = y
        self.destroyed = False
        self._parent_create = parent_create
        self._parent_step = parent_step
        self._parent_end_step = parent_end_step
        self._delayed_events = []
        # Expected GameMaker built-ins/inherited fields. Real parent Create
        # should override these, especially collisions and gravity.
        self.image_xscale = 2
        self.image_yscale = 2
        self.image_alpha = 1
        self.image_blend = 0xFFFFFF
        self.image_angle = 0
        self.image_index = 0
        self.image_speed = 0.25
        self.speed = 0
        self.direction = 0
        self.hspeed = 0
        self.vspeed = 0
        self.gravity = 0
        self.gravity_direction = 270
        self.sprite_width = 32
        self.sprite_height = 32
        self.bbox_bottom_r = 0
        self.grounded = True
        self.groundedprev = True
        self.grounded_lastX = x
        self.ground = NOONE
        self.wallhitspd = 0
        self.wallcollision = True
        self.physics = True
        self.paused = False
        self.custom_paused = False
        self.paused_grav = 0
        self.hitstop = False
        self.state = 0
        self.t = 0
        self.depth = 2050
        self.visible = True
        self.important = False
        self.highlighted = False
        self.id = self
        self.create()

    @property
    def globals(self):
        return getattr(self.engine, "global_state", self.engine)

    @property
    def bbox_left(self):
        return getattr(self, "_bbox_left", self.x - self.sprite_width/2)

    @bbox_left.setter
    def bbox_left(self, value):
        self._bbox_left = value

    @property
    def bbox_right(self):
        return getattr(self, "_bbox_right", self.x + self.sprite_width/2)

    @bbox_right.setter
    def bbox_right(self, value):
        self._bbox_right = value

    @property
    def bbox_top(self):
        return getattr(self, "_bbox_top", self.y - self.sprite_height)

    @bbox_top.setter
    def bbox_top(self, value):
        self._bbox_top = value

    @property
    def bbox_bottom(self):
        return getattr(self, "_bbox_bottom", self.y)

    @bbox_bottom.setter
    def bbox_bottom(self, value):
        self._bbox_bottom = value

    def _call(self, name, *args, default=MISSING):
        method = getattr(self.engine, name, None)
        if callable(method):
            return method(*args)
        if default is not MISSING:
            return default
        raise NotImplementedError(f"obj_plat_follower needs engine.{name}(...)")

    def _set_platform_difference(self, platform):
        """Use the platform's own GML context when the helper is bound."""
        bound = getattr(platform, "scr_plat_set_difference", None)
        if callable(bound):
            return bound()
        engine_call = getattr(self.engine, "scr_plat_set_difference", None)
        if callable(engine_call):
            return engine_call(platform)
        from scr_plat_set_difference import scr_plat_set_difference
        return scr_plat_set_difference(platform)

    def _snap_to_ground(self):
        """Call the per-follower snap function if bound, else the engine API."""
        bound = getattr(self, "scr_plat_snap_to_ground", None)
        if callable(bound):
            return bound()
        return self._call("scr_plat_snap_to_ground", self)

    def _sprite(self, name):
        return getattr(self.engine, name, name)

    def _resource(self, object_type):
        return getattr(self.engine, object_type, object_type)

    def _exists(self, obj):
        if obj in (None, NOONE) or obj == 0:
            return False
        for name in ("i_ex", "instance_exists"):
            method = getattr(self.engine, name, None)
            if callable(method):
                return bool(method(obj))
        return not isinstance(obj, (str, int, float)) and not getattr(obj, "destroyed", False)

    def _resolve(self, obj):
        if not isinstance(obj, (str, int, float)):
            return obj
        if not self._exists(obj):
            return None
        method = getattr(self.engine, "resolve_instance", None)
        if callable(method):
            return method(obj)
        # some engines expose singleton objects under object resource keys
        method = getattr(self.engine, "instance_first", None)
        if callable(method):
            return method(obj)
        raise NotImplementedError("resolve_instance required for numeric/string references")

    def _first(self, obj_type):
        value = self._resource(obj_type)
        if not isinstance(value, (str, int, float)) and hasattr(value, "x"):
            return value
        finder = getattr(self.engine, "instance_first", None)
        if callable(finder):
            return finder(value)
        for name in ("iter_instances", "instances_of", "get_instances"):
            fn = getattr(self.engine, name, None)
            if callable(fn):
                return next(iter(fn(value)), None)
        return None

    def _instances(self, obj_type):
        value = self._resource(obj_type)
        for name in ("iter_instances", "instances_of", "get_instances"):
            fn = getattr(self.engine, name, None)
            if callable(fn):
                return tuple(fn(value))
        obj = self._first(obj_type)
        return (obj,) if obj is not None else ()

    def instance_create(self, x, y, obj_type):
        """Engine forwarding for scr_plat_set_cooldown(self, ...)."""
        return self._call("instance_create", x, y, obj_type)

    def _spawn(self, x, y, object_type):
        return self._call("instance_create", x, y, self._resource(object_type))

    def _kill(self, obj):
        if not self._exists(obj):
            return
        self._call("instance_destroy", obj)

    def _destroy_self(self):
        if self.destroyed:
            return
        self.destroyed = True
        self.destroy()
        self._call("instance_destroy", self, default=None)

    def _instance_place(self, x, y, obj_type):
        return self._call("instance_place", x, y, self._resource(obj_type), default=NOONE)

    def _collision_line(self, x1, y1, x2, y2, obj_type, precise=0, notme=1):
        return self._call("collision_line", x1, y1, x2, y2,
                          self._resource(obj_type), precise, notme, default=NOONE)

    def _sound(self, name, pitch=None):
        if pitch is None:
            return self._call("snd_play", self._resource(name), default=None)
        return self._call("snd_play_pitch", self._resource(name), pitch, default=None)

    def _custom(self, name, *args, default=MISSING):
        method = getattr(self, name, None)
        if callable(method):
            return method(*args)
        return self._call(name, *args, default=default)

    def _delay(self, action, frames):
        """Schedule local callback; engine should tick via step()."""
        self._delayed_events.append([frames, action])

    def _tick_delays(self):
        active = []
        for frames, callback in self._delayed_events:
            frames -= 1
            if frames <= 0:
                callback()
            else:
                active.append([frames, callback])
        self._delayed_events = active

    def create(self):
        """GameMaker Create event: execute obj_plat_entity Create first."""
        if self._parent_create is not None:
            self._parent_create(self)
        self.t = 0
        self.depth = 2050
        self.position_history_length = 36
        self.entity_gravity = self.default_gravity = 1.25
        self.jumpheight = 20
        self.attacking = False
        self.attacktimer = 0
        self.target = NOONE
        self.climbing = False
        self.dashing = False
        self.land_anim = False
        self.turn_anim = False
        self.runstop_anim = False
        self.hurt = False
        self.hspeed_max = 9
        self.autorun = False
        self.autorun_xscale = self.image_xscale
        self.autorun_img_freq = 2
        self.scale_multiplier = 1
        self.player_stood_on_ralsei_recently = True
        self.act_busy = False
        self.dbg_targets = []
        self.air_accel, self.air_decel = 1.5, 0.85
        self.ground_accel, self.ground_decel = 2, 0.65
        self.important = False
        self.important_blend = 1
        self.jumping = 0
        self.jump_coyote_time_max = 4
        self.jump_coyote_time = 0
        self.jumpsquat = 0
        self.jumpsquat_max = 2
        self.fallen_in_pit = False
        self.respawn_leap = False
        self.respawn_leap_wait = 15
        self.respawn_leap_enabled = 0
        self.mount = NOONE
        self.remx = [self.x] * 37
        self.remy = [self.y] * 37
        self.remspd = [self.speed] * 37
        self.remdir = [self.direction] * 37
        self.remgnd = [NOONE] * 37
        self.caterpillarmode = 1
        self.caterpillardist = 2
        self.parent = NOONE
        self.default_dist = 2
        self.axethrow = 0
        self.axe = NOONE
        self.can_catch_kris = 0
        self.kris_throw_state = 0
        self.kris_throw_wait = 0
        self.kris_throw_jumptime = 20
        self.throwzone = NOONE
        self.autostop_when_reached = False
        self.key_left_override = False
        self.key_right_override = False
        self.buster_explode = True
        self.is_quick_attack = False
        self.buster_interim = 0
        self.__susie_act_cooldown = 120
        self.character = 1
        self.name = "???"
        self.forced_anim = False
        self.anim_delayer = NOONE
        self.sprite_offset_x = 0
        self.sprite_offset_y = 0
        self.custom_state = None
        self.custom_waiter = None
        self.long = False
        self.axethrow_cooldown = 45
        self.outlinecolor = 0xFF00FF
        self.get_preset(1)
        # Input clear matches scr_get_inputs(false) with no keyboard poll.
        self._clear_inputs()
        self.release_jump = False
        self.state = 0
        self.followtarget = "__nothing"
        self.followxoffset = 0
        self.followyoffset = 0
        self.is_platform_mode = False
        self.platform = self._spawn(-999, 0, "obj_plat_movingplat")
        self.platform.image_xscale = 2
        self.platform.movetype = -1
        self.platform.visible = False
        self.platform.image_yscale = 2
        self.platform_mode_target = NOONE
        self.platform_mode_offset = [0, 0]
        self.platform_mode_timer = 0
        self.reachedtarget = False
        self.custom_platform_mode = NOONE
        self.defaultdepth = self.depth
        self.highlighted = False
        self.back_marker = NOONE
        self.back_marker_scale = 1
        self.image_speed = 0.25
        self.platform_valid = False
        self.free_will = False
        self.free_will_target = NOONE
        self.free_will_target_lerp = 0
        self.free_will_target_x = 0
        self.free_will_target_y = 0
        self.offscreen_despawn_cooldown = 0
        self.__splats = False
        self.__splat_duration = 60
        self._susie_attack_cooldown_text = self._call(
            "stringsetloc", "RECHARGE", "obj_plat_follower_slash_Create_0_gml_604_0",
            default="RECHARGE")
        self.hspeedprev = 0

    def _clear_inputs(self):
        from scr_get_inputs import scr_get_inputs
        # This function handles its disabled path without needing keys.
        scr_get_inputs(self, False)

    def get_preset(self, char_id):
        self.character = char_id
        if char_id == 1:
            self.caterpillardist = self.default_dist = 6
            self.name = "susie"
            for key, sprite in self.SUSIE_SPRITES.items():
                setattr(self, key, sprite)
            if self._call("scr_use_unhappy_sprites", default=False):
                self.spr_idle, self.spr_run, self.spr_halt = 4958, 2121, 7652
            self.mask_index = self.sprite_index = self.spr_idle
            self._call("set_bbox_relative", self, default=None)
            self.can_catch_kris = 1
            self.jumpheight = 21
            self._call("scr_plat_set_group", self, 11, False, default=None)
        elif char_id == 2:
            self.caterpillardist = self.default_dist = 12
            self.axethrow = 0
            self.name = "ralsei"
            self.outlinecolor = 0x00FF00
            for key, sprite in self.RALSEI_SPRITES.items():
                setattr(self, key, sprite)
            if self._call("scr_use_unhappy_sprites", default=False):
                self.spr_idle = 6157
            self.mask_index = self.sprite_index = self.spr_idle
            flags = getattr(self.globals, "flag", ())
            if len(flags) > 1311 and flags[1311] == 1:
                for key, sprite in dict(spr_run=6967, spr_halt=5555,
                                        spr_turn=7564, spr_jump=316,
                                        spr_fall=5582, spr_land=1577,
                                        spr_climb=5175).items():
                    setattr(self, key, sprite)
            self._call("set_bbox_relative", self, default=None)
            self.can_catch_kris = 0
            self.jumpheight = 20.5
            self.entity_gravity = self.default_gravity = 1.1
            self.hspeed_max = 8
            self.depth += 50
            self._call("scr_plat_set_group", self, 10, False, default=None)

    def destroy(self):
        """Destroy event: remove back marker and Ralsei's platform."""
        for obj in (self.back_marker, self.platform):
            self._kill(obj)

    def alarm_1(self):
        """GML Alarm[1] is empty (exit)."""
        return None

    def init_caterpillarmode(self):
        leader = self._first("obj_plat_player")
        if leader is None or self.caterpillarmode:
            return
        self.offscreen_despawn_cooldown = 10
        self.caterpillarmode = 1
        self.enable_unstuck_failsafe = 0
        if not self._exists(self.parent):
            self.parent = leader
        parent = self._resolve(self.parent)
        collides = self._collision_line(self.x, self.y, parent.x, parent.y,
                                        "obj_plat_block", 0, 1)
        if self._exists(collides):
            jump_time = max(self.default_dist, 30)
            self.caterpillardist = jump_time
            for i in range(jump_time + 1):
                f = i / jump_time
                t = self._call("lerp_ease_inout", parent.x, self.x, f, 3,
                               default=lerp(parent.x, self.x, f*f*(3-2*f)))
                y = self._call("lerp_ease_inout", parent.bbox_bottom - self.bbox_bottom_r,
                               self.y, f, 3, default=lerp(parent.bbox_bottom - self.bbox_bottom_r,
                                                        self.y, f*f*(3-2*f)))
                self.remx[i] = t
                self.remy[i] = y - math.sin(i * math.pi / jump_time) * 80
                self.remspd[i] = self.remdir[i] = 0
                self.remgnd[i] = NOONE
        else:
            t = int(self.caterpillardist)
            for i in range(t + 1):
                f = i / t
                weight = 1-(1-f)**3
                self.remx[i] = self._call("lerp_ease_out", parent.x, self.x, f, 3,
                                          default=lerp(parent.x, self.x, weight))
                self.remy[i] = self._call("lerp_ease_out", parent.bbox_bottom - self.bbox_bottom_r,
                                          self.y, f, 3,
                                          default=lerp(parent.bbox_bottom - self.bbox_bottom_r,
                                                       self.y, weight))
                self.remspd[i] = self.remdir[i] = 0
                self.remgnd[i] = NOONE
        self.x = self.remx[int(self.caterpillardist)]
        self.y = self.remy[int(self.caterpillardist)]

    def reached_target(self):
        if self.followtarget == "__nothing":
            return None
        obj = None
        if self.state == 1:
            if isinstance(self.followtarget, str):
                for candidate in self._instances("obj_plat_movemarker"):
                    if candidate.extflag == self.followtarget:
                        obj = candidate
                        break
            elif self._exists(self.followtarget):
                obj = self._resolve(self.followtarget)
        self.reachedtarget = False
        if obj is None:
            return False
        self.reachedtarget = abs(self.x - (obj.x + self.followxoffset)) < 10
        if self.reachedtarget and self.autostop_when_reached:
            self.followtarget = "__nothing"
        if self.reachedtarget:
            self.followxoffset = 0
        return self.reachedtarget

    def turn(self, facing_right):
        if (facing_right and self.image_xscale > 0) or (not facing_right and self.image_xscale < 0):
            return
        if facing_right:
            self.key_right_override = True
        else:
            self.key_left_override = True
        old_state, old_mode = self.state, self.caterpillarmode
        self.state = 0
        self.caterpillarmode = 0
        self._delay(lambda: setattr(self, "key_left_override", False), 2)
        self._delay(lambda: setattr(self, "key_right_override", False), 2)
        self._delay(lambda: setattr(self, "state", old_state), 2)
        self._delay(lambda: setattr(self, "caterpillarmode", old_mode), 2)

    def force_jump(self):
        self.press_jump = True

    def force_axe_throw(self):
        self.axethrow_cooldown = 0

    def force_attack_target(self, target, explode=True, quick=False, interim=0, cooldown=120):
        """Create-event method called by scr_plat_susie_attack(_fast)."""
        self.restore_default_behavior()
        self.restore_animation()
        self.target = target
        self.state = 1
        self.caterpillarmode = 0
        self.buster_explode = explode
        self.is_quick_attack = quick
        self.buster_interim = interim
        self.attacking = 1
        self.attacktimer = 0
        self.__susie_act_cooldown = cooldown
        self.offscreen_despawn_cooldown = 100

    def force_heal_target(self, target, arg1=False, quick=False):
        """Create-event method called by scr_plat_ralsei_heal(_fast)."""
        was_platform = self.is_platform_mode
        self.drop_off_platform_mode(True)
        self.restore_default_behavior()
        self.restore_animation()
        self.target = target
        self.attacktimer = 0
        self.is_quick_attack = quick
        if was_platform:
            self.attacking = 0.5
        else:
            self.state = 1
            self.restore_animation()
            self.caterpillarmode = 0
            self.attacking = 1
        # Original GML does not otherwise use arg1 here.

    def force_animation(self, sprite, duration, zero_offsets=False):
        if self._exists(self.anim_delayer):
            self._kill(self.anim_delayer)
        self.forced_anim = True
        if sprite in (7823, 2417, 7411):
            zero_offsets = True
        if zero_offsets:
            self.sprite_offset_x = self.sprite_offset_y = 0
        else:
            sw = self._call("sprite_get_width", sprite)
            sh = self._call("sprite_get_height", sprite)
            ih = self._call("sprite_get_height", self.spr_idle)
            self.sprite_offset_x = 0.5*sw - self._call("sprite_get_xoffset", sprite)
            self.sprite_offset_y = -0.5*ih + sh - self._call("sprite_get_yoffset", sprite)
        self.sprite_index = self.paused_spr = sprite
        if isinstance(duration, (int, float)) or duration is None:
            if duration is not None and duration > 0:
                self.anim_delayer = self._call("scr_delay_var", self,
                                             "forced_anim", False, duration)
        else:
            self.anim_delayer = self._call("scr_delay_var_until", self,
                                         "forced_anim", False, duration)

    def restore_animation(self):
        if self._exists(self.anim_delayer):
            self._kill(self.anim_delayer)
        self.sprite_offset_x = self.sprite_offset_y = 0
        self.forced_anim = False

    def custom_behaviour(self, routine, wait, callback=None):
        self.restore_default_behavior(True)
        self.caterpillarmode = False
        self.custom_state = routine
        self.state = -1
        if callback is None:
            callback = self.restore_default_behavior
        if isinstance(wait, (int, float)) or wait is None:
            if wait is not None and wait > 0:
                self.custom_waiter = self._call("scr_script_delayed", callback, wait)
        else:
            self.custom_waiter = self._call("scr_script_delayed_until", callback, wait)

    def restore_default_behavior(self, keep_caterpillar=False):
        if self._exists(self.custom_waiter):
            self._kill(self.custom_waiter)
        self.long = False
        self.wallcollision = True
        self.back_marker_scale = 1
        self.platform_mode_target = NOONE
        self.attacking = 0
        self.is_platform_mode = 0
        if self.image_speed == 0:
            self.image_speed = 0.25
        self.important = False
        self.grounded = self._call("check_if_above_ground", self,
                                   default=NOONE) != NOONE
        self.groundedprev = self.grounded
        self.physics = True
        if self.sprite_index == self._sprite("spr_plat_ralsei_hanging_torso"):
            self.sprite_index = self._sprite("spr_plat_ralsei_hanging")
        self.platform.mask_index = self._sprite("spr_plat_blankmask")
        self.entity_gravity = self.default_gravity
        if self.paused:
            self.paused_grav = self.default_gravity
        else:
            self.gravity = self.default_gravity
        self._call("scr_plat_depthcast", self, default=None)
        self.jumpsquat = self.jumping = 0
        self.state = 0
        self.platform_valid = False
        if not keep_caterpillar:
            self.init_caterpillarmode()
            self.restore_animation()

    def turn_into_platform(self, target, xoffset, yoffset, custom_mode=NOONE):
        """Create-event method called by scr_plat_ralsei_attach."""
        self.restore_default_behavior()
        self.wallcollision = 0
        self.offscreen_despawn_cooldown = 100
        self.is_platform_mode = 1
        self.platform_valid = False
        self.long = bool(self._first("obj_dw_fcastle_top_ascent") and
                         len(getattr(self.globals, "flag", [])) > 1903 and
                         self.globals.flag[1903])
        self.player_stood_on_ralsei_recently = False
        self.custom_platform_mode = custom_mode
        self.hspeed = 0
        self.image_alpha = 1
        self.state = 1
        self.gravity = self.entity_gravity
        self.caterpillarmode = False
        self.forced_anim = False
        self.platform_mode_timer = 0
        self.platform_mode_target = target
        self.platform_mode_offset = [xoffset, yoffset]
        self.force_jump()
        self.physics = False
        self.land_anim = False
        self.vspeed = 1
        self.jump_coyote_time = 5

    def onscreen_tolerance(self, tolerance, check_vertical=True):
        for camera in self._instances("obj_plat_camera"):
            if self.x + tolerance <= camera.x - 320:
                return False
            if self.x - tolerance >= camera.x + 320:
                return False
            if check_vertical:
                if self.y + tolerance <= camera.y - 240:
                    return False
                if self.y - tolerance >= camera.y + 240:
                    return False
        return True

    def drop_off_platform_mode(self, fade=False):
        if not (self.is_platform_mode or self.attacking or not self.onscreen_tolerance(120)):
            return
        self.back_marker_scale = 1
        self.image_alpha = 1
        self.attacking = 0
        self.player_stood_on_ralsei_recently = True
        self.long = False
        self.act_busy = False
        self.is_platform_mode = 0
        self.platform_valid = False
        self.important = False
        self.physics = True
        self.entity_gravity = self.default_gravity
        self.restore_default_behavior()
        self.gravity = self.entity_gravity
        self.image_xscale = sign(self.image_xscale) * 2 * self.scale_multiplier
        self.caterpillarmode = True
        self.forced_anim = False
        if fade:
            self.image_alpha = 0
            self._call("scr_lerpvar", self, "image_alpha", -1, 1, 30)
            parent = self._resolve(self.parent)
            if parent is None:
                raise RuntimeError("platform drop-off requires a valid parent")
            for i in range(self.position_history_length + 1):
                self.remx[i] = parent.x
                self.remy[i] = parent.y
                self.remspd[i] = parent.speed
                self.remdir[i] = parent.direction
                self.remgnd[i] = parent.ground

    def set_sprite_simple(self, sprite):
        self.sprite_index = sprite

    def draw_back_marker(self):
        self._call("draw_sprite_ext", self._sprite("spr_plat_ralsei_hanging_back_loop"),
                   0, self.x, self.y-20, self.image_xscale * self.scale_multiplier,
                   self.image_yscale * 20, 0, self.image_blend, self.image_alpha)
        self._call("draw_sprite_ext", self._sprite("spr_plat_ralsei_hanging_back"),
                   self.image_index, self.x, self.y, self.image_xscale * self.scale_multiplier,
                   2, 0, self.image_blend, self.image_alpha)

    def deactivate(self):
        self.restore_default_behavior()
        self.restore_animation()
        self._kill(self.back_marker)
        self._destroy_self()

    def ralsei_fall_down(self, duration):
        if self.name != "ralsei":
            return
        if self.is_platform_mode < 3:
            self.drop_off_platform_mode(True)
            return
        self.back_marker_scale = 1
        self.long = False
        self.force_animation(8099, None, True)
        self.__splats = duration > 0
        self.__splat_duration = duration

        def freeze():
            self.hspeed = self.vspeed = 0
            self.platform_valid = True

        def fall():
            self.platform_valid = True
            self.vspeed = min(self.vspeed + 0.5, 15)

        def landed():
            if self.__splats:
                self._sound("snd_splat")
                self.hspeed = self.vspeed = 0
                self.force_animation(4440, None, True)
                from scr_partner_abilities import scr_plat_set_cooldown
                label = self._call("stringsetloc", "SPLAT",
                                   "obj_plat_follower_slash_Create_0_gml_579_0",
                                   default="SPLAT")
                scr_plat_set_cooldown(self, label, self.__splat_duration)
                def splat_wait():
                    self.platform_valid = False
                    self.apply_ground_difference()
                self.custom_behaviour(splat_wait, self.__splat_duration)
            else:
                self.hspeed = self.vspeed = 0
                self.force_animation(1829, None, True)
                def recovered():
                    self.platform_valid = True
                    self.act_busy = False
                    self.apply_ground_difference()
                self.custom_behaviour(recovered, -1)

        def next_stage():
            self.custom_behaviour(fall, lambda: self.grounded and self._exists(self.ground), landed)
        self.custom_behaviour(freeze, 15, next_stage)

    def apply_ground_difference(self):
        ground = self._resolve(self.ground)
        if ground is None:
            return
        self.grounded = 1
        if ground.moving_platform or ground.rideable:
            if not self._exists(self._instance_place(self.x + ground.dif_x,
                                                      self.y + ground.dif_y,
                                                      "obj_plat_block")):
                self.x += ground.dif_x
                self.y += ground.dif_y
                for i in range(self.position_history_length, -1, -1):
                    self.remx[i] += ground.dif_x
                    self.remy[i] += ground.dif_y

    def _player(self):
        return self._first("obj_plat_player")

    def _follow_parent(self):
        return self._resolve(self.parent)

    def _above_ground(self):
        return self._call("check_if_above_ground", self, default=NOONE)

    def _onscreen(self):
        return bool(self._call("scr_onscreen", self, default=True))

    def _cooldown(self, name, length):
        from scr_partner_abilities import scr_plat_set_cooldown
        # This adapter is designed for the original helper's caller context.
        return scr_plat_set_cooldown(self, name, length)

    def _new_afterimage(self, *, color=0x800080, alpha=0.6, fade=0.1):
        fx = self._spawn(self.x, self.y, "obj_afterimage")
        fx.depth = self.depth + 1
        camera = self._first("obj_runner_camera")
        if camera is not None:
            fx.hspeed = camera.movespeed / 1.5
        fx.sprite_index = self.sprite_index
        fx.image_index = self.image_index
        fx.image_speed = 0
        fx.image_xscale = self.image_xscale
        fx.image_yscale = self.image_yscale
        fx.image_blend = color
        fx.image_alpha = alpha
        fx.fadeSpeed = fade
        return fx

    def _spawn_attack_afterimage(self, timermax):
        maker = getattr(self.engine, "scr_afterimage_monochrome", None)
        if not callable(maker):
            raise NotImplementedError("scr_afterimage_monochrome needed for spell charging")
        fx = maker(self, 0x00FF00 if self.name == "ralsei" else 0xFF00FF, False)
        fx.image_alpha = self.attacktimer/timermax
        fx.image_xscale = self.image_xscale + (sign(self.image_xscale) * self.attacktimer)/100
        fx.image_yscale = self.image_yscale + self.attacktimer/100
        self._call("scr_lerpvar", fx, "image_xscale", fx.image_xscale,
                   self.image_xscale, 10)
        self._call("scr_lerpvar", fx, "image_yscale", fx.image_yscale,
                   self.image_yscale, 10)

    def _select_follow_object(self):
        player = self._player()
        if self.state == 0:
            if player is None:
                return None
            return self._call("instance_nearest", self.x, self.y,
                              self._resource("obj_plat_player"), default=player)
        if self.state == 1:
            next_marker = NOONE
            follow = None
            if isinstance(self.followtarget, str):
                for marker in self._instances("obj_plat_movemarker"):
                    if marker.extflag == self.followtarget:
                        follow = marker
                        next_marker = marker.next_extflag
                        break
            elif self._exists(self.followtarget):
                follow = self._resolve(self.followtarget)
                if getattr(follow, "object_index", None) == self._resource("obj_plat_movemarker"):
                    next_marker = follow.next_extflag
            if follow is not None:
                if (distance(follow.x, follow.y, self.x+self.followxoffset, self.y)
                        <= 60 and next_marker not in ("", NOONE)):
                    self.followtarget = next_marker
            return follow
        if self.state == 2 and player is not None:
            if player.x-80 < self.x < player.x+80:
                facing = sign(self.image_xscale)
                if self.x < player.x:
                    self.key_left = True
                    facing = -1
                else:
                    self.key_right = True
                    facing = 1
                edge = self.bbox_left-4 if facing == -1 else self.bbox_right+4
                early_cancel = (not self._exists(self._collision_line(
                    edge, self.y, edge, self.bbox_bottom+10,
                    "obj_plat_floor", 0, 0)) or self.wallhitspd != 0)
                if early_cancel:
                    self.key_left = self.key_right = False
                    self.state = 1
                return None, early_cancel
        if self.state == -1 and callable(self.custom_state):
            self.custom_state()
        return None

    def _follower_ai(self, follow):
        if follow is None:
            return
        player = self._player()
        followx = follow.x + self.followxoffset
        followy = follow.y
        if not self.caterpillarmode:
            if self.vspeed > -3 and not self.grounded:
                ground = self._above_ground()
                if not self._exists(ground):
                    followx = self.grounded_lastX
                    if follow == 912 and player is not None and player.grounded:
                        followx = player.x
            follow_dist = 90 + (40 if self.character == 2 else 0)
            if self.y > followy:
                follow_dist = 60
            if not self.grounded:
                follow_dist = 20
            if self.state == 1:
                follow_dist = min(10, follow_dist)
            if player is not None and self._exists(player.mount):
                follow_dist = 10
                followx = player.x
                self.press_jump = True
            if self.x > followx + follow_dist:
                self.key_left = True
            if self.x < followx - follow_dist:
                self.key_right = True
            if self.state == 0 and not self.attacking:
                if (self.y > followy + 120 and self.press_jump and
                        self.y > followy + 40 and
                        (not hasattr(follow, "grounded") or follow.grounded)):
                    self.press_jump = True
                if self.key_left and self._exists(self._instance_place(
                        self.x-4, self.y-2, "obj_plat_block")):
                    self.press_jump = True
                if self.key_right and self._exists(self._instance_place(
                        self.x+4, self.y-2, "obj_plat_block")):
                    self.press_jump = True
            if self.state == 1 and self.grounded:
                if self.y > followy+40 and abs(followx-self.x) <= 80:
                    self.press_jump = True
            if self.grounded and player is not None:
                if (self.hspeed != 0 and
                    not self._exists(self._collision_line(
                        self.x, self.y, self.x, self.bbox_bottom+10,
                        "obj_plat_floor", 0, 0)) and
                    not self._exists(self._collision_line(
                        self.x, self.y, self.x, self.bbox_bottom+10,
                        player.ground, 0, 0))):
                    self.press_jump = True
            cue = self._instance_place(self.x, self.y, "obj_plat_followercue")
            if self._onscreen() and self._exists(cue):
                cue = self._resolve(cue)
                if cue.dothing == 0:
                    self.press_jump = True
                elif cue.dothing == 1 and self.grounded:
                    if self.hspeed > 0 and not self._exists(self._instance_place(
                            self.x+20, self.y+2, "obj_plat_floor")):
                        self.press_jump = True
                    if self.hspeed < 0 and not self._exists(self._instance_place(
                            self.x-20, self.y+2, "obj_plat_floor")):
                        self.press_jump = True
            self.release_jump = bool(not self.climbing and self.y < follow.y and self.vspeed < 0)
            if not self._onscreen() and self.climbing:
                self.press_jump = True
                self.key_up = self.key_down = False
        if self.fallen_in_pit:
            self._clear_inputs()

    def _movement_input(self):
        speedmax = self.hspeed_max
        dashspeed = 18
        if abs(self.hspeed) < abs(self.hspeed_max) and not self.hitstop:
            self.dashing = False
        # `_gate = -4` in the source, so its conditional never runs.
        if self.dashing:
            speedmax = dashspeed
            if not hasattr(self, "afterimagetimer"):
                self.afterimagetimer = 4
            if self.afterimagetimer == 0:
                self._call("scr_afterimage", self)
                self.afterimagetimer = 4
            if self.afterimagetimer > 0:
                self.afterimagetimer -= 1
        accel = self.ground_accel if self.grounded else self.air_accel
        if self.climbing:
            accel = 0
        if self.attacking < 2 and not self.climbing:
            if self.key_left:
                self.hspeed -= accel
                if self.autorun:
                    speedmax = 18
                if self.hspeed <= -speedmax:
                    self.hspeed = -speedmax
                if self._exists(self._instance_place(self.x-1, self.y, "obj_plat_block")):
                    self.hspeed = 0
                    self.x = self.xprevious
            if self.key_right:
                self.hspeed += accel
                if self.autorun:
                    speedmax = 3   # Asymmetric autorun speeds in original GML.
                if self.hspeed >= speedmax:
                    self.hspeed = speedmax
                if self._exists(self._instance_place(self.x+1, self.y, "obj_plat_block")):
                    self.hspeed = 0
                    self.x = self.xprevious
        decel = self.ground_decel if self.grounded else self.air_decel
        if self.respawn_leap:
            decel = 1
        if self.climbing:
            decel = 0
        if ((not self.key_left and not self.key_right) or
            (self.key_left and self.key_right) or self.attacking > 2):
            self.hspeed *= decel
        if self.grounded or self.climbing:
            self.jump_coyote_time = self.jump_coyote_time_max
            self.jumping = 0
        elif self.jump_coyote_time > 0:
            self.jump_coyote_time -= 1
        if ((self.press_jump or self.jumpsquat > 0) and
            (self.climbing or self.grounded or
             (self.jump_coyote_time > 0 and self.vspeed > -1)) and
            not self.attacking and
            not self._exists(self._instance_place(self.x, self.y-4, "obj_plat_block"))):
            self.jumpsquat = max(self.jumpsquat+1, 1)
            self.press_jump = False
            if self.jumpsquat > self.jumpsquat_max:
                self.jumpsquat = 0
                self.climbing = False
                self.vspeed = -self.jumpheight
                self.y -= 1
                self.jumping = 1
        else:
            self.jumpsquat = 0
        if self.vspeed < 0 and self.release_jump and self.jumping:
            self.vspeed *= 0.8
            self.jumping = 0
        if self.vspeed > 0:
            self.jumping = 0

    def _pit_respawn(self):
        if not (self.respawn_leap_enabled or self.fallen_in_pit):
            # No need to query camera bounds if pit recovery is disabled.
            return
        viewport = self._call("scr_get_vxy", 0)
        # scr_get_vxy writes vx,vy,vw,vh in the caller's GML scope.
        if viewport is not None and len(viewport) == 4:
            vx, vy, vw, vh = viewport
        else:
            try:
                vx, vy, vw, vh = (self.vx, self.vy, self.vw, self.vh)
            except AttributeError as exc:
                raise NotImplementedError(
                    "scr_get_vxy must return (vx,vy,vw,vh) or set follower fields"
                ) from exc
        if (not self.fallen_in_pit and
            self.y > vy+vh+self.sprite_height*.5 and self.respawn_leap_enabled):
            self.fallen_in_pit = True
            self._sound("snd_firework_send")
            self.respawn_leap = False
            self.physics = False
            self.vspeed = self.hspeed = self.gravity = 0
            self.respawn_leap_wait = 15
            player = self._player()
            if player is None:
                raise RuntimeError("Pit recovery requires obj_plat_player")
            self.checkpoint_x = clamp(player.x-80*sign(player.image_xscale),
                                      vx+80, vx+vw-80)
            self._call("scr_lerpvar_instance", self, "x", self.x,
                       self.checkpoint_x, self.respawn_leap_wait, 2, "out")
        if self.fallen_in_pit:
            if not self.respawn_leap:
                self.respawn_leap_wait -= 1
                self.vspeed = 0
                self.y = vy+vh+self.sprite_height*2
            if self.respawn_leap_wait <= 0 and not self.respawn_leap:
                self.x = self.checkpoint_x
                self._sound("snd_jump")
                self.y = vy+vh
                self.respawn_leap = True
                self.vspeed = -33
                self.hspeed = 0
                self.gravity = self.entity_gravity
                self.gravity_direction = 270
            if self.respawn_leap:
                if self.x != clamp(self.x, vx+80, vx+vw-80):
                    self.hspeed = 0
                    self.x = clamp(self.x, vx+80, vx+vw-80)
                if self.vspeed > 0 and self._onscreen():
                    if (not self._exists(self._instance_place(
                            self.x, self.y, "obj_plat_block")) and
                        self.y < vy+vh-40 and
                        self.x == clamp(self.x, vx+self.sprite_width,
                                        vx+vw-self.sprite_width)):
                        self.fallen_in_pit = False
                        self.respawn_leap = False
                        self.physics = True

    def _caterpillar_follow(self):
        if not self.caterpillarmode:
            return
        parent = self._follow_parent()
        if parent is None:
            return
        d = int(self.caterpillardist)
        self.ground = self.remgnd[d]
        force_follow = 0
        candidate = self._collision_line(self.x, self.bbox_bottom-2,
                                         self.x, self.bbox_bottom+2,
                                         "obj_plat_floor", 0, 0)
        if self._exists(candidate):
            self.ground = candidate
        else:
            force_follow = 1
        wall = self._collision_line(self.x, self.bbox_top,
                                    self.x, self.y, "obj_plat_block", 0, 0)
        if self._exists(wall):
            force_follow = 1
        if self.offscreen_despawn_cooldown > 0:
            force_follow = 0
        self.remgnd[d] = self.ground
        self.apply_ground_difference()
        self.parent_dist = distance(self.x, self.y, parent.x, parent.y)
        if (force_follow or not self.grounded or not parent.grounded or
                round(parent.speed) > 2 or self.parent_dist >= 200):
            for i in range(self.position_history_length, 0, -1):
                self.remx[i] = self.remx[i-1]
                self.remy[i] = self.remy[i-1]
                self.remspd[i] = self.remspd[i-1]
                self.remdir[i] = self.remdir[i-1]
                self.remgnd[i] = self.remgnd[i-1]
            self.remx[0] = parent.x
            self.remy[0] = parent.bbox_bottom - self.bbox_bottom_r
            self.remspd[0] = parent.speed
            self.remdir[0] = parent.direction
            self.remgnd[0] = parent.ground
        destx = self.remx[d]
        desty = self.remy[d]
        dist = distance(self.x, self.y, destx, desty)
        self._call("move_towards_point", self, destx, desty, dist*.5)
        self.gravity = 0
        if (self.grounded and not self.turn_anim and
            sign(self.hspeed) != sign(self.image_xscale) and abs(self.hspeed) > 0):
            self.turn_anim = True
            self.sprite_index = self.spr_turn
            self.image_speed = .5
            self.image_index = 0
        if self.x < destx:
            self.image_xscale = 2*self.scale_multiplier
        if self.x > destx:
            self.image_xscale = -2*self.scale_multiplier
        self.ground = self.remgnd[d]
        if self._exists(self.ground):
            self.grounded = True

    def _attack_tick(self, early_cancel=False):
        if self.attacking <= 0:
            return
        self.vspeed = max(self.vspeed, 0)
        self.apply_ground_difference()
        if self.caterpillarmode:
            self.attacktimer += 1
            if self.attacktimer >= 30:
                self.state = 1
                self.restore_animation()
                self.caterpillarmode = 0
                self.attacking = 1
                self.attacktimer = 0
            return
        if self.is_quick_attack:
            t = min(self.attacktimer / 10, 1)
            self.vspeed = lerp(self.vspeed, -self.gravity, t)
            self.hspeed = lerp(self.hspeed, 0, t)
        if self.attacking == 0.5:
            # GML has no special case for 0.5, though it remains >0.
            return
        if self.attacking == 1:
            self.state = 2
            self.caterpillarmode = False
            if self.is_quick_attack:
                self.attacking = 2
                self.forced_anim = True
                self.state = 0
                obj = self._resolve(self.target)
                if obj is not None:
                    self.image_xscale = 2*self.scale_multiplier if obj.x > self.x else -2*self.scale_multiplier
                self.image_speed = .25
                self.attacktimer = 0
            elif self.grounded:
                self.attacktimer += 1
                player = self._player()
                in_range = bool(player and player.x-80 < self.x < player.x+80)
                if early_cancel or self.attacktimer > 40 or not in_range:
                    obj = self._resolve(self.target)
                    player_dist = (distance(self.x, self.y, player.x, player.y)
                                   if player is not None else float("inf"))
                    if ((not early_cancel and player_dist < 40) or obj is None):
                        self.attacking = 0
                        self.state = 0
                        self.init_caterpillarmode()
                    else:
                        if self.name == "susie":
                            self._sound("snd_boost")
                            self.sprite_index = self._sprite("spr_plat_susie_spellready_unhappy" if
                                self._call("scr_use_unhappy_sprites", default=False) else "spr_plat_susie_spellready")
                        else:
                            self._sound("snd_spellcast")
                            self.sprite_index = self._sprite("spr_plat_ralsei_spellready")
                        self.attacking = 2
                        self.forced_anim = True
                        self.state = 0
                        self.image_xscale = (2*self.scale_multiplier if obj.x > self.x
                                             else -2*self.scale_multiplier)
                        self.image_speed = .25
                        self.hspeed = self.vspeed = 0
                        self.attacktimer = 0
        elif self.attacking == 2:
            self.attacktimer += 1
            t1, t2 = (2, 6) if self.is_quick_attack else (30, 40)
            if self.attacktimer == t1:
                if self.name == "susie":
                    self.sprite_index = self._sprite("spr_susiep_attackready")
                else:
                    self.sprite_index = self._sprite("spr_plat_ralsei_spell")
                self.image_index = 0
                self.image_speed = .25
            if self.attacktimer < t2 and self.attacktimer % 3 == 0:
                self._spawn_attack_afterimage(t2)
            if self.attacktimer == t2:
                obj = self._resolve(self.target)
                if obj is not None:
                    if self.name == "susie":
                        self.sprite_index = self._sprite("spr_susiep_attack")
                        self._sound("snd_rudebuster_swing")
                        self.image_index = 0
                        self.image_speed = .25
                        blast = self._spawn(self.x+40, self.y+30, "obj_rudebuster_bolt_plat")
                        blast.caster = 0
                        blast.interim_target_reached = self.buster_interim == 0
                        blast.interim_target_x = self.buster_interim
                        blast.explodes = self.buster_explode
                        blast.target = self.target
                        blast.owner = self
                        blast.damage = 2
                        blast.star = 0
                    elif self.name == "ralsei":
                        self._sound("snd_power")
                        self._call("event_user", obj, 7)
                        heal = self._spawn(obj.x, obj.y, "obj_healanim")
                        heal.target = self.target
                else:
                    self._cooldown(self._susie_attack_cooldown_text,
                                   self.__susie_act_cooldown)
                    self.attacking = False
                    self.attacktimer = 0
                # Preserving the original unconditional `attacking = 3` even
                # when the target disappeared during attack stage 2.
                self.attacktimer = 0
                self.attacking = 3
        elif self.attacking == 3:
            self.attacktimer += 1
            timermax = 10 if self.is_quick_attack else 22
            if self.attacktimer > timermax:
                self.forced_anim = False
                self.init_caterpillarmode()
                self._cooldown(self._susie_attack_cooldown_text,
                               self.__susie_act_cooldown)
                self.attacking = False

    def _platform_tick(self):
        if self.is_platform_mode:
            self.platform_mode_timer += 1
            self.grounded = False
            target = self._resolve(self.platform_mode_target)
            if self.is_platform_mode == 1:
                self.ground = NOONE
                self.image_alpha -= .15
                if self.platform_mode_timer == 8 and self._first("obj_dog_hanging") is None:
                    if target is None:
                        raise RuntimeError("Ralsei's platform-mode target is missing")
                    self.image_alpha = 0
                    self.is_platform_mode = 2
                    self.platform_mode_timer = 0
                    self.x = target.x + target.hang_xoffset
                    self.y = target.y + target.hang_yoffset - 20
                    self.vspeed = 2
            elif self.is_platform_mode == 2:
                if target is None:
                    raise RuntimeError("Ralsei's platform-mode target is missing")
                self.x = target.x + target.hang_xoffset
                self.vspeed += .2
                self.gravity = 1
                ytarget = target.y + target.hang_yoffset + 60
                self.image_alpha += .1
                if self.y+self.vspeed >= ytarget:
                    self.y = ytarget
                    self.platform.mask_index = self.platform.sprite_index
                    self.image_alpha = 1
                    self.is_platform_mode = 3
                    self.forced_anim = True
                    self.vspeed = self.entity_gravity = self.gravity = 0
                    self._sound("snd_grab")
                    self.back_marker = self._spawn(self.x, self.y, "obj_marker_fancy")
                    self.back_marker.sprite_index = self._sprite("spr_plat_ralsei_hanging_back")
                    self._call("scr_darksize", self.back_marker)
                    self.back_marker.draw_func = self.draw_back_marker
        if self.is_platform_mode < 3:
            self.platform.mask_index = (self.platform.sprite_index if self.platform_valid
                                        else self._sprite("spr_plat_blankmask"))
            if self._exists(self.back_marker):
                self._kill(self.back_marker)
        if self.visible:
            if (self.state != 1 and self.offscreen_despawn_cooldown <= 0 and
                    not self.onscreen_tolerance(120)):
                self.drop_off_platform_mode(True)
            if (self.is_platform_mode > 1 and self.offscreen_despawn_cooldown <= 0 and
                    not self.onscreen_tolerance(120, False)):
                self.drop_off_platform_mode(True)
        self.physics = not self.is_platform_mode > 1
        if self.caterpillardist > self.default_dist:
            self.caterpillardist = approach(self.caterpillardist, self.default_dist, 1)

    def _free_will_tick(self):
        # Uses engine's collision queries rather than assuming all candidates
        # are accessible from instance lists. Candidates expose original
        # `char`, `active`, `blocked`, `activetimer`, `owner` and `select`.
        if self.free_will and not self.act_busy and self.is_platform_mode % 3 == 0 and self.attacking == 0:
            player = self._player()
            if player is None:
                return
            selected = None
            can_act = False
            if self.name == "ralsei":
                can_act = ((not self.is_platform_mode or
                            (self.is_platform_mode == 3 and self.player_stood_on_ralsei_recently))
                           and not player.grounded and player.vspeed < 12)
                candidates = self._call("collision_circle_list", player.x,
                                        player.y, 300,
                                        self._resource("obj_plat_targethelper"),
                                        False, True, default=())
                best_dist = float("inf")
                for cand in candidates:
                    owner = self._resolve(cand.owner)
                    if (cand.char == "ra" and owner is not None and
                            hasattr(owner, "ralsei_ready")):
                        d = distance(player.x, player.y, cand.x, cand.y)
                        if (cand.active and not cand.blocked and
                                not owner.ralsei_ready and d < best_dist and cand.activetimer > 60):
                            selected, best_dist = cand, d
                if selected is not None:
                    d = distance(player.x, player.y, selected.x, selected.y)
                    self.free_will_target_lerp = 1 - (d-200)/100
                    if d > 200:
                        can_act = False
            else:
                can_act = self.attacking == 0 and player.vspeed > -30
                vradius, hradius = 160, 260
                candidates = self._call("collision_rectangle_list",
                                        player.x-hradius-100,
                                        player.y-vradius-40,
                                        player.x+hradius+100,
                                        player.y+vradius+40,
                                        self._resource("obj_plat_targethelper"),
                                        False, True, default=())
                for cand in candidates:
                    if cand.active and not cand.blocked and cand.char == "su" and cand.activetimer > 20:
                        selected = cand  # original chooses last eligible
                if selected is not None:
                    self.free_will_target_lerp = 1 - (
                        distance(0, 0, selected.x-player.x,
                                 (selected.y-player.y)*1.8) - 260)/200
                    if (selected.x < player.x-hradius or selected.x > player.x+hradius or
                        selected.y < player.y-vradius or selected.y > player.y+vradius):
                        can_act = False
            if self.free_will_target is not selected:
                self.free_will_target = selected if selected is not None else NOONE
                if not can_act and selected is not None:
                    self.free_will_target_x = selected.x
                    self.free_will_target_y = selected.y
            if can_act and selected is not None:
                if self._onscreen():
                    self._sound("snd_select")
                selected.select()
                self.free_will_target = NOONE
            if not self._exists(self.free_will_target):
                self.free_will_target_x, self.free_will_target_y = self.x, self.y
        if self.free_will:
            highlighted = True
            if self._first("obj_dw_fcastle_top_ascent") is not None:
                player = self._player()
                if player is not None:
                    highlighted = self.y > 2960 and player.x < 1800
            self.highlighted = not self.act_busy and highlighted
            if not self.highlighted:
                self.free_will_target = NOONE
            self.important = True

    def step(self):
        """Main Step event from supplied second attachment.

        External physics, collision and parent-object callbacks are routed to
        the engine (and intentionally *not* invented).
        """
        if self.destroyed:
            return
        self._tick_delays()
        player = self._player()
        if self.parent == NOONE and player is not None:
            self.parent = player
            for i in range(self.position_history_length+1):
                self.remx[i] = player.x
                self.remy[i] = player.bbox_bottom-self.bbox_bottom_r-2
                self.remspd[i] = player.speed
                self.remdir[i] = player.direction
                self.remgnd[i] = NOONE
        if self.paused or self.custom_paused:
            self._call("scr_pause_alarms", self, default=None)
            return
        self.offscreen_despawn_cooldown -= 1
        jump_pressed = self.press_jump
        self._clear_inputs()
        self.key_left = self.key_left_override
        self.key_right = self.key_right_override
        self.press_jump = jump_pressed
        self.onscreen = True
        follow = self._select_follow_object()
        early_cancel = False
        if isinstance(follow, tuple):
            follow, early_cancel = follow
        self._follower_ai(follow)
        self._movement_input()
        self._pit_respawn()
        if self._parent_step is not None:
            self._parent_step(self)
        self._caterpillar_follow()
        if self.axethrow and self.state == 0 and not self.attacking:
            self.axethrow_cooldown -= 1
        if self.axethrow_cooldown <= 0:
            self.user_event_0()
        self._attack_tick(early_cancel)
        self._platform_tick()
        self._free_will_tick()
        if self.state == 1:
            self.reached_target()

    def end_step(self):
        """GML Step_2: platform placement, sprite animation, collision failsafe."""
        if self.destroyed:
            return
        if self._exists(self.platform):
            platform = self._resolve(self.platform)
            platform.image_xscale = .75*self.image_xscale
            platform.image_yscale = 2
            old_x = platform.x
            platform.x = self.x - .75*platform.sprite_width
            if self.long > 0:
                platform.image_xscale *= 1+self.long
                platform.x -= 24*self.long
            if abs(platform.x-old_x) > 20:
                platform.xprevious += platform.x-old_x
            platform.y = self.y+4
            if self.is_platform_mode == 3:
                obj = self._resolve(self.platform_mode_target)
                if obj is None:
                    raise RuntimeError("Hanging platform requires platform_mode_target")
                self.x = obj.x+obj.hang_xoffset
                self.y = obj.y+obj.hang_yoffset+60
                self.image_xscale = abs(self.image_xscale)
                self.image_speed = 0
                self.image_index = 0
                platform.mask_index = platform.sprite_index
                if self._call("scr_plat_standing_on", "kr", platform, default=False):
                    self.image_index += 1
                    self.player_stood_on_ralsei_recently = True
                if self._call("scr_plat_standing_on", "su", platform, default=False):
                    self.image_index += 1
                self.sprite_index = self._sprite("spr_plat_ralsei_hanging_torso")
                if self.custom_platform_mode != NOONE:
                    # GML `with(platform_mode_target) other.custom_platform_mode(other)`
                    self._call("invoke_platform_mode_callback", obj,
                               self.custom_platform_mode, self)
            self._set_platform_difference(platform)
        player = self._player()
        cutscene = self._first("obj_cutscene_master") is not None
        targetmode = bool(player is not None and player.targetmode)
        if cutscene or self.attacking or self.forced_anim or targetmode:
            self.important_blend = approach(self.important_blend, 1, .15)
            if self.attacking or self.forced_anim:
                if player is not None and not targetmode and not self.is_platform_mode:
                    self._call("scr_plat_depthcast", self, default=None)
                if self.important:
                    self.depth -= 2
        elif not self.is_platform_mode:
            self.important_blend = approach(self.important_blend,
                                            self.important, .15)
            self._call("scr_plat_depthcast", self, default=None)
            if self.important:
                self.depth -= 2
        if self.paused or self.custom_paused:
            return
        if not self.caterpillarmode and not self.platform_valid and not self.attacking:
            if self._parent_end_step is not None:
                self._parent_end_step(self)
        if self._exists(self.back_marker):
            marker = self._resolve(self.back_marker)
            self.y += (self.back_marker_scale-1)*20
            self.platform.y = self.y+4
            marker.x, marker.y = self.x, self.y
            marker.image_xscale = self.image_xscale
            marker.image_yscale = self.image_yscale + self.back_marker_scale
            marker.image_blend = self.image_blend
            marker.image_index = self.image_index
            marker.depth = self.depth+20
        if self.kris_throw_state > 0:
            self.speed = self.gravity = 0
            return
        landing_sound = False
        do_autorun = bool(self.autorun and self.grounded and not self.climbing)
        if self.forced_anim:
            return
        if (self.grounded != self.groundedprev and self.grounded and
                not self.land_anim and self.ground != NOONE):
            self.land_anim = True
            landing_sound = True
            self.sprite_index = self.spr_land
            self.image_index = 0
            self.image_speed = .25
        if not self.climbing:
            if self.key_left:
                if self.grounded and not self.turn_anim and self.hspeed > .1:
                    self.turn_anim = True
                    self.sprite_index = self.spr_turn
                    self.image_speed = .5
                self.image_xscale = -2*self.scale_multiplier
            if self.key_right:
                self.image_xscale = 2*self.scale_multiplier
                if self.grounded and not self.turn_anim and self.hspeed < -.1:
                    self.turn_anim = True
                    self.sprite_index = self.spr_turn
                    self.image_speed = .5
        if self.grounded and not self.climbing and not do_autorun:
            is_stopping = (((not self.key_left and not self.key_right) or
                            (self.key_left and self.key_right)) and
                           not self.caterpillarmode) or (
                               self.caterpillarmode and abs(self.hspeed) <= .5 and
                               self.sprite_index == self.spr_run and not self.turn_anim)
            if (is_stopping and not self.runstop_anim and not self.land_anim
                    and self.sprite_index == self.spr_run):
                self.turn_anim = False
                self.runstop_anim = True
                self.sprite_index = self.spr_halt
                self.image_index = 0
                self.image_speed = .3
        if self.key_left or self.key_right or self.sprite_index != self.spr_halt:
            self.runstop_anim = False
        if not self.grounded:
            self.land_anim = self.turn_anim = self.runstop_anim = False
        if self.sprite_index != self.spr_land or self.key_left or self.key_right:
            self.land_anim = False
        if (not self.hurt and not self.land_anim and not self.turn_anim and
            not self.runstop_anim and not self.climbing and not do_autorun):
            if not self.turn_anim:
                self.image_speed = .25
            if self.grounded:
                if ((self.key_left or self.key_right) or
                        (self.caterpillarmode and abs(self.hspeed) > 0)):
                    if self.x != self.xprevious:
                        self.sprite_index = self.spr_run
                if self.key_left and self.hspeed > .1 and not self.turn_anim:
                    self.turn_anim = True
                    self.sprite_index = self.spr_turn
                if self.key_right and self.hspeed < -.1 and not self.turn_anim:
                    self.turn_anim = True
                    self.sprite_index = self.spr_turn
                if -.25 < self.hspeed < .25:
                    if not self.turn_anim:
                        self.image_speed = .25
                        self.sprite_index = self.spr_idle
                else:
                    if not self.turn_anim:
                        self.image_speed = .15+.25*(abs(self.hspeed)/abs(self.hspeed_max))
                    if self.key_left and self.key_right:
                        self.turn_anim = False
                        self.image_speed = .25
                        self.sprite_index = self.spr_idle
            else:
                self.image_speed = .25
                self.sprite_index = self.spr_jump if self.vspeed < 1 else self.spr_fall
        if self.climbing:
            self.sprite_index = self.spr_climb
            self.image_speed = 0
            if self.key_up:
                self.image_speed = .25
            if self.key_down:
                self.image_speed = -.25
        if do_autorun:
            self.sprite_index = self.spr_run
            self.image_speed = .25
            self.image_xscale = abs(self.image_xscale)
        if self.jumpsquat > 0:
            self.sprite_index = self.spr_land
        if self.autorun:
            self.image_xscale = self.autorun_xscale
            frequency = round(self.autorun_img_freq)
            if frequency == 0:
                raise ZeroDivisionError("GML autorun_img_freq rounded to zero")
            if self.t % frequency == 0:
                self._new_afterimage()
        # `_landingsound` block is empty in GML; no sound intentionally.
        if self.physics and self.wallcollision and self.visible:
            if not self.respawn_leap and not self.fallen_in_pit and not self.caterpillarmode:
                self._call("scr_collision_failsafe", self)
            self._snap_to_ground()

    def animation_end(self):
        """Other_7: Animation End."""
        if self.forced_anim:
            return
        if self.turn_anim and self.sprite_index == self.spr_turn:
            self.sprite_index = self.spr_idle
        self.turn_anim = False
        if self.runstop_anim and self.sprite_index == self.spr_halt:
            self.sprite_index = self.spr_idle
        self.runstop_anim = False
        if self.attacking and self.sprite_index == self._sprite("spr_susiep_attack"):
            self.sprite_index = self.spr_idle
        if self.land_anim:
            self.sprite_index = self.spr_idle
        self.land_anim = False
        if self.kris_throw_state >= 4:
            self.kris_throw_state = 0
            self.kris_throw_wait = 60
            self.throwing_kris = False
            self.catch_waiting = False
            self.sprite_index = self.spr_jump
            self.vspeed = -17.5
            self._sound("snd_smallswing", 1.5)

    def user_event_0(self):
        """Other_10: seek a target for Susie's automatic axe attack."""
        if not self.grounded or self.attacking or self.climbing:
            return
        self.dbg_targets = []
        candidates = self._call("scr_collision_rectangle_list", self.x-300,
                                self.y-150, self.x+300, self.y+150,
                                [322, 1722], default=())
        best, best_score = None, 0
        for candidate in candidates:
            # The original adds *unsigned* distances to x/y, not signed offsets.
            best_x = self.x + min(abs(candidate.x-self.x),
                                  abs(candidate.bbox_left-self.x),
                                  abs(candidate.bbox_right-self.x))
            best_y = self.y + min(abs(candidate.y-self.y),
                                  abs(candidate.bbox_top-self.y),
                                  abs(candidate.bbox_bottom-self.y))
            dist = abs(best_x-self.x)
            if dist < 40:
                continue
            angle = direction(self.x, self.y, best_x, best_y)
            if 35 < (angle % 180) < 145:
                continue
            if angle > 90:
                angle -= 180
            score = abs(35-abs(angle))/35
            score += math.sin(math.radians((dist-40)/260*180))
            self.dbg_targets.append([best_x, best_y, 32768, score])
            if score > best_score:
                best, best_score = candidate, score
        self.axethrow_cooldown = 10
        if best is not None:
            self.target = best
            if best.x < self.x:
                self.image_xscale = -abs(self.image_xscale)
            else:
                self.image_xscale = abs(self.image_xscale)
            self.attacking = True
            self.attacktimer = 0
            self.hspeed = 0
            self.sprite_index = self._sprite("spr_susiep_attackready")
            self._sound("snd_wallclaw", 1.1)
            self.axethrow_cooldown = 140

    def event_user(self, index):
        if index != 0:
            raise ValueError("Only User Event 0 is provided for obj_plat_follower")
        return self.user_event_0()

    def _current_time(self):
        """GameMaker current_time is a builtin value; support engine value or method."""
        value = getattr(self.engine, "current_time", 0)
        return value() if callable(value) else value

    def _merge_color(self, first, second, fraction):
        color_fn = getattr(self.engine, "merge_color", None)
        if callable(color_fn):
            return color_fn(first, second, fraction)
        # GameMaker stores BGR packed integers; interpolate channels in place.
        t = clamp(fraction, 0, 1)
        return sum(round(((first >> shift)&255)*(1-t) +
                         ((second >> shift)&255)*t) << shift for shift in (0, 8, 16))

    def _outline(self):
        pulse = .8 + math.sin(self._current_time()/100)*.2
        color = self._merge_color(self.outlinecolor, 0xFFFFFF, pulse)
        self._call("scr_draw_outline", self, 2, color, 1)

    def _draw_self(self):
        return self._call("draw_self", self)

    def _draw_sprite_ext(self, spr, frame, x, y, sx, sy, angle, blend, alpha):
        return self._call("draw_sprite_ext", self._sprite(spr), frame,
                          x, y, sx, sy, angle, blend, alpha)

    def _draw_hanging_long(self):
        spr = 5688
        if self.image_index == 1:
            spr = 345
        if self.image_index == 2:
            spr = 3128
        xoff = -10-32*self.long
        basey = self.y-20+4*self.image_index
        for outline_pass in ((True, False) if self.highlighted else (False,)):
            yy = basey
            for i in range(5):
                xs = self.image_xscale
                xx = self.x+xoff-30
                if i in (1, 3):
                    xs *= (1+self.long)*.85
                    width = self._call("sprite_get_width", spr, default=32)
                    if i == 1:
                        xx -= .1*width*xs
                    if i == 3:
                        xx += .2*width*xs
                if i == 2:
                    xx = self.x-50
                if i == 4:
                    xx = self.x-60-xoff
                    yy += 2
                if i == 0:
                    xx -= 8
                if outline_pass:
                    saved = (self.image_xscale, self.image_index,
                             self.sprite_index, self.x, self.y)
                    try:
                        self.image_xscale = xs
                        self.sprite_index = spr
                        self.image_index = i
                        self.x, self.y = xx, yy
                        self._outline()
                    finally:
                        (self.image_xscale, self.image_index,
                         self.sprite_index, self.x, self.y) = saved
                else:
                    self._draw_sprite_ext(spr, i, xx, yy, xs, self.image_yscale,
                                          0, self.image_blend, self.image_alpha)

    def _draw_hanging_short(self):
        self._draw_self()
        frame = 0
        yy = self.y-11*self.image_yscale+4*self.image_index
        for player in self._instances("obj_plat_player"):
            if player.x < self.x-11*player.image_xscale:
                frame = 1
        if self.image_index > 0:
            frame = 2
        if self.highlighted:
            self._outline()
            self._draw_self()
        self._draw_sprite_ext("spr_plat_ralsei_hanging_head", frame,
                              self.x-11*self.image_xscale, yy,
                              self.image_xscale, self.image_yscale,
                              self.image_angle, self.image_blend, self.image_alpha)

    def _draw_target_arrows(self):
        if not self._exists(self.free_will_target):
            return
        xx, yy = self.x, self.y
        cx, cy = self.free_will_target_x, self.free_will_target_y
        dist = distance(xx, yy, cx, cy)
        heading = direction(xx, yy, cx, cy)
        ms = self._current_time()
        dist_off = (ms*.01) % 20
        i = 20
        while i < dist-20:
            radius = i+dist_off
            x1, y1 = lengthdir(radius, heading)
            alpha = 1
            if radius < 40:
                alpha = (radius-20)/20
            elif radius > dist-40:
                alpha = (radius-(dist-20)) / -20
            alpha2 = clamp(alpha-dist_off/20, 0, 1)/3
            x2, y2 = lengthdir(radius+dist_off*.75, heading)
            color = 0xFF00FF if self.name == "susie" else 0x00FF00
            color = self._merge_color(color, 0x808080, .5)
            self._draw_sprite_ext("spr_plat_targetmode_arrow", 0,
                xx+x2, yy+y2, 1, 1, heading, color,
                alpha2*self.free_will_target_lerp)
            self._draw_sprite_ext("spr_plat_targetmode_arrow", 0,
                xx+x1, yy+y1, 1, 1, heading, color,
                alpha*self.free_will_target_lerp)
            i += 20

    def draw(self):
        """GML Draw_0: follower, Ralsei hanging pose, debug and target arrows."""
        self.image_blend = self._merge_color(0x8F8F8F, 0xFFFFFF,
                                              self.important_blend)
        if self.is_platform_mode == 3:
            if self.long > .05:
                self._draw_hanging_long()
            else:
                self._draw_hanging_short()
        else:
            oldx, oldy = self.x, self.y
            try:
                self.x -= self.sprite_offset_x*self.image_xscale
                self.y -= self.sprite_offset_y*self.image_yscale
                if self.highlighted:
                    self._outline()
                self._draw_self()
            finally:
                self.x, self.y = oldx, oldy
        if self._call("scr_debug", default=False):
            for px, py, color, score in self.dbg_targets:
                self._call("draw_set_color", color)
                self._call("draw_line", self.x, self.y, px, py)
                self._call("draw_text", px, py, str(score))
        if getattr(self.globals, "pause_plat", False):
            return
        self._draw_target_arrows()

    def pre_draw(self):
        """GML Draw_76: collision snap, depth and back-marker depth."""
        if self.physics and self.grounded:
            self._snap_to_ground()
        player = self._player()
        if player is not None and not player.targetmode:
            if self.platform_mode_target != NOONE:
                target = self._resolve(self.platform_mode_target)
                if target is not None:
                    self.depth = target.depth-3
                    marker = self._resolve(self.back_marker)
                    if marker is not None:
                        marker.depth = target.depth-2
        else:
            marker = self._resolve(self.back_marker)
            if marker is not None:
                marker.depth = self.depth+1
        if self.forced_anim and player is not None and not player.targetmode:
            if self.is_platform_mode == 3 and self.image_index > 0:
                self.depth = player.depth-1


# GameMaker-style exported object name.
obj_plat_follower = PlatFollower

__all__ = ["PlatFollower", "PlatformFollowerPhysics", "obj_plat_follower"]
