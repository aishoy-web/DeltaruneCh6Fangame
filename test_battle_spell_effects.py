"""Source-driven regression tests: scr_spell + scr_monsterdefeat."""
import unittest
from random import Random
from math import ceil
from battle_combat import BattleCombatController
from battle_monsters import MonsterHooks
from battle_spells import scr_spell
from encounter_setup import setup_encounter


def make(party=(1, 2, 3), flags=None, *, chapter=6, **kw):
    stats = kw.pop('party_stats', {1:{'attack':12, 'magic':9, 'hp':70,'max_hp':100},
                                   2:{'attack':15, 'magic':8, 'hp':70,'max_hp':100},
                                   3:{'attack':3, 'magic':6, 'hp':70,'max_hp':100},
                                   4:{'attack':3, 'magic':10, 'hp':70,'max_hp':100}})
    c = BattleCombatController(setup_encounter(203, party), party,
                               flags if flags is not None else {},
                               chapter=chapter, party_stats=stats, **kw)
    for e in c.state.enemies:
        c.set_enemy_stats(e.slot, hp=200, max_hp=200, defense=4, mercy=0,
                          gold=35+e.slot, exp=5+e.slot, status=0)
    return c


class DefeatScriptTests(unittest.TestCase):
    def test_gold_exp_collected_once_and_flag_violence(self):
        c=make(party=(1,))
        c.state.enemies[0].hp=0
        self.assertTrue(c.defeat_enemy(0))
        self.assertFalse(c.defeat_enemy(0))
        self.assertEqual((c.state.reward_gold,c.state.reward_exp),(35,5))
        self.assertEqual(c.flags[51],1)
        self.assertEqual(c.flags[40],1)
        self.assertTrue(c.state.enemies[1].active)
        c.state.enemies[1].hp=-1
        c.defeat_enemy(1)
        self.assertEqual((c.state.reward_gold,c.state.reward_exp),(71,11))
        self.assertEqual(c.flags[50],1)
        c.win_combat()
        self.assertEqual(c.state.reward_gold,71+0)  # victory reward is separate
        self.assertEqual(c.state.reward_exp,11)
        self.assertEqual(c.state.xp,11)

    def test_defeat_counters_and_priority_overrides(self):
        for code, counter in ((1,40),(2,41),(3,42),(5,43),(6,45)):
            with self.subTest(code=code):
                c=make(party=(1,))
                c.defeat_enemy(0,outcome=code)
                self.assertEqual(c.flags.get(counter,0),1)
                if code == 6:
                    self.assertEqual(c.state.reward_gold,59)
                else:
                    self.assertEqual(c.state.reward_gold,35)
        c=make(party=(1,))
        c.defeat_enemy(0,outcome=6)
        c.defeat_enemy(1,outcome=3)
        self.assertEqual(c.flags[50],3)
        c=make(party=(1,))
        c.defeat_enemy(0,outcome=1)
        c.defeat_enemy(1,outcome=6)
        self.assertEqual(c.flags[50],1)

    def test_final_frozen_flag_and_encounter_flag_recorder(self):
        c=make(flags={54:1001}, party=(1,))
        c.defeat_enemy(0,outcome=6)
        c.defeat_enemy(1,outcome=6)
        self.assertEqual(c.flags[50],6)
        self.assertEqual(c.flags[926],1)
        self.assertEqual(c.flags[1001],6)
        self.assertEqual(c.flags[54],0)
        self.assertEqual(c.flags[45],2)
        self.assertEqual(c.state.reward_gold,35+36+48)

    def test_fatal_counter(self):
        c=make(party=(1,))
        c.state.enemies[0].fatal=1
        c.defeat_enemy(0,outcome=1)
        self.assertEqual(c.flags[44],1)

    def test_user10_then_user11_then_legacy_defeat_hook(self):
        calls=[]
        h=MonsterHooks(event_user_10=lambda e:calls.append((e.slot,10)),
                       event_user_11=lambda e:calls.append((e.slot,11)),
                       monster_defeat=lambda e:calls.append((e.slot,'defeat')))
        c=make(party=(1,), monster_hooks={'*':h})
        c.defeat_enemy(0,outcome=2,call_user10=True)
        self.assertEqual(calls,[(0,10),(0,11),(0,'defeat')])

    def test_wincombat_collects_survivor_rewards_before_victory(self):
        c=make(party=(1,))
        c.state.tension=0
        c.win_combat()
        self.assertEqual(c.state.phase,'victory')
        self.assertEqual(c.state.xp,11)
        self.assertEqual(c.state.reward_gold,71)
        self.assertEqual(c.state.gold,71)
        self.assertEqual(c.flags[41],2)
        self.assertEqual(c.flags[50],2)


