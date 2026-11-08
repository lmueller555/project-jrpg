"""Whole-cavern routing, room labels and accessible navigation."""
import os
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from map_ui import MapUI
from ui_style import UIStyle

ROOT = Path(__file__).resolve().parents[1]


class SanctuaryCaveMapTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init()
        window = pygame.display.set_mode((960, 640))
        def image(path, alpha=True):
            surface = pygame.image.load(ROOT/path)
            return surface.convert_alpha() if alpha else surface.convert()
        town = NS(data={'landmarks': [], 'size_pixels': [960, 1440]},
                  size=(960, 1440), image=image)
        data = self.scene()
        self.game = NS(town=town, world=NS(data=data),
            player=NS(position=pygame.Vector2(360, 240)),
            exterior_position=pygame.Vector2(516, 1284), window=window, map_open=True,
            audio=NS(text_scale=1., effects_volume=0),
            _scene_by_id=Mock(side_effect=AssertionError('Maps do not load rooms')))
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = lambda point: (point[0]/2, point[1]/2)
        self.map = MapUI(self.game)
        self.canvas = pygame.Surface((960, 640))

    @staticmethod
    def scene():
        rooms = [('entrance', 'Cave Entrance', [360, 240]),
                 ('vein', 'Vein Gallery', [800, 300]),
                 ('hollow', 'Splitstone Hollow', [1200, 600]),
                 ('deep', 'Deep Gallery', [1600, 850]),
                 ('quiet', 'Quiet Shelf', [1750, 1100]),
                 ('echo', 'Echo Chamber', [2100, 1300])]
        return {'id': 'sanctuary_cave', 'name': 'Sanctuary Cave',
                'size_pixels': [2304, 1536],
                'overview': 'assets/terrain/elden_vale_sanctuary/overview.png',
                'landmarks': [{'id': identifier, 'name': name,
                    'position': point, 'description': 'A crystal-lined cavern.'}
                    for identifier, name, point in rooms],
                'cave': {'links': [{'id': 'entrance_exit', 'position': [120, 120],
                    'destination': 'elden_vale_sanctuary'}],
                    'treasures': [{'id': 'secret-cache', 'position': [220, 160]}]}}

    def tearDown(self):pygame.quit()

    def test_routes_actual_scene_coordinates_without_revealing_treasure(self):
        self.map.draw(self.canvas)
        local = self.map._cave()
        self.assertEqual(local.player_position(), (360, 240))
        self.assertEqual(set(local.marker_rects),
                         {'entrance', 'vein', 'hollow', 'deep', 'quiet', 'echo',
                          'passage:entrance_exit'})
        self.assertEqual(local.selected_landmark['id'], 'entrance')
        self.assertIn('entrance', local.label_rects)
        self.assertTrue(local.overview.get_width())
        self.game._scene_by_id.assert_not_called()
        rect = local.marker_rects['passage:entrance_exit']
        self.map.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                              button=1, pos=(rect.centerx*2, rect.centery*2)))
        self.assertEqual(local.selected_landmark['id'], 'passage:entrance_exit')
        self.assertEqual(local.selected_landmark['name'], 'To Sanctuary grounds')

    def test_walking_to_another_room_keeps_the_complete_map(self):
        self.map.draw(self.canvas)
        local = self.map._cave()
        data = local.data
        overview = local.overview
        local.selected = 1;local.detail_scroll = 70;local.hovered = 1
        self.game.player.position.update(2100, 1300)
        self.map.reset();self.map.draw(self.canvas)
        self.assertIs(local.data, data)
        self.assertIs(local.overview, overview)
        self.assertEqual(local.selected_landmark['id'], 'echo')
        self.assertIn('entrance', local.marker_rects)
        self.assertIn('echo', local.label_rects)
        self.assertTrue(local.map_rect.contains(local.label_rects['echo']))
        self.assertEqual(local.detail_scroll, 0)
        self.assertIsNone(local.hovered)
        self.game._scene_by_id.assert_not_called()

    def test_large_text_details_scroll_and_map_close(self):
        self.game.audio.text_scale = 1.5
        self.map._cave().landmarks[0]['description'] = 'A crystal-lined cavern. '*80
        self.map.draw(self.canvas)
        local = self.map._cave()
        self.assertGreater(local.detail_max_scroll, 0)
        self.map.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END))
        self.assertEqual(local.detail_scroll, local.detail_max_scroll)
        self.map.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
        self.assertFalse(self.game.map_open)


if __name__ == '__main__':unittest.main()
