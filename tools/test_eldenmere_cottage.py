"""Check cottage reuse, door anchoring, smoke motion and lossless scene delivery."""
import json
from pathlib import Path
import unittest
from PIL import Image, ImageChops, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/cottage'
MILL=PACK.parent/'watermill'
SOURCE=ROOT/'assets/source/terrain/eldenmere/cottage'


def load(p): return json.loads(p.read_text())
def opened(p): return Image.open(p).convert('RGBA')


class CottageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=load(PACK/'cottage.json'); cls.scene=load(PACK/'review_scene.json')
        cls.palette=load(PACK/'palette.json')['materials']; cls.recipe=load(SOURCE/'recipe.json')

    def test_native_materials_component_reconstruction_and_reuse(self):
        self.assertEqual(self.meta['tile_size'],[24,24]); self.assertEqual(self.meta['ground_rect'],[12,72,96,72])
        for name,ramp in load(MILL/'palette.json')['materials'].items(): self.assertEqual(self.palette[name],ramp)
        allowed={tuple(bytes.fromhex(c[1:])) for r in self.palette.values() for c in r.values()}
        for folder in ('parts','doors','smoke','lantern','preview_frames'):
            for path in (PACK/folder).glob('*.png'):
                image=opened(path)
                self.assertLessEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
                self.assertTrue(all(not p[3] or p[:3] in allowed for p in image.get_flattened_data()),path.name)
        native=opened(SOURCE/'parts/building_native.png'); assembled=Image.new('RGBA',native.size)
        for c in self.meta['components']: assembled.alpha_composite(opened(PACK/c['image']),tuple(c['rect'][:2]))
        self.assertEqual(native.tobytes(),assembled.tobytes())
        self.assertEqual(opened(PACK/'parts/roof_repeat.png').size,(24,45))
        panel=opened(PACK/'parts/wall_blank.png'); self.assertEqual(panel.size,(24,43))
        self.assertEqual(set(panel.getchannel('A').get_flattened_data()),{255})
        # Every lit-window change is inside an original glass pixel; framing stays identical.
        glass={(*bytes.fromhex(c[1:]),255) for c in self.palette['glass'].values()}
        for name in ('window_left','window_right'):
            day=opened(PACK/f'parts/{name}.png'); lit=opened(PACK/f'parts/{name}_lit.png'); changed=0
            for a,b in zip(day.get_flattened_data(),lit.get_flattened_data()):
                if a!=b: self.assertIn(a,glass); self.assertEqual(a[3],b[3]); changed+=1
            self.assertGreater(changed,0)

    def test_triggered_door_hinge_and_static_structure(self):
        door=self.meta['door']; self.assertFalse(door['opening']['loop']); self.assertFalse(door['closing']['loop'])
        self.assertEqual(door['closing']['frames'],list(reversed(door['opening']['frames'])))
        frames=[opened(PACK/f['image']) for f in door['opening']['frames']]
        x,y=door['position']; w,h=door['size']
        for width,image,info in zip((13,10,6,3,1),frames,door['opening']['frames'],strict=True):
            self.assertEqual(image.getbbox(),(x,y,x+width,y+h)); self.assertEqual(info['duration_ms'],100)
        base=opened(PACK/self.meta['structure'])
        for tick in range(18):
            actual=opened(PACK/f'preview_frames/frame_{tick+1:02}.png')
            expected=base.copy(); index=self.scene['frames'][tick]['door_frame']
            expected.alpha_composite(frames[index]); expected.alpha_composite(opened(PACK/f'lantern/frame_{tick+1:02}.png'))
            expected.alpha_composite(opened(PACK/f'smoke/frame_{tick+1:02}.png'))
            self.assertEqual(actual.tobytes(),expected.tobytes())
        for state,index in (('closed',0),('open',4)):
            expected=base.copy();expected.alpha_composite(frames[index]);expected.alpha_composite(opened(PACK/'lantern/frame_01.png'))
            self.assertEqual(expected.tobytes(),opened(PACK/f'{state}.png').tobytes())
        sheet=opened(PACK/'door_sheet.png'); self.assertEqual(sheet.size,(600,144))
        for index,leaf in enumerate(frames):
            expected=base.copy();expected.alpha_composite(leaf);expected.alpha_composite(opened(PACK/'lantern/frame_01.png'))
            self.assertEqual(expected.tobytes(),sheet.crop((index*120,0,(index+1)*120,144)).tobytes())

    def test_observed_smoke_rise_east_drift_thinning_and_lantern_anchor(self):
        smoke=self.meta['smoke']; self.assertEqual(smoke['cycle_duration_ms'],3600)
        self.assertEqual(smoke['direction'],'east');self.assertTrue(smoke['optional'])
        unique=set()
        for index,record in enumerate(smoke['frames']):
            image=opened(PACK/record['image']);unique.add(image.tobytes())
            for particle in record['particles']:
                age=particle['age']; x,y=particle['center']
                self.assertEqual((x,y),(90+age//2,47-2*age))
                crop=image.crop((x-3,y-2,x+4,y+3)).getchannel('A')
                if age<17: self.assertIsNotNone(crop.getbbox())
                else: self.assertIsNone(crop.getbbox())
                if age>=13: self.assertLessEqual(sum(bool(v) for v in crop.get_flattened_data()),5)
            bbox=image.getbbox(); self.assertTrue(87<=bbox[0]<bbox[2]<=101 and 12<=bbox[1]<bbox[3]<=49)
            lantern=opened(PACK/f'lantern/frame_{index+1:02}.png')
            # The bracket crop stays attached while the lower light moves.
            fixed=opened(PACK/'lantern/frame_01.png').crop((68,107,76,112))
            self.assertEqual(fixed.tobytes(),lantern.crop((68,107,76,112)).tobytes())
        self.assertEqual(len(unique),18)
        # Follow one tagged puff between resets: actual occupied patches move up/east.
        centers=[record['particles'][0]['center'] for record in smoke['frames']]
        for a,b in zip(centers,centers[1:]): self.assertLess(b[1],a[1]);self.assertGreaterEqual(b[0],a[0])

    def test_dry_level_approach_and_unchanged_previous_scene(self):
        scene=self.scene; self.assertEqual(scene['elevations']['ground'],scene['elevations']['threshold'])
        position=scene['position']; x,y,w,h=self.meta['ground_rect']; px,py=position
        ground=(px+x,py+y,px+x+w,py+y+h)
        fx,fy=scene['doorway_foot'];self.assertTrue(ground[0]<=fx<ground[2] and ground[1]<=fy<ground[3])
        path={tuple(p) for p in scene['path_cells']};joins=path|{tuple(p) for p in scene['path_join_cells']}
        reached={next(iter(path))}
        while True:
            grown=reached|{(x+dx,y+dy) for x,y in reached for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)) if (x+dx,y+dy) in joins}
            if grown==reached:break
            reached=grown
        self.assertTrue(joins<=reached)
        stream=load(PACK.parent/'stream/review_scene.json'); mill=load(MILL/'review_scene.json')
        corridor={tuple(p['cell']) for p in mill['race']}
        for x,y in joins|{(xx,yy) for xx in range(ground[0]//24,(ground[2]-1)//24+1) for yy in range(ground[1]//24,(ground[3]-1)//24+1)}:
            self.assertNotIn((x,y),corridor)
            if y<len(stream['water_masks']) and x<len(stream['water_masks'][y]): self.assertIsNone(stream['water_masks'][y][x])
        paths=opened(PACK/'review_path.png'); self.assertEqual(paths.getpixel((fx,fy))[3],255)
        for tick,record in enumerate(scene['frames']):
            previous=opened(MILL/f"scene_running/frame_{record['water_phase']+1:02}.png")
            frame=opened(PACK/f'preview_frames/frame_{tick+1:02}.png')
            expected=previous.copy();expected.alpha_composite(paths);expected.alpha_composite(frame,tuple(position))
            actual=opened(PACK/record['image']);self.assertEqual(expected.tobytes(),actual.tobytes())
            allowed=paths.getchannel('A').copy(); coverage=Image.new('L',previous.size); coverage.paste(frame.getchannel('A'),tuple(position));allowed=ImageChops.lighter(allowed,coverage)
            diff=ImageChops.difference(previous.convert('RGB'),actual.convert('RGB'))
            self.assertIsNone(ImageChops.multiply(diff,ImageChops.invert(allowed).convert('RGB')).getbbox())

    def test_review_gifs_exact_pixels_and_timing(self):
        for name,scale,crop in (('review_scene',3,None),('cottage_closeup',5,self.scene['review']['closeup_rect'])):
            with Image.open(PACK/f'{name}.gif') as gif:
                self.assertEqual(gif.n_frames,18);self.assertEqual(gif.info['loop'],0)
                for tick,record in enumerate(self.scene['frames']):
                    expected=Image.open(PACK/record['image']).convert('RGB')
                    if crop: expected=expected.crop(crop)
                    expected=expected.resize((expected.width*scale,expected.height*scale),Image.Resampling.NEAREST)
                    gif.seek(tick);self.assertEqual(gif.info['duration'],200);self.assertEqual(expected.tobytes(),gif.convert('RGB').tobytes())
                first=Image.open(PACK/f'{name}.png').convert('RGB'); gif.seek(0)
                self.assertEqual(first.tobytes(),gif.convert('RGB').tobytes())


if __name__=='__main__':unittest.main()
