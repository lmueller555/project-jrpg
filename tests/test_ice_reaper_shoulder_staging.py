"""The approved fast retreat and shoulder sweep frame the same grounded cast.

Stage camera helpers below use the canonical action clock; the production
awakening segment runs one second later on the playback clock.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import json
from pathlib import Path
import unittest
import pygame
from ice_reaper_action import IceReaperActionStage as Stage

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT/'docs/reviews/ice_reaper_guard_correction/scope_baseline.json'

class ShoulderStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((480, 320))
        cls.stage = Stage(ROOT/'assets/story/ice_reaper_rescue', strict=True)
        cls.baseline = json.loads(BASELINE.read_text())

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_earlier_camera_matches_recorded_samples_before_replaced_awakening(self):
        for sample in self.baseline['camera']:
            time = sample[0]
            if time >= 15.1:
                continue
            camera = Stage.camera(time)
            current = [time, list(camera.position), list(camera.target), camera.focal, list(camera.center)]
            self.assertEqual(current, sample, f'Camera changed at {time}')

    def test_rise_begins_after_release_and_settles_before_shoulder_sweep(self):
        original = pygame.Vector3(2, 6.6, -8)
        for time in (0., 5., 9., 14.7, 16.29, 16.3):
            self.assertEqual(Stage.reaper_position(time), original)
        heights = [Stage.reaper_position(time).y for time in (16.3, 16.45, 16.65, 16.8, 16.95)]
        self.assertEqual(heights, sorted(heights))
        settled = Stage.reaper_position(16.95)
        self.assertGreater(settled.y, original.y+2.)
        self.assertGreater(settled.distance_to(original), 2.5)
        for time in (16.95, 17.5, 18.3, 19., 19.8, 20.):
            self.assertEqual(Stage.reaper_position(time), settled)

    def test_reposition_leaves_other_characters_in_place(self):
        # Lucan now plants at the revised forward-shield interception point.
        # Raising the Reaper must not move him out of that settled guard.
        guard_position = Stage.actor_positions(9.7)['lucan']
        guard_heading = Stage.actor_heading('lucan',9.7)
        for value in self.baseline['lucan_end']:
            time = float(value)
            self.assertEqual(Stage.actor_positions(time)['lucan'], guard_position)
            self.assertEqual(Stage.actor_heading('lucan',time), guard_heading)
        for time in (16.3, 17., 18.15, 19.8):
            positions = Stage.actor_positions(time)
            self.assertEqual(positions['rhea'], pygame.Vector3(-3,0,0))
            self.assertEqual(positions['mira'], pygame.Vector3(7,0,10))
            self.assertEqual(positions['caelan'], pygame.Vector3(-5.3,0,-.7))

    def test_lower_body_is_naturally_outside_ending_viewport(self):
        for time in (16.95, 18.1, 19.25):
            camera = self.stage.camera(time)
            position = self.stage.actor_positions(time)['ice_reaper']
            image, data = self.stage._approved_boss_frame(camera, position, time)
            lower = image.copy()
            lower.fill((0,0,0,0), (0,0,image.get_width(),110))
            canvas = pygame.Surface((480,320),pygame.SRCALPHA)
            self.stage._projected_boss(canvas,lower,data,position,camera)
            self.assertEqual(pygame.mask.from_surface(canvas).count(),0,
                             f'Lower torso/legs visible at {time}')

    def test_shoulder_edges_leave_rhea_readable(self):
        for time in (16.95, 19.25):
            camera = self.stage.camera(time)
            canvas = pygame.Surface((480,320),pygame.SRCALPHA)
            self.stage._foreground_boss(canvas,camera,time)
            mask = pygame.mask.from_surface(canvas)
            self.assertGreater(mask.count(),1000)
            head = camera.project(self.stage.actor_positions(time)['rhea']+pygame.Vector3(0,1.6,0))
            body = pygame.Rect(round(head[0]-7),round(head[1]-4),14,31)
            visible = mask.overlap_area(pygame.mask.Mask(body.size,fill=True),body.topleft)
            self.assertEqual(visible,0,f'Reaper obstructs Rhea at shoulder edge {time}')

    def test_only_brief_central_occlusion_during_the_sweep(self):
        any_occlusion = 0
        substantial_occlusion = 0
        for frame in range(1017,1156):
            time = frame/60
            camera = self.stage.camera(time)
            head = camera.project(self.stage.actor_positions(time)['rhea']+pygame.Vector3(0,1.6,0))
            body = pygame.Rect(round(head[0]-7),round(head[1]-4),14,31)
            layer = pygame.Surface((480,320),pygame.SRCALPHA)
            self.stage._foreground_boss(layer,camera,time)
            covered = pygame.mask.from_surface(layer).overlap_area(
                pygame.mask.Mask(body.size,fill=True),body.topleft)
            if covered:
                any_occlusion += 1
                self.assertTrue(17.4 < time < 18.85)
            if covered > body.width*body.height*.5:
                substantial_occlusion += 1
        self.assertLessEqual(any_occlusion/60,.6)
        self.assertLessEqual(substantial_occlusion/60,.3)

if __name__ == '__main__':
    unittest.main()
