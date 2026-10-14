"""Fullscreen scale and legacy collision continuity regression tests."""
import unittest
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from main import ART_SCALE, LOGICAL_W, LOGICAL_H, TILE, VIEW_W, VIEW_H, Game


class PresentationTests(unittest.TestCase):
    def test_new_presentation_scale_preserves_map_units(self):
        self.assertEqual(TILE, 16)  # Collision/grid JSON remains compatible.
        self.assertEqual(ART_SCALE, 2)
        self.assertEqual((LOGICAL_W, LOGICAL_H), (640, 448))
        self.assertEqual((VIEW_W, VIEW_H), (320, 224))

    def test_fullscreen_default_and_window_toggle(self):
        import pygame
        game = Game()
        try:
            self.assertTrue(game.fullscreen)
            self.assertEqual(game.world_canvas.get_size(), (640, 448))
            game.toggle_fullscreen()
            self.assertFalse(game.fullscreen)
            game.render()
        finally:
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
