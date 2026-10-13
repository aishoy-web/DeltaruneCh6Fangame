"""Recovered GML scr_boltcheck, scr_boltcheck_onebutton and scr_spelltext."""
import random
import unittest
from battle_combat import BattleCombatController, CombatOption, QueuedAction
from battle_phases import AttackPressPhase
from battle_spelltext import SOURCE_TEMPLATES, battle_text_to_display, scr_spelltext
from encounter_setup import setup_encounter


def make(party=(1,2,3), **kwargs):
    return BattleCombatController(setup_encounter(203,party_ids=party), party, {}, **kwargs)


def timing(party=(1,), actions=(1,0,0), *, flags=None, weapons=None):
    c=BattleCombatController(setup_encounter(203,party_ids=party),party,flags or {},
                             equipped_weapons=weapons or {})
    c.state.charaction[:]=actions
    c.attack_phase()
    return c,c.attack_press


class BoltScoreTests(unittest.TestCase):
    def test_perfect_one_button_150_and_burst(self):
        c,p=timing()
        p.boltx=p.bolts[0].frame
        self.assertTrue(p.button('z'))
        self.assertEqual(p.points,[150,0,0])
        self.assertEqual(p.bolts[0].pressed,True)
        self.assertEqual(p.bursts[0].color,'yellow')
        self.assertEqual(p.bursts[0].magnitude,0.2)
        self.assertEqual(p.pressbuffer,[5,5,5,5])
        self.assertEqual(p.bolt_hits,[(0,0,150)])

    def test_one_button_plus_one_weapon33_is_perfect(self):
        c,p=timing(weapons={1:33})
        p.boltx=p.bolts[0].frame-1
        p.button('z')
        self.assertEqual(p.points[0],150)

    def test_one_button_plus_one_without_weapon_gets_120(self):
        c,p=timing()
        p.boltx=p.bolts[0].frame-1
        p.button('z')
        self.assertEqual(p.points[0],120)

    def test_three_button_plus_one_ignores_weapon33_special(self):
        c,p=timing(flags={13:1},weapons={1:33})
        p.boltx=p.bolts[0].frame-1
        p.button('z')
        self.assertEqual(p.points[0],120)
        self.assertEqual(p.pressbuffer[1],5)

    def test_offset_plus_two_is_110(self):
        c,p=timing()
        p.boltx=p.bolts[0].frame-2
        p.button('z')
        self.assertEqual(p.points[0],110)

    def test_offset_plus_14_is_72(self):
        c,p=timing()
        p.boltx=p.bolts[0].frame-14
        p.button('z')
        self.assertEqual(p.points[0],72)

    def test_offset_minus_four_is_92(self):
        c,p=timing()
        p.boltx=p.bolts[0].frame+4
        p.button('z')
        self.assertEqual(p.points[0],92)

    def test_negative_five_and_positive_fifteen_are_excluded(self):
        for difference in (-5,15):
            with self.subTest(offset=difference):
                c,p=timing()
                p.boltx=p.bolts[0].frame-difference
                p.button('z')
                self.assertEqual(p.points[0],0)
                self.assertTrue(p.bolts[0].alive)

    def test_second_button_cannot_score_same_bolt(self):
        c,p=timing()
        p.boltx=p.bolts[0].frame
        p.button('z')
        p.button('z')
        self.assertEqual(p.points[0],150)
        self.assertEqual(len(p.bursts),1)

    def test_one_button_dual_simultaneous_bolts_award_both(self):
        c,p=timing((1,2),(1,1,0))
        p.bolts[0].frame=p.bolts[1].frame=29
        p.boltx=29
        p.button('z')
        self.assertEqual(sum(p.points),300)
        self.assertEqual(len(p.bolt_hits),2)
        self.assertEqual(sorted(p.points[:2]),[150,150])

    def test_three_button_filters_to_the_requested_lane(self):
        c,p=timing((1,2),(1,1,0),flags={13:1})
        p.bolts[0].frame=p.bolts[1].frame=29
        p.boltx=29
        p.button('x')
        self.assertEqual(p.points,[0,150,0])
        self.assertEqual(len(p.bolt_hits),1)

    def test_late_bolt_preferred_over_early_bolt(self):
        c,p=timing((1,2),(1,1,0))
        for b in p.bolts:
            b.party_slot=0
            b.frame=31
        p.bolts[1].frame=28
        p.boltx=30
        p.boltcheck(0)
        self.assertEqual(p.bolt_hits[0],(1,0,110))

    def test_points_pass_through_to_hero_attack_callback(self):
        observed=[]
        c,p=timing()
        c.on_hero_attack=lambda state,actor,slot:observed.append((actor.points,slot))
        p.on_attack_trigger=c.on_hero_attack
        p.boltx=p.bolts[0].frame
        p.button('z')
        p.advance()
        self.assertEqual(observed,[(150,0)])

    def test_noelle_pressbuffer_expands_for_character_id_4(self):
        c,p=timing((1,4),(0,1,0),flags={13:1})
        p.boltx=p.bolts[0].frame
        p.button('x')
        self.assertEqual(p.pressbuffer[4],5)
        self.assertEqual(p.points[1],150)


