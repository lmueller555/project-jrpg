"""Opening interaction, signal-camera and departure contracts with runtime art."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from audio_settings import AudioSettings
from opening_cinematic import OpeningCinematic
from ui_style import UIStyle


class OpeningBeaconTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((960, 640)),
                                    audio=AudioSettings(), _music_focused=True)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = lambda point: (point[0]/2, point[1]/2)
        self.canvas = pygame.Surface((480, 320))
        self.ui = pygame.Surface((960, 640))
        self.scene = OpeningCinematic(self.game)
        self.scene.start()
        self.events = self.scene.data['events']

    def tearDown(self):
        pygame.quit()

    def at(self, seconds):
        self.scene.elapsed = seconds
        return self.scene

    def line(self, identifier):
        return next(record for record in self.scene.data['dialogue']
                    if record['id'] == identifier)

    def render(self):
        self.scene.draw(self.canvas, self.ui)
        return pygame.image.tobytes(self.canvas, 'RGB')

    def test_free_hands_are_held_before_mira_speaks_and_released_before_work(self):
        line = self.line('understood_problem')
        self.assertIn('Your hands stopped shaking.', line['text'])
        self.assertLess(self.events['cup_set_down'], self.events['hand_reach'])
        self.assertLess(self.events['hand_reach'], self.events['hand_hold'])
        self.assertLessEqual(self.events['hand_hold'], line['start'])
        self.assertGreaterEqual(self.events['hand_release'], line['end'])
        self.assertLess(self.events['hand_release'], self.events['lamp_walk_start'])
        self.assertFalse(self.at(self.events['cup_set_down']-.05).cup_visible)
        self.assertTrue(self.at(self.events['hand_hold']).cup_visible)

        self.at(line['start']+.01)
        held_poses = (self.scene.pose('caelan'), self.scene.pose('mira'))
        self.assertEqual(held_poses, ('hands_hold', 'hands_hold'))
        for actor, _, _, transitions in self.scene.actors:
            contact_seconds = sum(duration for _, duration in
                                  transitions.get('hands_reach:hands_hold', ()))
            self.assertLessEqual(self.events['hand_hold']+contact_seconds, line['start'],
                                 actor['id'])
        separation = self.scene.actor_position('caelan').distance_to(
            self.scene.actor_position('mira'))
        self.assertTrue(15 < separation < 75, separation)
        self.at(line['end']-.01)
        self.assertEqual((self.scene.pose('caelan'), self.scene.pose('mira')), held_poses)
        self.assertTrue(self.scene.cup_visible)

    def test_mira_walks_to_the_lamp_before_incremental_repairs(self):
        start = self.at(self.events['lamp_walk_start']).actor_position('mira').copy()
        working = self.at(self.events['lamp_work_start']).actor_position('mira').copy()
        self.assertGreater(start.distance_to(working), 90)
        self.assertLess(working.x, start.x)
        self.assertLess(self.events['lamp_work_start'], self.events['flare_launch'])
        self.assertLess(self.at(self.events['lamp_work_start']).lamp_stage, 3)
        cues = self.scene.data['dynamic_props']['lamp']['stage_cues']
        observed = {self.at(cue['start']+.01).lamp_stage for cue in cues}
        self.assertEqual(observed, {0, 1, 2, 3})
        stages = self.scene._prop_art['lamp']
        self.assertEqual(len({pygame.image.tobytes(image, 'RGBA') for image in stages}), 4)

    def test_lamp_completion_waits_for_the_returned_camera_and_completion_line(self):
        returned = self.events['camera_returned']
        complete = self.line('so_do_i')
        self.assertIn("Don't break on me now.", complete['text'])
        self.assertLessEqual(self.events['camera_return_start'], returned)
        self.assertLessEqual(returned, complete['start'])
        self.assertEqual(self.events['lamp_restored'], complete['start'])
        self.assertLess(self.at(returned-.01).lamp_stage, 3)
        self.assertTrue(self.at(returned+.001).camera_settled)
        self.assertEqual(self.at(self.events['lamp_restored']+.001).lamp_stage, 3)
        self.assertEqual(self.scene.dialogue['id'], 'so_do_i')

        # An early completion request cannot defeat the shot/line barrier.
        cues = self.scene.data['dynamic_props']['lamp']['stage_cues']
        original = [dict(cue) for cue in cues]
        early = (self.events['flare_launch']+self.events['flare_burst'])/2
        try:
            cues.append({'start': early, 'stage': 3})
            cues.sort(key=lambda cue: cue['start'])
            self.assertLess(self.at(early+.001).lamp_stage, 3)
            self.assertEqual(self.at(self.events['lamp_restored']+.001).lamp_stage, 3)
        finally:
            cues[:] = original

        # The matching spoken completion is held by the same camera barrier.
        original_times = complete['start'], complete['end']
        try:
            complete['start'], complete['end'] = early, early+1
            self.assertIsNone(self.at(early+.01).dialogue)
        finally:
            complete['start'], complete['end'] = original_times

    def test_camera_follows_the_flying_signal_and_glimmer_persists_after_the_burst(self):
        launch, burst = self.events['flare_launch'], self.events['flare_burst']
        ground = self.at(launch-.001).camera_position.copy()
        self.assertEqual(self.at(launch-.001).flare_phase, 'charging')
        for fraction in (.01, .25, .5, .75, .99):
            scene = self.at(launch+(burst-launch)*fraction)
            self.assertEqual(scene.flare_phase, 'flight')
            point = scene.flare_position-scene.camera_position
            self.assertTrue(0 <= point.x <= 480 and 0 <= point.y <= 320,
                            (fraction, point))
        self.assertLess(self.scene.camera_position.y, ground.y)
        self.assertEqual(self.at(burst+.01).flare_phase, 'burst')
        self.assertTrue(self.at(self.events['flare_glimmer']+.01).glimmer_visible)
        self.assertTrue(self.at(self.events['camera_returned']+.01).glimmer_visible)
        self.assertTrue(self.at(self.scene.duration-.02).glimmer_visible)

    def test_departure_follows_then_centers_the_foreground_memorial_and_stops(self):
        departure, centered = self.events['departure_start'], self.events['memorial_centered']
        offscreen, zoom = self.events['actors_offscreen'], self.events['helmet_zoom_start']
        self.assertLess(departure, centered)
        self.assertLess(centered, offscreen)
        self.assertLessEqual(offscreen, zoom)
        self.assertFalse(self.at(departure-.01).memorial_visible)
        start_camera = self.at(departure).camera_position.copy()
        start_actors = {actor: self.scene.actor_position(actor).copy()
                        for actor in ('caelan', 'mira')}
        self.assertTrue(self.at(departure+.01).memorial_visible)
        camera = self.at(centered+.001).camera_position.copy()
        self.assertLess(camera.x, start_camera.x)
        memorial = pygame.Vector2(self.scene.data['dynamic_props']['memorial']['position'])
        self.assertAlmostEqual(memorial.x-camera.x, 240, delta=1)
        for time in (centered+.01, (centered+offscreen)/2, offscreen):
            self.at(time)
            self.assertEqual(self.scene.camera_position, camera)
            for actor in start_actors:
                self.assertLess(self.scene.actor_position(actor).x, start_actors[actor].x)
        self.at(offscreen)
        for actor in start_actors:
            # Entire96px actor canvases have left the fixed viewport.
            self.assertLess(self.scene.actor_position(actor).x-camera.x+48, 0)

    def test_departure_moves_twenty_percent_faster_with_the_same_spacing_and_gait(self):
        departure = self.events['departure_start']
        duration = self.events['actors_offscreen']-departure
        self.assertAlmostEqual(duration, 15.5/1.2, places=5)
        for actor in ('caelan', 'mira'):
            before = self.at(departure+1).actor_position(actor).copy()
            after = self.at(departure+2).actor_position(actor).copy()
            self.assertAlmostEqual(before.x-after.x, 48, places=4)
            self.assertAlmostEqual(before.y, after.y)
            self.assertEqual([duration for _, duration in self.scene._actor_loops[actor]['walk_left']],
                             [.18, .18, .18, .18])
            _, _, frames, transitions = next(record for record in self.scene.actors
                                             if record[0]['id'] == actor)
            self.at(departure+.01)
            first = self.scene._actor_frame(actor, frames, transitions)
            self.at(departure+.17)
            self.assertIs(self.scene._actor_frame(actor, frames, transitions), first)
            self.at(departure+.19)
            self.assertIsNot(self.scene._actor_frame(actor, frames, transitions), first)
            self.at(departure+.73)
            self.assertIs(self.scene._actor_frame(actor, frames, transitions), first)
        for fraction in (0, .25, .5, .75, 1):
            self.at(departure+duration*fraction)
            gap = self.scene.actor_position('caelan')-self.scene.actor_position('mira')
            self.assertAlmostEqual(gap.x, 85)
            self.assertAlmostEqual(gap.y, 0)

    def test_departure_camera_and_ending_retime_together_without_rushing_the_memorial(self):
        departure = self.events['departure_start']
        centered = self.events['memorial_centered']
        self.assertAlmostEqual(centered-departure, 7/1.2, places=5)
        start = self.at(departure).camera_position.copy()
        middle = self.at((departure+centered)/2).camera_position.copy()
        end = self.at(centered).camera_position.copy()
        self.assertEqual((start, end), (pygame.Vector2(435, 160), pygame.Vector2(155, 160)))
        self.assertAlmostEqual(middle.x, (start.x+end.x)/2)
        self.assertEqual(middle.y, 160)
        self.assertAlmostEqual(self.events['helmet_zoom_start']-self.events['actors_offscreen'], .5)
        self.assertAlmostEqual(self.scene.duration-self.events['helmet_zoom_start'], 10)
        self.assertAlmostEqual(self.events['fade_start']-self.events['helmet_zoom_start'], 1.5)
        self.assertAlmostEqual(self.scene.duration, 252.566667, places=5)

    def test_earlier_lamp_approach_keeps_its_authored_speed(self):
        # The pace adjustment belongs to the final departure, not Mira's
        # earlier movement into the repair scene or a global animation clock.
        self.assertEqual(self.events['lamp_walk_start'], 180.8)
        before = self.at(182).actor_position('mira').copy()
        after = self.at(183).actor_position('mira').copy()
        self.assertAlmostEqual(before.x-after.x, 40)
        self.assertAlmostEqual(before.y, after.y)

    def test_zoom_waits_for_the_exit_and_fully_fades_the_helmet_shot(self):
        zoom, fade = self.events['helmet_zoom_start'], self.events['fade_start']
        self.assertEqual(self.at(zoom-.01).camera_zoom, 1)
        self.assertGreater(self.at((zoom+self.scene.duration)/2).camera_zoom, 1)
        self.assertGreaterEqual(fade, zoom)
        self.at(zoom+.01)
        self.render()
        before = sum(pygame.transform.average_color(self.ui, (120, 100, 720, 420))[:3])
        self.at(self.scene.duration-.001)
        self.render()
        after = sum(pygame.transform.average_color(self.ui, (120, 100, 720, 420))[:3])
        self.assertLess(after, before)
        self.assertEqual(self.scene.fade_alpha, 255)
        # The shared UI veil uses the game's dark green, rather than literal
        # black. Its opaque final cover must hide every part of the picture.
        self.assertEqual(len({self.ui.get_at(point)[:3] for point in
                              ((150, 120), (480, 280), (800, 490))}), 1)

    def test_the_memorial_draws_in_front_of_characters_passing_behind_it(self):
        self.at(self.events['memorial_centered']+.01)
        record = self.scene.data['dynamic_props']['memorial']
        art = self.scene._prop_art['memorial']
        # Choose an opaque pixel in the helmet/upper blade, above near rubble.
        point = next(pygame.Vector2(x, y)
                     for y in range(art.get_height()//2)
                     for x in range(art.get_width())
                     if art.get_at((x, y)).a == 255)
        screen = (pygame.Vector2(record['position'])-record['anchor']
                  +point-self.scene.camera_position)
        screen = (round(screen.x), round(screen.y))
        self.assertTrue(pygame.Rect(0, 0, 480, 320).collidepoint(screen))

        def actor_behind(canvas, camera):
            canvas.fill('#03f717')

        # A solid actor silhouette deliberately overlaps the chosen pixel;
        # the foreground prop must still own it after the actual draw pass.
        with patch.object(self.scene, '_draw_actors', actor_behind):
            self.render()
        expected = art.get_at((round(point.x), round(point.y)))
        self.assertEqual(self.canvas.get_at(screen)[:3], expected[:3])

    def test_escape_freezes_every_new_stage_including_particles_walks_and_zoom(self):
        samples = [self.events['hand_hold']+.1, self.events['lamp_work_start']+.5,
                   (self.events['flare_launch']+self.events['flare_burst'])/2,
                   self.events['flare_burst']+.1,
                   (self.events['departure_start']+self.events['memorial_centered'])/2,
                   self.events['helmet_zoom_start']+1]
        for time in samples:
            with self.subTest(time=time):
                self.scene.paused = False
                self.at(time)
                self.scene.handle_event(pygame.event.Event(
                    pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
                before = self.render()
                state = (self.scene.elapsed, self.scene.camera_position.copy(),
                         self.scene.camera_zoom, self.scene.flare_phase, self.scene.lamp_stage,
                         tuple(self.scene.actor_position('caelan')),
                         tuple(self.scene.actor_position('mira')))
                self.scene.update(5)
                self.assertEqual(self.render(), before)
                self.assertEqual((self.scene.elapsed, self.scene.camera_position,
                                  self.scene.camera_zoom, self.scene.flare_phase, self.scene.lamp_stage,
                                  tuple(self.scene.actor_position('caelan')),
                                  tuple(self.scene.actor_position('mira'))), state)

    def test_sky_and_helmet_stages_can_be_skipped_once_while_paused(self):
        for time in (self.events['flare_burst']+.1, self.events['helmet_zoom_start']+1):
            with self.subTest(time=time):
                calls = []
                self.scene.start(lambda: calls.append('finished'))
                self.at(time)
                self.scene.paused = True
                self.render()
                point = self.scene.skip_rect.center
                self.scene.handle_event(pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, button=1, pos=(point[0]*2, point[1]*2)))
                self.scene.skip()
                self.assertEqual(calls, ['finished'])
                self.assertFalse(self.scene.active)
                self.assertFalse(self.scene.paused)

    def test_reduced_motion_keeps_sky_shots_static_and_retains_story_outcomes(self):
        self.game.audio.set_reduced_motion(True)
        self.at(self.events['lamp_work_start']+.5)
        working = self.render()
        self.at(self.events['lamp_work_start']+.6)
        self.assertEqual(self.render(), working)
        flight = (self.events['flare_launch']+self.events['flare_burst'])/2
        camera = self.at(flight).camera_position.copy()
        self.at(flight+.1)
        self.assertEqual(self.scene.camera_position, camera)
        glimmer = self.events['flare_glimmer']+.1
        self.at(glimmer)
        image = self.render()
        self.at(glimmer+.1)
        self.assertEqual(self.render(), image)
        self.assertTrue(self.scene.glimmer_visible)
        self.assertEqual(self.at(self.events['lamp_restored']+.01).lamp_stage, 3)
        self.assertEqual(self.at(self.events['helmet_zoom_start']+1).camera_zoom, 1)

        # Essential locomotion keeps its authored gait instead of sliding a
        # frozen standing pose while the optional camera/ambient motion stops.
        _, _, frames, transitions = next(actor for actor in self.scene.actors
                                         if actor[0]['id'] == 'caelan')
        self.at(self.events['departure_start']+.01)
        first = self.scene._actor_frame('caelan', frames, transitions)
        first_duration = self.scene._actor_loops['caelan']['walk_left'][0][1]
        self.at(self.events['departure_start']+first_duration+.01)
        self.assertIsNot(self.scene._actor_frame('caelan', frames, transitions), first)


if __name__ == '__main__':
    unittest.main()
