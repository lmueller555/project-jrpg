"""Cartographic map selection, letterboxing, and full-text accessibility."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from map_ui import DESCRIPTIONS, MapUI
from ui_style import UIStyle

ROOT = Path(__file__).resolve().parents[1]


class MapUITests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        window = pygame.display.set_mode((1100, 750))
        data = json.loads((ROOT/'assets/maps/eldenmere/playable/map.json').read_text())
        town = SimpleNamespace(data=data, size=tuple(data['size_pixels']), npcs=[])
        self.game = SimpleNamespace(town=town, world=town, window=window,
            player=SimpleNamespace(position=pygame.Vector2(396, 300)),
            exterior_position=pygame.Vector2(396, 300), map_open=True,
            audio=SimpleNamespace(text_scale=1.0, reduced_motion=False, effects_volume=0),
            quest_ui=SimpleNamespace(draw_map_markers=Mock()),
            _scene_by_id=Mock(side_effect=AssertionError('Map cannot load a room')))
        def to_canvas(point):
            width, height = self.game.window.get_size()
            scale = max(1, min(width//480, height//320))
            x = (point[0]-(width-480*scale)//2)/scale
            y = (point[1]-(height-320*scale)//2)/scale
            return (x, y) if 0 <= x < 480 and 0 <= y < 320 else None
        self.game.to_canvas = to_canvas
        self.game.ui = UIStyle(self.game)
        self.map = MapUI(self.game)
        self.canvas = pygame.Surface((960, 640))

    def tearDown(self):pygame.quit()

    def click(self, logical):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        point = (round((width-480*scale)//2+logical[0]*scale),
                 round((height-320*scale)//2+logical[1]*scale))
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            handled = self.map.handle_event(pygame.event.Event(kind, button=1, pos=point))
            if kind == pygame.MOUSEBUTTONDOWN:self.assertTrue(handled)

    def key(self, value, repeat=False):
        return self.map.handle_event(pygame.event.Event(pygame.KEYDOWN, key=value, repeat=repeat))

    def test_all_nine_landmarks_have_selectable_geographically_correct_footprints(self):
        self.assertEqual(len(self.map.building_rects), 9)
        for record in self.game.town.data['landmarks']:
            with self.subTest(place=record['id']):
                footprint = self.map.building_rects[record['id']]
                self.assertTrue(self.map.map_rect.contains(footprint))
                self.assertTrue(footprint.collidepoint(self.map.world_to_map(record['position'])))
                self.click(footprint.center)
                self.assertEqual(self.map.selected_landmark['id'], record['id'])
        sanctuary = self.map.building_rects['sanctuary'].center
        venn = self.map.building_rects['venn'].center
        self.assertLess(sanctuary[0], venn[0])
        self.assertLess(sanctuary[1], venn[1])

    def test_letterboxed_clicks_and_close_button_do_not_use_window_coordinates(self):
        self.map.selected = 0
        self.map.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)))
        self.map.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(0, 0)))
        self.assertEqual(self.map.selected, 0)
        self.click(self.map.building_rects['school'].center)
        self.assertEqual(self.map.selected_landmark['id'], 'school')
        self.assertTrue(self.game.map_open)
        self.click(self.map.close_rect.center)
        self.assertFalse(self.game.map_open)
        self.assertFalse(self.map.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)))

    def test_keyboard_selection_wraps_ignores_repeat_and_closes(self):
        self.map.selected = 0
        self.key(pygame.K_LEFT)
        self.assertEqual(self.map.selected, 8)
        self.assertTrue(self.key(pygame.K_RIGHT, repeat=True))
        self.assertEqual(self.map.selected, 8)
        self.key(pygame.K_RIGHT)
        self.assertEqual(self.map.selected, 0)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.game.map_open)

    def test_indoor_player_marker_uses_town_entrance_without_loading_rooms(self):
        self.game.world = SimpleNamespace(data={'name': 'Sanctuary dining room'})
        self.game.player.position.update(120, 180)
        self.game.exterior_position.update(396, 300)
        self.assertEqual(self.map.player_position(), (396, 300))
        self.map.draw(self.canvas)
        self.game._scene_by_id.assert_not_called()
        draw = self.game.quest_ui.draw_map_markers
        draw.assert_called_once_with(self.canvas, self.map.map_rect.topleft, self.map.map_rect.size,
                                     avoid_point=self.map.world_to_map((396, 300)))
        self.assertFalse(self.map.player_legend_rect.colliderect(self.map.map_rect))
        self.assertFalse(self.map.player_legend_rect.colliderect(self.map.close_rect))

    def test_large_selected_place_text_remains_scrollable_instead_of_being_discarded(self):
        self.game.audio.text_scale = 1.5
        self.map.selected = 8
        full_description = ' '.join(['A quiet place for learning, friends, and stories.']*12)
        with patch.dict(DESCRIPTIONS, {'school': full_description}):
            self.map.draw(pygame.Surface((480, 320)))
            self.assertGreater(self.map.detail_max_scroll, 0)
            self.key(pygame.K_END)
            self.assertEqual(self.map.detail_scroll, self.map.detail_max_scroll)
            self.map.draw(self.canvas)
            self.map.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=1))
            self.assertLess(self.map.detail_scroll, self.map.detail_max_scroll)
            self.key(pygame.K_HOME)
            self.assertEqual(self.map.detail_scroll, 0)
        self.click(self.map.building_rects['sanctuary'].center)
        self.assertEqual(self.map.detail_scroll, 0)

    def test_draw_preserves_town_data_and_layout_when_ui_is_closed(self):
        before = json.dumps(self.game.town.data, sort_keys=True)
        self.map.draw(self.canvas)
        self.assertEqual(json.dumps(self.game.town.data, sort_keys=True), before)
        self.game.map_open = False
        self.canvas.fill('#123456')
        self.map.draw(self.canvas)
        self.assertEqual(self.canvas.get_at((50, 50))[:3], (18, 52, 86))
        self.assertEqual(self.map.world_to_map((0, 0)), self.map.map_rect.topleft)
        self.assertEqual(self.map.world_to_map(self.game.town.size), self.map.map_rect.bottomright)


if __name__ == '__main__':unittest.main()
