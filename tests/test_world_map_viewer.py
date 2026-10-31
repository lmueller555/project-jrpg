"""The classroom atlas remains detailed, bounded and modal at display resolution."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
                  PYGAME_HIDE_SUPPORT_PROMPT='1')

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

import pygame

from ui_style import UIStyle
from world_map_viewer import WorldMapViewer


class WorldMapViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((960, 640))
        cls.temp = TemporaryDirectory()
        cls.image_path = Path(cls.temp.name)/'map.png'
        image = pygame.Surface((1448, 1086))
        for x in range(image.get_width()):
            pygame.draw.line(image, (x % 251, (x*7) % 253, 80), (x, 0), (x, 1085))
        pygame.image.save(image, cls.image_path)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        pygame.quit()

    def setUp(self):
        self.game = SimpleNamespace(ui_surface=pygame.Surface((960, 640)),
                                    audio=SimpleNamespace(effects_volume=0, text_scale=1))
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = lambda point: (point[0]/2, point[1]/2)
        self.viewer = WorldMapViewer(self.game, self.image_path)
        self.viewer.open()

    def event(self, kind, **values):
        return self.viewer.handle_event(pygame.event.Event(kind, **values))

    def test_fit_preserves_aspect_and_open_reuses_source(self):
        viewer = self.viewer
        source = viewer.image
        image_rect = viewer.image_rect
        self.assertTrue(viewer.viewport.contains(image_rect))
        self.assertAlmostEqual(image_rect.width/image_rect.height, 4/3, delta=.005)
        viewer.zoom_at(viewer.viewport.center, 4)
        viewer.close()
        viewer.open()
        self.assertIs(viewer.image, source)
        self.assertEqual(viewer.zoom, 1)
        self.assertEqual(viewer.center, pygame.Vector2(724, 543))

    def test_zoom_is_anchored_under_pointer_and_clamped(self):
        viewer = self.viewer
        viewer.zoom_at(viewer.viewport.center, 3)
        point = pygame.Vector2(viewer.viewport.center)+(24, -16)
        original = viewer.image_point(point)
        viewer.zoom_at(point, 1)
        self.assertLess(viewer.image_point(point).distance_to(original), .001)
        viewer.zoom_at(point, 1000)
        self.assertEqual(viewer.zoom, viewer.MAX_ZOOM)
        viewer.zoom_at(point, -1000)
        self.assertEqual(viewer.zoom, 1)
        self.assertEqual(viewer.center, pygame.Vector2(724, 543))

    def test_drag_clamps_to_art_edges_and_release_stops_pan(self):
        viewer = self.viewer
        viewer.zoom_at(viewer.viewport.center, 5)
        start = viewer.viewport.center
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=(start[0]*2, start[1]*2))
        self.event(pygame.MOUSEMOTION, pos=(9000, 9000))
        self.assertGreaterEqual(viewer.image_rect.right, viewer.viewport.right-1)
        self.assertGreaterEqual(viewer.image_rect.bottom, viewer.viewport.bottom-1)
        self.assertLessEqual(viewer.image_rect.left, viewer.viewport.left+1)
        self.assertLessEqual(viewer.image_rect.top, viewer.viewport.top+1)
        self.event(pygame.MOUSEBUTTONUP, button=1, pos=(9000, 9000))
        center = viewer.center.copy()
        self.event(pygame.MOUSEMOTION, pos=(200, 200))
        self.assertEqual(viewer.center, center)

    def test_keyboard_and_button_close_consume_events(self):
        self.assertTrue(self.event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
        self.assertFalse(self.viewer.is_open)
        self.assertFalse(self.event(pygame.KEYDOWN, key=pygame.K_e, repeat=False))
        self.viewer.open()
        self.event(pygame.KEYDOWN, key=pygame.K_e, repeat=True)
        self.assertTrue(self.viewer.is_open)
        self.event(pygame.KEYDOWN, key=pygame.K_e, repeat=False)
        self.assertFalse(self.viewer.is_open)
        self.viewer.open()
        point = self.viewer.close_rect.center
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=(point[0]*2, point[1]*2))
        self.assertFalse(self.viewer.is_open)

    def test_wheel_outside_map_does_not_zoom_and_fit_resets_camera(self):
        viewer = self.viewer
        self.event(pygame.MOUSEWHEEL, y=1, pos=(20, 20))
        self.assertEqual(viewer.zoom, 1)
        point = viewer.viewport.center
        self.event(pygame.MOUSEWHEEL, y=2, pos=(point[0]*2, point[1]*2))
        self.assertGreater(viewer.zoom, 1)
        fit = viewer.fit_rect.center
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=(fit[0]*2, fit[1]*2))
        self.assertEqual(viewer.zoom, 1)
        self.assertEqual(viewer.center, pygame.Vector2(724, 543))

    def test_render_keeps_sub_world_pixel_detail_and_survives_resize(self):
        viewer = self.viewer
        viewer.zoom_at(viewer.viewport.center, 3)
        target = self.game.ui_surface
        viewer.draw(target)
        rect = self.game.ui.painter(target).area(viewer.viewport)
        row = [target.get_at((x, rect.centery))[:3] for x in range(rect.left, rect.right)]
        # A 480px intermediate enlarged 2x would duplicate every adjacent pair.
        transitions = sum(a != b for a, b in zip(row, row[1:]))
        self.assertGreater(transitions, viewer.viewport.width)
        cached = viewer._cached_crop
        viewer.draw(target)
        self.assertIs(viewer._cached_crop, cached)
        large = pygame.Surface((1920, 1280))
        viewer.draw(large)
        self.assertNotEqual(viewer._cached_crop.get_size(), cached.get_size())
        # Rendering retains only a visible crop, even at maximum zoom.
        viewer.zoom_at(viewer.viewport.center, 1000)
        viewer.draw(large)
        bounds = self.game.ui.painter(large).area(viewer.viewport)
        self.assertLessEqual(viewer._cached_crop.get_width(), bounds.width+30)
        self.assertLessEqual(viewer._cached_crop.get_height(), bounds.height+30)


if __name__ == '__main__':unittest.main()
