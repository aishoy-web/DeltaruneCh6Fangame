"""Python port of ``gml_GlobalScript_scr_makenpc``.

Provides the three original GameMaker helpers:
    scr_makenpc(state, layer_name="", sprite_name="", marker_option=False,
                show_hitbox=False)
    scr_makenpc_fromasset(state, sprite_element, marker_option=False,
                          show_hitbox=False)
    scr_makenpc_from_marker(state, marker, show_hitbox=False)

The supplied engine ``state`` must expose its existing GameMaker-like methods:
    layer_get_id(name)
    layer_sprite_get_id(layer_id, sprite_name)
    layer_sprite_get_{sprite,x,y,xscale,yscale,alpha,angle,blend,speed,index}(id)
    instance_create_depth(x, y, depth, object_type)
    scr_marker_ext(x, y, sprite, xscale, yscale, angle, frame, blend,
                   depth, extra1, extra2, alpha, marker_option)
    setxy(x, y, instance)
    scr_sizeexact(width, height, instance)
    scr_depth_alt(marker)
    scr_debug()                     [only when requesting debug hitbox display]
    scr_debug_print(message)        [only on layer/sprite lookup errors]
    debug_message(message)          [only on layer/sprite lookup errors]

``state.obj_trigger_interact`` may optionally identify the NPC resource; otherwise
its original GML resource name is forwarded as a string for engine resolution.

GML ``undefined`` arguments are represented by ``None``. Your marker adapter
should interpret these as unspecified, not as literal depth/coordinates.

These functions configure NPCs; they do not provide the marker, collision,
interaction, or depth-management implementations themselves.
"""


NO_NPC = -4
_UNDEFINED = None


def _layer_sprite_properties(state, sprite_element):
    """Read in GML order, including angle and speed (unused in source)."""
    sprite = state.layer_sprite_get_sprite(sprite_element)
    x = state.layer_sprite_get_x(sprite_element)
    y = state.layer_sprite_get_y(sprite_element)
    xscale = state.layer_sprite_get_xscale(sprite_element)
    yscale = state.layer_sprite_get_yscale(sprite_element)
    alpha = state.layer_sprite_get_alpha(sprite_element)
    state.layer_sprite_get_angle(sprite_element)  # Read but not used in GML.
    blend = state.layer_sprite_get_blend(sprite_element)
    state.layer_sprite_get_speed(sprite_element)  # Read but not used in GML.
    frame = state.layer_sprite_get_index(sprite_element)
    return sprite, x, y, xscale, yscale, alpha, blend, frame


def _finish_npc(state, npc, *, show_hitbox, debug_only):
    marker = npc.marker
    true_x = marker.bbox_left
    true_y = marker.bbox_top
    true_width = marker.bbox_right - marker.bbox_left
    true_height = marker.bbox_bottom - marker.bbox_top

    # The original script positions the interactable at the marker's BBOX,
    # not necessarily at the source sprite/marker origin.
    state.setxy(true_x, true_y, npc)
    npc.markerxoffset = true_x - marker.x
    npc.markeryoffset = true_y - marker.y
    npc.markerstick = True
    state.scr_sizeexact(true_width, true_height, npc)

    # scr_makenpc's visibility is unconditional; the other two helpers
    # require both a requested hitbox and an enabled debug mode.
    if show_hitbox and (not debug_only or state.scr_debug()):
        npc.visible = True
        npc.image_alpha = 1

    npc.strict = True
    npc.issolid = True
    npc.talked = 0
    state.scr_depth_alt(marker)
    return npc


def _npc_type(state):
    return getattr(state, "obj_trigger_interact", "obj_trigger_interact")


def _npc_from_sprite_element(
    state, sprite_element, marker_option, show_hitbox, *, from_asset
):
    sprite, x, y, xscale, yscale, alpha, blend, frame = (
        _layer_sprite_properties(state, sprite_element)
    )
    npc = state.instance_create_depth(0, 0, 0, _npc_type(state))

    npc.marker = state.scr_marker_ext(
        x, y, sprite, xscale, yscale, 0, frame, blend,
        npc.depth if from_asset else _UNDEFINED,
        _UNDEFINED, _UNDEFINED, alpha, marker_option,
    )
    return _finish_npc(
        state, npc, show_hitbox=show_hitbox, debug_only=from_asset
    )


def scr_makenpc(
    state, layer_name="", sprite_name="", marker_option=False, show_hitbox=False
):
    """Make an interactable NPC from a named layer sprite, or return -4.

    In contrast to the other variants, ``show_hitbox=True`` takes effect
    *even in non-debug builds*, matching the source GML.
    """
    layer_id = state.layer_get_id(layer_name)
    if layer_id == -1:
        state.scr_debug_print("Warning: Check Output Console")
        state.debug_message(
            f"scr_makenpc({layer_name},{sprite_name}) Result: Layer Not Found"
        )
        return NO_NPC

    sprite_element = state.layer_sprite_get_id(layer_id, sprite_name)
    if sprite_element == -1:
        state.debug_message(
            f'scr_makenpc("{layer_name}","{sprite_name}") Result: Sprite Not Found'
        )
        state.scr_debug_print("Warning: Check Output Console")
        return NO_NPC

    return _npc_from_sprite_element(
        state, sprite_element, marker_option, show_hitbox, from_asset=False
    )


def scr_makenpc_fromasset(
    state, sprite_element, marker_option=False, show_hitbox=False
):
    """Make an interactable NPC from a known layer-sprite element ID.

    Passes the new NPC's depth to ``scr_marker_ext``, as in the source.
    """
    return _npc_from_sprite_element(
        state, sprite_element, marker_option, show_hitbox, from_asset=True
    )


def scr_makenpc_from_marker(state, marker, show_hitbox=False):
    """Wrap an existing marker in an interactable NPC without recreating it."""
    # Original GML reads these attributes (though it does not subsequently
    # use them). Retain the accesses to mirror the original requirements.
    _ = (
        marker.sprite_index,
        marker.x,
        marker.y,
        marker.image_xscale,
        marker.image_yscale,
        marker.image_alpha,
        marker.image_angle,
        marker.image_blend,
        marker.image_speed,
    )
    npc = state.instance_create_depth(0, 0, 0, _npc_type(state))
    npc.marker = marker
    return _finish_npc(
        state, npc, show_hitbox=show_hitbox, debug_only=True
    )


__all__ = ["scr_makenpc", "scr_makenpc_fromasset", "scr_makenpc_from_marker"]
