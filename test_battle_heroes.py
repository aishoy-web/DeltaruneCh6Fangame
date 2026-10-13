"""Tests for recovered obj_heroparent Create, Step, and Draw pose data."""
import unittest
from battle_combat import BattleCombatController
from battle_heroes import calculate_attack_damage, hero_profile
from battle_monsters import MonsterHooks
from encounter_setup import setup_encounter


def make(party=(1,), *, stats=None, hooks=None, **kw):
    return BattleCombatController(setup_encounter(203, party_ids=party), party, {},
                                  party_stats=stats or {}, monster_hooks=hooks or {}, **kw)


class HeroCreateTests(unittest.TestCase):
    def test_four_char_profiles_and_dimensions(self):
        cases={1:(6,6,5,10,68,74), 2:(5,5,5,8,70,82),
               3:(6,6,7,10,52,86), 4:(4,9,0,6,52,86)}
        for cid, expected in cases.items():
            with self.subTest(cid=cid):
                p=hero_profile(cid)
                self.assertEqual((p.attackframes,p.itemframes,p.defendframes,
                                  p.spellframes,p.width,p.height),expected)
                self.assertTrue(p.sprites['idle'].startswith('spr_'))
                self.assertEqual(p.victoryframes,None)

    def test_unarmed_susie_ch5_225_and_hooded_ralsei(self):
        p=hero_profile(2,weapon=0)
        self.assertEqual(p.sprites['attack'],'spr_susieb_attack_unarmed')
        p=hero_profile(2,chapter=5,encounter_no=225,weapon=0)
        self.assertEqual(p.sprites['idle'],'spr_susieb_idle_unarmed_unhappy')
        p=hero_profile(3,chapter=5,flag_1311=True)
        self.assertEqual(p.attackframes,5)
        self.assertEqual(p.sprites['attack'],'spr_ralseib_attack')
        self.assertEqual(hero_profile(4,encounter_no=73).sprites['idle'],
                         'spr_noelle_shocked_dw')

    def test_victory_frame_count_requires_supplied_sprite_metadata(self):
        p=hero_profile(1,sprite_frame_counts={'spr_krisb_victory':12})
        self.assertEqual(p.victoryframes,12)


