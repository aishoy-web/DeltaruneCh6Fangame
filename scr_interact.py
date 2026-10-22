"""GML-compatible scr_interact() for DELTARUNE Chapter 6.

Source (gml_GlobalScript_scr_interact)::

    function scr_interact() {
        myinteract = 1;
        event_user(0);
    }

GameMaker executes this script in the current *target instance's* context,
usually inside ``with (interactedobject) scr_interact();``. Python has no
implicit GameMaker ``self``, so pass that target explicitly.

No automatic dialogue locking, collision tests, or input detection occurs here.
"""
from __future__ import annotations

from typing import Any


def scr_interact(target: Any) -> None:
    """Start an interaction on *target* and execute its User Event 0.

    ``myinteract`` is assigned before event dispatch, as in the source GML.
    The return value of the user event is intentionally discarded: GML
    ``scr_interact`` has no return statement.

    The target must implement ``event_user(0)``. If an engine does not provide
    that operation, wire its event dispatch into the instance adapter rather
    than skipping the event.
    """
    target.myinteract = 1
    target.event_user(0)


__all__ = ["scr_interact"]
