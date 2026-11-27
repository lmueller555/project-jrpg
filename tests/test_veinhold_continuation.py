"""Production reel timing, shared effects and isolated later-shot playback."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from fire_veinhold_opening import ROOT, SCENE, FireVeinholdOpening, available_shots, sequence_duration


class VeinholdContinuationTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 640))
        self.game = SimpleNamespace(audio=SimpleNamespace(reduced_motion=False, effects_volume=0),
                                    _music_focused=True, to_canvas=lambda point:point)
        self.scene = FireVeinholdOpening(self.game)
        self.addCleanup(self.scene.reset)

    def tearDown(self):
        self.scene.reset()
        pygame.quit()

    def test_reel_is_47_seconds_with_four_seconds_of_warning_before_the_rush(self):
        self.assertEqual(sequence_duration(), 47.)
        expected = ((25., 'island_orbit', 'orbit', False),
                    (30., 'alarm_hold', 'alarm_hold', True),
                    (34., 'bridge_rush', 'rush', True),
                    (35., 'frozen_bridge', 'reveal', True),
                    (39., 'bridge_running', 'bridge_running', True),
                    (42., 'face_reveal', 'face_reveal', True))
        for time, identifier, phase, alarm in expected:
            with self.subTest(time=time):
                state = self.scene.state_at(time)
                self.assertEqual(state['shot_id'], identifier)
                self.assertEqual(state['phase'], phase)
                self.assertEqual(state['local_time'], 0.)
                self.assertEqual(state['global_time'], time)
                self.assertEqual(state['alarm']['active'], alarm)
                self.assertNotIn('eagle', state)
        self.assertEqual(self.scene.state_at(34.)['alarm']['elapsed'], 4.)
        self.assertFalse(self.scene.state_at(30.-1e-6)['alarm']['active'])

    def test_orbit_and_rush_have_inclusive_endpoints_and_shared_camera_joins(self):
        self.scene._load()
        art = self.scene._assets['island_orbit']['perspective']
        self.assertEqual(len(art.segments['orbit']['frames']), 301)
        self.assertEqual(len(art.segments['rush']['frames']), 61)
        for segment, end, following in (('orbit', 5., 'alarm_hold'),
                                        ('alarm_hold', 4., 'rush'),
                                        ('rush', 1., 'reveal')):
            with self.subTest(segment=segment):
                a = art.samples(segment, end)['camera']
                b = art.samples(following, 0.)['camera']
                self.assertEqual(a, b)
        self.assertEqual(art.samples('orbit', 5.)['frame_index'], 300)
        self.assertEqual(art.samples('rush', 1.)['frame_index'], 60)

    def test_camera_reverses_and_finishes_twenty_feet_onto_the_merovar_bridge(self):
        source = ROOT/'assets/source/cinematics/fire_veinhold/continuation/scene_config.json'
        config = json.loads(source.read_text())
        cameras = json.loads((SCENE.parent/'continuation/orbit/cameras.json').read_text())
        initial = pygame.Vector2(cameras[0]['camera']['position'][:2])
        reverse = pygame.Vector2(cameras[-1]['camera']['position'][:2])
        self.assertAlmostEqual(abs(initial.angle_to(reverse)), 180., places=4)
        bridge = next(item for item in config['bridges'] if item['name'] == 'Merovar bridge')
        landing, gate = map(pygame.Vector3, (bridge['start'], bridge['end']))
        axis = (gate-landing).normalize()
        endpoint = json.loads((SCENE.parent/'continuation/reveal/cameras.json').read_text())[0]['camera']
        camera, target = map(pygame.Vector3, (endpoint['position'], endpoint['target']))
        self.assertAlmostEqual((camera-landing).dot(axis), 6.096, places=4)
        self.assertLess((target-camera).normalize().dot(axis), -.9)
        self.assertEqual(len(config['guards']), 4)
        for guard in config['guards']:
            self.assertGreater((pygame.Vector3(guard['position'])-camera).dot(target-camera), 0.)

    def test_rendered_beauty_endpoints_match_across_each_new_shot_join(self):
        self.scene._load()
        reel = self.scene._assets['island_orbit']['perspective']
        for before, after in (('orbit', 'alarm_hold'), ('alarm_hold', 'rush'), ('rush', 'reveal')):
            with self.subTest(join=(before, after)):
                a = reel.segments[before]
                end = a['frames'][0] if a['loop'] else a['frames'][-1]
                start = reel.segments[after]['frames'][0]
                first, second = pygame.image.load(str(end)), pygame.image.load(str(start))
                self.assertEqual(pygame.image.tobytes(first, 'RGB'), pygame.image.tobytes(second, 'RGB'))

    def test_each_standalone_clip_matches_its_complete_reel_state_and_pixels(self):
        offset = 0.
        for shot in available_shots():
            if shot['type'] != 'perspective_sequence':
                offset += shot['duration']
                continue
            with self.subTest(shot=shot['id']):
                clip = FireVeinholdOpening(self.game, shot['id'])
                self.addCleanup(clip.reset)
                local = min(.25, shot['duration']/2)
                self.assertEqual(clip.global_offset, offset)
                self.assertEqual(clip.state_at(local), self.scene.state_at(offset+local))
                self.assertEqual(pygame.image.tobytes(clip.render_frame(local), 'RGB'),
                                 pygame.image.tobytes(self.scene.render_frame(offset+local), 'RGB'))
                clip.reset()
            offset += shot['duration']

    def test_the_first_shot_keeps_amber_power_but_has_no_active_red_warning(self):
        for time in (0., 15., 20., 24.99):
            state = self.scene.state_at(time)
            self.assertEqual(state['facility']['beacons'], [])
            self.assertTrue(state['facility']['conduits'])
            self.assertTrue(state['facility']['embers'])

    def test_sampling_a_loaded_reel_does_not_decode_images_or_change_time(self):
        self.scene._load()
        before = self.scene.elapsed
        with patch('pygame.image.load', side_effect=AssertionError('Sampling performed image I/O')):
            for time in (25., 25.17, 29.99, 30., 33.9, 34.5, 35., 38.9, 39., 42., 43.5, 46.9):
                self.assertEqual(self.scene.state_at(time), self.scene.state_at(time))
        self.assertEqual(self.scene.elapsed, before)

    def test_rush_streaks_are_deterministic_and_clear_before_the_guard_reveal(self):
        base = pygame.Surface((960, 640))
        base.fill('#14293a')
        pygame.draw.rect(base, '#a4c7d2', (80, 90, 130, 170))
        original = pygame.image.tobytes(base, 'RGB')
        for seconds in (0., .88, 1.):
            target = base.copy()
            self.scene._bridge_motion(target, seconds)
            self.assertEqual(pygame.image.tobytes(target, 'RGB'), original)
        a, b = base.copy(), base.copy()
        self.scene._bridge_motion(a, .44)
        self.scene._bridge_motion(b, .44)
        self.assertEqual(pygame.image.tobytes(a, 'RGB'), pygame.image.tobytes(b, 'RGB'))
        self.assertNotEqual(pygame.image.tobytes(a, 'RGB'), original)

    def test_pause_and_focus_loss_freeze_the_whole_continuation_then_restart_cleans_up(self):
        self.scene.start()
        self.scene.update(31.)
        before = deepcopy(self.scene.state_at(self.scene.elapsed))
        escape = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False)
        self.scene.handle_event(escape)
        self.scene.update(2.)
        self.assertEqual(self.scene.state_at(self.scene.elapsed), before)
        self.scene.handle_event(escape)
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.scene.update(2.)
        self.assertEqual(self.scene.state_at(self.scene.elapsed), before)
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.scene.update(.25)
        self.assertEqual(self.scene.elapsed, 31.25)
        perspective = self.scene._assets['island_orbit']['perspective']
        self.assertGreater(perspective.cache_info['surfaces'], 0)
        self.scene.reset()
        self.assertEqual(perspective.cache_info['surfaces'], 0)
        self.assertFalse(self.scene.alert_audio.voices)
        self.assertFalse(self.scene.flight_audio.voices)
        self.scene.start()
        self.assertEqual(self.scene.elapsed, 0.)

    def test_shot_boundaries_do_not_rearm_eagle_cues_and_completion_fires_once(self):
        calls = []
        self.scene.start(lambda:calls.append('complete'))
        with patch.object(self.scene.flight_audio, 'begin_shot',
                          side_effect=AssertionError('Rearmed eagle cues during the continuation')):
            for time in (24.9, 25., 29.9, 30., 33.9, 34., 34.9, 35., 38.99):
                self.scene.update(time-self.scene.elapsed)
                self.assertTrue(self.scene.active)
            self.scene.update(.01)
            self.assertEqual(self.scene.elapsed, 39.)
            self.assertTrue(self.scene.active)
            self.scene.update(3.)
            self.assertEqual(self.scene.elapsed, 42.)
            self.assertTrue(self.scene.active)
            self.scene.update(5.)
        self.assertEqual(self.scene.elapsed, 47.)
        self.assertFalse(self.scene.active)
        self.scene.skip()
        self.scene.update(10.)
        self.assertEqual(calls, ['complete'])
        self.assertFalse(self.scene.alert_audio.voices)

    def test_regular_sixty_hz_updates_show_each_exact_first_frame_without_clock_drift(self):
        self.scene.start()
        boundaries = {1500:('island_orbit', 25.), 1800:('alarm_hold', 30.),
                      2040:('bridge_rush', 34.), 2100:('frozen_bridge', 35.),
                      2340:('bridge_running', 39.), 2520:('face_reveal', 42.)}
        # Frame selection and effects use production metadata. Skip image
        # warming here so this clock test does not benchmark the filesystem.
        with patch.object(self.scene, '_preload_at'):
            for frame in range(1, 2821):
                self.scene.update(1/60)
                if frame in boundaries:
                    identifier, time = boundaries[frame]
                    state = self.scene.state_at(self.scene.elapsed)
                    self.assertEqual(self.scene.elapsed, time)
                    self.assertEqual(state['shot_id'], identifier)
                    self.assertEqual(state['local_time'], 0.)
                    if 'perspective' in state:
                        self.assertEqual(state['perspective']['frame_index'], 0)
                    else:
                        self.assertEqual(state['runners'][0]['frame_index'],
                                         12 if identifier == 'face_reveal' else 0)
        self.assertFalse(self.scene.active)
        self.assertEqual(self.scene.elapsed, 47.)

    def test_standalone_end_does_not_sound_the_following_shots_first_cue(self):
        self.game.audio.effects_volume = .5
        for identifier, unwanted in (('island_orbit', 'industrial_siren.wav'),
                                    ('alarm_hold', 'bridge_rush.wav'),
                                    ('bridge_rush', 'ice_settle.wav')):
            with self.subTest(shot=identifier):
                clip = FireVeinholdOpening(self.game, identifier)
                self.addCleanup(clip.reset)
                clip.start()
                clip.update(clip.duration-.05)
                clip.update(.05)
                self.assertFalse(clip.active)
                self.assertNotIn(unwanted, [event['id'] for event in clip.alert_audio.events])
                self.assertFalse(clip.alert_audio.voices)

    def test_perspective_shots_share_one_bounded_cache(self):
        self.scene._load()
        players = [art['perspective'] for art in self.scene._assets.values() if 'perspective' in art]
        self.assertEqual(len({id(player) for player in players}), 1)
        player = players[0]
        for time in (25., 26., 27., 28., 29., 30., 30.5, 31., 32., 33., 34., 34.5, 35., 36., 37.):
            self.scene.render_frame(time)
            self.assertLessEqual(player.cache_info['surfaces'], player.cache_info['capacity'])
            self.assertLessEqual(player.cache_info['bytes'], player.cache_info['capacity']*960*640*4)
        self.scene.skip()
        self.scene.reset()
        self.assertEqual(player.cache_info['surfaces'], 0)

    def test_application_exit_closes_gallery_decoders_before_quitting_pygame(self):
        from main import Game, main
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            game = Game(window_size=(960, 640), fullscreen=False,
                        save_path=directory/'journey.json', settings_path=directory/'settings.json')
            game.audio.set_effects(0)
            persisted = {path.name:path.read_bytes() for path in directory.glob('*.json')}
            self.assertTrue(game.open_gallery())
            self.assertTrue(game.launch_gallery_scene('fire_veinhold_shot_02'))
            session = game.gallery_session
            scene = session.game.cinematic
            perspective = scene._assets['island_orbit']['perspective']
            self.assertGreater(perspective.cache_info['surfaces'], 0)
            pygame.event.clear()
            with patch('main.Game', return_value=game), \
                    patch.object(game, 'update', wraps=game.update) as update:
                main(['--headless', '--frames', '1'])
            self.assertEqual(update.call_args.args[0], 0.)
            self.assertTrue(session.closed)
            self.assertFalse(scene.active)
            self.assertIsNone(perspective._executor)
            self.assertEqual(perspective.cache_info['surfaces'], 0)
            self.assertFalse(scene.alert_audio.voices)
            self.assertEqual({path.name:path.read_bytes() for path in directory.glob('*.json')}, persisted)


if __name__ == '__main__':
    unittest.main()
