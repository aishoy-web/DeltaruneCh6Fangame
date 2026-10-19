"""Python port of ``gml_GlobalScript_scr_darkcameraideal``.

Calculate Kris's ideal Dark World camera position without moving the camera.
Returns ``{'x': number, 'y': number}``, or ``None`` if no main character
instance is available (equivalent to an undefined GML result).

Engine adapter requirements on ``state``:
    obj_mainchara (optional): resource handle for Kris (or Kris instance)
    resolve_instance(resource_or_id): find a live instance (if necessary)
    room_width, room_height: dimensions of the current room
    view_wport[0], view_hport[0]: dimensions of the camera viewport
    obj_camera_nudger, obj_camera_clamper (optional): resource handles
    instance_place(x, y, resource): find an instance colliding with Kris's
        position, with Kris as the collision source (or implement the same
        method on Kris itself)
    i_ex(ref) / instance_exists(ref) (optional): instance existence check

Kris needs x, y, initwd, initht, nudgex, nudgey, nudgelerp.  The nudger
instance needs xamt, yamt and lerpstrength; the clamper needs xmin,
xmax, ymin and ymax (-4 means 'use the default boundary').

Source quirks intentionally retained:
- The sign-dependent ``_xoff`` is calculated but NEVER used. Both nudgex
  and nudgey lerp towards values using ``_yoff``.
- Camera position is clamped against room dimensions, then possibly
  clamped again to a camera-clamper object's custom boundaries.
- ``camerax()`` and ``cameray()`` initialize a temporary struct in GML,
  but both fields are unconditionally overwritten before it is returned.
  Their unused results are omitted from this Python port.
- No special adjustment is made for rooms smaller than the viewport.
"""

from math import floor


def _clamp(value, minimum, maximum):
    """GameMaker-like clamp; normal usage assumes minimum <= maximum."""
    return min(max(value, minimum), maximum)


def _lerp(start, end, amount):
    return start + (end - start) * amount


def _resolve_character(state):
    reference = getattr(state, "obj_mainchara", "obj_mainchara")
    if hasattr(reference, "x") and hasattr(reference, "y"):
        return reference

    resolver = getattr(state, "resolve_instance", None)
    if not callable(resolver):
        raise AttributeError(
            "state.resolve_instance(reference) is required to find obj_mainchara"
        )
    return resolver(reference)


def _instance_at_player(state, kris, resource_name):
    """Resolve the first overlapping object, if any, as a live instance."""
    reference = getattr(state, resource_name, resource_name)
    place = getattr(kris, "instance_place", None)
    if not callable(place):
        place = getattr(state, "instance_place", None)
    if not callable(place):
        raise AttributeError("Kris or state must implement instance_place(x, y, object)")

    candidate = place(kris.x, kris.y, reference)
    if candidate is None or candidate == -4:
        return None

    exists = getattr(state, "i_ex", None)
    if not callable(exists):
        exists = getattr(state, "instance_exists", None)
    if callable(exists) and not exists(candidate):
        return None

    if hasattr(candidate, "__dict__") or hasattr(candidate, "xamt") or hasattr(candidate, "xmin"):
        return candidate

    resolver = getattr(state, "resolve_instance", None)
    if not callable(resolver):
        raise AttributeError(
            "state.resolve_instance(reference) is required when "
            "instance_place returns an instance ID"
        )
    instance = resolver(candidate)
    if instance is None:
        raise LookupError(f"Overlapping instance {candidate!r} could not be resolved")
    return instance


def scr_darkcameraideal(state):
    """Return the calculated ideal Dark World camera position for Kris.

    Note: like the source script, this may update Kris's persistent
    ``nudgex``, ``nudgey``, and ``nudgelerp`` fields when a nudger exists.
    It does NOT set the actual camera position.
    """
    kris = _resolve_character(state)
    if kris is None:
        return None

    roomw = state.room_width
    roomh = state.room_height
    vieww = state.view_wport[0]
    viewh = state.view_hport[0]
    krx = kris.initwd / 2
    kry = kris.initht / 2

    nudger = _instance_at_player(state, kris, "obj_camera_nudger")
    if nudger is not None:
        if nudger.lerpstrength != -4:
            kris.nudgelerp = nudger.lerpstrength

        yoff = 2 if nudger.yamt > 0 else -2
        xoff = 2 if nudger.xamt > 0 else -2  # GML computes this but never uses it.
        _ = xoff

        kris.nudgex = _lerp(kris.nudgex, nudger.xamt + yoff, kris.nudgelerp)
        kris.nudgey = _lerp(kris.nudgey, nudger.yamt + yoff, kris.nudgelerp)
        kris.nudgex = _clamp(kris.nudgex, -abs(nudger.xamt), abs(nudger.xamt))
        kris.nudgey = _clamp(kris.nudgey, -abs(nudger.yamt), abs(nudger.yamt))

    camx = _clamp(kris.x - floor(vieww / 2 - krx) + kris.nudgex, 0, roomw - vieww)
    camy = _clamp(kris.y - floor(viewh / 2 - kry) + kris.nudgey, 0, roomh - viewh)

    clamper = _instance_at_player(state, kris, "obj_camera_clamper")
    if clamper is not None:
        lclamp = 0 if clamper.xmin == -4 else clamper.xmin
        rclamp = (roomw - vieww) if clamper.xmax == -4 else clamper.xmax
        uclamp = 0 if clamper.ymin == -4 else clamper.ymin
        dclamp = (roomh - viewh) if clamper.ymax == -4 else clamper.ymax
        camx = _clamp(camx, lclamp, rclamp)
        camy = _clamp(camy, uclamp, dclamp)

    return {"x": camx, "y": camy}


__all__ = ["scr_darkcameraideal"]
