"""Bestiary encounters use real ATB, namespaced damage and living-party cycles."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from battle_model import ACTION_PATH, ENEMY_PATH, BattleModel, load_actions, load_enemies
from bestiary import build_enemy, load_bestiary
from character_attributes import ATTRIBUTE_IDS, CharacterAttributes
from leveling import character_stats


class FixedVariance:
    def randint(self, low, high):
        assert (low, high) == (95, 105)
        return 100


def player(level=2, **overrides):
    attributes = CharacterAttributes()
    snapshot = attributes.to_dict()
    snapshot['attributes'] = character_stats('caelan', level)
    snapshot['attributes'].update(overrides)
    snapshot['current_hp'] = snapshot['attributes']['hp']
    snapshot['current_mp'] = snapshot['attributes']['mp']
    assert attributes.restore(snapshot)
    return attributes


def party_profiles():
    profiles = []
    for identifier, name in (('player', 'Caelan'), ('mira', 'Mira'), ('lucan', 'Lucan')):
        stats = character_stats('caelan' if identifier == 'player' else identifier, 2)
        stats['hp'] = 9999
        profiles.append({'identifier': identifier, 'name': name, 'attributes': stats,
                         'hp': stats['hp'], 'mp': stats['mp'],
                         'attack': 'bolt_shot' if identifier == 'mira' else 'attack'})
    return profiles


class BestiaryBattleTests(unittest.TestCase):
    def model(self, level=2, source=None, **options):
        options.setdefault('rng', FixedVariance())
        return BattleModel.from_bestiary(source or player(level), 'cave_bat', level,
                                         **options)

    def enemy_turn(self, model):
        """Make the enemy ready, then finish its real timed battle action."""
        model.enemy.atb = 1
        model.update(0)
        self.assertEqual(model.phase, 'acting')
        self.assertEqual(model.current_action.actor, 'enemy')
        action = model.current_action
        mp = model.enemy.mp
        model.update(action.duration)
        self.assertTrue(action.resolved)
        return action, mp

    def test_level_profiles_and_metadata_are_independent_battle_copies(self):
        expected = {2: ([73, 5, 13, 14, 11, 13, 13, 13, 14, 15, 13], 59),
                    3: ([85, 5, 15, 15, 13, 14, 14, 14, 15, 16, 15], 73)}
        catalog = load_bestiary()
        original = deepcopy(catalog)
        actions = json.loads(ACTION_PATH.read_text())
        original_actions = deepcopy(actions)
        source = player()
        self.assertTrue(source.set_current(hp=19, mp=7))
        saved = source.to_dict()
        for level, (values, xp) in expected.items():
            with self.subTest(level=level):
                model = self.model(level, source=source, bestiary_data=catalog,
                                   action_data=actions)
                self.assertEqual([model.enemy.value(key) for key in ATTRIBUTE_IDS], values)
                self.assertEqual((model.enemy.hp, model.enemy.mp), tuple(values[:2]))
                self.assertEqual(model.enemy_id, 'cave_bat')
                self.assertEqual(model.enemy_bestiary_id, 'cave_bat')
                self.assertEqual((model.enemy_level, model.enemy_xp_reward), (level, xp))
                self.assertEqual(model.enemy_sprite_id, 'bat')
                self.assertEqual((model.player.hp, model.player.mp), (19, 7))
                self.assertEqual(model.enemy_definition['rewards'], {'drops': {}})
                model.enemy_bestiary_record['combat']['attributes']['hp'] = 1
                self.assertEqual(model.enemy.max_hp, values[0])
                model.enemy.attributes['str'] = 999
        self.assertEqual(catalog, original)
        self.assertEqual(actions, original_actions)
        self.assertEqual(source.to_dict(), saved)

    def test_namespaced_actions_preserve_old_bat_potencies(self):
        actions = load_actions()
        self.assertEqual((actions['bite']['potency'], actions['wing_gust']['potency']),
                         (1, 1.5))
        self.assertEqual((actions['cave_bat_bite']['potency'],
                          actions['cave_bat_wing_gust']['potency']), (.6, .65))
        model = self.model()
        action, _ = self.enemy_turn(model)
        self.assertEqual((action.action, action.animation), ('cave_bat_bite', 'bite'))
        self.assertEqual(model.events[-1]['action'], 'cave_bat_bite')
        self.assertEqual(model.enemy_action_aliases,
                         {'cave_bat_bite': 'bite', 'cave_bat_wing_gust': 'wing_gust'})

    def test_action_elements_validate_without_activating_elemental_damage(self):
        data = json.loads(ACTION_PATH.read_text())
        original = deepcopy(data)
        self.assertNotIn('element', load_actions(data)['cave_bat_wing_gust'])
        for element in ('non_elemental', 'fire', 'electric', 'water', 'ice',
                        'nature', 'wind', 'holy', 'ground'):
            with self.subTest(element=element):
                tagged = deepcopy(data)
                tagged['actions']['cave_bat_wing_gust']['element'] = element
                self.assertEqual(load_actions(tagged)['cave_bat_wing_gust']['element'], element)
                model = self.model(action_data=tagged)
                self.enemy_turn(model)
                # Existing approved damage stays 22 regardless of an action's
                # authoring tag; weakness/resistance application is deferred.
                self.assertEqual(self.enemy_turn(model)[0].damage, 22)
        self.assertEqual(data, original)
        for value in ('poison', 'lightning', '', None, True, 1, [], {}):
            with self.subTest(invalid_element=value):
                malformed = deepcopy(data)
                malformed['actions']['aether_dart']['element'] = value
                with self.assertRaisesRegex(ValueError, 'Invalid battle action element'):
                    load_actions(malformed)
        for identifier in ('guard', 'flee', 'prepare_charge', 'overclock', 'nature_edge'):
            with self.subTest(utility=identifier):
                malformed = deepcopy(data)
                malformed['actions'][identifier]['element'] = 'electric'
                with self.assertRaisesRegex(ValueError, 'Invalid battle action element'):
                    load_actions(malformed)

    def test_real_enemy_turns_alternate_until_two_gusts_exhaust_mp(self):
        model = self.model(source=player(hp=9999))
        turns = [self.enemy_turn(model) for _ in range(8)]
        self.assertEqual([action.action for action, _ in turns],
                         ['cave_bat_bite', 'cave_bat_wing_gust']*2
                         +['cave_bat_bite']*4)
        self.assertEqual([mp for _, mp in turns], [5, 3, 3, 1, 1, 1, 1, 1])
        self.assertEqual(model.enemy.mp, 1)
        impacts = [event for event in model.events if event['type'] == 'impact']
        self.assertEqual([event['action'] for event in impacts],
                         [action.action for action, _ in turns])

    def test_same_level_damage_uses_approved_potencies_and_guard(self):
        for level, damages in ((2, (18, 22)), (3, (24, 26))):
            with self.subTest(level=level):
                model = self.model(level)
                hits = [self.enemy_turn(model)[0].damage for _ in range(2)]
                self.assertEqual(tuple(hits), damages)
                guarded = self.model(level)
                guarded.player.atb = 1
                guarded.update(0)
                self.assertTrue(guarded.choose_action('guard'))
                guarded.update(guarded.current_action.duration)
                before = guarded.player.hp, guarded.player.mp
                action, _ = self.enemy_turn(guarded)
                self.assertEqual(action.damage, damages[0]//2)
                self.assertFalse(guarded.player.guarded)
                self.assertEqual((guarded.player.hp, guarded.player.mp),
                                 (before[0]-action.damage, before[1]))
                self.assertEqual(self.enemy_turn(guarded)[0].damage, damages[1])

    def test_target_cycle_uses_party_order_skips_ko_and_keeps_query_read_only(self):
        profiles = party_profiles()
        model = self.model(party_members=profiles, bot_loadouts={})
        self.assertEqual([model._enemy_target('cave_bat_bite') for _ in range(3)],
                         ['player']*3)
        targets = [self.enemy_turn(model)[0].target for _ in range(4)]
        self.assertEqual(targets, ['player', 'mira', 'lucan', 'player'])
        model.combatant('mira').hp = 0
        targets = [self.enemy_turn(model)[0].target for _ in range(4)]
        self.assertEqual(targets, ['lucan', 'player', 'lucan', 'player'])
        model.player.hp = 0
        self.assertEqual(self.enemy_turn(model)[0].target, 'lucan')
        self.assertEqual([profile['hp'] for profile in profiles], [9999]*3)

    def test_atb_and_damage_pause_at_player_choice_and_during_actions(self):
        model = self.model(source=player(speed=255))
        model.update(100)
        self.assertTrue(model.waiting_for_player)
        before = model.player.atb, model.enemy.atb, model.player.hp, model.enemy.mp
        model.update(100)
        self.assertEqual((model.player.atb, model.enemy.atb,
                          model.player.hp, model.enemy.mp), before)
        model.choose_action('guard')
        model.update(model.current_action.duration)
        model.enemy.atb = 1
        model.update(0)
        action = model.current_action
        gauges = model.player.atb, model.enemy.atb
        model.update(action.impact_at-.01)
        self.assertEqual(model.player.hp, before[2])
        model.update(.01)
        after_impact = model.player.hp
        self.assertLess(after_impact, before[2])
        model.update(.01)
        self.assertEqual(model.player.hp, after_impact)
        self.assertEqual((model.player.atb, model.enemy.atb), gauges)

    def test_legacy_fixed_enemy_loading_stats_and_targeting_are_unchanged(self):
        catalog = json.loads(ENEMY_PATH.read_text())
        fixed = load_enemies(load_actions(), catalog)
        self.assertEqual(set(fixed), {'bat', 'ridgeback_tusker'})
        self.assertEqual(fixed['bat']['attributes']['hp'], 72)
        self.assertEqual(fixed['ridgeback_tusker']['attributes']['hp'], 700)
        for enemy_id in fixed:
            with self.subTest(enemy=enemy_id):
                model = BattleModel(player(), enemy_id=enemy_id,
                                    party_members=party_profiles(), bot_loadouts={})
                self.assertEqual(model.enemy_definition, catalog['enemies'][enemy_id])
                self.assertEqual(model.enemy_sprite_id, enemy_id)
                self.assertIsNone(model.enemy_level)
                self.assertIsNone(model.enemy_xp_reward)
                action = 'bite' if enemy_id == 'bat' else 'tusk_strike'
                target = 'player' if enemy_id == 'bat' else 'mira'
                for _ in range(2):
                    model._start_action('enemy', action)
                    self.assertEqual(model.current_action.target, target)
                    model.update(model.current_action.duration)

    def test_legacy_fixtures_work_and_filtered_species_are_still_validated(self):
        catalog = load_bestiary()
        fixture = {'version': 1, 'enemies': {'test_bat': catalog['enemies']['bat']}}
        model = BattleModel(player(), enemy_id='test_bat', enemy_data=fixture)
        self.assertEqual(model.enemy.hp, 72)
        self.assertEqual(set(load_enemies(load_actions(), fixture)), {'test_bat'})
        catalog['enemies']['cave_bat']['behavior']['fallback'] = 'unknown_action'
        with self.assertRaises(ValueError):
            # Even a legacy battle validates computed entries before filtering.
            BattleModel(player(), enemy_data=catalog)

    def test_factory_rejects_invalid_level_and_unsupported_future_style(self):
        for level in (None, True, 1, 4, 2.0, '2'):
            with self.subTest(level=level), self.assertRaises((TypeError, ValueError)):
                self.model(level, source=player())
        with self.assertRaises(ValueError):
            BattleModel.from_bestiary(player(), 'unknown', 2)
        catalog = load_bestiary()
        catalog['enemies']['cave_bat']['fighting_style'] = 'wounded_targeting'
        # The dictionary can author future styles; this adapter cannot silently run them.
        build_enemy('cave_bat', 2, data=catalog)
        with self.assertRaisesRegex(ValueError, 'Unsupported Bestiary fighting style'):
            self.model(bestiary_data=catalog)

    def test_pending_species_are_authorable_but_cannot_start_a_battle(self):
        source = player()
        before = source.to_dict()
        catalog = load_bestiary()
        for identifier in ('lithrusk', 'veylume'):
            catalog['enemies'][identifier]['presentation'] = {'sprite_id': None, 'action_aliases': {}}
        original = deepcopy(catalog)
        for identifier, level in (('lithrusk', 2), ('veylume', 3)):
            with self.subTest(enemy=identifier):
                record = build_enemy(identifier, level, data=catalog)
                self.assertTrue(record['metadata']['presentation_pending'])
                with patch.object(BattleModel, '__init__',
                                  side_effect=AssertionError('Battle construction must not begin')):
                    with self.assertRaisesRegex(ValueError, 'Bestiary enemy presentation is pending'):
                        BattleModel.from_bestiary(source, identifier, level, bestiary_data=catalog)
        self.assertEqual(source.to_dict(), before)
        self.assertEqual(catalog, original)

    def test_unsupported_future_style_stays_guarded_with_ready_presentation(self):
        catalog = load_bestiary()
        catalog['enemies']['veylume']['fighting_style'] = 'wounded_targeting'
        self.assertFalse(build_enemy('veylume', 3, data=catalog)['metadata']['presentation_pending'])
        with patch.object(BattleModel, '__init__',
                          side_effect=AssertionError('Unsupported AI must not start a battle')):
            with self.assertRaisesRegex(ValueError, 'Unsupported Bestiary fighting style'):
                BattleModel.from_bestiary(player(3), 'veylume', 3, bestiary_data=catalog)


class CaveSpeciesBattleTests(unittest.TestCase):
    def model(self, identifier, level, **options):
        # This fixture isolates real AI from sprite generation. The separate
        # asset/scene suite exercises the canonical species art and renderer.
        catalogue = load_bestiary()
        actions = load_actions()
        aliases = {key: 'prepare_charge' if actions[key]['kind'] == 'prepare' else 'tusk_strike'
                   for key in catalogue['enemies'][identifier]['behavior']['sequence']}
        catalogue['enemies'][identifier]['presentation'] = {
            'sprite_id': 'ridgeback_tusker', 'action_aliases': aliases}
        options.setdefault('party_members', party_profiles())
        options.setdefault('bot_loadouts', {})
        return BattleModel.from_bestiary(player(level, hp=9999), identifier, level,
                                         bestiary_data=catalogue, rng=FixedVariance(), **options)

    def enemy_turn(self, model):
        model.enemy.atb = 1
        model.update(0)
        self.assertEqual(model.phase, 'acting')
        action = model.current_action
        self.assertEqual(action.actor, 'enemy')
        paid_mp = model.enemy.mp
        model.update(action.duration)
        self.assertTrue(action.resolved)
        return action, paid_mp

    def test_lithrusk_uses_both_physical_attacks_at_each_authored_level(self):
        for level in (2, 3):
            with self.subTest(level=level):
                model = self.model('lithrusk', level)
                turns = [self.enemy_turn(model)[0] for _ in range(6)]
                self.assertEqual([turn.action for turn in turns],
                                 ['lithrusk_claw_clamp', 'lithrusk_shell_bash']*3)
                self.assertEqual([turn.target for turn in turns],
                                 ['player', 'mira', 'lucan']*2)
                self.assertTrue(all(turn.kind == 'physical' and turn.damage > 0 for turn in turns))
                self.assertEqual(model.enemy.mp, 0)
                self.assertIsNone(model.telegraphed_target)

    def test_veylume_has_two_charged_flashes_then_only_free_sparks(self):
        for level, remaining in ((3, 2), (4, 3)):
            with self.subTest(level=level):
                model = self.model('veylume', level)
                turns = [self.enemy_turn(model) for _ in range(12)]
                self.assertEqual([turn.action for turn, _ in turns],
                                 ['veylume_static_spark', 'veylume_gather_charge', 'veylume_veinflash']*2
                                 +['veylume_static_spark']*6)
                self.assertEqual([mp for _, mp in turns][2:6],
                                 [remaining+4, remaining+4, remaining+4, remaining])
                self.assertEqual(model.enemy.mp, remaining)
                self.assertTrue(all(turn.kind == 'magical' and turn.damage > 0
                                    for turn, _ in turns if turn.action != 'veylume_gather_charge'))
                self.assertIsNone(model.telegraphed_target)

    def test_veylume_locks_a_living_target_and_uses_its_own_charge_tell(self):
        model = self.model('veylume', 3)
        first, _ = self.enemy_turn(model)
        self.assertEqual(first.target, 'player')
        prepare, _ = self.enemy_turn(model)
        self.assertEqual(prepare.action, 'veylume_gather_charge')
        target = model.telegraphed_target
        self.assertEqual(target, 'mira')
        self.assertIn('Mira', model.message)
        self.assertIn('charge', model.message.lower())
        self.assertNotIn('head', model.message.lower())
        flash, _ = self.enemy_turn(model)
        self.assertEqual(flash.target, target)
        self.assertIsNone(model.telegraphed_target)

    def test_veylume_retargets_a_ko_and_never_prepares_an_unaffordable_flash(self):
        model = self.model('veylume', 3)
        self.enemy_turn(model)
        self.enemy_turn(model)
        target = model.telegraphed_target
        model.combatant(target).hp = 0
        model.update(0)
        self.assertNotEqual(model.telegraphed_target, target,
                            'The visible charge warning must update before the next turn')
        flash, _ = self.enemy_turn(model)
        self.assertNotEqual(flash.target, target)
        self.assertGreater(model.combatant(flash.target).hp, 0)
        self.assertIsNone(model.telegraphed_target)
        for insufficient in (0, 1, 2, 3):
            with self.subTest(mp=insufficient):
                model.enemy.mp = insufficient
                model._enemy_action_index = 1
                actions = [self.enemy_turn(model)[0].action for _ in range(4)]
                self.assertEqual(actions, ['veylume_static_spark']*4)
                self.assertEqual(model.enemy.mp, insufficient)
                self.assertIsNone(model.telegraphed_target)

    def test_lost_mp_cancels_a_held_charge_and_a_midflash_ko_is_retargeted(self):
        model = self.model('veylume', 3)
        self.enemy_turn(model)
        self.enemy_turn(model)
        self.assertIsNotNone(model.telegraphed_target)
        model.enemy.mp = 3
        model.update(0)
        self.assertIsNone(model.telegraphed_target)
        self.assertEqual(self.enemy_turn(model)[0].action, 'veylume_static_spark')
        self.assertEqual(model.enemy.mp, 3)

        model = self.model('veylume', 3)
        self.enemy_turn(model)
        self.enemy_turn(model)
        model.enemy.atb = 1
        model.update(0)
        flash = model.current_action
        self.assertEqual(flash.action, 'veylume_veinflash')
        target = flash.target
        model.combatant(target).hp = 0
        model.update(0)
        self.assertNotEqual(flash.target, target)
        self.assertEqual(flash.target, model.telegraphed_target)
        model.update(flash.duration)
        self.assertTrue(flash.resolved)
        self.assertGreater(flash.damage, 0)


if __name__ == '__main__':unittest.main()
