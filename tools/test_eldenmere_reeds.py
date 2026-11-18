"""Verify connected reed motion, dry bank anchors and lossless scene delivery."""
import json
from pathlib import Path
import unittest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'assets/terrain/eldenmere/reeds'
SOURCE = ROOT / 'assets/source/terrain/eldenmere/reeds'
PREVIOUS = PACK.parent / 'grass_flowers'


def load(path):
    return json.loads(path.read_text())


def opened(path):
    with Image.open(path) as image:
        return image.convert('RGBA')


class ReedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe = load(SOURCE / 'recipe.json')
        cls.scene = load(PACK / 'review_scene.json')
        cls.metadata = {p['id']: load(PACK / p['id'] / 'reeds.json') for p in cls.recipe['plants']}
        cls.frames = {name: [opened(PACK / name / f['image']) for f in meta['wind']['frames']]
                      for name, meta in cls.metadata.items()}
        cls.unions = {}
        for name, frames in cls.frames.items():
            union = Image.new('L', frames[0].size)
            for frame in frames:
                union = ImageChops.lighter(union, frame.getchannel('A'))
            cls.unions[name] = union

    def test_native_palette_alpha_source_rest_and_registration(self):
        self.assertEqual(set(self.metadata), {'tall', 'short'})
        palette = load(PACK / 'palette.json')['materials']
        self.assertEqual(palette['greens'], load(PACK.parent / 'foliage/palette.json')['materials']['leaves'])
        self.assertEqual(palette['seedheads'], load(PACK.parent / 'cottage/palette.json')['materials']['wood'])
        colors = {tuple(bytes.fromhex(c[1:])) for ramp in palette.values() for c in ramp.values()}
        seed_colors = {(*bytes.fromhex(c[1:]), 255) for c in palette['seedheads'].values()}
        for name, meta in self.metadata.items():
            w, h = (24, 48) if name == 'tall' else (24, 24)
            self.assertEqual(meta['frame_size'], [w, h])
            self.assertEqual(meta['tile_size'], [24, 24])
            self.assertEqual(meta['ground_rect'], [0, h - 24, 24, 24])
            self.assertEqual(meta['placement'], 'dry_bank')
            self.assertFalse(meta['collision'])
            rest = self.frames[name][0]
            self.assertEqual(opened(SOURCE / f'parts/{name}_native.png').tobytes(), rest.tobytes())
            self.assertEqual(opened(PACK / name / 'idle.png').tobytes(), rest.tobytes())
            self.assertEqual(opened(PACK / name / 'sheet.png').size, (216, h))
            self.assertEqual(any(p in seed_colors for p in rest.get_flattened_data()), name == 'tall')
            for path in (PACK / name).rglob('*.png'):
                image = opened(path)
                self.assertLessEqual(set(image.getchannel('A').get_flattened_data()), {0, 255})
                self.assertTrue(all(not p[3] or p[:3] in colors for p in image.get_flattened_data()), path)

    def test_fixed_roots_exact_band_motion_and_sheet_reconstruction(self):
        for name, meta in self.metadata.items():
            wind = meta['wind']
            self.assertEqual(wind['direction'], 'E')
            self.assertEqual(wind['max_displacement_pixels'], [1, 0])
            self.assertFalse(wind['whole_plant_moves'])
            self.assertTrue(wind['loop'])
            self.assertEqual(sum(f['duration_ms'] for f in wind['frames']), 5400)
            base = opened(PACK / name / meta['fixed_base'])
            sheet = opened(PACK / name / 'sheet.png')
            rest = self.frames[name][0]
            self.assertIsNotNone(base.getbbox())
            self.assertGreaterEqual(len({f.tobytes() for f in self.frames[name]}), 6)
            for phase, (record, actual) in enumerate(zip(wind['frames'], self.frames[name], strict=True)):
                expected = Image.new('RGBA', rest.size)
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
                root_rect = (0, meta['fixed_rows_from'], 24, rest.height)
                self.assertEqual(actual.crop(root_rect).tobytes(), rest.crop(root_rect).tobytes())
                self.assertEqual(sheet.crop((phase * 24, 0, (phase + 1) * 24, rest.height)).tobytes(), actual.tobytes())
                self.assertIsNone(ImageChops.multiply(ImageChops.difference(actual.convert('RGB'), rest.convert('RGB')),
                                                     base.getchannel('A').convert('RGB')).getbbox())

    def test_stalks_leaves_and_seedheads_remain_connected_and_unclipped(self):
        for name, frames in self.frames.items():
            for phase, frame in enumerate(frames):
                left, top, right, bottom = frame.getbbox()
                self.assertTrue(0 < left < right <= frame.width and 0 < top < bottom < frame.height)
                pixels = {(x, y) for y in range(frame.height) for x in range(frame.width) if frame.getpixel((x, y))[3]}
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

    def test_dry_bank_anchors_near_water_and_clearance_in_every_scene_phase(self):
        ground = PACK.parent / 'grass_dirt'
        grass = {p for path in load(ground / 'tileset.json')['grass']['images']
                 for p in opened(ground / path).get_flattened_data()}
        coverage = Image.new('L', (768, 1296))
        first = opened(PREVIOUS / 'scene_frames/frame_01.png')
        water = {(*bytes.fromhex(c[1:]), 255) for key, c in load(PACK.parent / 'stream/palette.json')['materials']['water'].items()
                 if key in ('base', 'deep', 'flow')}
        self.assertEqual(len(self.scene['instances']), 7)
        for instance in self.scene['instances']:
            self.assertEqual(instance['ground_elevation_pixels'], 24)
            if 'water_surface_elevation_pixels' in instance:
                self.assertGreater(instance['ground_elevation_pixels'], instance['water_surface_elevation_pixels'])
            x, y = instance['position']
            meta = self.metadata[instance['plant']]
            gx, gy, w, h = meta['ground_rect']
            for yy in range(y + gy, y + gy + h):
                for xx in range(x + gx, x + gx + w):
                    self.assertIn(first.getpixel((xx, yy)), grass, instance)
            root_x, root_y = x + 12, y + meta['frame_size'][1] - 3
            self.assertTrue(any(first.getpixel((xx, yy)) in water
                                for yy in range(max(0, root_y - 32), min(first.height, root_y + 33))
                                for xx in range(max(0, root_x - 32), min(first.width, root_x + 33))), instance)
            layer = Image.new('L', coverage.size)
            layer.paste(self.unions[instance['plant']], (x, y))
            self.assertIsNone(ImageChops.multiply(layer, coverage).getbbox(), instance)
            coverage = ImageChops.lighter(coverage, layer)
        points = [(x, y) for y in range(coverage.height) for x in range(coverage.width) if coverage.getpixel((x, y))]
        for tick in range(54):
            previous = opened(PREVIOUS / f'scene_frames/frame_{tick + 1:02}.png')
            self.assertTrue(all(previous.getpixel(p) in grass for p in points), f'Non-grass coverage at phase {tick}')
        self.assertEqual(self.scene['wind_direction'], load(PREVIOUS / 'review_scene.json')['wind_direction'])

    def test_scene_exact_reconstruction_and_shared_timing(self):
        self.assertEqual(len(self.scene['frames']), 54)
        self.assertEqual(self.scene['cycle_duration_ms'], 10800)
        self.assertEqual(self.scene['reeds_cycle_duration_ms'], 5400)
        self.assertEqual(self.scene['instances'], self.recipe['instances'])
        for tick, record in enumerate(self.scene['frames']):
            self.assertEqual(record['base_phase'], tick)
            self.assertEqual(record['duration_ms'], 200)
            expected = opened(PREVIOUS / f'scene_frames/frame_{tick + 1:02}.png')
            for instance, phase in zip(self.scene['instances'], record['reed_phases'], strict=True):
                self.assertEqual(phase, (tick // 3 + instance['phase_offset']) % 9)
                expected.alpha_composite(self.frames[instance['plant']][phase], tuple(instance['position']))
            actual = opened(PACK / record['image'])
            self.assertEqual(actual.size, (768, 1296))
            self.assertEqual(expected.tobytes(), actual.tobytes())

    def test_gif_lossless_pixels_durations_and_matching_character_scale(self):
        review = self.scene['review']
        for name, crop, scale in (('review_scene', None, review['scene_scale']),
                                  ('banks_closeup', review['closeup_rect'], review['closeup_scale'])):
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
        with Image.open(PACK / 'reeds_review.gif') as gif:
            self.assertEqual(gif.info['loop'], 0)
            tick = 0
            for encoded in range(gif.n_frames):
                gif.seek(encoded)
                self.assertEqual(gif.info['duration'] % 600, 0)
                board = gif.convert('RGB')
                for phase in range(tick, tick + gif.info['duration'] // 600):
                    for name, x in (('tall', 24), ('short', 400)):
                        frame = self.frames[name][phase]
                        tile = Image.new('RGBA', frame.size, '#70935a')
                        tile.alpha_composite(frame)
                        expected = tile.convert('RGB').resize((288, frame.height * 12), Image.Resampling.NEAREST)
                        self.assertEqual(expected.tobytes(), board.crop((x, 94, x + 288, 94 + frame.height * 12)).tobytes())
                    scale = Image.new('RGBA', (96, 56), '#70935a')
                    scale.alpha_composite(opened(ROOT / 'assets/characters/caelan/idle_front.png'), (2, 17))
                    scale.alpha_composite(self.frames['tall'][phase], (36, 6))
                    scale.alpha_composite(self.frames['short'][phase], (68, 30))
                    self.assertEqual(scale.convert('RGB').resize((576, 336), Image.Resampling.NEAREST).tobytes(),
                                     board.crop((512, 430, 1088, 766)).tobytes())
                tick += gif.info['duration'] // 600
            self.assertEqual(tick, 9)


if __name__ == '__main__':
    unittest.main()
