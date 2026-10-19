"""Python port of gml_GlobalScript_d3d_draw_block.

Draw a six-sided textured block using the exact normals, UV coordinates and
triangle order of the supplied GML: 36 vertices, primitive kind 4.

The engine-state adapter must implement:
    gpu_get_texrepeat()
    gpu_set_texrepeat(enabled)
    d3d_primitive_begin_texture(primitive_kind, texture)
    d3d_vertex_normal_texture(x, y, z, nx, ny, nz, u, v)
    d3d_primitive_end()

This helper emits 3D drawing commands; it does not implement a 3D renderer.
"""


_TRIANGLES = (0, 1, 2, 2, 3, 0)


def d3d_draw_block(
    state,
    x1, y1, z1,
    x2, y2, z2,
    texture,
    hrepeat,
    vrepeat,
):
    """Draw the textured six-faced block specified by two opposite corners.

    Return ``None`` on success. No corner sorting, normal recalculation, or
    zero-size skipping is performed, matching the supplied GML.
    """
    # Two UV orientations appear in the original GML.
    uv_standard = ((0, 0), (0, vrepeat), (hrepeat, vrepeat), (hrepeat, 0))
    uv_z_positive = ((0, 0), (hrepeat, 0), (hrepeat, vrepeat), (0, vrepeat))

    # Vertices are listed as four corners per face; the triangle indices
    # below reproduce every one of the original GML's 36 vertex calls.
    faces = (
        # z1 (-Z)
        (((x1, y1, z1), (x1, y2, z1), (x2, y2, z1), (x2, y1, z1)), (0, 0, -1), uv_standard),
        # z2 (+Z)
        (((x1, y1, z2), (x2, y1, z2), (x2, y2, z2), (x1, y2, z2)), (0, 0, 1), uv_z_positive),
        # y2 (+Y)
        (((x1, y2, z1), (x1, y2, z2), (x2, y2, z2), (x2, y2, z1)), (0, 1, 0), uv_standard),
        # x2 (+X)
        (((x2, y2, z1), (x2, y2, z2), (x2, y1, z2), (x2, y1, z1)), (1, 0, 0), uv_standard),
        # y1 (-Y)
        (((x2, y1, z1), (x2, y1, z2), (x1, y1, z2), (x1, y1, z1)), (0, -1, 0), uv_standard),
        # x1 (-X)
        (((x1, y1, z1), (x1, y1, z2), (x1, y2, z2), (x1, y2, z1)), (-1, 0, 0), uv_standard),
    )

    old_repeat = state.gpu_get_texrepeat()
    try:
        state.gpu_set_texrepeat(True)
        state.d3d_primitive_begin_texture(4, texture)
        try:
            for corners, (nx, ny, nz), uvs in faces:
                for index in _TRIANGLES:
                    x, y, z = corners[index]
                    u, v = uvs[index]
                    state.d3d_vertex_normal_texture(x, y, z, nx, ny, nz, u, v)
        finally:
            state.d3d_primitive_end()
    finally:
        state.gpu_set_texrepeat(old_repeat)
