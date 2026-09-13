"""Frame-based cutscene command system for the Chapter 6 fangame.

The design mirrors DELTARUNE's Chapter 5 cutscene pipeline:

* authoring helpers append commands to a dynamic command tape;
* commands run immediately until one of the wait commands blocks;
* actor movement, animation, lerps, and delayed commands remain active while
  the main tape is waiting;
* ``wait_custom`` hands control to the scene owner until ``resume_custom`` is
  called; and
* reaching the end of the tape behaves like its trailing ``terminate`` command.

The module intentionally uses duck typing.  A cutscene actor only needs ``x``
and ``y`` attributes.  Optional methods such as ``set_position``,
``set_facing``, ``set_sprite``, and ``destroy`` are used when present.  This
lets the real Player object, NPC classes, and lightweight scene props all share
the same command system.

Typical use::

    scene = CutsceneMaster(game, owner=self)
    scene.register_actor("kris", game.player)
    scene.register_actor("cage", cage)

    scene.select("cage")
    scene.shake_actor()
    scene.delay(8, "soundplay", "snd_cage_rattle")
    scene.wait(20)
    scene.select("kris")
    scene.walk_direct(160, 130, 30)
    scene.wait(30)
    scene.terminate()

Call ``scene.update()`` once per logical 30 FPS game frame.  All public builder
methods return ``self``, so command chaining is optional.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import inspect
import math
import operator
import random
from typing import Any, Callable, Hashable, Iterable, Mapping, Protocol


Number = int | float
ActorKey = Hashable
CommandHandler = Callable[["CutsceneMaster", "CutsceneCommand", Any, bool], None]


class CutsceneError(RuntimeError):
    """Raised when a cutscene command cannot be executed safely."""


class SupportsPosition(Protocol):
    x: Number
    y: Number


@dataclass(slots=True)
class CutsceneHooks:
    """Optional engine-specific callbacks.

    The cutscene master discovers common methods on ``game`` and ``game.audio``
    when a hook is omitted.  Supplying hooks is preferable when the surrounding
    engine uses different method names or signatures.
    """

    play_sound: Callable[[Any, float | None, float | None], Any] | None = None
    music: Callable[..., Any] | None = None
    start_dialogue: Callable[[list[Any], Mapping[str, Any]], Any] | None = None
    dialogue_active: Callable[[], bool] | None = None
    dialogue_box_state: Callable[[int], Any] | None = None
    shake_screen: Callable[[float, float, float], Any] | None = None
    shake_actor: Callable[[Any, float, float, int], Any] | None = None
    fade: Callable[[float, Any | None], Any] | None = None
    pan: Callable[[float, float, int], Any] | None = None
    create_instance: Callable[[float, float, Any], Any] | None = None
    on_finish: Callable[["CutsceneMaster"], Any] | None = None


_USE_SELECTED = object()
_NO_ARGUMENT = object()


@dataclass(slots=True)
class CutsceneCommand:
    """A single entry on the cutscene command tape."""

    name: str
    args: tuple[Any, ...] = ()
    actor: Any = _USE_SELECTED


class CutsceneTask:
    """Base class for nonblocking work that advances once per update."""

    done: bool = False

    def update(self, frames: float = 1.0) -> None:
        raise NotImplementedError

    def complete(self) -> None:
        """Jump the task to its final state (used by instant/skip mode)."""
        self.done = True

    def cancel(self) -> None:
        self.done = True


@dataclass(slots=True)
class MoveByTask(CutsceneTask):
    actor: Any
    dx: float
    dy: float
    frames_left: float
    on_stop: Callable[[Any], None]
    done: bool = False

    def update(self, frames: float = 1.0) -> None:
        if self.done:
            return
        step = min(max(frames, 0.0), self.frames_left)
        _set_position(
            self.actor,
            _get_attr(self.actor, "x", 0.0) + self.dx * step,
            _get_attr(self.actor, "y", 0.0) + self.dy * step,
        )
        self.frames_left -= step
        if self.frames_left <= 0:
            self.done = True
            self.on_stop(self.actor)

    def complete(self) -> None:
        if not self.done:
            self.update(self.frames_left)


@dataclass(slots=True)
class MoveToTask(CutsceneTask):
    actor: Any
    start_x: float
    start_y: float
    target_x: float
    target_y: float
    duration: float
    on_stop: Callable[[Any], None]
    elapsed: float = 0.0
    done: bool = False

    def update(self, frames: float = 1.0) -> None:
        if self.done:
            return
        self.elapsed = min(self.duration, self.elapsed + max(frames, 0.0))
        progress = 1.0 if self.duration <= 0 else self.elapsed / self.duration
        _set_position(
            self.actor,
            _lerp(self.start_x, self.target_x, progress),
            _lerp(self.start_y, self.target_y, progress),
        )
        if self.elapsed >= self.duration:
            self.done = True
            self.on_stop(self.actor)

    def complete(self) -> None:
        if not self.done:
            _set_position(self.actor, self.target_x, self.target_y)
            self.done = True
            self.on_stop(self.actor)


@dataclass(slots=True)
class LerpAttributeTask(CutsceneTask):
    target: Any
    attribute: str
    start: Number
    end: Number
    duration: float
    ease_power: float = 1.0
    ease_mode: str = "in"
    elapsed: float = 0.0
    done: bool = False

    def update(self, frames: float = 1.0) -> None:
        if self.done:
            return
        self.elapsed = min(self.duration, self.elapsed + max(frames, 0.0))
        progress = 1.0 if self.duration <= 0 else self.elapsed / self.duration
        amount = _ease(progress, self.ease_power, self.ease_mode)
        _set_attr(self.target, self.attribute, _lerp(self.start, self.end, amount))
        self.done = self.elapsed >= self.duration

    def complete(self) -> None:
        _set_attr(self.target, self.attribute, self.end)
        self.done = True


@dataclass(slots=True)
class RangeAnimationTask(CutsceneTask):
    actor: Any
    start: float
    end: float
    speed: float
    current: float = field(init=False)
    done: bool = False

    def __post_init__(self) -> None:
        self.current = self.start
        _set_image_index(self.actor, self.start)

    def update(self, frames: float = 1.0) -> None:
        if self.done:
            return
        direction = 1.0 if self.end >= self.start else -1.0
        self.current += abs(self.speed) * direction * max(frames, 0.0)
        reached = self.current >= self.end if direction > 0 else self.current <= self.end
        if reached:
            self.current = self.end
            self.done = True
        _set_image_index(self.actor, self.current)

    def complete(self) -> None:
        _set_image_index(self.actor, self.end)
        self.done = True


@dataclass(slots=True)
class ActorShakeTask(CutsceneTask):
    actor: Any
    amount_x: float = 1.0
    amount_y: float = 1.0
    duration: float = 8.0
    elapsed: float = 0.0
    base_x: float = field(init=False)
    base_y: float = field(init=False)
    done: bool = False

    def __post_init__(self) -> None:
        self.base_x = float(_get_attr(self.actor, "x", 0.0))
        self.base_y = float(_get_attr(self.actor, "y", 0.0))

    def update(self, frames: float = 1.0) -> None:
        if self.done:
            return
        self.elapsed += max(frames, 0.0)
        if self.elapsed >= self.duration:
            self.complete()
            return
        _set_position(
            self.actor,
            self.base_x + random.uniform(-self.amount_x, self.amount_x),
            self.base_y + random.uniform(-self.amount_y, self.amount_y),
        )

    def complete(self) -> None:
        _set_position(self.actor, self.base_x, self.base_y)
        self.done = True

    def cancel(self) -> None:
        self.complete()


@dataclass(slots=True)
class DelayedCommand:
    frames_left: float
    command: CutsceneCommand


@dataclass(slots=True)
class _WaitState:
    kind: str
    data: Any = None


class CutsceneMaster:
    """Builds and executes one appendable cutscene command tape."""

    _ALIASES = {
        "call": "customfunc",
        "custom_func": "customfunc",
        "image_index": "imageindex",
        "image_speed": "imagespeed",
        "sound": "soundplay",
        "sndplay": "soundplay",
        "snd_play": "soundplay",
        "sound_play": "soundplay",
        "mus": "music",
        "set_xy": "setxy",
        "add_xy": "addxy",
        "walk_direct": "walkdirect",
        "walk_to": "walkto",
        "wait_if": "waitif",
        "wait_until": "waituntil",
        "wait_custom": "waitcustom",
        "wait_dialogue": "waitdialoguer",
        "wait_talk": "waitdialoguer",
        "shake_actor": "shakeobj",
        "set_var": "var",
        "add_var": "varadd",
        "lerp_var": "lerpvar",
    }

    _OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
        "=": operator.eq,
        "==": operator.eq,
        "!=": operator.ne,
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
    }

    def __init__(
        self,
        game: Any | None = None,
        owner: Any | None = None,
        *,
        hooks: CutsceneHooks | None = None,
        strict: bool = True,
        max_commands_per_frame: int = 10_000,
        on_finish: Callable[["CutsceneMaster"], Any] | None = None,
    ) -> None:
        self.game = game
        self.owner = owner
        self.hooks = hooks or CutsceneHooks()
        self.strict = strict
        self.max_commands_per_frame = max(1, int(max_commands_per_frame))
        self.on_finish = on_finish

        self.commands: list[CutsceneCommand] = []
        self.current_command = 0
        self.actors: dict[ActorKey, Any] = {}
        self.actor_names: dict[ActorKey, str] = {}
        self.temporary_actors: set[ActorKey] = set()
        self.selected_actor_key: ActorKey | None = None

        self.tasks: list[CutsceneTask] = []
        self.delayed_commands: list[DelayedCommand] = []
        self._wait: _WaitState | None = None
        self._custom_handlers: dict[str, CommandHandler] = {}
        self._dialogue_messages: list[Any] = []
        self._dialogue_session: Any | None = None
        self._message_options: dict[str, Any] = {
            "speaker": "normal",
            "side": "any",
            "stay": 0,
            "runcheck": False,
            "prevent_skip": False,
        }

        self.started = False
        self.finished = False
        self.killed_actors = False
        self.instant = False

        if game is not None and getattr(game, "cutscene", None) in (None, self):
            game.cutscene = self

    # ------------------------------------------------------------------
    # Actor registration and command authoring
    # ------------------------------------------------------------------
    @property
    def waiting(self) -> bool:
        return self._wait is not None

    @property
    def selected_actor(self) -> Any | None:
        if self.selected_actor_key is None:
            return None
        return self.actors.get(self.selected_actor_key)

    @property
    def remaining_commands(self) -> int:
        return max(0, len(self.commands) - self.current_command)

    def register_actor(
        self,
        key: ActorKey,
        actor: Any,
        name: str | None = None,
        *,
        temporary: bool = False,
    ) -> Any:
        if key in self.actors and self.actors[key] is not actor:
            raise CutsceneError(f"Actor key {key!r} is already registered")
        self.actors[key] = actor
        self.actor_names[key] = name or str(key)
        if temporary:
            self.temporary_actors.add(key)
        return actor

    add_actor = register_actor

    def unregister_actor(self, key: ActorKey) -> Any | None:
        self.actor_names.pop(key, None)
        self.temporary_actors.discard(key)
        if self.selected_actor_key == key:
            self.selected_actor_key = None
        return self.actors.pop(key, None)

    def register_command(self, name: str, handler: CommandHandler) -> None:
        self._custom_handlers[self._normalize_name(name)] = handler

    def command(self, name: str, *args: Any, actor: Any = _USE_SELECTED) -> "CutsceneMaster":
        if self.finished:
            raise CutsceneError("Cannot append commands to a finished cutscene")
        self.commands.append(CutsceneCommand(self._normalize_name(name), tuple(args), actor))
        return self

    def extend(self, commands: Iterable[CutsceneCommand]) -> "CutsceneMaster":
        for item in commands:
            self.command(item.name, *item.args, actor=item.actor)
        return self

    def select(self, actor: ActorKey) -> "CutsceneMaster":
        return self.command("select", actor)

    sel = select

    def wait(self, frames: Number) -> "CutsceneMaster":
        return self.command("wait", frames)

    def wait_if(self, target: Any, attribute: str, op: str, value: Any) -> "CutsceneMaster":
        return self.command("waitif", target, attribute, op, value)

    def wait_until(self, predicate: Callable[[], bool]) -> "CutsceneMaster":
        return self.command("waituntil", predicate)

    def wait_custom(self) -> "CutsceneMaster":
        return self.command("waitcustom")

    def wait_dialogue(self) -> "CutsceneMaster":
        return self.command("waitdialoguer")

    wait_talk = wait_dialogue

    def wait_box(self, state: int, *, end: bool = False) -> "CutsceneMaster":
        return self.command("waitboxend" if end else "waitbox", state)

    def delay(self, frames: Number, command: str, *args: Any) -> "CutsceneMaster":
        return self.command("delaycmd", frames, command, *args)

    delay_command = delay

    def call(self, function: Callable[..., Any], argument: Any = _NO_ARGUMENT) -> "CutsceneMaster":
        return self.command("customfunc", function, argument)

    custom_func = call

    def set_xy(self, x: Number, y: Number) -> "CutsceneMaster":
        return self.command("setxy", x, y)

    def add_xy(self, x: Number, y: Number) -> "CutsceneMaster":
        return self.command("addxy", x, y)

    def visible(self, value: bool) -> "CutsceneMaster":
        return self.command("visible", value)

    def facing(self, direction: Any) -> "CutsceneMaster":
        return self.command("facing", direction)

    def walk(self, direction: str, speed: Number, frames: Number) -> "CutsceneMaster":
        return self.command("walk", direction, speed, frames)

    def walk_direct(
        self,
        x: Number,
        y: Number,
        duration_or_negative_speed: Number,
        *,
        wait_for_completion: bool = False,
    ) -> "CutsceneMaster":
        return self.command(
            "walkdirect", x, y, duration_or_negative_speed, wait_for_completion
        )

    def walk_to(
        self,
        target: Any,
        x_offset: Number,
        y_offset: Number,
        duration_or_negative_speed: Number,
        *,
        match_origins: bool = False,
        actor_origin: bool = False,
    ) -> "CutsceneMaster":
        return self.command(
            "walkto",
            target,
            x_offset,
            y_offset,
            duration_or_negative_speed,
            match_origins,
            actor_origin,
        )

    def sprite(self, value: Any) -> "CutsceneMaster":
        return self.command("sprite", value)

    def image_index(self, value: Number) -> "CutsceneMaster":
        return self.command("imageindex", value)

    def image_speed(self, value: Number) -> "CutsceneMaster":
        return self.command("imagespeed", value)

    def animate(self, start: Number, end: Number, speed: Number) -> "CutsceneMaster":
        return self.command("animate", start, end, speed)

    def auto_walk(self, value: bool) -> "CutsceneMaster":
        return self.command("autowalk", value)

    def auto_facing(self, value: bool) -> "CutsceneMaster":
        return self.command("autofacing", value)

    def auto_depth(self, value: bool) -> "CutsceneMaster":
        return self.command("autodepth", value)

    def depth(self, value: Number) -> "CutsceneMaster":
        return self.command("depth", value)

    def set_var(self, target: Any, attribute: str, value: Any) -> "CutsceneMaster":
        return self.command("var", target, attribute, value)

    def add_var(self, target: Any, attribute: str, amount: Number) -> "CutsceneMaster":
        return self.command("varadd", target, attribute, amount)

    def lerp_var(
        self,
        target: Any,
        attribute: str,
        start: Number | None,
        end: Number,
        duration: Number,
        ease_power: Number = 1,
        ease_mode: str = "in",
    ) -> "CutsceneMaster":
        return self.command(
            "lerpvar", target, attribute, start, end, duration, ease_power, ease_mode
        )

    def sound(self, sound: Any, volume: float | None = None, pitch: float | None = None) -> "CutsceneMaster":
        return self.command("soundplay", sound, volume, pitch)

    play_sound = sound

    def music(self, action: str, *args: Any) -> "CutsceneMaster":
        return self.command("music", action, *args)

    def shake(self, x: Number = 1, y: Number = 1, speed: Number = 1) -> "CutsceneMaster":
        return self.command("shakex", x, y, speed)

    def shake_actor(
        self, x: Number = 1, y: Number = 1, duration: int = 8
    ) -> "CutsceneMaster":
        return self.command("shakeobj", x, y, duration)

    def shake_target(
        self, target: Any, x: Number = 1, y: Number = 1, duration: int = 8
    ) -> "CutsceneMaster":
        return self.command("shaketarget", target, x, y, duration)

    def fade(self, frames: Number, color: Any | None = None) -> "CutsceneMaster":
        return self.command("fadeout", frames, color)

    def pan(self, x: Number, y: Number, frames: Number) -> "CutsceneMaster":
        return self.command("pan", x, y, frames)

    def speaker(self, name: str) -> "CutsceneMaster":
        return self.command("speaker", name)

    def message_set(self, text: Any, index: int = 0) -> "CutsceneMaster":
        return self.command("msgset", index, text)

    msgset = message_set

    def message_next(self, text: Any) -> "CutsceneMaster":
        return self.command("msgnext", text)

    msgnext = message_next

    def message_side(self, side: str) -> "CutsceneMaster":
        return self.command("msgside", side)

    def message_stay(self, value: Any) -> "CutsceneMaster":
        return self.command("msgstay", value)

    def talk(self, *, wait: bool = False) -> "CutsceneMaster":
        self.command("talk")
        return self.wait_dialogue() if wait else self

    def talk_wait(self) -> "CutsceneMaster":
        return self.talk(wait=True)

    def terminate(self, *, kill_actors: bool = False) -> "CutsceneMaster":
        return self.command("terminatekillactors" if kill_actors else "terminate")

    # ------------------------------------------------------------------
    # Runtime
    # ------------------------------------------------------------------
    def update(self, frames: Number = 1) -> bool:
        """Advance tasks and the command tape; return ``True`` while active."""
        if self.finished:
            return False
        if frames < 0:
            raise ValueError("frames must be non-negative")
        self.started = True

        self._update_tasks(float(frames))
        self._update_delayed(float(frames))

        if self._wait is not None and not self._update_wait(float(frames)):
            return True

        commands_run = 0
        while self._wait is None and not self.finished:
            if self.current_command >= len(self.commands):
                self._finish()
                break
            if commands_run >= self.max_commands_per_frame:
                raise CutsceneError(
                    "Cutscene exceeded max_commands_per_frame without waiting"
                )

            command = self.commands[self.current_command]
            self.current_command += 1
            commands_run += 1
            self._execute(command, instant=self.instant)

        return not self.finished

    def run_until_blocked(self) -> bool:
        """Execute the immediate portion of the tape without advancing time."""
        return self.update(0)

    def resume_custom(self) -> None:
        if self._wait is None or self._wait.kind != "custom":
            if self.strict:
                raise CutsceneError("Cutscene is not waiting on wait_custom")
            return
        self._wait = None

    waitcustom_end = resume_custom

    def skip(self) -> None:
        """Complete time-based work and interpret the rest in instant mode.

        Sound, dialogue, shake, animation playback, fades, and pans are skipped;
        final positions and variable values are retained.  A custom wait remains
        a deliberate owner-controlled boundary.
        """
        if self.finished:
            return
        for task in self.tasks:
            task.complete()
        self.tasks.clear()
        delayed = tuple(self.delayed_commands)
        self.delayed_commands.clear()
        for item in delayed:
            self._execute(item.command, instant=True, detached=True)
        if self._wait is not None and self._wait.kind != "custom":
            self._wait = None
        self.instant = True
        self.update(0)

    def cancel(self, *, kill_actors: bool = False) -> None:
        if self.finished:
            return
        for task in self.tasks:
            task.cancel()
        self.tasks.clear()
        self.delayed_commands.clear()
        self._wait = None
        self.killed_actors = kill_actors
        if kill_actors:
            self._destroy_temporary_actors()
        self._finish()

    def _execute(self, command: CutsceneCommand, *, instant: bool, detached: bool = False) -> None:
        name = self._normalize_name(command.name)
        args = command.args
        actor = self._command_actor(command)

        custom = self._custom_handlers.get(name)
        if custom is not None:
            custom(self, command, actor, instant)
            return

        if name == "select":
            key = args[0]
            if key not in self.actors:
                self._error(f"Unknown cutscene actor {key!r}")
                return
            self.selected_actor_key = key
            return

        if name == "delaycmd":
            delay, nested_name, *nested_args = args
            nested = CutsceneCommand(
                self._normalize_name(str(nested_name)), tuple(nested_args), actor
            )
            if instant:
                self._execute(nested, instant=True, detached=True)
            else:
                self.delayed_commands.append(DelayedCommand(float(delay), nested))
            return

        if name in {"wait", "waitif", "waituntil", "waitcustom", "waitdialoguer", "waitbox", "waitboxend"}:
            if detached:
                return
            self._begin_wait(name, args, instant)
            return

        if name in {"terminate", "terminatekillactors"}:
            if name == "terminatekillactors":
                self.killed_actors = True
                self._destroy_temporary_actors()
            self._finish()
            return

        if name == "customfunc":
            function = args[0]
            argument = args[1] if len(args) > 1 else _NO_ARGUMENT
            if not callable(function):
                self._error("customfunc requires a callable")
            elif argument is _NO_ARGUMENT:
                function()
            else:
                function(argument)
            return

        if name == "setxy":
            self._require_actor(actor, name)
            _set_position(actor, args[0], args[1])
        elif name == "addxy":
            self._require_actor(actor, name)
            _set_position(actor, _get_attr(actor, "x", 0) + args[0], _get_attr(actor, "y", 0) + args[1])
        elif name == "visible":
            self._require_actor(actor, name)
            _set_attr(actor, "visible", bool(args[0]))
        elif name == "facing":
            self._require_actor(actor, name)
            _set_facing(actor, args[0])
        elif name == "walk":
            self._execute_walk(actor, args, instant)
        elif name == "walkdirect":
            self._execute_walk_direct(actor, args, instant, detached)
        elif name == "walkto":
            self._execute_walk_to(actor, args, instant, detached)
        elif name == "sprite":
            self._require_actor(actor, name)
            _set_sprite(actor, args[0])
        elif name == "specialsprite":
            self._require_actor(actor, name)
            _set_sprite(actor, _get_attr(actor, "specialsprite")[args[0]])
            _set_attr(actor, "specialspriteno", args[0])
        elif name == "imageindex":
            self._require_actor(actor, name)
            _set_image_index(actor, args[0])
        elif name == "imagespeed":
            self._require_actor(actor, name)
            _set_attr(actor, "image_speed", args[0])
        elif name == "animate":
            self._execute_animate(actor, args, instant)
        elif name in {"autowalk", "autofacing", "autodepth", "depth", "spin"}:
            self._execute_actor_property(name, actor, args[0])
        elif name == "depthobject":
            self._require_actor(actor, name)
            target = self._resolve_target(args[0])
            _set_attr(actor, "depth", _get_attr(target, "depth", 0) + args[1])
        elif name == "var":
            target = self._resolve_target(args[0], actor)
            _set_attr(target, args[1], args[2])
        elif name == "varadd":
            target = self._resolve_target(args[0], actor)
            _set_attr(target, args[1], _get_attr(target, args[1], 0) + args[2])
        elif name == "lerpvar":
            self._execute_lerp(args, actor, instant)
        elif name == "globalvar":
            target = getattr(self.game, "globals", self.game)
            if target is None:
                self._error("globalvar requires game or game.globals")
            else:
                _set_attr(target, args[0], args[1])
        elif name == "soundplay":
            if not instant:
                self._play_sound(*_pad(args, 3, None))
        elif name == "music":
            if not instant:
                self._music(*args)
        elif name in {"shake", "shakex"}:
            if not instant:
                values = _pad(args, 3, 1)
                self._shake_screen(float(values[0]), float(values[1]), float(values[2]))
        elif name == "shakeobj":
            if not instant:
                values = _pad(args, 3, 1)
                self._shake_actor(actor, float(values[0]), float(values[1]), int(values[2]))
        elif name == "shaketarget":
            if not instant:
                values = _pad(args[1:], 3, 1)
                self._shake_actor(self._resolve_target(args[0]), float(values[0]), float(values[1]), int(values[2]))
        elif name == "fadeout":
            if not instant:
                self._fade(args[0], args[1] if len(args) > 1 else None)
        elif name in {"pan", "panspeed"}:
            if not instant:
                self._pan(args[0], args[1], int(args[2]))
        elif name == "speaker":
            self._message_options["speaker"] = args[0]
        elif name == "msgside":
            self._message_options["side"] = args[0]
        elif name == "msgstay":
            self._message_options["stay"] = args[0]
        elif name == "msgruncheck":
            self._message_options["runcheck"] = bool(args[0])
        elif name == "msgpreventcskip":
            self._message_options["prevent_skip"] = bool(args[0])
        elif name == "msgset":
            self._message_set(args)
        elif name == "msgnext":
            self._dialogue_messages.append(args[0])
        elif name == "talk":
            if not instant:
                self._talk()
        elif name == "instancecreate":
            created = self._create_instance(args[0], args[1], args[2])
            if self.owner is not None:
                setattr(self.owner, "cutscene_instance", created)
        elif name in {"actortokris", "actortocaterpillar", "actortoparty", "actortocaterpillarstill"}:
            self._transfer_actors(name)
        elif name == "actortoobject":
            self._require_actor(actor, name)
            self._create_instance(_get_attr(actor, "x", 0), _get_attr(actor, "y", 0), args[0])
            _set_attr(actor, "visible", False)
        elif name == "debugprint":
            print(args[0])
        else:
            self._error(f"Unsupported cutscene command {name!r}")

    def _begin_wait(self, name: str, args: tuple[Any, ...], instant: bool) -> None:
        if name == "wait":
            if instant:
                return
            self._wait = _WaitState("frames", max(0.0, float(args[0])))
        elif name == "waitif":
            if instant:
                return
            target, attribute, op, value = args
            self._wait = _WaitState("if", (target, attribute, op, value))
        elif name == "waituntil":
            if instant:
                return
            self._wait = _WaitState("until", args[0])
        elif name == "waitcustom":
            self._wait = _WaitState("custom")
            if self.owner is not None:
                setattr(self.owner, "customcon", 1)
        elif name == "waitdialoguer":
            if not instant:
                self._wait = _WaitState("dialogue")
        elif name in {"waitbox", "waitboxend"}:
            if not instant:
                self._wait = _WaitState("box", (int(args[0]), name == "waitboxend"))

    def _update_wait(self, frames: float) -> bool:
        wait = self._wait
        if wait is None:
            return True
        complete = False
        if wait.kind == "frames":
            wait.data -= frames
            complete = wait.data <= 0
        elif wait.kind == "if":
            target_ref, attribute, op, value = wait.data
            target = self._resolve_target(target_ref)
            attr = "visible" if attribute == "visi" else attribute
            current = _get_attr(target, attr)
            compare = self._OPERATORS.get(op)
            if compare is None:
                raise CutsceneError(f"Unsupported wait_if operator {op!r}")
            complete = compare(current, value)
        elif wait.kind == "until":
            complete = bool(wait.data())
        elif wait.kind == "dialogue":
            complete = not self._dialogue_active()
        elif wait.kind == "box":
            desired, wait_for_end = wait.data
            state = self._dialogue_box_state(desired)
            complete = bool(state) if not wait_for_end else not bool(state)
        elif wait.kind == "custom":
            complete = False
        if complete:
            self._wait = None
        return complete

    def _update_tasks(self, frames: float) -> None:
        for task in tuple(self.tasks):
            task.update(frames)
        self.tasks[:] = [task for task in self.tasks if not task.done]

    def _update_delayed(self, frames: float) -> None:
        due: list[DelayedCommand] = []
        pending: list[DelayedCommand] = []
        for delayed in self.delayed_commands:
            delayed.frames_left -= frames
            (due if delayed.frames_left <= 0 else pending).append(delayed)
        self.delayed_commands = pending
        for delayed in due:
            self._execute(delayed.command, instant=self.instant, detached=True)

    def _execute_walk(self, actor: Any, args: tuple[Any, ...], instant: bool) -> None:
        self._require_actor(actor, "walk")
        direction, speed, frames = args[:3]
        direction = str(direction).lower()[0]
        vectors = {"l": (-1, 0), "d": (0, 1), "r": (1, 0), "u": (0, -1)}
        if direction not in vectors:
            raise CutsceneError(f"Unknown walk direction {direction!r}")
        _set_facing(actor, direction)
        dx, dy = vectors[direction]
        if instant:
            _set_position(
                actor,
                _get_attr(actor, "x", 0) + dx * speed * frames,
                _get_attr(actor, "y", 0) + dy * speed * frames,
            )
            return
        self._start_walking(actor)
        self.tasks.append(MoveByTask(actor, dx * float(speed), dy * float(speed), max(0.0, float(frames)), self._stop_walking))

    def _execute_walk_direct(self, actor: Any, args: tuple[Any, ...], instant: bool, detached: bool) -> None:
        self._require_actor(actor, "walkdirect")
        x, y, duration_or_speed = args[:3]
        wait_for_completion = bool(args[3]) if len(args) > 3 else False
        start_x = float(_get_attr(actor, "x", 0))
        start_y = float(_get_attr(actor, "y", 0))
        target_x = start_x if x == 0 else float(x)
        target_y = start_y if y == 0 else float(y)
        if instant:
            _set_position(actor, target_x, target_y)
            return
        duration = float(duration_or_speed)
        if duration < 0:
            speed = -duration
            if speed <= 0:
                raise CutsceneError("Negative walk_direct speed must be non-zero")
            duration = max(1.0, round(math.dist((start_x, start_y), (target_x, target_y)) / speed))
        duration = max(1.0, duration)
        self._auto_face_movement(actor, target_x - start_x, target_y - start_y)
        self._start_walking(actor)
        task = MoveToTask(actor, start_x, start_y, target_x, target_y, duration, self._stop_walking)
        self.tasks.append(task)
        if wait_for_completion and not detached:
            self._wait = _WaitState("until", lambda task=task: task.done)

    def _execute_walk_to(self, actor: Any, args: tuple[Any, ...], instant: bool, detached: bool) -> None:
        self._require_actor(actor, "walkto")
        target = self._resolve_target(args[0])
        x = float(_get_attr(target, "x", 0)) + float(args[1])
        y = float(_get_attr(target, "y", 0)) + float(args[2])
        duration = args[3]
        match_origins = bool(args[4]) if len(args) > 4 else False
        actor_origin = bool(args[5]) if len(args) > 5 else False
        if match_origins:
            x += _origin_center_x(actor) - _origin_center_x(target)
            y += _origin_bottom_y(target) - _origin_bottom_y(actor)
        elif actor_origin:
            x -= _origin_center_x(actor)
            y -= _origin_bottom_y(actor)
        self._execute_walk_direct(actor, (x, y, duration, False), instant, detached)

    def _execute_animate(self, actor: Any, args: tuple[Any, ...], instant: bool) -> None:
        self._require_actor(actor, "animate")
        start, end, speed = map(float, args[:3])
        if instant:
            _set_image_index(actor, end)
            return
        method = getattr(actor, "animate_range", None)
        if callable(method):
            method(start, end, speed)
        else:
            self.tasks.append(RangeAnimationTask(actor, start, end, speed))

    def _execute_lerp(self, args: tuple[Any, ...], actor: Any, instant: bool) -> None:
        target = self._resolve_target(args[0], actor)
        attribute = str(args[1])
        start = _get_attr(target, attribute) if args[2] is None else args[2]
        end, duration = args[3], float(args[4])
        power = float(args[5]) if len(args) > 5 else 1.0
        mode = str(args[6]) if len(args) > 6 else "in"
        if instant:
            _set_attr(target, attribute, end)
        else:
            self.tasks.append(LerpAttributeTask(target, attribute, start, end, max(1.0, duration), power, mode))

    def _execute_actor_property(self, name: str, actor: Any, value: Any) -> None:
        self._require_actor(actor, name)
        attributes = {
            "autowalk": ("auto_walk", "auto_facing"),
            "autofacing": ("auto_facing",),
            "autodepth": ("auto_depth",),
            "depth": ("depth",),
            "spin": ("spin_speed",),
        }
        for attribute in attributes[name]:
            _set_attr(actor, attribute, value)

    def _auto_face_movement(self, actor: Any, dx: float, dy: float) -> None:
        if not bool(_get_attr(actor, "auto_facing", True)) or (dx == 0 and dy == 0):
            return
        direction = "r" if dx > 0 else "l"
        if abs(dy) > abs(dx):
            direction = "d" if dy > 0 else "u"
        _set_facing(actor, direction)

    def _start_walking(self, actor: Any) -> None:
        _set_attr(actor, "is_moving", True)
        method = _first_callable(actor, "start_walking", "start_moving")
        if method is not None:
            _invoke_compatible(method, [(), (True,)])

    def _stop_walking(self, actor: Any) -> None:
        _set_attr(actor, "is_moving", False)
        method = _first_callable(actor, "stop_walking", "stop_moving", "halt")
        if method is not None:
            _invoke_compatible(method, [(), (False,)])
        if hasattr(actor, "image_index"):
            _set_image_index(actor, 0)
        if hasattr(actor, "image_speed"):
            _set_attr(actor, "image_speed", 0)

    def _command_actor(self, command: CutsceneCommand) -> Any | None:
        if command.actor is not _USE_SELECTED:
            return command.actor
        return self.selected_actor

    def _resolve_target(self, reference: Any, default: Any = None) -> Any:
        if reference in (None, 0, _USE_SELECTED):
            if default is not None:
                return default
            actor = self.selected_actor
            if actor is not None:
                return actor
        try:
            if reference in self.actors:
                return self.actors[reference]
        except TypeError:
            pass
        if reference is None:
            self._error("A cutscene target is required")
        return reference

    def _require_actor(self, actor: Any, command: str) -> None:
        if actor is None:
            raise CutsceneError(f"{command} requires a selected actor")

    def _message_set(self, args: tuple[Any, ...]) -> None:
        if len(args) == 1:
            index, text = 0, args[0]
        else:
            index, text = int(args[0]), args[1]
        while len(self._dialogue_messages) <= index:
            self._dialogue_messages.append("")
        self._dialogue_messages[index] = text
        del self._dialogue_messages[index + 1 :]

    def _talk(self) -> None:
        messages = list(self._dialogue_messages)
        options = dict(self._message_options)
        if self.hooks.start_dialogue is not None:
            self._dialogue_session = self.hooks.start_dialogue(messages, options)
            return
        method = _first_callable(self.game, "start_dialogue", "show_dialogue", "begin_dialogue")
        if method is None:
            dialogue = _first_attr(self.game, "dialogue_box", "dialogue", "dialoguer")
            method = _first_callable(dialogue, "start", "show", "begin")
        if method is None:
            self._error("talk requires hooks.start_dialogue or a game dialogue method")
            return
        self._dialogue_session = _invoke_compatible(
            method,
            [
                (messages, options),
                (messages,),
                (messages[0] if len(messages) == 1 else messages,),
            ],
        )

    def _dialogue_active(self) -> bool:
        if self.hooks.dialogue_active is not None:
            return bool(self.hooks.dialogue_active())
        candidates = [
            self._dialogue_session,
            _first_attr(self.game, "dialogue_box", "dialogue", "dialoguer"),
        ]
        for candidate in candidates:
            if candidate is None:
                continue
            method = _first_callable(candidate, "is_active", "is_open", "active")
            if method is not None:
                return bool(method())
            for attribute in ("finished", "done", "closed"):
                if hasattr(candidate, attribute):
                    return not bool(getattr(candidate, attribute))
            for attribute in ("active", "open", "visible", "is_typing"):
                if hasattr(candidate, attribute):
                    return bool(getattr(candidate, attribute))
        return False

    def _dialogue_box_state(self, index: int) -> Any:
        if self.hooks.dialogue_box_state is not None:
            return self.hooks.dialogue_box_state(index)
        dialogue = _first_attr(self.game, "dialogue_box", "dialogue", "dialoguer")
        if dialogue is None:
            return False
        method = _first_callable(dialogue, "box_state", "is_box_state")
        if method is not None:
            return method(index)
        current = _first_attr(dialogue, "box_index", "state", "current_state")
        return current == index

    def _play_sound(self, sound: Any, volume: float | None, pitch: float | None) -> Any:
        if self.hooks.play_sound is not None:
            return self.hooks.play_sound(sound, volume, pitch)
        audio = _first_attr(self.game, "audio", "audio_manager") or self.game
        method = _first_callable(audio, "play_sound", "play_sfx", "play")
        if method is None:
            self._error("soundplay requires hooks.play_sound or an audio manager")
            return None
        result = _invoke_compatible(method, [(sound, volume, pitch), (sound, volume), (sound,)])
        if result is not None:
            if volume is not None:
                volume_method = _first_callable(result, "set_volume")
                if volume_method is not None:
                    volume_method(volume)
            if pitch is not None:
                pitch_method = _first_callable(result, "set_pitch")
                if pitch_method is not None:
                    pitch_method(pitch)
        return result

    def _music(self, action: str, *args: Any) -> Any:
        if self.hooks.music is not None:
            return self.hooks.music(action, *args)
        audio = _first_attr(self.game, "audio", "audio_manager") or self.game
        action = str(action).lower()
        if action in {"init", "initplay", "initloop", "play", "loop"}:
            method = _first_callable(audio, "play_music", "start_music")
            if method is not None:
                track = args[0] if args else None
                loop = action in {"initloop", "loop"}
                return _invoke_compatible(method, [(track, loop), (track, -1 if loop else 0), (track,)])
        elif action == "stop":
            method = _first_callable(audio, "stop_music", "stop")
            if method is not None:
                return method()
        elif action in {"pause", "resume"}:
            method = _first_callable(audio, f"{action}_music", action)
            if method is not None:
                return method()
        elif action in {"volume", "pitch"}:
            method = _first_callable(audio, f"set_music_{action}", f"music_{action}")
            if method is not None:
                return method(*args)
        self._error(f"No music adapter for action {action!r}")
        return None

    def _shake_screen(self, x: float, y: float, speed: float) -> None:
        if self.hooks.shake_screen is not None:
            self.hooks.shake_screen(x, y, speed)
            return
        method = _first_callable(self.game, "shake_screen", "screen_shake")
        if method is not None:
            _invoke_compatible(method, [(x, y, speed), (max(x, y),), ()])
        else:
            self._error("shake requires hooks.shake_screen or game.shake_screen")

    def _shake_actor(self, actor: Any, x: float, y: float, duration: int) -> None:
        self._require_actor(actor, "shakeobj")
        if self.hooks.shake_actor is not None:
            self.hooks.shake_actor(actor, x, y, duration)
            return
        method = _first_callable(actor, "shake", "start_shake")
        if method is not None:
            _invoke_compatible(method, [(x, y, duration), (max(x, y), duration), ()])
        else:
            self.tasks.append(ActorShakeTask(actor, x, y, duration))

    def _fade(self, frames: Number, color: Any | None) -> None:
        if self.hooks.fade is not None:
            self.hooks.fade(float(frames), color)
            return
        method = _first_callable(self.game, "fade", "fade_out" if frames >= 0 else "fade_in")
        if method is not None:
            _invoke_compatible(method, [(abs(frames), color), (abs(frames),), ()])
        else:
            self._error("fadeout requires hooks.fade or a game fade method")

    def _pan(self, x: Number, y: Number, frames: int) -> None:
        if self.hooks.pan is not None:
            self.hooks.pan(float(x), float(y), frames)
            return
        camera = _first_attr(self.game, "camera") or self.game
        method = _first_callable(camera, "pan", "pan_to", "move_to")
        if method is not None:
            _invoke_compatible(method, [(x, y, frames), ((x, y), frames), (x, y)])
        else:
            self._error("pan requires hooks.pan or a camera pan method")

    def _create_instance(self, x: Number, y: Number, kind: Any) -> Any:
        if self.hooks.create_instance is not None:
            return self.hooks.create_instance(float(x), float(y), kind)
        method = _first_callable(self.game, "create_instance", "spawn", "create_actor")
        if method is not None:
            return _invoke_compatible(method, [(x, y, kind), (kind, x, y), (kind, (x, y))])
        self._error("instancecreate requires hooks.create_instance or game.spawn")
        return None

    def _transfer_actors(self, command: str) -> None:
        method_names = {
            "actortokris": ("actor_to_kris", "restore_player_from_cutscene"),
            "actortocaterpillar": ("actors_to_party", "restore_party_from_cutscene"),
            "actortocaterpillarstill": ("actors_to_party_still", "restore_party_from_cutscene"),
            "actortoparty": ("actors_to_party", "restore_party_from_cutscene"),
        }
        method = _first_callable(self.owner, *method_names[command]) or _first_callable(self.game, *method_names[command])
        if method is not None:
            method(self)
            return
        # The Python engine normally registers the real player/party objects, so
        # no transfer is necessary unless a scene deliberately used stand-ins.

    def _destroy_temporary_actors(self) -> None:
        for key in tuple(self.temporary_actors):
            actor = self.actors.get(key)
            if actor is None:
                continue
            method = _first_callable(actor, "destroy", "delete", "remove")
            if method is not None:
                method()
            else:
                _set_attr(actor, "visible", False)
            self.unregister_actor(key)

    def _finish(self) -> None:
        if self.finished:
            return
        self.finished = True
        self._wait = None
        for task in self.tasks:
            task.cancel()
        self.tasks.clear()
        self.delayed_commands.clear()
        if self.game is not None and getattr(self.game, "cutscene", None) is self:
            self.game.cutscene = None
        if self.hooks.on_finish is not None:
            self.hooks.on_finish(self)
        if self.on_finish is not None:
            self.on_finish(self)

    def _normalize_name(self, name: str) -> str:
        normalized = str(name).strip().lower().replace("-", "_")
        return self._ALIASES.get(normalized, normalized)

    def _error(self, message: str) -> None:
        if self.strict:
            raise CutsceneError(message)


def _get_attr(target: Any, name: str, default: Any = _NO_ARGUMENT) -> Any:
    if isinstance(target, Mapping):
        if default is _NO_ARGUMENT:
            return target[name]
        return target.get(name, default)
    if default is _NO_ARGUMENT:
        return getattr(target, name)
    return getattr(target, name, default)


def _set_attr(target: Any, name: str, value: Any) -> None:
    if target is None:
        raise CutsceneError(f"Cannot set {name!r} on None")
    if isinstance(target, dict):
        target[name] = value
    else:
        setattr(target, name, value)


def _set_position(actor: Any, x: Number, y: Number) -> None:
    method = _first_callable(actor, "set_position", "set_xy")
    if method is not None:
        _invoke_compatible(method, [(x, y), ((x, y),)])
    else:
        _set_attr(actor, "x", x)
        _set_attr(actor, "y", y)


def _set_facing(actor: Any, direction: Any) -> None:
    # Keep a conventional attribute available even when the actor's setter also
    # performs sprite selection.
    try:
        _set_attr(actor, "facing", direction)
    except (AttributeError, TypeError):
        pass
    method = _first_callable(actor, "set_facing", "face")
    if method is not None:
        _invoke_compatible(method, [(direction,), ()])


def _set_sprite(actor: Any, sprite: Any) -> None:
    method = _first_callable(actor, "set_sprite")
    if method is not None:
        method(sprite)
    elif hasattr(actor, "sprite_index"):
        _set_attr(actor, "sprite_index", sprite)
    else:
        _set_attr(actor, "sprite", sprite)


def _set_image_index(actor: Any, index: Number) -> None:
    method = _first_callable(actor, "set_image_index", "set_frame")
    if method is not None:
        method(index)
    elif hasattr(actor, "image_index"):
        _set_attr(actor, "image_index", index)
    else:
        _set_attr(actor, "frame", index)


def _first_attr(target: Any, *names: str) -> Any | None:
    if target is None:
        return None
    for name in names:
        if hasattr(target, name):
            return getattr(target, name)
    return None


def _first_callable(target: Any, *names: str) -> Callable[..., Any] | None:
    value = _first_attr(target, *names)
    return value if callable(value) else None


def _invoke_compatible(function: Callable[..., Any], variants: list[tuple[Any, ...]]) -> Any:
    """Call the first argument tuple compatible with a callable's signature."""
    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        return function(*variants[0])
    for args in variants:
        try:
            signature.bind(*args)
        except TypeError:
            continue
        return function(*args)
    raise CutsceneError(f"No compatible call signature for {function!r}")


