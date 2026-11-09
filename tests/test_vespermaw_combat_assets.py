"""The miniboss bank retains generous real drawings and reproducible registration."""
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/'assets/combat/vespermaw'
SOURCE = ROOT/'assets/source/combat/vespermaw'
COUNTS = {'idle': 16, 'prowl': 16, 'raking_claw': 32, 'confluence_roar': 32,
          'gather_resonance': 32, 'charged_hold': 32, 'ruinous_pounce': 32,
          'exhausted': 16, 'hurt': 16, 'defeat': 32}


class VespermawCombatAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ART/'animation.json').read_text())
        cls.recipe = json.loads((SOURCE/'registration.json').read_text())

    def test_builder_reproduces_all_runtime_exports_from_retained_source_art(self):
        result = subprocess.run([sys.executable, 'tools/build_vespermaw_combat.py', '--check'],
                                cwd=ROOT, capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(self.data['registration_sha256'],
                         sha256((SOURCE/'registration.json').read_bytes()).hexdigest())

    def test_every_animation_uses_generous_distinct_whole_body_drawings(self):
        data = self.data
        self.assertEqual((data['actor'], data['facing']), ('vespermaw', 'right'))
        self.assertEqual(data['canvas'], [160, 144])
        self.assertEqual(data['anchor'], [64, 128])
        self.assertEqual(data['authored_frames'], 256)
        self.assertEqual(set(data['animations']), set(COUNTS))
        all_sources, all_colors = set(), set()
        for state, count in COUNTS.items():
            with self.subTest(state=state):
                animation = data['animations'][state]
                self.assertEqual(len(animation['frames']), count)
                self.assertEqual(animation['loop'], state in ('idle', 'prowl', 'charged_hold', 'exhausted'))
                fingerprints, silhouettes = set(), set()
                for frame in animation['frames']:
                    self.assertIs(type(frame['duration_ms']), int)
                    self.assertGreater(frame['duration_ms'], 0)
                    all_sources.add((frame['source_sheet'], frame['source_cell']))
                    with Image.open(ART/frame['file']) as image:
                        self.assertEqual(image.mode, 'RGBA')
                        self.assertEqual(image.size, (160, 144))
                        alpha = image.getchannel('A')
                        self.assertEqual(set(alpha.tobytes()), {0, 255})
                        bounds = alpha.getbbox()
                        self.assertIsNotNone(bounds)
                        self.assertGreater(bounds[0], 0)
                        self.assertGreater(bounds[1], 0)
                        self.assertLess(bounds[2], image.width)
                        self.assertLess(bounds[3], image.height)
                        self.assertEqual(list(bounds), frame['native_bounds'])
                        fingerprints.add(sha256(image.tobytes()).digest())
                        silhouettes.add(sha256(alpha.tobytes()).digest())
                        all_colors.update(pixel[:3] for pixel in image.get_flattened_data() if pixel[3])
                self.assertGreaterEqual(len(fingerprints), math.ceil(count*.9))
                self.assertGreaterEqual(len(silhouettes), math.ceil(count*.5))
        self.assertEqual(len(all_sources), 256, 'Held or recolored copies are not extra authored poses')
        self.assertLessEqual(len(all_colors), self.data['palette_colors'])

    def test_source_provenance_and_anatomical_anchors_survive_registration(self):
        source_sizes = {}
        for name, expected in self.data['source_sha256'].items():
            path = ROOT/name
            self.assertEqual(sha256(path.read_bytes()).hexdigest(), expected)
            with Image.open(path) as image:source_sizes[name] = image.size
        used = set()
        for animation in self.data['animations'].values():
            for frame in animation['frames']:
                with self.subTest(file=frame['file']):
                    source = frame['source_sheet']
                    self.assertEqual(frame['source_sha256'], self.data['source_sha256'][source])
                    self.assertEqual(frame['native_scale'], self.data['native_scale'])
                    x, y, width, height = frame['source_rect']
                    sheet_width, sheet_height = source_sizes[source]
                    self.assertTrue(0 <= x < x+width <= sheet_width)
                    self.assertTrue(0 <= y < y+height <= sheet_height)
                    self.assertIs(type(frame['source_cell']), int)
                    self.assertGreaterEqual(frame['source_cell'], 0)
                    self.assertEqual(frame['anchors']['floor'], [64, 128])
                    self.assertTrue({'floor', 'body', 'contact', 'cast_origin'} <= set(frame['anchors']))
                    for point in frame['anchors'].values():
                        self.assertEqual(len(point), 2)
                        self.assertTrue(all(type(value) is int for value in point))
                        self.assertTrue(0 <= point[0] < 160 and 0 <= point[1] < 144)
                    used.add((source, frame['source_cell']))
        self.assertEqual(len(used), 256)

    def test_action_contacts_have_exact_art_clocks_and_defeat_keeps_its_corpse(self):
        for state in ('raking_claw', 'confluence_roar', 'gather_resonance', 'ruinous_pounce'):
            with self.subTest(state=state):
                animation = self.data['animations'][state]
                self.assertFalse(animation['loop'])
                contact = animation['contact_frame']
                self.assertEqual(sum(frame['duration_ms'] for frame in animation['frames'][:contact]),
                                 animation['contact_ms'])
        final = self.data['animations']['defeat']['frames'][-1]
        with Image.open(ART/final['file']) as image:
            self.assertGreater(image.getchannel('A').getbbox()[2]-image.getchannel('A').getbbox()[0], 30)
            self.assertLessEqual(abs(image.getchannel('A').getbbox()[3]-128), 2)
        self.assertFalse(self.data['animations']['defeat']['loop'])

    def test_registration_keeps_grounded_feet_still_and_preserves_the_authored_jump(self):
        for state in ('idle', 'prowl', 'gather_resonance', 'charged_hold', 'exhausted'):
            with self.subTest(state=state):
                bottoms = []
                for frame in self.data['animations'][state]['frames']:
                    with Image.open(ART/frame['file']) as image:bottoms.append(image.getbbox()[3])
                self.assertLessEqual(max(bottoms)-min(bottoms), 2)
                self.assertLessEqual(abs(sum(bottoms)/len(bottoms)-128), 2)
        bottoms = []
        for frame in self.data['animations']['ruinous_pounce']['frames']:
            with Image.open(ART/frame['file']) as image:bottom = image.getbbox()[3]
            bottoms.append(bottom)
            _, y, _, height = frame['source_rect']
            # The visible airborne gap comes from each real source drawing's
            # position above its authored row floor, not an added animation arc.
            expected = 128-(frame['source_foot'][1]-y-height)*self.data['native_scale']
            self.assertLessEqual(abs(bottom-expected), 1)
        self.assertLess(min(bottoms), 128-30)
        self.assertLessEqual(abs(bottoms[-1]-128), 2)

    def test_atlas_contains_each_export_once_and_has_no_hidden_extra_frames(self):
        data = self.data
        with Image.open(ART/data['sheet']) as sheet:
            self.assertEqual(sheet.size, (160*16, 144*16))
            index = 0
            for animation in data['animations'].values():
                for frame in animation['frames']:
                    x, y = index%16*160, index//16*144
                    with Image.open(ART/frame['file']) as image:
                        self.assertEqual(sheet.crop((x,y,x+160,y+144)).tobytes(), image.tobytes())
                    index += 1
            self.assertEqual(index, 256)


if __name__ == '__main__':unittest.main()
