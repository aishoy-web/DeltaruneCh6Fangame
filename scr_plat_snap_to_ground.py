"""Python port of DELTARUNE's gml_GlobalScript_scr_plat_snap_to_ground.

The function acts on the calling GameMaker-style instance, rather than on a
shared global collision context. It intentionally preserves GML's quirks,
including the immediate ``y`` assignment for entity ground *before* a separate
block test on the standard floor snap coordinate.

The engine must supply instance_exists, instance_place and place_meeting; it
may additionally supply resolve_instance when references are numeric IDs.
"""
from __future__ import annotations

from math import pi, sin

NOONE = -4


def _engine(instance):
    return getattr(instance, "engine", instance)


def _method(instance, name):
    method = getattr(instance, name, None)
    if not callable(method):
        method = getattr(_engine(instance), name, None)
    if not callable(method):
        raise NotImplementedError(
            f"scr_plat_snap_to_ground requires {name}(...) on the entity or engine"
        )
    return method


def _exists(instance, reference):
    if reference is None or reference == NOONE or reference == 0:
        return False
    checker = getattr(instance, "instance_exists", None)
    if not callable(checker):
        checker = getattr(_engine(instance), "instance_exists", None)
    if callable(checker):
        return bool(checker(reference))
    # An object reference can be inspected in a minimal Python test harness;
    # numeric handles need an actual instance-registry implementation.
    if isinstance(reference, (int, float, str)):
        raise NotImplementedError("numeric references require instance_exists")
    return not getattr(reference, "destroyed", False)


def _resolve(instance, reference):
    if not isinstance(reference, (int, float, str)):
        return reference
    return _method(instance, "resolve_instance")(reference)


def _block_type(instance):
    return getattr(_engine(instance), "obj_plat_block", "obj_plat_block")


def _clamp(value, lower, upper):
    # GameMaker-style clamp. Do not reorder endpoints: the source does not.
    return min(max(value, lower), upper)


def scr_plat_snap_to_ground(instance):
    """Snap *instance* to its ``ground`` according to the original GML.

    The return value is always None (equivalent to no meaningful GML return).
    Note: ``bbox_bottom_r`` is an origin-relative offset from the entity's
    initialization, not ``bbox_bottom - y`` recomputed here.
    """
    ground_ref = instance.ground
    if not _exists(instance, ground_ref):
        return

    ground = _resolve(instance, ground_ref)
    block = _block_type(instance)

    if ground.is_slope:
        if ground.plattype == 0:
            # Original straight-line slope, using the correct collision-box
            # edge for the slope's horizontal orientation.
            m = (ground.y2 - ground.y1) / (ground.x2 - ground.x1)
            floor_x = instance.bbox_right - ground.x1
            if ground.image_xscale < 0:
                floor_x = instance.bbox_left - ground.x1

            instance.floorY = _clamp(m * floor_x + ground.y1,
                                     ground.y2, ground.y1)
            new_y = instance.floorY - (instance.bbox_bottom_r + 2)
            solid = _method(instance, "instance_place")(instance.x, new_y, block)
            if not _exists(instance, solid):
                instance.y = new_y

        if ground.plattype == 1:
            # Sinusoidal/curved surface. Like GML, zero width is invalid.
            h = ground.y2 - ground.y1
            floor_x = instance.x - ground.x1
            instance.floorY = ground.y - (
                sin((pi * floor_x) / abs(ground.x1 - ground.x2)) * abs(h)
            )
            new_y = instance.floorY - instance.bbox_bottom_r
            solid = _method(instance, "instance_place")(instance.x, new_y, block)
            if not _exists(instance, solid):
                instance.y = new_y
    else:
        new_y = instance.y
        offset = instance.bbox_bottom_r

        if not ground.quicksand:
            new_y = ground.bbox_top - offset - 1
            if ground.is_entity:
                # Intentional: this assignment is made BEFORE the collision
                # test, and is not rolled back when the test is blocked.
                instance.y = ground.y - ground.bbox_top_r - offset - 1
        else:
            # Identical numerical expression, but without the entity rewrite.
            new_y = ground.bbox_top - instance.bbox_bottom_r - 1

        if not _method(instance, "place_meeting")(instance.x, new_y, block):
            instance.y = new_y


def bind_snap_to_ground(instance):
    """Bind the helper to a specific entity after Create/inherited Create.

    Compatible with ``obj_plat_entity``'s bound-per-instance dispatch and the
    ``obj_plat_follower`` Step/Pre Draw dispatch in the updated modules.
    """
    instance.scr_plat_snap_to_ground = lambda: scr_plat_snap_to_ground(instance)
    return instance


__all__ = ["scr_plat_snap_to_ground", "bind_snap_to_ground", "NOONE"]
