"""The complete Ice Reaper preview preserves actor identity and a thirty-two-second clock."""
import copy
import gc
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from ice_reaper_opening import IceReaperOpening


ROOT = Path(__file__).resolve().parents[1]
PARTY = {
    'caelan': 'assets/combat/caelan/idle_01.png',
    'mira': 'assets/combat/mira/idle_01.png',
    'rhea': 'assets/combat/rhea/idle_01.png',
    'lucan': 'assets/combat/lucan/idle_01.png',
}


class IceReaperOpeningTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((480, 320))
        self.game = SimpleNamespace(audio=SimpleNamespace(reduced_motion=False),
                                    _music_focused=True, to_canvas=lambda point: point)
        self.scene = IceReaperOpening(self.game)

    def tearDown(self):
        pygame.quit()

    def test_exact_thirty_two_second_completion_at_30_and_60_fps(self):
        for fps in (30, 60):
            with self.subTest(fps=fps):
                calls = []
                self.scene.start(lambda: calls.append('done'))
                for _ in range(fps*32):
                    self.scene.update(1/fps)
                self.assertFalse(self.scene.active)
                self.assertEqual(self.scene.elapsed, 32.)
                self.assertEqual(self.scene.finished_reason, 'completed')
                self.scene.update(1)
                self.scene.skip()
                self.assertEqual(calls, ['done'])

    def test_party_uses_approved_frames_with_matching_combat_display_scale(self):
        for actor in self.scene.data['actors']:
            if actor['id'] not in PARTY:
                continue
            with self.subTest(actor=actor['id']):
                path = self.scene.scene_path.parent/actor['manifest']
                manifest = json.loads(path.read_text())
                if actor['id'] == 'caelan':
                    self.assertEqual(manifest['canvas'], [128, 128])
                    self.assertEqual(manifest['anchor'], [64, 116])
                    self.assertEqual(actor.get('pixel_scale', 1), 1)
                    source_path = ROOT/'assets/story/ice_reaper_rescue/actors/caelan/animation.json'
                    source = json.loads(source_path.read_text())
                    ready = manifest['loops']['ready']
                    self.assertEqual(len(ready), 4)
                    for local, authored in zip(ready, source['animations']['ready']['frames']):
                        self.assertEqual((path.parent/local['file']).read_bytes(),
                                         (source_path.parent/authored['file']).read_bytes())
                    continue
                source = json.loads((ROOT/f"assets/combat/{actor['id']}/animation.json").read_text())
                self.assertEqual(manifest['canvas'], source['canvas'])
                self.assertEqual(manifest['anchor'], source['anchor'])
                self.assertEqual(actor.get('pixel_scale', 1), 2)
                self.assertTrue(manifest['copied_without_pixel_changes'])
                self.assertEqual((path.parent/manifest['poses']['stand']).read_bytes(),
                                 (ROOT/PARTY[actor['id']]).read_bytes())

    def test_rhea_holds_while_companions_cycle_their_combat_ready_frames(self):
        self.scene.start()
        sampled = {}
        for actor in ('rhea', 'lucan', 'caelan', 'mira'):
            record, anchor, frames, transitions = next(
                entry for entry in self.scene.actors if entry[0]['id'] == actor)
            sampled[actor] = []
            for time in (0., .2, .4, .6):
                self.scene.elapsed = time
                image = self.scene._actor_frame(actor, frames, transitions)
                sampled[actor].append(pygame.image.tostring(image, 'RGBA'))
        self.assertEqual(len(set(sampled['rhea'])), 1)
        for actor in ('lucan', 'caelan', 'mira'):
            self.assertGreater(len(set(sampled[actor])), 1)
        self.assertNotIn('caelan', self.scene.data['position_tracks'])

    def test_frozen_rhea_and_raised_shard_do_not_release_an_attack(self):
        self.scene.start()
        origin = tuple(self.scene.actor_position('rhea'))
        for time in (0., .9, 2.4, 3.4, 4.99):
            self.scene.elapsed = time
            self.assertEqual(tuple(self.scene.actor_position('rhea')), origin)
            self.assertEqual(self.scene.pose('ice_reaper'), 'charge')
        self.assertEqual(self.scene.data['dynamic_props']['glacial_shard']['position'], [510, 140])
        self.assertEqual(self.scene.data['dialogue'][0]['text'], 'Rhea! No!')

    def test_focus_and_pause_freeze_every_visual_clock(self):
        self.scene.start()
        self.scene.update(1.9)
        before = (self.scene.elapsed, self.scene.brush_progress,
                  tuple(self.scene.camera_position),
                  tuple(self.scene.actor_position('ice_reaper')))
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.scene.update(.4)
        self.assertEqual(before, (self.scene.elapsed, self.scene.brush_progress,
                                 tuple(self.scene.camera_position),
                                 tuple(self.scene.actor_position('ice_reaper'))))
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.scene.update(.4)
        self.assertEqual(self.scene.elapsed, before[0])

    def test_camera_establishes_then_finds_reaper_and_rhea(self):
        self.scene.elapsed = 1.
        self.assertEqual(self.scene.shot, 'frozen_field')
        self.assertEqual(self.scene.brush_progress, 1.)
        self.assertEqual(self.scene.camera_zoom, 1.)
        self.scene.elapsed = 2.5
        self.assertEqual(self.scene.shot, 'reaper_hold')
        self.assertEqual(self.scene.camera_zoom, 1.55)
        self.scene.elapsed = 4.2
        self.assertEqual(self.scene.shot, 'frozen_rhea')
        self.assertEqual(tuple(self.scene.camera_position), (100., 128.))
        self.assertEqual(self.scene.camera_zoom, 1.8)
        self.assertEqual(self.scene.dialogue['text'], 'Rhea! No!')

    def test_reduced_motion_uses_static_crops_without_shake_or_hover(self):
        self.game.audio.reduced_motion = True
        self.scene.elapsed = 1.8
        point = tuple(self.scene.camera_position)
        boss = tuple(self.scene.actor_position('ice_reaper'))
        self.scene.elapsed = 2.2
        self.assertEqual(tuple(self.scene.camera_position), point)
        self.assertEqual(tuple(self.scene.actor_position('ice_reaper')), boss)
        self.assertEqual(self.scene.camera_zoom, 1.55)

    def test_paused_frame_is_pixel_identical(self):
        self.scene.start()
        self.scene.update(1.9)
        canvas = pygame.Surface((480, 320))
        self.scene._draw_scene(canvas, self.scene.camera_position)
        self.scene._zoom(canvas, self.scene.camera_position)
        before = pygame.image.tobytes(canvas, 'RGB')
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.scene.update(.7)
        self.scene._draw_scene(canvas, self.scene.camera_position)
        self.scene._zoom(canvas, self.scene.camera_position)
        self.assertEqual(pygame.image.tobytes(canvas, 'RGB'), before)

    def test_rescue_pause_freezes_rendered_action_at_each_major_beat(self):
        self.scene.start()
        canvas = pygame.Surface((480, 320))
        for elapsed in (8.5, 13.8, 16.7, 19.5, 24.5, 27.9, 31.):
            with self.subTest(elapsed=elapsed):
                self.scene.elapsed = elapsed
                self.scene._draw_scene(canvas, self.scene.camera_position)
                before = pygame.image.tobytes(canvas, 'RGB')
                self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
                self.scene.update(.7)
                self.scene._draw_scene(canvas, self.scene.camera_position)
                self.assertEqual(pygame.image.tobytes(canvas, 'RGB'), before)
                self.assertEqual(self.scene.elapsed, elapsed)
                self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))

    def test_lucan_cover_line_follows_caelan_alarm(self):
        alarm, cover = self.scene.data['dialogue'][:2]
        self.assertEqual((alarm['speaker'], alarm['text']), ('Caelan', 'Rhea! No!'))
        self.assertEqual((cover['speaker'], cover['text']), ('Lucan', "Cael, go! I'll cover!"))
        self.assertGreaterEqual(cover['start'], alarm['end'])
        self.assertLessEqual(cover['end'], 7.)

    def test_mira_calls_the_intercept_as_the_rescue_orbit_reveals_her(self):
        self.scene.start()
        cue = self.scene.data['dialogue'][2]
        self.assertEqual((cue['speaker'], cue['text']),
                         ('Mira', 'Incoming! I got this one!'))
        self.assertEqual((cue['start'], cue['end']), (10.6, 12.8))
        self.assertIn('Mira', self.scene._dialogue_speakers)
        portrait = self.scene._dialogue_speakers['Mira']['portrait']
        self.assertIn(portrait, self.scene._dialogue_portraits)
        for time in (10.6, 11., 12.79):
            self.scene.elapsed = time
            self.assertEqual(self.scene.dialogue, cue)
        self.scene.elapsed = 12.8
        self.assertIsNone(self.scene.dialogue)

    def test_rhea_takes_control_and_interrupts_caelan_at_the_staff_sweep(self):
        self.assertEqual(len(self.scene.data['dialogue']), 5)
        rhea, caelan = self.scene.data['dialogue'][-2:]
        self.assertEqual((rhea['speaker'], rhea['text']),
                         ('Rhea', 'Thanks guys, now leave her to me...'))
        self.assertEqual((caelan['speaker'], caelan['text']),
                         ('Caelan', 'Rhea...are you su-'))
        self.assertEqual((rhea['start'], rhea['end']), (21.1, 23.15))
        self.assertEqual((caelan['start'], caelan['end']), (23.2, 24.))
        self.assertEqual(self.scene.data['speakers']['rhea']['portrait'], 'ice_reaper_rhea')
        self.assertEqual(self.scene.data['speakers']['rhea']['portrait_file'],
                         'portraits/rhea_awakening_shawl.png')
        for time, text in ((22., rhea['text']), (23.5, caelan['text'])):
            self.scene.elapsed = time
            self.assertEqual(self.scene.dialogue['text'], text)
        self.scene.elapsed = 24.
        self.assertIsNone(self.scene.dialogue)

    def test_charge_fades_without_extending_the_cinematic_clock(self):
        self.scene.elapsed = 31.1
        self.assertEqual(self.scene.fade_alpha, 0)
        self.scene.elapsed = 31.7
        self.assertGreater(self.scene.fade_alpha, 0)
        self.scene.elapsed = 32.
        self.assertEqual(self.scene.fade_alpha, 255)

    def test_invalid_duration_and_brush_direction_fail_explicitly(self):
        for field in ('duration', 'brush_direction', 'hover'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                data = copy.deepcopy(self.scene.data)
                if field == 'duration':
                    data['duration'] = 4.9
                elif field == 'brush_direction':
                    data['layers'][1]['brush_direction'] = []
                else:
                    data['hover'] = None
                path = Path(folder)/'scene.json'
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    IceReaperOpening(self.game, scene_path=path)


class IceReaperGalleryTests(unittest.TestCase):
    def setUp(self):
        from main import Game
        self.folder = tempfile.TemporaryDirectory(prefix='ice-reaper-tests-')
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name)
        self.path, self.settings = root/'journey.json', root/'settings.json'
        seed = Game(window_size=(960, 800), fullscreen=False, start_on_title=False,
                    save_path=self.path, settings_path=self.settings)
        self.assertTrue(seed.save_progress())
        seed.music.stop();seed.opening_audio.reset();seed.regional_audio.reset()
        self.parent = Game(window_size=(960, 800), fullscreen=False,
                           save_path=self.path, settings_path=self.settings)
        self.parent.audio.set_effects(0)
        pygame.event.clear()

    def tearDown(self):
        if self.parent.gallery_session is not None:
            self.parent.gallery_session.close(resume_music=False)
        self.parent.music.stop()
        self.parent.opening_audio.reset();self.parent.regional_audio.reset()
        self.parent = None
        pygame.quit()
        gc.collect()

    def launch(self):
        self.assertTrue(self.parent.open_gallery())
        self.assertTrue(self.parent.launch_gallery_scene('ice_reaper_opening'),
                        self.parent.gallery.error)
        return self.parent.gallery_session

    def key(self, key):
        self.parent.handle_events([
            pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False),
            pygame.event.Event(pygame.KEYUP, key=key)])

    def test_real_preview_finishes_at_thirty_two_seconds_without_mutating_the_journey(self):
        before = (self.path.read_bytes(), self.settings.read_bytes(),
                  self.parent._progress_signature(), self.parent.elapsed_ms,
                  tuple(self.parent.player.position), copy.deepcopy(self.parent.saved_journey),
                  self.parent.opening_cinematic)
        session = self.launch()
        self.assertIsInstance(session.game.opening_cinematic, IceReaperOpening)
        self.assertFalse(session.game.save_store.enabled)
        for frame in range(960):
            self.assertIs(self.parent.gallery_session, session, frame)
            self.assertEqual(session.game.music.desired_track, 'those_i_swore_to_save')
            self.parent.update(1/30, (1, 0), True)
        self.assertTrue(session.closed)
        self.assertIsNone(self.parent.gallery_session)
        self.assertTrue(self.parent.on_gallery)
        self.assertFalse(self.parent.combat.active)
        after = (self.path.read_bytes(), self.settings.read_bytes(),
                 self.parent._progress_signature(), self.parent.elapsed_ms,
                 tuple(self.parent.player.position), self.parent.saved_journey,
                 self.parent.opening_cinematic)
        self.assertEqual(before, after)

    def test_gallery_pause_focus_and_restart_preserve_the_preview_boundary(self):
        session = self.launch()
        self.parent.update(8.5, (0,0), False)
        self.key(pygame.K_p)
        self.parent.update(.5, (0,0), False)
        self.assertEqual(session.game.opening_cinematic.elapsed, 8.5)
        self.key(pygame.K_p)
        self.parent.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        self.parent.update(.5, (0,0), False)
        self.assertEqual(session.game.opening_cinematic.elapsed, 8.5)
        self.parent.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.key(pygame.K_r)
        replacement = self.parent.gallery_session
        self.assertIsNot(replacement, session)
        self.assertTrue(session.closed)
        self.assertEqual(replacement.game.opening_cinematic.elapsed, 0.)
        self.assertEqual(replacement.game.music.desired_track, 'those_i_swore_to_save')
        self.key(pygame.K_ESCAPE)
        self.assertIsNone(self.parent.gallery_session)
        self.assertTrue(self.parent.on_gallery)

    def test_large_caption_does_not_cover_the_rendered_frozen_character(self):
        self.parent.audio.text_scale = 2.
        session = self.launch()
        child, scene = session.game, session.game.opening_cinematic
        scene.elapsed = 4.2
        self.parent.draw()
        self.assertEqual(' '.join(scene.caption_lines), 'Rhea! No!')
        actor, anchor, frames, transitions = next(record for record in scene.actors
                                                 if record[0]['id'] == 'rhea')
        image = scene._actor_frame(actor['id'], frames, transitions)
        camera = scene.camera_position
        point = scene.actor_position(actor['id'])-camera
        unzoomed = pygame.Surface((480,320), pygame.SRCALPHA)
        scale = actor.get('pixel_scale', 1)
        image = pygame.transform.scale(image, (image.get_width()*scale, image.get_height()*scale))
        unzoomed.blit(image, (round(point.x-anchor[0]*scale), round(point.y-anchor[1]*scale)))
        zoom = scene.camera_zoom
        enlarged = pygame.transform.scale(unzoomed, (round(480*zoom), round(320*zoom)))
        rendered = pygame.Surface((480,320), pygame.SRCALPHA)
        rendered.blit(enlarged, (round(240*(1-zoom)), round(160*(1-zoom))))
        self.assertFalse(scene.caption_rect.colliderect(rendered.get_bounding_rect()))
