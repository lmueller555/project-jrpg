"""Billowing follows scene time, remains bounded and registers to terrain."""
from copy import deepcopy
import json
import os
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from cinematic_smoke import CinematicSmoke
from fire_veinhold_opening import SCENE


class CinematicSmokeTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode((960, 640))
        folder = SCENE.parent/'shot01/environment'
        self.records = json.loads((folder/'art.json').read_text())['smoke']['emitters']
        self.texture = pygame.image.load(str(folder/'smoke_puff.png')).convert_alpha()
        self.smoke = CinematicSmoke(self.texture, self.records, (1024, 1536))

    def tearDown(self):
        pygame.quit()

    def test_both_plumes_are_prewarmed_and_animate_without_history_or_global_random(self):
        initial = self.smoke.samples(0)
        self.assertEqual({p['id'] for p in initial}, {'main_steam', 'distant_ash'})
        later = self.smoke.samples(20)
        self.smoke.samples(1)
        self.assertEqual(self.smoke.samples(20), later)
        self.assertEqual(CinematicSmoke(self.texture, self.records, (1024, 1536)).samples(20), later)
        for identifier in ('main_steam', 'distant_ash'):
            self.assertNotEqual([p for p in later if p['id'] == identifier],
                                [p for p in self.smoke.samples(20.25) if p['id'] == identifier])
        self.assertLess(len(self.smoke.samples(1000000)), 100)

    def test_one_billow_rises_expands_and_dissipates_without_a_loop_reset(self):
        def particle(time):
            return next(p for p in self.smoke.samples(time)
                        if p['id'] == 'main_steam' and p['serial'] == 0)
        first, later, end = particle(.3), particle(2), particle(7.8)
        self.assertGreater(later['size'], first['size'])
        self.assertLess(later['position'][1], first['position'][1])
        self.assertLessEqual(end['alpha'], first['alpha'])
        self.assertFalse(any(p['id'] == 'main_steam' and p['serial'] == 0
                             for p in self.smoke.samples(9.01)))

    def test_both_billows_draw_at_their_projected_vents_and_change_visibly(self):
        background = pygame.Surface((1024, 650));background.fill('#0c1a36')
        first = background.copy();second = background.copy()
        self.smoke.draw(first, self.smoke.samples(15), 1., (0, -50))
        self.smoke.draw(second, self.smoke.samples(15.5), 1., (0, -50))
        for rect in (pygame.Rect(470, 50, 180, 230), pygame.Rect(735, 35, 230, 240)):
            self.assertNotEqual(pygame.image.tobytes(first.subsurface(rect), 'RGB'),
                                pygame.image.tobytes(background.subsurface(rect), 'RGB'))
            self.assertNotEqual(pygame.image.tobytes(first.subsurface(rect), 'RGB'),
                                pygame.image.tobytes(second.subsurface(rect), 'RGB'))
        hidden = background.copy()
        self.smoke.draw(hidden, self.smoke.samples(0), 1., (0, -650))
        self.assertEqual(pygame.image.tobytes(hidden, 'RGB'), pygame.image.tobytes(background, 'RGB'))

    def test_invalid_or_unbounded_emitters_fail_before_playback(self):
        for key, value in (('interval', 0), ('lifetime', float('inf')),
                           ('opacity', float('nan')), ('origin', [2000, 1]),
                           ('seed', True), ('tint', [1, 2])):
            with self.subTest(key=key):
                records = deepcopy(self.records);records[0][key] = value
                with self.assertRaises(ValueError):
                    CinematicSmoke(self.texture, records, (1024, 1536))
        with self.assertRaises(ValueError):
            CinematicSmoke(self.texture, [self.records[0]]*2, (1024, 1536))
        with self.assertRaises(ValueError):self.smoke.samples(float('nan'))
