"""Real crossing movement, bounded travel and checkpointed bridge changes.

Selected positions and conditions are isolated system fixtures. No test stages
the future Carcovian attack or grants its unimplemented story receipts.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import PropertyMock, patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from bridge_condition import BridgeCondition, DEFAULT_REPAIR_FLAG
from bridge_crew import SCENE_ID
from main import Game
from overworld_travel import TOWN_EXIT


class BridgePlayableGameplayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='bridge-playable-game-')
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.path = self.folder/'journey.json'
        self.games = []

    def tearDown(self):
        for game in self.games:
            game.social.cancel_script()
            game.opening_audio.reset();game.regional_audio.reset();game.music.stop()
        pygame.quit()

    def game(self, *, title=False, persistent=True):
        game = Game(fullscreen=False, start_on_title=title, window_size=(960, 640),
                    save_path=self.path if persistent else None,
                    settings_path=self.folder/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        self.games.append(game)
        pygame.event.clear()
        return game

    @staticmethod
    def free_exploration(game):
        """Isolate crossing systems after checking the real New Game boundary."""
        game.social.cancel_script()
        game.opening.restore({'version': 1, 'stage': 'disabled'})
        game.opening_fade = game.transfer_cooldown = 0

    @staticmethod
    def stage(game, phase):
        game.overworld_travel.restore_bridge_condition(
            {'bridge_condition': BridgeCondition(phase).to_dict()})
        return game.overworld_world

    @staticmethod
    def deck(world):
        return world._tile_rect(world.region['bridge']['deck_rect_tiles'])

    @staticmethod
    def facts(game):
        snapshot = game.journey_snapshot()
        return {key: deepcopy(snapshot[key]) for key in (
            'quests', 'dialogue_flags', 'inventory', 'battle_rewards',
            'character_levels', 'character_abilities', 'party')}

    def station_east(self, game):
        world = game.overworld_world
        game.world = world
        preferred = world._tile_point(world.region['bridge']['east_approach_tile'])
        landing = game.overworld_travel._landing(world, preferred)
        self.assertIsNotNone(landing)
        self.assertEqual(world.bridge_bank(landing), 'east')
        game.player.position.update(landing)
        game.player.moving = game.player.running = False
        game.opening_fade = game.transfer_cooldown = 0
        game.camera.reset()
        return world

    def walk(self, game, destination, *, running=False, limit=1200):
        world = game.world
        goal = pygame.Vector2(destination)
        for index in range(limit):
            delta = goal-game.player.position
            if delta.length() < .35:
                game.player.moving = game.player.running = False
                return
            before = game.player.position.copy()
            seconds = min(.04, delta.length()/(108 if running else 72))
            game.update(seconds, delta, running)
            self.assertIs(game.world, world)
            self.assertFalse(game.combat.active)
            self.assertTrue(world.can_stand(game.player.position))
            self.assertGreater(game.player.position.distance_to(before), 0,
                               ('Blocked crossing fixture', list(before), list(goal)))
            if index % 40 == 0:game.draw()
        self.fail(('Crossing movement timed out', list(game.player.position), list(goal)))

    def test_real_new_game_opens_an_intact_bridge_walkable_and_runnable_both_ways(self):
        game = self.game(title=True)
        game.title.selected = game.title.options.index('New Game')
        self.assertTrue(game.handle_events([
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=False),
            pygame.event.Event(pygame.KEYUP, key=pygame.K_RETURN)]))
        game.update(.7, (0, 0), False)
        self.assertFalse(game.on_title)
        self.assertEqual(game.opening.stage, 'wake')
        self.assertEqual(game.overworld_travel.bridge_condition.to_dict(),
                         BridgeCondition('intact').to_dict())
        self.assertNotIn(DEFAULT_REPAIR_FLAG, game.social.flags)
        self.free_exploration(game)
        world = self.station_east(game)
        deck = self.deck(world)
        east = (deck.right+12, deck.centery)
        west = (deck.left-12, deck.centery)
        facts = self.facts(game)
        game.player.position.update(east)
        self.assertTrue(world.can_stand(east));self.assertTrue(world.can_stand(west))
        for running in (False, True):
            with self.subTest(running=running):
                self.walk(game, west, running=running)
                self.assertEqual(world.bridge_bank(game.player.position), 'west')
                self.walk(game, east, running=running)
                self.assertEqual(world.bridge_bank(game.player.position), 'east')
        self.assertEqual(self.facts(game), facts)
        self.assertFalse(world.bridge_crew.active)

    def test_west_landing_is_bounded_and_returns_to_the_same_crossing(self):
        game = self.game();world = self.station_east(game)
        deck = self.deck(world)
        game.player.position.update(deck.left-12, deck.centery)
        road = next(record for record in world.region['roads'] if record['id'] == 'south_town_road')
        approach = world._tile_point(world.region['bridge']['west_approach_tile'])
        self.walk(game, approach)
        points = [world._tile_point(point) for point in road['points']]
        start = min(range(len(points)), key=lambda index: pygame.Vector2(points[index]).distance_to(approach))
        route = points[start:]
        terminal = world._tile_point(world.region['far_bank']['terminal_tile'])
        self.assertEqual(tuple(route[-1]), tuple(terminal))
        for goal in route:self.walk(game, goal, running=True)
        self.assertEqual(world.bridge_bank(game.player.position), 'west')
        self.assertFalse(world.region['far_bank']['future_exit']['destination_ready'])
        origin = game.player.position.copy()
        # The road ending remains a place to turn around. Repeated southward
        # movement must stop at visible authored terrain, never change scenes.
        for _ in range(120):game.update(.05, (0, 1), True)
        self.assertIs(game.world, world)
        self.assertTrue(world.can_stand(game.player.position))
        self.assertLess(game.player.position.distance_to(origin), 8*24)
        self.walk(game, terminal)
        for goal in reversed(route):self.walk(game, goal, running=True)
        self.walk(game, (deck.left-12, deck.centery))
        self.walk(game, (deck.right+12, deck.centery))
        self.assertNotIn('CH01_OPENING_REGION_RELEASED', game.social.flags)

    def test_manual_and_scene_autosave_continue_on_the_playable_west_bank(self):
        game = self.game()
        game.player.position.update(TOWN_EXIT)
        self.assertTrue(game.overworld_travel.enter_region())
        world = game.world;deck = self.deck(world)
        west = (deck.left-12, deck.centery)
        self.assertTrue(world.can_stand(west))
        game.player.position.update(west)
        game.opening_fade = game.transfer_cooldown = 0
        game.saves.update(.1)
        autos = game.saves.library.autos(game.saves.campaign)
        self.assertEqual(len(autos), 1)
        self.assertEqual(autos[0]['metadata']['reason'], 'scene')
        self.assertTrue(game.saves.manual(1), game.saves.notice)
        manual = deepcopy(game.saves.library.manual(1))
        rows = [('Slot 1', manual, ('manual', 1)),
                next(row for row in game.saves.entries() if row[2][0] == 'auto')]
        for row in rows:
            with self.subTest(kind=row[2][0]):
                game.update(.6, (0, 0), False) # Let a prior Continue's fade settle.
                self.assertEqual(game.opening_fade, 0)
                self.assertEqual(game.transfer_cooldown, 0)
                self.walk(game, (deck.right+12, deck.centery), running=True)
                self.assertEqual(world.bridge_bank(game.player.position), 'east')
                self.assertTrue(game.overworld_travel.change_bridge_condition('destroyed'))
                self.assertTrue(game.saves.load(row), game.save_error)
                self.assertEqual(game.overworld_travel.bridge_condition.phase, 'intact')
                self.assertIs(game.world, world)
                self.assertEqual(tuple(game.player.position), west)
                self.assertEqual(world.bridge_bank(game.player.position), 'west')
                self.assertTrue(world.can_stand(game.player.position))
                game.draw()

    def test_legacy_southwest_road_footpoint_lands_locally_on_the_west_bank(self):
        source = self.game()
        payload = source.journey_snapshot()
        payload['overworld']['bridge_condition'] = BridgeCondition('destroyed', 'legacy_layout').to_dict()
        payload['player'].update(scene=source.overworld_world.data['id'],
                                 position=[-174*24, 182*24], facing='back')
        before = {key: deepcopy(payload[key]) for key in self.facts(source)}
        self.path.write_text(json.dumps(payload)+'\n', encoding='utf-8')
        raw = self.path.read_bytes()
        loaded = self.game(title=True)
        self.assertTrue(loaded.has_saved_journey, loaded.save_error)
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertTrue(loaded.begin_journey(True), loaded.save_error)
        world = loaded.overworld_world
        self.assertIs(loaded.world, world)
        self.assertEqual(loaded.overworld_travel.bridge_condition.phase, 'intact')
        self.assertEqual(world.bridge_bank(loaded.player.position), 'west')
        self.assertNotEqual(tuple(loaded.player.position), tuple(world.data['spawn']))
        self.assertTrue(world.can_stand(loaded.player.position))
        self.assertLess(pygame.Vector2(loaded.player.position).distance_to(
            world._tile_point(world.region['bridge']['west_approach_tile'])), 4*24)
        self.assertEqual(self.facts(loaded), before)
        self.assertEqual(loaded.player.facing, 'back')

    def test_explicit_destroyed_and_restored_saves_keep_their_selected_conditions(self):
        source = self.game();base = source.journey_snapshot()
        source_world = source.overworld_world
        east = source_world._tile_point(source_world.region['bridge']['east_approach_tile'])
        for phase in ('destroyed', 'restored'):
            with self.subTest(phase=phase):
                payload = deepcopy(base)
                payload['overworld']['bridge_condition'] = BridgeCondition(phase).to_dict()
                payload['dialogue_flags'] = ([DEFAULT_REPAIR_FLAG] if phase == 'destroyed' else [])
                payload['player'].update(scene=source_world.data['id'], position=list(east))
                self.path.write_text(json.dumps(payload)+'\n', encoding='utf-8')
                loaded = self.game(title=True)
                self.assertTrue(loaded.begin_journey(True), loaded.save_error)
                world = loaded.overworld_world
                self.assertIs(loaded.world, world)
                self.assertEqual(tuple(loaded.player.position), tuple(east))
                self.assertEqual(world.bridge_condition.to_dict(), BridgeCondition(phase).to_dict())
                self.assertEqual(world.can_stand(self.deck(world).center), phase == 'restored')
                self.assertEqual(loaded.journey_snapshot()['dialogue_flags'], payload['dialogue_flags'])

    def test_checkpointed_change_relocates_underfoot_player_and_npc_without_story_progress(self):
        game = self.game();world = self.station_east(game)
        deck = self.deck(world)
        game.player.position.update(deck.centerx+24, deck.centery)
        actor = world.grain_farm.loader
        actor.position.update(deck.centerx-24, deck.centery)
        original_actor = actor
        original_position = actor.position.copy()
        actor_bank = world.bridge_bank(actor.position)
        player_bank = world.bridge_bank(game.player.position)
        self.assertEqual(player_bank, 'east')
        facts = self.facts(game)
        farm = deepcopy(world.grain_farm.to_dict())
        self.assertTrue(game.overworld_travel.change_bridge_condition('destroyed'))
        self.assertIs(world.grain_farm.loader, original_actor)
        self.assertTrue(world.can_stand(game.player.position))
        self.assertTrue(world.can_stand(actor.position, actor.probe_size, actor))
        self.assertNotEqual(actor.position, original_position)
        self.assertEqual(world.bridge_bank(actor.position), actor_bank)
        self.assertEqual(world.bridge_bank(game.player.position), player_bank)
        self.assertFalse(actor.blocker.colliderect(world.probe_rect(game.player.position)))
        self.assertEqual(world.grain_farm.to_dict(), farm)
        self.assertEqual(self.facts(game), facts)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['overworld']['bridge_condition'], BridgeCondition('destroyed').to_dict())
        self.assertEqual(saved['player']['position'], list(game.player.position))

    def test_failed_checkpoint_restores_condition_feet_and_original_save_bytes(self):
        game = self.game();world = self.station_east(game)
        deck = self.deck(world)
        game.player.position.update(deck.centerx+24, deck.centery)
        self.assertEqual(world.bridge_bank(game.player.position), 'east')
        self.assertTrue(game.save_progress())
        raw = self.path.read_bytes()
        position = game.player.position.copy()
        condition = game.overworld_travel.bridge_condition.to_dict()
        actors = [(actor, tuple(actor.position)) for actor in world.npcs]
        with patch('save_game.os.replace', side_effect=OSError('bridge checkpoint blocked')) as replace:
            self.assertFalse(game.overworld_travel.change_bridge_condition('destroyed'))
            self.assertTrue(replace.called, 'The fixture must reach the failed checkpoint.')
        self.assertEqual(game.overworld_travel.bridge_condition.to_dict(), condition)
        self.assertEqual(world.bridge_condition.to_dict(), condition)
        self.assertEqual(game.player.position, position)
        self.assertEqual([(actor, tuple(actor.position)) for actor, _ in actors], actors)
        self.assertTrue(world.can_stand(position))
        self.assertEqual(self.path.read_bytes(), raw)

    def test_closed_west_landing_refuses_destruction_without_mutation_or_checkpoint(self):
        game = self.game();world = self.station_east(game)
        game.player.position.update(world._tile_point(world.region['bridge']['west_approach_tile']))
        self.assertTrue(world.can_stand(game.player.position))
        self.assertEqual(world.bridge_bank(game.player.position), 'west')
        self.assertFalse(world.region['far_bank']['future_exit']['destination_ready'])
        self.assertTrue(game.save_progress())
        raw = self.path.read_bytes()
        before = deepcopy(game.journey_snapshot())
        positions = [(actor, tuple(actor.position)) for actor in [game.player, *world.npcs]]
        with patch.object(game, 'save_progress', side_effect=AssertionError('Unsafe change checkpointed')):
            self.assertFalse(game.overworld_travel.change_bridge_condition('destroyed'))
        self.assertEqual(game.journey_snapshot(), before)
        self.assertEqual([(actor, tuple(actor.position)) for actor, _ in positions], positions)
        self.assertEqual(world.bridge_condition.phase, 'intact')
        self.assertTrue(world.can_stand(self.deck(world).center))
        self.assertEqual(self.path.read_bytes(), raw)

    def test_destroyed_west_checkpoint_refuses_continue_readably_without_overwriting(self):
        source = self.game();world = source.overworld_world
        payload = source.journey_snapshot()
        payload['overworld']['bridge_condition'] = BridgeCondition('destroyed').to_dict()
        payload['player'].update(scene=world.data['id'],
                                 position=list(world._tile_point(world.region['bridge']['west_approach_tile'])))
        self.path.write_text(json.dumps(payload)+'\n', encoding='utf-8')
        raw = self.path.read_bytes()
        loaded = self.game(title=True)
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertFalse(loaded.begin_journey(True))
        self.assertTrue(loaded.on_title)
        self.assertRegex(loaded.save_error or '', r'(?i)(bridge|crossing|west bank)')
        self.assertEqual(self.path.read_bytes(), raw)

    def test_owned_dialogue_is_cancelled_only_after_a_successful_checkpoint(self):
        game = self.game();world = self.stage(game, 'destroyed');game.world = world
        crew = world.bridge_crew
        state = {'sorted': 3, 'tea_beat': 1, 'request_read': False,
                 'greeted': [], 'cup_phase': 'tender'}
        crew.restore(state)
        game.player.position.update(-2376, 642)
        self.assertTrue(crew.interact(game))
        self.assertEqual(game.social.script_identifier, SCENE_ID)
        with patch.object(game, 'save_progress', return_value=False):
            self.assertFalse(game.overworld_travel.change_bridge_condition('intact'))
        self.assertTrue(game.social.active)
        self.assertEqual(game.social.script_identifier, SCENE_ID)
        self.assertEqual(crew.to_dict(), state)
        self.assertEqual(world.bridge_condition.phase, 'destroyed')
        self.assertTrue(game.overworld_travel.change_bridge_condition('intact'))
        self.assertFalse(game.social.active)
        self.assertEqual(crew.to_dict(), state)
        self.assertEqual(world.bridge_condition.phase, 'intact')

    def test_unrelated_dialogue_and_busy_interfaces_refuse_changes_without_checkpoints(self):
        game = self.game();world = self.station_east(game)
        expected = game.overworld_travel.bridge_condition.to_dict()
        self.assertTrue(game.social.start_script(
            [{'speaker': 'caelan', 'text': 'An unrelated conversation.'}],
            identifier='bridge_change_unrelated'))
        with patch.object(game, 'save_progress') as checkpoint:
            self.assertFalse(game.overworld_travel.change_bridge_condition('destroyed'))
            checkpoint.assert_not_called()
        self.assertTrue(game.social.active)
        game.social.cancel_script()
        with patch.object(game, 'save_progress') as checkpoint:
            for owner, field in ((game, 'on_title'), (game.pause, 'is_open'),
                                 (game.inventory_ui, 'is_open'), (game, 'map_open')):
                with self.subTest(field=field), patch.object(owner, field, True):
                    self.assertFalse(game.overworld_travel.change_bridge_condition('destroyed'))
            with patch.object(type(game.combat), 'active', new_callable=PropertyMock, return_value=True):
                self.assertFalse(game.overworld_travel.change_bridge_condition('destroyed'))
            game.cinematic = SimpleNamespace(active=True)
            self.assertFalse(game.overworld_travel.change_bridge_condition('destroyed'))
            game.cinematic = None
            checkpoint.assert_not_called()
        self.assertEqual(game.overworld_travel.bridge_condition.to_dict(), expected)
        self.assertIs(game.world, world)

    def test_missing_save_ownership_and_preview_refuse_changes(self):
        game = self.game(persistent=False)
        expected = game.overworld_travel.bridge_condition.to_dict()
        self.assertFalse(game.overworld_travel.change_bridge_condition('destroyed'))
        self.assertEqual(game.overworld_travel.bridge_condition.to_dict(), expected)
        preview = self.game();preview._is_gallery_preview = True
        self.assertFalse(preview.overworld_travel.change_bridge_condition('destroyed'))
        self.assertEqual(preview.overworld_travel.bridge_condition.to_dict(), expected)

    def test_same_condition_is_a_noop_and_offscreen_town_changes_preserve_town_feet(self):
        game = self.game()
        before = (game.world, tuple(game.player.position), self.facts(game))
        with patch.object(game, 'save_progress', side_effect=AssertionError('No-op checkpointed')):
            self.assertTrue(game.overworld_travel.change_bridge_condition('intact'))
        self.assertTrue(game.overworld_travel.change_bridge_condition('restored'))
        self.assertEqual((game.world, tuple(game.player.position), self.facts(game)), before)
        self.assertEqual(json.loads(self.path.read_text())['overworld']['bridge_condition'],
                         BridgeCondition('restored').to_dict())


if __name__ == '__main__':unittest.main()
