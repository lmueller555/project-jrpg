"""Authored battlefield assets and ground projections in the real scene renderer."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from battle_model import BattleModel
from battle_scene import BattleScene
from character_attributes import CharacterAttributes


class EmptySprites:
    def __init__(self):
        self.image = pygame.Surface((48, 48), pygame.SRCALPHA)

    def frame(self, actor, state, elapsed_ms):
        return self.image, (24, 42)


class BattlefieldTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.display.set_mode((480, 320))
        self.game = SimpleNamespace(audio=SimpleNamespace(reduced_motion=False))
        self.model = BattleModel(CharacterAttributes())

    def tearDown(self):
        pygame.quit()

    def scene(self):
        return BattleScene(self.game, self.model, sprites=EmptySprites())

    def test_native_authored_background_is_cached_during_battle_rendering(self):
        with patch.object(pygame.image, 'load', wraps=pygame.image.load) as load:
            scene = self.scene()
            initial_loads = load.call_count
            canvas = pygame.Surface((480, 320))
            for _ in range(5):
                scene.update(1/60)
                scene._draw_field(canvas)
            self.assertEqual(load.call_count, initial_loads)
        self.assertEqual(scene._background.get_size(), (480, 320))
        self.assertIsNone(scene._background.get_alpha())

    def test_wrong_native_asset_dimensions_fail_instead_of_stretching_art(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'wrong-size.png'
            pygame.image.save(pygame.Surface((240, 160)), str(path))
            with self.assertRaisesRegex(ValueError, '480 by 320'):
                BattleScene._make_background(path)

    def test_foreground_breeze_stays_in_corners_and_reduced_motion_is_static(self):
        scene = self.scene()
        canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
        frames = []
        for elapsed in (0.0, 1.0, 3.0):
            canvas.fill((0, 0, 0, 0))
            scene._elapsed = elapsed
            scene._draw_foreground(canvas)
            self.assertEqual(canvas.subsurface((80, 0, 320, 320)).get_bounding_rect().width, 0)
            frames.append(pygame.image.tostring(canvas, 'RGBA'))
        self.assertGreater(len(set(frames)), 1)
        self.game.audio.reduced_motion = True
        frames = []
        for elapsed in (0.0, 1.0, 3.0):
            canvas.fill((0, 0, 0, 0))
            scene._elapsed = elapsed
            scene._draw_foreground(canvas)
            frames.append(pygame.image.tostring(canvas, 'RGBA'))
        self.assertEqual(len(set(frames)), 1)

    def test_grounded_contact_shadow_tracks_caelans_approach(self):
        scene = self.scene()
        canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
        for point in ((354, 184), (152, 174)):
            canvas.fill((0, 0, 0, 0))
            scene._draw_shadow(canvas, 'player', pygame.Vector2(point))
            bounds = canvas.get_bounding_rect()
            self.assertEqual(bounds.center, point)
            self.assertGreater(canvas.get_at(point).a, 0)
            self.assertLess(canvas.get_at(point).a, 255)

    def test_hover_shadow_stays_on_ground_while_bat_bobs_and_dives(self):
        scene = self.scene()
        canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
        bounds = []
        for point in ((126, 168), (126, 172), (328, 187)):
            canvas.fill((0, 0, 0, 0))
            scene._draw_shadow(canvas, 'enemy', pygame.Vector2(point))
            bounds.append(canvas.get_bounding_rect())
        self.assertEqual(bounds[0], bounds[1])
        self.assertEqual(bounds[2].center, (328, 184))
        self.assertGreater(bounds[2].width, bounds[0].width)


if __name__ == '__main__':
    unittest.main()
