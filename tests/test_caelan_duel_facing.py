"""Caelan keeps the threat in view while the existing gust carries him right."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import hashlib
import json
import math
from pathlib import Path
import unittest

import pygame

from ice_reaper_action import IceReaperActionStage
from ice_reaper_duel import IceReaperDuel


ROOT = Path(__file__).resolve().parents[1]
GUST_START = 24.12
FLIGHT_START = 24.3246
LANDING_START = 24.8175
LANDING_END = 25.05


def flat_direction(vector):
    result = pygame.Vector3(vector)
    result.y = 0
    return result.normalize()


def rounded(value):
    # Quantize insignificant platform math differences in the recorded camera
    # and blocking contract; a visible staging change is many orders larger.
    if isinstance(value, float):
        return round(value, 9)
    if isinstance(value, (list, tuple)):
        return [rounded(item) for item in value]
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    return value


class CaelanDuelFacingGeometryTests(unittest.TestCase):
    def initial_heading(self):
        positions = IceReaperDuel.actor_positions(21.)
        return flat_direction(positions['ice_reaper']-positions['caelan'])

    def landing_heading(self):
        boss = IceReaperDuel.actor_positions(21.)['ice_reaper']
        return flat_direction(boss-pygame.Vector3(4.6, 0, 10.2))

    def test_dialogue_and_initial_crosswind_hit_keep_his_torso_toward_the_reaper(self):
        expected = self.initial_heading()
        times = [frame/60 for frame in range(1260, 1460)]
        times += [21.1, 21.5, 22., 23.5, 24., GUST_START, FLIGHT_START]
        for elapsed in times:
            with self.subTest(elapsed=elapsed):
                heading = IceReaperDuel.headings(elapsed)['caelan']
                self.assertGreater(heading.dot(expected), 1-1e-9)

    def test_gust_and_flight_handoffs_have_no_orientation_jump(self):
        for boundary in (24., GUST_START, FLIGHT_START, LANDING_START, LANDING_END):
            with self.subTest(boundary=boundary):
                before = IceReaperDuel.headings(boundary-1e-6)['caelan']
                after = IceReaperDuel.headings(boundary+1e-6)['caelan']
                self.assertLess(before.distance_to(after), 1e-5)

    def test_airborne_turn_progresses_to_a_fixed_landing_heading_without_reversing(self):
        destination = self.landing_heading()
        previous = IceReaperDuel.headings(FLIGHT_START)['caelan']
        previous_error = previous.angle_to(destination)
        for frame in range(1460, 1490):
            elapsed = frame/60
            heading = IceReaperDuel.headings(elapsed)['caelan']
            error = heading.angle_to(destination)
            with self.subTest(elapsed=elapsed):
                self.assertLessEqual(error, previous_error+1e-7)
                self.assertGreater(heading.dot(previous), math.cos(math.radians(5)))
            previous, previous_error = heading, error
        self.assertGreater(IceReaperDuel.headings(LANDING_START)['caelan'].dot(destination),
                           1-1e-9)

    def test_landing_heading_stays_fixed_when_the_reaper_later_charges(self):
        expected = self.landing_heading()
        for elapsed in (LANDING_START, LANDING_END, 25.15, 26.7, 29.15, 30.3, 31., 31.65, 32.):
            with self.subTest(elapsed=elapsed):
                self.assertGreater(IceReaperDuel.headings(elapsed)['caelan'].dot(expected),
                                   1-1e-9)

    def test_existing_gust_still_moves_him_right_toward_mira(self):
        camera = IceReaperDuel.camera(24.)
        start = IceReaperDuel.actor_positions(GUST_START)['caelan']
        initial_screen = camera.project(start)
        for elapsed in (24.3, 24.5, 24.7):
            with self.subTest(elapsed=elapsed):
                position = IceReaperDuel.actor_positions(elapsed)['caelan']
                self.assertGreater(camera.project(position)[0], initial_screen[0])
                self.assertGreater(position.y, 0)
        landed = IceReaperDuel.actor_positions(LANDING_END)
        self.assertEqual(landed['caelan'], pygame.Vector3(4.6, 0, 10.2))
        self.assertLess(landed['caelan'].distance_to(landed['mira']), 3.)

    def test_all_camera_paths_positions_and_other_actor_headings_remain_approved(self):
        # Recorded before this change from approved c799726. Every duel frame
        # protects the entire cast's translation, both camera modes, and the
        # headings of everyone except Caelan; only his orientation may change.
        result = hashlib.sha256()
        for frame in range(1260, 1920):
            elapsed = frame/60
            camera = IceReaperDuel.camera(elapsed)
            reduced = IceReaperDuel.camera(elapsed, True)
            record = dict(frame=frame,
                camera=[list(camera.position), list(camera.target), camera.focal, list(camera.center)],
                reduced_camera=[list(reduced.position), list(reduced.target), reduced.focal,
                                list(reduced.center)],
                positions={actor: list(point)
                           for actor, point in IceReaperDuel.actor_positions(elapsed).items()},
                headings={actor: list(point)
                          for actor, point in IceReaperDuel.headings(elapsed).items()
                          if actor != 'caelan'})
            result.update((json.dumps(rounded(record), sort_keys=True,
                                      separators=(',', ':'))+'\n').encode())
        self.assertEqual(result.hexdigest(),
                         'a34b53e978b0e8ef083cf84368df0ed270feed9938c73fbca3021610366bc57a')


class CaelanDuelFacingDrawingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((480, 320))
        cls.stage = IceReaperActionStage(ROOT/'assets/story/ice_reaper_rescue', strict=True)
        cls.duel = cls.stage.duel

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_dialogue_uses_the_reviewed_enemy_facing_rear_quarter_drawing(self):
        expected = self.stage.actors['caelan']['sequences']['ready_rear_right'][0][0]
        for elapsed in (21., 21.1, 21.5, 22., 23.5, 24., 24.119):
            with self.subTest(elapsed=elapsed):
                positions = self.duel.actor_positions(elapsed)
                camera = self.duel.camera(elapsed)
                image, _, key = self.duel._image('caelan', camera, positions['caelan'], elapsed)
                # This unmirrored quarter view shows his nape and rightward
                # gaze; Rhea and the Reaper are on his screen-right here.
                self.assertEqual(key, 'ready_rear_right')
                self.assertIs(image, expected)

    def test_initial_gust_uses_a_rear_view_instead_of_the_old_left_facing_hit(self):
        for elapsed in (GUST_START, 24.2, 24.3):
            with self.subTest(elapsed=elapsed):
                positions = self.duel.actor_positions(elapsed)
                camera = self.duel.camera(elapsed)
                _, _, key = self.duel._image('caelan', camera, positions['caelan'], elapsed)
                self.assertTrue(key.startswith('wind_hit_'))
                entry = self.duel.authored['caelan'][key]
                azimuth = self.duel._azimuth('caelan', camera, positions['caelan'], elapsed)
                self.assertGreaterEqual(abs(entry['angle']), 120.)
                self.assertLess(abs((azimuth-entry['angle']+180)%360-180), 50.)

    def test_earlier_rescue_and_awakening_drawings_and_registration_stay_unchanged(self):
        result = hashlib.sha256()
        for frame in range(300, 1260):
            actual = frame/60
            if actual < 15.1:
                time = actual
                camera = self.stage.camera(time)
            else:
                local = self.stage.awakening.local_time(actual)
                time = self.stage.awakening.canonical_time(local)
                camera = self.stage.awakening.camera(local)
            position = self.stage.actor_positions(time)['caelan']
            action, local, duration = self.stage._action('caelan', time)
            key = self.stage.sequence_key('caelan', action, local, duration, camera,
                                          position, time)
            image, data = self.stage._sequence('caelan', action, local, duration, camera,
                                               position, time=time)
            result.update(f'{frame}:{key}:{data["anchor"]}:{data["body_pixels"]}:'.encode())
            result.update(pygame.image.tobytes(image, 'RGBA'))
        self.assertEqual(result.hexdigest(),
                         '303406762967896d3537d1c30eb521c98f2eb84d2baa7fb87cddd1ce90f8e3b3')


if __name__ == '__main__':
    unittest.main()
