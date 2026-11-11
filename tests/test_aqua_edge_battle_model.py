"""A free cave lesson encounter unlocks a persistent Water-aligned strike."""
from copy import deepcopy
from fractions import Fraction
import json
import random
import unittest

from battle_model import BattleModel, ENEMY_PATH
from character_attributes import CharacterAttributes
from combat_damage import magical_damage, physical_damage
from test_aether_edge_battle_model import FixedVariance, attributes
from test_vespermaw_live_model import profiles


BATS = [{'enemy_id': 'cave_bat', 'level': 2}, {'enemy_id': 'cave_bat', 'level': 2}]


class AquaEdgeBattleModelTests(unittest.TestCase):
    def model(self, mp=0, **options):
        source = attributes()
        source.set_current(mp=mp)
        options.setdefault('weapon_equipped', True)
        options.setdefault('owned_gems', ('water',))
        options.setdefault('learned_abilities', ['aether_edge'])
        options.setdefault('guest_id', 'mira')
        options.setdefault('rng', FixedVariance())
        options.setdefault('initial_atb_seed', 27)
        options.setdefault('aqua_edge_tutorial', True)
        return BattleModel.from_bestiary_group(source, BATS, **options)

    def ready(self, model):
        model.update(1000)
        self.assertTrue(model.waiting_for_player)
        self.assertEqual(model.ready_actor, 'player')

    def test_zero_mp_lesson_holds_companions_and_bats_until_success(self):
        model = self.model()
        self.assertEqual(len(model.enemies), 2)
        self.assertTrue(all(0 <= value <= .5 for value in model.initial_atb_values.values()))
        before = [(actor.identifier, actor.hp, actor.atb) for actor in (*model.party[1:], *model.enemies)]
        self.ready(model)
        self.assertEqual(before, [(actor.identifier, actor.hp, actor.atb)
                                  for actor in (*model.party[1:], *model.enemies)])
        self.assertEqual(model.skill_actions(), ['aqua_edge'])
        self.assertEqual(model.action_mp_cost('aqua_edge'), 0)
        self.assertEqual(model.command_reason('skills'), '')
        self.assertFalse(model.select_ready('mira'))
        for identifier in ('attack', 'guard', 'flee', 'aether_edge'):
            self.assertFalse(model.choose_action(identifier))
        self.assertTrue(model.choose_action('aqua_edge', target_id='enemy_2'))
        action = model.current_action
        self.assertEqual((action.action, action.target, action.choreography),
                         ('aqua_edge', 'enemy_2', 'aether_edge'))
        model.update(action.impact_at)
        self.assertGreater(action.damage, 0)
        self.assertEqual(model.player.mp, 0)
        self.assertTrue(model.aqua_edge_discovered)
        self.assertFalse(model.aqua_edge_guided)
        self.assertIn('aqua_edge', model.learned_abilities)
        self.assertEqual(model.action_mp_cost('aqua_edge', 'player'), 0)
        self.assertEqual(sum(event['type'] == 'aqua_edge_discovered' for event in model.events), 1)
        model.update(action.duration-action.elapsed)
        for _ in range(100):
            model.update(1000)
            if model.ended:break
            if model.ready_actor == 'player':
                self.assertEqual(model.action_reason('aqua_edge'), '')
            self.assertTrue(model.choose_action('attack'))
        self.assertTrue(model.ended)
        self.assertEqual(model.phase, 'victory')

    def test_every_aqua_cast_in_the_introductory_fight_is_free(self):
        model = self.model(mp=4)
        model.enemy.attributes['hp'] = model.enemy.hp = 10000
        self.ready(model)
        self.assertTrue(model.choose_action('aqua_edge'))
        model.update(model.current_action.duration)
        self.assertEqual(model.player.mp, 4)
        for actor in (*model.party, *model.enemies):actor.atb = 0
        model.player.atb = 1
        model.update(0)
        self.assertTrue(model.choose_action('aqua_edge'))
        self.assertEqual(model.player.mp, 4)
        model.update(model.current_action.duration)
        self.assertEqual(sum(event['type'] == 'aqua_edge_discovered' for event in model.events), 1)

    def test_intro_retries_keep_free_casts_without_replaying_lesson_and_normal_battles_cost_four(self):
        for tutorial in (False, True):
            model = self.model(aqua_edge_tutorial=tutorial,
                               learned_abilities=['aether_edge', 'aqua_edge'])
            self.assertFalse(model.aqua_edge_guided)
            self.assertFalse(model.aqua_edge_discovered)
            self.assertEqual(model.action_mp_cost('aqua_edge', 'player'), 0 if tutorial else 4)
            for actor in (*model.party, *model.enemies):actor.atb = 0
            model.player.atb = 1
            model.update(0)
            self.assertEqual(model.action_reason('aqua_edge'), '' if tutorial else 'Not enough MP.')
            self.assertEqual(model.choose_action('aqua_edge'), tutorial)

    def test_unavailable_tutorial_configuration_is_rejected_before_battle(self):
        for options in ({'weapon_equipped': False}, {'active_gem': 'fire', 'owned_gems': ('water', 'fire')},
                        {'owned_gems': ('fire',)}, {'aqua_edge_tutorial': 1}):
            with self.subTest(options=options), self.assertRaises(ValueError):self.model(**options)
        with self.assertRaises(ValueError):
            BattleModel.from_bestiary_group(attributes(), BATS[:1],
                aqua_edge_tutorial=True, weapon_equipped=True)

    def test_caelan_incapacitation_releases_guidance_without_granting_aqua(self):
        model = self.model()
        self.ready(model)
        model.player.hp = 0
        model.update(1000)
        self.assertFalse(model.aqua_edge_guided)
        self.assertNotIn('aqua_edge', model.learned_abilities)
        self.assertFalse(model.aqua_edge_discovered)
        self.assertNotEqual(model.ready_actor, 'player')

    def elemental_model(self, percent=100, absorb=False, **stats):
        catalog = json.loads(ENEMY_PATH.read_text())
        profile = catalog['enemies']['cave_bat']['elemental_profile']
        profile['damage_percentages']['water'] = percent
        if absorb:
            profile['element'] = 'water'
            profile['absorption']['elements'] = ['water']
        model = BattleModel.from_bestiary(attributes(**stats), 'cave_bat', 2,
            bestiary_data=catalog, weapon_equipped=True, owned_gems=('water',),
            learned_abilities=['aqua_edge', 'aether_edge'], rng=FixedVariance())
        model.enemy.attributes['hp'] = model.enemy.hp = 10000
        model.player.atb = 1
        model.update(0)
        return model

    def test_each_affinity_changes_only_the_magical_component(self):
        for percent in (0, 25, 50, 100, 137.5, 150, 200):
            with self.subTest(percent=percent):
                model = self.elemental_model(percent)
                self.assertTrue(model.choose_action('aqua_edge'))
                action = model.current_action
                model.update(action.impact_at)
                expected = physical_damage(model.player, model.enemy) + magical_damage(
                    model.player, model.enemy, .5, affinity=Fraction(str(percent))/100)
                self.assertEqual(action.damage, expected)
                self.assertEqual(model.rng.calls, 1)
                self.assertEqual(model.player.mp, 26)

    def test_absorption_heals_magic_at_neutral_strength_after_normal_physical_component(self):
        model = self.elemental_model(0, absorb=True, str=1, mag=30)
        model.enemy.hp = 400
        before = model.enemy.hp
        self.assertTrue(model.choose_action('aqua_edge'))
        model.update(model.current_action.impact_at)
        physical = physical_damage(model.player, model.enemy)
        healing = magical_damage(model.player, model.enemy, .5)
        self.assertEqual(model.current_action.damage, physical)
        self.assertEqual(model.enemy.hp, before-physical+healing)
        impact = next(event for event in model.events if event['type'] == 'impact')
        self.assertEqual((impact['damage'], impact['healing'], impact['absorbed']),
                         (physical, healing, True))

    def test_absorption_cannot_exceed_max_hp_or_cancel_ordinary_aether_damage(self):
        model = self.elemental_model(absorb=True, str=1, mag=30)
        self.assertTrue(model.choose_action('aqua_edge'))
        model.update(model.current_action.duration)
        self.assertEqual(model.enemy.hp, model.enemy.max_hp)
        for actor in (*model.party, *model.enemies):actor.atb = 0
        model.player.atb = 1;model.update(0)
        self.assertTrue(model.choose_action('aether_edge'))
        model.update(model.current_action.impact_at)
        expected = physical_damage(model.player, model.enemy)+magical_damage(model.player, model.enemy, .5)
        self.assertEqual(model.current_action.damage, expected)
        self.assertEqual(model.enemy.hp, model.enemy.max_hp-expected)

    def test_only_owned_gems_can_be_selected_and_unarmed_characters_may_own_none(self):
        model = self.model()
        self.assertEqual(model.owned_gems, ('water',))
        for gem in ('nature', 'fire', 'ice'):
            self.assertFalse(model.set_active_gem(gem))
        unarmed = BattleModel(attributes(), weapon_equipped=False, owned_gems=())
        self.assertEqual(unarmed.owned_gems, ())
        self.assertFalse(unarmed.set_active_gem('water'))
        plain_sword = BattleModel(attributes(), weapon_equipped=True, owned_gems=(),
                                  learned_abilities=['aqua_edge'])
        plain_sword.player.atb = 1;plain_sword.update(0)
        self.assertIn('Requires the', plain_sword.action_reason('aqua_edge'))
        with self.assertRaises(ValueError):
            BattleModel(attributes(), enemy_id='ridgeback_tusker', guest_id='mira',
                        weapon_equipped=True, owned_gems=('fire',), active_gem='fire',
                        spellblade_tutorial=True)

    def test_blue_only_initial_story_party_wins_boar_with_guarded_telegraphs(self):
        for seed in range(5):
            with self.subTest(seed=seed):
                model = BattleModel(attributes(), enemy_id='ridgeback_tusker', guest_id='mira',
                    weapon_equipped=True, owned_gems=('water',), spellblade_tutorial=True,
                    rng=random.Random(seed))
                for _ in range(20000):
                    if model.waiting_for_player:
                        actor = model.ready_actor
                        if model.spellblade_stage == 'guard' or actor == model.telegraphed_target:command = 'guard'
                        elif model.spellblade_stage == 'first_edge':command = 'aqua_edge'
                        elif actor == 'player' and model.player.mp >= 4:command = 'aether_edge'
                        else:command = 'attack'
                        self.assertTrue(model.choose_action(command))
                    model.update(.05);model.drain_events()
                    if model.ended:break
                self.assertEqual(model.phase, 'victory')
                self.assertTrue(model.aether_edge_discovered)
                self.assertNotIn('aqua_edge', model.learned_abilities)
                self.assertTrue(all(member.hp > 0 for member in model.party))

    def test_actual_two_member_party_can_defeat_boss_using_blue_only_loadout(self):
        for seed in range(5):
            with self.subTest(seed=seed):
                members = profiles(level=7, ids=('caelan', 'mira'))
                before = deepcopy(members)
                model = BattleModel.from_bestiary(attributes(), 'vespermaw', 7,
                    party_members=members, weapon_equipped=True, owned_gems=('water',),
                    learned_abilities=['aether_edge', 'aqua_edge'], rng=random.Random(seed),
                    initial_atb=True, initial_atb_seed=seed)
                for _ in range(20000):
                    if model.waiting_for_player:
                        actor = model.ready_actor
                        if actor in model.enemy_telegraphs.values():command = 'guard'
                        elif actor == 'player' and model.player.mp >= 4:command = 'aqua_edge'
                        else:command = 'attack'
                        self.assertTrue(model.choose_action(command))
                    model.update(.05);model.drain_events()
                    if model.ended:break
                self.assertEqual(model.phase, 'victory')
                self.assertEqual(members, before)


if __name__ == '__main__':unittest.main()
