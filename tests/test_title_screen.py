"""Title screen navigation and drawing smoke tests."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame
from engine.title_screen import TitleScreen


class TitleScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_initial_selection_starts_game(self):
        screen = TitleScreen()
        self.assertEqual(screen.selected, 0)
        self.assertEqual(screen.handle_key(pygame.K_RETURN), "start")

    def test_navigation_wraps_and_quit(self):
        screen = TitleScreen()
        screen.handle_key(pygame.K_UP)
        self.assertEqual(screen.selected, 2)
        self.assertEqual(screen.handle_key(pygame.K_SPACE), "quit")
        screen.handle_key(pygame.K_DOWN)
        self.assertEqual(screen.selected, 0)
        screen.handle_key(pygame.K_DOWN)
        self.assertEqual(screen.handle_key(pygame.K_RETURN), "library")
        self.assertEqual(screen.handle_key(pygame.K_ESCAPE), "quit")

    def test_draws_at_game_and_window_resolution(self):
        screen = TitleScreen()
        screen.update(0.016)
        screen.draw_canvas(pygame.Surface((640, 448)))
        screen.draw(pygame.Surface((960, 672)))
        screen.draw(pygame.Surface((320, 224)))


if __name__ == "__main__":
    unittest.main()
