"""GML scr_ground_checks + scr_ground_entity_checks for Chapter 6.

Both functions execute in the context of the calling entity, like GameMaker's
instance-scoped global scripts. Their colliding-object list is a managed DS-list
when the game supplies ``scr_ds_list_create_managed``; otherwise a normal Python
list serves as a lightweight engine adapter.

IMPORTANT: GML deliberately (or accidentally) keeps ``_above`` and
``_floor_too_small`` outside the candidate loops. That behavior is retained.
"""
from __future__ import annotations

from math import ceil
from typing import Any

NOONE = -4
ENTITY_RESOURCE_ID = 693
_MISSING = object()


def _engine(instance):
    return getattr(instance, "engine", instance)


def _get_method(instance, name, required=True):
    # Prefer the instance itself, then its engine. Do not allow the engine to
    # supply a bare, unbound 'current instance': each caller owns its list.
    method = getattr(instance, name, None)
    if not callable(method):
        method = getattr(_engine(instance), name, None)
    if callable(method):
        return method
    if required:
        raise NotImplementedError(f"scr_ground_checks needs {name}(...) on the entity or engine")
    return None


def _ds_type(instance):
    return getattr(_engine(instance), "ds_type_list", "ds_type_list")


def _list_is_valid(instance, handle):
    if isinstance(handle, list):
        return True
    checker = _get_method(instance, "ds_exists", required=False)
    if checker is None:
        return False
    return bool(checker(handle, _ds_type(instance)))


def _ensure_checklist(instance):
    handle = getattr(instance, "__platchecks_list", _MISSING)
    exists_fn = _get_method(instance, "variable_instance_exists", required=False)
    if exists_fn is not None:
        exists = bool(exists_fn(getattr(instance, "id", instance), "__platchecks_list"))
    else:
        exists = handle is not _MISSING

    if not exists or handle is _MISSING or not _list_is_valid(instance, handle):
        create = _get_method(instance, "scr_ds_list_create_managed", required=False)
        # The Python list fallback is an adapter, not a fake GameMaker DS handle.
        handle = create() if create is not None else []
        setattr(instance, "__platchecks_list", handle)
    if isinstance(handle, list):
        handle.clear()
    else:
        _get_method(instance, "ds_list_clear")(handle)
    return handle


def _candidate_items(instance, x, y, object_type, handle):
    result = _get_method(instance, "instance_place_list")(
        x, y, object_type, handle, False
    )
    if isinstance(result, (list, tuple)):
        # Support engines that return a Python sequence instead of a GML count.
        if isinstance(handle, list):
            handle[:] = result
        yield from result
        return

    count = int(result)
    if isinstance(handle, list):
        if count > len(handle):
            raise RuntimeError(
                "instance_place_list returned more candidates than it wrote "
                "to __platchecks_list"
            )
        for i in range(count):
            yield handle[i]
    else:
        find_value = _get_method(instance, "ds_list_find_value")
        for i in range(count):
            yield find_value(handle, i)


def _resolve(instance, candidate):
    """An engine may represent instances by either objects or numeric IDs."""
    if isinstance(candidate, (int, str)):
        if candidate == NOONE:
            return None
        resolver = _get_method(instance, "resolve_instance", required=False)
        if resolver is None:
            raise NotImplementedError(
                "numeric collision candidates require resolve_instance(id)"
            )
        return resolver(candidate)
    return candidate


def scr_ground_checks(instance, x, y, object_type):
    """Select a qualifying floor; return its reference or GameMaker -4.

    Args:
        instance: collision-checking entity (with bbox_bottom, vspeed, etc.)
        x, y: position passed to GameMaker instance_place_list
        object_type: collision object/resource passed through unchanged
    """
    checklist = _ensure_checklist(instance)
    above = False
    best_ref = NOONE
    best = None
    vertical_speed = ceil(abs(instance.vspeed))

    for ref in _candidate_items(instance, x, y, object_type, checklist):
        obj = _resolve(instance, ref)
        if obj is None:
            continue
        if obj.is_barrier and instance.ignore_barriers:
            continue

        if (instance.bbox_bottom - vertical_speed) < (obj.bbox_top + 2):
            above = True
        if obj.is_slope:
            if obj.plattype == 0 and instance.y < obj.y:
                above = True
            if obj.plattype == 1:
                above = True
        if obj.quicksand and instance.bbox_bottom < obj.bbox_bottom:
            above = True

        if above:
            if best is None or (obj.y < best.y and obj.y >= instance.bbox_bottom):
                best, best_ref = obj, ref

    return best_ref


def scr_ground_entity_checks(instance, x, y):
    """Return the first qualifying rideable entity, or -4.

    The GML's _above and _floor_too_small variables are intentionally sticky
    across all candidates in the same search.
    """
    checklist = _ensure_checklist(instance)
    above = False
    floor_too_small = False

    for ref in _candidate_items(instance, x, y, ENTITY_RESOURCE_ID, checklist):
        obj = _resolve(instance, ref)
        if obj is None:
            continue
        if (instance.bbox_bottom - ceil(abs(instance.vspeed) + 2)) < (obj.bbox_top + 2):
            above = True

        area = abs(obj.bbox_right - obj.bbox_left) * abs(obj.bbox_bottom - obj.bbox_top)
        myarea = abs(instance.bbox_right - instance.bbox_left) * abs(
            instance.bbox_bottom - instance.bbox_top
        )
        if (area * 5) < myarea:
            floor_too_small = True

        if above and not floor_too_small and obj.rideable:
            return ref

    return NOONE


def bind_ground_checks(instance):
    """Opt-in binding for obj_plat_entity: keep per-entity GML `self` context.

    Call this AFTER the entity/follower has been initialized. The parent's
    ordinary Step prefers these bound hooks but falls back to engine methods
    when they have not been installed.
    """
    instance.scr_ground_checks = (
        lambda x, y, resource: scr_ground_checks(instance, x, y, resource)
    )
    instance.scr_ground_entity_checks = (
        lambda x, y: scr_ground_entity_checks(instance, x, y)
    )
    return instance


__all__ = ["scr_ground_checks", "scr_ground_entity_checks", "bind_ground_checks", "NOONE", "ENTITY_RESOURCE_ID"]
