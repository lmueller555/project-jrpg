"""Actual internal-braid RGB regressions, including the alpha blind spot."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import json
import unittest

import numpy as np
from PIL import Image

from tools.audit_prologue_braid import (CONTRACT, audit, exported_image, observation_for,
                                        rejected_groups, selected_pixels)
from tools.audit_prologue_motion import load_drawings, validate_registration_observations
from tools.prologue_motion_review import find_reviewed_exception


class PaintedBraidNegativeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text())
        cls.groups = rejected_groups()

    def test_real_rejected_reach_joins_fail_actual_rgb_measurement(self):
        for group in ('rejected_10_11', 'original_rejected_14_15',
                      'rejected_32_33', 'rejected_39_40', 'late_rejected_38_39'):
            with self.subTest(group=group):
                report = audit(self.groups[group], self.contract, complete=False)
                self.assertTrue(any(item['check'] == 'braid_region_step'
                                    for item in report['violations']))
                self.assertEqual(report['coverage']['visible'], 2)

    def test_ordinary_real_braid_neighbors_do_not_become_forced_negatives(self):
        for group in ('ordinary_31_32', 'ordinary_33_34'):
            with self.subTest(group=group):
                self.assertFalse(audit(self.groups[group], self.contract, complete=False)['violations'])

    def test_authoring_tip_targets_cannot_rescue_unchanged_bad_paintings(self):
        rules = deepcopy(self.contract)
        for observation in rules['observations']:
            observation['desired_tip'] = [600 + observation['frame'], 330]
            observation['desired_phase'] = 'perfectly continuous braid'
        drawings = self.groups['rejected_10_11']
        before = audit(drawings, self.contract, complete=False)
        after = audit(drawings, rules, complete=False)
        self.assertEqual(before, after)

    def test_rgb_braid_removal_is_detected_while_alpha_pixels_stay_identical(self):
        drawing = self.groups['rejected_10_11'][1]
        observation = observation_for(drawing, self.contract)
        original = exported_image(drawing)
        rgba = np.array(original)
        box = observation['box_exported']
        mask = selected_pixels(original, box, self.contract['color_mask'])
        # Sample actual dark-blue clothing, then remove only the measured braid
        # colors inside this opaque torso region. Keep every alpha byte intact.
        blue = ((rgba[:, :, 3] > 128) & (rgba[:, :, 0] < 80)
                & (rgba[:, :, 2].astype(int) > rgba[:, :, 0].astype(int) + 20))
        color = rgba[np.nonzero(blue)][0, :3]
        region = rgba[box[1]:box[3], box[0]:box[2]]
        region[mask, :3] = color
        self.assertTrue(np.array_equal(np.asarray(original)[:, :, 3], rgba[:, :, 3]))
        neck = tuple(drawing.neck[i] * drawing.scale + round(drawing.origin[i]) for i in (0, 1))
        belt = tuple(drawing.belt[i] * drawing.scale + round(drawing.origin[i]) for i in (0, 1))
        changed = replace(drawing, image=Image.fromarray(rgba), scale=1, origin=(0, 0),
                          cell=(0, 0, 1024, 1024), neck=neck, belt=belt)
        # Grant this synthetic mutated view correct fresh pixel/file identity,
        # isolating the color measurement from the independent hash guard.
        stream = BytesIO()
        changed.image.save(stream, format='PNG', compress_level=6)
        changed = replace(changed, digest=sha256(stream.getvalue()).hexdigest())
        rules = deepcopy(self.contract)
        altered_observation = next(row for row in rules['observations'] if row['frame'] == drawing.index)
        altered_observation.update({'source_sha256': None, 'exported_snapshot_sha256': changed.digest,
            'exported_pixels_sha256': sha256(rgba.tobytes()).hexdigest(), 'neck_exported': list(neck)})
        faults = audit([changed], rules, complete=False)['violations']
        self.assertTrue(any(item['check'] == 'braid_visible_pixel_coverage' for item in faults))

    def test_repeated_actual_braid_region_fails_minimum_cycle_excursion(self):
        drawing = self.groups['rejected_10_11'][0]
        rules = deepcopy(self.contract)
        observation = observation_for(drawing, rules)
        rules['observations'] = [{**observation, 'frame': index} for index in range(48)]
        rules['mask_review_state'] = 'reviewed'
        repeated = [replace(drawing, index=index) for index in range(48)]
        faults = audit(repeated, rules)['violations']
        self.assertTrue(any(item['check'] == 'frozen_braid_region' for item in faults))

    def test_known_join_cannot_be_skipped_as_missing_or_hidden(self):
        rules = deepcopy(self.contract)
        rules['observations'] = [row for row in rules['observations'] if row['frame'] != 11]
        faults = audit(self.groups['rejected_10_11'], rules, complete=False)['violations']
        self.assertTrue(any(item['check'] == 'required_braid_join_coverage' for item in faults))

    def test_new_pixel_region_needs_its_own_identity_review(self):
        rules = deepcopy(self.contract)
        rules['mask_review_state'] = 'reviewed'
        drawings = self.groups['ordinary_31_32']
        observation = observation_for(drawings[1], rules)
        observation['pixel_identity_reviewed'] = False
        faults = audit(drawings, rules, complete=False)['violations']
        self.assertTrue(any(item['check'] == 'braid_pixel_identity_review_pending' for item in faults))

    def test_export_geometry_change_cannot_reuse_old_braid_pixel_approval(self):
        drawings = self.groups['ordinary_31_32']
        shifted = [replace(drawing, origin=(drawing.origin[0] + 15, drawing.origin[1]),
                           neck=(drawing.neck[0] - 15 / drawing.scale, drawing.neck[1]))
                   for drawing in drawings]
        # The compensated declared neck is unchanged in exported coordinates,
        # while the actual crop/scale/origin view moves. Pixel identity must fail
        # even if the separate global registration artifact were re-approved.
        faults = audit(shifted, self.contract, complete=False)['violations']
        self.assertEqual({item['frame'] for item in faults
                          if item['check'] == 'reviewed_braid_observation_coverage'}, {31, 32})

    def test_exact_reviewed_diagnostic_cannot_approve_source_region_or_metric_mutations(self):
        drawings = self.groups['rejected_10_11']
        rules = deepcopy(self.contract)
        baseline = audit(drawings, rules, complete=False)
        fault = next(item for item in baseline['violations'] if item['check'] == 'braid_region_step')
        review = {'id': 'test_only_exact_pair', 'review_state': 'accepted',
                  'context': fault['review_context'], 'default_limit': 65,
                  'reviewed_value': fault['pixels'], 'sampling_tolerance': 1,
                  'maximum_reviewed_value': fault['pixels'] + 1,
                  'reason': 'Synthetic test-only review, never a production approval.'}
        rules['reviewed_metric_exceptions'] = [review]
        approved = audit(drawings, rules, complete=False)
        self.assertTrue(any(item['check'] == 'reviewed_braid_region_step' for item in approved['diagnostics']))
        changed_source = [replace(drawings[0], digest='f' * 64), drawings[1]]
        rejected = audit(changed_source, rules, complete=False)
        self.assertTrue(rejected['violations'])
        self.assertFalse(rejected['diagnostics'])
        changed_region = deepcopy(rules)
        observation = observation_for(drawings[0], changed_region)
        observation['box_exported'][0] += 1
        rejected = audit(drawings, changed_region, complete=False)
        self.assertTrue(any(item['check'] == 'braid_region_step' for item in rejected['violations']))
        self.assertIsNone(find_reviewed_exception([review], context=fault['review_context'],
            value=review['maximum_reviewed_value'] + .01, default_limit=65))


class ProductionPaintedBraid(unittest.TestCase):
    def test_full_cycle_uses_reviewed_actual_visible_braid_regions(self):
        drawings = load_drawings('iselin')
        validate_registration_observations('iselin', drawings)
        report = audit(drawings)
        self.assertEqual(report['violations'], [], json.dumps(report['violations'], indent=2))


if __name__ == '__main__':
    unittest.main()
