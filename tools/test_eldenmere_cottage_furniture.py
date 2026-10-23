"""Verify reusable furniture exports, room access, unchanged art and GIF delivery."""
import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'assets/terrain/eldenmere/cottage_furniture'
INTERIOR = PACK.parent / 'cottage_interior'
SOURCE = ROOT / 'assets/source/terrain/eldenmere/cottage_furniture'


def load(path): return json.loads(path.read_text())


def opened(path):
    with Image.open(path) as image: return image.convert('RGBA')


class CottageFurnitureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = load(PACK/'furniture.json')
        cls.room = load(PACK/'room.json')
        cls.base = load(INTERIOR/'room.json')

    def test_native_assets_palette_alpha_source_and_atlas(self):
        palette = self.meta['palette']
        approved = load(INTERIOR/'palette.json')['materials']
        for shade in ('shadow','base','light','worn'):
            self.assertEqual(palette['wood_'+shade],approved['wood'][shade])
        self.assertEqual(palette['linen_light'],approved['plaster']['light'])
        colors = {(*bytes.fromhex(c[1:]),255) for c in palette.values()}
        self.assertEqual({r['id'] for r in self.meta['sprites']},
                         {'bed','table','chair_down','chair_up','chair_left','chair_right'})
        atlas = opened(PACK/'sprite_sheet.png')
        self.assertEqual(atlas.size,(144,144))
        for record in self.meta['sprites']:
            sprite = opened(PACK/record['image'])
            self.assertEqual(sprite.size,tuple(record['frame_size']))
            self.assertEqual(set(sprite.getchannel('A').get_flattened_data()),{0,255})
            self.assertTrue(all(not p[3] or p in colors for p in sprite.get_flattened_data()))
            self.assertGreater(sum(p[3]>0 for p in sprite.get_flattened_data()),100)
            self.assertFalse(record['animated'])
            self.assertEqual(sprite.tobytes(),opened(SOURCE/'parts'/f"{record['id']}.png").tobytes())
            x,y,w,h = record['atlas_rect']
            self.assertEqual(atlas.crop((x,y,x+w,y+h)).tobytes(),sprite.tobytes())

    def test_approved_bed_and_table_preserved_byte_for_byte(self):
        approved_hashes = {
            'bed':'7bd844ed1bf6b9c715c59f0f8e0adeab780da79313ca579451031fa907db237d',
            'table':'89e50d63c782d5ccb6dde32763ecb788a863a9c038ead9e8375ca9ecc610104a'}
        records = {r['id']:r for r in self.meta['sprites']}
        for name, expected in approved_hashes.items():
            self.assertEqual(records[name]['status'],'approved')
            for directory in (PACK/'sprites',SOURCE/'parts'):
                self.assertEqual(hashlib.sha256((directory/f'{name}.png').read_bytes()).hexdigest(),expected)
        self.assertEqual(records['bed']['position'],[36,108])
        self.assertEqual(records['table']['position'],[192,132])

    def test_four_chair_directions_compact_frames_matching_baseline_and_alias(self):
        records = [r for r in self.meta['sprites'] if r['id'].startswith('chair_')]
        self.assertEqual({r['direction'] for r in records},{'down','up','left','right'})
        frames = {r['direction']:opened(PACK/r['image']) for r in records}
        self.assertEqual(len({f.tobytes() for f in frames.values()}),4)
        wood = {(*bytes.fromhex(c[1:]),255) for key,c in self.meta['palette'].items()
                if key == 'outline' or key.startswith('wood_')}
        for frame in frames.values():
            self.assertEqual(frame.size,(24,36))
            x0,y0,x1,y1 = frame.getbbox()
            self.assertLessEqual(x1-x0,18)
            self.assertEqual(y1,34)
            self.assertTrue(all(not p[3] or p in wood for p in frame.get_flattened_data()))
        self.assertEqual(frames['right'].tobytes(),frames['left'].transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes())
        self.assertEqual(self.meta['aliases'],{'chair':'chair_down'})
        for directory in (SOURCE/'parts',PACK/'sprites'):
            self.assertEqual(opened(directory/'chair.png').tobytes(),frames['down'].tobytes())

    def test_floor_containment_clear_entry_and_continuous_central_path(self):
        layer = opened(PACK/self.room['furniture_layer'])
        floor = opened(INTERIOR/'room/floor.png').getchannel('A')
        self.assertIsNone(ImageChops.multiply(layer.getchannel('A'),ImageChops.invert(floor)).getbbox())
        x,y,w,h = self.room['clear_path_rect']
        self.assertGreaterEqual(w,24)
        self.assertEqual((y,y+h),(72,264))
        self.assertIsNone(layer.crop((x,y,x+w,y+h)).getbbox())
        ex,ey,ew,eh = self.base['entry_rect']
        self.assertTrue(x <= ex and ex+ew <= x+w)
        self.assertIsNone(layer.crop((ex,ey,ex+ew,ey+eh)).getbbox())
        # Object extents stay separate, including room for a pulled-out chair.
        occupied = Image.new('L',layer.size)
        for record in self.meta['sprites']:
            mask = opened(PACK/record['image']).getchannel('A')
            px,py = record['position']
            self.assertIsNone(ImageChops.multiply(occupied.crop((px,py,px+mask.width,py+mask.height)),mask).getbbox())
            occupied.paste(mask,(px,py),mask)
        self.assertEqual(occupied.tobytes(),layer.getchannel('A').tobytes())
        self.assertFalse(self.meta['collision_implemented'])
        self.assertFalse(self.room['exterior_transition_implemented'])

    def test_reuses_room_character_and_only_approved_daylight_changes(self):
        self.assertEqual(self.room['room_size'],self.base['room_size'])
        self.assertEqual(self.room['hero_position'],self.base['hero_position'])
        self.assertEqual(len(self.room['frames']),9)
        layer = opened(PACK/self.room['furniture_layer'])
        light_mask = Image.open(INTERIOR/'room/daylight_mask.png').convert('L')
        self.assertIsNone(ImageChops.multiply(light_mask,layer.getchannel('A')).getbbox())
        hero = opened(ROOT/'assets/characters/caelan/idle_front.png')
        self.assertEqual(hero.size,(24,36))
        first = opened(PACK/self.room['frames'][0]['image'])
        for record, base_record in zip(self.room['frames'],self.base['frames'],strict=True):
            expected = opened(INTERIOR/'room/structure.png')
            self.assertEqual(opened(PACK/record['light']).tobytes(),opened(INTERIOR/base_record['light']).tobytes())
            expected.alpha_composite(opened(PACK/record['light']))
            expected.alpha_composite(layer)
            expected.alpha_composite(hero,tuple(self.room['hero_position']))
            actual = opened(PACK/record['image'])
            self.assertEqual(actual.tobytes(),expected.tobytes())
            diff = ImageChops.difference(first.convert('RGB'),actual.convert('RGB'))
            self.assertIsNone(ImageChops.multiply(diff,ImageChops.invert(light_mask).convert('RGB')).getbbox())
            self.assertEqual(record['duration_ms'],600)

    def test_loop_complete_timing_lossless_enlargement_and_static_preview(self):
        tick = 0
        with Image.open(PACK/'room_review.gif') as gif:
            self.assertEqual(gif.info['loop'],0)
            self.assertEqual(gif.size,(1152,1152))
            for encoded in range(gif.n_frames):
                gif.seek(encoded)
                duration = gif.info['duration']
                self.assertEqual(duration%600,0)
                for phase in range(tick,tick+duration//600):
                    expected = opened(PACK/self.room['frames'][phase]['image']).convert('RGB').resize((1152,1152),Image.Resampling.NEAREST)
                    self.assertEqual(gif.convert('RGB').tobytes(),expected.tobytes())
                tick += duration//600
            self.assertEqual(tick*600,5400)
            gif.seek(0)
            self.assertEqual(gif.convert('RGB').tobytes(),opened(PACK/'room_review.png').convert('RGB').tobytes())


if __name__ == '__main__': unittest.main()
