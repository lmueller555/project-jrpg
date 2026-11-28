"""The side shot keeps authored gait, camera geometry and lifecycle separate."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from cinematic_bridge_run import CinematicBridgeRun, RENDER_SIZE, RUN_SCENE, read_run_timing


class BridgeRunTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode(RENDER_SIZE)
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root/'scene.json'
        self.players = []
        bridge = pygame.Surface((1920, 640), pygame.SRCALPHA)
        bridge.fill('#192d3f')
        for x in range(0, 1920, 90):
            pygame.draw.line(bridge, '#6b7e90', (x, 0), (x, 639), 3)
        pygame.image.save(bridge, str(self.root/'bridge.png'))
        actors = []
        for identifier, phase, offset, depth, ground in (
                ('lucan', 0., 0., 1., 532), ('iselin', .16, -.5, 1.04, 558),
                ('crown_soldier', .31, -3.048, .86, 506)):
            directory = self.root/identifier;directory.mkdir()
            frames = []
            for index in range(36):
                image = pygame.Surface((480, 480), pygame.SRCALPHA)
                # Deliberately recognizable head and lower-body regions test
                # viewport cropping; these rectangles are test fixtures only.
                pygame.draw.rect(image, '#ff00ff', (225, 30, 30, 30))
                pygame.draw.rect(image, (50+index*4, 100, 160), (200, 310, 70, 136))
                filename = f'frame_{index:02d}.png'
                pygame.image.save(image, str(directory/filename))
                frames.append({'file':filename, 'duration_ms':1000/60})
            animation = {'version':1, 'canvas':[480, 480], 'anchor':[240, 448],
                         'duration_ms':600, 'frames':frames,
                         'contacts':[{'frame':0, 'foot':'near'}, {'frame':18, 'foot':'far'}]}
            (directory/'animation.json').write_text(json.dumps(animation))
            actors.append({'id':identifier, 'animation':f'{identifier}/animation.json',
                           'phase_offset_seconds':phase, 'offset_metres':offset,
                           'depth_scale':depth, 'ground_y':ground})
        self.data = {'version':1, 'render_size':[960, 640], 'duration_seconds':3,
            'camera':{'anchor_x':760, 'pixels_per_metre':660, 'actor_scale':3.,
                      'speed_metres_per_second':3.6, 'drift_metres':2.,
                      'drift_start':1.15, 'drift_end':2.85},
            'layers':[{'id':'deck', 'file':'bridge.png', 'plane':'background',
                       'speed_factor':1., 'reduced_motion_factor':1., 'offset_y':0,
                       'mirror_repeat':True, 'ground':True}], 'actors':actors}
        self.write()

    def tearDown(self):
        for player in self.players:player.close()
        self.temp.cleanup();pygame.quit()

    def write(self):
        self.path.write_text(json.dumps(self.data))

    def player(self, **kwargs):
        player = CinematicBridgeRun(self.path, **kwargs)
        self.players.append(player)
        return player

    def controller(self):
        from fire_veinhold_opening import FireVeinholdOpening
        path = self.root/'film.json'
        path.write_text(json.dumps({'version':1, 'id':'fire_veinhold_opening',
            'render_size':[960, 640], 'logical_size':[480, 320], 'shots':[
                {'id':'bridge_running', 'gallery_id':'run_fixture', 'name':'Run fixture',
                 'description':'Synthetic staging fixture', 'type':'bridge_running',
                 'duration':3, 'performance':'scene.json'}]}))
        game = SimpleNamespace(audio=SimpleNamespace(reduced_motion=False, effects_volume=0),
                               _music_focused=True, to_canvas=lambda point:point)
        # This isolated controller fixture does not claim production Foley.
        with patch('prologue_alert_audio.running_contact_events', return_value=()):
            scene = FireVeinholdOpening(game, scene_path=path)
        self.addCleanup(scene.reset)
        return scene

    def test_shared_audio_contacts_are_actual_drawn_contact_frames(self):
        with patch('pygame.image.load', side_effect=AssertionError('Timing decoded an image')):
            timings = read_run_timing(self.path)
        self.assertEqual([item['id'] for item in timings], ['lucan', 'iselin', 'crown_soldier'])
        for item in timings:
            self.assertAlmostEqual(item['cycle_seconds'], .6)
            self.assertEqual([contact['frame'] for contact in item['contacts']], [0, 18])
            self.assertAlmostEqual(item['contacts'][1]['time_seconds'], .3)
        self.assertEqual(timings[1]['phase_offset_seconds'], .16)

    def test_sixty_hz_uses_thirty_six_authored_phases_five_times(self):
        player = self.player()
        indices = [player.samples(index/60)['runners'][0]['frame_index'] for index in range(180)]
        self.assertEqual(indices, list(range(36))*5)
        self.assertEqual(player.samples(3.)['runners'][0]['frame_index'], 0)

    def test_sampling_and_seeks_have_no_image_io_or_mutable_clock(self):
        player = self.player()
        with patch('pygame.image.load', side_effect=AssertionError('State decoded an image')):
            with patch.object(Path, 'open', side_effect=AssertionError('State opened a file')):
                expected = deepcopy(player.samples(2.3))
                player.samples(.1)
                self.assertEqual(player.samples(2.3), expected)
        self.assertEqual(player.cache_info['surfaces'], 0)

    def test_camera_keeps_ten_foot_gap_and_never_shrinks_the_actor_bank(self):
        player = self.player()
        for at in (0., .3, 1.5, 2.8, 3.):
            state = player.samples(at)
            actors = {actor['id']:actor for actor in state['runners']}
            self.assertAlmostEqual(actors['lucan']['world_position_metres'][0]
                                   -actors['crown_soldier']['world_position_metres'][0], 3.048)
            self.assertEqual(actors['lucan']['scale'], 3.)
            self.assertEqual(state['camera']['direction'], 'toward_veinhold')
        self.assertFalse(player.samples(0.)['runners'][2]['visible'])
        self.assertTrue(player.samples(3.)['runners'][2]['visible'])

    def test_reduced_motion_keeps_gait_and_world_travel_but_removes_camera_drift(self):
        player = self.player()
        normal, reduced = player.samples(2.5), player.samples(2.5, True)
        self.assertGreater(normal['camera']['drift_metres'], 0.)
        self.assertEqual(reduced['camera']['drift_metres'], 0.)
        for a, b in zip(normal['runners'], reduced['runners']):
            self.assertEqual(a['frame_index'], b['frame_index'])
            self.assertEqual(a['world_position_metres'], b['world_position_metres'])
            self.assertEqual(a['scale'], b['scale'])

    def test_draw_is_deterministic_and_crops_faces_without_changing_source_pixels(self):
        player = self.player()
        a, b = pygame.Surface(RENDER_SIZE), pygame.Surface(RENDER_SIZE)
        state = player.samples(.125)
        player.draw(a, state);player.draw(b, state)
        self.assertEqual(pygame.image.tobytes(a, 'RGB'), pygame.image.tobytes(b, 'RGB'))
        colors = pygame.surfarray.array3d(a)
        self.assertFalse(((colors[:, :, 0] == 255) & (colors[:, :, 1] == 0)
                          & (colors[:, :, 2] == 255)).any())
        self.assertEqual(pygame.image.load(str(self.root/'lucan/frame_00.png')).get_at((230, 35)),
                         pygame.Color('#ff00ff'))

    def test_source_cache_stays_bounded_and_close_releases_reusable_drawing_data(self):
        player = self.player(cache_size=9)
        target = pygame.Surface(RENDER_SIZE)
        for frame in range(180):
            state = player.preload(frame/60)
            player.draw(target, state)
            info = player.cache_info
            self.assertLessEqual(info['frame_surfaces'], 9)
            self.assertLessEqual(info['surfaces'], info['capacity'])
            self.assertLessEqual(info['bytes'], 9*480*480*4+2*1920*640*4)
        player.close()
        self.assertEqual(player.cache_info['surfaces'], 0)
        self.assertEqual(player.cache_info['bytes'], 0)
        player.draw(target, player.samples(.25))
        self.assertGreater(player.cache_info['surfaces'], 0)

    def test_distant_stars_stay_fixed_while_the_transparent_bridge_moves(self):
        rail = pygame.Surface((1920, 640), pygame.SRCALPHA)
        pygame.draw.rect(rail, '#203d53', (0, 300, 1920, 340))
        for x in range(0, 1920, 75):
            pygame.draw.line(rail, '#8da3b4', (x, 200), (x, 639), 4)
        pygame.image.save(rail, str(self.root/'rail.png'))
        self.data['layers'] = [
            {'id':'distant', 'file':'bridge.png', 'plane':'background',
             'speed_factor':0., 'reduced_motion_factor':0., 'offset_y':0},
            {'id':'ground', 'file':'rail.png', 'plane':'background',
             'speed_factor':1., 'reduced_motion_factor':1., 'offset_y':0,
             'mirror_repeat':True, 'ground':True}]
        self.write();player = self.player()
        a, b = pygame.Surface(RENDER_SIZE), pygame.Surface(RENDER_SIZE)
        player.draw(a, player.samples(0.));player.draw(b, player.samples(2.25))
        self.assertEqual(pygame.image.tobytes(a.subsurface((0, 0, 960, 90)), 'RGB'),
                         pygame.image.tobytes(b.subsurface((0, 0, 960, 90)), 'RGB'))
        self.assertNotEqual(pygame.image.tobytes(a, 'RGB'), pygame.image.tobytes(b, 'RGB'))

    def test_pending_decodes_reserve_slots_and_close_drains_both_workers(self):
        import cinematic_bridge_run
        player = self.player(cache_size=9)
        original = cinematic_bridge_run._decode_png
        release, started, closed = threading.Event(), threading.Event(), threading.Event()
        def blocked(path, canvas):
            started.set()
            if not release.wait(3.):raise RuntimeError('Test did not release its software decoder')
            return original(path, canvas)
        with patch('cinematic_bridge_run._decode_png', side_effect=blocked):
            player.preload(0.)
            self.assertTrue(started.wait(1.))
            info = player.cache_info
            self.assertGreater(info['pending_bytes'], 0)
            self.assertLessEqual(info['surfaces'], info['capacity'])
            futures = [*player._cache.values(), *player._backgrounds.values()]
            def close():
                player.close();closed.set()
            worker = threading.Thread(target=close)
            worker.start()
            try:
                self.assertFalse(closed.wait(.02))
            finally:
                release.set();worker.join(3.)
            self.assertTrue(closed.is_set())
            self.assertTrue(all(future.done() for future in futures))
            self.assertEqual(player.cache_info['surfaces'], 0)
            self.assertIsNone(player._executor)

    def test_missing_frames_path_traversal_bad_contacts_and_compressed_formation_fail(self):
        for mutate in (
                lambda data:data['actors'][0].update(animation='../outside.json'),
                lambda data:data['actors'][2].update(offset_metres=-.5),
                lambda data:data['camera'].update(drift_end=.5, drift_start=1.),
                lambda data:data['layers'][0].update(reduced_motion_factor=.5),
                lambda data:data['actors'][0].update(phase_offset_seconds=float('nan'))):
            with self.subTest(mutate=mutate):
                original = deepcopy(self.data)
                mutate(self.data);self.write()
                with self.assertRaises(ValueError):self.player()
                self.data = original
        self.write()
        animation_path = self.root/'lucan/animation.json'
        animation = json.loads(animation_path.read_text())
        animation['contacts'][1]['foot'] = 'near'
        animation_path.write_text(json.dumps(animation))
        with self.assertRaises(ValueError):self.player()

    def test_controller_pause_restart_and_completion_release_the_native_bank(self):
        scene = self.controller();completed = []
        scene.start(lambda:completed.append('complete'))
        scene.update(.25)
        player = scene._assets['bridge_running']['running']
        before = deepcopy(scene.state_at(scene.elapsed))
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
        scene.update(1.)
        self.assertEqual(scene.state_at(scene.elapsed), before)
        scene.reset()
        self.assertEqual(player.cache_info['surfaces'], 0)
        scene.start(lambda:completed.append('complete'))
        scene.update(3.)
        self.assertFalse(scene.active)
        self.assertEqual(scene.elapsed, 3.)
        self.assertEqual(player.cache_info['surfaces'], 0)
        self.assertEqual(completed, ['complete'])

    def test_failed_running_load_can_retry_after_the_missing_art_is_restored(self):
        scene = self.controller()
        image = self.root/'lucan/frame_00.png'
        moved = image.with_suffix('.missing')
        image.rename(moved)
        with self.assertRaises(ValueError):scene.start()
        self.assertEqual(scene._assets, {})
        self.assertEqual(scene._running, {})
        moved.rename(image)
        scene.start()
        self.assertTrue(scene.active)
        self.assertEqual(scene.render_frame().get_size(), RENDER_SIZE)


class ProductionBridgeRunTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode(RENDER_SIZE)
        self.game = SimpleNamespace(audio=SimpleNamespace(reduced_motion=False, effects_volume=0),
                                    _music_focused=True, to_canvas=lambda point:point)
        from fire_veinhold_opening import FireVeinholdOpening
        self.scene = FireVeinholdOpening(self.game)
        self.clip = FireVeinholdOpening(self.game, 'bridge_running')
        self.addCleanup(self.scene.reset);self.addCleanup(self.clip.reset)

    def tearDown(self):
        self.scene.reset();self.clip.reset();pygame.quit()

    def test_side_shot_is_three_seconds_and_standalone_pixels_match_global_time(self):
        self.assertEqual(self.scene.duration, 55.)
        self.assertEqual(self.clip.global_offset, 39.)
        self.assertEqual(self.clip.duration, 3.)
        for local in (0., .4, 1.5, 2.8):
            self.assertEqual(self.scene.state_at(39.+local), self.clip.state_at(local))
            self.assertEqual(pygame.image.tobytes(self.scene.render_frame(39.+local), 'RGB'),
                             pygame.image.tobytes(self.clip.render_frame(local), 'RGB'))

    def test_party_appears_only_after_guard_hold_with_independent_gait_and_display_clocks(self):
        for at in (0., 25., 30., 34., 35., 38.999):
            self.assertNotIn('runners', self.scene.state_at(at))
        self.assertEqual(self.scene.state_at(39.)['phase'], 'bridge_running')
        timings = read_run_timing(RUN_SCENE)
        self.assertEqual(len(timings), 3)
        for actor in timings:
            self.assertAlmostEqual(actor['cycle_seconds'], .8)
            self.assertEqual([contact['frame'] for contact in actor['contacts']], [0, 12])
        indices = [self.clip.state_at(index/60)['runners'][0]['frame_index'] for index in range(180)]
        self.assertEqual(indices, [(tick//2) % 24 for tick in range(180)])
        self.assertEqual(self.clip.state_at(0.)['camera']['position_metres'][0], 0.)
        self.assertEqual(self.clip._assets['bridge_running']['running'].data['camera']['speed_metres_per_second'], 4.)

    def test_retimed_deck_preserves_stride_excursion_and_trailing_soldier_framing(self):
        self.clip.state_at(0.)
        owner = self.clip._assets['bridge_running']['running']
        camera = owner.data['camera']
        # The new world-density calibration retains the artwork's original
        # deck distance per two-step cycle while slowing its cadence by half.
        self.assertAlmostEqual(camera['speed_metres_per_second']*.8*camera['pixels_per_metre'],
                               11.42*.4*660)
        last = {actor['id']:actor for actor in owner.samples(3.)['runners']}
        self.assertAlmostEqual(last['crown_soldier']['ground_anchor'][0], 126.32)
        self.assertTrue(last['crown_soldier']['visible'])
        self.assertEqual(owner.samples(0.)['runners'][0]['ground_anchor'][0], 620.)
        self.assertEqual(owner.samples(0.)['camera']['party_travel_metres'], 22.26)
        self.assertAlmostEqual(owner.samples(3.)['camera']['party_travel_metres'], 34.26)

    def test_pause_focus_and_natural_completion_release_the_running_cache(self):
        self.clip.start()
        self.clip.update(.25)
        owner = self.clip._assets['bridge_running']['running']
        self.assertGreater(owner.cache_info['surfaces'], 0)
        before = deepcopy(self.clip.state_at(self.clip.elapsed))
        self.clip.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
        self.clip.update(1.)
        self.assertEqual(self.clip.state_at(self.clip.elapsed), before)
        self.clip.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
        self.clip.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.clip.update(1.)
        self.assertEqual(self.clip.state_at(self.clip.elapsed), before)
        self.clip.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.clip.update(2.75)
        self.assertEqual(self.clip.elapsed, 3.)
        self.assertFalse(self.clip.active)
        self.assertEqual(owner.cache_info['surfaces'], 0)
        self.assertFalse(self.clip.flight_audio.voices)
        self.assertFalse(self.clip.alert_audio.voices)


if __name__ == '__main__':unittest.main()
