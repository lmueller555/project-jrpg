"""Real ascent-bank validation and ownership, using native placeholder pictures.

The party/guard manifests declare unused pose files. These fixtures establish
metadata, lazy decoding and cache contracts; they do not represent final art.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame
from PIL import Image

from cinematic_bridge_ascent import (ACTORS, CAMERA, CinematicBridgeAscent,
                                     camera_at, camera_signature,
                                     performance_signature)
from cinematic_perspective import CinematicPerspective


class AscentBankTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 640))
        self.addCleanup(pygame.quit)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root/'scene.json'
        self.bank_path = self.root/'environment/manifest.json'
        self.bank_path.parent.mkdir()
        self.players = []
        self.addCleanup(self.close_players)
        for index in range(9):
            Image.new('RGB', (960, 640), (index*20, 40, 60)).save(
                self.bank_path.parent/f'picture_{index}.png')
        digest = sha256((self.bank_path.parent/'picture_0.png').read_bytes()).hexdigest()
        self.profile_paths = {}
        for actor in ACTORS:
            name = actor['id']
            path = self.root/f'characters/{name}/actorperformance.json'
            self.profile_paths[name] = path
            self.write_json(path, {
                'version': 1, 'actor': name, 'source_sha256': {'unused_pose.png': digest},
                'transition_frames': [{'index': index, 'file': 'unused_pose.png',
                                       'cell': [0, 0, 16, 16]} for index in range(133)],
                'overhead_cycle': {'frames': [{'file': 'unused_pose.png'} for _ in range(48)]}})
        guard_path = self.root/'guards/guardperformance.json'
        self.profile_paths['guards'] = guard_path
        self.write_json(guard_path, {
            'version': 1, 'source_sha256': {'unused_pose.png': digest},
            'frozen': [{'source': 'unused_pose.png'} for _ in range(4)],
            'live': {'frames': [{'file': 'unused_pose.png'} for _ in range(16)]}})
        self.scene = {
            'version': 1, 'duration_seconds': 8, 'render_size': [960, 640],
            'camera': deepcopy(CAMERA), 'actors': list(ACTORS), 'baked_characters': True,
            'environment': 'environment/manifest.json',
            'environment_segments': {'normal': 'bridge_ascent',
                                     'reduced_motion': 'bridge_ascent_reduced'},
            'party_performances': {actor['id']: self.profile_paths[actor['id']].relative_to(
                self.root).as_posix() for actor in ACTORS},
            'guard_performance': guard_path.relative_to(self.root).as_posix()}
        self.write_json(self.path, self.scene)
        self.rows = [{'index': index, 'time_seconds': index/60,
                      'camera': camera_at(index/60)} for index in range(481)]
        segment = {'duration_ms': 8000,
                   'frames': [f'picture_{index%9}.png' for index in range(481)],
                   'alarm_frames': ['picture_0.png']*481, 'metadata_path': 'cameras.json'}
        self.bank = {'version': 1, 'width': 960, 'height': 640, 'fps': 60,
                     'baked_characters': True, 'camera_signature': camera_signature(),
                     'performance_signature': performance_signature(self.path, allowed_root=self.root),
                     'segments': {name: deepcopy(segment)
                                  for name in self.scene['environment_segments'].values()}}
        self.write_bank()

    @staticmethod
    def write_json(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, allow_nan=False))

    def write_bank(self, data=None):
        self.write_json(self.bank_path.parent/'cameras.json', self.rows)
        self.write_json(self.bank_path, self.bank if data is None else data)

    def player(self):
        player = CinematicBridgeAscent(self.path, allowed_root=self.root)
        self.players.append(player)
        return player

    def close_players(self):
        for player in self.players:
            player.close()

    def test_real_bank_and_signatures_do_not_eagerly_decode_images(self):
        with patch('pygame.image.load', side_effect=AssertionError('Eager picture decode')):
            signature = performance_signature(self.path, allowed_root=self.root)
            self.assertEqual(signature, self.bank['performance_signature'])
            owner = self.player()
            self.assertIsInstance(owner.environment, CinematicPerspective)
            for reduced in (False, True):
                for seconds in (0., .5, 2.2, 7.999, 8.):
                    state = owner.samples(seconds, reduced)
                    expected = min(480, math.floor(seconds*60+1e-8))
                    self.assertEqual(state['environment']['frame_index'], expected)
                    self.assertEqual(state['environment']['camera'], camera_at(expected/60))
                    self.assertNotIn('blend_frame_index', state['environment'])
            self.assertEqual(owner.cache_info['bytes'], 0)
            self.assertEqual(owner.cache_info['actor_cache']['bytes'], 0)

    def test_real_prefetch_reserves_four_then_eight_slots_and_close_is_reusable(self):
        owner = self.player()
        owner.preload(0., blocking=True, max_slots=4, priority='upcoming')
        self.assertEqual(owner.cache_info['surfaces'], 4)
        self.assertLessEqual(owner.cache_info['bytes'], 4*960*640*4)
        owner.prepare(0.)
        self.assertEqual(owner.cache_info['surfaces'], 8)
        self.assertLessEqual(owner.cache_info['bytes'], owner.cache_info['byte_capacity'])
        owner.close()
        self.assertEqual(owner.cache_info['bytes'], 0)
        owner.prepare(.5)
        self.assertEqual(owner.cache_info['surfaces'], 8)
        owner.close()
        self.assertEqual(owner.cache_info['surfaces'], 0)

    def test_either_camera_segment_rejects_a_loop_despite_481_valid_rows(self):
        for name in self.bank['segments']:
            with self.subTest(segment=name):
                changed = deepcopy(self.bank)
                changed['segments'][name]['loop_ms'] = 1000
                self.write_bank(changed)
                with self.assertRaisesRegex(ValueError, 'must not loop'):
                    self.player()

    def test_either_camera_segment_requires_the_inclusive_endpoint(self):
        for name in self.bank['segments']:
            with self.subTest(segment=name):
                changed = deepcopy(self.bank)
                changed['segments'][name]['frames'].pop()
                changed['segments'][name]['alarm_frames'].pop()
                self.write_bank(changed)
                with self.assertRaisesRegex(ValueError, 'inclusive 60 FPS endpoints'):
                    self.player()

    def test_changed_party_or_guard_png_declaration_invalidates_the_bake(self):
        for name, path in self.profile_paths.items():
            with self.subTest(art=name):
                original = path.read_text()
                changed = json.loads(original)
                changed['source_sha256']['unused_pose.png'] = '0'*64
                self.write_json(path, changed)
                try:
                    with self.assertRaisesRegex(ValueError, 'baked performance is stale'):
                        self.player()
                finally:
                    path.write_text(original)

    def test_changed_declared_crop_invalidates_the_bake(self):
        path = self.profile_paths['iselin']
        changed = json.loads(path.read_text())
        changed['transition_frames'][0]['cell'][0] = 1
        self.write_json(path, changed)
        with self.assertRaisesRegex(ValueError, 'baked performance is stale'):
            self.player()

    def test_post_construction_camera_failure_closes_the_real_environment(self):
        self.rows[60]['camera']['position'][1] += .25
        self.write_bank()
        closed = []
        original_close = CinematicPerspective.close

        def close(environment):
            closed.append(environment)
            original_close(environment)

        with patch.object(CinematicPerspective, 'close', close):
            with self.assertRaisesRegex(ValueError, 'camera differs'):
                self.player()
        self.assertEqual(len(closed), 1)
        self.assertIsInstance(closed[0], CinematicPerspective)
        self.assertEqual(closed[0].cache_info['bytes'], 0)


if __name__ == '__main__':
    unittest.main()
