"""Charging warnings remain readable, local and deterministic on the scene clock."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import unittest

import pygame

from enemy_charge_aura import EnemyChargeAura


class EnemyChargeAuraTests(unittest.TestCase):
    def render(self, age=.4, *, body=(55, 60, 60, 70), reduced=False,
               bounds=(10, 25, 160, 135), actor='enemy', front=True):
        image = pygame.Surface((180, 180), pygame.SRCALPHA)
        effect = EnemyChargeAura()
        region = effect.draw(image, body, age, actor_key=actor,
                             reduced_motion=reduced, bounds=bounds)
        if front:
            effect.draw(image, body, age, actor_key=actor,
                        reduced_motion=reduced, bounds=bounds, foreground=True)
        return image, effect, region

    def test_scene_clock_is_seekable_and_does_not_use_global_randomness(self):
        first, _, _ = self.render(.42)
        later, _, _ = self.render(.67)
        scrubbed, _, _ = self.render(.42)
        self.assertEqual(pygame.image.tobytes(first, 'RGBA'),
                         pygame.image.tobytes(scrubbed, 'RGBA'))
        self.assertNotEqual(pygame.image.tobytes(first, 'RGBA'),
                            pygame.image.tobytes(later, 'RGBA'))

    def test_reduced_motion_uses_one_static_readable_frame(self):
        first, _, _ = self.render(0, reduced=True)
        later, _, _ = self.render(120, reduced=True)
        self.assertEqual(pygame.image.tobytes(first, 'RGBA'),
                         pygame.image.tobytes(later, 'RGBA'))
        self.assertGreater(first.get_bounding_rect().width, 60)
        self.assertGreater(first.get_bounding_rect().height, 70)

    def test_bounds_clip_every_effect_pixel_away_from_cards_and_hud(self):
        bounds = pygame.Rect(49, 57, 75, 58)
        image, _, region = self.render(body=(48, 54, 80, 70), bounds=bounds)
        self.assertTrue(bounds.contains(region))
        self.assertTrue(bounds.contains(image.get_bounding_rect()))
        self.assertEqual(image.get_at((48, 80)).a, 0)
        self.assertEqual(image.get_at((70, bounds.bottom)).a, 0)

    def test_aura_emits_above_and_beside_small_and_large_enemies(self):
        for body in ((70, 80, 13, 15), (23, 44, 125, 110)):
            with self.subTest(body=body):
                image, _, _ = self.render(body=body, bounds=(0, 0, 180, 180))
                occupied = image.get_bounding_rect()
                enemy = pygame.Rect(body)
                self.assertLess(occupied.top, enemy.top)
                self.assertLess(occupied.left, enemy.left)
                self.assertGreater(occupied.right, enemy.right)

    def test_colors_form_a_red_warning_with_hot_lightning_tips(self):
        image, _, _ = self.render()
        visible = [image.get_at((x, y)) for x in range(180) for y in range(180)
                   if image.get_at((x, y)).a]
        red = sum(color.r > color.g * 1.5 and color.r > color.b * 1.5
                  for color in visible)
        hot = sum(color.r > 240 and color.g > 180 for color in visible)
        self.assertGreater(red, 250)
        self.assertGreater(hot, 4)

    def test_foreground_has_sparks_at_edges_but_does_not_cover_sprite_center(self):
        effect = EnemyChargeAura()
        body = pygame.Rect(50, 50, 60, 80)
        image = pygame.Surface((180, 180), pygame.SRCALPHA)
        effect.draw(image, body, .4, foreground=True)
        self.assertGreater(image.get_bounding_rect().width, 60)
        center = body.inflate(-body.width // 2, -body.height // 3)
        self.assertTrue(all(image.get_at((x, y)).a == 0
                            for x in range(center.left, center.right)
                            for y in range(center.top, center.bottom)))

    def test_different_enemy_identities_use_distinct_but_repeatable_flames(self):
        first = EnemyChargeAura.sample((30, 30, 50, 60), .5, actor_key='enemy')
        other = EnemyChargeAura.sample((30, 30, 50, 60), .5, actor_key='enemy_2')
        self.assertNotEqual(first['flames'], other['flames'])
        self.assertEqual(first, EnemyChargeAura.sample((30, 30, 50, 60), .5,
                                                      actor_key='enemy'))

    def test_surface_is_reused_and_cache_does_not_grow_with_clock_or_enemy_ids(self):
        image = pygame.Surface((180, 180), pygame.SRCALPHA)
        effect = EnemyChargeAura()
        effect.draw(image, (40, 40, 70, 90), .2)
        layer = effect._layer
        for index in range(30):
            effect.draw(image, (45, 50, 60, 70), index / 10,
                        actor_key='enemy_' + str(index), foreground=bool(index % 2))
            self.assertIs(effect._layer, layer)
        self.assertLessEqual(layer.get_width(), image.get_width())
        self.assertLessEqual(layer.get_height(), image.get_height())
        smaller = pygame.Surface((80, 70), pygame.SRCALPHA)
        effect.draw(smaller, (15, 15, 40, 45), .2)
        self.assertLessEqual(effect._layer.get_width(), smaller.get_width())
        self.assertLessEqual(effect._layer.get_height(), smaller.get_height())

    def test_outside_bounds_do_not_allocate_or_modify_canvas(self):
        image = pygame.Surface((180, 180), pygame.SRCALPHA)
        effect = EnemyChargeAura()
        region = effect.draw(image, (400, 400, 20, 25), .2, bounds=(0, 0, 100, 100))
        self.assertEqual(region.size, (0, 0))
        self.assertIsNone(effect._layer)
        self.assertEqual(image.get_bounding_rect().size, (0, 0))

    def test_invalid_time_and_geometry_are_rejected(self):
        for age in (True, -1, float('nan'), float('inf'), '1'):
            with self.subTest(age=age):
                with self.assertRaises(ValueError):
                    EnemyChargeAura.sample((10, 10, 20, 30), age)
        with self.assertRaises(ValueError):
            EnemyChargeAura.sample((10, 10, 0, 30), .2)
        with self.assertRaises(ValueError):
            EnemyChargeAura.sample((10, 10, 20, 30), .2, bounds=(0, 0, 0, 10))


if __name__ == '__main__':
    unittest.main()
