"""First-shot timing, native rendering and disposable Gallery playback.

The eagle shot is a standalone presentation review. Its Gallery fixtures do
not replace the current playable morning or grant prologue story progress.
"""
from copy import deepcopy
import gc
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from fire_veinhold_opening import (FireVeinholdOpening, SCENE,
                                  available_shots, sequence_duration)
from dense_art import WorldCanvas
from ui_style import UIStyle


class FireVeinholdOpeningTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 640))
        self.game = SimpleNamespace(
            audio=SimpleNamespace(reduced_motion=False, effects_volume=0,
                                  music_volume=0, text_scale=1),
            _music_focused=True, _is_gallery_preview=True,
            to_canvas=lambda point: point)
        self.game.ui = UIStyle(self.game)
        self.scene = FireVeinholdOpening(self.game, shot_id='eagle_ascent')

    def tearDown(self):
        self.scene.reset()
        pygame.quit()

    def test_summit_is_cleared_at_fifteen_with_ten_full_seconds_of_vista(self):
        self.scene.start()
        self.scene.update(15.-1e-6)
        self.assertEqual(self.scene.state_at(self.scene.elapsed)['phase'], 'ascent')
        self.scene.update(1e-6)
        crest = self.scene.state_at(self.scene.elapsed)
        self.assertEqual(crest['phase'], 'cinder_vista')
        self.assertEqual(crest['vista_elapsed'], 0.)
        image = self.scene._assets['eagle_ascent']['layers']['panorama']
        record = crest['layers']['panorama']
        scale = max(960/image.get_width(), 640/image.get_height())*record['scale']
        # The source window has passed the approach and exposes the authored
        # upper vista (volcano around sourcey260, coast starts belowy530).
        top = (640-image.get_height()*scale)/2+record['offset'][1]
        self.assertAlmostEqual(top, 0., delta=1.)
        self.assertLess(530*scale, 640)
        self.scene.update(10.-1e-6)
        self.assertTrue(self.scene.active)
        self.assertAlmostEqual(self.scene.state_at(self.scene.elapsed)['vista_elapsed'], 10., places=5)
        self.scene.update(1e-6)
        self.assertFalse(self.scene.active)

    def test_climb_starts_higher_and_flies_faster_than_the_previous_approach(self):
        state = self.scene.state_at(0.)
        self.assertGreater(state['camera']['position'][2], 110.)
        self.assertGreater(state['camera']['velocity'][1], 22.)
        self.assertEqual(self.scene.state_at(15.)['eagle']['scale'], 1.)
        self.assertLess(self.scene.state_at(25.)['eagle']['scale'], .5)

    def test_terrain_is_one_opaque_panorama_with_one_shared_transform(self):
        self.scene.start()
        self.assertEqual(set(self.scene._assets['eagle_ascent']['layers']), {'panorama'})
        panorama = self.scene._assets['eagle_ascent']['layers']['panorama']
        self.assertEqual(pygame.mask.from_surface(panorama).count(),
                         panorama.get_width()*panorama.get_height())
        for time in (0., 2., 5., 8., 10.):
            self.assertEqual(set(self.scene.state_at(time)['layers']), {'panorama'})

    def test_single_shot_finishes_at_twenty_five_seconds_for_both_frame_rates(self):
        self.assertEqual(self.scene.duration, 25.)
        for fps in (30, 60):
            with self.subTest(fps=fps):
                calls = []
                self.scene.start(lambda: calls.append('finished'))
                for _ in range(fps*25-1):
                    self.scene.update(1/fps)
                self.assertTrue(self.scene.active)
                self.assertEqual(calls, [])
                self.scene.update(1/fps)
                self.assertFalse(self.scene.active)
                self.assertEqual(self.scene.elapsed, 25.)
                self.assertEqual(calls, ['finished'])
                self.scene.update(25.)
                self.scene.skip()
                self.assertEqual(calls, ['finished'])

    def test_genuinely_before_boundary_remains_active(self):
        calls = []
        self.scene.start(lambda: calls.append('finished'))
        self.scene.update(25.-1e-6)
        self.assertTrue(self.scene.active)
        self.assertEqual(calls, [])
        self.scene.update(1e-6)
        self.assertFalse(self.scene.active)
        self.assertEqual(self.scene.elapsed, 25.)
        self.assertEqual(calls, ['finished'])

    def test_pause_focus_and_host_focus_freeze_the_whole_shot_clock(self):
        self.scene.start()
        self.scene.update(2.35)
        before = self.scene.state_at(self.scene.elapsed)
        escape = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False)
        self.scene.handle_event(escape)
        self.scene.update(.5)
        self.assertEqual(self.scene.state_at(self.scene.elapsed), before)
        self.scene.handle_event(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=True))
        self.scene.update(.5)
        self.assertEqual(self.scene.state_at(self.scene.elapsed), before)
        self.scene.handle_event(escape)
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.scene.update(.5)
        self.assertEqual(self.scene.state_at(self.scene.elapsed), before)
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.game._music_focused = False
        self.scene.update(.5)
        self.assertEqual(self.scene.state_at(self.scene.elapsed), before)
        self.game._music_focused = True
        self.scene.update(.1)
        self.assertAlmostEqual(self.scene.elapsed, 2.45)
        self.assertNotEqual(self.scene.state_at(self.scene.elapsed)['eagle'], before['eagle'])

    def test_reset_discards_callback_and_a_restarted_skip_completes_once(self):
        calls = []
        self.scene.start(lambda: calls.append('discarded'))
        self.scene.update(3.)
        self.scene.reset()
        self.assertFalse(self.scene.active)
        self.assertEqual(self.scene.elapsed, 0.)
        self.scene.skip()
        self.assertEqual(calls, [])
        self.scene.start(lambda: calls.append('second'))
        self.scene.update(.4)
        self.scene.skip()
        self.scene.skip()
        self.scene.update(25.)
        self.assertFalse(self.scene.active)
        self.assertEqual(calls, ['second'])

    def test_endpoint_retains_camera_velocity_wing_phase_and_audio_handoff(self):
        end = self.scene.state_at(25.)
        just_before = self.scene.state_at(25.-1e-4)
        velocity = end['camera']['velocity']
        self.assertGreater(math.dist(velocity, [0, 0, 0]), .01)
        difference = [(last-first)/1e-4 for first, last in zip(
            just_before['camera']['position'], end['camera']['position'])]
        for measured, authored in zip(difference, velocity):
            self.assertAlmostEqual(measured, authored,
                                   delta=max(.03, abs(authored)*.01))
        self.assertLess(abs(end['eagle']['wing_phase']-
                            just_before['eagle']['wing_phase']), .01)
        self.scene.start()
        self.scene.update(25.)
        handoff = self.scene.handoff_state
        self.assertEqual(handoff['camera'], end['camera'])
        self.assertEqual(handoff['eagle'], end['eagle'])
        self.assertEqual(handoff['audio']['wind_playhead'], 25.)
        self.assertTrue(handoff['audio']['wind_continues'])

    def test_reduced_motion_preserves_authored_flight_and_wing_locomotion(self):
        times = (0., .13, .31, .57, .86, 1.2, 3.1, 6.4, 9.98)
        normal = [self.scene.state_at(time)['eagle'] for time in times]
        self.game.audio.reduced_motion = True
        reduced = [self.scene.state_at(time)['eagle'] for time in times]
        for ordinary, comfort in zip(normal, reduced):
            for key in ('sequence', 'frame', 'wing_phase', 'anchor'):
                self.assertEqual(comfort[key], ordinary[key], key)
        self.assertGreater(len({(state['sequence'], state['frame'])
                                for state in reduced}), 1)
        self.assertGreater(len({state['wing_phase'] for state in reduced}), 1)

    def test_native_render_is_drawn_to_ui_without_losing_detail_or_advancing_time(self):
        self.assertEqual(self.scene.render_size, (960, 640))
        self.scene.start()
        self.scene.update(2.35)
        before = (self.scene.elapsed, deepcopy(self.scene.state_at(self.scene.elapsed)))
        native = self.scene.render_frame()
        self.assertEqual(native.get_size(), (960, 640))
        self.assertEqual(pygame.image.tobytes(native, 'RGB'), pygame.image.tobytes(
            self.scene.render_frame(2.35), 'RGB'))
        logical = WorldCanvas((480, 320))
        ui_surface = pygame.Surface((960, 640))
        self.scene.draw(logical, ui_surface)
        # Controls occupy the bottom. This scene area must retain native pixels
        # even though Game's cinematic branch bypasses present_detail().
        scene_area = pygame.Rect(0, 0, 960, 520)
        native_pixels = pygame.image.tobytes(native.subsurface(scene_area), 'RGB')
        self.assertEqual(pygame.image.tobytes(
            ui_surface.subsurface(scene_area), 'RGB'), native_pixels)
        enlarged_logical = pygame.transform.scale(logical, (960, 640))
        self.assertNotEqual(pygame.image.tobytes(
            enlarged_logical.subsurface(scene_area), 'RGB'), native_pixels)
        self.assertEqual(before, (self.scene.elapsed,
                                 self.scene.state_at(self.scene.elapsed)))

    def test_final_frame_stays_visible_without_an_end_fade(self):
        before = self.scene.render_frame(24.99)
        end = self.scene.render_frame(25.)
        before_light = sum(pygame.image.tobytes(before, 'RGB'))
        end_light = sum(pygame.image.tobytes(end, 'RGB'))
        self.assertGreater(before_light, 0)
        self.assertGreater(end_light, before_light*.9)

    def test_catalogue_and_complete_sequence_follow_appended_authored_order(self):
        with tempfile.TemporaryDirectory(prefix='prologue-appended-shot-') as folder:
            destination = Path(folder)/'scene'
            shutil.copytree(SCENE.parent, destination)
            path = destination/'scene.json'
            data = json.loads(path.read_text())
            first = deepcopy(data['shots'][0])
            appended = deepcopy(first)
            appended.update(id='fixture_second_ascent',
                            gallery_id='fixture_second_gallery',
                            name='Second ascent fixture')
            data['shots'] = [first, appended]
            path.write_text(json.dumps(data))
            self.assertEqual([shot['id'] for shot in available_shots(path)],
                             [first['id'], appended['id']])
            self.assertEqual(sequence_duration(path), first['duration']*2)
            returned = available_shots(path)
            returned.reverse()
            returned[0]['duration'] = 999
            self.assertEqual(sequence_duration(path), first['duration']*2)
            sequence = FireVeinholdOpening(self.game, scene_path=path)
            self.addCleanup(sequence.reset)
            calls = []
            sequence.start(lambda: calls.append('complete'))
            sequence.update(first['duration']-1e-4)
            self.assertEqual(sequence.state_at(sequence.elapsed)['shot_id'], first['id'])
            sequence.update(1e-4)
            state = sequence.state_at(sequence.elapsed)
            self.assertEqual(state['shot_id'], appended['id'])
            self.assertEqual(state['local_time'], 0.)
            self.assertTrue(sequence.active)
            self.assertEqual(calls, [])
            sequence.update(appended['duration'])
            self.assertFalse(sequence.active)
            self.assertEqual(calls, ['complete'])
            individual = FireVeinholdOpening(self.game, shot_id=appended['id'],
                                             scene_path=path)
            self.addCleanup(individual.reset)
            self.assertEqual(individual.duration, appended['duration'])
            self.assertEqual(individual.state_at(0)['shot_id'], appended['id'])

    def test_invalid_scene_duration_shot_identity_and_render_metadata_fail_closed(self):
        source = json.loads(SCENE.read_text())
        cases = []
        for duration in (0, -1, float('nan'), float('inf'), True):
            invalid = deepcopy(source)
            invalid['shots'][0]['duration'] = duration
            cases.append((f'duration {duration}', invalid))
        for ascent, vista in ((0, 25), ('bad', 10), (15, 5), (float('nan'), 10)):
            invalid = deepcopy(source)
            invalid['shots'][0].update(ascent_duration=ascent, vista_duration=vista)
            cases.append(('invalid phase lengths', invalid))
        for field, value in (('shots', []), ('render_size', [480, 320]),
                             ('logical_size', [960, 640])):
            invalid = deepcopy(source)
            invalid[field] = value
            cases.append((field, invalid))
        for duplicate in ('id', 'gallery_id'):
            invalid = deepcopy(source)
            second = deepcopy(invalid['shots'][0])
            second.update(id='second_fixture', gallery_id='second_fixture_gallery')
            second[duplicate] = invalid['shots'][0][duplicate]
            invalid['shots'].append(second)
            cases.append((f'duplicate {duplicate}', invalid))
        invalid = deepcopy(source)
        invalid['shots'][0]['type'] = 'unimplemented_fixture'
        cases.append(('unknown shot type', invalid))
        with tempfile.TemporaryDirectory(prefix='prologue-invalid-scene-') as folder:
            path = Path(folder)/'scene.json'
            for label, invalid in cases:
                with self.subTest(case=label):
                    path.write_text(json.dumps(invalid))
                    with self.assertRaises(ValueError):
                        available_shots(path)
                    with self.assertRaises(ValueError):
                        FireVeinholdOpening(self.game, scene_path=path)
        with self.assertRaises(ValueError):
            FireVeinholdOpening(self.game, shot_id='unimplemented_fixture')

    def test_asset_references_are_confined_to_the_scene_directory(self):
        source = json.loads(SCENE.read_text())
        with tempfile.TemporaryDirectory(prefix='prologue-invalid-route-') as folder:
            path = Path(folder)/'scene.json'
            for reference in ('../outside/art.json', '/tmp/outside/art.json'):
                with self.subTest(reference=reference):
                    invalid = deepcopy(source)
                    invalid['shots'][0]['environment'] = reference
                    path.write_text(json.dumps(invalid))
                    scene = FireVeinholdOpening(self.game, scene_path=path)
                    self.addCleanup(scene.reset)
                    with self.assertRaises(ValueError):
                        scene.start()

    def test_invalid_native_art_and_flight_metadata_are_rejected_before_playback(self):
        with tempfile.TemporaryDirectory(prefix='prologue-invalid-art-') as folder:
            destination = Path(folder)/'scene'
            shutil.copytree(SCENE.parent, destination)
            path = destination/'scene.json'
            shot = json.loads(path.read_text())['shots'][0]
            environment_path = destination/shot['environment']
            eagle_path = destination/shot['eagle']
            environment = json.loads(environment_path.read_text())
            eagle = json.loads(eagle_path.read_text())
            cases = []
            for duration in (0, -1, float('nan'), float('inf'), True):
                invalid = deepcopy(eagle)
                invalid['sequences']['flap']['frames'][0]['duration_ms'] = duration
                cases.append((f'frame duration {duration}', environment, invalid))
            invalid = deepcopy(eagle)
            invalid['sequences']['flap']['frames'] = []
            cases.append(('empty flight sequence', environment, invalid))
            invalid = deepcopy(eagle)
            invalid['canvas'] = [128, 128]
            cases.append(('wrong native canvas', environment, invalid))
            invalid = deepcopy(eagle)
            invalid['anchor'] = [128, True]
            cases.append(('noninteger registration', environment, invalid))
            invalid = deepcopy(eagle)
            invalid['sequences']['flap']['frames'][0]['file'] = '../../../../../escape.png'
            cases.append(('escaped pose', environment, invalid))
            invalid_environment = deepcopy(environment)
            invalid_environment['density'] = 1
            cases.append(('wrong scenery density', invalid_environment, eagle))
            for framing in ([], {'ascent_start_y':float('inf')}, {'vista_y':-1}):
                invalid_environment = deepcopy(environment)
                invalid_environment['framing'] = framing
                cases.append(('invalid source framing', invalid_environment, eagle))
            for label, environment_record, eagle_record in cases:
                with self.subTest(case=label):
                    environment_path.write_text(json.dumps(environment_record))
                    eagle_path.write_text(json.dumps(eagle_record))
                    scene = FireVeinholdOpening(self.game, scene_path=path)
                    self.addCleanup(scene.reset)
                    with self.assertRaises(ValueError):
                        scene.start()

    def test_malformed_timing_and_required_art_containers_fail_as_authoring_errors(self):
        with tempfile.TemporaryDirectory(prefix='prologue-malformed-containers-') as folder:
            destination = Path(folder)/'scene'
            shutil.copytree(SCENE.parent, destination)
            path = destination/'scene.json'
            shot = json.loads(path.read_text())['shots'][0]
            environment_path = destination/shot['environment']
            eagle_path = destination/shot['eagle']
            environment = json.loads(environment_path.read_text())
            eagle = json.loads(eagle_path.read_text())
            cases = []
            invalid = deepcopy(eagle)
            invalid['timing']['period_ms'] = 0
            cases.append(('zero wing period', environment, invalid))
            invalid = deepcopy(eagle)
            invalid['timing'] = []
            cases.append(('timing is not a mapping', environment, invalid))
            invalid = deepcopy(eagle)
            del invalid['sequences']
            cases.append(('missing flight sequences', environment, invalid))
            invalid_environment = deepcopy(environment)
            del invalid_environment['layers']
            cases.append(('missing scenery layers', invalid_environment, eagle))
            for label, environment_record, eagle_record in cases:
                with self.subTest(case=label):
                    environment_path.write_text(json.dumps(environment_record))
                    eagle_path.write_text(json.dumps(eagle_record))
                    scene = FireVeinholdOpening(self.game, scene_path=path)
                    self.addCleanup(scene.reset)
                    with self.assertRaises(ValueError):
                        scene.start()
                    self.assertFalse(scene.active)

    def test_failed_later_clip_load_cannot_leave_a_partially_usable_asset_cache(self):
        with tempfile.TemporaryDirectory(prefix='prologue-atomic-load-') as folder:
            destination = Path(folder)/'scene'
            shutil.copytree(SCENE.parent, destination)
            path = destination/'scene.json'
            data = json.loads(path.read_text())
            first = deepcopy(data['shots'][0])
            appended = deepcopy(first)
            appended.update(id='fixture_later_ascent', gallery_id='fixture_later_gallery',
                            eagle='shot01/eagle/invalid_later_animation.json')
            data['shots'] = [first, appended]
            path.write_text(json.dumps(data))
            good_eagle = json.loads((destination/first['eagle']).read_text())
            invalid_eagle = deepcopy(good_eagle)
            invalid_eagle['canvas'] = [128, 128]
            later_path = destination/appended['eagle']
            later_path.write_text(json.dumps(invalid_eagle))
            scene = FireVeinholdOpening(self.game, scene_path=path)
            self.addCleanup(scene.reset)
            for attempt in (1, 2):
                with self.subTest(attempt=attempt):
                    with self.assertRaises(ValueError):
                        scene.start()
                    self.assertFalse(scene.active)
            # Correcting the actual failed source permits a clean retry. Both
            # clips must then be usable, including the one beyond the join.
            later_path.write_text(json.dumps(good_eagle))
            calls = []
            scene.start(lambda: calls.append('complete'))
            scene.update(first['duration']+.01)
            self.assertTrue(scene.active)
            self.assertEqual(scene.state_at(scene.elapsed)['shot_id'], appended['id'])
            self.assertEqual(calls, [])
            scene.update(appended['duration'])
            self.assertFalse(scene.active)
            self.assertEqual(calls, ['complete'])

    def test_velocity_matches_actual_camera_motion_when_authored_duration_changes(self):
        with tempfile.TemporaryDirectory(prefix='prologue-duration-velocity-') as folder:
            destination = Path(folder)/'scene'
            shutil.copytree(SCENE.parent, destination)
            path = destination/'scene.json'
            data = json.loads(path.read_text())
            data['shots'] = [data['shots'][0]]
            data['shots'][0].update(duration=20., ascent_duration=12., vista_duration=8.)
            path.write_text(json.dumps(data))
            scene = FireVeinholdOpening(self.game, scene_path=path)
            self.addCleanup(scene.reset)
            self.assertEqual(scene.duration, 20.)
            for time in (5., 12., 20.):
                with self.subTest(time=time):
                    before = scene.state_at(time-1e-4)['camera']
                    current = scene.state_at(time)['camera']
                    measured = [(last-first)/1e-4 for first, last in zip(
                        before['position'], current['position'])]
                    for actual, authored in zip(measured, current['velocity']):
                        self.assertAlmostEqual(actual, authored,
                                               delta=max(.01, abs(authored)*.01))


