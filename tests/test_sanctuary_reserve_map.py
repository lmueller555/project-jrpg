"""Local navigation shows the reserve outdoors and at its hall entrance."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from map_ui import MapUI
from ui_style import UIStyle

ROOT = Path(__file__).resolve().parents[1]


class SanctuaryReserveMapTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init()
        window = pygame.display.set_mode((960, 640))
        data = json.loads((ROOT/'assets/maps/elden_vale_sanctuary/map.json').read_text())
        def image(path, alpha=True):
            result = pygame.image.load(ROOT/path)
            return result.convert_alpha() if alpha else result.convert()
        town = SimpleNamespace(data={'landmarks': [], 'size_pixels': [960, 1440]},
                               size=(960, 1440), image=image)
        self.game = SimpleNamespace(town=town, world=SimpleNamespace(data=data),
            player=SimpleNamespace(position=pygame.Vector2(data['spawn'])),
            exterior_position=pygame.Vector2(516, 1284), window=window, map_open=True,
            audio=SimpleNamespace(text_scale=1., effects_volume=0),
            _scene_by_id=Mock(side_effect=AssertionError('A map cannot instantiate rooms')))
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = lambda point: (point[0]/2, point[1]/2)
        self.map = MapUI(self.game)
        self.canvas = pygame.Surface((960, 640))

    def tearDown(self):pygame.quit()

    def test_reserve_routes_map_selection_without_using_town_coordinates_or_travel(self):
        before = self.game.player.position.copy()
        self.map.draw(self.canvas)
        local = self.map._reserve()
        self.assertEqual(local.player_position(), tuple(before))
        self.assertNotEqual(local.player_position(), tuple(self.game.exterior_position))
        self.assertGreaterEqual(len(local.landmarks), 5)
        for landmark in local.landmarks:
            self.assertTrue(landmark.get('description'))
            rect = local.marker_rects[landmark['id']]
            self.assertTrue(local.map_rect.contains(rect))
            point = (rect.centerx*2, rect.centery*2)
            self.map.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
            self.map.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point))
            self.assertEqual(local.selected_landmark['id'], landmark['id'])
        self.assertEqual(self.game.player.position, before)
        self.game._scene_by_id.assert_not_called()

    def test_hall_marker_stays_at_its_reserve_door_without_loading_the_exterior(self):
        data = json.loads((ROOT/'assets/maps/elden_vale_sanctuary_hall/map.json').read_text())
        self.game.world = SimpleNamespace(data=data)
        self.game.player.position.update(data['spawn'])
        self.map.reset();self.map.draw(self.canvas)
        local = self.map._reserve()
        expected = tuple(data['exterior_map_position'])
        self.assertEqual(local.player_position(), expected)
        self.assertNotEqual(expected, tuple(self.game.player.position))
        self.game._scene_by_id.assert_not_called()

    def test_large_text_keeps_detail_scroll_and_close_usable(self):
        local = self.map._reserve()
        original = local.landmarks[0].get('description', '')
        try:
            local.landmarks[0]['description'] = 'Remembering and tending the living grove. '*50
            local.selected = 0
            for size in ((480, 320), (960, 640), (1280, 720)):
                self.game.window = pygame.display.set_mode(size)
                self.game.audio.text_scale = 1.5
                self.map.draw(pygame.Surface(size))
                self.assertGreater(local.detail_max_scroll, 0)
                local.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END, repeat=False))
                self.assertEqual(local.detail_scroll, local.detail_max_scroll)
                local.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_HOME, repeat=False))
                self.assertEqual(local.detail_scroll, 0)
            self.assertTrue(self.game.map_open)
            self.map.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
            self.assertFalse(self.game.map_open)
        finally:local.landmarks[0]['description'] = original


if __name__ == '__main__':unittest.main()
