"""Verify hearth geometry, restrained local animation, placement and complete GIFs."""
import json
from pathlib import Path
import unittest
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/cottage_hearth'
SOURCE=ROOT/'assets/source/terrain/eldenmere/cottage_hearth'
INTERIOR=PACK.parent/'cottage_interior'
FURNITURE=PACK.parent/'cottage_furniture'
STORAGE=PACK.parent/'cottage_storage'


def load(path):return json.loads(path.read_text())


def opened(path):
    with Image.open(path) as image:return image.convert('RGBA')


class CottageHearthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=load(PACK/'hearth.json');cls.room=load(PACK/'room.json')
        cls.recipe=load(SOURCE/'recipe.json');cls.previous=load(STORAGE/'room.json')

    def test_native_source_parts_materials_alpha_and_atlas(self):
        approved=load(INTERIOR/'palette.json')['materials']
        for key,color in approved['stone'].items():self.assertEqual(self.meta['palette']['stone_'+key],color)
        self.assertEqual(self.meta['frame_size'],[48,72])
        colors={(*bytes.fromhex(c[1:]),255) for c in self.meta['palette'].values()}
        for record in self.recipe['samples']:
            part=opened(PACK/'parts'/f"{record['id']}.png")
            self.assertEqual(part.size,tuple(record['size']))
            self.assertLessEqual(set(part.getchannel('A').get_flattened_data()),{0,255})
            self.assertTrue(all(not p[3] or p in colors for p in part.get_flattened_data()))
            self.assertEqual(part.tobytes(),opened(SOURCE/'parts'/f"{record['id']}.png").tobytes())
        atlas=opened(PACK/'sprite_sheet.png');self.assertEqual(atlas.size,(192,72))
        self.assertEqual(len(self.meta['frames']),4)
        for record in self.meta['frames']:
            frame=opened(PACK/record['image']);self.assertEqual(frame.size,(48,72))
            self.assertLessEqual(set(frame.getchannel('A').get_flattened_data()),{0,255})
            x,y,w,h=record['atlas_rect']
            self.assertEqual(atlas.crop((x,y,x+w,y+h)).tobytes(),frame.tobytes())

    def test_fixed_body_logs_and_motion_confined_to_fire_embers_and_rim(self):
        body=opened(PACK/self.meta['static_base'])
        masks={name:Image.open(PACK/path).convert('L') for name,path in self.meta['animation_masks'].items()}
        allowed=Image.new('L',body.size)
        for mask in masks.values():
            self.assertIsNotNone(mask.getbbox())
            self.assertLessEqual(set(mask.get_flattened_data()),{0,255})
            allowed=ImageChops.lighter(allowed,mask)
        x,y,w,h=self.meta['opening_rect']
        opening=Image.new('L',body.size);opening.paste(255,(x,y,x+w,y+h))
        self.assertIsNone(ImageChops.multiply(masks['fire'],ImageChops.invert(opening)).getbbox())
        frames=[opened(PACK/r['image']) for r in self.meta['frames']]
        self.assertEqual(len({f.tobytes() for f in frames}),4)
        self.assertEqual(len({opened(PACK/'parts'/f'flame_{i+1:02}.png').tobytes() for i in range(4)}),4)
        for frame in frames:
            self.assertEqual(frame.getchannel('A').tobytes(),body.getchannel('A').tobytes())
            diff=ImageChops.difference(frame.convert('RGB'),body.convert('RGB'))
            self.assertIsNone(ImageChops.multiply(diff,ImageChops.invert(allowed).convert('RGB')).getbbox())
            self.assertEqual(frame.crop((0,0,48,36)).tobytes(),body.crop((0,0,48,36)).tobytes())
        self.assertFalse(self.meta['structure_moves']);self.assertFalse(self.meta['logs_move'])
        self.assertFalse(self.meta['smoke_included'])
        self.assertLessEqual(max(self.meta['glow_strengths']),.1)

    def test_window_door_furniture_character_and_path_remain_clear(self):
        mask=Image.new('L',(288,288));body=opened(PACK/'structure.png')
        px,py=self.room['hearth_position'];mask.paste(body.getchannel('A'),(px,py))
        glow=Image.open(PACK/'masks/floor_glow.png').convert('L')
        floor=opened(INTERIOR/'room/floor.png').getchannel('A')
        self.assertEqual(set(glow.get_flattened_data()),{0,128,255})
        self.assertIsNone(ImageChops.multiply(glow,ImageChops.invert(floor)).getbbox())
        for path in (INTERIOR/'room/fixtures.png',INTERIOR/'room/supports.png',FURNITURE/'furniture_layer.png',STORAGE/'storage_layer.png'):
            protected=opened(path).getchannel('A')
            self.assertIsNone(ImageChops.multiply(mask,protected).getbbox(),path)
        for path in (FURNITURE/'furniture_layer.png',STORAGE/'storage_layer.png'):
            self.assertIsNone(ImageChops.multiply(glow,opened(path).getchannel('A')).getbbox())
        combined=ImageChops.lighter(mask,glow)
        x,y,w,h=self.room['clear_path_rect']
        self.assertEqual((x,y,w,h),(120,72,72,192))
        self.assertIsNone(combined.crop((x,y,x+w,y+h)).getbbox())
        x,y,w,h=self.room['entry_rect'];self.assertIsNone(combined.crop((x,y,x+w,y+h)).getbbox())
        x,y=self.room['hero_position'];self.assertIsNone(combined.crop((x,y,x+24,y+36)).getbbox())
        x,y,w,h=self.room['hearth_floor_rect']
        self.assertEqual(set(floor.crop((px+x,py+y,px+x+w,py+y+h)).get_flattened_data()),{255})

    def test_scene_reconstruction_locality_and_independent_daylight_timing(self):
        self.assertEqual(self.room['room_size'],[288,288]);self.assertEqual(len(self.room['frames']),36)
        self.assertEqual(self.room['cycle_duration_ms'],10800)
        self.assertEqual(self.room['fire_cycle_duration_ms'],1200)
        self.assertEqual(self.room['daylight_cycle_duration_ms'],5400)
        px,py=self.room['hearth_position']
        coverage=Image.new('L',(288,288));coverage.paste(opened(PACK/'structure.png').getchannel('A'),(px,py))
        floor_mask=Image.open(PACK/'masks/floor_glow.png').convert('L').point(lambda p:255 if p else 0)
        allowed=ImageChops.lighter(coverage,floor_mask)
        for tick,record in enumerate(self.room['frames']):
            self.assertEqual(record['duration_ms'],300)
            self.assertEqual(record['fire_phase'],tick%4)
            self.assertEqual(record['daylight_phase'],tick//2%9)
            previous=opened(STORAGE/self.previous['frames'][record['daylight_phase']]['image'])
            expected=previous.copy();overlay=opened(PACK/record['floor_glow'])
            self.assertLessEqual(set(overlay.getchannel('A').get_flattened_data()),{0,255})
            self.assertEqual(overlay.getchannel('A').tobytes(),floor_mask.tobytes())
            expected.alpha_composite(overlay)
            expected.alpha_composite(opened(PACK/self.meta['frames'][record['fire_phase']]['image']),(px,py))
            actual=opened(PACK/record['image']);self.assertEqual(actual.tobytes(),expected.tobytes())
            diff=ImageChops.difference(previous.convert('RGB'),actual.convert('RGB'))
            self.assertIsNone(ImageChops.multiply(diff,ImageChops.invert(allowed).convert('RGB')).getbbox())
        self.assertFalse(self.meta['collision_implemented'])

    def test_lossless_room_and_hearth_loops_complete_timing_and_nearest_pixels(self):
        for filename,records,scale,duration in [('room_review.gif',self.room['frames'],4,10800),('hearth_review.gif',self.meta['frames'],8,1200)]:
            tick=0
            with Image.open(PACK/filename) as gif:
                self.assertEqual(gif.info['loop'],0)
                for index in range(gif.n_frames):
                    gif.seek(index);held=gif.info['duration'];self.assertEqual(held%300,0)
                    for phase in range(tick,tick+held//300):
                        native=opened(PACK/records[phase]['image']).convert('RGB')
                        if filename=='hearth_review.gif':
                            cell=Image.new('RGBA',native.size,'#c5c2b4');cell.alpha_composite(opened(PACK/records[phase]['image']));native=cell.convert('RGB')
                        expected=native.resize((native.width*scale,native.height*scale),Image.Resampling.NEAREST)
                        self.assertEqual(gif.convert('RGB').tobytes(),expected.tobytes())
                    tick+=held//300
                self.assertEqual(tick*300,duration)
                if filename=='room_review.gif':
                    gif.seek(0);self.assertEqual(gif.convert('RGB').tobytes(),opened(PACK/'room_review.png').convert('RGB').tobytes())


if __name__=='__main__':unittest.main()
