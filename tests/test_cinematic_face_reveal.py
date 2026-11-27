"""Frontal projection, phase continuity and bounded presentation ownership."""
from copy import deepcopy
from concurrent.futures import Future
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from cinematic_face_reveal import (CinematicFaceReveal, DEFAULT_CAMERA, FACE_SCENE,
                                   camera_at, performance_signature, project_world, read_face_timing)


class FaceRevealTests(unittest.TestCase):
    """Colored blocks are diagnostic fixtures, never production character art."""
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 640))
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.players = []
        environment = self.root/'environment'
        environment.mkdir()
        background = pygame.Surface((960, 640))
        background.fill('#12273b')
        pygame.image.save(background, str(environment/'background.png'))
        for index in range(9):
            shutil.copyfile(environment/'background.png', environment/f'frame_{index}.png')
        clear = pygame.Surface((960, 640), pygame.SRCALPHA)
        pygame.image.save(clear, str(environment/'clear.png'))
        frames = [f'frame_{index%9}.png' for index in range(301)]
        cameras = [{'index':index, 'time_seconds':index/60, 'camera':camera_at(index/60)}
                   for index in range(301)]
        (environment/'cameras.json').write_text(json.dumps(cameras))
        segments = {name:{'duration_ms':5000, 'frames':frames, 'alarm_frames':['clear.png']*301,
                          'metadata_path':'cameras.json'}
                    for name in ('face_reveal', 'face_reveal_reduced')}
        (environment/'manifest.json').write_text(json.dumps(
            {'version':1, 'width':960, 'height':640, 'fps':60, 'segments':segments}))
        actors = []
        for identifier, phase, along, lane, color in (
                ('lucan', .2, 0., 0., '#fa140a'),
                ('iselin', .2+5/60, -.5, .65, '#dde3ff'),
                ('crown_soldier', .2+9/60, -3.048, -.75, '#e5b964')):
            folder = self.root/identifier
            folder.mkdir()
            image = pygame.Surface((768, 1024), pygame.SRCALPHA)
            pygame.draw.rect(image, '#416a9c', (305, 160, 158, 700))
            pygame.draw.circle(image, color, (384, 100), 52)
            pygame.image.save(image, str(folder/'source.png'))
            poses = []
            for index in range(24):
                filename = f'frame_{index:02d}.png'
                shutil.copyfile(folder/'source.png', folder/filename)
                poses.append({'file':filename, 'duration_ms':1000/60})
            (folder/'animation.json').write_text(json.dumps({
                'version':1, 'canvas':[768,1024], 'anchor':[384,960],
                'duration_ms':400, 'frames':poses,
                'contacts':[{'frame':0,'foot':'near'}, {'frame':12,'foot':'far'}]}))
            actors.append({'id':identifier, 'animation':f'{identifier}/animation.json',
                           'phase_offset_seconds':phase, 'offset_metres':along, 'lane_metres':lane})
        self.data = {'version':1, 'render_size':[960,640], 'duration_seconds':5,
                     'camera':dict(DEFAULT_CAMERA), 'actors':actors,
                     'environment':'environment/manifest.json',
                     'environment_segments':{'normal':'face_reveal', 'reduced_motion':'face_reveal_reduced'}}
        self.path = self.root/'scene.json'
        self.write()

    def tearDown(self):
        for player in self.players:
            player.close()
        self.temp.cleanup()
        pygame.quit()

    def write(self):
        self.path.write_text(json.dumps(self.data))

    def player(self, **kwargs):
        player = CinematicFaceReveal(self.path, **kwargs)
        self.players.append(player)
        return player

    def controller(self):
        from fire_veinhold_opening import FireVeinholdOpening
        film = {'version':1, 'id':'fire_veinhold_opening', 'render_size':[960,640],
                'logical_size':[480,320], 'shots':[
                    {'id':'face_reveal', 'gallery_id':'face_fixture', 'name':'Face fixture',
                     'description':'Synthetic projection fixture', 'type':'face_reveal',
                     'duration':5, 'performance':'scene.json'}]}
        path = self.root/'film.json'
        path.write_text(json.dumps(film))
        game = SimpleNamespace(audio=SimpleNamespace(reduced_motion=False, effects_volume=0),
                               _music_focused=True, to_canvas=lambda point:point)
        with patch('prologue_alert_audio.running_contact_events', return_value=()):
            scene = FireVeinholdOpening(game, scene_path=path)
        self.addCleanup(scene.reset)
        return scene

    def test_camera_reveals_heads_after_initial_sky_and_tracks_world_travel(self):
        first, last = camera_at(0), camera_at(1.5)
        point = (0., first['party_travel_metres'], 1.76)
        self.assertGreater(project_world(point, first)[1], 640)
        point = (0., last['party_travel_metres'], 1.76)
        self.assertTrue(140 < project_world(point, last)[1] < 240)
        self.assertEqual(project_world((0., 2000., 0.), last), None)
        later = camera_at(4.)
        self.assertAlmostEqual(later['position'][1]-last['position'][1], 2.5*DEFAULT_CAMERA['speed_metres_per_second'])
        self.assertEqual(project_world(point, last)[:2],
                         project_world((0., later['party_travel_metres'], 1.76), later)[:2])

    def test_travel_speed_does_not_relocate_the_authored_starting_marker(self):
        slow = dict(DEFAULT_CAMERA, speed_metres_per_second=2.)
        fast = dict(DEFAULT_CAMERA, speed_metres_per_second=6.)
        self.assertEqual(camera_at(0., config=slow)['party_travel_metres'], 34.26)
        self.assertEqual(camera_at(0., config=fast)['party_travel_metres'], 34.26)
        self.assertEqual(camera_at(2., config=slow)['party_travel_metres'], 38.26)
        self.assertEqual(camera_at(2., config=fast)['party_travel_metres'], 46.26)

    def test_baked_performance_streams_pixels_without_loading_source_drawings(self):
        self.data['baked_characters'] = True
        self.write()
        manifest_path = self.root/'environment/manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['baked_characters'] = True
        manifest['performance_signature'] = performance_signature(self.path)
        manifest_path.write_text(json.dumps(manifest))
        player = self.player()
        target = pygame.Surface((960, 640))
        with patch('cinematic_bridge_run._decode_png', side_effect=AssertionError('Source drawing decoded')):
            for at in (0., .8, 1.5, 3., 5.):
                state = player.preload(at, blocking=True)
                player.draw(target, state)
                self.assertEqual(target.get_at((480, 320))[:3], (18, 39, 59))
                info = player.cache_info
                self.assertEqual(info['actor_cache']['surfaces'], 0)
                self.assertEqual(info['expected_frames'], 0)
                self.assertLessEqual(info['bytes'], 8*960*640*4)
                self.assertEqual(info['byte_capacity'], 8*960*640*4)
        player.close()
        self.assertEqual(player.cache_info['bytes'], 0)

    def test_baked_playback_rejects_an_uncomposited_environment_bank(self):
        self.data['baked_characters'] = True
        self.write()
        manifest_path = self.root/'environment/manifest.json'
        manifest = json.loads(manifest_path.read_text())
        for marker in (None, False, 'true', 1):
            if marker is None:
                manifest.pop('baked_characters', None)
            else:
                manifest['baked_characters'] = marker
            manifest_path.write_text(json.dumps(manifest))
            with self.subTest(marker=marker):
                with self.assertRaisesRegex(ValueError, 'character-composited environment bank'):
                    self.player()
        # Explicit offline mode can still author the missing full performance.
        self.assertFalse(self.player(baked_characters=False).baked_characters)

    def test_baked_signature_rejects_changed_phase_camera_segment_and_frame_contract(self):
        self.data['baked_characters'] = True
        self.write()
        manifest_path = self.root/'environment/manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest.update(baked_characters=True, performance_signature=performance_signature(self.path))
        manifest_path.write_text(json.dumps(manifest))
        original_scene = deepcopy(self.data)
        animation_path = self.root/'lucan/animation.json'
        original_animation = json.loads(animation_path.read_text())
        for change in ('phase', 'camera', 'segments', 'duration', 'anchor', 'frame_order', 'frame_count'):
            self.data = deepcopy(original_scene)
            animation = deepcopy(original_animation)
            if change == 'phase':
                self.data['actors'][0]['phase_offset_seconds'] += 1/60
            elif change == 'camera':
                self.data['camera']['speed_metres_per_second'] += 1.
            elif change == 'segments':
                self.data['environment_segments']['normal'] = 'face_reveal_reduced'
            elif change == 'duration':
                animation['duration_ms'] *= 2
                for frame in animation['frames']:
                    frame['duration_ms'] *= 2
            elif change == 'anchor':
                animation['anchor'][0] += 1
            elif change == 'frame_order':
                animation['frames'][0], animation['frames'][1] = animation['frames'][1], animation['frames'][0]
            elif change == 'frame_count':
                animation['frames'].pop()
                animation['duration_ms'] = sum(frame['duration_ms'] for frame in animation['frames'])
            self.write()
            animation_path.write_text(json.dumps(animation))
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError, 'performance is stale'):
                    self.player()
        self.data = original_scene
        self.write()
        animation_path.write_text(json.dumps(original_animation))
        self.player()  # Restoring the exact metadata restores the accepted bake.

    def test_signature_is_portable_canonical_and_reads_no_pose_pixels(self):
        with patch('pygame.image.load', side_effect=AssertionError('Signature decoded a drawing')):
            before = performance_signature(self.path)
        with tempfile.TemporaryDirectory() as destination:
            relocated = Path(destination)/'relocated'
            shutil.copytree(self.root, relocated)
            self.assertEqual(performance_signature(relocated/'scene.json'), before)
            animation_path = relocated/'lucan/animation.json'
            metadata = json.loads(animation_path.read_text())
            animation_path.write_text(json.dumps(metadata, sort_keys=True, indent=7))
            self.assertEqual(performance_signature(relocated/'scene.json'), before)
        provenance = self.root/'lucan/provenance.json'
        provenance.write_text(json.dumps({'registrations':[{'frame':0, 'sha256':'a'*64}]}))
        declared = performance_signature(self.path)
        self.assertNotEqual(declared, before)
        provenance.write_text(json.dumps({'registrations':[{'frame':0, 'sha256':'b'*64}]}))
        self.assertNotEqual(performance_signature(self.path), declared)

    def test_offline_override_can_draw_source_figures_over_a_fresh_background(self):
        self.data['baked_characters'] = True
        self.write()
        player = self.player(baked_characters=False)
        target = pygame.Surface((960, 640))
        target.fill('#12273b')
        state = player.preload(1.5, blocking=True)
        player.draw_unbaked(target, state)
        self.assertNotEqual(target.get_at((480, 160))[:3], (18, 39, 59))
        manifest_path = self.root/'environment/manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['baked_characters'] = True
        manifest['performance_signature'] = performance_signature(self.path)
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'unbaked owner'):
            self.player().draw_unbaked(target, state)

    def test_anatomical_sides_and_ten_foot_gap_survive_perspective(self):
        player = self.player()
        for local in (0., .4, 1.5, 3., 5.):
            actors = {actor['id']:actor for actor in player.samples(local)['runners']}
            self.assertLess(actors['iselin']['ground_anchor'][0], actors['lucan']['ground_anchor'][0])
            self.assertGreater(actors['crown_soldier']['ground_anchor'][0], actors['lucan']['ground_anchor'][0])
            self.assertAlmostEqual(actors['lucan']['world_position_metres'][1]-
                                   actors['crown_soldier']['world_position_metres'][1], 3.048)
            self.assertLess(actors['crown_soldier']['scale'], actors['iselin']['scale'])
            self.assertLess(actors['iselin']['scale'], actors['lucan']['scale'])

    def test_each_of_300_ticks_advances_one_phase_without_resetting_at_the_cut(self):
        player = self.player()
        starts = (12,17,21)
        for actor, first in enumerate(starts):
            indices = [player.samples(tick/60)['runners'][actor]['frame_index'] for tick in range(300)]
            self.assertEqual(indices[0], first)
            self.assertTrue(all((right-left)%24 == 1 for left,right in zip(indices,indices[1:])))

    def test_timing_and_sample_queries_do_not_decode_images(self):
        player = self.player()
        expected = deepcopy(player.samples(2.25))
        with patch('pygame.image.load', side_effect=AssertionError('State decoded an image')):
            timing = read_face_timing(self.path)
            player.samples(.2)
            self.assertEqual(player.samples(2.25), expected)
        self.assertEqual(timing[0]['contacts'][1]['frame'], 12)
        self.assertEqual(player.cache_info['surfaces'], 0)

    def test_render_reveals_all_three_diagnostic_faces_without_changing_anatomy(self):
        player = self.player()
        image = pygame.Surface((960,640))
        for local in (0., 1.5):
            state = player.preload(local, blocking=True)
            player.draw(image, state)
            rgb = pygame.surfarray.array3d(image).astype('int16')
            for color in ((250,20,10), (221,227,255), (229,185,100)):
                # Premultiplied SDL sampling can round opaque channels by a
                # couple of levels; identify the marker, not byte-exact color.
                count = int(((abs(rgb-color) <= 3).all(axis=2)).sum())
                self.assertEqual(count, 0) if local == 0 else self.assertGreater(count, 100)

    def test_actor_and_environment_caches_respect_reservations_and_drain(self):
        player = self.player()
        image = pygame.Surface((960,640))
        for tick in range(18):
            state = player.preload(tick/60, blocking=True)
            player.draw(image, state)
            info = player.cache_info
            self.assertLessEqual(info['actor_cache']['surfaces'], 72)
            self.assertLessEqual(info['environment_cache']['surfaces'], 8)
            self.assertLessEqual(info['bytes'], info['byte_capacity'])
        self.assertGreater(player.cache_info['bytes'], 0)
        player.close()
        self.assertEqual(player.cache_info['surfaces'], 0)
        self.assertEqual(player.cache_info['bytes'], 0)
        player.preload(0., blocking=True)
        self.assertGreater(player.cache_info['bytes'], 0)

    def test_full_cycle_is_prepared_once_and_reused_without_actor_decode_or_eviction(self):
        player = self.player()
        player.preload(0., blocking=True)
        before = player.cache_info['actor_cache']
        self.assertEqual(player.cache_info['prepared_frames'], 72)
        self.assertEqual(before['surfaces'], 72)
        image = pygame.Surface((960,640))
        with patch('cinematic_bridge_run._decode_png', side_effect=AssertionError('Repeated actor decode')):
            for tick in range(72):
                state = player.preload(1.5+tick/60)
                player.draw(image, state)
                info = player.cache_info
                self.assertEqual(info['actor_cache']['surfaces'], 72)
                self.assertEqual(info['actor_cache']['decodes'], before['decodes'])
                self.assertEqual(info['actor_cache']['waits'], before['waits'])
                self.assertLessEqual(info['bytes'], info['byte_capacity'])

    def test_nonblocking_warmup_converts_at_most_two_ready_drawings_per_call(self):
        player = self.player()
        software = pygame.Surface((768,1024), pygame.SRCALPHA)

        def completed(path, *, background=False):
            future = Future()
            future.set_result(software)
            player._cache[path] = future
            player._decodes += 1

        with patch.object(player, '_queue', side_effect=completed):
            player.preload(0.)
            self.assertEqual(player.cache_info['actor_cache']['surfaces'], 72)
            self.assertEqual(player.cache_info['prepared_frames'], 2)
            player.preload(0.)
            self.assertEqual(player.cache_info['prepared_frames'], 4)
        self.assertEqual(player.cache_info['actor_cache']['decodes'], 72)

    def test_reduced_motion_preserves_essential_disclosure_gait_and_registration(self):
        player = self.player()
        for at in (0., .5, 1.5, 4.5):
            regular, reduced = player.samples(at), player.samples(at, True)
            self.assertEqual(regular['camera'], reduced['camera'])
            self.assertEqual(regular['runners'], reduced['runners'])
            self.assertEqual(regular['environment']['frame_index'], reduced['environment']['frame_index'])
            self.assertNotIn('blend_frame_index', reduced['environment'])

    def test_invalid_formation_and_camera_are_rejected(self):
        self.data['actors'][2]['offset_metres'] = -1.
        self.write()
        with self.assertRaises(ValueError):
            self.player()
        self.data['actors'][2]['offset_metres'] = -3.048
        self.data['camera']['pitch_start_radians'] = float('nan')
        self.write()
        with self.assertRaises(ValueError):
            self.player()

    def test_background_registration_cannot_silently_diverge_from_the_actor_camera(self):
        path = self.root/'environment/cameras.json'
        cameras = json.loads(path.read_text())
        cameras[45]['camera']['position'][2] += .1
        path.write_text(json.dumps(cameras))
        with self.assertRaisesRegex(ValueError, 'background camera'):
            self.player()

    def test_controller_pause_focus_seek_restart_and_natural_completion_cleanup(self):
        scene = self.controller()
        finished = []
        scene.start(lambda:finished.append(scene.finished_reason))
        scene.update(1.)
        first = pygame.image.tobytes(scene.render_frame(), 'RGB')
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        scene.update(1.)
        self.assertEqual(scene.elapsed, 1.)
        self.assertEqual(pygame.image.tobytes(scene.render_frame(), 'RGB'), first)
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        scene.update(1.)
        self.assertEqual(scene.elapsed, 1.)
        scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        scene.update(4.)
        self.assertEqual(finished, ['completed'])
        self.assertFalse(scene.active)
        self.assertTrue(all(not owner.cache_info['surfaces'] for owner in scene._face_reveals.values()))
        scene.start()
        self.assertEqual(scene.elapsed, 0.)
        scene.skip()
        self.assertTrue(all(not owner.cache_info['bytes'] for owner in scene._face_reveals.values()))


class ProductionFaceRevealTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960,640))

    def tearDown(self):
        pygame.quit()

    def test_production_phase_continues_the_side_shot_for_300_ticks(self):
        from cinematic_bridge_run import CinematicBridgeRun
        previous, player = CinematicBridgeRun(), CinematicFaceReveal()
        try:
            self.assertAlmostEqual(previous.samples(3.)['camera']['party_travel_metres'],
                                   player.samples(0.)['camera']['party_travel_metres'])
            previous_stages = previous.samples(3.)['runners']
            current_stages = player.samples(0.)['runners']
            for before, after in zip(previous_stages, current_stages):
                self.assertAlmostEqual(before['cycle_phase'], after['cycle_phase'])
            for actor_index, actor in enumerate(player.data['actors']):
                animation = actor['animation']
                self.assertAlmostEqual(animation['cycle_seconds'], .8)
                self.assertEqual(len(animation['frames']), 48)
                indices = [player.samples(tick/60)['runners'][actor_index]['frame_index']
                           for tick in range(300)]
                self.assertTrue(all((right-left)%len(animation['frames']) == 1
                                    for left,right in zip(indices,indices[1:])))
            self.assertTrue(player.baked_characters)
            self.assertEqual(player.cache_info['expected_frames'], 0)
        finally:
            previous.close()
            player.close()

    def test_full_and_standalone_seeks_share_picture_and_global_clock(self):
        from fire_veinhold_opening import FireVeinholdOpening
        game = SimpleNamespace(audio=SimpleNamespace(reduced_motion=False, effects_volume=0),
                               _music_focused=True, to_canvas=lambda point:point)
        complete, single = FireVeinholdOpening(game), FireVeinholdOpening(game, 'face_reveal')
        try:
            for at in (0., .4, 1.5, 3., 299/60):
                self.assertEqual(complete.state_at(42.+at), single.state_at(at))
                self.assertEqual(pygame.image.tobytes(complete.render_frame(42.+at), 'RGB'),
                                 pygame.image.tobytes(single.render_frame(at), 'RGB'))
        finally:
            complete.reset()
            single.reset()

    def test_frontal_cut_releases_preceding_caches_and_completion_releases_new_owners(self):
        from fire_veinhold_opening import FireVeinholdOpening
        game = SimpleNamespace(audio=SimpleNamespace(reduced_motion=False, effects_volume=0),
                               _music_focused=True, to_canvas=lambda point:point)
        scene = FireVeinholdOpening(game)
        try:
            scene.start()
            self.assertEqual(scene.elapsed, 0.)
            self.assertTrue(all(owner.cache_info['prepared_frames'] == 0
                                for owner in scene._face_reveals.values()))
            scene.update(40.99)
            self.assertTrue(all(owner.cache_info['prepared_frames'] == 0
                                for owner in scene._face_reveals.values()))
            scene.update(.01)
            self.assertTrue(all(owner.cache_info['actor_cache']['surfaces'] == 0
                                for owner in scene._face_reveals.values()))
            scene.update(1.)
            scene.render_frame()
            self.assertEqual(scene.state_at(scene.elapsed)['phase'], 'face_reveal')
            self.assertTrue(all(not owner.cache_info['bytes'] for owner in scene._running.values()))
            self.assertTrue(all(not owner.cache_info['bytes'] for owner in scene._perspectives.values()))
            self.assertTrue(any(owner.cache_info['bytes'] for owner in scene._face_reveals.values()))
            scene.update(5.)
            self.assertEqual(scene.elapsed, 47.)
            self.assertTrue(all(not owner.cache_info['surfaces'] for owner in scene._face_reveals.values()))
        finally:
            scene.reset()


if __name__ == '__main__':
    unittest.main()
