"""Rhea's winter wardrobe persists while authored hair and cloth begin flowing."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from pathlib import Path
import unittest

import pygame
import numpy as np

from ice_reaper_action import IceReaperActionStage
from rhea_winter import VIEWS, EXPRESSIONS


ROOT = Path(__file__).resolve().parents[1]


class RheaWinterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((480, 320))
        cls.stage = IceReaperActionStage(ROOT/'assets/story/ice_reaper_rescue', strict=True)
        cls.winter = cls.stage.winter

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_all_camera_views_have_registered_resting_and_animated_energy_art(self):
        self.assertEqual(set(self.winter.rested), VIEWS)
        self.assertEqual(set(self.winter.energy), VIEWS)
        self.assertEqual(set(self.winter.expressions), EXPRESSIONS)
        self.assertEqual(self.winter.opening.get_size(), (64, 64))
        self.assertEqual(self.winter.data, dict(anchor=(64, 116), body_pixels=82))
        for name, sequence in self.winter.energy.items():
            with self.subTest(view=name):
                self.assertGreaterEqual(len(sequence), 6)
                self.assertTrue(all(image.get_size() == (128, 128) for image,_ in sequence))
                self.assertGreaterEqual(len({pygame.image.tobytes(image, 'RGBA')
                                             for image,_ in sequence}), 4)

    def test_frozen_clothing_is_static_and_energy_begins_at_the_visible_shatter(self):
        first, _, name = self.winter.hold(0., 5.)
        self.assertTrue(name.startswith('winter_rested_'))
        for time in (8.5, 15.1, 17.299):
            self.assertIs(self.winter.hold(0., time)[0], first)
        image, _, name = self.winter.hold(0., 17.3)
        self.assertTrue(name.startswith('winter_energy_front_'))
        self.assertIs(image, self.winter.energy['front'][0][0])

    def test_opening_contains_a_complete_body_without_detached_second_figure(self):
        alpha = pygame.surfarray.array_alpha(self.winter.opening) > 0
        rows = np.flatnonzero(alpha.any(axis=0))
        # The old contaminated export measured 41px overall but contained a
        # much shorter body and a detached head/staff below its feet.
        np.testing.assert_array_equal(rows, np.arange(14,55))
        remaining = set(map(tuple, np.argwhere(alpha)))
        components = []
        while remaining:
            pending = [remaining.pop()]
            component = []
            while pending:
                x,y = pending.pop()
                component.append((x,y))
                for dx in (-1,0,1):
                    for dy in (-1,0,1):
                        neighbor = (x+dx,y+dy)
                        if neighbor in remaining:
                            remaining.remove(neighbor)
                            pending.append(neighbor)
            components.append(component)
        body = max(components, key=len)
        self.assertEqual(max(y for _,y in body)-min(y for _,y in body)+1, 41)
        self.assertTrue(all(len(component)<5 for component in components if component is not body))

    def test_flow_uses_cinematic_time_and_reduced_motion_holds_one_drawing(self):
        sequence = self.winter.energy['rear']
        duration = sum(length for _,length in sequence)
        image = self.winter.hold(180., 17.3+.02)[0]
        self.assertIs(self.winter.hold(180., 17.3+duration+.02)[0], image)
        changed = self.winter.hold(180., 17.3+sequence[0][1]+.02)[0]
        self.assertIsNot(changed, image)
        for time in (17.3, 18., 21., 27.5, 31.5):
            self.assertIs(self.winter.hold(180., time, reduced=True)[0], sequence[0][0])

    def test_authored_flow_keeps_registered_body_core_still(self):
        for name, entry in self.winter.manifest['energy'].items():
            with self.subTest(view=name):
                mask_path = self.winter.root/entry['core_mask']
                mask = pygame.surfarray.array3d(pygame.image.load(str(mask_path)))[:, :, 0] > 0
                self.assertGreater(np.count_nonzero(mask), 20)
                sequence = self.winter.energy[name]
                first = pygame.surfarray.array3d(sequence[0][0])[mask]
                for image, _ in sequence[1:]:
                    np.testing.assert_array_equal(pygame.surfarray.array3d(image)[mask], first)

    def test_direction_selection_wraps_without_mirroring_equipment(self):
        for view, entry in self.winter.manifest['energy'].items():
            angle = entry['view_azimuth_deg']
            expected = self.winter.energy[view][0][0]
            for azimuth in (angle-360, angle, angle+360):
                with self.subTest(view=view, angle=azimuth):
                    self.assertIs(self.winter.hold(azimuth, 17.3)[0], expected)

    def test_sweep_and_cast_use_authored_actions_then_resume_the_energy_loop(self):
        for action, count in (('staff_sweep', 8), ('cast', 6), ('cast_rear', 6)):
            self.assertGreaterEqual(len(self.winter.actions[action]), count)
        for time in (21.5, 24.35, 25.3, 26.2, 27.8, 29.1):
            positions = self.stage.duel.actor_positions(time)
            camera = self.stage.duel.camera(time)
            image, data, action = self.stage.duel._image('rhea', camera, positions['rhea'], time)
            self.assertEqual(data, self.winter.data)
            self.assertEqual(image.get_size(), (128, 128))
            if 24 <= time < 24.8:
                self.assertTrue(action.startswith('staff_sweep'))
            elif 25.65 <= time < 26.7:
                self.assertTrue(action.startswith('cast'))
            else:
                self.assertTrue(action.startswith('winter_energy_'))

    def test_actual_render_keeps_one_rhea_across_awake_turn_and_orbit(self):
        canvas = pygame.Surface((480, 320))
        for time in (15.2, 16.6, 17.3, 17.6, 20., 21.4, 24.4, 26.2, 27.8):
            with self.subTest(time=time):
                self.stage.draw(canvas, time)
                bodies = [entry for entry in self.stage.last_draw_trace
                          if entry.get('actor') == 'rhea']
                self.assertEqual(len(bodies), 1)
                self.assertEqual(bodies[0]['source_canvas'], [128, 128])


if __name__ == '__main__':
    unittest.main()
