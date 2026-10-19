"""Port of the Create, Step, and Draw events of obj_cutscene_master.

This controller orchestrates cutscene commands and their wait conditions. It
DOES NOT implement ``scr_cutscene_master_commands_initialize`` or
``scr_cutscene_commands``, whose GML sources have not yet been supplied.

Integration contract
--------------------
    master = CutsceneMaster(
        game,
        commands_initializer=lambda master: ...,  # optional
        command_handler=lambda master: ...,       # required to execute cmds
        instance_id=12345,                        # engine instance ID, optional
    )
    master.step()     # call once per game frame
    master.draw()     # original Draw event is empty

If the callbacks are omitted, the game may provide methods named
``scr_cutscene_master_commands_initialize(master)`` and
``scr_cutscene_commands(master)``. The game also supplies these operations
when the relevant waits or termination are used:

    i_ex(reference) or instance_exists(reference)
    resolve_instance(reference)                 # for instance IDs/resources
    variable_instance_exists(reference, name)
    variable_instance_get(reference, name)
    instance_destroy(reference)
    scr_debug_print(message)                    # optional

All Create-event defaults, the in-frame wait checks, the command pointer's
``i + 1`` update, and all named GML sentinels are deliberately preserved.
The exposed ``command`` and ``command_actor`` lists are only safe storage
scaffolding; actual command initialization belongs to the external script.

Be aware of original GML oddities:
* ``current_command = i + 1`` also runs on a frame already spent waiting.
* If multiple wait flags are active, any of their conditions may set
  ``waiting = 0`` before the others finish.
* A wait set by a command is evaluated in the *same* frame.
* ``cs_wait_plat_dialogue`` clears only if a sequencer exists AND messages
  becomes empty; missing sequencers do not release the wait.
"""

from __future__ import annotations

from typing import Any, Callable


NO_ACTOR = 99999999
NO_MASTER_OBJECT = 9999999
NO_DIALOGUER = 438438943


