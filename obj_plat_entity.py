"""GameMaker obj_plat_entity port for the DELTARUNE Chapter 6 Python fangame.

Supplied source: Create, Step (ordinary), Begin Step, End Step, Clean Up.

The five public ``plat_entity_*`` functions act on any instance with the
expected GameMaker-style fields. This lets PlatFollower use them as inherited
callbacks without changing its existing class layout::

    PlatFollower(game, parent_create=plat_entity_create,
                 parent_step=plat_entity_step,
                 parent_end_step=plat_entity_end_step)

The caller's engine implements GameMaker collision queries, sprite/bbox data,
platform helpers, and the normal built-in movement/gravity update. This port
reproduces the *scripted* entity logic, not GameMaker's entire physics runtime.

In GameMaker, ``obj_plat_entity`` inherits from ``obj_culled_object``. Its
parent Create event may be supplied as an ``inherited_create`` callback.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Callable

NOONE = -4
DS_TYPE_LIST = "ds_type_list"
_MISSING = object()


@dataclass(frozen=True)
class PlatformEntityPhysicsMetadata:
    density: float = 0.5
    restitution: float = 0.1
    group: int = 1
    linear_damping: float = 0.1
    angular_damping: float = 0.1
    friction: float = 0.2
    is_awake: bool = True
    is_kinematic: bool = False
    vertices: tuple = ((-20, -20), (14, -20), (14, 16), (-20, 16))


def _engine(obj):
    return getattr(obj, "engine", obj)


def _call(obj, name, *args, default=_MISSING):
    fn = getattr(_engine(obj), name, None)
    if callable(fn):
        return fn(*args)
    if default is not _MISSING:
        return default
    raise NotImplementedError(
        f"obj_plat_entity requires engine.{name}(...) for this operation"
    )


def _ref(obj, resource):
    return getattr(_engine(obj), resource, resource) if isinstance(resource, str) else resource


def _exists(obj, value):
    if value is None or value == NOONE or value == 0:
        return False
    engine = _engine(obj)
    fn = getattr(engine, "i_ex", None) or getattr(engine, "instance_exists", None)
    if callable(fn):
        return bool(fn(value))
    return not isinstance(value, (int, float, str)) and not getattr(value, "destroyed", False)


def _resolve(obj, value):
    if not _exists(obj, value):
        return None
    if not isinstance(value, (int, float, str)):
        return value
    return _call(obj, "resolve_instance", value)


def _place(obj, x, y, resource):
    return _call(obj, "instance_place", x, y, _ref(obj, resource))


def _clamp(value, low, high):
    return min(max(value, low), high)


def _list_valid(obj, handle):
    if isinstance(handle, list):
        return True
    checker = getattr(_engine(obj), "ds_exists", None)
    return bool(checker(handle, _ref(obj, DS_TYPE_LIST))) if callable(checker) else False


def _list_create(obj):
    return _call(obj, "ds_list_create", default=[])


def _list_clear(obj, handle):
    if isinstance(handle, list):
        handle.clear()
    else:
        _call(obj, "ds_list_clear", handle)


def _list_items(obj, handle, count):
    if isinstance(handle, list):
        return handle[:count]
    return [_call(obj, "ds_list_find_value", handle, i) for i in range(count)]


def _colliding_slopes(obj, left, top, right, bottom, handle):
    """Populate a GameMaker DS list, or accept an iterable Python adapter.

    Original call: collision_rectangle_list(..., obj_plat_slope, 1, 1,
                                          __checklist, 0).
    """
    result = _call(obj, "collision_rectangle_list", left, top, right, bottom,
                   _ref(obj, "obj_plat_slope"), 1, 1, handle, 0)
    if isinstance(result, (list, tuple)):
        return list(result)
    return _list_items(obj, handle, int(result))


def plat_entity_create(obj, *, inherited_create: Callable | None = None):
    """Create_0; may be used as a PlatFollower parent_create callback."""
    if inherited_create is not None:
        inherited_create(obj)
    else:
        # The parent is obj_culled_object, not included in the provided GML.
        # Only invoke it when the engine has an explicit adapter.
        _call(obj, "obj_culled_object_create", obj, default=None)

    obj.physics = 1  # GML variable; NOT the GameMaker 'Uses physics' checkbox.
    obj.is_entity = 1
    obj.entity_gravity = 0.5
    obj.ground = NOONE
    obj.grounded = 0
    obj.groundedprev = 0
    obj.landspd = 0
    obj.wallhitspd = 0
    obj.max_fallspeed = 15
    obj.force_yplat = False
    obj.ignore_barriers = False
    xscale = getattr(obj, "image_xscale", 1)
    obj.image_xscale = (1 if xscale > 0 else -1 if xscale < 0 else 0) * 2
    obj.image_yscale = 2
    obj.windimmune = 0
    obj.visible_is_active = False

    obj.set_bbox_relative = lambda: plat_entity_set_bbox_relative(obj)
    obj.set_bbox_relative()
    setattr(obj, "__checklist", _list_create(obj))
    obj.wallcollision = True
    obj.floorY = 0
    obj.show_slope_angle = 0
    obj.climbing = 0
    obj.fallen_in_pit = 0
    obj.checkpoint_x = obj.x
    obj.checkpoint_y = obj.y
    obj.grounded_lastX = obj.x
    obj.flash_white = 0
    obj.shake = 0
    obj.shake_angle = 0
    obj.moved_by_platform = 0
    obj.is_slope = 0
    obj.rideable = 0
    obj.can_ride_entities = 0
    obj.moving_platform = 0
    obj.conveyor_hspeed = 0
    obj.quicksand = 0
    obj.enable_unstuck_failsafe = 1
    obj.stuck_time = 0
    obj.open_x = obj.x
    obj.open_y = obj.y
    obj.slopecheck = [0] * 5
    obj.paused_spd = 0
    obj.paused_dir = 0
    obj.paused_spr = 0
    obj.paused_img = 0
    obj.paused_imgspd = 1
    obj.paused = 0
    obj.hitstop = -1
    obj.attacking = 0
    obj.do_hitstop = lambda amount: None  # Deliberately empty in supplied GML.
    obj.lerpinst = [NOONE]
    obj.doom_obj = NOONE
    obj.__storeddepth = 100000 - ((obj.y * 10) + (obj.sprite_height * 10))
    obj.check_if_above_ground = lambda: plat_entity_check_if_above_ground(obj)
    obj.dif_type = 1
    _set_difference_call(obj)
    _call(obj, "scr_plat_set_group", 3, True)
    obj.custom_paused = False
    obj.on_pause = lambda: _call(obj, "scr_pause_plat_entity", obj)
    obj.on_unpause = lambda: _call(obj, "scr_unpause_plat_entity", obj)
    return obj


def plat_entity_set_bbox_relative(obj):
    obj.mask_width = obj.sprite_width
    obj.mask_height = obj.sprite_height
    obj.bbox_top_r = obj.y - obj.bbox_top
    obj.bbox_bottom_r = obj.bbox_bottom - obj.y


def plat_entity_check_if_above_ground(obj):
    dist = 40
    for _ in range(15):
        ground = _place(obj, obj.x, obj.y + dist, "obj_plat_floor")
        if _exists(obj, ground):
            return ground
        dist += 40
    return NOONE


def _wall_blocked(obj, wall):
    return _exists(obj, wall) and not (
        bool(getattr(_resolve(obj, wall), "is_barrier", False)) and obj.ignore_barriers
    )


def _handle_walls(obj, wall):
    if _wall_blocked(obj, wall) and obj.enable_unstuck_failsafe:
        obj.stuck_time += 1
        if obj.stuck_time >= 3:
            obj.stuck_time = 0
            obj.x = obj.open_x
            obj.y = obj.open_y
            wall = _place(obj, obj.x, obj.y, "obj_plat_block")
            if _exists(obj, wall) and getattr(_resolve(obj, wall), "moving_platform", False):
                obj.vspeed = 0
                obj.ground = wall
                _snap_to_ground_call(obj)
    obj.wallhitspd = 0
    distcheck = 2
    for _ in range(ceil(abs(obj.hspeed))):
        left = _place(obj, obj.x - distcheck, obj.y, "obj_plat_block")
        if _wall_blocked(obj, left) and obj.hspeed <= 0:
            left_obj = _resolve(obj, left)
            if obj.hspeed < 0:
                obj.wallhitspd = obj.hspeed
                obj.hspeed = 0
            if obj.x > left_obj.bbox_right:
                obj.x = left_obj.bbox_right + (round(obj.x) - obj.bbox_left) + 2
        right = _place(obj, obj.x + distcheck, obj.y, "obj_plat_block")
        if _wall_blocked(obj, right) and obj.hspeed >= 0:
            right_obj = _resolve(obj, right)
            if obj.hspeed > 0:
                obj.wallhitspd = obj.hspeed
                obj.hspeed = 0
            if obj.x < right_obj.bbox_left:
                obj.x = right_obj.bbox_left - (obj.bbox_right - round(obj.x)) - 2
        distcheck += 1


def _select_slope(obj, ground):
    slope = NOONE
    if _exists(obj, ground) and getattr(_resolve(obj, ground), "is_slope", False):
        slope = ground
    if obj.vspeed < 0:
        return slope, ground

    checklist = getattr(obj, "__checklist")
    if not _list_valid(obj, checklist):
        checklist = _list_create(obj)
        setattr(obj, "__checklist", checklist)
    _list_clear(obj, checklist)
    speed = getattr(obj, "speed", 0)
    nearby = _colliding_slopes(
        obj, obj.bbox_left - 2,
        (obj.y + obj.bbox_bottom_r) - abs(speed) - 4,
        obj.bbox_right + 2,
        obj.y + obj.bbox_bottom_r + 6 + abs(speed), checklist,
    )
    obj.slopecheck = [0] * 5
    selected = NOONE
    for i, candidate in enumerate(nearby):
        if i >= len(obj.slopecheck):
            obj.slopecheck.append(candidate)
        else:
            obj.slopecheck[i] = candidate
        candidate = _resolve(obj, candidate)
        if candidate is None:
            continue
        bounds = (min(candidate.x1, candidate.x2), max(candidate.x1, candidate.x2))
        hit_right = bounds[0] <= obj.bbox_right <= bounds[1]
        hit_left = bounds[0] <= obj.bbox_left <= bounds[1]
        if (hit_right or hit_left) if candidate.image_xscale > 0 else (hit_left or hit_right):
            selected = candidate
    if _exists(obj, selected):
        slope = selected
        ground = selected
    return slope, ground


def _snap_to_ground_call(obj):
    """Prefer per-entity GML context; retain the original engine fallback."""
    bound = getattr(obj, "scr_plat_snap_to_ground", None)
    if callable(bound):
        return bound()
    return _call(obj, "scr_plat_snap_to_ground", obj)


def _set_difference_call(obj):
    """Prefer per-instance GML context; accept the older engine adapter."""
    bound = getattr(obj, "scr_plat_set_difference", None)
    if callable(bound):
        return bound()
    engine_call = getattr(_engine(obj), "scr_plat_set_difference", None)
    if callable(engine_call):
        return engine_call(obj)
    # Standalone fallback when no legacy engine callback is registered.
    from scr_plat_set_difference import scr_plat_set_difference
    return scr_plat_set_difference(obj)


def _ground_check_call(obj, name, *args):
    """Keep the caller's GML instance context when a bound helper is installed.

    Existing engine-level adapters remain supported for older ported objects.
    """
    bound = getattr(obj, name, None)
    if callable(bound):
        return bound(*args)
    return _call(obj, name, *args)


def _handle_ground(obj):
    obj.ground = NOONE
    obj.groundedprev = obj.grounded
    obj.landspd = 0
    ycheck = obj.y + _clamp(getattr(obj, "dif_y", 0) * 4, 4, 18)
    if obj.vspeed > 0:
        ycheck = obj.y + ceil(abs(obj.vspeed) + 4)
    ground = _ground_check_call(obj, "scr_ground_checks", obj.x, ycheck, 708)
    slope, ground = _select_slope(obj, ground)
    if obj.can_ride_entities:
        entity = _ground_check_call(obj, "scr_ground_entity_checks", obj.x, ycheck)
        if _exists(obj, entity):
            ground = entity

    if _exists(obj, ground) and obj.vspeed >= 0 and not obj.climbing:
        if not obj.grounded:
            obj.grounded = 1
        obj.grounded_lastX = obj.x
        obj.ground = ground
        obj.gravity = 0
        obj.gravity_direction = 270
        obj.landspd = obj.vspeed
        obj.vspeed = 0
        _snap_to_ground_call(obj)
    else:
        if obj.grounded:
            obj.grounded = 0
            obj.ground = NOONE
        obj.gravity = obj.entity_gravity
        obj.gravity_direction = 270
        runner = _place(obj, obj.x, obj.y, "obj_plat_slope_runner")
        if obj.vspeed < 0 and _exists(obj, runner):
            # GML uses an unbounded while loop. Bound iterations to catch a
            # malformed/stale collision provider rather than hang the game.
            for _ in range(4096):
                if (_exists(obj, _place(obj, obj.x, obj.y - 4, "obj_plat_block")) or
                        not _exists(obj, _place(obj, obj.x, obj.y, runner))):
                    break
                obj.y -= 4
            else:
                raise RuntimeError("Slope-runner push-out failed to converge")

    if obj.grounded and _exists(obj, obj.ground):
        floor = _resolve(obj, obj.ground)
        if floor.quicksand:
            obj.y += floor.quicksand
        if floor.conveyor_hspeed != 0:
            change = floor.conveyor_hspeed
            if not _exists(obj, _place(obj, obj.x + change, obj.y, "obj_plat_block")):
                obj.x += change

    if obj.wallcollision:
        ceiling = _place(obj, obj.x, obj.y - abs(obj.vspeed), "obj_plat_block")
        if _wall_blocked(obj, ceiling) and obj.vspeed < 0:
            obj.vspeed = 0
            obj.y += 2
            obj.gravity = obj.entity_gravity
            obj.gravity_direction = 270

    if obj.vspeed > obj.max_fallspeed:
        obj.vspeed = obj.max_fallspeed


def plat_entity_step(obj):
    """Ordinary Step_0; does not simulate GameMaker's built-in movement tick."""
    if obj.visible_is_active and not obj.visible:
        return
    wall = NOONE
    if obj.wallcollision:
        wall = _place(obj, obj.x, obj.y, "obj_plat_block")
        if not _wall_blocked(obj, wall):
            obj.open_x, obj.open_y = obj.x, obj.y
            obj.stuck_time = 0

    if obj.physics and not obj.paused and not obj.custom_paused:
        if obj.wallcollision:
            _handle_walls(obj, wall)
        _handle_ground(obj)


