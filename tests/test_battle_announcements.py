"""Named combat actions, authored events and held enemy preparations."""
from copy import deepcopy
import math
import unittest

from battle_announcements import BattleAnnouncements, basic_attack, enemy_charge_warnings
from battle_model import BattleModel
from test_random_enemy_groups import attributes, clear_gauges, group


class BattleAnnouncementTests(unittest.TestCase):
    def model(self, **options):
        options.setdefault('weapon_equipped', True)
        options.setdefault('learned_abilities', ('aether_edge',))
        options.setdefault('initial_atb', False)
        model = BattleModel(attributes(), **options)
        model.drain_events()
        return model

    def start(self, model, actor, identifier):
        clear_gauges(model)
        model._start_action(actor, identifier)
        return model.current_action

    def feed(self, notices, model):
        for event in model.drain_events():notices.consume(event)

    def test_ordinary_attacks_resolve_for_each_actor_and_enemy_species(self):
        model = self.model(guest_id='mira')
        expected = {'player': 'attack', 'mira': 'bolt_shot',
                    'rivet': 'piston_jab', 'enemy': 'bite'}
        for actor, attack in expected.items():
            with self.subTest(actor=actor):
                self.assertEqual(basic_attack(model, actor), attack)
                notices = BattleAnnouncements(model)
                self.start(model, actor, attack)
                self.feed(notices, model)
                self.assertIsNone(notices.current)
        for enemy, attack in (('cave_bat', 'cave_bat_bite'),
                              ('lithrusk', 'lithrusk_claw_clamp'),
                              ('veylume', 'veylume_static_spark')):
            with self.subTest(enemy=enemy):
                model = group([{'enemy_id': enemy, 'level': 3}])
                notices = BattleAnnouncements(model)
                self.assertEqual(basic_attack(model, 'enemy'), attack)
                self.start(model, 'enemy', attack)
                self.feed(notices, model)
                self.assertIsNone(notices.current)

    def test_named_skill_is_visible_immediately_before_event_drain_and_is_not_duplicated(self):
        model = self.model()
        notices = BattleAnnouncements(model)
        clear_gauges(model)
        model.player.atb = 1
        model.update(0)
        self.assertTrue(model.choose_action('aether_edge'))
        self.assertEqual(notices.current['text'], 'Caelan — Aether Edge')
        self.assertEqual(notices.current['kind'], 'ability')
        self.assertGreaterEqual(notices.current['duration'], 2.5)
        notices.update(.8)
        self.feed(notices, model)
        self.assertAlmostEqual(notices.current['age'], .8)
        self.assertEqual(len(notices._queue), 0)

    def test_basic_attack_does_not_replace_the_previous_special_title(self):
        model = self.model()
        notices = BattleAnnouncements(model)
        action = self.start(model, 'player', 'aether_edge')
        self.feed(notices, model)
        model.update(action.duration)
        self.feed(notices, model)
        notices.update(action.duration)
        self.start(model, 'player', 'attack')
        self.feed(notices, model)
        self.assertEqual(notices.current['text'], 'Caelan — Aether Edge')
        notices.update(3)
        self.assertIsNone(notices.current)

    def test_future_long_ability_keeps_its_title_until_the_animation_finishes(self):
        model = self.model()
        model.actions['aether_dart'].update(duration=8., impact_at=7.)
        notices = BattleAnnouncements(model)
        action = self.start(model, 'player', 'aether_dart')
        self.feed(notices, model)
        self.assertGreaterEqual(notices.current['duration'], action.duration)
        model.update(4)
        self.feed(notices, model)
        notices.update(4)
        self.assertIs(model.current_action, action)
        self.assertEqual(notices.current['text'], 'Caelan — Aether Dart')
        model.update(4)
        self.feed(notices, model)
        notices.update(4)
        self.assertIsNone(notices.current)

    def test_distinct_repeated_abilities_get_fresh_holds_but_duplicate_events_do_not(self):
        model = self.model(guest_id='mira')
        notices = BattleAnnouncements(model)
        first = self.start(model, 'mira', 'overclock')
        self.feed(notices, model)
        model.update(first.duration)
        self.feed(notices, model)
        notices.update(first.duration)
        self.assertGreater(notices.current['age'], 0)

        second = self.start(model, 'mira', 'overclock')
        self.assertIsNot(first, second)
        starts = [event for event in model.drain_events() if event['type'] == 'action_started']
        self.assertEqual(notices.current['age'], 0)
        notices.update(.4)
        for event in starts:
            notices.consume(event)
            notices.consume(dict(event))
        self.assertEqual(notices.current['text'], 'Mira — Overclock')
        self.assertAlmostEqual(notices.current['age'], .4)

    def test_ability_interruptions_do_not_restart_the_multiple_charge_rotation(self):
        model = group([{'enemy_id': 'veylume', 'level': 3},
                       {'enemy_id': 'veylume', 'level': 3}],
                      learned_abilities=['aether_edge'], weapon_equipped=True)
        for enemy in model.enemies:
            enemy.attributes['hp'] = 9999
            enemy.hp = 9999
        for actor in ('enemy', 'enemy_2'):
            preparation = self.start(model, actor, 'veylume_gather_charge')
            model.update(preparation.duration)
        model.drain_events()
        notices = BattleAnnouncements(model, display_name=lambda actor: 'Moth '+actor)
        first_duration = notices.warnings[0]['duration']
        self.assertEqual(notices.current['actor'], 'enemy')
        # UI time can advance while the player is deciding and ATB is held.
        clear_gauges(model)
        model.player.atb = 1
        model.update(0)
        notices.update(first_duration*.6)
        seen = {notices.current['actor']}
        for _ in range(3):
            clear_gauges(model)
            model.player.atb = 1
            model.update(0)
            self.assertTrue(model.choose_action('aether_edge'))
            self.feed(notices, model)
            self.assertEqual(notices.current['kind'], 'ability')
            action = model.current_action
            model.update(action.duration)
            self.feed(notices, model)
            notices.update(action.duration)
            title = notices.current
            extra = max(0, title['duration']-title['age'])+.01
            model.update(extra)
            self.feed(notices, model)
            notices.update(extra)
            self.assertEqual(len(notices.warnings), 2)
            self.assertEqual(notices.current['kind'], 'warning')
            seen.add(notices.current['actor'])
        self.assertEqual(seen, {'enemy', 'enemy_2'})

    def test_secondary_enemy_attacks_are_announced_even_without_mp_cost(self):
        for species, action in (('cave_bat', 'cave_bat_wing_gust'),
                                ('lithrusk', 'lithrusk_shell_bash')):
            with self.subTest(species=species):
                model = group([{'enemy_id': species, 'level': 3}])
                notices = BattleAnnouncements(model)
                self.start(model, 'enemy', action)
                self.feed(notices, model)
                self.assertEqual(notices.current['action'], action)
                self.assertIn(model.actions[action]['name'], notices.current['text'])

    def test_tusker_warning_begins_before_commit_holds_between_turns_and_ends_at_impact(self):
        model = self.model(enemy_id='ridgeback_tusker', guest_id='mira')
        notices = BattleAnnouncements(model)
        action = self.start(model, 'enemy', 'prepare_charge')
        warning = notices.warnings[0]
        self.assertEqual((warning['action'], warning['stage'], warning['target']),
                         ('tusker_charge', 'prepare', None))
        self.assertIn('Bankbreaker Charge', warning['text'])
        model.update(action.duration)
        self.assertEqual(notices.warnings[0]['stage'], 'ready')
        target = notices.warnings[0]['target']
        self.assertIn(target, ('player', 'mira'))
        model.player.atb = 1
        model.update(0)
        self.assertEqual(model.phase, 'ready')
        self.assertEqual(notices.warnings[0]['target'], target)
        self.start(model, 'enemy', 'tusker_charge')
        self.assertEqual(notices.warnings[0]['stage'], 'release')
        model.update(model.current_action.impact_at)
        self.assertEqual(notices.warnings, ())

    def test_held_spell_retargets_and_cancels_from_authoritative_state(self):
        model = group([{'enemy_id': 'veylume', 'level': 3}])
        notices = BattleAnnouncements(model)
        action = self.start(model, 'enemy', 'veylume_gather_charge')
        model.update(action.duration)
        first = notices.warnings[0]
        self.assertEqual(first['action'], 'veylume_veinflash')
        model.combatant(first['target']).hp = 0
        model.update(0)
        self.assertNotEqual(notices.warnings[0]['target'], first['target'])
        self.assertGreater(model.combatant(notices.warnings[0]['target']).hp, 0)
        model.enemy.mp = 0
        self.assertEqual(notices.warnings, ())
        model.enemy.mp = 8
        model.enemy.hp = 0
        self.assertEqual(notices.warnings, ())

    def test_multiple_charged_enemies_keep_distinct_names_and_rotate_without_mutation(self):
        model = group([{'enemy_id': 'veylume', 'level': 3},
                       {'enemy_id': 'veylume', 'level': 3}])
        for actor in ('enemy', 'enemy_2'):
            action = self.start(model, actor, 'veylume_gather_charge')
            model.update(action.duration)
        notices = BattleAnnouncements(model, display_name=lambda identifier: 'Moth '+identifier)
        saved = deepcopy({key: value for key, value in model.__dict__.items() if key != 'rng'})
        random_state = model.rng.getstate()
        warnings = notices.warnings
        self.assertEqual([item['actor'] for item in warnings], ['enemy', 'enemy_2'])
        self.assertTrue(warnings[1]['text'].startswith('Moth enemy_2 readies '))
        self.assertEqual(notices.current['actor'], 'enemy')
        self.assertEqual(notices.current['age'], 0)
        notices.update(warnings[0]['duration']+.1)
        self.assertEqual(notices.current['actor'], 'enemy_2')
        self.assertAlmostEqual(notices.current['age'], .1)
        self.assertEqual({key: value for key, value in model.__dict__.items() if key != 'rng'}, saved)
        self.assertEqual(model.rng.getstate(), random_state)

    def test_emotes_and_events_keep_full_wrappable_text_and_bounded_queue(self):
        model = self.model()
        notices = BattleAnnouncements(model)
        text = 'The crystal-veined walls answer the beast with a low, rising chorus. ' * 4
        notices.consume({'type': 'event', 'text': text})
        self.assertEqual(notices.current['text'], text.strip())
        self.assertEqual(notices.current['duration'], 12)
        notices.consume({'type': 'event', 'text': text})
        self.assertEqual(len(notices._queue), 0)
        for index in range(20):
            notices.consume({'type': 'emote', 'actor': 'enemy', 'text': 'Twitch '+str(index)})
        self.assertLessEqual(len(notices._queue), 6)
        notices.update(100)
        self.assertIsNone(notices.current)

    def test_actual_status_events_are_readable_and_basic_damage_is_not_a_fake_critical(self):
        model = self.model(guest_id='mira')
        notices = BattleAnnouncements(model)
        action = self.start(model, 'mira', 'overclock')
        self.feed(notices, model)
        self.assertIn('Overclock', notices.current['text'])
        model.update(action.duration)
        self.feed(notices, model)
        notices.update(3)
        self.assertIn('Rivet gains Haste for 8 turns', notices.current['text'])
        notices.clear()
        notices.consume({'type': 'impact', 'actor': 'player', 'target': 'enemy',
                         'damage': 9999, 'remaining_hp': 10})
        self.assertIsNone(notices.current)
        notices.consume({'type': 'spellblade_discovered', 'actor': 'player'})
        self.assertEqual(notices.current['text'], 'Caelan discovers Aether Edge!')

    def test_guard_and_failed_elemental_focus_report_existing_events(self):
        model = self.model()
        notices = BattleAnnouncements(model)
        notices.consume({'type': 'guard', 'actor': 'player'})
        self.assertEqual(notices.current['text'], 'Caelan uses Guard.')
        notices.consume({'type': 'spellblade_failed', 'actor': 'player', 'action': 'aqua_edge'})
        notices.update(3)
        self.assertIn('Aqua Edge fails', notices.current['text'])

    def test_held_charge_outweighs_queued_haste_before_the_enemys_next_turn(self):
        model = self.model(enemy_id='ridgeback_tusker', guest_id='mira')
        notices = BattleAnnouncements(model)
        action = self.start(model, 'enemy', 'prepare_charge')
        self.feed(notices, model)
        model.update(action.duration)
        notices.update(action.duration)
        self.assertEqual(notices.warnings[0]['stage'], 'ready')

        action = self.start(model, 'mira', 'overclock')
        self.feed(notices, model)
        self.assertIn('Overclock', notices.current['text'])
        model.update(action.duration)
        self.feed(notices, model)
        notices.update(action.duration)
        self.assertTrue(any('Haste' in item['text'] for item in notices._queue))
        # Advance real ATB as well as the UI clock. The utility notice must
        # yield as soon as the skill title expires, before the charged turn.
        model.update(1.7)
        self.feed(notices, model)
        notices.update(1.7)
        self.assertLess(model.enemy.atb, 1)
        self.assertEqual(notices.current['kind'], 'warning')
        self.assertIn('readies Bankbreaker Charge', notices.current['text'])
        self.assertEqual(notices.current['target'], model.telegraphed_target)
        for event in ({'type': 'guard', 'actor': 'player'},
                      {'type': 'bot_deployed', 'actor': 'rivet', 'owner': 'mira'}):
            notices.consume(event)
            self.assertEqual(notices.current['kind'], 'warning')

        # A newly used named attack still appears immediately. After impact
        # clears the threat, the retained, still-recent status can be read.
        action = self.start(model, 'enemy', 'tusker_charge')
        self.feed(notices, model)
        self.assertIn('Bankbreaker Charge', notices.current['text'])
        self.assertEqual(notices.current['kind'], 'ability')
        model.update(action.impact_at)
        self.feed(notices, model)
        self.assertEqual(notices.warnings, ())
        notices.update(3)
        self.assertIn('Rivet gains Haste', notices.current['text'])

    def test_results_clear_titles_queue_and_even_legacy_telegraphs(self):
        model = self.model(enemy_id='ridgeback_tusker')
        notices = BattleAnnouncements(model)
        action = self.start(model, 'enemy', 'prepare_charge')
        model.update(action.duration)
        self.assertTrue(notices.warnings)
        notices.consume({'type': 'narration', 'text': 'The beast roars.'})
        model._result('fled')
        self.assertEqual(enemy_charge_warnings(model), ())
        self.assertIsNone(notices.current)
        self.assertFalse(notices._queue)

    def test_clock_validation_and_repeated_draws_do_not_advance_time(self):
        notices = BattleAnnouncements(self.model())
        notices.consume({'type': 'emote', 'actor': 'player', 'text': 'Steady now.'})
        for _ in range(10):self.assertEqual(notices.current['age'], 0)
        notices.update(.5)
        self.assertEqual(notices.current['age'], .5)
        for invalid in (-1, math.inf, math.nan, True, None, '1'):
            with self.subTest(value=invalid):
                with self.assertRaises(ValueError):notices.update(invalid)


if __name__ == '__main__':
    unittest.main()
