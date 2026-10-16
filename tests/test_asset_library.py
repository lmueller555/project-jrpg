"""Keyboard and mouse coverage for manifest-backed asset library."""
import os
import unittest
from pathlib import Path
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame
from engine.assets import AtlasRegistry
from engine.asset_library import AssetLibrary, PAGE_SIZE, window_to_canvas

ROOT = Path(__file__).resolve().parents[1]


class AssetLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        cls.registry = AtlasRegistry(ROOT / "assets")

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.gallery = AssetLibrary(self.registry, ROOT / "assets")

    def test_includes_manifest_and_portraits(self):
        ids = {e[0] for e in self.gallery.entries}
        self.assertTrue(set(self.registry.manifest["assets"]).issubset(ids))
        self.assertIn("portrait.caelen.neutral", ids)

    def test_category_and_selection_bounds(self):
        self.gallery.handle_key(pygame.K_TAB)
        self.assertEqual(self.gallery.selected, 0)
        self.gallery.handle_key(pygame.K_END)
        self.assertEqual(self.gallery.selected, len(self.gallery.filtered) - 1)
        self.gallery.handle_key(pygame.K_DOWN)
        self.assertEqual(self.gallery.selected, len(self.gallery.filtered) - 1)
        self.gallery.handle_key(pygame.K_HOME)
        self.assertEqual(self.gallery.selected, 0)
        self.gallery.handle_key(pygame.K_PAGEDOWN)
        self.assertLessEqual(self.gallery.selected, PAGE_SIZE)
        self.assertEqual(self.gallery.handle_key(pygame.K_ESCAPE), "back")

    def test_mouse_and_resized_window_coordinates(self):
        self.assertEqual(window_to_canvas((480, 336), (960, 672)), (320, 224))
        self.assertEqual(self.gallery.handle_click((40, 29), (640, 448)), "back")
        self.assertIsNone(self.gallery.handle_click((-1, -1), (640, 448)))

    def test_draws_native_and_scaled(self):
        self.gallery.draw_canvas(pygame.Surface((640, 448)))
        self.gallery.draw(pygame.Surface((960, 672)))


if __name__ == "__main__":
    unittest.main()
