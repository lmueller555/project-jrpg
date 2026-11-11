"""Production art registration and reproducibility across Mira's equipment cutover."""
import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image
from tools.build_mira_rig_continuity import build

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/characters/mira/arm_rig'


class WornRigContinuityTests(unittest.TestCase):
    def test_every_registered_export_rebuilds_without_changing_runtime_art(self):
        registration = json.loads((SOURCE/'registration.json').read_text())
        paths = [ROOT/entry['file'] for entry in registration['exports']]
        paths += list((ROOT/'assets/story/mira_prefire_aim').glob('*.png'))
        paths += list((ROOT/'assets/characters/mira').rglob('animation.json'))
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        build()
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        for source in registration['sources']:
            self.assertEqual(source['sha256'], hashlib.sha256((SOURCE/source['file']).read_bytes()).hexdigest())

    def test_directional_walks_keep_ground_contact_and_their_original_timing(self):
        drawings = []
        for direction in ('front', 'back', 'left', 'right'):
            folder = ROOT/f'assets/characters/mira/walk_{direction}'
            data = json.loads((folder/'animation.json').read_text())
            self.assertEqual(data['foot_anchor'], [16,34])
            self.assertEqual(len(data['frames']), 4)
            self.assertEqual([entry['duration_ms'] for entry in data['frames']], [140]*4)
            for entry in data['frames']:
                image = Image.open(folder/entry['file']).convert('RGBA')
                self.assertEqual(image.size, (32,36))
                self.assertIn(image.getbbox()[3], (34,35,36))
                drawings.append(image.tobytes())
        self.assertEqual(len(set(drawings)),16)
        # Authored profiles must not collapse into one mirrored drawing.
        left = Image.open(ROOT/'assets/characters/mira/idle_left.png')
        right = Image.open(ROOT/'assets/characters/mira/idle_right.png')
        self.assertNotEqual(left.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes(), right.tobytes())

    def test_prefire_endpoints_remain_the_exact_adjacent_runtime_drawings(self):
        folder = ROOT/'assets/story/mira_prefire_aim'
        for raised, endpoint in [('raise_01.png','ice_reaper_rescue/actors/mira/load_08.png'),
                                 ('raise_04.png','ice_reaper_continuity/actors/mira/aim_front_01.png')]:
            self.assertEqual(Image.open(folder/raised).tobytes(),
                             Image.open(ROOT/'assets/story'/endpoint).tobytes())
