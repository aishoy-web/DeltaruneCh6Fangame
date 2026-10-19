"""Port of DELTARUNE's ``gml_GlobalScript_scr_makecaterpillar``.

``state.instance_create(x, y, object_type)`` must create and return a mutable
follower instance. The instance is stored in ``global_state.cinstance[slot]``.
Resource references are taken from same-named attributes of ``state``; when
unavailable, the literal original GML sprite name is used. This allows a
Tkinter sprite resolver to look up these names without encoding asset paths.

Only character IDs 3..9 customize sprites in the supplied source; ID 2 keeps
the default sprites assigned by obj_caterpillarchara's Create event.
"""

from scr_flag_get import scr_flag_get


def _asset(state, resource_name):
    return getattr(state, resource_name, resource_name)


def _sprite_set(state, follower, prefix_names):
    follower.usprite = _asset(state, prefix_names[0])
    follower.dsprite = _asset(state, prefix_names[1])
    follower.rsprite = _asset(state, prefix_names[2])
    follower.lsprite = _asset(state, prefix_names[3])


def scr_makecaterpillar(state, x, y, character_id, slot):
    """Create one overworld follower and return the newly created instance."""
    globals_ = getattr(state, "global_state", state)
    follower_type = _asset(state, "obj_caterpillarchara")
    follower = state.instance_create(x, y, follower_type)
    globals_.cinstance[slot] = follower
    follower.target = 12 + (slot * 12)

    if character_id == 3:  # Ralsei
        _sprite_set(state, follower, (
            "spr_ralseiu", "spr_ralseid", "spr_ralseir", "spr_ralseil",
        ))
        if globals_.chapter >= 2:
            follower.name = "ralsei"
            _sprite_set(state, follower, (
                "spr_ralsei_walk_up", "spr_ralsei_walk_down",
                "spr_ralsei_walk_right", "spr_ralsei_walk_left",
            ))
            if globals_.chapter == 5 and scr_flag_get(globals_, 1311) == 1:
                _sprite_set(state, follower, (
                    "spr_ralseiu", "spr_ralseid", "spr_ralseir", "spr_ralseil",
                ))

    elif character_id == 4:  # Noelle
        follower.name = "noelle"
        if globals_.darkzone == 0:
            suffix = "lw"
        else:
            suffix = "dw"
        _sprite_set(state, follower, (
            f"spr_noelle_walk_up_{suffix}",
            f"spr_noelle_walk_down_{suffix}",
            f"spr_noelle_walk_right_{suffix}",
            f"spr_noelle_walk_left_{suffix}",
        ))

    elif character_id == 5:  # Berdly
        follower.name = "berdly"
        _sprite_set(state, follower, (
            "spr_berdly_walk_up_dw", "spr_berdly_walk_down_dw",
            "spr_berdly_walk_right_dw", "spr_berdly_walk_left_dw",
        ))

    elif character_id == 6:  # Original Starwalker
        follower.name = "starwalker"
        _sprite_set(state, follower, ("spr_npc_originalstarwalker",) * 4)

    elif character_id == 7:  # Flowery
        follower.name = "flowery"
        _sprite_set(state, follower, (
            "spr_flowery_walk_up", "spr_flowery_walk_down",
            "spr_flowery_walk_right", "spr_flowery_walk_left",
        ))

    elif character_id == 8:  # Aqua
        follower.name = "aqua"
        _sprite_set(state, follower, (
            "spr_aqua_walk_up", "spr_aqua_walk_down",
            "spr_aqua_walk_right", "spr_aqua_walk_left",
        ))

    elif character_id == 9:  # Orange
        follower.name = "orange"
        _sprite_set(state, follower, (
            "spr_enemy_orange_walk_up", "spr_enemy_orange_walk_down_sad",
            "spr_enemy_orange_walk_right_sad", "spr_enemy_orange_walk_left_sad",
        ))

    return follower


__all__ = ["scr_makecaterpillar"]