class CutsceneMaster:
    """GameMaker-compatible cutscene command/wait controller."""

    object_name = "obj_cutscene_master"
    sprite_index = None
    visible = True
    solid = False
    persistent = False
    parent = None
    texture_mask_id = None
    uses_physics = False
    is_sensor = False
    collision_shape = "circle"

    physics_density = 0.5
    physics_restitution = 0.1
    physics_group = 0
    physics_linear_damping = 0.1
    physics_angular_damping = 0.1
    physics_friction = 0.2
    physics_awake = True
    physics_kinematic = False
    physics_shape_vertices = ()

    def __init__(
        self,
        game: Any = None,
        *,
        commands_initializer: Callable[["CutsceneMaster"], Any] | None = None,
        command_handler: Callable[["CutsceneMaster"], Any] | None = None,
        instance_id: Any = None,
    ) -> None:
        self.game = game
        self.id = self if instance_id is None else instance_id
        self._commands_initializer = commands_initializer
        self._command_handler = command_handler
        self.create()

    def _adapter(self, method_name: str) -> Callable[..., Any]:
        """Find an engine callback without silently simulating a GML API."""
        local = getattr(self, method_name, None)
        if callable(local):
            return local
        remote = getattr(self.game, method_name, None)
        if callable(remote):
            return remote
        raise NotImplementedError(
            f"obj_cutscene_master requires the {method_name} engine adapter"
        )

    def _exists(self, reference: Any) -> bool:
        if reference is None:
            return False
        # Let the engine test numeric references first: the apparently
        # sentinel-like GML default may still be registered in a mock/game.
        for name in ("i_ex", "instance_exists"):
            local = getattr(self, name, None)
            remote = getattr(self.game, name, None)
            if callable(local):
                return bool(local(reference))
            if callable(remote):
                return bool(remote(reference))
        # Explicit Python instance references work without an instance registry.
        if not isinstance(reference, (int, float, str)):
            return not bool(getattr(reference, "destroyed", False))
        if reference in (-4, -1, NO_ACTOR, NO_DIALOGUER):
            return False
        raise NotImplementedError(
            "instance existence checks for resource names/IDs require "
            "i_ex() or instance_exists()"
        )

    def _resolve(self, reference: Any) -> Any:
        if not isinstance(reference, (int, float, str)):
            return reference
        return self._adapter("resolve_instance")(reference)

    def _debug_print(self, message: str) -> None:
        for obj in (self, self.game):
            callback = getattr(obj, "scr_debug_print", None)
            if callable(callback):
                callback(message)
                break

    def create(self) -> None:
        """GameMaker Create event; initialize and optionally delegate command setup."""
        self.customfuncs = []
        self.waiting = 0
        self.cs_wait_timer = 0
        self.cs_wait_amount = 0
        self.cs_wait_dialogue = 0
        self.cs_wait_custom = 0
        self.cs_wait_box = -1
        self.cs_wait_box_end = False
        self.cs_wait_plat_dialogue = 0
        self.cs_wait_if = -1
        self.cs_wait_if_objectid = self.id
        self.cs_wait_if_varname = "cs_wait_if_varvalue"
        self.cs_wait_if_operator = "="
        self.cs_wait_if_varvalue = 0
        self.mydialoguer = NO_DIALOGUER
        self.kill_actors = 0
        self.loadedState = 0
        self.instant = 0
        self.breakme = 0
        self.current_command = 0
        self.maximum_command = 1
        self.master_object = NO_MASTER_OBJECT
        self.msgside = -1
        self.stay = 0
        self.runcheck = 0
        self.preventcskip = False
        self.zurasu = 0
        self.mysound = -1
        self.initialized = 0
        self.actor_selected = "noone"
        self.actor_selected_id = NO_ACTOR

        self.actor_id = [NO_ACTOR] * 20
        self.actor_name = ["noone"] * 20
        self.save_object = [NO_ACTOR] * 10

        # The external initializer owns the meaning and contents of commands.
        self.command = []
        self.command_actor = []

        # The Create event uses the instance variable i in two for loops;
        # it ends at 10, and the Step event reuses i even when waiting.
        self.i = 10

        initializer = self._commands_initializer
        if initializer is None:
            initializer = getattr(self.game, "scr_cutscene_master_commands_initialize", None)
        self.commands_initialized = False
        if callable(initializer):
            initializer(self)
            self.commands_initialized = True

        self.terminate_this_frame = 0

    def _dispatch_command(self) -> None:
        handler = self._command_handler
        if handler is None:
            handler = getattr(self.game, "scr_cutscene_commands", None)
        if not callable(handler):
            raise NotImplementedError(
                "scr_cutscene_commands(master) must be provided to execute "
                "cutscene commands; the command-handler GML is still needed"
            )
        handler(self)

    def _evaluate_waits(self) -> None:
        """Direct translation of Step event's sequential waiting checks."""
        if self.cs_wait_amount > 0:
            self.cs_wait_timer += 1
            if self.cs_wait_timer >= self.cs_wait_amount:
                self.cs_wait_amount = 0
                self.cs_wait_timer = 0
                self.waiting = 0

        if self.cs_wait_box >= 0:
            if not self._exists(self.mydialoguer):
                self.cs_wait_box = -1
                self.waiting = 0
                self.cs_wait_box_end = False
            else:
                dialoguer = self._resolve(self.mydialoguer)
                if dialoguer.active == 1 and self._exists(dialoguer.writer):
                    writer = self._resolve(dialoguer.writer)
                    if (
                        (
                            writer.msgno == self.cs_wait_box
                            and (not self.cs_wait_box_end or writer.halt > 0)
                        )
                        or writer.msgno > self.cs_wait_box
                    ):
                        self.cs_wait_box = -1
                        self.waiting = 0
                        self.cs_wait_box_end = False

        if self.cs_wait_dialogue == 1:
            if not self._exists(self.mydialoguer):
                self.cs_wait_dialogue = 0
                self.waiting = 0

        if self.cs_wait_plat_dialogue == 1:
            sequencer_ref = getattr(
                self.game, "obj_plat_dialogue_sequencer", "obj_plat_dialogue_sequencer"
            )
            if self._exists(sequencer_ref):
                sequencer = self._resolve(sequencer_ref)
                if len(sequencer.messages) == 0:
                    self.cs_wait_plat_dialogue = 0
                    self.waiting = 0
                    self._debug_print("dialogue gone")

        if self.cs_wait_if == 1:
            exists = self._adapter("variable_instance_exists")(
                self.cs_wait_if_objectid, self.cs_wait_if_varname
            )
            passed = not exists
            if not passed:
                value = self._adapter("variable_instance_get")(
                    self.cs_wait_if_objectid, self.cs_wait_if_varname
                )
                target = self.cs_wait_if_varvalue
                op = self.cs_wait_if_operator
                if op == "=":
                    passed = value == target
                elif op == "!=":
                    passed = value != target
                elif op == ">=":
                    passed = value >= target
                elif op == "<=":
                    passed = value <= target
                elif op == ">":
                    passed = value > target
                elif op == "<":
                    passed = value < target
                else:
                    passed = True  # GML releases unknown operators.

            if passed:
                self.cs_wait_if = 0
                self.waiting = 0

    def step(self) -> None:
        """GameMaker Step event, including original command-loop pointer rules."""
        if self.initialized == 0:
            self.initialized = 1

        if self.waiting == 0:
            # GML uses an instance variable, not a local loop variable.
            self.i = self.current_command
            while self.i < self.maximum_command:
                index = self.i
                if index < 0 or index >= len(self.command):
                    raise IndexError(
                        f"Missing command[{index}]; provide "
                        "scr_cutscene_master_commands_initialize() or "
                        "populate command[] before Step"
                    )
                if len(self.command_actor) <= index:
                    self.command_actor.extend(
                        [NO_ACTOR] * (index + 1 - len(self.command_actor))
                    )
                self.command_actor[index] = self.actor_selected_id
                self._c = self.command[index]
                self._dispatch_command()
                if self.breakme == 1:
                    self.breakme = 0
                    break
                self.i += 1

        # The original assignment happens even on pre-existing wait frames.
        self.current_command = self.i + 1

        if self.waiting == 1:
            self._evaluate_waits()

        if self.terminate_this_frame == 1:
            destroy = self._adapter("instance_destroy")
            if self.kill_actors == 1:
                for jj in range(20):
                    actor = self.actor_id[jj]
                    if actor not in (NO_ACTOR, -4, None) and self._exists(actor):
                        destroy(actor)
            destroy(self)

    def draw(self) -> None:
        """The supplied Draw event is just ``exit;``."""
        return None


obj_cutscene_master = CutsceneMaster

__all__ = ["CutsceneMaster", "obj_cutscene_master"]
