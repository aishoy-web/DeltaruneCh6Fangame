"""Python port of gml_GlobalScript_d3d_draw_floor.

Draws a textured four-vertex vertical plane between the X/Z endpoints,
spanning y1 to y2. This intentionally preserves the supplied GML's
primitive kind (6), vertex order, normals, and texture coordinates.

The ``state`` adapter must implement:
    gpu_get_texrepeat()
    gpu_set_texrepeat(enabled)
    d3d_primitive_begin_texture(primitive_kind, texture)
    d3d_vertex_normal_texture(x, y, z, nx, ny, nz, u, v)
    d3d_primitive_end()
"""

from math import sqrt


def d3d_draw_floor(
    state,
    x1,
    y1,
    z1,
    x2,
    y2,
    z2,
    texture,
    hrepeat,
    vrepeat,
):
    """Draw the textured plane defined by the two opposite corners.

    Returns 0 if its X/Z endpoints coincide (as in GML), otherwise None.
    """
    xdiff = x2 - x1
    zdiff = z2 - z1
    length_squared = xdiff * xdiff + zdiff * zdiff

    if length_squared == 0:
        return 0

    length = sqrt(length_squared)
    nx = -zdiff / length
    nz = xdiff / length

    old_repeat = state.gpu_get_texrepeat()
    try:
        state.gpu_set_texrepeat(True)
        state.d3d_primitive_begin_texture(6, texture)
        try:
            state.d3d_vertex_normal_texture(x1, y1, z1, nx, 0, nz, 0, 0)
            state.d3d_vertex_normal_texture(x1, y2, z1, nx, 0, nz, 0, vrepeat)
            state.d3d_vertex_normal_texture(x2, y2, z2, nx, 0, nz, hrepeat, vrepeat)
            state.d3d_vertex_normal_texture(x2, y1, z2, nx, 0, nz, hrepeat, 0)
        finally:
            state.d3d_primitive_end()
    finally:
        state.gpu_set_texrepeat(old_repeat)
