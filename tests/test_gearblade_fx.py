"""Authored action timing and registered, deterministic gearblade effects."""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

import pygame

from gearblade_art import GearbladeCombat, anchors, combat_frame, prepare_combat_art
from gearblade_fx import GearbladeEffects


ROOT=Path(__file__).resolve().parents[1]


def pixels(surface):
    return pygame.image.tobytes(surface,'RGBA')


class GearbladeEffectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((480,320))
        cls.art=prepare_combat_art()
        cls.fx=GearbladeEffects(cls.art)

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def render(self, *, point=(160,140), state='idle', time_ms=0,
               gem='water', elapsed=1., slot_age=None, action=None, reduced_motion=False):
        canvas=pygame.Surface((480,320),pygame.SRCALPHA)
        self.fx.draw(canvas,point,state,time_ms,gem,elapsed,slot_age,action,reduced_motion)
        return canvas

    def test_authored_gesture_and_edge_have_distinct_drawings_registered_to_same_floor(self):
        for state,count,total in (('focus_adjust',4,600),('aether_edge',8,900)):
            entry=self.art.manifest['animations'][state]
            self.assertEqual(sum(f['duration_ms'] for f in entry['frames']),total)
            drawings=[]
            time=0
            for frame in entry['frames']:
                image,anchor=combat_frame(pygame.Surface((48,48)),state,time)
                self.assertEqual(image.get_size(),(64,64))
                self.assertEqual(anchor,(32,56))
                bounds=image.get_bounding_rect()
                self.assertGreater(bounds.left,0)
                self.assertLess(bounds.right,64)
                self.assertLessEqual(bounds.bottom,58)
                self.assertGreaterEqual(bounds.bottom,55)
                drawings.append(pixels(image))
                for key in ('guard','active_gem','blade_base','blade_tip'):
                    self.assertEqual(len(anchors(state,time)[key]),2)
                time+=frame['duration_ms']
            self.assertEqual(len(set(drawings)),count)
            self.assertEqual(pixels(self.art.frame(state,9999)[0]),drawings[-1])
        edge=self.art.manifest['animations']['aether_edge']
        self.assertEqual(edge['contact_at_ms'],500)
        self.assertEqual(sum(f['duration_ms'] for f in edge['frames'][:edge['contact_frame']]),500)
        self.assertEqual(self.art.anchors('aether_edge',499)['frame_index'],3)
        self.assertEqual(self.art.anchors('aether_edge',500)['frame_index'],4)

    def test_additional_atlas_is_the_unmodified_generated_asset(self):
        folder=ROOT/'assets/story/gearblade_focus/combat'
        record=json.loads((folder/'focus_aether_provenance.json').read_text())
        self.assertEqual(record['generated_with'],'image_gen')
        self.assertEqual(hashlib.sha256((folder/record['file']).read_bytes()).hexdigest(),record['sha256'])
        self.assertEqual(record['drawings'],12)

    def test_effects_translate_with_moving_actor_and_selected_weapon_pose(self):
        first=self.render(point=(160,140),state='attack',time_ms=200)
        second=self.render(point=(230,165),state='attack',time_ms=200)
        self.assertEqual(first.get_bounding_rect().move(70,25),second.get_bounding_rect())
        self.assertEqual(pixels(first.subsurface(first.get_bounding_rect())),
                         pixels(second.subsurface(second.get_bounding_rect())))
        sample=self.fx.sample((230,165),'attack',200,'water',1.)
        local=self.art.anchors('attack',200)
        self.assertEqual(sample['anchors']['blade_tip'],
                         (230+(local['blade_tip'][0]-32)*2,
                          165+(local['blade_tip'][1]-56)*2))
        idle=self.fx.sample((230,165),'idle',0,'water',1.)
        self.assertNotEqual(sample['anchors']['blade_tip'],idle['anchors']['blade_tip'])

    def test_all_four_element_loops_are_visible_distinct_and_quiet(self):
        frames=[]
        for gem in ('nature','water','fire','ice'):
            canvas=self.render(gem=gem)
            self.assertTrue(canvas.get_bounding_rect())
            self.assertLess(canvas.get_bounding_rect().width,65)
            self.assertLess(canvas.get_bounding_rect().height,65)
            frames.append(pixels(canvas))
        self.assertEqual(len(set(frames)),4)
        self.assertNotEqual(pixels(self.render(elapsed=1.)),pixels(self.render(elapsed=1.6)))

    def test_failed_attempt_sputters_and_never_draws_a_successful_edge(self):
        fail=SimpleNamespace(action='flame_edge',kind='failed_edge',elapsed=.28)
        sample=self.fx.sample((160,140),'cast',280,'fire',1.,action=fail)
        self.assertEqual(sample['mode'],'failed')
        self.assertEqual(sample['effect'],'fire')
        active=self.render(state='cast',time_ms=280,gem='fire',action=fail)
        fail.elapsed=.8
        spent=self.render(state='cast',time_ms=280,gem='fire',action=fail)
        self.assertNotEqual(pixels(active),pixels(spent))
        self.assertEqual(self.fx.sample((160,140),'cast',280,'fire',1.,action=fail)['contact'],0)

    def test_aether_is_non_elemental_for_every_gem_and_contact_is_at_half_second(self):
        edge=SimpleNamespace(action='aether_edge',kind='spellblade',elapsed=.5)
        frames=[pixels(self.render(state='aether_edge',time_ms=500,gem=gem,action=edge))
                for gem in ('nature','water','fire','ice')]
        self.assertEqual(len(set(frames)),1)
        sample=self.fx.sample((160,140),'aether_edge',500,'fire',1.,action=edge)
        self.assertEqual(sample['effect'],'aether')
        self.assertEqual(sample['contact'],1.)
        edge.elapsed=.3
        self.assertEqual(self.fx.sample((160,140),'aether_edge',300,'fire',1.,action=edge)['contact'],0.)
        edge.elapsed=.8
        self.assertEqual(self.fx.sample((160,140),'aether_edge',800,'fire',1.,action=edge)['contact'],0.)

    def test_reduced_motion_is_static_and_defeat_has_no_weapon_effect(self):
        for gem in ('nature','water','fire','ice'):
            self.assertEqual(pixels(self.render(gem=gem,elapsed=0.,reduced_motion=True)),
                             pixels(self.render(gem=gem,elapsed=99.,reduced_motion=True)))
        self.assertFalse(self.render(state='defeat').get_bounding_rect())

    def test_draw_is_seekable_bounded_and_never_reads_assets(self):
        layer=self.fx._layer
        with patch('pygame.image.load',side_effect=AssertionError('Render-time asset read')):
            expected=pixels(self.render(state='focus_adjust',time_ms=260,slot_age=.2))
            for age in (40.,0.,900.,.2,200.):
                self.render(elapsed=age,state='aether_edge',time_ms=age*1000)
            self.assertEqual(expected,pixels(self.render(state='focus_adjust',time_ms=260,slot_age=.2)))
        self.assertIs(self.fx._layer,layer)
        self.assertEqual(layer.get_size(),(176,176))


if __name__=='__main__':unittest.main()