class HeroDamageTests(unittest.TestCase):
    def test_damage_formula_modifiers_and_min_zero(self):
        self.assertEqual(calculate_attack_damage(12,150,5,73),75)
        self.assertEqual(calculate_attack_damage(12,150,5,19),23)
        self.assertEqual(calculate_attack_damage(12,150,5,73,trashy_trio_present=True),8)
        self.assertEqual(calculate_attack_damage(12,0,5,73),0)
        self.assertIsNone(calculate_attack_damage(None,150,5,73))
        self.assertIsNone(calculate_attack_damage(12,150,None,73))

    def _timed_hit(self, *, attack=12, defense=5, hp=500, points=150, target=0, **kw):
        c=make(stats={1:{'attack':attack,'hp':100,'max_hp':100}},**kw)
        if defense is not None or hp is not None:
            c.set_enemy_stats(target, hp=hp, defense=defense, max_hp=hp)
        s=c.state
        s.charaction[0]=1
        s.chartarget[0]=target
        c.attack_phase()
        phase=c.attack_press
        assert phase is not None
        phase.points[0]=points
        # Other[11] starts hero attack; the hero Step owns the delayed damage.
        phase.attacked[0] = 1
        phase._trigger(0)
        return c

    def test_hit_is_delayed_11_hero_steps_and_tp_gains(self):
        c=self._timed_hit()
        enemy=c.state.enemies[0]
        c.update(10)
        self.assertEqual(enemy.hp,500)
        self.assertEqual(c.state.hero_attack_events,[])
        c.update(1)
        self.assertEqual(enemy.hp,425)
        self.assertEqual(c.state.tension,15)
        self.assertEqual(c.state.hittarget[0],1)
        self.assertEqual(c.state.hero_attack_events[0].damage,75)
        self.assertEqual(c.state.faceaction[0],0)
        c.update(20)
        self.assertEqual(enemy.hp,425)
        self.assertEqual(len(c.state.hero_attack_events),1)

    def test_zero_score_does_zero_damage_and_no_tp(self):
        c=self._timed_hit(points=0)
        c.update(11)
        self.assertEqual(c.state.enemies[0].hp,500)
        self.assertEqual(c.state.hero_attack_events[0].damage,0)
        self.assertEqual(c.state.tension,0)

    def test_zero_attack_or_unknown_defense_does_not_fabricate_damage(self):
        c=self._timed_hit(attack=None)
        c.update(11)
        self.assertEqual(c.state.enemies[0].hp,500)
        self.assertFalse(c.state.hero_attack_events[-1].resolved)
        self.assertIsNone(c.state.hero_attack_events[-1].damage)
        c2=self._timed_hit(defense=None)
        c2.update(11)
        self.assertFalse(c2.state.hero_attack_events[-1].resolved)

    def test_unknown_enemy_hp_prevents_mutation(self):
        c=self._timed_hit(hp=None)
        c.update(11)
        hit=c.state.hero_attack_events[-1]
        self.assertIsNone(c.state.enemies[0].hp)
        self.assertFalse(hit.resolved)
        self.assertEqual(hit.damage,75)

    def test_lethal_hit_deactivates_enemy_and_calls_defeat(self):
        calls=[]
        hooks={'*':MonsterHooks(monster_defeat=lambda e:calls.append(('defeat',e.slot)),
                                on_damage=lambda e,a,d:calls.append(('damage',d)))}
        c=self._timed_hit(hp=50,hooks=hooks)
        c.update(11)
        self.assertFalse(c.state.enemies[0].active)
        self.assertEqual(c.state.enemies[0].hp,-25)
        self.assertEqual(c.state.hero_attack_events[-1].defeated,True)
        self.assertEqual(calls,[('damage',75),('defeat',0)])

    def test_susie_weapon54_heals_before_hit_via_basic_heal_adapter(self):
        c=make(party=(1,2), stats={1:{'attack':3},
                                   2:{'attack':8,'hp':20,'max_hp':80}},
               equipped_weapons={2:54})
        c.set_enemy_stats(0, hp=1000, defense=0)
        c.state.charaction[:] = [0,1,0]
        c.attack_phase()
        c.attack_press.attacked[1] = 1
        c.attack_press.points[1] = 150
        c.attack_press._trigger(1)
        c.update(11)
        self.assertEqual(c.state.actors[1].hp,28)
        self.assertEqual(c.state.enemies[0].hp,940)

    def test_invalid_target_requires_retarget_hook(self):
        c=self._timed_hit(target=0)
        c.state.enemies[0].active=False
        c.update(11)
        self.assertIsNone(c.state.hero_attack_events[-1].damage)
        self.assertFalse(c.state.hero_attack_events[-1].resolved)
        c=self._timed_hit(on_hero_retarget=lambda s,a,t:1)
        c.set_enemy_stats(1,hp=200,defense=5)
        c.state.enemies[0].active=False
        c.update(11)
        self.assertEqual(c.state.enemies[1].hp,125)
        self.assertEqual(c.state.chartarget[0],1)

    def test_multiple_party_attacks_resolve_once_per_actor(self):
        c=make(party=(1,2),stats={1:{'attack':10},2:{'attack':8}})
        c.set_enemy_stats(0,hp=500,defense=0)
        c.state.charaction[:]=[1,1,0]
        c.state.chartarget[:]=[0,0,0]
        c.attack_phase()
        c.attack_press.points=[150,120,0]
        c.attack_press.attacked[:2] = [1, 1]
        c.attack_press._trigger(0)
        c.attack_press._trigger(1)
        c.update(11)
        self.assertEqual(c.state.enemies[0].hp,500-75-48)
        self.assertEqual(len(c.state.hero_attack_events),2)
        self.assertEqual(c.state.hittarget[0],2)

    def test_auto_susie_kill_sets_flag_on_target(self):
        c=self._timed_hit(hp=50)
        actor=c.state.actors[0]
        actor.is_auto_susie=True
        c.update(11)
        self.assertEqual(c.flags[51],5)

    def test_poison_tick_preserves_at_least_one_hp(self):
        c=make(stats={1:{'hp':3,'max_hp':10}})
        animation=c.state.actors[0].hero_animation
        animation.poisonamount=5
        c.update(30)
        self.assertEqual(c.state.actors[0].hp,1)
        self.assertEqual(animation.poisonamount,0)

    def test_defend_idle_pose_and_animation_timer(self):
        c=make()
        actor=c.state.actors[0]
        c.state.faceaction[0]=4
        c.update(10)
        animation=actor.hero_animation
        self.assertEqual(animation.thissprite,'spr_krisb_defend')
        self.assertEqual(animation.defendtimer,5)
        c.state.faceaction[0]=0
        c.update(1)
        self.assertEqual(animation.defendtimer,0)


class HeroSpellTests(unittest.TestCase):
    def test_spell_effect_16_frames_after_first_cast(self):
        called=[]
        c=make(on_spell_effect=lambda s,a,spell:called.append((a.slot,spell)))
        c.state.charspecial[0]=9
        c.state.charaction[0]=2
        c.attack_phase()
        c.update(5)
        self.assertEqual(c.spell_phase.cast_history,[(0,'spell')])
        self.assertEqual(c.state.hero_spell_events,[])
        c.update(14)
        self.assertEqual(c.state.hero_spell_events,[])
        c.update(1)
        self.assertEqual(c.state.hero_spell_events,[(0,9)])
        self.assertEqual(called,[(0,9)])
        self.assertEqual(c.state.actors[0].state,0)
        c.update(17)
        self.assertEqual(called,[(0,9)])

    def test_item_use_starts_item_sprite_before_effect_callback(self):
        c=make()
        c.state.charaction[0]=4
        c.state.charspecial[0]=205
        c.attack_phase()
        c.update(5)
        self.assertEqual(c.state.actors[0].hero_animation.thissprite,'spr_krisb_item')
        c.update(16)
        self.assertEqual(c.state.hero_spell_events,[(0,205)])
        self.assertEqual(c.state.actors[0].state,0)

if __name__=='__main__':
    unittest.main()
