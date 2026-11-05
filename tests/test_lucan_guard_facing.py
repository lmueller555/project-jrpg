"""The approved orbit guard and dash survive the forward intercept revision."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import hashlib
import json
from pathlib import Path
import unittest

import pygame

from ice_reaper_action import IceReaperActionStage


ROOT = Path(__file__).resolve().parents[1]
# Actual pixel-art head landmarks: back of helmet/hair and the nose/face edge.
# The atlas suffixes were previously assigned the opposite stage view sign.
FACES = {
    'hold_brace_right': ((60, 63), (70, 65)),
    'hold_brace_left': ((69, 63), (61, 65)),
}
SHIELDS = {
    'hold_brace_right': ((65, 65), (80, 57)),
    'hold_brace_left': ((67, 65), (44, 62)),
}


class LucanGuardFacingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((480, 320))
        cls.stage = IceReaperActionStage(ROOT/'assets/story/ice_reaper_rescue', strict=True)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def sample(self, time):
        stage = self.stage
        positions = stage.actor_positions(time)
        camera = stage.camera(time)
        action, local, duration = stage._action('lucan', time)
        key = stage.sequence_key('lucan', action, local, duration, camera,
                                 positions['lucan'], time)
        image, data = stage._sequence('lucan', action, local, duration, camera,
                                      positions['lucan'], time=time)
        return key, image, data, camera, positions

    def test_held_profiles_face_the_reaper_instead_of_rhea_at_both_ends_of_the_orbit(self):
        # The near-frontal quarter views have ambiguous nose/shield normals in
        # two dimensions; verify the unambiguous profiles rather than infer a
        # threat direction from the shield's equipment-hand placement alone.
        for time in (9.7, 9.8, 9.9, 10.9, 11.):
            with self.subTest(time=time):
                key, image, _, camera, positions = self.sample(time)
                self.assertIn(key, FACES)
                nape, nose = FACES[key]
                self.assertGreater(image.get_at(nape).a, 0)
                self.assertGreater(image.get_at(nose).a, 0)
                guard = camera.project(positions['lucan'])
                threat = camera.project(positions['ice_reaper'])
                protected = camera.project(positions['rhea'])
                face_sign = nose[0]-nape[0]
                self.assertGreater(face_sign*(threat[0]-guard[0]), 0)
                self.assertLess(face_sign*(protected[0]-guard[0]), 0)

    def test_profile_shield_is_raised_on_the_threat_side_of_his_head(self):
        for time in (9.7, 9.8, 9.9, 10.9, 11.):
            key, image, _, camera, positions = self.sample(time)
            self.assertIn(key, SHIELDS)
            head, shield = SHIELDS[key]
            self.assertGreater(image.get_at(head).a, 0)
            self.assertGreater(image.get_at(shield).a, 0)
            self.assertLess(shield[1], head[1])
            guard = camera.project(positions['lucan'])
            threat = camera.project(positions['ice_reaper'])
            self.assertGreater((shield[0]-head[0])*(threat[0]-guard[0]), 0)

    def asset_digest(self, pattern):
        result = hashlib.sha256()
        folder = ROOT/'assets/story/ice_reaper_continuity/actors/lucan'
        for path in sorted(folder.glob(pattern)):
            result.update(path.name.encode()+b'\0'+path.read_bytes())
        return result.hexdigest()

    def test_dash_drawings_and_timing_stay_intact_while_the_intercept_is_revised(self):
        # The new request intentionally replaces brace/impact drawings and may
        # adjust the dash destination to put the forward shield on the ray.
        # Preserve the actual approved dash artwork and its timing instead of
        # requiring the obsolete overhead interception images to remain.
        self.assertEqual(self.asset_digest('dash_rear_*.png'),
                         'ab56cced695de5611b3edf38daf89a9b07dd75072b8ea95c6b5ec8f702357033')
        for time in (7.02,7.2,7.49):
            self.assertEqual(self.stage._action('lucan',time)[0], 'dash')
            self.assertEqual(self.stage._action('lucan',time)[2], .48)
        self.assertEqual(self.stage._action('lucan',7.5)[0], 'brace')
        # The earlier0–5s opening uses an unchanged combat frame, outside this atlas.
        opening = ROOT/'assets/story/ice_reaper_opening/actors/lucan/stand.png'
        combat = ROOT/'assets/combat/lucan/idle_01.png'
        self.assertEqual(opening.read_bytes(), combat.read_bytes())

    def test_approved_orbit_art_is_unchanged_and_authored_frames_match_provenance(self):
        self.assertEqual(self.asset_digest('hold_brace_*.png'),
                         'a175db2725b88e34a3139fc37bd6916fabe2b209d28441b4bbec9d99ffa683ea')
        folder = ROOT/'assets/story/ice_reaper_continuity/actors/lucan'
        provenance = json.loads((folder/'provenance.json').read_text())
        for record in provenance['frames']:
            self.assertEqual(hashlib.sha256((folder/record['file']).read_bytes()).hexdigest(),
                             record['sha256'])
        entries = self.stage.actors['lucan']['manifest']['animations']
        self.assertEqual(entries['dash_rear']['view_azimuth_deg'], 160)
        self.assertEqual(entries['brace_rear_left']['view_azimuth_deg'], -120)
        self.assertEqual(entries['impact_rear_left']['view_azimuth_deg'], -110)
        self.assertEqual(entries['hold_brace_right']['view_azimuth_deg'], -90)
        self.assertEqual(entries['hold_brace_left']['view_azimuth_deg'], 90)

    def test_duel_hold_keeps_the_enemy_facing_rear_view_until_the_wind_hits(self):
        for time in (21., 21.5, 22., 23., 24., 24.17):
            positions = self.stage.duel.actor_positions(time)
            camera = self.stage.duel.camera(time)
            image, _, key = self.stage.duel._image('lucan', camera, positions['lucan'], time)
            self.assertEqual(key, 'hold_brace_rear')
            expected = self.stage.actors['lucan']['sequences']['hold_brace_rear'][0][0]
            self.assertIs(image, expected)
            heading = self.stage.duel.headings(time)['lucan']
            to_enemy = positions['ice_reaper']-positions['lucan']
            to_enemy.y = 0
            # He remains aimed at the first shard's release point, slightly
            # offset from the Reaper's root position used by this projection.
            self.assertGreater(heading.dot(to_enemy.normalize()), .98)


if __name__ == '__main__':
    unittest.main()
