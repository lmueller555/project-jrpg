"""Environment detail must leave regional travel and older journeys usable."""
from collections import deque
import json
import math
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from main import Game
from overworld_world import OverworldWorld, TILE_SIZE
from overworld_travel import TOWN_EXIT, WORLD_ID


class OverworldPolishGameplayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        pygame.display.init()
        pygame.display.set_mode((480, 320))

    def tearDown(self):
        pygame.quit()

    def fixture(self, props):
        manifest = {
            'version': 1, 'id': WORLD_ID, 'name': 'Footprint fixture',
            'kind': 'overworld', 'tile_size': TILE_SIZE, 'chunk_size': 16,
            'detail_art_manifest': 'assets/terrain/overworld/elden_vale/polish/art.json',
            'bounds_tiles': [-32, -32, 64, 64], 'spawn_tile': [8, 8],
            'terrain': {'rivers': [], 'forests': [], 'fields': [], 'hills': []},
            'roads': [], 'walls': [], 'gates': [], 'landmarks': [],
            'setpieces': [{'id': 'yard', 'kind': 'farm', 'name': 'Farmyard',
                           'tile_position': [12, 8], 'props': props}],
        }
        path = self.root/'fixture.json'
        path.write_text(json.dumps(manifest))
        return OverworldWorld(path, collision_cache_limit=1, metadata_cache_limit=1)

    def test_authored_solid_straddles_chunk_boundary_after_eviction(self):
        world = self.fixture([
            {'id': 'solid', 'key': 'rock', 'tile_position': [16, 8], 'solid': [32, 16]},
            {'id': 'decoration', 'key': 'rock', 'tile_position': [12, 8]},
        ])
        # The authored rock is centred on the x=384 seam. Feet wholly in either
        # neighbouring chunk must see its overlapping solid footprint.
        for x in (360, 384, 408):
            self.assertFalse(world.can_stand((x, 192)), x)
        for x in (344, 424):
            self.assertTrue(world.can_stand((x, 192)), x)
        self.assertTrue(world.can_stand((12*TILE_SIZE, 8*TILE_SIZE)),
                        'A decoration without a solid footprint must stay passable')
        for point in ((-600, -600), (600, 600), (-600, 600)):
            world.can_stand(point)
        world.set_progress({'unrelated_story_fact'})
        self.assertFalse(world.can_stand((360, 192)))
        self.assertFalse(world.can_stand((408, 192)))
        self.assertLessEqual(world.cache_stats['collision_chunks'], 1)
        self.assertLessEqual(world.cache_stats['metadata_chunks'], 1)

    def test_new_farmyard_and_charm_approaches_are_connected_to_town(self):
        world = OverworldWorld(collision_cache_limit=256, metadata_cache_limit=256)
        setpieces = world.region.get('setpieces', [])
        self.assertGreaterEqual(sum(piece.get('kind') in ('farm', 'farmstead')
                                    for piece in setpieces), 3)
        goals = {piece['id']: tuple(piece.get('approach_tile', piece['tile_position']))
                 for piece in setpieces}
        for name, point in goals.items():
            self.assertTrue(world.can_stand(world._tile_point(point)), name)

        start = tuple(round(value/TILE_SIZE) for value in world.town_exit)
        queue = deque([start])
        visited = {start}
        remaining = set(goals.values())
        while queue and remaining:
            point = queue.popleft()
            remaining.discard(point)
            x, y = point
            for neighbour in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                if neighbour in visited:
                    continue
                visited.add(neighbour)
                if not (-140 < neighbour[0] < 140 and -96 < neighbour[1] < 96):
                    continue
                if world.can_stand(world._tile_point(neighbour)):
                    queue.append(neighbour)
        unreachable = [name for name, point in goals.items() if point in remaining]
        self.assertFalse(unreachable, f'Blocked setpiece approaches: {unreachable}')

    def test_opening_road_centres_remain_clear_of_new_buildings_and_fences(self):
        world = OverworldWorld(collision_cache_limit=256, metadata_cache_limit=256)
        damaged = world._tile_rect(world.region['bridge']['damage_rect_tiles']).inflate(48, 24)
        samples = 0
        for road in world.region['roads']:
            for a, b in zip(road['points'], road['points'][1:]):
                distance = math.dist(a, b)
                steps = max(1, math.ceil(distance*2))
                for index in range(steps+1):
                    point = tuple((a[axis]+(b[axis]-a[axis])*index/steps)*TILE_SIZE
                                  for axis in (0, 1))
                    # The beyond-wall corridors and far side of the destroyed
                    # bridge are deliberately unavailable during the opening.
                    if not (-98*TILE_SIZE < point[0] < 108*TILE_SIZE
                            and -93*TILE_SIZE < point[1] < 93*TILE_SIZE):
                        continue
                    if damaged.collidepoint(point):
                        continue
                    self.assertTrue(world.can_stand(point), f'{road["id"]}: {point}')
                    samples += 1
        self.assertGreater(samples, 500)

    def test_continue_from_a_newly_occupied_saved_spot_keeps_region_and_progress(self):
        save_path = self.root/'journey.json'

        def game(title=False):
            instance = Game(fullscreen=False, start_on_title=title,
                            save_path=save_path, settings_path=self.root/'settings.json')
            instance.audio.set_music(0)
            instance.audio.set_effects(0)
            instance.opening_fade = instance.transfer_cooldown = 0
            pygame.event.clear()
            return instance

        first = game()
        first.player.position.update(TOWN_EXIT)
        self.assertTrue(first.overworld_travel.enter_region())
        solid = next(prop for piece in first.world.region['setpieces']
                     for prop in piece['props'] if prop.get('solid'))
        occupied = first.world._tile_point(solid['tile_position'])
        self.assertFalse(first.world.can_stand(occupied))
        # An older version could save here before this farm prop existed.
        first.player.position.update(occupied)
        progress = first.quests.to_dict()
        self.assertTrue(first.save_progress())
        restored = game(True)
        self.assertTrue(restored.has_saved_journey)
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(restored.world.data['id'], WORLD_ID)
        self.assertTrue(restored.world.can_stand(restored.player.position))
        self.assertNotEqual(tuple(restored.player.position), tuple(occupied))
        self.assertEqual(restored.quests.to_dict(), progress)


if __name__ == '__main__':
    unittest.main()
