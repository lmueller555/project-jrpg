"""Mira's new drawings preserve anatomical registration and combat continuity."""
import hashlib
import json
import os
from pathlib import Path
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from PIL import Image

from battle_model import load_actions
from battle_scene import CombatSprites
from mira_combat_art import MiraCombatArt

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/'assets/combat/mira'


class MiraRedrawAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.display.set_mode((480,320))
        cls.data = json.loads((ART/'animation.json').read_text())
        cls.anchors = MiraCombatArt()
        cls.sprites = CombatSprites()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_drawings_use_anatomical_floor_registration_instead_of_silhouette_center(self):
        records = {frame['source_cell']: frame for animation in self.data['animations'].values()
                   for frame in animation['frames']}
        self.assertEqual(len(records), 82)
        for index, frame in records.items():
            with self.subTest(drawing=index):
                self.assertEqual(frame['anchors']['floor'], [32,54])
                left, top, _, _ = frame['source_bounds']
                cell_x, cell_y, _, _ = frame['source_rect']
                foot_x, foot_y = frame['source_foot']
                scale = frame['native_scale']
                self.assertEqual(frame['position'],
                    [round(32-(cell_x+foot_x-left)*scale),
                     round(54-(cell_y+foot_y-top)*scale)])

    def test_sprite_and_attachment_samplers_select_same_drawing_at_every_boundary(self):
        for state, animation in self.data['animations'].items():
            clock = 0
            for expected in animation['frames']:
                for time in (clock, clock+expected['duration_ms']-1):
                    with self.subTest(state=state, time=time):
                        record = self.anchors.frame_record(state, time)
                        self.assertEqual(record['file'], expected['file'])
                        actual, floor = self.sprites.frame('mira', state, time)
                        pixels = pygame.image.load(str(ART/expected['file']))
                        self.assertEqual(pygame.image.tobytes(actual,'RGBA'),
                                         pygame.image.tobytes(pixels,'RGBA'))
                        self.assertEqual(floor, (32,54))
                clock += expected['duration_ms']

    def test_release_is_on_weapon_and_keeps_existing_action_impact_and_duration(self):
        actions = load_actions()
        for state, action in (('attack','bolt_shot'),('overclock','overclock')):
            animation = self.data['animations'][state]
            self.assertEqual(sum(f['duration_ms'] for f in animation['frames']),
                             actions[action]['duration']*1000)
            self.assertEqual(animation['contact_ms'],actions[action]['impact_at']*1000)
        attack = self.data['animations']['attack']
        self.assertEqual(attack['release_ms'],280)
        self.assertLess(attack['release_ms'], attack['contact_ms'])
        record = self.anchors.frame_record('attack', attack['release_ms'])
        muzzle = record['anchors']['muzzle']
        image = Image.open(ART/record['file']).convert('RGBA')
        x,y = muzzle
        self.assertTrue(image.getchannel('A').crop((x-2,y-2,x+3,y+3)).getbbox(),
                        'Released bolt must be attached to the rendered weapon')
        for frame in self.data['animations']['overclock']['frames']:
            self.assertIn('controller', frame['anchors'])

    def test_held_guard_brace_and_hurt_have_different_authored_drawings(self):
        files = {state:{frame['file'] for frame in self.data['animations'][state]['frames']}
                 for state in ('guard','guard_impact','hurt')}
        for left,right in (('guard','guard_impact'),('guard_impact','hurt')):
            self.assertFalse(files[left] & files[right])
            pixels = [set(Image.open(ART/f).tobytes() for f in files[state])
                      for state in (left,right)]
            self.assertFalse(pixels[0] & pixels[1])
        self.assertTrue(self.data['animations']['guard']['loop'])
        self.assertFalse(self.data['animations']['guard_impact']['loop'])
        self.assertFalse(self.data['animations']['defeat']['loop'])
        self.assertFalse(self.data['animations']['victory']['loop'])

    def test_existing_overworld_launcher_remains_pixel_identical(self):
        self.assertEqual(hashlib.sha256((ART/'world_bolt_launcher.png').read_bytes()).hexdigest(),
                         'c4b72145c0007034958f8246d8b0c9e046a4eeddab78ff9457b4ae2f571f77cc')

    def test_arm_rig_studies_have_complete_registered_sequences_and_retained_sources(self):
        sources = {entry['path']: entry for entry in self.data['source_sheets']}
        self.assertEqual(len(sources), 2)
        for path, record in sources.items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), record['sha256'])
        for state in ('charged_bolt', 'bulwark', 'repair_pulse', 'impact_bolt', 'arc_discharge'):
            animation = self.data['animations'][state]
            self.assertEqual(len(animation['frames']), 8)
            self.assertFalse(animation['loop'])
            for frame in animation['frames']:
                with self.subTest(state=state, frame=frame['file']):
                    self.assertIn(frame['source_sheet'], sources)
                    image = Image.open(ART/frame['file']).convert('RGBA')
                    for anchor in ('muzzle', 'controller'):
                        x, y = frame['anchors'][anchor]
                        self.assertTrue(image.getchannel('A').crop((x-2,y-2,x+3,y+3)).getbbox(),
                                        anchor+' must attach to the worn rig')


if __name__ == '__main__':
    unittest.main()
