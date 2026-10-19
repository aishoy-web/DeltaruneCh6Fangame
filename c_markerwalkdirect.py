"""Python port of gml_GlobalScript_c_markerwalkdirect.

This helper enqueues a cutscene command using the host cutscene system.
It does not move any character immediately.
"""


def c_markerwalkdirect(state, arg0, arg1, arg2, arg3, arg4=-1, arg5=0.25):
    """Forward marker-walk parameters to the cutscene command queue.

    ``state`` must provide ``c_cmd_x(command_name, *arguments)``.
    Argument meanings are intentionally left unchanged from the supplied GML.
    """
    state.c_cmd_x("markerwalkdirect", arg0, arg1, arg2, arg3, arg4, arg5)