def plat_entity_begin_step(obj):
    """Begin Step (Step_1): manage hitstop and pause/unpause callbacks."""
    if obj.visible_is_active and not obj.visible:
        return
    globals_ = getattr(_engine(obj), "global_state", _engine(obj))
    if obj.hitstop > 0 and not getattr(globals_, "pause_plat", False):
        obj.hitstop -= 1
    should_pause = obj.hitstop > 0
    if not obj.custom_paused and should_pause:
        obj.on_pause()
        obj.paused = 0
        obj.custom_paused = True
    if obj.custom_paused and not should_pause:
        obj.on_unpause()
        obj.custom_paused = False


def plat_entity_end_step(obj):
    """End Step (Step_2): move alongside rideable or moving ground."""
    if obj.visible_is_active and not obj.visible:
        return
    if not obj.physics or not obj.grounded or not _exists(obj, obj.ground):
        return
    floor = _resolve(obj, obj.ground)
    if not (floor.moving_platform or floor.rideable):
        return
    x_next = obj.x + floor.dif_x
    y_next = obj.y + floor.dif_y
    if _exists(obj, _place(obj, x_next, y_next, "obj_plat_block")):
        if not _exists(obj, _place(obj, x_next, obj.y, "obj_plat_block")):
            obj.x = x_next
        if not _exists(obj, _place(obj, obj.x, y_next, "obj_plat_block")):
            obj.y = y_next
    else:
        obj.x, obj.y = x_next, y_next
    if obj.grounded:
        _snap_to_ground_call(obj)


