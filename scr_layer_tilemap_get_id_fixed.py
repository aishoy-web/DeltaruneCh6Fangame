"""Python port of gml_GlobalScript_scr_layer_tilemap_get_id_fixed.

The engine context (``state``) must provide:

* ``layer_get_all_elements(layer)``: return the layer's element IDs in order.
* ``layer_get_element_type(element_id)``: return that element's GML type ID.

GameMaker's tilemap layer element type is 5 in the supplied script.
"""

TILEMAP_ELEMENT_TYPE = 5
NO_TILEMAP = -1


def scr_layer_tilemap_get_id_fixed(state, layer):
    """Return the first tilemap element ID in *layer*, or -1 if absent.

    This ports the original GML's first-match lookup, not a lookup by layer ID.
    Any invalid-layer behavior is delegated to the engine's layer adapter.
    """
    elements = state.layer_get_all_elements(layer)

    for element_id in elements:
        if state.layer_get_element_type(element_id) == TILEMAP_ELEMENT_TYPE:
            return element_id

    return NO_TILEMAP
