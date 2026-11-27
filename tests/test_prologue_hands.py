"""Visible painted arms must retain their pump, independently of gait labels."""
from dataclasses import replace
import json
from math import dist
from pathlib import Path
import unittest

from PIL import Image

from tools.audit_prologue_hands import ACTORS, audit, measure, reviewed_window
from tools.audit_prologue_motion import load_drawings, load_fixture


class PaintedHandMovementTests(unittest.TestCase):
    def test_actual_rejected_fist_jumps_fail_the_scoped_gross_step_guard(self):
        folder = Path(__file__).parent/'fixtures/prologue_hands/before'
        for actor, transition in [('lucan', [35, 36]), ('iselin', [2, 3])]:
            with self.subTest(actor=actor):
                faults = audit(actor, load_fixture(actor, folder), complete=False)['violations']
                self.assertTrue(any(fault['check'] == 'hand_gross_step'
                                    and fault['frames'] == transition
                                    and fault['side'] == 'anatomical_right' for fault in faults))

    def test_incomplete_or_relabelled_cycle_cannot_hide_a_jump(self):
        folder = Path(__file__).parent/'fixtures/prologue_hands/before'
        first, second = load_fixture('lucan', folder)
        incomplete = [first, replace(second, index=37)]
        faults = audit('lucan', incomplete)['violations']
        self.assertTrue(any(fault['check'] == 'complete_hand_cycle_coverage' for fault in faults))
        self.assertTrue(audit('lucan', [])['violations'])

    def test_production_visible_hands_have_reviewed_coverage_and_pump(self):
        for actor in ACTORS:
            with self.subTest(actor=actor):
                report = audit(actor, load_drawings(actor))
                self.assertEqual(report['violations'], [])
                expected = {'anatomical_right', 'anatomical_left'} if actor == 'iselin' else {'anatomical_right'}
                self.assertEqual(len(report['measurements']), 48)
                for frame in report['measurements']:
                    self.assertEqual(set(frame['hands']), expected)
                    self.assertEqual(len(frame['sha256']), 64)
                if actor != 'iselin':
                    self.assertEqual(report['occluded'], ['anatomical_left_wrist_behind_shield'])

    def test_frozen_actual_paintings_cannot_pass_the_arm_motion_check(self):
        for actor in ACTORS:
            with self.subTest(actor=actor):
                reference = load_drawings(actor)[0]
                frozen = [replace(reference, index=index) for index in range(48)]
                faults = audit(actor, frozen)['violations']
                expected = {'anatomical_right', 'anatomical_left'} if actor == 'iselin' else {'anatomical_right'}
                self.assertEqual({fault['side'] for fault in faults if fault['check'] == 'hand_pump_range'}, expected)

    def test_missing_visible_hand_pixels_are_a_failure_not_an_occlusion_waiver(self):
        reference = load_drawings('iselin')[0]
        empty = replace(reference, image=Image.new('RGBA', reference.image.size))
        faults = audit('iselin', [empty])['violations']
        self.assertEqual({fault['side'] for fault in faults if fault['check'] == 'visible_hand_coverage'},
                         {'anatomical_right', 'anatomical_left'})

    def test_glove_window_review_cannot_survive_changed_pixels_crop_or_registration(self):
        reference = load_drawings('crown_soldier')[20]
        self.assertIsNotNone(reviewed_window('crown_soldier', reference, 'anatomical_right'))
        changed_pixels = reference.image.copy()
        changed_pixels.putpixel((0, 0), (255, 0, 0, 255))
        mutations = [replace(reference, image=changed_pixels),
                     replace(reference, digest='0'*64),
                     replace(reference, cell=(1, *reference.cell[1:])),
                     replace(reference, scale=reference.scale*1.1),
                     replace(reference, origin=(reference.origin[0]+15, reference.origin[1])),
                     replace(reference, neck=(reference.neck[0]+15, reference.neck[1]))]
        for drawing in mutations:
            with self.subTest(drawing=drawing.source, scale=drawing.scale, origin=drawing.origin):
                with self.assertRaisesRegex(ValueError, 'Review actual glove window'):
                    reviewed_window('crown_soldier', drawing, 'anatomical_right')

    def test_actual_sword_fittings_cannot_substitute_for_the_reviewed_gloves(self):
        path = Path(__file__).parent/'fixtures/prologue_hands/rejected_components.json'
        frames = load_drawings('crown_soldier')
        for case in json.loads(path.read_text()):
            with self.subTest(frame=case['frame']):
                drawing = frames[case['frame']]
                self.assertEqual((drawing.source, drawing.digest), (case['source'], case['sha256']))
                hand = measure(drawing, case['side'], gloved=True,
                    window=reviewed_window('crown_soldier', drawing, case['side']))
                x, y = hand['point_source']
                left, top, right, bottom = case['reviewed_glove_box_source']
                self.assertTrue(left <= x < right and top <= y < bottom,
                                'The measured component must identify the actual gripping glove.')
                self.assertGreater(dist(hand['point_source'], case['rejected_component_point_source']), 20)


if __name__ == '__main__':
    unittest.main()
