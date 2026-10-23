"""Verify kitchen native exports, accessible placement and unchanged ambient clocks."""
import json
from pathlib import Path
import unittest
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/cottage_kitchen'
SOURCE=ROOT/'assets/source/terrain/eldenmere/cottage_kitchen'
INTERIOR=PACK.parent/'cottage_interior'
FURNITURE=PACK.parent/'cottage_furniture'
STORAGE=PACK.parent/'cottage_storage'
HEARTH=PACK.parent/'cottage_hearth'


def load(path):return json.loads(path.read_text())


def opened(path):
    with Image.open(path) as image:return image.convert('RGBA')


class CottageKitchenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=load(PACK/'kitchen.json');cls.room=load(PACK/'room.json')

    def test_native_parts_exact_approved_materials_alpha_and_atlas(self):
        palette=self.meta['palette'];approved=load(INTERIOR/'palette.json')['materials']
        for shade,color in approved['wood'].items():self.assertEqual(palette['wood_'+shade],color)
        for shade in ('shadow','base'):self.assertEqual(palette['iron_'+shade],approved['iron'][shade])
        self.assertEqual(palette['ceramic_light'],approved['plaster']['light'])
        colors={(*bytes.fromhex(c[1:]),255) for c in palette.values()}
        self.assertEqual({r['id'] for r in self.meta['sprites']},{'counter','washbasin','pantry'})
        atlas=opened(PACK/'sprite_sheet.png');self.assertEqual(atlas.size,(144,48))
        for r in self.meta['sprites']:
            sprite=opened(PACK/r['image']);self.assertEqual(sprite.size,tuple(r['frame_size']))
            self.assertEqual(set(sprite.getchannel('A').get_flattened_data()),{0,255})
            self.assertTrue(all(not p[3] or p in colors for p in sprite.get_flattened_data()))
            self.assertEqual(sprite.tobytes(),opened(SOURCE/'parts'/f"{r['id']}.png").tobytes())
            x,y,w,h=r['atlas_rect'];self.assertEqual(atlas.crop((x,y,x+w,y+h)).tobytes(),sprite.tobytes())
            self.assertFalse(r['animated'])
        water={(*bytes.fromhex(c[1:]),255) for key,c in palette.items() if key.startswith('water_')}
        self.assertGreater(sum(p in water for p in opened(PACK/'sprites/washbasin.png').get_flattened_data()),8)

    def test_clear_access_no_overlaps_windows_door_and_original_furnishings(self):
        layer=opened(PACK/'kitchen_layer.png');alpha=layer.getchannel('A')
        furnishings=opened(PACK/'approved_furnishings_layer.png')
        for protected in (furnishings,opened(INTERIOR/'room/fixtures.png'),opened(INTERIOR/'room/supports.png')):
            self.assertIsNone(ImageChops.multiply(alpha,protected.getchannel('A')).getbbox())
        floor=opened(INTERIOR/'room/floor.png').getchannel('A')
        for r in self.meta['sprites']:
            px,py=r['position'];x,y,w,h=r['floor_rect']
            self.assertEqual(set(floor.crop((px+x,py+y,px+x+w,py+y+h)).get_flattened_data()),{255})
        combined=ImageChops.lighter(alpha,furnishings.getchannel('A'))
        x,y,w,h=self.room['clear_path_rect'];self.assertEqual((x,y,w,h),(120,72,72,192))
        self.assertIsNone(combined.crop((x,y,x+w,y+h)).getbbox())
        x,y,w,h=self.room['entry_rect'];self.assertIsNone(combined.crop((x,y,x+w,y+h)).getbbox())
        expected=Image.new('RGBA',layer.size)
        for key,pack in [('furniture_placements',FURNITURE),('storage_placements',STORAGE)]:
            for r in self.room[key]:expected.alpha_composite(opened(pack/'sprites'/f"{r['id']}.png"),tuple(r['position']))
        self.assertEqual(expected.tobytes(),furnishings.tobytes())
        placements={r['id']:r['position'] for r in self.room['furniture_placements']}
        self.assertEqual(placements['bed'],[36,108]);self.assertEqual(placements['table'],[192,132])

    def test_room_reconstruction_and_preserved_fire_daylight_timeline(self):
        previous=load(HEARTH/'room.json');base=load(INTERIOR/'room.json')
        self.assertEqual(len(self.room['frames']),36);self.assertEqual(self.room['cycle_duration_ms'],10800)
        self.assertEqual(self.room['hero_position'],previous['hero_position'])
        structure=opened(INTERIOR/'room/structure.png');kitchen=opened(PACK/'kitchen_layer.png')
        furnishings=opened(PACK/'approved_furnishings_layer.png');hero=opened(ROOT/'assets/characters/caelan/idle_front.png')
        for r,old in zip(self.room['frames'],previous['frames'],strict=True):
            for key in ('fire_phase','daylight_phase','duration_ms'):self.assertEqual(r[key],old[key])
            self.assertEqual(opened(PACK/r['floor_glow']).tobytes(),opened(HEARTH/old['floor_glow']).tobytes())
            expected=structure.copy();expected.alpha_composite(opened(INTERIOR/base['frames'][r['daylight_phase']]['light']))
            expected.alpha_composite(opened(PACK/r['floor_glow']));expected.alpha_composite(furnishings);expected.alpha_composite(kitchen)
            expected.alpha_composite(opened(HEARTH/'frames'/f"frame_{r['fire_phase']+1:02}.png"),tuple(self.room['hearth_position']))
            expected.alpha_composite(hero,tuple(self.room['hero_position']))
            self.assertEqual(expected.tobytes(),opened(PACK/r['image']).tobytes())
        self.assertFalse(self.meta['collision_implemented']);self.assertFalse(self.meta['interaction_implemented'])

    def test_preview_gif_lossless_nearest_enlargement_and_complete_loop(self):
        tick=0
        with Image.open(PACK/'room_review.gif') as gif:
            self.assertEqual(gif.info['loop'],0);self.assertEqual(gif.size,(1152,1152))
            for index in range(gif.n_frames):
                gif.seek(index);duration=gif.info['duration'];self.assertEqual(duration%300,0)
                for phase in range(tick,tick+duration//300):
                    expected=opened(PACK/self.room['frames'][phase]['image']).convert('RGB').resize((1152,1152),Image.Resampling.NEAREST)
                    self.assertEqual(gif.convert('RGB').tobytes(),expected.tobytes())
                tick+=duration//300
            self.assertEqual(tick*300,10800)
            gif.seek(0);self.assertEqual(gif.convert('RGB').tobytes(),opened(PACK/'room_review.png').convert('RGB').tobytes())


if __name__=='__main__':unittest.main()
