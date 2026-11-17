"""Walk the expanded town's public road, rather than teleporting to its exit."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from main import Game
from overworld_travel import (WORLD_ID, TOWN_EXIT, TOWN_RETURN, TOWN_EXIT_RECT,
                              town_exit_contract)

ROOT = Path(__file__).resolve().parents[1]


class TownSouthernExitContracts(unittest.TestCase):
    def test_authored_road_and_runtime_contact_reach_the_expanded_south_edge(self):
        recipe = json.loads((ROOT/'assets/source/maps/eldenmere/town_hd/recipe.json').read_text())
        town = json.loads((ROOT/'assets/maps/eldenmere/playable/map.json').read_text())
        contact = town['overworld_exit']
        self.assertEqual(contact, recipe['overworld_exit'])
        self.assertEqual(town['destinations']['southern_exit'], contact['position'])
        self.assertEqual(TOWN_EXIT, tuple(contact['position']))
        self.assertEqual(TOWN_RETURN, tuple(contact['return_position']))
        self.assertEqual(TOWN_EXIT_RECT, pygame.Rect(contact['rect']))
        self.assertEqual(town_exit_contract({}),
                         ((516, 1332), (516, 1284), pygame.Rect(492, 1320, 48, 24)))
        rect = pygame.Rect(contact['rect'])
        self.assertEqual(rect.bottom, town['size_pixels'][1])
        self.assertTrue(rect.collidepoint(contact['position']))
        self.assertFalse(rect.collidepoint(contact['return_position']))
        self.assertLess(contact['return_position'][1], rect.top)
        x = contact['position'][0]
        self.assertTrue(any(a[0] == b[0] == x and min(a[1], b[1]) < 1344
                            and max(a[1], b[1]) >= town['size_pixels'][1]
                            for a, b in recipe['road_centerlines']))


class TownSouthernExitGameplay(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'journey.json'
        self.settings = Path(self.temp.name)/'settings.json'
        self.game = self.make_game()

    def tearDown(self):
        self.game.music.stop()
        pygame.quit()
        self.temp.cleanup()

    def make_game(self):
        game = Game(fullscreen=False, start_on_title=True, save_path=self.path,
                    settings_path=self.settings)
        game.audio.set_music(0)
        game.audio.set_effects(0)
        game.on_title = False
        game.opening.restore({'version': 1, 'stage': 'disabled'})
        game.opening_fade = game.transfer_cooldown = 0
        game.world = game.town
        pygame.event.clear()
        return game

    def walk_to(self, game, target, running=False):
        """Follow a clear cardinal road segment with the production update loop."""
        for _ in range(600):
            delta = pygame.Vector2(target)-game.player.position
            if max(abs(delta.x), abs(delta.y)) <= 1.9:
                return
            direction = (int(delta.x > 1.9)-int(delta.x < -1.9),
                         int(delta.y > 1.9)-int(delta.y < -1.9))
            self.assertTrue(0 in direction, ('Expected cardinal segment', target))
            self.assertIs(game.world, game.town)
            game.update(1/60, direction, running)
        self.fail(('Road segment did not complete', target, tuple(game.player.position)))

    def leave_south(self, game, running=False, minimum_departure_y=1600):
        visited = []
        for _ in range(450):
            previous = tuple(game.player.position)
            game.update(1/60, (0, 1), running)
            if game.world is not game.town:
                self.assertEqual(game.world.data['id'], WORLD_ID)
                self.assertGreaterEqual(previous[1], minimum_departure_y,
                                        'Departed at the obsolete interior trigger')
                self.assertTrue(game.world.can_stand(game.player.position))
                return visited
            visited.append(tuple(game.player.position))
        self.fail(('Southern road failed to leave town', tuple(game.player.position)))

    def return_north(self, game):
        for _ in range(180):
            game.update(1/60, (0, -1), False)
            if game.world is game.town:
                self.assertTrue(game.world.can_stand(game.player.position))
                self.assertEqual(game.player.facing, 'back')
                return
        self.fail('Northern approach to regional miniature did not return to town')

    def test_walk_and_run_pass_old_boundary_and_shops_before_automatic_roundtrip(self):
        game = self.game
        for running in (False, True):
            with self.subTest(running=running):
                game.world = game.town
                game.player.position.update(528, 1260)
                game.transfer_cooldown = 0
                trace = self.leave_south(game, running)
                self.assertTrue(any(y > 1490 for _, y in trace), 'Never traversed business lane')
                self.return_north(game)
                self.assertEqual(tuple(game.player.position),
                                 tuple(game.town.data['overworld_exit']['return_position']))
                game.update(.6, (0, 0), False)
                self.assertIs(game.world, game.town, 'Return immediately bounced into region')
                # Leaving the return landing must rearm the same automatic exit.
                self.leave_south(game, running)

    def test_live_map_contract_controls_departure_and_return_without_default_constants(self):
        game = self.game
        game.town.data['overworld_exit'] = {
            'position': [528, 1536], 'return_position': [528, 1488],
            'rect': [504, 1524, 48, 24],
        }
        game.player.position.update(528, 1488)
        self.leave_south(game, minimum_departure_y=1515)
        self.assertLess(game.exterior_position.y, 1540)
        self.return_north(game)
        self.assertEqual(tuple(game.player.position), (528, 1488))

    def test_businesses_remain_accessible_from_the_same_public_lane(self):
        game = self.game
        game.player.position.update(528, 1488)
        for name in ('inn', 'item_shop'):
            with self.subTest(business=name):
                door = next(door for door in game.town.doors if door.data['id'] == name)
                self.walk_to(game, (door.data['anchor'][0], 1488))
                for _ in range(120):
                    game.update(1/60, (0, -1), False)
                    if game.world is not game.town:
                        break
                self.assertEqual(game.world.data['id'], name)
                self.assertTrue(game.world.can_stand(game.player.position))
                game.update(.3, (0, 0), False)
                exit_door = game.world.doors[0]
                # Room spawn is its authored arrival landing; continue toward
                # the actual door rather than setting the player on a trigger.
                direction = -1 if exit_door.data['entry_side'] == 'north' else 1
                for _ in range(180):
                    game.update(1/60, (0, direction), False)
                    if game.world is game.town:
                        break
                self.assertIs(game.world, game.town)
                self.assertTrue(game.world.can_stand(game.player.position))
                self.walk_to(game, (game.player.position.x, 1488))
                self.walk_to(game, (528, 1488))
        self.leave_south(game)

    def test_continue_from_old_road_and_business_district_preserves_feet_and_can_leave(self):
        game = self.game
        for position in ((516, 1284), (528, 1488)):
            with self.subTest(position=position):
                game.world = game.town
                game.player.position.update(position)
                game.transfer_cooldown = game.opening_fade = 0
                expected_quests = copy.deepcopy(game.quests.to_dict())
                expected_party = copy.deepcopy(game.party.to_dict())
                self.assertTrue(game.save_progress(), game.save_error)
                restored = Game(fullscreen=False, start_on_title=True,
                                save_path=self.path, settings_path=self.settings)
                try:
                    restored.audio.set_music(0)
                    restored.audio.set_effects(0)
                    self.assertTrue(restored.has_saved_journey, restored.save_error)
                    self.assertTrue(restored.begin_journey(True), restored.save_error)
                    self.assertIs(restored.world, restored.town)
                    self.assertEqual(tuple(restored.player.position), position)
                    self.assertEqual(restored.quests.to_dict(), expected_quests)
                    self.assertEqual(restored.party.to_dict(), expected_party)
                    restored.opening_fade = restored.transfer_cooldown = 0
                    self.walk_to(restored, (528, position[1]))
                    self.leave_south(restored)
                finally:
                    restored.music.stop()
