"""Actual native grass pixels preserve the requested scale and emerald hue."""
import colorsys
import json
import math
from pathlib import Path
import unittest

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT/'assets/terrain/grass_demo/assets.json'


def poses(variant):
    yield from ((f'idle_{index}', record) for index, record in enumerate(variant['idle']))
    for direction, frames in variant['parted'].items():
        yield from ((f'{direction}_{index}', record) for index, record in enumerate(frames))


class GrassAssetProportionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MANIFEST.read_text())
        cls.grass = cls.data['tall_grass']

    def test_actual_grass_silhouettes_stay_approximately_half_caelans_visible_height(self):
        with Image.open(ROOT/'assets/characters/caelan/idle_front.png') as hero:
            hero_bounds = hero.convert('RGBA').getchannel('A').getbbox()
            character_height = hero_bounds[3]-hero_bounds[1]
        self.assertEqual(character_height, 34)
        limit = math.ceil(character_height/2)
        for identifier, variant in self.grass['variants'].items():
            idle_heights = []
            for name, pose in poses(variant):
                with self.subTest(variant=identifier, pose=name):
                    with Image.open(ROOT/pose['rear']) as rear, Image.open(ROOT/pose['front']) as front:
                        self.assertEqual(rear.size, (24, 32))
                        self.assertEqual(front.size, (24, 32))
                        alpha = ImageChops.lighter(rear.getchannel('A'), front.getchannel('A'))
                        bounds = alpha.getbbox()
                        self.assertIsNotNone(bounds)
                        height = bounds[3]-bounds[1]
                        self.assertLessEqual(height, limit,
                                             ('Grass exceeds half-height scale', height, character_height))
                        if name.startswith('idle_'):idle_heights.append(height)
                        # The physical actor anchor is at sprite row 30.
                        # Foreground grass rooted at the same foot coordinate
                        # must begin at row 25 or lower on that drawing.
                        front_bounds = front.getchannel('A').getbbox()
                        self.assertGreaterEqual(front_bounds[1], self.grass['anchor'][1]-5)
            self.assertGreaterEqual(min(idle_heights), 13)

    def test_revised_grass_keeps_hard_alpha_and_the_same_anchored_roots_in_every_pose(self):
        self.assertEqual(self.grass['anchor'], [12, 28])
        for identifier, variant in self.grass['variants'].items():
            expected = {}
            for name, pose in poses(variant):
                for layer in ('rear', 'front'):
                    with self.subTest(variant=identifier, pose=name, layer=layer):
                        with Image.open(ROOT/pose[layer]) as image:
                            self.assertLessEqual(set(image.getchannel('A').get_flattened_data()), {0, 255})
                            root = image.crop((0, 26, 24, 32)).tobytes()
                        if layer not in expected:expected[layer] = root
                        self.assertEqual(root, expected[layer], 'Parting must leave roots anchored')

    def test_ground_base_is_deeper_emerald_than_the_rejected_olive_prototype(self):
        base = tuple(bytes.fromhex(self.data['palette']['base'].lstrip('#')))
        hue, saturation, value = colorsys.rgb_to_hsv(*(channel/255 for channel in base))
        self.assertGreater(base[1], base[2])
        self.assertGreater(base[2], base[0], 'Emerald needs more blue than the olive prototype')
        self.assertTrue(135 <= hue*360 <= 170, ('Emerald hue', hue*360))
        self.assertGreaterEqual(saturation, .5)
        self.assertTrue(.35 <= value <= .60, ('Deep green brightness', value))
        old = (98, 150, 78)  # The previous prototype's #62964e, rejected by the user.
        luminance = lambda rgb: sum(channel*weight for channel, weight in zip(rgb, (.2126, .7152, .0722)))
        self.assertLess(luminance(base), luminance(old)*.9)


if __name__ == '__main__':unittest.main()
