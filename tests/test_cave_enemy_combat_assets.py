"""Generous authored cave-enemy poses survive native export and real sampling."""
from collections import defaultdict
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
import pygame

from battle_model import load_actions
from battle_scene import CombatSprites
from bestiary import build_enemy


ROOT = Path(__file__).resolve().parents[1]
DESIGNS = {
    'lithrusk': {'canvas': (112, 96), 'anchor': (48, 84), 'level': 2,
                'states': {'idle': 12, 'walk': 12, 'claw_clamp': 16,
                           'shell_bash': 16, 'hurt': 10, 'defeat': 16}},
    'veylume': {'canvas': (112, 104), 'anchor': (56, 88), 'level': 3,
               'states': {'idle': 16, 'fly': 16, 'static_spark': 16,
                          'gather_charge': 16, 'veinflash': 20,
                          'hurt': 10, 'defeat': 16}},
}


class CaveEnemyCombatAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.display.set_mode((1, 1))
        cls.sprites = CombatSprites()
        cls.actions = load_actions()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def manifest(self, actor):
        return json.loads((ROOT/'assets/combat'/actor/'animation.json').read_text())

    def test_both_exporters_rebuild_deterministically_from_retained_sources(self):
        for actor in DESIGNS:
            with self.subTest(actor=actor):
                result = subprocess.run([sys.executable, 'tools/build_'+actor+'_combat.py', '--check'],
                                        cwd=ROOT, capture_output=True, text=True, timeout=180)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_every_animation_contains_generous_real_unclipped_binary_alpha_poses(self):
        for actor, design in DESIGNS.items():
            data = self.manifest(actor)
            self.assertEqual(tuple(data['canvas']), design['canvas'])
            self.assertEqual(tuple(data['anchor']), design['anchor'])
            self.assertEqual(data['facing'], 'right')
            self.assertTrue(set(design['states']) <= set(data['animations']))
            for state, minimum in design['states'].items():
                with self.subTest(actor=actor, state=state):
                    sequence = data['animations'][state]
                    frames = sequence['frames']
                    self.assertGreaterEqual(len(frames), minimum)
                    self.assertIs(type(sequence['loop']), bool)
                    colors, masks, sources = set(), set(), set()
                    for frame in frames:
                        self.assertIs(type(frame['duration_ms']), int)
                        self.assertGreater(frame['duration_ms'], 0)
                        with Image.open(ROOT/'assets/combat'/actor/frame['file']) as image:
                            self.assertEqual(image.mode, 'RGBA')
                            self.assertEqual(image.size, design['canvas'])
                            alpha = image.getchannel('A')
                            self.assertEqual(set(alpha.tobytes()), {0, 255})
                            box = alpha.getbbox()
                            self.assertIsNotNone(box)
                            self.assertGreater(box[0], 0)
                            self.assertGreater(box[1], 0)
                            self.assertLess(box[2], image.width)
                            self.assertLess(box[3], image.height)
                            colors.add(sha256(image.tobytes()).digest())
                            masks.add(sha256(alpha.tobytes()).digest())
                        sources.add((frame['source_sheet'], frame['source_cell']))
                    # Endpoint holds may repeat, but translations, glow-only
                    # changes or one repeated drawing cannot stand in for a
                    # generous bank of authored body/wing/claw poses.
                    self.assertGreaterEqual(len(colors), math.ceil(len(frames)*.75))
                    self.assertGreaterEqual(len(masks), math.ceil(len(frames)*.4))
                    self.assertGreaterEqual(len(sources), math.ceil(len(frames)*.75))

    def test_frames_reference_real_source_cells_at_one_scale_per_sheet(self):
        source_bytes = {}
        for actor in DESIGNS:
            scale_by_sheet = defaultdict(set)
            for state in DESIGNS[actor]['states']:
                for frame in self.manifest(actor)['animations'][state]['frames']:
                    sheet = frame['source_sheet']
                    if sheet not in source_bytes:
                        path = ROOT/sheet
                        self.assertTrue(path.is_file(), sheet)
                        source_bytes[sheet] = path.read_bytes()
                    self.assertEqual(sha256(source_bytes[sheet]).hexdigest(), frame['source_sha256'])
                    self.assertIs(type(frame['source_cell']), int)
                    self.assertGreaterEqual(frame['source_cell'], 0)
                    x, y, width, height = frame['source_rect']
                    self.assertTrue(all(type(value) is int for value in (x, y, width, height)))
                    self.assertGreater(width, 0)
                    self.assertGreater(height, 0)
                    with Image.open(ROOT/sheet) as image:
                        self.assertGreaterEqual(x, 0)
                        self.assertGreaterEqual(y, 0)
                        self.assertLessEqual(x+width, image.width)
                        self.assertLessEqual(y+height, image.height)
                    if 'native_scale' in frame:
                        self.assertGreater(frame['native_scale'], 0)
                        scale_by_sheet[sheet].add(frame['native_scale'])
            self.assertTrue(all(len(scales) == 1 for scales in scale_by_sheet.values()),
                            'Per-pose autoscaling would change body size during an animation')

    def test_every_species_action_selects_its_real_pose_and_exact_impact_clock(self):
        for actor, design in DESIGNS.items():
            data = self.manifest(actor)
            record = build_enemy(actor, design['level'])
            self.assertEqual(record['presentation']['sprite_id'], actor)
            self.assertFalse(record['metadata']['presentation_pending'])
            for identifier in record['behavior']['sequence']:
                action = self.actions[identifier]
                state = record['presentation']['action_aliases'].get(identifier, action['animation'])
                with self.subTest(actor=actor, action=identifier, state=state):
                    self.assertIn(state, data['animations'], 'An action must never fall back to idle')
                    animation = data['animations'][state]
                    self.assertFalse(animation['loop'])
                    frames = animation['frames']
                    self.assertEqual(sum(frame['duration_ms'] for frame in frames),
                                     round(action['duration']*1000))
                    elapsed = action['impact_at']*1000
                    start = 0
                    selected = None
                    for frame in frames:
                        if start <= elapsed < start+frame['duration_ms']:
                            selected = frame
                            break
                        start += frame['duration_ms']
                    self.assertIsNotNone(selected)
                    actual, anchor = self.sprites.frame(actor, state, elapsed)
                    expected = pygame.image.load(str(ROOT/'assets/combat'/actor/selected['file']))
                    self.assertEqual(anchor, design['anchor'])
                    self.assertEqual(pygame.image.tobytes(actual, 'RGBA'),
                                     pygame.image.tobytes(expected, 'RGBA'))
                    if 'contact_ms' in animation:
                        self.assertEqual(animation['contact_ms'], round(elapsed))
                    if 'contact_frame' in animation:
                        self.assertEqual(frames[animation['contact_frame']]['file'], selected['file'])

    def test_nonlooping_hurt_and_defeat_hold_their_authored_final_frame(self):
        for actor in DESIGNS:
            data = self.manifest(actor)
            for state in ('hurt', 'defeat'):
                with self.subTest(actor=actor, state=state):
                    animation = data['animations'][state]
                    self.assertFalse(animation['loop'])
                    expected = pygame.image.load(str(ROOT/'assets/combat'/actor/
                                                      animation['frames'][-1]['file']))
                    actual, _ = self.sprites.frame(actor, state, 1000000)
                    self.assertEqual(pygame.image.tobytes(actual, 'RGBA'),
                                     pygame.image.tobytes(expected, 'RGBA'))

    def test_grounded_feet_do_not_swim_and_the_moth_defeat_lands_on_its_anchor(self):
        data = self.manifest('lithrusk')
        for state in ('idle', 'walk', 'claw_clamp', 'shell_bash'):
            bottoms = []
            for frame in data['animations'][state]['frames']:
                with Image.open(ROOT/'assets/combat/lithrusk'/frame['file']) as image:
                    bottoms.append(image.getchannel('A').getbbox()[3])
            self.assertLessEqual(max(bottoms)-min(bottoms), 2, state)
            self.assertLessEqual(abs(sum(bottoms)/len(bottoms)-data['anchor'][1]), 2, state)
        data = self.manifest('veylume')
        final = data['animations']['defeat']['frames'][-1]
        with Image.open(ROOT/'assets/combat/veylume'/final['file']) as image:
            self.assertLessEqual(abs(image.getchannel('A').getbbox()[3]-data['anchor'][1]), 2)


if __name__ == '__main__':
    unittest.main()
