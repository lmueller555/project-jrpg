"""Rejected real paintings, independent pixel gates, and production coverage.

These tests do not establish anatomical correctness or physical foot locking.
The paired visual review remains necessary, particularly under occlusion.
"""
from dataclasses import replace
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from tools.audit_prologue_motion import (CONTRACT, SOURCE, audit, load_drawings,
                                         load_fixture, registered_image,
                                         validate_registration_observations)
from tools.prologue_motion_review import find_reviewed_exception


class PaintedMotionNegativeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = CONTRACT.parent / 'before'
        cls.lucan = load_fixture('lucan', cls.fixture)
        cls.iselin = load_fixture('iselin', cls.fixture)
        cls.crown = load_fixture('crown_soldier', cls.fixture)
        cls.bad_lucan = audit('lucan', cls.lucan, complete=False)
        cls.bad_iselin = audit('iselin', cls.iselin, complete=False)

    def test_real_held_and_rushed_lucan_paintings_fail(self):
        faults = self.bad_lucan['violations']
        self.assertTrue(any(f['check'] == 'held_exchange' for f in faults))
        concentration = [d for d in self.bad_lucan['diagnostics']
                         if d['check'] == 'concentrated_exchange']
        self.assertEqual({d['region'] for d in concentration},
                         {'viewer_left_boot', 'viewer_right_boot'})
        self.assertFalse(any(f['check'] == 'concentrated_exchange' for f in faults))
        for transition in ([11, 12], [13, 14], [38, 39]):
            with self.subTest(transition=transition):
                self.assertTrue(any(f['check'] == 'distal_step' and f['frames'] == transition for f in faults))

    def test_real_iselin_material_reset_fails(self):
        seam = [f for f in self.bad_iselin['violations']
                if f['check'] == 'material_contour' and f['frames'] == [47, 0]]
        self.assertEqual({f['region'] for f in seam}, {'shawl', 'free_coat'})

    def test_identity_reviewed_iselin_leg_snaps_still_fail(self):
        faults = self.bad_iselin['violations']
        for region, transition in (('viewer_right_boot', [14, 15]),
                                   ('viewer_left_boot', [15, 16]),
                                   ('viewer_right_boot', [23, 24]),
                                   ('viewer_right_boot', [41, 42])):
            with self.subTest(region=region, transition=transition):
                self.assertTrue(any(f['check'] == 'distal_step' and f['frames'] == transition
                                    and f['region'] == region for f in faults))

    def test_real_crown_recovery_foot_lift_and_reset_fails(self):
        faults = audit('crown_soldier', self.crown, complete=False)['violations']
        for transition in ([10, 11], [11, 12]):
            self.assertTrue(any(f['check'] == 'distal_step' and f['frames'] == transition
                                and f['region'] == 'viewer_left_boot' for f in faults))

    def test_ideal_guide_labels_cannot_make_bad_pixels_pass(self):
        manifest = json.loads((self.fixture / 'manifest.json').read_text())
        for actor in manifest.values():
            for record in actor['frames']:
                record['source'] = str((self.fixture / record['source']).resolve())
                record['phase'] = 'perfect continuous recovery'
                record['desired_wrist'] = [record['index'] * 4, 100]
                record['desired_boot'] = [300, 900 - record['index'] * 5]
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'manifest.json').write_text(json.dumps(manifest))
            result = audit('lucan', load_fixture('lucan', folder), complete=False)
        self.assertEqual(result['measurements'], self.bad_lucan['measurements'])
        self.assertEqual(result['violations'], self.bad_lucan['violations'])

    def test_repeated_real_painting_fails_minimum_movement(self):
        first = next(d for d in self.lucan if d.index == 7)
        repeated = [replace(first, index=i) for i in range(48)]
        faults = audit('lucan', repeated)['violations']
        self.assertEqual({f['region'] for f in faults if f['check'] == 'cycle_progress'},
                         {'viewer_left_boot', 'viewer_right_boot'})

    def test_frozen_actual_material_region_fails_minimum_excursion(self):
        rules = json.loads(CONTRACT.read_text())
        # Limit this test to material excursion; movement and seam bounds have
        # independent tests. The frozen region contains real painted RGBA pixels.
        rules['actors']['iselin']['distal_regions'] = {}
        first = registered_image(self.iselin[0])
        drawings = []
        for i in range(48):
            original = self.iselin[i % len(self.iselin)]
            image = registered_image(original)
            for region in rules['actors']['iselin']['material_regions'].values():
                x0, x1, y0, y1 = region['window']
                box = (x0 + 512, y0 + 200, x1 + 512, y1 + 200)
                image.paste(first.crop(box), box)
            drawings.append(replace(original, index=i, image=image, neck=(512, 200),
                                    belt=(512, 383), scale=1))
        faults = audit('iselin', drawings, rules)['violations']
        self.assertEqual({f['region'] for f in faults if f['check'] == 'frozen_material'},
                         {'loose_hair', 'shawl', 'free_coat'})

    def test_reordering_actual_paintings_introduces_a_detected_snap(self):
        frames = {d.index: d for d in self.lucan}
        smooth_pair = [frames[7], frames[8]]
        self.assertFalse(audit('lucan', smooth_pair, complete=False)['violations'])
        reordered = [frames[7], replace(frames[18], index=8)]
        self.assertTrue(any(f['check'] == 'distal_step'
                            for f in audit('lucan', reordered, complete=False)['violations']))
        # Keep the original registration/annotations but replace the actual
        # painted pixels. Plausible metadata cannot rescue the wrong picture.
        changed_pixels = [frames[7], replace(frames[8], image=frames[18].image)]
        self.assertTrue(any(f['check'] == 'distal_step'
                            for f in audit('lucan', changed_pixels, complete=False)['violations']))

    def test_missing_diagnosed_transition_cannot_silently_pass(self):
        drawings = [d for d in self.lucan if d.index != 12]
        faults = audit('lucan', drawings)['violations']
        self.assertTrue(any(f['check'] == 'required_coverage' and f['frames'] == [11, 12]
                            for f in faults))

    def test_negative_fixture_pixel_hash_is_enforced(self):
        manifest = json.loads((self.fixture / 'manifest.json').read_text())
        for actor in manifest.values():
            for record in actor['frames']:
                record['source'] = str((self.fixture / record['source']).resolve())
        manifest['lucan']['frames'][0]['sha256'] = '0' * 64
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Changed negative fixture'):
                load_fixture('lucan', folder)

    def test_changing_measurement_registration_requires_review(self):
        # Actual registration observations are inputs; authoring phase/guide
        # labels are not. Deliberately moving a measured neck must not silently
        # redefine the pixel windows.
        drawings = load_drawings('lucan')
        drawings[0] = replace(drawings[0], neck=(drawings[0].neck[0] + 50, drawings[0].neck[1]))
        with self.assertRaisesRegex(ValueError, 'Review actual artwork registration'):
            validate_registration_observations('lucan', drawings)

    def test_accidental_whole_drawing_density_change_fails_torso_model_guard(self):
        drawing = next(d for d in self.lucan if d.index == 7)
        enlarged = replace(drawing, scale=drawing.scale * 1.25)
        faults = audit('lucan', [enlarged], complete=False)['violations']
        self.assertTrue(any(f['check'] == 'projected_torso_model' for f in faults))

    def test_changed_source_crop_requires_registration_review(self):
        original = load_drawings('lucan')[0]
        observation = {'sha256': original.digest, 'source': original.source,
                       'cell': list(original.cell), 'neck': list(original.neck),
                       'belt': list(original.belt), 'scale': original.scale,
                       'origin': list(original.origin)}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'observations.json'
            path.write_text(json.dumps({'actors': {'lucan': {'0': observation}}}))
            validate_registration_observations('lucan', [original], path)
            # Same source bytes and measured points, but the actual selected
            # painted content has moved because 50 source pixels were cropped.
            x0, y0, x1, y1 = original.cell
            changed = replace(original, cell=(x0 + 50, y0, x1, y1),
                              image=original.image.crop((50, 0, original.image.width, original.image.height)))
            with self.assertRaisesRegex(ValueError, 'Review actual artwork registration'):
                validate_registration_observations('lucan', [changed], path)

    def test_export_origin_jump_fails_even_with_unchanged_painting_and_relative_points(self):
        original = next(d for d in self.lucan if d.index == 7)
        shifted = replace(original, index=8, origin=(original.origin[0] + 40, original.origin[1]))
        result = audit('lucan', [original, shifted], complete=False)
        self.assertEqual(result['measurements']['viewer_left_boot'][7],
                         result['measurements']['viewer_left_boot'][8])
        faults = [f for f in result['violations'] if f['check'] == 'exported_registration_step']
        self.assertEqual({f['landmark'] for f in faults}, {'neck', 'belt'})

    def test_edited_observed_sole_coordinate_fails_actual_pixel_support(self):
        rules = json.loads(CONTRACT.read_text())
        observations = rules['actors']['iselin']['distal_regions']['viewer_right_boot']['reviewed_window_overrides']
        observation = next(o for o in observations if o['original_sequence_index'] == 14)
        # Same actual painting, hash and identity ROI; only the claimed observed
        # lowest-visible sole position is changed. Authoring targets have their
        # separate invariance test and cannot act as observation evidence.
        observation['observed_distal_exported'][1] += 40
        self.assertFalse(any(f['check'] == 'reviewed_sole_pixel_support'
                             for f in self.bad_iselin['violations']))
        faults = audit('iselin', self.iselin, rules, complete=False)['violations']
        self.assertTrue(any(f['check'] == 'reviewed_sole_pixel_support' and f['frame'] == 14
                            for f in faults))

    def test_reviewed_contour_statistics_do_not_waive_changed_art_or_larger_excesses(self):
        rules = json.loads(CONTRACT.read_text())
        reviews = rules['actors']['iselin']['reviewed_metric_exceptions']
        self.assertEqual({tuple(row['frame'] for row in item['context']['frames'])
                          for item in reviews}, {(13, 14), (14, 15)})
        for review in reviews:
            context = review['context']
            kwargs = {'value': review['reviewed_value'], 'default_limit': review['default_limit']}
            self.assertIsNotNone(find_reviewed_exception(reviews, context=context, **kwargs))
            self.assertIsNone(find_reviewed_exception(reviews, context=context,
                value=review['maximum_reviewed_value']+1, default_limit=review['default_limit']))
            overly_broad = deepcopy(review)
            overly_broad['sampling_tolerance'] = 2
            self.assertIsNone(find_reviewed_exception([overly_broad], context=context, **kwargs))
            for field in ('source_sha256', 'cell', 'origin', 'rendered_rgba_sha256'):
                changed = deepcopy(context)
                changed['frames'][0][field] = 'changed'
                self.assertIsNone(find_reviewed_exception(reviews, context=changed, **kwargs))
            changed = deepcopy(context)
            changed['configuration']['window'][0] += 1
            self.assertIsNone(find_reviewed_exception(reviews, context=changed, **kwargs))
        drawings = load_drawings('iselin')[13:15]
        accepted = audit('iselin', drawings, rules, complete=False)
        self.assertTrue(any(row['check'] == 'reviewed_material_contour'
                            for row in accepted['diagnostics']))
        altered = [drawings[0], replace(drawings[1],
                    origin=(drawings[1].origin[0]+1, drawings[1].origin[1]))]
        faults = audit('iselin', altered, rules, complete=False)['violations']
        self.assertTrue(any(row['check'] == 'material_contour' and row['region'] == 'shawl'
                            for row in faults))

    def test_actual_rejected_calf_windows_cannot_support_reviewed_boot_observations(self):
        rejected = json.loads((CONTRACT.parent/'rejected_sole_windows.json').read_text())['records']
        banks = {actor: load_drawings(actor) for actor in {row['actor'] for row in rejected}}
        for old in rejected:
            with self.subTest(actor=old['actor'], frame=old['frame']):
                drawing = banks[old['actor']][old['frame']]
                self.assertEqual((drawing.source, drawing.digest), (old['source'], old['sha256']))
                rules = json.loads(CONTRACT.read_text())
                region = rules['actors'][old['actor']]['distal_regions']['viewer_left_boot']
                reviewed = next(row for row in region['reviewed_window_overrides']
                                if row['sha256'] == drawing.digest)
                reviewed['x'] = old['wrong_window_x']
                reviewed.pop('y', None)
                region['below_belt'] = old['wrong_below_belt']
                # Retain the independently inspected true sole observation;
                # restoring the old calf ROI must no longer silently pass.
                report = audit(old['actor'], [drawing], rules, complete=False)
                measured = report['measurements']['viewer_left_boot'][drawing.index]
                self.assertAlmostEqual(measured['x'], old['wrong_measured_x_neck_relative'], places=3)
                self.assertAlmostEqual(measured['y'], old['wrong_measured_y_neck_relative'], places=3)
                self.assertTrue(any(row['check'] == 'reviewed_sole_pixel_support'
                                    and row['frame'] == drawing.index
                                    for row in report['violations']))


class ProductionPaintedMotion(unittest.TestCase):
    def test_current_banks_meet_scoped_pixel_contract_and_cadence(self):
        for actor in ('lucan', 'iselin', 'crown_soldier'):
            with self.subTest(actor=actor):
                profile = json.loads((SOURCE / actor / 'source_art_48.json').read_text())
                self.assertEqual(len(profile['frames']), 48)
                self.assertEqual(profile['cycle_ms'], 800)
                drawings = load_drawings(actor)
                validate_registration_observations(actor, drawings)
                result = audit(actor, drawings)
                self.assertEqual(result['violations'], [], json.dumps(result['violations'], indent=2))


if __name__ == '__main__':
    unittest.main()
