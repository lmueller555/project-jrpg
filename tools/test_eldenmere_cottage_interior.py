"""Verify interior foundations, readable materials, clear entry and local daylight."""
import json
from pathlib import Path
import unittest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'assets/terrain/eldenmere/cottage_interior'
SOURCE = ROOT / 'assets/source/terrain/eldenmere/cottage_interior'


def load(path): return json.loads(path.read_text())


def opened(path):
    with Image.open(path) as im: return im.convert('RGBA')


class CottageInteriorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe = load(SOURCE / 'recipe.json')
        cls.meta = load(PACK / 'interior.json')
        cls.room = load(PACK / 'room.json')
        cls.palette = load(PACK / 'palette.json')

    def test_native_sizes_named_materials_source_parts_and_hard_alpha(self):
        cottage = load(PACK.parent / 'cottage/palette.json')['materials']
        for material in ('wood','plaster','glass','iron','stone'):
            self.assertEqual(self.palette['materials'][material], cottage[material])
        colors = {tuple(bytes.fromhex(c[1:])) for ramp in self.palette['materials'].values() for c in ramp.values()}
        colors |= {tuple(bytes.fromhex(c[1:])) for ramp in self.palette['daylight'] for c in ramp.values()}
        colors.add(tuple(bytes.fromhex(self.palette['void'][1:])))
        for directory in ('parts','tiles','room','lighting'):
            for path in (PACK / directory).glob('*.png'):
                im = opened(path)
                self.assertLessEqual(set(im.getchannel('A').get_flattened_data()), {0,255})
                if path.name == 'daylight_mask.png': continue
                self.assertTrue(all(not p[3] or p[:3] in colors for p in im.get_flattened_data()), path)
        for sample in self.recipe['source_samples']:
            name = sample['id'] + '.png'
            self.assertEqual(opened(PACK / 'parts' / name).size, tuple(sample['size']))
            self.assertEqual(opened(PACK / 'parts' / name).tobytes(), opened(SOURCE / 'parts' / name).tobytes())
        self.assertEqual(opened(PACK / 'parts/window.png').size, (24,30))
        self.assertEqual(opened(PACK / 'parts/door.png').size, (24,36))

    def test_distinct_quiet_floor_variants_matching_plank_rows_and_wall_joins(self):
        wood = self.palette['materials']['wood']
        base = (*bytes.fromhex(wood['base'][1:]),255)
        shadow = (*bytes.fromhex(wood['shadow'][1:]),255)
        frames = [opened(PACK / f'tiles/floor_{name}.png') for name in ('a','b','c')]
        self.assertEqual(len({f.tobytes() for f in frames}),3)
        for frame in frames:
            self.assertEqual(frame.size,(24,24))
            self.assertEqual(set(frame.getchannel('A').get_flattened_data()),{255})
            self.assertGreater(sum(p == base for p in frame.get_flattened_data()), 24*24*.65)
            for y in (0,8,16):
                self.assertGreaterEqual(sum(frame.getpixel((x,y)) == shadow for x in range(24)),16)
        for name in ('north_a','north_b'):
            im = opened(PACK / f'tiles/{name}.png')
            self.assertEqual(im.size,(24,48)); self.assertEqual(set(im.getchannel('A').get_flattened_data()),{255})
        self.assertEqual(opened(PACK/'tiles/northeast_corner.png').tobytes(), opened(PACK/'tiles/northwest_corner.png').transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes())
        self.assertEqual(opened(PACK/'tiles/east_side.png').tobytes(), opened(PACK/'tiles/west_side.png').transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes())
        atlas = opened(PACK/self.meta['tile_sheet']); self.assertEqual(atlas.size,(168,96))
        for record in self.meta['tiles']:
            x,y,w,h = record['atlas_rect']
            self.assertEqual(atlas.crop((x,y,x+w,y+h)).tobytes(),opened(PACK/record['image']).tobytes())

    def test_room_native_source_layer_and_tile_reconstruction(self):
        room = self.room
        self.assertEqual(room['room_size'],[288,288])
        self.assertEqual(self.meta['floor_size_tiles'],[10,8])
        floor = Image.new('RGBA',(288,288))
        for row in range(8):
            for col in range(10):
                name = room['floor_pattern'][(col+row*2)%3]
                floor.alpha_composite(opened(PACK / 'tiles' / f'{name}.png'),(24+col*24,72+row*24))
        self.assertEqual(floor.tobytes(),opened(PACK/'room/floor.png').tobytes())
        walls = Image.new('RGBA',floor.size)
        for record in room['wall_tile_placements']:
            walls.alpha_composite(opened(PACK/'tiles'/f"{record['tile']}.png"),tuple(record['position']))
        self.assertEqual(walls.tobytes(),opened(PACK/'room/walls.png').tobytes())
        supports = Image.new('RGBA',floor.size)
        for position in room['support_positions']: supports.alpha_composite(opened(PACK/'parts/vertical_beam.png'),tuple(position))
        self.assertEqual(supports.tobytes(),opened(PACK/'room/supports.png').tobytes())
        fixtures = Image.new('RGBA',floor.size)
        for position in room['window_positions']: fixtures.alpha_composite(opened(PACK/'parts/window.png'),tuple(position))
        fixtures.alpha_composite(opened(PACK/'parts/door.png'),tuple(room['door_position']))
        self.assertEqual(fixtures.tobytes(),opened(PACK/'room/fixtures.png').tobytes())
        expected = Image.new('RGBA',floor.size,self.recipe['void_color'])
        for layer in (floor,walls,supports,fixtures,opened(PACK/'room/contact_shadow.png')): expected.alpha_composite(layer)
        self.assertEqual(expected.tobytes(),opened(PACK/'room/structure.png').tobytes())

    def test_expanded_map_clear_entry_reused_threshold_and_original_character(self):
        self.assertEqual(self.meta['interior_scale'],'expanded_separate_room_map')
        self.assertFalse(self.meta['collision_implemented'])
        self.assertFalse(self.room['exterior_transition_implemented'])
        self.assertFalse(self.room['furniture_included'])
        self.assertEqual(self.room['floor_elevation_pixels'],0)
        x,y,w,h = self.room['entry_rect']; self.assertEqual((w,h),(24,8))
        walls = opened(PACK/'room/walls.png')
        self.assertIsNone(walls.crop((x,72,x+w,264)).getbbox())
        threshold = opened(PACK/'tiles/entry_threshold.png')
        self.assertEqual(walls.crop((x,y,x+w,y+h)).tobytes(),threshold.tobytes())
        original = opened(PACK.parent/'cottage/closed.png').crop((48,138,72,144))
        self.assertEqual(threshold.crop((0,0,24,6)).tobytes(),original.tobytes())
        hero = opened(ROOT/'assets/characters/caelan/idle_front.png'); self.assertEqual(hero.size,(24,36))
        px,py = self.room['hero_position']
        self.assertTrue(24 <= px and px+24 <= 264 and 72 <= py and py+36 < 264)
        for record in self.room['frames']:
            actual = opened(PACK/record['image'])
            for yy in range(36):
                for xx in range(24):
                    color = hero.getpixel((xx,yy))
                    if color[3]: self.assertEqual(actual.getpixel((px+xx,py+yy)),color)

    def test_daylight_fixed_geometry_floor_locality_and_scene_reconstruction(self):
        self.assertFalse(self.meta['structure_moves'])
        self.assertFalse(self.room['daylight']['geometry_moves'])
        self.assertEqual(self.room['cycle_duration_ms'],5400)
        structure = opened(PACK/'room/structure.png')
        floor = opened(PACK/'room/floor.png')
        mask = Image.open(PACK/'room/daylight_mask.png').convert('L')
        self.assertEqual(set(mask.get_flattened_data()),{0,255})
        self.assertIsNone(ImageChops.multiply(mask,ImageChops.invert(floor.getchannel('A'))).getbbox())
        self.assertGreater(sum(bool(p) for p in mask.get_flattened_data()),300)
        light_colors = {(*bytes.fromhex(c[1:]),255) for ramp in self.palette['daylight'] for c in ramp.values()}
        hero = opened(ROOT/'assets/characters/caelan/idle_front.png'); unique=set()
        self.assertEqual(len(self.room['frames']),9)
        for record in self.room['frames']:
            self.assertEqual(record['duration_ms'],600)
            overlay = opened(PACK/record['light']); self.assertEqual(overlay.getchannel('A').tobytes(),mask.tobytes())
            self.assertTrue(all(not p[3] or p in light_colors for p in overlay.get_flattened_data()))
            expected = structure.copy(); expected.alpha_composite(overlay); unique.add(expected.tobytes())
            diff = ImageChops.difference(expected.convert('RGB'),structure.convert('RGB'))
            self.assertIsNone(ImageChops.multiply(diff,ImageChops.invert(mask).convert('RGB')).getbbox())
            expected.alpha_composite(hero,tuple(self.room['hero_position']))
            self.assertEqual(expected.tobytes(),opened(PACK/record['image']).tobytes())
        self.assertEqual(len(unique),3)

    def test_enlarged_gif_lossless_pixels_complete_timeline_and_loop(self):
        tick = 0
        with Image.open(PACK/'room_review.gif') as gif:
            self.assertEqual(gif.info['loop'],0)
            for encoded in range(gif.n_frames):
                gif.seek(encoded); duration = gif.info['duration']; self.assertEqual(duration%600,0)
                actual = gif.convert('RGB')
                for phase in range(tick,tick+duration//600):
                    expected = opened(PACK/self.room['frames'][phase]['image']).convert('RGB').resize((1152,1152),Image.Resampling.NEAREST)
                    self.assertEqual(actual.tobytes(),expected.tobytes())
                tick += duration//600
            self.assertEqual(tick,9)
            gif.seek(0); self.assertEqual(gif.convert('RGB').tobytes(),opened(PACK/'room_review.png').convert('RGB').tobytes())


if __name__ == '__main__': unittest.main()
