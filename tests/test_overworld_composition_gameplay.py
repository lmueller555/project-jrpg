"""The composed vale remains usable and the bridge really has a three-tile deck."""
from collections import deque
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from main import Game, Player
from overworld_travel import TOWN_EXIT, WORLD_ID
from overworld_world import OverworldWorld, TILE_SIZE


class OverworldCompositionGameplayTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.display.set_mode((480, 320))
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

    def tearDown(self):
        pygame.quit()

    @staticmethod
    def player(point):
        actor = Player.__new__(Player)
        actor.position = pygame.Vector2(point)
        actor.facing = 'front'
        actor.moving = actor.running = False
        actor.walk_ms = 0
        return actor

    def test_bridge_is_exactly_three_tiles_wide_with_full_foot_edge_limits(self):
        world = OverworldWorld()
        bridge = world.region['bridge']
        deck = world._tile_rect(bridge['deck_rect_tiles'])
        self.assertEqual(bridge['deck_width_tiles'], 3)
        self.assertEqual(deck.height, 3*TILE_SIZE)
        self.assertEqual(deck.centery, round(bridge['deck_center_tile_y']*TILE_SIZE))
        x = round(bridge['tile_position'][0]*TILE_SIZE)

        # No other progression fact restores the crossing.
        for facts in (set(), {'CH01_OPENING_REGION_RELEASED'}):
            world.set_progress(facts)
            self.assertTrue(all(world.is_blocked_at((x, y))
                                for y in range(deck.top, deck.bottom)))

        world.set_progress({bridge['repair_flag']})
        self.assertTrue(all(not world.is_blocked_at((x, y))
                            for y in range(deck.top, deck.bottom)))
        self.assertTrue(world.is_blocked_at((x, deck.top-1)))
        self.assertTrue(world.is_blocked_at((x, deck.bottom)))

        # The centre of a 12px-deep foot probe needs six pixels of deck on each
        # side. Crossing a nominal edge by a single pixel must remain blocked.
        self.assertTrue(world.can_stand((x, deck.top+6)))
        self.assertTrue(world.can_stand((x, deck.bottom-6)))
        self.assertFalse(world.can_stand((x, deck.top+5)))
        self.assertFalse(world.can_stand((x, deck.bottom-5)))

    def test_three_bridge_lanes_cross_only_after_independent_repair(self):
        world = OverworldWorld()
        bridge = world.region['bridge']
        center_y = bridge['deck_center_tile_y']*TILE_SIZE
        start_x = bridge['east_approach_tile'][0]*TILE_SIZE
        west_x = bridge['west_approach_tile'][0]*TILE_SIZE
        for lane in (-TILE_SIZE, 0, TILE_SIZE):
            with self.subTest(lane=lane):
                start = (start_x, center_y+lane)
                world.set_progress(set())
                self.assertTrue(world.can_stand(start))
                actor = self.player(start)
                actor.update((-1, 0), 8, world, running=True)
                self.assertGreater(actor.position.x, bridge['tile_position'][0]*TILE_SIZE)

                world.set_progress({bridge['repair_flag']})
                actor = self.player(start)
                actor.update((-1, 0), 8, world, running=True)
                self.assertLess(actor.position.x, west_x)
                self.assertTrue(world.can_stand(actor.position))
        for gate in world.gates:
            self.assertFalse(world.can_stand(gate['position']))

    def test_doorstep_paths_and_orchard_arrivals_connect_to_the_town(self):
        world = OverworldWorld(collision_cache_limit=256, metadata_cache_limit=256)
        goals = {}
        farms = [scene for scene in world.region['setpieces']
                 if scene.get('kind') == 'farmstead']
        self.assertEqual(len(farms), 3)
        for scene in farms:
            self.assertGreaterEqual(len(scene.get('door_approaches', [])), 3, scene['id'])
            for index, point in enumerate(scene['door_approaches']):
                goals[f'{scene["id"]}:door:{index}'] = tuple(point)
        orchards = [scene for scene in world.region['setpieces']
                    if scene.get('kind') in ('orchard', 'wayside')]
        self.assertTrue(orchards)
        for scene in orchards:
            self.assertIn('arrival_tile', scene, scene['id'])
            goals[f'{scene["id"]}:arrival'] = tuple(scene['arrival_tile'])
        for name, point in goals.items():
            self.assertTrue(world.can_stand(world._tile_point(point)), name)

        # Half-tile sampling can enter a legitimate 1.5-tile gate whose centre
        # lies between full-tile vertices. Finish with production movement to
        # each exact, potentially fractional doorstep.
        step = TILE_SIZE//2
        start = tuple(round(value/step)*step for value in world.town_exit)
        queue = deque([start])
        seen = {start}
        reachable = {start}
        while queue:
            x, y = queue.popleft()
            for point in ((x-step, y), (x+step, y), (x, y-step), (x, y+step)):
                if point in seen:
                    continue
                seen.add(point)
                if not (-140*TILE_SIZE < point[0] < 140*TILE_SIZE
                        and -96*TILE_SIZE < point[1] < 96*TILE_SIZE):
                    continue
                if world.can_stand(point):
                    reachable.add(point)
                    queue.append(point)
        for name, goal in goals.items():
            target = pygame.Vector2(world._tile_point(goal))
            connected = False
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    point = (round(target.x/step)*step+dx*step,
                             round(target.y/step)*step+dy*step)
                    if point not in reachable:
                        continue
                    actor = self.player(point)
                    # Small steps toward the actual doorstep catch a fence or
                    # prop placed between a clear tile and the clear endpoint.
                    for _ in range(100):
                        delta = target-actor.position
                        if delta.length() < 1.1:
                            connected = True
                            break
                        actor.update(delta, min(.025, delta.length()/72), world)
                    if connected:
                        break
                if connected:
                    break
            self.assertTrue(connected, name)

    def test_every_relocated_guard_has_a_clear_inside_approach_and_can_speak(self):
        root = Path(self.temporary.name)
        game = Game(fullscreen=False, start_on_title=False,
                    save_path=root/'journey.json', settings_path=root/'settings.json')
        game.audio.set_music(0)
        game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        game.player.position.update(TOWN_EXIT)
        self.assertTrue(game.overworld_travel.enter_region())
        game.transfer_cooldown = 0
        progress = game.quests.to_dict()
        for gate in game.world.gates:
            inside = 1 if gate['position'][1] < 0 else -1
            for guard in gate['guard_positions']:
                candidates = [(guard[0]+dx, guard[1]+inside*dy)
                              for dy in (24, 36) for dx in (0, -16, 16)]
                approach = next((point for point in candidates if game.world.can_stand(point)), None)
                self.assertIsNotNone(approach, gate['id'])
                game.player.position.update(approach)
                self.assertTrue(game.overworld_travel.interact(), gate['id'])
                speaker = game.social.resolve_speaker()
                self.assertIsNotNone(speaker)
                self.assertTrue(speaker.data['id'].startswith('road_guard:'+gate['id']+':'))
                game.social.cancel_script()
            self.assertFalse(game.world.can_stand(gate['position']))
        self.assertEqual(game.quests.to_dict(), progress)
        self.assertNotIn('CH01_OPENING_REGION_RELEASED', game.social.flags)
        self.assertNotIn('ELDEN_VALE_WEST_BRIDGE_REPAIRED', game.social.flags)
        self.assertEqual(game.world.data['id'], WORLD_ID)


if __name__ == '__main__':
    unittest.main()
