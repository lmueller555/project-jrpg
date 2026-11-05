"""Spatial and playback contracts for Rhea's uninterrupted duel continuation."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

import math
from pathlib import Path
import unittest
from unittest.mock import patch

import pygame

from ice_reaper_action import IceReaperActionStage
from ice_reaper_duel import IceReaperDuel

ROOT=Path(__file__).resolve().parents[1]


class IceReaperDuelGeometryTests(unittest.TestCase):
    def test_companions_start_at_the_approved_rescue_positions(self):
        before=IceReaperActionStage.actor_positions(20.)
        for elapsed in (21.,23.,24.):
            actual=IceReaperDuel.actor_positions(elapsed)
            for actor in before:
                self.assertEqual(actual[actor],before[actor],(elapsed,actor))
        for elapsed in (24.5,25.15,27.,31.):
            actual=IceReaperDuel.actor_positions(elapsed)
            self.assertEqual(actual['rhea'],pygame.Vector3(-3,0,0))
            self.assertEqual(actual['mira'],pygame.Vector3(7,0,10))

    def test_gust_carries_both_companions_to_separate_positions_near_mira(self):
        airborne=IceReaperDuel.actor_positions(24.6)
        self.assertGreater(airborne['caelan'].y,.5)
        self.assertGreater(airborne['lucan'].y,.3)
        landed=IceReaperDuel.actor_positions(25.2)
        self.assertEqual(landed['caelan'],pygame.Vector3(4.6,0,10.2))
        self.assertEqual(landed['lucan'],pygame.Vector3(8.8,0,8.5))
        for actor in ('caelan','lucan'):
            self.assertLess(landed[actor].distance_to(landed['mira']),3.)
            self.assertGreater(landed[actor].distance_to(landed['mira']),1.8)
        self.assertGreater(landed['caelan'].distance_to(landed['lucan']),3.5)
        for actor in ('caelan','lucan','mira'):
            self.assertEqual(landed[actor],IceReaperDuel.actor_positions(29.)[actor])

    def test_ninety_degree_move_physically_arrives_behind_mira(self):
        center=pygame.Vector3(IceReaperDuel.RHEA)
        start=pygame.Vector3(IceReaperDuel.camera(24.).position)-center
        end=pygame.Vector3(IceReaperDuel.camera(25.15).position)-center
        start.y=end.y=0
        self.assertAlmostEqual(start.normalize().dot(end.normalize()),0.,places=7)
        self.assertEqual(IceReaperDuel.camera(25.15).position,IceReaperDuel.MIRA_CAMERA)
        self.assertEqual(IceReaperDuel.state(25.15)['pan_degrees'],-90.)

    def test_full_orbit_returns_to_the_rear_rhea_camera_before_pushing_in(self):
        start=IceReaperDuel.camera(26.7)
        end=IceReaperDuel.camera(29.15)
        self.assertLess(pygame.Vector3(start.position).distance_to(end.position),1e-7)
        self.assertEqual(start.target,end.target)
        center=pygame.Vector3(IceReaperDuel.ORBIT_CENTER)
        a=pygame.Vector3(start.position)-center
        b=pygame.Vector3(IceReaperDuel.camera((26.7+29.15)/2).position)-center
        self.assertAlmostEqual(a.x,-b.x,places=6)
        self.assertAlmostEqual(a.z,-b.z,places=6)
        self.assertEqual(IceReaperDuel.state(29.15)['orbit_degrees'],360.)
        self.assertEqual(IceReaperDuel.camera(29.55).position,IceReaperDuel.CHARGE_CAMERA)

    def test_charge_approaches_the_lens_and_fade_finishes_at_authored_end(self):
        camera=IceReaperDuel.camera(29.55)
        lens=pygame.Vector3(camera.position)
        distances=[]
        for elapsed in (30.3,30.7,31.1,31.65):
            chest=IceReaperDuel.actor_positions(elapsed)['ice_reaper']+pygame.Vector3(0,2.3,0)
            distances.append(chest.distance_to(lens))
            self.assertIsNotNone(camera.project(chest))
        self.assertTrue(all(a>b for a,b in zip(distances,distances[1:])))
        self.assertLess(distances[-1],.3)
        self.assertEqual(IceReaperDuel.state(31.1)['fade_progress'],0.)
        self.assertEqual(IceReaperDuel.state(32.)['fade_progress'],1.)

    def test_continuous_camera_boundaries_keep_lens_and_position(self):
        for elapsed in (24.,25.15,26.7,29.15,29.55,30.3):
            before=IceReaperDuel.camera(elapsed-1e-6)
            after=IceReaperDuel.camera(elapsed+1e-6)
            self.assertLess(pygame.Vector3(before.position).distance_to(after.position),1e-4,elapsed)
            self.assertAlmostEqual(before.focal,after.focal,places=4)


class IceReaperDuelRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((480,320))
        cls.stage=IceReaperActionStage(ROOT/'assets/story/ice_reaper_rescue',strict=True)
        cls.duel=cls.stage.duel

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def render(self,elapsed,reduced=False):
        canvas=pygame.Surface((480,320));self.stage.draw(canvas,elapsed,reduced)
        return pygame.image.tobytes(canvas,'RGB')

    def test_one_world_sprite_per_actor_and_rhea_keeps_native_canvas(self):
        for elapsed in (21.5,24.2,24.6,25.1,26.2,27.3,28.5,29.15,30.1,31.1):
            self.render(elapsed)
            trace=self.duel.last_draw_trace
            actors=[entry['actor'] for entry in trace]
            self.assertEqual(len(actors),len(set(actors)),elapsed)
            for entry in trace:
                if entry['actor']=='rhea':self.assertEqual(entry['source_canvas'],[128,128])
            self.assertFalse(any('portrait' in entry for entry in trace))

    def test_pause_seek_and_reduced_motion_are_deterministic_without_asset_reads(self):
        with patch('pygame.image.load',side_effect=AssertionError('draw loaded an asset')):
            for reduced in (False,True):
                for elapsed in (24.5,26.2,27.9,30.7):
                    expected=self.render(elapsed,reduced)
                    self.render(21.3,reduced);self.stage.reset()
                    self.assertEqual(self.render(elapsed,reduced),expected)

    def test_six_fireballs_rise_from_the_fixed_pointed_rune_patterns(self):
        fx=self.duel.fx
        metadata=self.stage.rune_seal.metadata
        self.assertEqual(len(fx.anchors),metadata['spokes'])
        self.assertEqual(len(fx.anchors),6)
        center=pygame.Vector3(-3,.035,0)
        for index,anchor in enumerate(fx.anchors):
            angle=math.radians(metadata['spoke_start_angle_degrees'])+index*math.tau/metadata['spokes']
            expected=center+pygame.Vector3(math.cos(angle)*8.2*.78,0,math.sin(angle)*8.2*.78)
            self.assertLess(anchor.distance_to(expected),1e-7)
        before=fx.state(25.79)['fireballs']
        after=fx.state(26.7)['fireballs']
        self.assertFalse(any(record['active'] for record in before))
        self.assertTrue(all(record['active'] and record['rise']==1. for record in after))
        for elapsed in (26.7,27.9,29.15,31.1):
            current=fx.state(elapsed)['fireballs']
            for record,initial in zip(current,after):
                self.assertEqual(record['ground'],initial['ground'])
                self.assertEqual(record['position'][0],initial['position'][0])
                self.assertEqual(record['position'][2],initial['position'][2])

    def test_final_authored_actions_and_effects_are_loaded(self):
        self.assertIsNotNone(self.duel.fx)
        for actor in ('caelan','lucan','mira','rhea','ice_reaper'):
            self.assertIn(actor,self.duel.authored)
        self.assertGreaterEqual(len(self.duel.authored['rhea']['cast_rear']['images']),6)
        for actor,action in (('rhea','staff_sweep'),('ice_reaper','sword_conjure'),
                             ('ice_reaper','sword_windup'),('ice_reaper','sword_charge')):
            groups=[record for key,record in self.duel.authored[actor].items()
                    if key==action or key.startswith(action+'_')]
            self.assertTrue(groups,(actor,action))
            self.assertTrue(any(4<=len(record['images'])<=10 for record in groups),(actor,action))


if __name__=='__main__':unittest.main()
