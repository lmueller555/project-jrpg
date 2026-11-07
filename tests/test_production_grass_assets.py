"""Production promotion preserves approved art and non-green source details."""
import json
from pathlib import Path
import unittest

from PIL import Image

from tools.build_grass_assets import products


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT/'assets/terrain/grass'
RECIPE = ROOT/'assets/source/terrain/grass/recipe.json'


class ProductionGrassAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((PACK/'assets.json').read_text())
        cls.recipe = json.loads(RECIPE.read_text())

    def test_every_production_material_and_grass_pose_matches_approved_pixels(self):
        reference = ROOT/'assets/terrain/grass_demo'
        images = [*PACK.joinpath('ground').rglob('*.png'),
                  *PACK.joinpath('tall').rglob('*.png')]
        self.assertEqual(len(images), 156)
        for path in images:
            with self.subTest(image=path.relative_to(PACK)):
                self.assertEqual(path.read_bytes(), (reference/path.relative_to(PACK)).read_bytes())
        self.assertEqual(self.manifest['palette']['base'], '#2c7c50')
        self.assertEqual(self.manifest['status'], 'approved')
        self.assertEqual(self.manifest['tall_grass']['opaque_height_limit'], 17)
        for family in ('lawn', 'meadow', 'woodland'):
            self.assertEqual(len(self.manifest['materials'][family]['tiles']), 4)
            self.assertTrue(all(path.startswith('assets/terrain/grass/')
                                for path in self.manifest['materials'][family]['tiles']))

    def assert_green_derivative(self, source, target):
        greens = {tuple(bytes.fromhex(color[1:])) for color in self.recipe['legacy_green_remap']}
        approved = {tuple(bytes.fromhex(color[1:]))
                    for color in self.recipe['legacy_green_remap'].values()}
        with Image.open(source) as old, Image.open(target) as new:
            old, new = old.convert('RGBA'), new.convert('RGBA')
            self.assertEqual(old.size, new.size)
            self.assertEqual(old.getchannel('A').tobytes(), new.getchannel('A').tobytes())
            for before, after in zip(old.get_flattened_data(), new.get_flattened_data()):
                if before[:3] in greens:
                    self.assertIn(after[:3], approved)
                    self.assertNotIn(after[:3], greens)
                else:
                    self.assertEqual(before, after, 'Non-green source detail changed')

    def test_dirt_derivatives_preserve_earth_geometry_and_alpha(self):
        source = ROOT/'assets/terrain/eldenmere/grass_dirt'
        old = json.loads((source/'tileset.json').read_text())
        records = self.manifest['dirt_transitions']['tiles']
        self.assertEqual(len(records), 47)
        self.assertEqual([record['mask'] for record in records],
                         [record['mask'] for record in old['tiles']])
        for previous, current in zip(old['tiles'], records):
            with self.subTest(mask=current['mask']):
                self.assert_green_derivative(source/previous['image'], ROOT/current['image'])
        for previous, current in zip(old['dirt_interiors']['images'],
                                     self.manifest['dirt_transitions']['interiors']):
            with self.subTest(interior=current):
                self.assertEqual((source/previous).read_bytes(), (ROOT/current).read_bytes())

    def test_flower_derivatives_preserve_petals_roots_alpha_and_timing(self):
        for name, record in self.manifest['flowers'].items():
            source = ROOT/self.recipe['legacy_flower_root']/name
            target = (ROOT/record['metadata']).parent
            old = json.loads((source/'plant.json').read_text())
            new = json.loads((target/'plant.json').read_text())
            self.assertEqual(new['wind'], old['wind'])
            self.assertEqual(new['fixed_rows_from'], old['fixed_rows_from'])
            self.assertFalse(new['collision'])
            for path in source.rglob('*.png'):
                with self.subTest(flower=name, image=path.relative_to(source)):
                    self.assert_green_derivative(path, target/path.relative_to(source))

    def test_production_exports_are_current_and_deterministic(self):
        for path, body in products().items():
            with self.subTest(image=path.relative_to(ROOT)):
                self.assertEqual(path.read_bytes(), body)


if __name__ == '__main__':
    unittest.main()