def _pad(values: tuple[Any, ...], size: int, fill: Any) -> tuple[Any, ...]:
    return values[:size] + (fill,) * max(0, size - len(values))


def _lerp(start: Number, end: Number, amount: float) -> Number:
    return start + (end - start) * amount


def _ease(amount: float, power: float, mode: str) -> float:
    amount = min(1.0, max(0.0, amount))
    power = max(0.0001, abs(power))
    mode = mode.lower().replace("-", "")
    if mode == "out":
        return 1.0 - (1.0 - amount) ** power
    if mode in {"inout", "outin"}:
        if amount < 0.5:
            return 0.5 * (2.0 * amount) ** power
        return 1.0 - 0.5 * (2.0 * (1.0 - amount)) ** power
    return amount**power


def _origin_center_x(actor: Any) -> float:
    width = float(_get_attr(actor, "sprite_width", 0))
    offset = float(_get_attr(actor, "sprite_xoffset", 0))
    return width / 2.0 - offset


def _origin_bottom_y(actor: Any) -> float:
    height = float(_get_attr(actor, "sprite_height", 0))
    offset = float(_get_attr(actor, "sprite_yoffset", 0))
    return height - offset


__all__ = [
    "ActorShakeTask",
    "CutsceneCommand",
    "CutsceneError",
    "CutsceneHooks",
    "CutsceneMaster",
    "CutsceneTask",
    "DelayedCommand",
    "LerpAttributeTask",
    "MoveByTask",
    "MoveToTask",
    "RangeAnimationTask",
]
