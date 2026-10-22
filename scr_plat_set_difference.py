"""Port of gml_GlobalScript_scr_plat_set_difference for Chapter 6.

GML executes this script in the *calling instance's* context. Pass that
instance explicitly when calling from Python. It sets ``dif_x``/``dif_y``
only for ``dif_type`` 0 and 1; other values leave them untouched.

The magnitude is max(abs(velocity), abs(position displacement)); the SIGN
comes from the actual position displacement. Consequently a stationary object
has zero difference even if its velocity is nonzero.
"""
from __future__ import annotations


def _sign(value):
    """Equivalent to GameMaker's sign(value) for numeric values."""
    return 1 if value > 0 else -1 if value < 0 else 0


def scr_plat_set_difference(instance):
    """Update the instance's per-frame displacement values (GML equivalent).

    The function intentionally does not modify previous positions or speeds.
    It returns None, as the supplied GML has no explicit return value.
    """
    if instance.dif_type in (0, 1):
        delta_x = instance.x - instance.xprevious
        delta_y = instance.y - instance.yprevious
        instance.dif_x = _sign(delta_x) * max(abs(instance.hspeed), abs(delta_x))
        instance.dif_y = _sign(delta_y) * max(abs(instance.vspeed), abs(delta_y))


def bind_set_difference(instance):
    """Attach a zero-argument method using this instance's GML context.

    Bind after Create/inherited Create for consistency with the other
    platforming helpers. Do not install on a class shared by all instances.
    """
    instance.scr_plat_set_difference = lambda: scr_plat_set_difference(instance)
    return instance


__all__ = ["scr_plat_set_difference", "bind_set_difference"]
