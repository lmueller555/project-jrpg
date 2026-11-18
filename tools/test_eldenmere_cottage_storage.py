"""Verify storage materials, wall mounting, room access and exact preview delivery."""
import json
from pathlib import Path
import unittest
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT/'assets/terrain/eldenmere/cottage_storage'
SOURCE = ROOT/'assets/source/terrain/eldenmere/cottage_storage'
INTERIOR = PACK.parent/'cottage_interior'
FURNITURE = PACK.parent/'cottage_furniture'


def load(path): return json.loads(path.read_text())


def opened(path):
    with Image.open(path) as image: return image.convert('RGBA')


class CottageStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = load(PACK/'storage.json')
        cls.room = load(PACK/'room.json')
        cls.base = load(FURNITURE/'room.json')

    def test_native_sizes_palette_binary_alpha_atlas_and_readable_handles(self):
        palette = self.meta['palette']
        approved = load(INTERIOR/'palette.json')['materials']
        for material in ('wood','iron'):
            for shade,color in approved[material].items():
                self.assertEqual(palette[material+'_'+shade],color)
        colors = {(*bytes.fromhex(c[1:]),255) for c in palette.values()}
        self.assertEqual({r['id'] for r in self.meta['sprites']},{'shelf','cupboard'})
        atlas = opened(PACK/'sprite_sheet.png'); self.assertEqual(atlas.size,(96,48))
        for record in self.meta['sprites']:
            sprite = opened(PACK/record['image'])
            self.assertEqual(sprite.size,(48,24) if record['id']=='shelf' else (48,48))
            self.assertEqual(set(sprite.getchannel('A').get_flattened_data()),{0,255})
            self.assertTrue(all(not p[3] or p in colors for p in sprite.get_flattened_data()))
            self.assertEqual(sprite.tobytes(),opened(SOURCE/'parts'/f"{record['id']}.png").tobytes())
            x,y,w,h = record['atlas_rect']
            self.assertEqual(atlas.crop((x,y,x+w,y+h)).tobytes(),sprite.tobytes())
            self.assertFalse(record['animated'])
        cupboard = opened(PACK/'sprites/cupboard.png')
        iron = {(*bytes.fromhex(c[1:]),255) for key,c in palette.items() if key.startswith('iron_')}
        for rect in ((20,22,23,29),(25,22,28,29)):
            self.assertGreaterEqual(sum(p in iron for p in cupboard.crop(rect).get_flattened_data()),3)

    def test_placement_preserves_windows_door_furniture_entry_and_path(self):
        layer = opened(PACK/'storage_layer.png'); alpha = layer.getchannel('A')
        fixtures = opened(INTERIOR/'room/fixtures.png').getchannel('A')
        supports = opened(INTERIOR/'room/supports.png').getchannel('A')
        furniture = opened(FURNITURE/'furniture_layer.png').getchannel('A')
        for protected in (fixtures,supports,furniture):
            self.assertIsNone(ImageChops.multiply(alpha,protected).getbbox())
        x,y,w,h = self.room['clear_path_rect']
        self.assertEqual((x,y,w,h),(120,72,72,192))
        self.assertIsNone(alpha.crop((x,y,x+w,y+h)).getbbox())
        ex,ey,ew,eh = self.room['entry_rect']
        self.assertIsNone(alpha.crop((ex,ey,ex+ew,ey+eh)).getbbox())
        expected = Image.new('RGBA',layer.size)
        floor = opened(INTERIOR/'room/floor.png').getchannel('A')
        for record in self.meta['sprites']:
            sprite = opened(PACK/record['image']); px,py = record['position']
            expected.alpha_composite(sprite,(px,py))
            if record['id']=='cupboard':
                fx,fy,fw,fh = record['floor_rect']
                self.assertEqual(set(floor.crop((px+fx,py+fy,px+fx+fw,py+fy+fh)).get_flattened_data()),{255})
            else:
                x0,y0,x1,y1 = sprite.getbbox()
                self.assertTrue(102 <= px+x0 < px+x1 <= 144)
                self.assertTrue(24 <= py+y0 < py+y1 <= 72)
        self.assertEqual(layer.tobytes(),expected.tobytes())
        self.assertFalse(self.meta['collision_implemented'])
        self.assertFalse(self.meta['door_interaction_implemented'])
        self.assertFalse(self.room['hearth_included'])

    def test_only_new_storage_changes_approved_scene_and_animation_stays_local(self):
        self.assertEqual(self.room['room_size'],self.base['room_size'])
        self.assertEqual(self.room['hero_position'],self.base['hero_position'])
        self.assertEqual(len(self.room['frames']),9)
        layer = opened(PACK/'storage_layer.png')
        mask = layer.getchannel('A')
        light = Image.open(INTERIOR/'room/daylight_mask.png').convert('L')
        first = opened(PACK/self.room['frames'][0]['image']).convert('RGB')
        hero = opened(ROOT/'assets/characters/caelan/idle_front.png')
        px,py = self.room['hero_position']
        self.assertIsNone(mask.crop((px,py,px+24,py+36)).getbbox())
        for record,previous in zip(self.room['frames'],self.base['frames'],strict=True):
            self.assertEqual(record['duration_ms'],600)
            old = opened(FURNITURE/previous['image'])
            expected = old.copy(); expected.alpha_composite(layer)
            actual = opened(PACK/record['image'])
            self.assertEqual(actual.tobytes(),expected.tobytes())
            diff = ImageChops.difference(actual.convert('RGB'),old.convert('RGB'))
            self.assertIsNone(ImageChops.multiply(diff,ImageChops.invert(mask).convert('RGB')).getbbox())
            motion = ImageChops.difference(first,actual.convert('RGB'))
            self.assertIsNone(ImageChops.multiply(motion,ImageChops.invert(light).convert('RGB')).getbbox())
            self.assertIsNone(ImageChops.multiply(motion,mask.convert('RGB')).getbbox())
            for yy in range(36):
                for xx in range(24):
                    color = hero.getpixel((xx,yy))
                    if color[3]: self.assertEqual(actual.getpixel((px+xx,py+yy)),color)

    def test_loop_lossless_enlargement_complete_timing_and_still(self):
        tick = 0
        with Image.open(PACK/'room_review.gif') as gif:
            self.assertEqual(gif.info['loop'],0)
            self.assertEqual(gif.size,(1152,1152))
            for index in range(gif.n_frames):
                gif.seek(index); duration = gif.info['duration']
                self.assertEqual(duration%600,0)
                for phase in range(tick,tick+duration//600):
                    expected = opened(PACK/self.room['frames'][phase]['image']).convert('RGB').resize((1152,1152),Image.Resampling.NEAREST)
                    self.assertEqual(gif.convert('RGB').tobytes(),expected.tobytes())
                tick += duration//600
            self.assertEqual(tick*600,5400)
            gif.seek(0)
            self.assertEqual(gif.convert('RGB').tobytes(),opened(PACK/'room_review.png').convert('RGB').tobytes())


if __name__ == '__main__': unittest.main()
