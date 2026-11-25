"""Reject invalid world-map survey references before generating regional exports."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from tools.build_elden_vale_overworld import validate_atlas_survey


ROOT = Path(__file__).resolve().parents[1]


class OverworldAtlasSurveyTests(unittest.TestCase):
    def setUp(self):
        recipe = ROOT/'assets/source/maps/overworld/elden_vale/recipe.json'
        self.geography = json.loads(recipe.read_text())['geography']

    def test_approved_survey_is_valid_without_mutating_source_coordinates(self):
        original = deepcopy(self.geography)
        validate_atlas_survey(self.geography)
        self.assertEqual(self.geography, original)

    def test_out_of_image_anchor_trace_and_polygon_are_rejected(self):
        width, height = self.geography['atlas_source_size']
        for kind in ('anchor', 'trace', 'polygon'):
            with self.subTest(kind=kind):
                geography = deepcopy(self.geography)
                if kind == 'anchor':
                    geography['anchors'][0]['atlas_pixel'] = [width, 0]
                elif kind == 'trace':
                    geography['atlas_traces'][0]['atlas_points'][0] = [0, height]
                else:
                    geography['opening_corridor_reference_polygon'][0] = [-1, 0]
                with self.assertRaises(ValueError):
                    validate_atlas_survey(geography)

    def test_crop_cannot_reverse_bounds_or_add_off_image_padding(self):
        width, height = self.geography['atlas_source_size']
        for crop in ((-1, 0, 100, 100), (0, 0, width, height + 1),
                     (100, 0, 50, 100), (0, 100, 100, 50)):
            with self.subTest(crop=crop):
                geography = deepcopy(self.geography)
                geography['reference_crop_atlas_pixels'] = crop
                with self.assertRaisesRegex(ValueError, 'reference crop'):
                    validate_atlas_survey(geography)

    def test_incomplete_watercourse_or_corridor_is_rejected(self):
        for kind in ('trace', 'polygon'):
            with self.subTest(kind=kind):
                geography = deepcopy(self.geography)
                if kind == 'trace':
                    geography['atlas_traces'][0]['atlas_points'] = [[10, 10]]
                else:
                    geography['opening_corridor_reference_polygon'] = [[10, 10], [20, 20]]
                with self.assertRaises(ValueError):
                    validate_atlas_survey(geography)


if __name__ == '__main__':
    unittest.main()
