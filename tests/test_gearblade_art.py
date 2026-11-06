"""Equipment and water-focus frame registration contracts."""
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

import pygame
from gearblade_art import GearbladeFocus,GearbladeCombat,combat_frame,prepare_combat_art

ROOT=Path(__file__).resolve().parents[1]


class GearbladeArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((480,320))
        cls.focus=GearbladeFocus()
        cls.combat=GearbladeCombat()
        prepare_combat_art()

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_water_focus_retains_mill_registration_and_clock(self):
        self.assertEqual(self.focus.anchor,(20,38))
        self.assertEqual(self.focus.duration,2.5)
        images=[]
        for time in (0.,.3,.6,.8,1.2,1.7,2.,2.4,2.5):
            image=self.focus.frame(time)
            self.assertEqual(image.get_size(),(40,48))
            bounds=image.get_bounding_rect()
            self.assertGreater(bounds.left,0)
            self.assertLess(bounds.right,40)
            self.assertGreaterEqual(bounds.bottom,41)
            self.assertLessEqual(bounds.bottom,44)
            images.append(pygame.image.tobytes(image,'RGBA'))
        self.assertGreaterEqual(len(set(images)),8)
        self.assertEqual(images[-1],pygame.image.tobytes(self.focus.frame(999),'RGBA'))

    def test_battle_canvas_margin_does_not_change_body_scale_or_floor_anchor(self):
        self.assertEqual(self.combat.anchor,(32,56))
        self.assertEqual(self.combat.manifest['body_pixels'],36)
        for state in ('idle','attack','cast','guard','hurt','victory','defeat'):
            for time in (0,100,300,1000):
                image,anchor=combat_frame(pygame.Surface((48,48)),state,time)
                self.assertEqual(image.get_size(),(64,64))
                self.assertEqual(anchor,(32,56))
                bounds=image.get_bounding_rect()
                self.assertGreater(bounds.left,0)
                self.assertLess(bounds.right,64)
                self.assertGreaterEqual(bounds.top,0)
                self.assertLessEqual(bounds.bottom,59)

    def test_cached_pose_selection_never_reads_assets_during_render(self):
        with patch('pygame.image.load',side_effect=AssertionError('Late asset read')):
            for time in (.1,.8,1.5,2.4):
                self.focus.frame(time)
                combat_frame(pygame.Surface((48,48)),'attack',time*1000)

    def test_source_and_export_provenance_matches_files(self):
        for family in ('world','combat'):
            folder=ROOT/'assets/story/gearblade_focus'/family
            record=json.loads((folder/'provenance.json').read_text())
            self.assertEqual(hashlib.sha256((ROOT/record['source']).read_bytes()).hexdigest(),record['source_sha256'])
            for frame in record['frames']:
                self.assertEqual(hashlib.sha256((folder/frame['file']).read_bytes()).hexdigest(),frame['sha256'])


if __name__=='__main__':unittest.main()
