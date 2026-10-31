"""Regional cartography stays bounded, geographically correct, and modal."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
                  PYGAME_HIDE_SUPPORT_PROMPT='1')

import pygame

from map_ui import MapUI
from overworld_map import RegionalMapUI
from ui_style import UIStyle


ROOT = Path(__file__).resolve().parents[1]


class MetadataOnlyRegion:
    is_overworld = True

    def __init__(self, data):self.region = self.data = data

    @property
    def overview(self):raise AssertionError('Regional map must never render the world')

    def draw(self, *args, **kwargs):raise AssertionError('No chunk rendering in a map')


class RegionalMapTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        window = pygame.display.set_mode((1100, 750))
        self.data = json.loads((ROOT/'assets/maps/overworld/elden_vale/region.json').read_text())
        town_data = json.loads((ROOT/'assets/maps/eldenmere/playable/map.json').read_text())
        town = SimpleNamespace(data=town_data, size=town_data['size_pixels'])
        self.game = SimpleNamespace(world=MetadataOnlyRegion(self.data), town=town, window=window,
            player=SimpleNamespace(position=pygame.Vector2(12*24, -20*24)),
            exterior_position=pygame.Vector2(516, 1284), map_open=True,
            audio=SimpleNamespace(text_scale=1, reduced_motion=False, effects_volume=0),
            social=SimpleNamespace(flags=set()), quest_ui=SimpleNamespace(draw_map_markers=Mock()))
        def to_canvas(point):
            width, height = self.game.window.get_size()
            scale = max(1, min(width//480, height//320))
            x, y = ((point[0]-(width-480*scale)//2)/scale,
                    (point[1]-(height-320*scale)//2)/scale)
            return (x, y) if 0 <= x < 480 and 0 <= y < 320 else None
        self.game.to_canvas = to_canvas
        self.game.ui = UIStyle(self.game)
        self.map_ui = MapUI(self.game)
        self.map = self.map_ui._regional_map

    def tearDown(self):pygame.quit()

    def event(self, kind, **values):
        return self.map_ui.handle_event(pygame.event.Event(kind, **values))

    def screen_point(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        return (round((width-480*scale)//2+point[0]*scale),
                round((height-320*scale)//2+point[1]*scale))

    def test_negative_global_origin_preserves_player_and_landmark_coordinates(self):
        x, y, width, height = self.data['bounds_tiles']
        northwest = self.map.world_to_map((x*24, y*24))
        southeast = self.map.world_to_map(((x+width)*24, (y+height)*24))
        self.assertGreaterEqual(northwest[0], self.map.map_rect.left)
        self.assertGreaterEqual(northwest[1], self.map.map_rect.top)
        self.assertLessEqual(southeast[0], self.map.map_rect.right)
        self.assertLessEqual(southeast[1], self.map.map_rect.bottom)
        self.assertAlmostEqual((southeast[0]-northwest[0])/(southeast[1]-northwest[1]), width/height)
        for record in self.map.landmarks:
            with self.subTest(landmark=record['id']):
                point = self.map.tile_to_map(record['tile_position'])
                self.assertTrue(self.map.map_rect.collidepoint(point))
                self.assertTrue(self.map.marker_rects[record['id']].collidepoint(point))
        player = self.map.world_to_map(self.game.player.position)
        self.assertEqual(player, self.map.tile_to_map((12, -20)))
        self.assertLess(player[1], self.map.tile_to_map((12, 0))[1])
        self.assertLess(self.map.tile_to_map((-111, 30))[0], player[0])

    def test_zoom_keeps_pointer_anchor_and_drag_is_clamped_and_released(self):
        point = (self.map.map_rect.centerx+18, self.map.map_rect.centery-12)
        before = self.map.map_to_tile(point)
        self.map.zoom_at(point, 3)
        self.assertLess(self.map.map_to_tile(point).distance_to(before), .001)
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=self.screen_point(self.map.map_rect.center))
        self.event(pygame.MOUSEMOTION, pos=self.screen_point((300, 270)))
        self.event(pygame.MOUSEBUTTONUP, button=1, pos=self.screen_point((300, 270)))
        center = self.map.center.copy()
        self.event(pygame.MOUSEMOTION, pos=self.screen_point((40, 80)))
        self.assertEqual(self.map.center, center)
        self.map.zoom_at(point, 1000)
        self.assertEqual(self.map.zoom, self.map.MAX_ZOOM)
        self.map.zoom_at(point, -1000)
        self.assertEqual(self.map.zoom, 1)
        self.assertEqual(self.map.center, pygame.Vector2(0, 0))

    def test_letterboxed_hover_select_close_and_repeat_controls(self):
        record = next(record for record in self.map.landmarks if record['kind'] == 'bridge')
        point = self.screen_point(self.map.marker_rects[record['id']].center)
        self.event(pygame.MOUSEMOTION, pos=point)
        self.assertEqual(self.map.landmarks[self.map.hovered]['id'], record['id'])
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=point)
        self.event(pygame.MOUSEBUTTONUP, button=1, pos=point)
        self.assertEqual(self.map.selected_landmark['id'], record['id'])
        selected = self.map.selected
        self.event(pygame.KEYDOWN, key=pygame.K_RIGHT, repeat=True)
        self.assertEqual(self.map.selected, selected)
        self.event(pygame.KEYDOWN, key=pygame.K_RIGHT, repeat=False)
        self.assertEqual(self.map.selected, (selected+1) % len(self.map.landmarks))
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0))
        self.assertTrue(self.game.map_open)
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=self.screen_point(self.map.close_rect.center))
        self.assertFalse(self.game.map_open)
        self.assertFalse(self.event(pygame.KEYDOWN, key=pygame.K_RIGHT, repeat=False))

    def test_discovery_and_progress_markers_reflect_controller_without_mutating_manifest(self):
        self.game.overworld_travel = SimpleNamespace(discovered={'eldenmere'})
        self.map.reset()
        self.assertEqual({record['kind'] for record in self.map.landmarks}, {'town', 'bridge', 'checkpoint'})
        identifier = self.data['landmarks'][0]['id']
        self.game.overworld_travel.discovered.add(identifier)
        self.map.reset()
        self.assertIn(identifier, {record['id'] for record in self.map.landmarks})
        bridge = next(record for record in self.map.landmarks if record['kind'] == 'bridge')
        self.assertIn('broken', self.map._description(bridge))
        self.game.social.flags.add(bridge['repair_flag'])
        self.assertIn('passable', self.map._description(bridge))
        self.assertNotIn('kind', self.data['bridge'])
        checkpoint = next(record for record in self.map.landmarks if record['kind'] == 'checkpoint')
        canvas = pygame.Surface((480, 320))
        painter = self.game.ui.painter(canvas)
        center = painter.point(self.map.tile_to_map(checkpoint['tile_position']))
        for clearance, destination_ready in ((False, False), (False, True), (True, False), (True, True)):
            with self.subTest(clearance=clearance, destination_ready=destination_ready):
                if clearance:self.game.social.flags.add(checkpoint['clearance_flag'])
                else:self.game.social.flags.discard(checkpoint['clearance_flag'])
                checkpoint['destination_ready'] = destination_ready
                canvas.fill('#e8d8ad')
                self.map._draw_marker(painter, checkpoint)
                closed = not (clearance and destination_ready)
                self.assertEqual(canvas.get_at(center)[:3] == (139, 79, 62), closed)
                self.assertEqual('closed' in self.map._description(checkpoint), closed)

    def test_display_resize_large_text_and_long_description_remain_bounded_and_scrollable(self):
        before = json.dumps(self.data, sort_keys=True)
        self.game.audio.text_scale = 1.5
        self.map.selected = next(i for i, record in enumerate(self.map.landmarks)
                                 if record['id'] == self.data['landmarks'][0]['id'])
        self.map.selected_landmark['description'] = 'A long woodland description with a clear view. '*25
        for size in ((480, 320), (960, 640), (1280, 720)):
            with self.subTest(size=size):
                self.game.window = pygame.display.set_mode(size)
                canvas = pygame.Surface(size)
                clip = canvas.get_rect().inflate(-2, -2)
                canvas.set_clip(clip)
                self.map_ui.draw(canvas)
                self.assertEqual(canvas.get_clip(), clip)
                self.assertGreater(self.map.detail_max_scroll, 0)
                self.event(pygame.KEYDOWN, key=pygame.K_END, repeat=False)
                self.assertEqual(self.map.detail_scroll, self.map.detail_max_scroll)
                self.map_ui.draw(canvas)
        self.assertEqual(json.dumps(self.data, sort_keys=True), before)
        self.game.quest_ui.draw_map_markers.assert_not_called()

    def test_map_allocations_depend_on_display_instead_of_region_extent(self):
        self.data['bounds_tiles'] = [-1000000, -750000, 2000000, 1500000]
        self.map.reset()
        canvas = pygame.Surface((640, 480))
        constructor = pygame.Surface
        sizes = []
        def bounded_surface(size, *args, **kwargs):
            sizes.append(size)
            self.assertLessEqual(size[0], 640)
            self.assertLessEqual(size[1], 480)
            return constructor(size, *args, **kwargs)
        with patch('pygame.Surface', side_effect=bounded_surface):self.map_ui.draw(canvas)
        self.assertTrue(sizes)

    def test_town_and_indoor_modes_keep_existing_map_and_exterior_position(self):
        region = self.game.world
        self.game.world = self.game.town
        self.map_ui.reset()
        with patch.object(self.map, 'draw') as regional_draw:
            self.map_ui.draw(pygame.Surface((480, 320)))
        regional_draw.assert_not_called()
        self.game.world = SimpleNamespace(data={'kind': 'interior'})
        self.assertEqual(self.map_ui.player_position(), tuple(self.game.exterior_position))
        self.game.world = region
        self.map_ui.reset()
        self.assertIs(self.map_ui._regional_map, self.map)

    def test_real_game_update_freezes_regional_world_until_map_closes(self):
        from main import Game
        game = Game.__new__(Game)
        game.__dict__.update(self.game.__dict__)
        game.opening_cinematic = SimpleNamespace(active=False)
        game.mill_quest = SimpleNamespace(sync_encounter_music=Mock())
        game.music = Mock()
        game._music_focused = True
        game.combat = SimpleNamespace(active=False, post_phase=False, tutorial_active=False,
            tick_world=Mock(side_effect=RuntimeError('world resumed')))
        game.social.active = False
        game.on_title = False
        game.pause = game.inventory_ui = game.world_map_viewer = SimpleNamespace(is_open=False)
        game.overworld_travel = SimpleNamespace(active=True)
        game.quest_ui.journal_open = False
        game.opening_audio = Mock()
        game.elapsed_ms = 1234
        game.opening_fade = 0
        game.update(.5, (1, 0), True)
        self.assertEqual(game.elapsed_ms, 1234)
        game.combat.tick_world.assert_not_called()
        self.assertEqual(game.player.position, pygame.Vector2(288, -480))
        regional_map = RegionalMapUI(game)
        regional_map.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, repeat=False))
        self.assertFalse(game.map_open)
        with self.assertRaisesRegex(RuntimeError, 'world resumed'):game.update(.5, (1, 0), True)
        game.combat.tick_world.assert_called_once_with(.5)


if __name__ == '__main__':unittest.main()
