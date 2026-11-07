"""Rivet and Overclock through real MQ02 entry, input, and journey saves.

Only earlier quest work is seeded. Battle phases, gauges, action timers, and
outcomes advance through the production Game update and command paths.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from main import Game
from test_mill_battle_gameplay import (
    acknowledge_battle_result, click, key, read_social,
    seed_completed_mill, seed_mill_handoff,
)
from ui_style import Painter


STARTING_LOADOUTS = {'mira': {'bot_id': 'rivet', 'ability_id': 'piston_jab'}}


class RivetGameplayTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='rivet-gameplay-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'
        self.games = []

    def tearDown(self):
        for game in self.games:
            game.opening_audio.reset()
            game.regional_audio.reset()
            game.music.stop()
        pygame.quit()

    def game(self, *, title=False):
        game = Game(window_size=(960, 640), fullscreen=False,
                    start_on_title=title, save_path=self.path,
                    settings_path=self.directory/'settings.json')
        self.games.append(game)
        game.audio.set_music(0)
        game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        return game

    def place(self, game, point, world=None):
        world = world or game.world
        game.world = world
        for radius in (0, 8, 16, 24):
            for offset in ((0, radius), (radius, 0), (-radius, 0), (0, -radius)):
                position = pygame.Vector2(point)+offset
                if not world.can_stand(position):
                    continue
                game.player.position.update(position)
                for delta in ((-24, 0), (24, 0), (0, 24), (0, -24)):
                    if world.can_stand(position+delta):
                        game.mill_quest._place_mira(world, position+delta)
                        break
                game.camera.reset()
                game.transfer_cooldown = 0
                return
        self.fail('No clear position for the story fixture.')

    def start_boar(self, game):
        seed_mill_handoff(game)
        controller = game.mill_quest
        self.place(game, controller.mira.position+(0, 28), game.town)
        key(game, pygame.K_e)
        self.assertEqual(game.social.script_identifier, 'mill_reunion')
        read_social(game)
        for name in ('mechanism', 'race'):
            self.place(game, controller.points[name])
            key(game, pygame.K_e)
            self.assertEqual(game.social.script_identifier, 'mill_'+name)
            read_social(game)
        self.assertTrue(controller.warned)
        self.place(game, (720, 12), game.town)
        key(game, pygame.K_e)
        self.assertEqual(game.world.data['id'], 'upstream')
        for _ in range(1000):
            if game.combat.active:
                break
            if game.social.active or controller.encounter_cutscene_active:
                read_social(game)
            else:
                game.update(.05, (0, 0), False)
        self.assertTrue(game.combat.active)
        self.assertEqual(game.combat.model.enemy_id, 'ridgeback_tusker')
        game.combat.model.rng = random.Random(7)
        return game.combat.scene

    def step(self, game, scene, *, guard_ready=True, seconds=.05):
        if game.combat.transitioning:
            game.update(seconds, (0, 0), False)
        elif scene.tutorial_active:
            key(game, pygame.K_SPACE)
        elif scene.model.waiting_for_player and guard_ready:
            game.draw()
            if getattr(scene.model, 'spellblade_stage', None) in ('first_edge', 'second_edge'):
                # Finish Caelan's authored introductory attempts through the
                # real Skills UI before exercising ordinary bot controls.
                click(game, scene.command_rects['skills'].center)
                game.draw()
                # The gear now gates attempts too; use its settled focus.
                attempt = {'nature': 'nature_edge', 'water': 'aqua_edge',
                           'fire': 'flame_edge'}[scene.model.active_gem]
                click(game, scene.command_rects[attempt].center)
            else:
                click(game, scene.command_rects['guard'].center)
        else:
            game.update(seconds, (0, 0), False)

    def advance_until(self, game, scene, predicate, *, guard_ready=True):
        for _ in range(5000):
            if predicate():
                return
            self.assertFalse(scene.model.ended, 'Battle ended before the expected state.')
            self.step(game, scene, guard_ready=guard_ready)
        self.fail('The production battle did not reach the expected state.')

    def ready_member(self, game, scene, identifier):
        for _ in range(2000):
            self.assertFalse(scene.model.ended)
            if game.combat.transitioning or scene.tutorial_active:
                self.step(game, scene)
            elif getattr(scene.model, 'spellblade_stage', None) not in (None, 'complete'):
                self.step(game, scene)
            elif scene.model.waiting_for_player:
                game.draw()
                if identifier in scene.model.ready_members:
                    if scene.model.ready_actor != identifier:
                        click(game, scene.party_rows[identifier]['row'].center)
                    if not scene.tutorial_active:
                        self.assertEqual(scene.model.ready_actor, identifier)
                        return
                else:
                    click(game, scene.command_rects['guard'].center)
            else:
                game.update(.05, (0, 0), False)
        self.fail(identifier+' never reached a real ready turn.')

    def gauges(self, scene):
        return tuple((member.identifier, member.atb)
                     for member in (*scene.model.party, scene.model.enemy, *scene.model.bots))

    def state(self, scene):
        action = scene.model.current_action
        return (scene.model.phase, self.gauges(scene),
                None if action is None else (action.actor, action.action, action.elapsed),
                tuple((member.identifier, member.hp, member.mp) for member in scene.model.party),
                tuple((bot.identifier, bot.haste_turns) for bot in scene.model.bots))

    def draw_text(self, game):
        records = []
        original = Painter.text

        def capture(painter, text, *args, **kwargs):
            records.append(str(text))
            return original(painter, text, *args, **kwargs)

        with patch.object(Painter, 'text', capture):
            game.draw()
        return records

    def assert_durable_loadout_only(self, saved):
        self.assertEqual(saved['bot_loadouts'], {'version': 1, 'loadouts': STARTING_LOADOUTS})

        def visit(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    self.assertNotIn(key, ('atb', 'haste_turns', 'remaining_turns',
                                           'rate_multiplier', 'haste_rate_multiplier',
                                           'current_action', 'bots'))
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(saved)

    def test_pre_mira_bat_has_no_bot_despite_starting_ownership(self):
        game = self.game()
        self.assertEqual(game.bot_loadouts.battle_loadouts(), STARTING_LOADOUTS)
        self.assertEqual(game.character_abilities.known_abilities('mira'),
                         frozenset({'overclock', 'rivet'}))
        self.assertNotIn('piston_jab', game.character_abilities.known_abilities('mira'))
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 24))
        game.player.facing = 'back'
        game.camera.reset()
        key(game, pygame.K_e)
        self.assertTrue(game.combat.active)
        scene = game.combat.scene
        self.assertEqual(scene.model.enemy_id, 'bat')
        self.assertEqual([member.identifier for member in scene.model.party], ['player'])
        self.assertEqual(scene.model.bots, ())
        self.assertIsNone(scene.model.bot_for('mira'))
        self.assertIsNone(scene.model.active_bot('mira'))
        game.draw()
        self.assertEqual(scene.bot_status, {})

    def test_mq02_deploys_empty_free_rivet_and_freezes_it_with_every_wait_state(self):
        game = self.game()
        before_attributes = deepcopy(game.attributes.to_dict())
        scene = self.start_boar(game)
        model = scene.model
        bot = model.bot_for('mira')
        self.assertIsNotNone(bot)
        self.assertEqual(model.bots, (bot,))
        self.assertIs(model.active_bot('mira'), bot)
        self.assertEqual((bot.identifier, bot.owner_id, bot.ability_id),
                         ('rivet', 'mira', 'piston_jab'))
        self.assertEqual((bot.atb, bot.haste_turns), (0, 0))
        self.assertFalse(hasattr(bot, 'hp'))
        self.assertFalse(hasattr(bot, 'mp'))
        self.assertNotIn('hp', bot.attributes)
        self.assertNotIn('mp', bot.attributes)
        self.assertEqual([member.identifier for member in model.party], ['player', 'mira'])
        mira = model.combatant('mira')
        self.assertEqual(mira.mp, model.guest_definitions['mira']['attributes']['mp'])
        self.assertEqual(model.guest_definitions['mira']['attack'], 'bolt_shot')
        self.assertEqual(game.attributes.to_dict(), before_attributes)
        self.assertNotIn('piston_jab', model.available_actions('mira'))
        self.assertNotIn('rivet', model.available_actions('mira'))
        self.advance_until(game, scene, lambda: scene.tutorial_active,
                           guard_ready=False)
        self.assertTrue(scene.tutorial_active)
        before = self.state(scene)
        game.update(10, (1, 0), True)
        self.assertEqual(self.state(scene), before)
        self.ready_member(game, scene, 'mira')
        game.draw()
        self.assertEqual(set(scene.party_rows), {'player', 'mira'})
        self.assertEqual(scene.bot_status, {})
        labels = self.draw_text(game)
        self.assertNotIn('Rivet ATB', labels)
        self.assertFalse(any(text.startswith('Haste ·') for text in labels))
        before = self.state(scene)
        game.update(10, (1, 0), True)
        self.assertEqual(self.state(scene), before)
        click(game, scene.command_rects['guard'].center)
        self.assertIsNotNone(model.current_action)
        key(game, pygame.K_ESCAPE)
        self.assertTrue(scene.paused)
        before = self.state(scene)
        game.update(10, (0, 0), False)
        self.assertEqual(self.state(scene), before)
        key(game, pygame.K_ESCAPE)
        self.assertFalse(scene.paused)
        self.ready_member(game, scene, 'mira')
        click(game, scene.command_rects['attack'].center)
        self.assertEqual((model.current_action.actor, model.current_action.action,
                          model.current_action.target), ('mira', 'bolt_shot', 'enemy'))
        self.assertIn('Bolt Shot', self.draw_text(game))
        self.assertTrue(game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)]))
        self.assertTrue(scene.paused)
        before = self.state(scene)
        game.update(10, (0, 0), False)
        self.assertEqual(self.state(scene), before)
        self.assertTrue(game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)]))
        self.assertTrue(scene.paused)
        key(game, pygame.K_ESCAPE)
        self.assertFalse(scene.paused)

    def test_real_overclock_costs_five_mp_at_start_hastes_at_impact_and_rivet_attacks_in_sequence(self):
        game = self.game()
        scene = self.start_boar(game)
        model = scene.model
        bot = model.bot_for('mira')
        mira = model.combatant('mira')
        events = []
        drain = model.drain_events

        def record_events():
            batch = drain()
            events.extend(deepcopy(batch))
            return batch

        with patch.object(model, 'drain_events', side_effect=record_events):
            self.ready_member(game, scene, 'mira')
            before = self.state(scene)
            click(game, scene.command_rects['skills'].center)
            self.assertEqual(scene.command_menu, 'skills')
            self.assertEqual(set(scene.command_rects), {'overclock', 'back'})
            self.assertIn('Overclock', self.draw_text(game))
            self.assertIn('5 MP · Haste: +50% ATB for 8 bot turns.', self.draw_text(game))
            self.assertEqual(self.state(scene), before)
            click(game, scene.command_rects['back'].center)
            self.assertEqual(scene.command_menu, 'root')
            self.assertEqual(self.state(scene), before)
            initial_mp, initial_gauge = mira.mp, bot.atb
            click(game, scene.command_rects['skills'].center)
            click(game, scene.command_rects['overclock'].center)
            action = model.current_action
            self.assertEqual((action.actor, action.action, action.target),
                             ('mira', 'overclock', 'rivet'))
            self.assertEqual((mira.mp, mira.atb), (initial_mp-5, 0))
            self.assertEqual((bot.atb, bot.haste_turns), (initial_gauge, 0))
            self.assertEqual(scene._pose('mira')[0], 'overclock')
            self.assertEqual(scene._pose('rivet')[0], 'overclock')
            self.assertIn('Overclock', self.draw_text(game))
            self.assertIn('overclock', scene.sprites.actors['mira']['animations'])
            self.assertIn('overclock', scene.sprites.actors['rivet']['animations'])
            self.advance_until(game, scene, lambda: action.resolved)
            self.assertEqual(bot.haste_turns, 8)
            self.assertEqual(bot.atb, initial_gauge)
            labels = self.draw_text(game)
            self.assertIn('Haste', labels)
            self.assertFalse(any(text.startswith('Haste ·') for text in labels))
            self.assertEqual(scene.bot_status, {})
            self.assertTrue(game.save_progress())
            self.assert_durable_loadout_only(json.loads(self.path.read_text()))
            self.advance_until(game, scene, lambda: model.current_action is not None
                               and model.current_action.actor == 'rivet')
            jab = model.current_action
            self.assertEqual((jab.action, jab.target), ('piston_jab', 'enemy'))
            self.assertEqual(bot.atb, 0)
            self.assertEqual(bot.haste_turns, 8)
            self.assertIn('Piston Jab', self.draw_text(game))
            self.advance_until(game, scene, lambda: jab.resolved)
            self.assertGreater(jab.damage, 0)
            self.assertEqual(bot.haste_turns, 8)
            self.advance_until(game, scene, lambda: model.current_action is not jab)
            self.assertEqual(bot.haste_turns, 7)
            self.ready_member(game, scene, 'mira')
            remaining, fraction, mp = bot.haste_turns, bot.atb, mira.mp
            self.assertGreater(remaining, 0)
            self.assertLess(remaining, 8)
            click(game, scene.command_rects['skills'].center)
            click(game, scene.command_rects['overclock'].center)
            refresh = model.current_action
            self.assertEqual(refresh.action, 'overclock')
            self.assertEqual((mira.mp, bot.atb, bot.haste_turns), (mp-5, fraction, remaining))
            self.advance_until(game, scene, lambda: refresh.resolved)
            self.assertEqual((bot.atb, bot.haste_turns), (fraction, 8))
            self.advance_until(game, scene, lambda: model.ended)
        self.assertEqual(model.phase, 'victory')
        bot_events = [event for event in events if event.get('actor') == 'rivet'
                      and event.get('action') == 'piston_jab'
                      and event['type'] in ('action_started', 'impact')]
        self.assertGreaterEqual(len(bot_events), 4)
        self.assertEqual([event['type'] for event in bot_events],
                         ['action_started', 'impact']*(len(bot_events)//2))
        self.assertTrue(all(event['target'] == 'enemy' for event in bot_events))
        self.assertTrue(all(event['target'] in ('player', 'mira') for event in events
                            if event['type'] == 'impact' and event.get('actor') == 'enemy'))
        haste = [event for event in events if event['type'] == 'haste_applied']
        self.assertEqual(len(haste), 2)
        self.assertTrue(all(event['remaining_turns'] == 8 and event['rate_multiplier'] == 1.5
                            for event in haste))
        self.assertEqual((bot.atb, bot.haste_turns), (0, 0))
        self.assertEqual(model.bots, ())
        self.assertIsNone(model.active_bot('mira'))
        pending = json.loads(self.path.read_text())
        self.assertEqual(pending['post_battle']['stage'], 'pending')
        self.assert_durable_loadout_only(pending)
        before_receipts = game.battle_rewards.to_dict()['receipts']
        before_items = game.inventory.quantity('aether_emerald')
        # Reload before Spoils awards anything. Restoring this completed fight
        # must perform ordinary result cleanup instead of redeploying Rivet.
        returning = self.game(title=True)
        self.assertTrue(returning.has_saved_journey, returning.save_error)
        self.assertTrue(returning.begin_journey(True))
        self.assertTrue(returning.combat.active)
        restored = returning.combat.scene
        self.assertEqual(restored.model.phase, 'victory')
        self.assertEqual(restored.model.bots, ())
        self.assertIsNone(restored.model.bot_for('mira'))
        self.assertIsNone(restored.model.active_bot('mira'))
        self.assertEqual(restored._encounter_bots, ())
        self.assertEqual(restored.model.drain_events(), [])
        returning.draw()
        self.assertEqual(restored.bot_status, {})
        self.assertTrue(returning.combat.spoils.awarded)
        expected = pending['post_battle']['rewards']
        self.assertEqual(returning.battle_rewards.to_dict()['receipts'],
                         sorted(before_receipts+[pending['post_battle']['receipt']]))
        self.assertEqual(returning.inventory.quantity('aether_emerald'),
                         before_items+expected['drops']['aether_emerald'])
        for _ in range(3):
            returning.update(.05, (0, 0), False)
        self.assertEqual(returning.battle_rewards.to_dict()['receipts'],
                         sorted(before_receipts+[pending['post_battle']['receipt']]))
        acknowledge_battle_result(returning, restored)
        self.assertFalse(returning.combat.active)
        self.assertTrue(returning.mill_quest.encounter_cleared)
        self.assertTrue(returning.world.can_stand(returning.player.position))
        read_social(returning)
        self.assertTrue(returning.save_progress())
        saved = json.loads(self.path.read_text())
        self.assert_durable_loadout_only(saved)
        resumed = self.game(title=True)
        self.assertTrue(resumed.has_saved_journey, resumed.save_error)
        self.assertTrue(resumed.begin_journey(True))
        self.assertFalse(resumed.combat.active)
        self.assertEqual(resumed.bot_loadouts.battle_loadouts(), STARTING_LOADOUTS)
        self.assertEqual(resumed.attributes.to_dict(), returning.attributes.to_dict())
        self.assertEqual(resumed.battle_rewards.to_dict(), returning.battle_rewards.to_dict())

    def test_legacy_save_missing_bot_loadouts_restores_only_starting_configuration(self):
        game = self.game()
        seed_completed_mill(game)
        saved = json.loads(self.path.read_text())
        del saved['bot_loadouts']
        raw = json.dumps(saved)
        self.path.write_text(raw)
        resumed = self.game(title=True)
        self.assertTrue(resumed.has_saved_journey, resumed.save_error)
        self.assertEqual(self.path.read_text(), raw)
        self.assertTrue(resumed.begin_journey(True))
        self.assertFalse(resumed.combat.active)
        self.assertEqual(resumed.bot_loadouts.battle_loadouts(), STARTING_LOADOUTS)
        self.assertEqual(resumed.character_abilities.known_abilities('mira'),
                         frozenset({'overclock', 'rivet'}))
        self.assertEqual(resumed.inventory.to_dict(), saved['inventory'])
        self.assertEqual(resumed.battle_rewards.to_dict(), saved['battle_rewards'])
        self.assert_durable_loadout_only(json.loads(self.path.read_text()))

    def test_title_rejects_malformed_null_unknown_ability_and_future_bot_without_overwrite(self):
        game = self.game()
        seed_completed_mill(game)
        saved = json.loads(self.path.read_text())
        unknown_ability = deepcopy(saved['bot_loadouts'])
        unknown_ability['loadouts']['mira']['ability_id'] = 'unknown_ability'
        future_bot = deepcopy(saved['bot_loadouts'])
        future_bot['loadouts']['mira']['bot_id'] = 'future_bot'
        malformed = (None, {}, {'version': True, 'loadouts': STARTING_LOADOUTS},
                     unknown_ability, future_bot)
        for state in malformed:
            with self.subTest(state=state):
                data = deepcopy(saved)
                data['bot_loadouts'] = state
                raw = json.dumps(data)
                self.path.write_text(raw)
                resumed = self.game(title=True)
                self.assertFalse(resumed.has_saved_journey)
                self.assertIsNotNone(resumed.save_error)
                self.assertFalse(resumed.begin_journey(True))
                self.assertEqual(self.path.read_text(), raw)
                self.assertEqual(resumed.bot_loadouts.battle_loadouts(), STARTING_LOADOUTS)
                self.assertEqual(resumed.inventory.entries(), [])


if __name__ == '__main__':
    unittest.main()