def plat_entity_cleanup(obj):
    """Clean Up event: destroy the slope-check DS list if it exists."""
    checklist = getattr(obj, "__checklist", None)
    if isinstance(checklist, list):
        checklist.clear()  # Python list analogue; no manual destruction needed.
    elif _list_valid(obj, checklist):
        _call(obj, "ds_list_destroy", checklist)


class PlatEntity:
    """Directly instantiable obj_plat_entity (for engine object registration)."""
    object_name = "obj_plat_entity"
    parent_object = "obj_culled_object"
    sprite_index_default = "spr_plat_entity"
    mask_index_default = "spr_plat_entity"
    visible_default = True
    solid_default = False
    persistent_default = False
    uses_physics = False
    collision_shape = "box"
    physics_metadata = PlatformEntityPhysicsMetadata()

    def __init__(self, engine, x=0, y=0, *, inherited_create=None):
        self.engine = engine
        self.x, self.y = x, y
        self.xprevious, self.yprevious = x, y
        self.image_xscale = 1
        self.image_yscale = 1
        self.sprite_index = self.sprite_index_default
        self.mask_index = self.mask_index_default
        # Actual mask/sprite dimensions belong to the renderer's asset data.
        # A 32x32 fallback only permits independent logic tests; it must not
        # be interpreted as the image's verified GameMaker collision mask.
        self.sprite_width = _call(self, "sprite_get_width", self.sprite_index, default=32)
        self.sprite_height = _call(self, "sprite_get_height", self.sprite_index, default=32)
        self.speed = self.hspeed = self.vspeed = self.gravity = 0
        self.gravity_direction = 270
        self.visible = True
        self.destroyed = False
        plat_entity_create(self, inherited_create=inherited_create)

    def _bbox(self):
        # The screenshot's physics vertices are NOT the collision mask while
        # Uses physics is unchecked. Prefer the runtime mask's true bounds.
        bbox = _call(self, "instance_get_bbox", self, default=None)
        if bbox is not None:
            return bbox  # (left, top, right, bottom)
        # Only a provisional fallback until actual mask/origin are loaded.
        scaled_width = self.sprite_width * abs(self.image_xscale)
        scaled_height = self.sprite_height * abs(self.image_yscale)
        return (self.x-scaled_width/2, self.y-scaled_height,
                self.x+scaled_width/2, self.y)

    @property
    def bbox_left(self):
        return self._bbox()[0]

    @property
    def bbox_top(self):
        return self._bbox()[1]

    @property
    def bbox_right(self):
        return self._bbox()[2]

    @property
    def bbox_bottom(self):
        return self._bbox()[3]

    def begin_step(self):
        plat_entity_begin_step(self)

    def step(self):
        plat_entity_step(self)

    def end_step(self):
        plat_entity_end_step(self)

    def cleanup(self):
        plat_entity_cleanup(self)

    def check_if_above_ground(self):
        return plat_entity_check_if_above_ground(self)

    def set_bbox_relative(self):
        return plat_entity_set_bbox_relative(self)


obj_plat_entity = PlatEntity

__all__ = (
    "PlatEntity", "obj_plat_entity", "PlatformEntityPhysicsMetadata",
    "plat_entity_create", "plat_entity_begin_step", "plat_entity_step",
    "plat_entity_end_step", "plat_entity_cleanup",
    "plat_entity_set_bbox_relative", "plat_entity_check_if_above_ground",
)
