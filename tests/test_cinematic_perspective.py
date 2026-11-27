"""Inclusive camera samples stay deterministic without retaining a full reel."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

import cinematic_perspective
from cinematic_perspective import CinematicPerspective, RENDER_SIZE


class PerspectiveTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode(RENDER_SIZE)
        self.temp = tempfile.TemporaryDirectory()
        self.players = []
        self.root = Path(self.temp.name)
        self.path = self.root/'manifest.json'
        self.colors = [(8+i, 20+i, 35+i) for i in range(20)]
        for index, color in enumerate(self.colors):
            surface = pygame.Surface(RENDER_SIZE);surface.fill(color)
            pygame.image.save(surface, str(self.root/f'beauty{index}.png'))
        alarm = pygame.Surface(RENDER_SIZE, pygame.SRCALPHA)
        alarm.fill((255, 255, 255, 0))
        pygame.draw.rect(alarm, (190, 0, 0, 255), (30, 30, 20, 20))
        pygame.image.save(alarm, str(self.root/'alarm.png'))
        def segment(count, duration, loop=None):
            result = {'duration_ms':duration,
                'frames':[f'beauty{i%20}.png' for i in range(count)],
                'alarm_frames':['alarm.png']*count}
            if loop is not None:result['loop_ms'] = loop
            return result
        self.data = {'version':1, 'width':960, 'height':640, 'fps':60,
            'segments':{'orbit':segment(301, 5000),
                        'alarm_hold':segment(16, 4000, 2000),
                        'rush':segment(61, 1000),
                        'reveal':segment(16, 4000, 2000)}}
        self.write()

    def tearDown(self):
        for player in self.players:player.close()
        self.temp.cleanup();pygame.quit()

    def write(self):
        self.path.write_text(json.dumps(self.data))

    def player(self, **kwargs):
        player = CinematicPerspective(self.path, allowed_root=self.root, **kwargs)
        self.players.append(player)
        return player

    def test_301_orbit_and_61_rush_samples_have_exact_endpoint_times(self):
        reel = self.player()
        for segment, count, duration in [('orbit', 301, 5.), ('rush', 61, 1.)]:
            self.assertEqual(reel.samples(segment, 0)['frame_index'], 0)
            self.assertEqual(reel.samples(segment, duration-1/60)['frame_index'], count-2)
            self.assertEqual(reel.samples(segment, duration)['frame_index'], count-1)
            self.assertEqual(reel.samples(segment, duration+1)['frame_index'], count-1)
            thirty_hz = [reel.samples(segment, i/30)['frame_index'] for i in range(round(duration*30))]
            self.assertEqual(thirty_hz, list(range(0, count-1, 2)))
        self.assertTrue(reel.validate_segment('orbit', 5))
        self.assertTrue(reel.validate_segment('alarm_hold', 4))
        with self.assertRaises(ValueError):reel.validate_segment('orbit', 301/60)

    def test_sampling_and_backward_seeks_do_not_decode_or_read_any_files(self):
        reel = self.player()
        with patch('pygame.image.load', side_effect=AssertionError('Unexpected decode')):
            with patch.object(Path, 'open', side_effect=AssertionError('Unexpected I/O')):
                expected = reel.samples('orbit', 4.25)
                reel.samples('orbit', 1)
                self.assertEqual(reel.samples('orbit', 4.25), expected)
        self.assertEqual(reel.cache_info['surfaces'], 0)

    def test_decoded_cache_is_bounded_and_close_is_reusable(self):
        reel = self.player(cache_size=8)
        target = pygame.Surface(RENDER_SIZE)
        for index in range(35):
            reel.draw(target, reel.samples('orbit', index/60), alarm_active=True,
                      alarm_elapsed=index/60)
            self.assertLessEqual(reel.cache_info['surfaces'], 8)
            self.assertLessEqual(reel.cache_info['bytes'], 8*960*640*4)
        misses = reel.cache_info['decodes']
        state = reel.samples('orbit', 34/60)
        reel.draw(target, state, alarm_active=True)
        self.assertEqual(reel.cache_info['decodes'], misses)
        reel.close()
        self.assertEqual(reel.cache_info['surfaces'], 0)
        self.assertEqual(reel.cache_info['bytes'], 0)
        reel.draw(target, state)
        self.assertGreater(reel.cache_info['decodes'], misses)

    def test_pending_decodes_share_the_cache_bound_and_close_drains_the_worker(self):
        reel = self.player(cache_size=8)
        entered, release = threading.Event(), threading.Event()
        decode = cinematic_perspective._decode_png
        def delayed(path):
            entered.set()
            if not release.wait(3):raise AssertionError('Decoder was not released')
            return decode(path)
        try:
            with patch('cinematic_perspective._decode_png', side_effect=delayed):
                reel.preload('orbit', 0., max_slots=8)
                self.assertTrue(entered.wait(1))
                # Replace the upcoming window while the first decode is still
                # running. Its memory reservation must remain visible.
                reel.preload('orbit', .2, max_slots=8)
                info = reel.cache_info
                self.assertEqual(info['surfaces'], 8)
                self.assertEqual(info['pending_surfaces'], 8)
                self.assertLessEqual(info['bytes'], 8*960*640*4)
                self.assertTrue(any(key[0].name == 'beauty0.png' for key in reel._cache))
                release.set();reel.close()
                self.assertIsNone(reel._executor)
                self.assertEqual(reel.cache_info['surfaces'], 0)
                self.assertEqual(reel.cache_info['pending_bytes'], 0)
        finally:release.set()

    def test_standalone_warmup_decodes_a_ready_window_before_playback(self):
        reel = self.player()
        threads = []
        decode = cinematic_perspective._decode_png
        def record_thread(path):
            threads.append(threading.get_ident())
            return decode(path)
        with patch('cinematic_perspective._decode_png', side_effect=record_thread):
            reel.preload('orbit', 0., blocking=True)
        self.assertEqual(reel.cache_info['decoded_surfaces'], 16)
        self.assertEqual(reel.cache_info['pending_surfaces'], 0)
        self.assertTrue(threads)
        self.assertNotIn(threading.get_ident(), threads)

    def test_advancing_active_window_keeps_upcoming_start_ready_without_decode_thrash(self):
        for index in range(4):
            shutil.copyfile(self.root/f'beauty{index}.png', self.root/f'next{index}.png')
            shutil.copyfile(self.root/'alarm.png', self.root/f'next_alarm{index}.png')
        rush = self.data['segments']['rush']
        rush['frames'] = [f'next{i%4}.png' for i in range(61)]
        rush['alarm_frames'] = [f'next_alarm{i%4}.png' for i in range(61)]
        self.write();reel = self.player()
        reel.preload('orbit', 0., blocking=True)
        reel.preload('rush', 0., alarm_active=True, priority='upcoming', max_slots=8, blocking=True)
        target = pygame.Surface(RENDER_SIZE)
        reel.draw(target, reel.samples('orbit', 0.))
        before = reel.cache_info['decodes']
        reel.preload('orbit', 1/60)
        reel.preload('rush', 0., alarm_active=True, priority='upcoming', max_slots=8)
        # Only the newly upcoming orbit image needs decoding; the bridge's
        # ready frame-zero window survives the active shot advancing.
        self.assertEqual(reel.cache_info['decodes']-before, 1)
        self.assertEqual(reel.cache_info['surfaces'], 24)
        for index in range(4):
            for name, alarm in ((f'next{index}.png', False), (f'next_alarm{index}.png', True)):
                self.assertIn((self.root/name, alarm), reel._cache)

    def test_alert_is_explicit_phase_locked_and_respects_transparent_occlusion(self):
        reel = self.player()
        target = pygame.Surface(RENDER_SIZE)
        state = reel.samples('alarm_hold', 0)
        reel.draw(target, state)
        self.assertEqual(target.get_at((35, 35))[:3], self.colors[0])
        reel.draw(target, state, alarm_active=True, alarm_elapsed=0)
        bright = target.get_at((35, 35)).r
        self.assertGreater(bright, self.colors[0][0]+150)
        # Hidden RGB behind a transparent pixel cannot become additive white.
        self.assertEqual(target.get_at((5, 5))[:3], self.colors[0])
        reel.draw(target, state, alarm_active=True, alarm_elapsed=.9)
        self.assertLess(target.get_at((35, 35)).r, bright-100)
        reel.draw(target, state, alarm_active=True, alarm_elapsed=2.)
        self.assertEqual(target.get_at((35, 35)).r, bright)

    def test_hold_loops_and_reduced_motion_uses_calm_endpoint_views(self):
        reel = self.player()
        self.assertEqual(reel.samples('reveal', .125)['frame_index'], 1)
        self.assertEqual(reel.samples('reveal', 2.125)['frame_index'], 1)
        self.assertEqual(reel.samples('reveal', 4)['frame_index'], 0)
        for seconds in (0., .5, 3.):
            self.assertEqual(reel.samples('reveal', seconds, True)['frame_index'], 0)
        rush = reel.samples('rush', .5, True)
        self.assertEqual((rush['frame_index'], rush['blend_frame_index'], rush['blend']), (0, 60, .5))
        self.assertEqual(reel.samples('rush', 1., True)['frame_index'], 60)
        self.assertEqual(reel.alarm_strength(0, True), reel.alarm_strength(1, True))

    def test_fixed_camera_hold_blends_smoothly_across_frames_and_loop_seam(self):
        camera = {'position':[0, 0, 10], 'target':[0, 1, 0], 'up':[0, 0, 1], 'fov_degrees':55}
        metadata = [{'index':i, 'time_seconds':i/8, 'camera':camera} for i in range(16)]
        (self.root/'hold_camera.json').write_text(json.dumps(metadata))
        self.data['segments']['alarm_hold']['metadata_path'] = 'hold_camera.json';self.write()
        reel = self.player()
        midway = reel.samples('alarm_hold', .0625)
        self.assertEqual((midway['frame_index'], midway['blend_frame_index'], midway['blend']), (0, 1, .5))
        target = pygame.Surface(RENDER_SIZE)
        for boundary in (.125, 2.):
            pixels = []
            for seconds in (boundary-1e-5, boundary, boundary+1e-5):
                state = reel.samples('alarm_hold', seconds)
                self.assertEqual(state['camera'], camera)
                reel.draw(target, state)
                pixels.append(target.get_at((5, 5))[:3])
            self.assertLessEqual(max(p[0] for p in pixels)-min(p[0] for p in pixels), 1)
        # Moving-camera sequences retain all their authored 60 Hz samples.
        orbit = reel.samples('orbit', .0625)
        self.assertNotIn('blend_frame_index', orbit)

    def test_camera_metadata_is_validated_and_returned_without_shared_mutation(self):
        camera = {'position':[0, 0, 10], 'target':[0, 1, 0], 'up':[0, 0, 1], 'fov_degrees':55}
        metadata = [{'index':i, 'time_seconds':i/60, 'camera':deepcopy(camera),
                     'landmarks':{'gate':[200, 300, 100]}} for i in range(301)]
        (self.root/'camera.json').write_text(json.dumps(metadata))
        self.data['segments']['orbit']['metadata_path'] = 'camera.json';self.write()
        reel = self.player()
        sample = reel.samples('orbit', 1)
        self.assertEqual(sample['camera'], camera)
        sample['camera']['position'][0] = 999
        self.assertEqual(reel.samples('orbit', 1)['camera'], camera)
        metadata[4]['camera']['position'][0] = float('nan')
        (self.root/'camera.json').write_text(json.dumps(metadata))
        with self.assertRaises(ValueError):self.player()

    def test_missing_corrupt_wrong_size_and_escaped_images_fail_validation(self):
        original = deepcopy(self.data)
        for filename in ('missing.png', '../outside.png'):
            self.data = deepcopy(original)
            self.data['segments']['orbit']['frames'][0] = filename;self.write()
            with self.assertRaises(ValueError):self.player()
        self.data = deepcopy(original);self.write()
        filename = self.root/'beauty0.png'
        intact = filename.read_bytes()
        corrupt = bytearray(intact);corrupt[len(corrupt)//2] ^= 1
        filename.write_bytes(corrupt)
        with self.assertRaises(ValueError):self.player()
        pygame.image.save(pygame.Surface((20, 20)), str(filename))
        with self.assertRaises(ValueError):self.player()

    def test_invalid_counts_clocks_and_manifest_values_are_rejected(self):
        original = deepcopy(self.data)
        for change in ('short', 'nonfinite', 'fps', 'alarm_count'):
            self.data = deepcopy(original)
            if change == 'short':self.data['segments']['orbit']['frames'].pop()
            elif change == 'nonfinite':self.data['segments']['orbit']['duration_ms'] = float('inf')
            elif change == 'fps':self.data['fps'] = 30
            else:self.data['segments']['orbit']['alarm_frames'].pop()
            self.write()
            with self.assertRaises(ValueError):self.player()
        self.data = original;self.write();reel = self.player()
        for value in (-1, float('nan'), float('inf'), True, '1'):
            with self.assertRaises(ValueError):reel.samples('orbit', value)
        with self.assertRaises(ValueError):reel.samples('absent', 0)


if __name__ == '__main__':unittest.main()
