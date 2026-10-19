"""Python port of DELTARUNE's ``gml_GlobalScript_scr_down_partymember``.

This is battle logic, not rendering code. Pass an engine/battle context as
``state``. Its ``global_state`` attribute, if present, holds GML's ``global``
party arrays; otherwise the party arrays are read directly from ``state``.

Required global-state fields:
    char[slot]          -> character ID (0 means the slot is empty)
    hp[character_id]    -> current HP
    maxhp[character_id] -> maximum HP
    charinstance[slot]  -> live actor object with x, y, myheight, hurt,
                           and hurttimer attributes
    myfight             -> battle mode flag
    charturn            -> active party slot

Required engine methods:
    scr_debug_print(message)
    instances_of(object_type) -> iterable of instances of that object type
    instance_create(x, y, object_type) -> newly created instance
    instance_exists(object_type) -> bool
    scr_dead(party_slot)
    snd_play(sound_id)

Battle controllers returned by ``instances_of('obj_battlecontroller')`` must
expose ``scr_nexthero()``. This models GML's
``with (obj_battlecontroller) scr_nexthero();`` execution context.

The object types ``obj_dmgwriter``, ``obj_battlecontroller``, ``obj_shake``
and sound ID ``snd_hurt1`` default to their GML names as strings. If
``state`` has matching attributes, those asset handles are used instead.

An engine adapter must implement the above operations. No Tkinter rendering,
sound playback, or object management is hard-coded in this module.
"""

from math import ceil, floor


def _gml_round(value: float) -> int:
    """Round half values away from zero, matching the project's GML ports."""
    return floor(value + 0.5) if value >= 0 else ceil(value - 0.5)


def scr_down_partymember(state, party_slot: int) -> None:
    """Down the character occupying ``party_slot``, triggering battle effects.

    Matches the supplied GML's operation order, including spawning a damage
    writer even when the computed damage is zero, and calling ``scr_dead``
    regardless of the character's current HP.
    """
    global_state = getattr(state, "global_state", state)

    if global_state.char[party_slot] == 0:
        state.scr_debug_print(f"No party member in slot {party_slot}")
        return

    damage_writer_type = getattr(state, "obj_dmgwriter", "obj_dmgwriter")
    battle_controller_type = getattr(state, "obj_battlecontroller", "obj_battlecontroller")
    shake_type = getattr(state, "obj_shake", "obj_shake")
    hurt_sound = getattr(state, "snd_hurt1", "snd_hurt1")

    # Retire previously scheduled damage writers with an active delay timer.
    for writer in state.instances_of(damage_writer_type):
        if writer.delaytimer >= 1:
            writer.killactive = 1

    char_target = global_state.char[party_slot]
    hp_diff = max(
        0,
        global_state.hp[char_target]
        + _gml_round(global_state.maxhp[char_target] / 2),
    )

    actor = global_state.charinstance[party_slot]
    if hp_diff > 0:
        actor.hurt = 1
        actor.hurttimer = 0

    # Unqualified `dmgwriter = ...` in GML stores this on the caller instance.
    state.dmgwriter = state.instance_create(
        actor.x,
        (actor.y + actor.myheight) - 24,
        damage_writer_type,
    )
    state.dmgwriter.damage = hp_diff

    # Character HP is indexed by character ID, not by party slot.
    global_state.hp[char_target] = _gml_round(-global_state.maxhp[char_target] / 2)
    state.scr_dead(party_slot)

    if global_state.myfight == 0 and global_state.charturn == party_slot:
        for controller in state.instances_of(battle_controller_type):
            controller.scr_nexthero()

    state.snd_play(hurt_sound)

    if not state.instance_exists(shake_type):
        state.instance_create(0, 0, shake_type)


__all__ = ["scr_down_partymember"]
