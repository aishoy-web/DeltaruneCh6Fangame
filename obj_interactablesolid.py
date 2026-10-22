"""GML-derived obj_interactablesolid for the Chapter 6 Python fangame.

GameMaker parent: obj_solidblock (not obj_interactable).
Events supplied: Create, Step, Other/User 0.

`obj_solidblock` is an eventless base class. `scr_depth` is an engine
adapter: the original child Create event calls it, but no implementation is
assumed here. The child Create event does not call event_inherited().
"""
from __future__ import annotations

from typing import Any, Callable

from obj_readable_room1 import SPR_INTERACTABLE
from obj_solidblock import SolidBlock


_MISSING = object()
DEFAULT_DIALOGUE = "* Can you see me...?/%"
DEFAULT_DIALOGUE_KEY = "obj_interactablesolid_slash_Other_10_gml_2_0"


def interactablesolid_user_event_0(instance: Any) -> Any:
    """Port obj_interactablesolid User Event 0 against any compatible instance.

    A present `on_interact` callback completely replaces the placeholder
    dialogue path, without changing `myinteract` further. The caller normally
    invokes `scr_interact(instance)` first to set `myinteract = 1`.
    """
    callback = getattr(instance, "on_interact", _MISSING)
    if callback is not _MISSING:
        return callback()

    game = instance.game
    state = getattr(game, "global_state", None)
    if state is None:
        raise NotImplementedError("obj_interactablesolid requires game.global_state")

    localize = getattr(game, "stringsetloc", None)
    if callable(localize):
        message = localize(DEFAULT_DIALOGUE, DEFAULT_DIALOGUE_KEY)
    else:
        # No invented Chapter 6 dialogue. Retain the literal supplied by GML.
        message = DEFAULT_DIALOGUE

    msgs = getattr(state, "msg", None)
    if msgs is None:
        msgs = []
        state.msg = msgs
    if isinstance(msgs, list):
        if not msgs:
            msgs.append(message)
        else:
            msgs[0] = message
    else:
        msgs[0] = message  # Dict-like or engine-managed indexed storage.

    instance.myinteract = 3
    state.msc = 0
    state.typer = 5
    state.fc = 0
    # GML redundantly assigns fc twice. One write yields the same state.
    state.interact = 1

    create = getattr(game, "instance_create", None)
    if not callable(create):
        raise NotImplementedError(
            "Default dialogue requires game.instance_create(x, y, obj_dialoguer)"
        )
    resource = getattr(game, "obj_dialoguer", "obj_dialoguer")
    instance.mydialoguer = create(0, 0, resource)
    # The event's return value is not used by scr_interact; return None.
    return None


class InteractableSolid(SolidBlock):
    """GameMaker obj_interactablesolid's three supplied event handlers.

    Inherits only the resource/instance base from eventless `SolidBlock`;
    no fictitious parent Create or Step logic is called.
    """

    object_name = "obj_interactablesolid"
    parent_object = "obj_solidblock"
    sprite_index_default = "spr_interactable"
    sprite_metadata = SPR_INTERACTABLE
    visible_default = False
    solid_default = False  # GameMaker editor checkbox, despite parent name
    persistent_default = False
    uses_physics = False
    collision_shape = "circle"  # Editor-only Box2D shape; physics is disabled

    def __init__(
        self,
        game: Any,
        x: float = 0,
        y: float = 0,
        *,
        image_xscale: float = 1.0,
        image_yscale: float = 1.0,
        extflag: Any = _MISSING,
        on_interact: Callable[[], Any] | Any = _MISSING,
        depth_callback: Callable[[Any], Any] | None = None,
    ) -> None:
        super().__init__(
            game, x, y,
            image_xscale=image_xscale,
            image_yscale=image_yscale,
        )
        self._depth_callback = depth_callback
        if extflag is not _MISSING:
            self.extflag = extflag
        if on_interact is not _MISSING:
            self.on_interact = on_interact
        self.create()

    def create(self) -> None:
        """GML Create: reset interaction, stop sprite, compute depth if wired."""
        self.myinteract = 0
        self.image_speed = 0
        depth = self._depth_callback
        if depth is None:
            depth = getattr(self.game, "scr_depth", None)
        if callable(depth):
            depth(self)  # GameMaker script runs in this object's context.
        # The GML initializes extflag only if the field does not exist.
        if not hasattr(self, "extflag"):
            self.extflag = 0
        # The original Create event does NOT initialize mydialoguer.

    def user_event_0(self) -> Any:
        """GML Other_10; callback takes precedence over default dialogue."""
        return interactablesolid_user_event_0(self)

    def event_user(self, index: int) -> Any:
        if index != 0:
            raise NotImplementedError(
                f"obj_interactablesolid only supplies User Event 0, got {index}"
            )
        return self.user_event_0()

    def _dialoguer_exists(self) -> bool:
        dialoguer = getattr(self, "mydialoguer", _MISSING)
        if dialoguer in (_MISSING, None, -4, -1):
            return False
        exists = getattr(self.game, "i_ex", None)
        if not callable(exists):
            exists = getattr(self.game, "instance_exists", None)
        if not callable(exists):
            raise NotImplementedError(
                "Checking a created dialoguer requires game.i_ex or game.instance_exists"
            )
        return bool(exists(dialoguer))

    def _release_player_buffer(self) -> None:
        """Run `with (obj_mainchara) onebuffer = 5` for available characters."""
        instances_of = getattr(self.game, "instances_of", None)
        if callable(instances_of):
            for player in instances_of("obj_mainchara"):
                player.onebuffer = 5
            return
        # Common Chapter-6 game.py adapter for its single Kris instance.
        player = getattr(self.game, "mainchara", None)
        if player is not None:
            player.onebuffer = 5

    def step(self) -> None:
        """GML normal Step: unlock after a dialogue instance disappears."""
        if self.myinteract == 3 and not self._dialoguer_exists():
            state = getattr(self.game, "global_state", None)
            if state is None:
                raise NotImplementedError("obj_interactablesolid requires game.global_state")
            state.interact = 0
            self.myinteract = 0
            self._release_player_buffer()


obj_interactablesolid = InteractableSolid

__all__ = [
    "InteractableSolid", "interactablesolid_user_event_0",
    "DEFAULT_DIALOGUE", "DEFAULT_DIALOGUE_KEY", "obj_interactablesolid",
]
