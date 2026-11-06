"""Weapon skill gating and single-hit physical/magical Aether Edge damage."""
from copy import deepcopy
import json
import unittest

from battle_model import ACTION_PATH, ENEMY_PATH, BattleModel, load_actions
from character_attributes import CharacterAttributes
from combat_damage import magical_damage, physical_damage


class FixedVariance:
    def __init__(self, percent=100):
        self.percent = percent
        self.calls = 0

    def randint(self, low, high):
        assert (low, high) == (95, 105)
        self.calls += 1
        return self.percent


def attributes(**values):
    result = CharacterAttributes()
    record = result.to_dict()
    record['attributes'].update(values)
    record['current_hp'] = record['attributes']['hp']
    record['current_mp'] = record['attributes']['mp']
    assert result.restore(record)
    return result


class AetherEdgeBattleModelTests(unittest.TestCase):
    def model(self, source=None, **options):
        enemies = json.loads(ENEMY_PATH.read_text())
        enemies['enemies']['bat']['attributes'].update(hp=1000000, speed=0)
        options.setdefault('enemy_data', enemies)
        options.setdefault('learned_abilities', ['aether_edge'])
        options.setdefault('weapon_equipped', True)
        options.setdefault('rng', FixedVariance())
        return BattleModel(source or attributes(), **options)

    def ready(self, model):
        model.update(1000)
        self.assertTrue(model.waiting_for_player)

    def take_turn(self, model, action):
        self.ready(model)
        self.assertTrue(model.choose_action(action))
        record = model.current_action
        model.update(record.duration)
        return record

    def test_commands_separate_skills_from_executable_actions_and_keep_dart(self):
        model = self.model(learned_abilities=['aether_edge', 'aether_dart', 'focused_strike'])
        self.assertEqual(model.command_actions(), ['attack', 'skills', 'guard', 'flee', 'aether_dart'])
        self.assertEqual(model.skill_actions(), ['aether_edge'])
        self.assertEqual(model.available_actions(), ['attack', 'guard', 'flee', 'aether_dart', 'aether_edge'])
        self.assertNotIn('skills', model.available_actions())
        self.ready(model)
        self.assertEqual(model.command_reason('skills'), '')
        self.assertFalse(model.choose_action('skills'))
        self.assertTrue(model.choose_action('aether_dart'))

    def test_skill_command_reports_readiness_weapon_and_no_skills_in_order(self):
        model = self.model(learned_abilities=[], weapon_equipped=False)
        self.assertEqual(model.available_actions(), ['attack', 'guard', 'flee'])
        self.assertIn('not ready', model.command_reason('skills'))
        self.ready(model)
        self.assertEqual(model.command_reason('skills'), 'Requires a weapon.')
        armed = self.model(learned_abilities=[])
        self.ready(armed)
        self.assertEqual(armed.command_reason('skills'), 'No skills learned.')

    def test_known_edge_requires_weapon_ready_turn_and_four_mp_without_mutation(self):
        for known, armed, mp, reason in ((False, True, 30, 'not available'),
                                        (True, False, 30, 'Requires a weapon.'),
                                        (True, True, 3, 'Not enough MP.')):
            with self.subTest(known=known, armed=armed, mp=mp):
                source = attributes()
                self.assertTrue(source.set_current(mp=mp))
                model = self.model(source, learned_abilities=['aether_edge'] if known else [],
                                   weapon_equipped=armed)
                self.ready(model)
                before = (model.player.mp, model.player.atb, deepcopy(model.events))
                self.assertIn(reason, model.action_reason('aether_edge'))
                self.assertFalse(model.choose_action('aether_edge'))
                self.assertEqual((model.player.mp, model.player.atb, model.events), before)
                self.assertEqual(model.player.aether_edge_hits, 0)
        model = self.model()
        self.assertIn('not ready', model.action_reason('aether_edge'))
        self.assertFalse(model.choose_action('aether_edge'))

    def test_strike_spends_one_atb_and_four_mp_with_one_delayed_combined_impact(self):
        source=attributes();before=source.to_dict();model=self.model(source)
        self.ready(model);enemy_atb=model.enemy.atb
        self.assertTrue(model.choose_action('aether_edge'))
        self.assertEqual((model.player.mp,model.player.atb),(26,0))
        self.assertEqual((model.current_action.kind,model.current_action.target,
                          model.current_action.animation),('spellblade','enemy','attack'))
        model.update(.499)
        self.assertEqual(model.enemy.hp,1000000)
        self.assertEqual(model.enemy.atb,enemy_atb)
        model.update(.001)
        expected=physical_damage(model.player,model.enemy)+magical_damage(model.player,model.enemy,.5)
        self.assertEqual(model.current_action.damage,expected)
        self.assertEqual(model.enemy.hp,1000000-expected)
        self.assertEqual(model.rng.calls,1)
        self.assertEqual(model.player.aether_edge_hits,0)
        model.update(.1)
        impacts=[e for e in model.events if e['type']=='impact' and e['actor']=='player']
        self.assertEqual(len(impacts),1)
        self.assertEqual(source.to_dict(),before)

    def test_following_ordinary_attacks_receive_no_lingering_bonus(self):
        model=self.model();edge=self.take_turn(model,'aether_edge')
        normal=self.take_turn(model,'attack')
        self.assertEqual(normal.damage,physical_damage(model.player,model.enemy))
        self.assertGreater(edge.damage,normal.damage)
        self.assertEqual(model.player.aether_edge_hits,0)
        second=self.take_turn(model,'aether_edge')
        self.assertEqual(second.damage,edge.damage)
        self.assertEqual(model.player.mp,22)

    def test_mag_improves_only_the_magical_component_with_one_variance_roll(self):
        damages=[]
        for mag in (5,40):
            model=self.model(attributes(mag=mag),rng=FixedVariance(95))
            self.ready(model);calls=model.rng.calls
            self.assertTrue(model.choose_action('aether_edge'));model.update(.5)
            self.assertEqual(model.rng.calls,calls+1)
            expected=(physical_damage(model.player,model.enemy,variance_percent=95)+
                      magical_damage(model.player,model.enemy,.5,variance_percent=95))
            self.assertEqual(model.current_action.damage,expected)
            damages.append(model.current_action.damage)
        self.assertGreater(damages[1],damages[0])

    def test_guard_reduces_both_components_and_the_sum_uses_one_shared_cap(self):
        model=self.model(attributes(str=25,mag=30));model.enemy.guarded=True
        action=self.take_turn(model,'aether_edge')
        expected=(physical_damage(model.player,model.enemy,protected=True)+
                  magical_damage(model.player,model.enemy,.5,protected=True))
        self.assertEqual(action.damage,expected);self.assertFalse(model.enemy.guarded)
        impact=next(e for e in model.events if e['type']=='impact' and e['actor']=='player')
        self.assertTrue(impact['guarded'])
        capped=self.model(attributes(str=220,mag=220))
        action=self.take_turn(capped,'aether_edge')
        self.assertLess(physical_damage(capped.player,capped.enemy),9999)
        self.assertLess(magical_damage(capped.player,capped.enemy,.5),9999)
        self.assertEqual(action.damage,9999)
        self.assertEqual(capped.enemy.hp,1000000-9999)

    def test_guest_cannot_use_caelans_weapon_skill(self):
        model=self.model(guest_id='mira')
        model.player.atb=model.combatant('mira').atb=1;model.update(0)
        self.assertTrue(model.choose_action('aether_edge',actor_id='player'));model.update(.9)
        self.assertEqual(model.ready_actor,'mira')
        self.assertEqual(model.skill_actions(),['overclock'])
        self.assertNotIn('aether_edge',model.available_actions())
        self.assertFalse(model.choose_action('aether_edge'))
        self.assertTrue(model.choose_action('attack'));model.update(.4)
        self.assertEqual(model.current_action.damage,
                         physical_damage(model.combatant('mira'),model.enemy,.75))
        self.assertEqual(model.combatant('mira').mp,30)

    def test_spellblade_schema_validates_its_bonus_and_rejects_retired_hit_charges(self):
        original=json.loads(ACTION_PATH.read_text());parsed=load_actions(original)
        self.assertEqual(parsed['aether_edge']['magical_potency'],.5)
        parsed['aether_edge']['magical_potency']=1
        self.assertEqual(original['actions']['aether_edge']['magical_potency'],.5)
        for field,value in (('magical_potency',0),('magical_potency',True),
                            ('magical_potency',float('nan')),('potency',0),
                            ('target','self'),('weapon_hits',3),('element','fire')):
            with self.subTest(field=field,value=value):
                bad=deepcopy(original);bad['actions']['aether_edge'][field]=value
                with self.assertRaises(ValueError):load_actions(bad)
        bad=deepcopy(original);del bad['actions']['aether_edge']['magical_potency']
        with self.assertRaises(ValueError):load_actions(bad)
        bad=deepcopy(original);bad['actions']['attack']['magical_potency']=.5
        with self.assertRaises(ValueError):load_actions(bad)


if __name__ == '__main__':unittest.main()