class FireVeinholdGalleryTests(unittest.TestCase):
    def setUp(self):
        from main import Game
        self.directory = tempfile.TemporaryDirectory(prefix='fire-veinhold-gallery-')
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.path = self.folder/'journey.json'
        self.settings = self.folder/'settings.json'
        seed = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                    save_path=self.path, settings_path=self.settings)
        seed.audio.set_music(0);seed.audio.set_effects(0)
        self.assertTrue(seed.save_progress())
        seed.music.stop();seed.opening_audio.reset();seed.regional_audio.reset()
        self.parent = Game(window_size=(960, 640), fullscreen=False,
                           save_path=self.path, settings_path=self.settings)
        pygame.event.clear()

    def tearDown(self):
        if self.parent.gallery_session is not None:
            self.parent.gallery_session.close(resume_music=False)
        self.parent.music.stop()
        self.parent.opening_audio.reset();self.parent.regional_audio.reset()
        self.parent = None
        pygame.quit()
        gc.collect()

    def parent_state(self):
        return ({str(path.relative_to(self.folder)): path.read_bytes()
                 for path in self.folder.rglob('*') if path.is_file()},
                deepcopy(self.parent.saved_journey),
                self.parent._progress_signature(), self.parent.elapsed_ms,
                tuple(self.parent.player.position), self.parent.cinematic)

    def launch(self, identifier):
        if not self.parent.on_gallery:
            self.assertTrue(self.parent.open_gallery())
        self.assertTrue(self.parent.launch_gallery_scene(identifier),
                        self.parent.gallery.error)
        return self.parent.gallery_session

    def key(self, key):
        self.parent.handle_events([
            pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False),
            pygame.event.Event(pygame.KEYUP, key=key)])

    def test_full_sequence_and_individual_shot_finish_without_changing_parent_save(self):
        before = self.parent_state()
        for identifier, duration in (
                ('fire_veinhold_opening', sequence_duration()),
                ('fire_veinhold_shot_01', 25.)):
            with self.subTest(entry=identifier):
                session = self.launch(identifier)
                scene = session.game.cinematic
                self.assertIsInstance(scene, FireVeinholdOpening)
                self.assertFalse(session.game.save_store.enabled)
                self.assertEqual(scene.duration, duration)
                self.assertFalse(session.game.save_progress())
                self.parent.update(duration-.001, (1, 0), True)
                self.assertIs(self.parent.gallery_session, session)
                self.assertTrue(scene.active)
                self.parent.update(.001, (1, 0), True)
                self.assertTrue(session.closed)
                self.assertIsNone(self.parent.gallery_session)
                self.assertTrue(self.parent.on_gallery)
                self.assertEqual(self.parent_state(), before)

    def test_gallery_pause_focus_restart_and_close_release_disposable_scene(self):
        before = self.parent_state()
        session = self.launch('fire_veinhold_shot_01')
        scene = session.game.cinematic
        self.parent.update(2.35, (0, 0), False)
        self.key(pygame.K_p)
        self.parent.update(.5, (0, 0), False)
        self.assertEqual(scene.elapsed, 2.35)
        self.key(pygame.K_p)
        self.parent.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        self.parent.update(.5, (0, 0), False)
        self.assertEqual(scene.elapsed, 2.35)
        self.parent.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.key(pygame.K_r)
        replacement = self.parent.gallery_session
        self.assertIsNot(replacement, session)
        self.assertTrue(session.closed)
        self.assertFalse(scene.active)
        self.assertEqual(scene.elapsed, 0.)
        self.assertEqual(replacement.game.cinematic.elapsed, 0.)
        self.key(pygame.K_ESCAPE)
        self.assertTrue(replacement.closed)
        self.assertIsNone(replacement.game.cinematic)
        self.assertTrue(self.parent.on_gallery)
        self.assertEqual(self.parent_state(), before)

    def test_production_new_game_still_begins_in_the_current_bedroom(self):
        self.assertTrue(self.parent.begin_journey())
        self.assertFalse(self.parent.on_title)
        self.assertIsNone(self.parent.cinematic)
        self.assertEqual(self.parent.world.data['id'], 'sanctuary_bedroom')
        self.assertEqual(self.parent.opening.stage, 'wake')
