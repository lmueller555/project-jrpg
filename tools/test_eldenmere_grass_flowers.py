"""Verify native ground plants, anchored motion, safe placements and review delivery."""
import json
from pathlib import Path
import unittest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'assets/terrain/eldenmere/grass_flowers'
SOURCE = ROOT / 'assets/source/terrain/eldenmere/grass_flowers'
PREVIOUS = PACK.parent / 'foliage'


def load(path):
    return json.loads(path.read_text())


def opened(path):
    with Image.open(path) as image:
        return image.convert('RGBA')


class GroundPlantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe = load(SOURCE / 'recipe.json')
        cls.scene = load(PACK / 'review_scene.json')
        cls.metadata = {p['id']: load(PACK / p['id'] / 'plant.json') for p in cls.recipe['plants']}
        cls.frames = {name: [opened(PACK / name / f['image']) for f in meta['wind']['frames']]
                      for name, meta in cls.metadata.items()}
        cls.unions = {}
        for name, frames in cls.frames.items():
            union = Image.new('L', (24, 24))
            for frame in frames:
                union = ImageChops.lighter(union, frame.getchannel('A'))
            cls.unions[name] = union

    def test_native_palette_alpha_source_rest_and_registration(self):
        self.assertEqual(set(self.metadata), {'grass_sparse', 'grass_splayed', 'grass_dense',
                                             'flowers_white', 'flowers_yellow', 'flowers_violet'})
        palette = load(PACK / 'palette.json')['materials']
        self.assertEqual(palette['greens'], load(PREVIOUS / 'palette.json')['materials']['leaves'])
        colors = {tuple(bytes.fromhex(c[1:])) for ramp in palette.values() for c in ramp.values()}
        for name, meta in self.metadata.items():
            self.assertEqual(meta['tile_size'], [24, 24])
            self.assertEqual(meta['frame_size'], [24, 24])
            self.assertEqual(meta['ground_rect'], [0, 0, 24, 24])
            self.assertFalse(meta['collision'])
            self.assertEqual(opened(SOURCE / f'parts/{name}_native.png').tobytes(), self.frames[name][0].tobytes())
            self.assertEqual(opened(PACK / name / 'idle.png').tobytes(), self.frames[name][0].tobytes())
            for path in (PACK / name).rglob('*.png'):
                image = opened(path)
                self.assertLessEqual(set(image.getchannel('A').get_flattened_data()), {0, 255})
                self.assertTrue(all(not p[3] or p[:3] in colors for p in image.get_flattened_data()), path)
            for frame in self.frames[name]:
                x, y, right, bottom = frame.getbbox()
                self.assertTrue(0 < x < right <= 24 and 0 < y < bottom < 24)

    def test_fixed_roots_bending_bounds_exact_bands_and_sheets(self):
        for name, meta in self.metadata.items():
            wind = meta['wind']
            self.assertEqual(wind['direction'], 'E')
            self.assertEqual(wind['max_displacement_pixels'], [1, 0])
            self.assertFalse(wind['whole_plant_moves'])
            self.assertTrue(wind['loop'])
            self.assertEqual(sum(f['duration_ms'] for f in wind['frames']), 5400)
            base = opened(PACK / name / meta['fixed_base'])
            self.assertIsNotNone(base.getbbox())
            sheet = opened(PACK / name / 'sheet.png')
            self.assertEqual(sheet.size, (216, 24))
            rest = self.frames[name][0]
            self.assertGreaterEqual(len({f.tobytes() for f in self.frames[name]}), 6)
            for phase, (record, actual) in enumerate(zip(wind['frames'], self.frames[name], strict=True)):
                expected = Image.new('RGBA', (24, 24))
                for band, dx in zip(meta['bands'], record['band_offsets_x'], strict=True):
                    self.assertIn(dx, (0, 1))
                    part = opened(PACK / name / band['image'])
                    self.assertGreaterEqual(part.getbbox()[1], band['rows'][0])
                    self.assertLessEqual(part.getbbox()[3], band['rows'][1])
                    expected.alpha_composite(part, (dx, 0))
                expected.alpha_composite(base)
                self.assertEqual(expected.tobytes(), actual.tobytes())
                self.assertEqual(sum(bool(a) for a in actual.getchannel('A').get_flattened_data()),
                                 sum(bool(a) for a in rest.getchannel('A').get_flattened_data()))
                self.assertEqual(actual.crop((0, 20, 24, 24)).tobytes(), rest.crop((0, 20, 24, 24)).tobytes())
                self.assertEqual(sheet.crop((phase * 24, 0, (phase + 1) * 24, 24)).tobytes(), actual.tobytes())
                self.assertIsNone(ImageChops.multiply(ImageChops.difference(actual.convert('RGB'), rest.convert('RGB')),
                                                     base.getchannel('A').convert('RGB')).getbbox())

    def test_grass_only_placement_all_wind_phases_no_new_plant_occlusion(self):
        ground = PACK.parent / 'grass_dirt'
        grass = {pixel for p in load(ground / 'tileset.json')['grass']['images']
                 for pixel in opened(ground / p).get_flattened_data()}
        coverage = Image.new('L', (768, 1296))
        for instance in self.scene['instances']:
            self.assertEqual(instance['ground_elevation_pixels'], 0)
            union = self.unions[instance['plant']]
            layer = Image.new('L', coverage.size)
            layer.paste(union, tuple(instance['position']))
            self.assertIsNone(ImageChops.multiply(layer, coverage).getbbox(), instance)
            coverage = ImageChops.lighter(coverage, layer)
        points = [(x, y) for y in range(coverage.height) for x in range(coverage.width) if coverage.getpixel((x, y))]
        for tick in range(54):
            previous = opened(PREVIOUS / f'scene_frames/frame_{tick + 1:02}.png')
            self.assertTrue(all(previous.getpixel(p) in grass for p in points), f'Non-grass coverage at phase {tick}')
        self.assertEqual(self.scene['wind_direction'], load(PREVIOUS / 'review_scene.json')['wind_direction'])

    def test_no_detached_blades_petals_or_stems_in_any_pose(self):
        # Every retained source clump is connected. Bending must not shed loose pixels.
        for name, frames in self.frames.items():
            for phase, frame in enumerate(frames):
                pixels = {(x, y) for y in range(24) for x in range(24) if frame.getpixel((x, y))[3]}
                reached = {next(iter(pixels))}
                pending = list(reached)
                while pending:
                    x, y = pending.pop()
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            point = x + dx, y + dy
                            if point in pixels and point not in reached:
                                reached.add(point)
                                pending.append(point)
                self.assertEqual(reached, pixels, f'Detached pixels in {name} phase {phase}')

    def test_scene_exact_reconstruction_prior_pixels_and_shared_timing(self):
        self.assertEqual(len(self.scene['frames']), 54)
        self.assertEqual(self.scene['cycle_duration_ms'], 10800)
        self.assertEqual(self.scene['plants_cycle_duration_ms'], 5400)
        for tick, record in enumerate(self.scene['frames']):
            self.assertEqual(record['base_phase'], tick)
            self.assertEqual(record['duration_ms'], 200)
            previous = opened(PREVIOUS / f'scene_frames/frame_{tick + 1:02}.png')
            expected = previous.copy()
            for instance, phase in zip(self.scene['instances'], record['plant_phases'], strict=True):
                self.assertEqual(phase, (tick // 3 + instance['phase_offset']) % 9)
                expected.alpha_composite(self.frames[instance['plant']][phase], tuple(instance['position']))
            actual = opened(PACK / record['image'])
            self.assertEqual(actual.size, (768, 1296))
            self.assertEqual(expected.tobytes(), actual.tobytes())

    def test_gif_lossless_pixels_durations_loops_and_scale_reference(self):
        for name, crop, scale in (('review_scene', None, 2), ('garden_closeup', self.scene['review']['closeup_rect'], 4)):
            with Image.open(PACK / f'{name}.gif') as gif:
                self.assertEqual(gif.n_frames, 54)
                self.assertEqual(gif.info['loop'], 0)
                for phase, record in enumerate(self.scene['frames']):
                    expected = opened(PACK / record['image']).convert('RGB')
                    if crop:
                        expected = expected.crop(crop)
                    expected = expected.resize((expected.width * scale, expected.height * scale), Image.Resampling.NEAREST)
                    gif.seek(phase)
                    self.assertEqual(gif.info['duration'], 200)
                    self.assertEqual(expected.tobytes(), gif.convert('RGB').tobytes())
                gif.seek(0)
                self.assertEqual(gif.convert('RGB').tobytes(), opened(PACK / f'{name}.png').convert('RGB').tobytes())
        # GIF encoders may merge consecutive held poses; check the decoded timeline.
        with Image.open(PACK / 'plants_review.gif') as gif:
            self.assertEqual(gif.info['loop'], 0)
            tick = 0
            for encoded in range(gif.n_frames):
                gif.seek(encoded)
                self.assertEqual(gif.info['duration'] % 600, 0)
                board = gif.convert('RGB')
                for phase in range(tick, tick + gif.info['duration'] // 600):
                    for index, plant in enumerate(self.recipe['plants']):
                        tile = Image.new('RGBA', (24, 24), '#70935a')
                        tile.alpha_composite(self.frames[plant['id']][phase])
                        expected = tile.convert('RGB').resize((288, 288), Image.Resampling.NEAREST)
                        x, y = 24 + index % 3 * 344, 118 + index // 3 * 350
                        self.assertEqual(expected.tobytes(), board.crop((x, y, x + 288, y + 288)).tobytes())
                    scale = Image.new('RGBA', (100, 38), '#70935a')
                    scale.alpha_composite(opened(ROOT / 'assets/characters/caelan/idle_front.png'), (2, 1))
                    scale.alpha_composite(self.frames['grass_sparse'][phase], (32, 14))
                    scale.alpha_composite(self.frames['flowers_white'][phase], (64, 14))
                    self.assertEqual(scale.convert('RGB').resize((300, 114), Image.Resampling.NEAREST).tobytes(),
                                     board.crop((24, 788, 324, 902)).tobytes())
                tick += gif.info['duration'] // 600
            self.assertEqual(tick, 9)


if __name__ == '__main__':
    unittest.main()
