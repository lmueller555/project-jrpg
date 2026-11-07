"""Impact-owned recoil and anchored, deterministic combat effects."""
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from battle_action_fx import BattleActionEffects, target_reaction
from gearblade_fx import GearbladeEffects


ROOT = Path(__file__).resolve().parents[1]


def pixels(surface):return pygame.image.tobytes(surface, 'RGBA')


class BattleActionEffectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((480, 320))

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def setUp(self):
        self.fx = BattleActionEffects()
        self.dart = SimpleNamespace(action='aether_dart', kind='magical', duration=1.6,
                                    impact_at=1.1, elapsed=0., resolved=False)
        self.anchors = {'cast_origin': (314, 138), 'release_origin': (310, 135),
                        'target_hit': (126, 133)}

    def sample(self, age, **kwargs):
        return self.fx.sample((354, 184), (126, 170), self.dart, age,
                              kwargs.pop('anchors', self.anchors), **kwargs)

    def render(self, age, **kwargs):
        canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
        self.fx.draw(canvas, (354, 184), (126, 170), self.dart, age,
                     kwargs.pop('anchors', self.anchors), **kwargs)
        return canvas

    def test_dart_charges_at_pose_anchor_then_releases_and_arrives_at_contact(self):
        preparation = self.sample(.6)
        self.assertGreater(preparation['charge'], .5)
        self.assertEqual(preparation['origin'], self.anchors['cast_origin'])
        self.assertIsNone(preparation['projectile'])
        self.assertIsNone(self.sample(.749)['projectile'])
        release = self.sample(.75)
        self.assertEqual(release['charge'], 0.)
        self.assertEqual(release['projectile']['point'], self.anchors['release_origin'])
        middle = self.sample(.925)['projectile']
        self.assertAlmostEqual(middle['fraction'], .5)
        self.assertAlmostEqual(middle['point'][0], 218.)
        arrival = self.sample(1.1-1e-9)['projectile']
        self.assertAlmostEqual(arrival['point'][0], 126., places=5)
        self.assertAlmostEqual(arrival['point'][1], 133., places=5)
        self.assertIsNone(self.sample(1.1)['projectile'])
        self.assertIsNone(self.sample(1.59)['projectile'])

    def test_impact_flash_requires_resolved_action_or_event_clock_and_expires_at_80_ms(self):
        self.assertEqual(self.sample(1.1)['impact_strength'], 0.)
        self.dart.resolved = True
        self.assertEqual(self.sample(1.1)['impact_strength'], 1.)
        self.assertGreater(self.sample(1.179)['impact_strength'], 0.)
        self.assertEqual(self.sample(1.18)['impact_strength'], 0.)
        self.assertEqual(self.sample(1.09)['impact_strength'], 0.)
        # An event survives an action finishing or a large update crossing it.
        record = dict(self.anchors, impact_age=.025)
        self.assertGreater(self.sample(1.6, anchors=record)['impact_strength'], 0.)
        record['show_impact'] = False
        self.assertEqual(self.sample(1.6, anchors=record)['impact_strength'], 0.)
        flash = pygame.Surface((480, 320), pygame.SRCALPHA)
        self.fx.draw_impact(flash, (126, 133), .025, 'aether_dart')
        self.assertTrue(flash.get_bounding_rect())
        expired = pygame.Surface((480, 320), pygame.SRCALPHA)
        self.fx.draw_impact(expired, (126, 133), .08, 'aether_dart')
        self.assertFalse(expired.get_bounding_rect())

    def test_charge_and_projectile_translate_with_world_pose_anchors(self):
        offset = pygame.Vector2(30, 17)
        moved = {key: tuple(pygame.Vector2(point)+offset) for key, point in self.anchors.items()}
        for age in (.6, .925):
            first, second = self.render(age), self.render(age, anchors=moved)
            self.assertEqual(first.get_bounding_rect().move(30, 17), second.get_bounding_rect())
            self.assertEqual(pixels(first.subsurface(first.get_bounding_rect())),
                             pixels(second.subsurface(second.get_bounding_rect())))

    def test_non_damage_actions_do_not_create_contact_flashes(self):
        for kind in ('guard', 'haste', 'failed_edge', 'enchant', 'flee', 'prepare'):
            action = dict(action=kind, kind=kind, duration=.9, impact_at=.5,
                          elapsed=.5, resolved=True)
            sample = self.fx.sample((354, 184), (126, 170), action)
            self.assertEqual(sample['impact_strength'], 0.)
            self.assertIsNone(sample['projectile'])

    def test_dust_only_appears_at_explicit_departure_and_landing_boundaries(self):
        edge = dict(action='aether_edge', kind='spellblade', elapsed=0., duration=2., impact_at=1.)
        anchors = {'dash_origin': (354, 184), 'dash_at': .46,
                   'landing': (354, 184), 'landing_at': 1.8}
        sample = lambda age, reduced=False: self.fx.sample((354, 184), (126, 170), edge,
                                                          age, anchors, reduced)
        self.assertEqual(sample(.45)['dust'], [])
        self.assertEqual(len(sample(.5)['dust']), 1)
        self.assertFalse(sample(.5)['dust'][0]['landing'])
        self.assertEqual(sample(.7)['dust'], [])
        self.assertTrue(sample(1.85)['dust'][0]['landing'])
        self.assertEqual(sample(1.85, True)['dust'], [])
        for kind in ('magical', 'guard'):
            edge['kind'] = kind
            self.assertEqual(sample(.5)['dust'], [])

    def test_reduced_motion_keeps_anchors_and_core_projectile_with_quiet_accents(self):
        sample = self.sample(.925, reduced_motion=True)
        self.assertEqual(sample['projectile']['point'], (218., 134.))
        self.assertLess(self.render(.925, reduced_motion=True).get_bounding_rect().width,
                        self.render(.925).get_bounding_rect().width)
        self.assertEqual(self.sample(.6, reduced_motion=True)['origin'], self.anchors['cast_origin'])

    def test_seek_and_repeat_do_not_read_assets_or_accumulate_particles(self):
        expected = pixels(self.render(.925))
        layer = self.fx._layer
        with patch('pygame.image.load', side_effect=AssertionError('Render-time asset read')):
            for age in (10., .2, 1.1, .6, 3.):self.render(age)
            self.assertEqual(pixels(self.render(.925)), expected)
        self.assertIs(layer, self.fx._layer)
        self.assertEqual(layer.get_size(), (480, 320))

    def test_existing_two_recoil_drawings_are_distinct_and_keep_the_ground_height(self):
        for actor, first, duration in (('bat', .15, .37), ('ridgeback_tusker', .18, .42)):
            with self.subTest(actor=actor):
                start = target_reaction(actor, .03)
                settle = target_reaction(actor, first+.01)
                self.assertEqual((start['state'], settle['state']), ('hurt', 'hurt'))
                self.assertEqual((start['frame_index'], settle['frame_index']), (0, 1))
                self.assertEqual(start['offset'][1], 0.)
                self.assertEqual(settle['offset'][1], 0.)
                self.assertEqual(target_reaction(actor, .03, direction=-1)['offset'][0],
                                 -start['offset'][0])
                self.assertEqual(target_reaction(actor, .03, reduced_motion=True)['offset'], (0., 0.))
                self.assertFalse(target_reaction(actor, duration)['active'])
                self.assertEqual(target_reaction(actor, duration)['offset'], (0., 0.))
                a = pygame.image.load(str(ROOT/'assets/combat'/actor/'hurt_01.png'))
                b = pygame.image.load(str(ROOT/'assets/combat'/actor/'hurt_02.png'))
                self.assertNotEqual(pixels(a), pixels(b))

    def test_gearblade_contact_follows_actual_long_edge_impact(self):
        fx = GearbladeEffects()
        edge = dict(action='aether_edge', kind='spellblade', duration=2., impact_at=1., elapsed=.5)
        self.assertEqual(fx.sample((354, 184), 'aether_edge', 500, 'water', .5, action=edge)['contact'], 0.)
        edge['elapsed'] = 1.
        contact = fx.sample((354, 184), 'aether_edge', 500, 'water', 1., action=edge)
        self.assertEqual(contact['contact'], 1.)
        self.assertEqual(contact['impact_at'], 1.)
        edge['elapsed'] = 1.08
        self.assertEqual(fx.sample((354, 184), 'aether_edge', 600, 'water', 1.08, action=edge)['contact'], 0.)

    def test_caelan_guard_and_hurt_recovery_have_the_authored_lengths(self):
        self.assertEqual(target_reaction('caelan', .1)['state'], 'hurt_recover')
        self.assertEqual(target_reaction('caelan', .1, guarded=True)['state'], 'guard_impact')
        self.assertTrue(target_reaction('caelan', .35)['active'])
        self.assertFalse(target_reaction('caelan', .36)['active'])
        self.assertTrue(target_reaction('caelan', .23, guarded=True)['active'])
        self.assertFalse(target_reaction('caelan', .24, guarded=True)['active'])

    def test_gearblade_accepts_the_same_authored_motion_anchors_as_the_actor(self):
        fx = GearbladeEffects()
        pose = dict(floor=(20, 40), guard=(16, 29), active_gem=(19, 29),
                    blade_base=(14, 27), blade_tip=(3, 18))
        sample = fx.sample((354, 184), 'run_approach', 200, 'water', .2, pose_anchors=pose)
        self.assertEqual(sample['anchors']['blade_tip'], (320., 140.))
        self.assertEqual(sample['anchors']['guard'], (346., 162.))
        self.assertEqual(sample['anchors']['gems']['water'], (352., 162.))

    def test_invalid_clocks_are_rejected(self):
        for age in (float('inf'), float('nan')):
            with self.assertRaises(ValueError):self.sample(age)
            with self.assertRaises(ValueError):target_reaction('bat', age)
        with self.assertRaises(TypeError):self.sample(True)


if __name__ == '__main__':unittest.main()