class SpellTextTests(unittest.TestCase):
    def test_templates_cover_every_regular_case(self):
        for code in (1,2,4,5,6,8,9,10,11,12,13,*range(205,218),*range(222,244),*range(260,271)):
            with self.subTest(code=code):
                self.assertIn(code,SOURCE_TEMPLATES)

    def test_standard_spells_and_ch5_items(self):
        c=make()
        self.assertIn('Susie cast RUDE BUSTER',scr_spelltext(1,1,c.state).messages[0])
        self.assertIn('Kris used the SHIKACOLA',scr_spelltext(270,0,c.state).messages[0])
        self.assertEqual(len(scr_spelltext(217,0,c.state).messages),2)
        self.assertIn('nothing happened',scr_spelltext(217,0,c.state).messages[1])

    def test_case_0_and_unknown_have_no_new_message(self):
        c=make()
        self.assertEqual(scr_spelltext(0,0,c.state).messages,())
        self.assertEqual(scr_spelltext(999,0,c.state).messages,())

    def test_manual_uses_1463_script_for_cases_218_to_221(self):
        c=make()
        for code in (218,219,220,221):
            r=scr_spelltext(code,0,c.state)
            self.assertEqual(r.text_id,1463)
            self.assertIn('scr_text:1463',r.pending_effects)
        r=scr_spelltext(219,0,c.state,on_text_id=lambda *args:'* External script.')
        self.assertEqual(r.messages,('* External script.',))

    def test_pacify_retains_original_target_after_retarget_callback(self):
        c=make()
        c.set_enemy_stats(0,name='Target One',status=0,mercy=100)
        c.set_enemy_stats(1,name='Target Two',status=1)
        c.state.chartarget[0]=0
        calls=[]
        result=scr_spelltext(3,0,c.state,
                             on_retarget=lambda s,slot:(calls.append(slot),s.chartarget.__setitem__(slot,1)))
        self.assertEqual(result.target_slot,0)
        self.assertEqual(calls,[0])
        self.assertIn('try',battle_text_to_display(result.messages[0]))
        self.assertIn('SPARING',battle_text_to_display(result.messages[0]))

    def test_pacify_tired_has_basic_cast_line(self):
        c=make()
        c.set_enemy_stats(0,status=1)
        result=scr_spelltext(3,0,c.state)
        self.assertIn('cast PACIFY!',result.messages[0])
        self.assertNotIn('wasn',result.messages[0])

    def test_spare_unready_target_gives_ralsei_tip(self):
        c=make()
        c.set_enemy_stats(0,name='Target',mercy=30,status=1)
        result=scr_spelltext(100,0,c.state)
        self.assertEqual(len(result.messages),2)
        self.assertIn('MERCY was not',result.messages[0])
        self.assertIn('Ralsei',result.messages[1])

    def test_spare_unready_target_gives_noelle_tip(self):
        c=make((1,4))
        c.set_enemy_stats(0,mercy=30,status=1)
        result=scr_spelltext(100,0,c.state)
        self.assertIn('Noelle',result.messages[1])

    def test_glowshard_writes_mercy_200_and_calls_shift_hook(self):
        c=make()
        foe=c.state.enemies[0]
        foe.monster_type=5
        calls=[]
        c.state.bmenucoord[4][0]=2
        result=scr_spelltext(203,0,c.state,on_item_shift=lambda *args:calls.append(args))
        self.assertEqual(foe.mercy,200)
        self.assertEqual(calls,[(2,0)])
        self.assertEqual(len(result.messages),3)
        self.assertIn('became enraptured',result.messages[1])

    def test_glowshard_without_type_5_does_not_shift_inventory(self):
        c=make()
        calls=[]
        result=scr_spelltext(203,0,c.state,on_item_shift=lambda *args:calls.append(args))
        self.assertEqual(calls,[])
        self.assertIn('nothing happened',result.messages[1])

    def test_manual_tires_type5_and_adds_mercy_to_type7_once(self):
        c=make()
        a,b=c.state.enemies[:2]
        a.monster_type=5
        b.monster_type=7
        calls=[]
        callback=lambda enemy,amount:calls.append((enemy.slot,amount))
        result=scr_spelltext(204,0,c.state,on_mercy_add=callback)
        self.assertEqual(a.status,1)
        self.assertTrue(a.tired)
        self.assertEqual(a.comment,'(Tired)')
        self.assertEqual((b.battlecancel,b.manual),(1,True))
        self.assertEqual(calls,[(1,50)])
        self.assertIn('sentimental',result.messages[1])
        scr_spelltext(204,0,c.state,on_mercy_add=callback)
        self.assertEqual(calls,[(1,50)])

    def test_spellphase_generates_text_and_invokes_writer_callback(self):
        seen=[]
        c=make((1,),on_spell_cast=lambda state,slot,kind:seen.append((slot,kind)) or False)
        c.state.charaction[0]=2
        c.state.charspecial[0]=3
        c.state.chartarget[0]=0
        c.set_enemy_stats(0,status=0,mercy=0)
        c.attack_phase()
        c.update(5)
        self.assertIn('PACIFY',c.state.spell_messages[0])
        self.assertIn('wasn',c.state.spell_messages[0])
        self.assertEqual(seen,[(0,'spell')])
        self.assertEqual(c.state.spell_message_history[0][:2],(0,3))

    def test_spellphase_queued_item_uses_its_registered_code(self):
        c=make((1,))
        c.state.queued[0]=QueuedAction(0,'item',option=CombatOption('Flavigne',code=241))
        c.attack_phase()
        c.update(5)
        self.assertIn('FLAVIGNE',c.state.spell_messages[0])

    def test_hud_display_removes_writer_codes(self):
        raw=r'\* A cast PACIFY^1!&\* The foe was \cBTIRED\cW!/%'
        self.assertEqual(battle_text_to_display(raw),'* A cast PACIFY!\n* The foe was TIRED!')


if __name__=='__main__':
    unittest.main()
