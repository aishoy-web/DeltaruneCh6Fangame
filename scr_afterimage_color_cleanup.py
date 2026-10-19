"""Python port of ``gml_GlobalScript_scr_afterimage_color_cleanup``.

Run in the context of an afterimage instance (``state``). GameMaker's DS-list
handles are not ordinary Python lists: ``ds_exists`` and ``ds_list_destroy``
should be supplied by the game's DS registry/adapter.

The original script:
  * Checks whether the instance has ``trail_x``.
  * Destroys anything only if ``trail_x`` is a registered DS list.
  * Then destroys all seven list handles in the original order, without
    separately validating each one.
  * Does not clear the instance attributes or return a value.
"""

from typing import Any


_TRAIL_LIST_NAMES = (
    "trail_x",
    "trail_y",
    "trail_xscale",
    "trail_yscale",
    "trail_img",
    "trail_spr",
    "alpha",
)


def scr_afterimage_color_cleanup(state: Any) -> None:
    """Destroy the seven DS lists belonging to the calling afterimage.

    Requires ``state.ds_exists(handle, state.ds_type_list)`` and
    ``state.ds_list_destroy(handle)``. If the engine provides
    ``variable_instance_exists(instance_id, variable_name)``, use it to check
    ``trail_x``. Otherwise, a Python attribute-existence check is equivalent
    for ordinary Python instances.
    """
    variable_exists = getattr(state, "variable_instance_exists", None)
    if callable(variable_exists):
        instance_id = getattr(state, "id", state)
        if not variable_exists(instance_id, "trail_x"):
            return
    elif not hasattr(state, "trail_x"):
        return

    if not state.ds_exists(state.trail_x, state.ds_type_list):
        return

    for name in _TRAIL_LIST_NAMES:
        state.ds_list_destroy(getattr(state, name))
