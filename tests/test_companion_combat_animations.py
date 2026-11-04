"""Companion combat packs retain every authored pose and play at native size."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from PIL import Image

from battle_scene import CombatSprites
from tools import build_companion_combat_animations as exporter
from tools import build_companion_sprite_studies as studies


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/'assets/combat'
ACTORS = {'lucan': 'technique', 'rhea': 'cast'}
TIMINGS = {
    'idle': ([180]*4, True),
    'attack': ([160, 180, 120, 260], False),
    'special': ([220, 280, 160, 240], False),
    'guard': ([240]*2, True),
    'hurt': ([160, 240], False),
    'victory': ([340]*2, True),
    'defeat': ([260, 420], False),
    'walk': ([140]*4, True),
}


def manifest(actor):
    return json.loads((ART/actor/'animation.json').read_text(encoding='utf-8'))


def frame_bytes(actor, filename):
    with Image.open(ART/actor/filename) as image:
        return image.convert('RGBA').tobytes()


class CompanionCombatAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.display.set_mode((480, 320))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_all_24_native_poses_are_distinct_transparent_and_unclipped(self):
        for actor in ACTORS:
            data = manifest(actor)
            self.assertEqual(data['canvas'], [64, 64])
            self.assertEqual(data['anchor'], [32, 54])
            self.assertEqual(data['facing'], 'left')
            records = {record['file']: record
                       for animation in data['animations'].values()
                       for record in animation['frames']}
            self.assertEqual(len(records), 24, actor)
            unique_pixels = set()
            for filename in records:
                with self.subTest(actor=actor, frame=filename):
                    with Image.open(ART/actor/filename) as source:
                        image = source.convert('RGBA')
                    self.assertEqual(image.size, (64, 64))
                    alpha = image.getchannel('A')
                    self.assertEqual(set(alpha.tobytes()), {0, 255})
                    bounds = alpha.getbbox()
                    self.assertIsNotNone(bounds)
                    self.assertGreater(bounds[0], 0)
                    self.assertGreater(bounds[1], 0)
                    self.assertLess(bounds[2], 64)
                    self.assertLess(bounds[3], 64)
                    unique_pixels.add(image.tobytes())
            self.assertEqual(len(unique_pixels), 24, actor)

    def test_source_hash_and_cells_account_for_every_authored_pose(self):
        for actor in ACTORS:
            with self.subTest(actor=actor):
                data = manifest(actor)
                source = ROOT/data['source_sheet']
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
                                 data['source_sha256'])
                with Image.open(source) as image:
                    width, height = image.size
                    source_alpha = image.convert('RGBA').getchannel('A')
                records = {record['file']: record
                           for animation in data['animations'].values()
                           for record in animation['frames']}
                self.assertEqual({record['source_cell'] for record in records.values()},
                                 set(range(24)))
                for filename, record in records.items():
                    with self.subTest(frame=filename):
                        cell = record['source_cell']
                        column, row = cell % 4, cell // 4
                        left, top, right, bottom = record['source_bounds']
                        self.assertTrue(0 <= left < right <= width)
                        self.assertTrue(0 <= top < bottom <= height)
                        # A sword may cross a grid line. Its complete cutout
                        # must still belong to the declared logical cell.
                        self.assertTrue(column*width/4 <= (left+right)/2
                                        < (column+1)*width/4)
                        self.assertTrue(row*height/6 <= (top+bottom)/2
                                        < (row+1)*height/6)
                        self.assertIsNotNone(source_alpha.crop(
                            (left, top, right, bottom)).getbbox())

    def test_full_state_timing_and_contacts_use_the_authored_impact_pose(self):
        sprites = CombatSprites()
        for actor, special in ACTORS.items():
            animations = manifest(actor)['animations']
            required = {special if state == 'special' else state for state in TIMINGS}
            self.assertLessEqual(required | {'flee'}, set(animations))
            for state, (durations, loop) in TIMINGS.items():
                state = special if state == 'special' else state
                with self.subTest(actor=actor, state=state):
                    animation = animations[state]
                    self.assertEqual([frame['duration_ms'] for frame in animation['frames']],
                                     durations)
                    self.assertIs(animation['loop'], loop)
            for state, contact in (('attack', 360), (special, 500)):
                with self.subTest(actor=actor, contact=state):
                    animation = animations[state]
                    self.assertEqual(animation['contact_ms'], contact)
                    frames = animation['frames']
                    contact_start = sum(frame['duration_ms'] for frame in frames[:2])
                    self.assertLessEqual(contact_start, contact)
                    self.assertLess(contact, contact_start+frames[2]['duration_ms'])
                    surface, anchor = sprites.frame(actor, state, contact)
                    self.assertEqual(pygame.image.tobytes(surface, 'RGBA'),
                                     frame_bytes(actor, frames[2]['file']))
                    self.assertEqual(anchor, (32, 54))

    def test_loader_selects_each_frame_then_wraps_or_holds_without_anchor_drift(self):
        sprites = CombatSprites()
        self.assertEqual(set(sprites.actors), {'caelan', 'bat'})
        for actor, special in ACTORS.items():
            animations = manifest(actor)['animations']
            for state, (_, loop) in TIMINGS.items():
                state = special if state == 'special' else state
                frames = animations[state]['frames']
                elapsed = 0
                for frame in frames:
                    for time in (elapsed, elapsed+frame['duration_ms']-1):
                        with self.subTest(actor=actor, state=state, elapsed=time):
                            surface, anchor = sprites.frame(actor, state, time)
                            self.assertEqual(surface.get_size(), (64, 64))
                            self.assertEqual(anchor, (32, 54))
                            self.assertEqual(pygame.image.tobytes(surface, 'RGBA'),
                                             frame_bytes(actor, frame['file']))
                    elapsed += frame['duration_ms']
                for time in (elapsed, elapsed*3+1):
                    with self.subTest(actor=actor, state=state, end=time):
                        surface, _ = sprites.frame(actor, state, time)
                        expected = frames[0] if loop else frames[-1]
                        self.assertEqual(pygame.image.tobytes(surface, 'RGBA'),
                                         frame_bytes(actor, expected['file']))
                surface, _ = sprites.frame(actor, state, -1)
                self.assertEqual(pygame.image.tobytes(surface, 'RGBA'),
                                 frame_bytes(actor, frames[0]['file']))
            for elapsed in (0, 139, 140, 279, 280, 419, 420, 559, 560, 1681):
                with self.subTest(actor=actor, flee=elapsed):
                    flee, flee_anchor = sprites.frame(actor, 'flee', elapsed)
                    walk, walk_anchor = sprites.frame(actor, 'walk', elapsed)
                    self.assertEqual(pygame.image.tobytes(flee, 'RGBA'),
                                     pygame.image.tobytes(walk, 'RGBA'))
                    self.assertEqual(flee_anchor, walk_anchor)
        self.assertLessEqual(set(ACTORS), set(sprites.actors))

    def test_exporter_roundtrip_is_byte_identical_and_repeatable(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            for actor in ACTORS:
                exporter.build_actor(actor, output_root=output)
                generated = {path.relative_to(output/actor): path.read_bytes()
                             for path in (output/actor).rglob('*') if path.is_file()}
                required = {Path('animation.json')} | {
                    Path(frame['file'])
                    for animation in manifest(actor)['animations'].values()
                    for frame in animation['frames']}
                self.assertLessEqual(required, set(generated))
                for relative, content in generated.items():
                    with self.subTest(actor=actor, file=str(relative)):
                        self.assertEqual(content, (ART/actor/relative).read_bytes())
                exporter.build_actor(actor, output_root=output)
                rebuilt = {path.relative_to(output/actor): path.read_bytes()
                           for path in (output/actor).rglob('*') if path.is_file()}
                self.assertEqual(rebuilt, generated)

    def test_appearance_study_rebuild_preserves_the_complete_combat_pack(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            for actor in ACTORS:
                with self.subTest(actor=actor):
                    folder = temporary_root/'assets/combat'/actor
                    shutil.copytree(ART/actor, folder)
                    original = {path.relative_to(folder): path.read_bytes()
                                for path in folder.rglob('*') if path.is_file()}
                    with patch.object(studies, 'ROOT', temporary_root), \
                            patch.object(studies, 'SOURCE', ROOT/'assets/source/companions'), \
                            patch.object(studies, 'FORMATS', {'combat': studies.FORMATS['combat']}), \
                            patch.object(studies, 'export_pose') as export_pose, \
                            patch.object(studies, 'write_json') as write_json, \
                            patch.object(Image.Image, 'save') as save_image:
                        frames, records = studies.build_actor(actor)
                    export_pose.assert_not_called()
                    write_json.assert_not_called()
                    save_image.assert_not_called()
                    self.assertEqual(frames['combat'].tobytes(),
                                     frame_bytes(actor, 'idle_01.png'))
                    self.assertEqual(records['combat']['status'], manifest(actor)['status'])
                    preserved = {path.relative_to(folder): path.read_bytes()
                                 for path in folder.rglob('*') if path.is_file()}
                    self.assertEqual(preserved, original)


if __name__ == '__main__':
    unittest.main()