class SpellEffectTests(unittest.TestCase):
    def test_rudebuster_initial_damage_and_lethal_defeat(self):
        c=make(party=(1,))
        c.state.chartarget[0]=0
        outcome=scr_spell(c,1,0)
        self.assertEqual(outcome.direct_damage,108)
        self.assertEqual(outcome.spell_delay,30)
        self.assertEqual(c.state.enemies[0].hp,92)
        self.assertEqual(outcome.animations[0].object_name,'obj_basicattack')
        c.state.enemies[0].hp=20
        scr_spell(c,1,0)
        self.assertFalse(c.state.enemies[0].active)
        self.assertEqual(c.flags[40],1)
        self.assertEqual(c.state.reward_gold,35)

    def test_unknown_stats_do_not_create_damage(self):
        c=make(party=(1,))
        c.set_enemy_stats(0, defense=4)
        c.state.battleat[0]=None
        result=scr_spell(c,1,0)
        self.assertIsNone(result.direct_damage)
        self.assertIn('scr_damage_enemy:unknown_attack_or_defense',result.unresolved)
        self.assertEqual(c.state.enemies[0].hp,200)

    def test_rudebuster_anim_deferred_with_armor_modifier(self):
        req=[]
        c=make(party=(1,2), equipped_armors={2:(36,)},
               on_spell_animation=lambda s,r:req.append(r))
        c.state.chartarget[1]=0
        result=scr_spell(c,4,1)
        self.assertEqual(result.spell_delay,70)
        self.assertEqual(result.animations[0].object_name,'obj_rudebuster_anim')
        self.assertEqual(result.animations[0].damage,
                         ceil(8*5.5+15*12-4*3))
        self.assertEqual(c.state.enemies[0].hp,200)  # animated damage not applied
        self.assertEqual(req,result.animations and list(result.animations))
        result=scr_spell(c,5,1)
        self.assertEqual(result.animations[0].damage,ceil(8*6+15*13-4*6))

    def test_prayer_dualheal_and_item_heals(self):
        c=make(party=(1,2,3))
        c.state.actors[0].hp=10
        c.state.chartarget[2]=0
        result=scr_spell(c,2,2)
        self.assertEqual(result.heals,((0,30),))
        self.assertEqual(c.state.actors[0].hp,40)
        result=scr_spell(c,6,2)
        self.assertEqual(result.heals,((0,33),(1,33),(2,33)))
        self.assertEqual(c.state.actors[0].hp,73)
        self.assertEqual(result.spell_delay,15)
        result=scr_spell(c,211,2)
        self.assertEqual(len(result.heals),3)
        self.assertEqual(c.state.actors[0].hp,100)

    def test_pacify_and_spare_defeat_with_flags(self):
        c=make(party=(1,2,3))
        c.state.enemies[0].status=1
        c.state.chartarget[2]=0
        result=scr_spell(c,3,2)
        self.assertFalse(c.state.enemies[0].active)
        self.assertEqual(c.flags[51],3)
        self.assertEqual(c.flags[42],1)
        self.assertEqual(result.animations[0].object_name,'obj_pacifyspell')
        c.state.enemies[1].mercy=100
        c.state.chartarget[0]=1
        result=scr_spell(c,100,0)
        self.assertFalse(c.state.enemies[1].active)
        self.assertEqual(c.flags[52],2)
        self.assertEqual(c.flags[50],2)  # SPARE wins over PACIFY in source
        self.assertEqual(result.spell_delay,0)

    def test_spare_fail_increases_mercy_but_does_not_defeat(self):
        c=make(party=(1,))
        e=c.state.enemies[0]; e.mercy=60;e.spare_point=10
        c.state.chartarget[0]=0
        r=scr_spell(c,100,0)
        self.assertTrue(e.active)
        self.assertEqual(e.mercy,70)
        self.assertEqual(r.animations[0].object_name,'obj_pacifyspell')

    def test_pacify_exception_monster_not_defeated(self):
        c=make(party=(1,))
        e=c.state.enemies[0];e.monster_type=52;e.status=1
        c.state.chartarget[0]=0
        r=scr_spell(c,3,0)
        self.assertTrue(e.active)
        self.assertEqual(e.pacifycon,1)
        self.assertEqual(r.spell_delay,20)
        self.assertTrue(any(rq.object_name=='obj_pacifyspell' for rq in r.animations))
        e.mercy=100
        r=scr_spell(c,100,0)
        self.assertEqual(e.sparecon,1)
        self.assertTrue(e.active)

    def test_snowgrave_iceshock_and_mist_are_deferred(self):
        c=make(party=(1,4),spell_rng=Random(42))
        c.state.chartarget[1]=0
        r=scr_spell(c,9,1)
        self.assertEqual(c.flags[925],1)
        self.assertEqual(r.animations[0].object_name,'obj_icespell')
        self.assertEqual(r.spell_delay,40)
        self.assertEqual(c.state.enemies[0].hp,200)
        r=scr_spell(c,10,1)
        self.assertEqual(r.spell_delay,140)
        self.assertEqual(r.animations[0].damage,1000)
        r=scr_spell(c,8,1)
        self.assertEqual([req.delay for req in r.animations],[0,10])
        self.assertEqual(r.spell_delay,40)
        r=scr_spell(c,13,1)
        self.assertEqual([req.delay for req in r.animations],[0,10])
        self.assertEqual(r.spell_delay,84)
        self.assertEqual(c.state.enemies[1].hp,200)

    def test_revivesong_is_deferred_healing(self):
        c=make(party=(1,2,3))
        c.state.actors[0].hp=-20
        c.state.chartarget[2]=0
        r=scr_spell(c,12,2)
        self.assertEqual(r.spell_delay,75)
        self.assertEqual(r.animations[0].heal,65)
        self.assertEqual(c.state.actors[0].hp,-20)

    def test_items_202_230_231_revive_negative_hp(self):
        c=make(party=(1,2,3))
        c.state.chartarget[0]=1
        c.state.actors[1].hp=-10
        r=scr_spell(c,202,0)
        self.assertEqual(r.heals,((1,110),))
        self.assertEqual(c.state.actors[1].hp,100)
        c.state.actors[0].hp=-30
        r=scr_spell(c,230,0)
        self.assertEqual(c.state.actors[0].hp,25)
        self.assertEqual(len(r.heals),3)
        c.state.actors[0].hp=-30
        r=scr_spell(c,231,0)
        self.assertEqual(c.state.actors[0].hp,100)

    def test_item_232_poison_and_heal(self):
        c=make(party=(1,))
        c.state.chartarget[0]=0
        r=scr_spell(c,232,0)
        self.assertEqual(c.state.actors[0].hp,100)
        self.assertEqual(c.state.actors[0].hero_animation.poisonamount,60)
        c.update(10)
        self.assertEqual(c.state.actors[0].hp,99)

    def test_character_specific_item_healing(self):
        c=make(party=(1,2,4))
        c.state.chartarget[0]=2
        self.assertEqual(scr_spell(c,212,0).heals,((2,30),))
        self.assertEqual(scr_spell(c,260,0).heals,((2,40),))
        c.state.chartarget[0]=0
        self.assertEqual(scr_spell(c,260,0).heals,((0,400),))
        c.state.chartarget[0]=2
        r=scr_spell(c,262,0)
        self.assertEqual(r.heals,((2,155),(0,5)))

    def test_heal_mod_callback_applied(self):
        c=make(party=(1,),on_spell_heal_modifier=lambda amount,s,slot:amount*1.2)
        r=scr_spell(c,201,0)
        self.assertEqual(r.heals,((0,144),))

    def test_heal_spell_11_flag_and_magic_slot_one(self):
        c=make(party=(1,2),flags={1045:14})
        c.state.chartarget[1]=0
        c.state.actors[0].hp=1
        r=scr_spell(c,11,1)
        self.assertEqual(c.flags[20],1)
        self.assertEqual(c.flags[1045],15)
        self.assertEqual(r.heals,((0,85),))
        self.assertEqual(r.spell_delay,15)

    def test_missing_spell_ids_are_noop_except_delay(self):
        c=make(party=(1,))
        for code in (0,200,203,204,217,227,228,229,233,235,500):
            with self.subTest(code=code):
                r=scr_spell(c,code,0)
                self.assertFalse(r.heals)
                self.assertFalse(r.animations)
                self.assertIsNone(r.direct_damage)
                self.assertEqual(r.spell_delay,10)

    def test_hero_16_frame_cast_invokes_builtin_scr_spell(self):
        c=make(party=(1,))
        c.state.charaction[0]=2
        c.state.charspecial[0]=2
        c.state.chartarget[0]=0
        c.state.actors[0].hp=10
        c.attack_phase()
        c.update(20)
        self.assertEqual(c.state.hero_spell_events,[(0,2)])
        self.assertEqual(c.state.actors[0].hp,55)
        self.assertEqual(c.state.spell_effect_outcomes[-1].heals,((0,45),))

if __name__=='__main__':
    unittest.main()
