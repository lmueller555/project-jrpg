"""Approved future growth can enter the existing combat/attribute boundaries."""
from copy import deepcopy
import json
import unittest

from battle_model import BattleModel, ENEMY_PATH
from character_attributes import CharacterAttributes
from combat_damage import NORMAL_DAMAGE_CAP
from enemy_growth import STAT_PROFILE_IDS, baseline_enemy_stats, profile_enemy_stats
from leveling import character_ids, character_stats


class FixedVariance:
    def randint(self, low, high):
        assert (low, high) == (95, 105)
        return 100


def attributes_at_level(identifier, level):
    catalog = deepcopy(CharacterAttributes().catalog)
    catalog['characters'] = {
        key: {'name': key.title(), 'attributes': character_stats(key, level)}
        for key in character_ids()}
    return CharacterAttributes(identifier, catalog)


def enemy_at_level(level):
    catalog = json.loads(ENEMY_PATH.read_text())
    catalog['enemies']['bat']['attributes'] = baseline_enemy_stats(level)
    return catalog


class LevelingCombatIntegrationTests(unittest.TestCase):
    def test_all_named_profiles_enter_the_real_enemy_validator(self):
        for level in (1, 50, 100):
            source = attributes_at_level('caelan', level)
            for profile in STAT_PROFILE_IDS:
                with self.subTest(level=level, profile=profile):
                    expected = profile_enemy_stats(profile, level)
                    catalog = enemy_at_level(level)
                    catalog['enemies']['bat']['attributes'] = expected
                    model = BattleModel(source, enemy_data=catalog, rng=FixedVariance())
                    self.assertEqual(model.enemy.attributes, expected)

    def test_defensive_profiles_affect_real_attack_resolution(self):
        for profile, action, expected_damage in (
                ('armored', 'attack', 2800), ('armored', 'aether_dart', 9999),
                ('warded', 'attack', 5463), ('warded', 'aether_dart', 5560)):
            with self.subTest(profile=profile, action=action):
                source = attributes_at_level('caelan', 100)
                catalog = enemy_at_level(100)
                expected = profile_enemy_stats(profile, 100)
                catalog['enemies']['bat']['attributes'] = expected
                model = BattleModel(source, learned_abilities=['aether_dart'],
                                    enemy_data=catalog, rng=FixedVariance())
                model.player.atb = 1
                model.update(0)
                self.assertTrue(model.choose_action(action))
                model.update(model.current_action.impact_at)
                self.assertEqual(model.current_action.damage, expected_damage)
                self.assertEqual(model.enemy.hp, expected['hp']-expected_damage)

    def test_every_growth_profile_round_trips_through_real_attributes(self):
        for identifier in character_ids():
            for level in (1, 25, 50, 75, 100):
                with self.subTest(character=identifier, level=level):
                    source = attributes_at_level(identifier, level)
                    self.assertEqual(source.to_dict()['attributes'],
                                     character_stats(identifier, level))
                    self.assertTrue(source.set_current(hp=0, mp=0))
                    clone = attributes_at_level(identifier, 1)
                    self.assertTrue(clone.restore(source.to_dict()))
                    self.assertEqual(clone.to_dict(), source.to_dict())

    def test_generated_three_member_formations_enter_real_battle(self):
        for level in (1, 25, 50, 100):
            for companions in (('mira', 'lucan'), ('rhea', 'edran')):
                with self.subTest(level=level, companions=companions):
                    source = attributes_at_level('caelan', level)
                    identifiers = ('caelan', *companions)
                    party = []
                    for identifier in identifiers:
                        stats = character_stats(identifier, level)
                        party.append({
                            'identifier': 'player' if identifier == 'caelan' else identifier,
                            'name': identifier.title(), 'attributes': stats,
                            'hp': stats['hp'], 'mp': stats['mp'],
                            'attack': 'bolt_shot' if identifier == 'mira' else 'attack'})
                    model = BattleModel(source, party_members=party, bot_loadouts={},
                                        enemy_data=enemy_at_level(level), rng=FixedVariance())
                    self.assertEqual(model.enemy.attributes, baseline_enemy_stats(level))
                    self.assertEqual(len(model.party), 3)
                    for member, identifier in zip(model.party, identifiers):
                        self.assertEqual(member.attributes, character_stats(identifier, level))

    def test_endgame_spell_resolves_against_fifty_thousand_hp(self):
        source = attributes_at_level('caelan', 100)
        before = source.to_dict()
        model = BattleModel(source, learned_abilities=['aether_dart'],
                            enemy_data=enemy_at_level(100), rng=FixedVariance())
        model.player.atb = 1
        model.update(0)
        self.assertTrue(model.choose_action('aether_dart'))
        model.update(model.current_action.impact_at)
        self.assertEqual(model.current_action.damage, 8041)
        self.assertEqual(model.enemy.hp, 50000-8041)
        self.assertEqual(model.player.mp, 396)
        self.assertEqual(source.to_dict(), before)

    def test_modifier_headroom_works_with_existing_damage_cap(self):
        source = attributes_at_level('caelan', 100)
        self.assertTrue(source.set_modifiers('preview_equipment', {'mag': 999}))
        self.assertEqual(source.value('mag'), 999)
        model = BattleModel(source, learned_abilities=['aether_dart'],
                            enemy_data=enemy_at_level(100), rng=FixedVariance())
        model.player.atb = 1
        model.update(0)
        self.assertTrue(model.choose_action('aether_dart'))
        model.update(model.current_action.impact_at)
        self.assertEqual(model.current_action.damage, NORMAL_DAMAGE_CAP)
        self.assertEqual(model.enemy.hp, 50000-NORMAL_DAMAGE_CAP)


if __name__ == '__main__':
    unittest.main()
