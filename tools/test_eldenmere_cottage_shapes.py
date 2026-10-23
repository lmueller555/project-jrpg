"""Check modular cottage sizes, exact reused animation and lossless review delivery."""
from pathlib import Path
import json
import unittest
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/cottage_shapes'
BASE=PACK.parent/'cottage'
PREVIOUS=PACK.parent/'cottage_variants'
GROUND=PACK.parent/'grass_dirt'


def load(p):return json.loads(p.read_text())
def opened(p):return Image.open(p).convert('RGBA')


class CottageShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=load(PACK/'shapes.json');cls.scene=load(PACK/'review_scene.json')
        cls.instances=cls.meta['instances'];cls.schedule=load(BASE/'review_scene.json')['frames']

    def test_footprints_windows_materials_and_closed_wall_coverage(self):
        self.assertEqual(len(self.instances),8);self.assertEqual(self.meta['palettes'],['slate','terracotta','moss','heather'])
        for instance in self.instances:
            directory=PACK/instance['shape']/instance['palette'];meta=load(directory/'cottage.json');source=ROOT/meta['source_from_repo_root']
            compact=instance['shape']=='compact';width=96 if compact else 144
            self.assertEqual(meta['prefab_size'],[width,144]);self.assertEqual(meta['ground_rect'],[12,72,72 if compact else 120,72])
            self.assertEqual(meta['tile_size'],[24,24]);self.assertEqual(meta['window_count'],1 if compact else 3)
            self.assertEqual(len(meta['window_rects']),meta['window_count'])
            self.assertEqual(load(directory/'palette.json')['materials'],load(source/'palette.json')['materials'])
            colors={tuple(bytes.fromhex(c[1:])) for ramp in load(source/'palette.json')['materials'].values() for c in ramp.values()}
            for path in directory.rglob('*.png'):
                image=opened(path);self.assertLessEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
                self.assertTrue(all(not p[3] or p[:3] in colors for p in image.get_flattened_data()),str(path))
            closed=opened(directory/'closed.png')
            self.assertEqual(set(closed.crop((16,106,width-16,138)).getchannel('A').get_flattened_data()),{255})

    def test_exact_source_bays_windows_and_reconstructable_structure(self):
        for instance in self.instances:
            directory=PACK/instance['shape']/instance['palette'];meta=load(directory/'cottage.json');source=ROOT/meta['source_from_repo_root']
            structure=Image.new('RGBA',tuple(meta['prefab_size']))
            for component in meta['components']:structure.alpha_composite(opened(directory/component['image']),tuple(component['position']))
            self.assertEqual(structure.tobytes(),opened(directory/'structure.png').tobytes())
            original=opened(source/'structure.png')
            self.assertEqual(opened(directory/'parts/east.png').tobytes(),original.crop((48,0,120,144)).tobytes())
            if instance['shape']=='compact':
                west=opened(directory/'parts/west.png')
                self.assertEqual(west.crop((0,0,19,144)).tobytes(),original.crop((0,0,19,144)).tobytes())
                self.assertEqual(opened(directory/'parts/flower_box.png').tobytes(),opened(source/'closed.png').crop((23,123,39,132)).tobytes())
            else:
                self.assertEqual(opened(directory/'parts/west.png').tobytes(),original.crop((0,0,48,144)).tobytes())
                for output,name in (('roof_insert','roof_repeat'),('wall_insert','wall_blank'),('extra_window','window_right')):
                    self.assertEqual(opened(directory/f'parts/{output}.png').tobytes(),opened(source/f'parts/{name}.png').tobytes())

    def test_animation_pixels_translated_without_deformation_or_clipping(self):
        for instance in self.instances:
            directory=PACK/instance['shape']/instance['palette'];meta=load(directory/'cottage.json');source=ROOT/meta['source_from_repo_root']
            original=load(source/'cottage.json');dx,dy=meta['animation_offset_from_source'];width,height=meta['prefab_size']
            self.assertEqual(meta['door']['position'],[original['door']['position'][0]+dx,111])
            for key in ('opening','closing','hold_open','hold_closed','hinge','size'):self.assertEqual(meta['door'][key],original['door'][key])
            self.assertEqual(meta['lantern'],original['lantern'])
            for folder,count in (('doors',5),('lantern',18),('smoke',18)):
                for phase in range(count):
                    before=opened(source/f'{folder}/frame_{phase+1:02}.png');after=opened(directory/f'{folder}/frame_{phase+1:02}.png')
                    expected=Image.new('RGBA',(width,height));expected.paste(before,(dx,dy))
                    self.assertEqual(expected.tobytes(),after.tobytes())
                    self.assertEqual(sum(bool(v) for v in before.getchannel('A').get_flattened_data()),sum(bool(v) for v in after.getchannel('A').get_flattened_data()))
            for a,b in zip(original['smoke']['frames'],meta['smoke']['frames'],strict=True):
                self.assertEqual(a['duration_ms'],b['duration_ms'])
                for p,q in zip(a['particles'],b['particles'],strict=True):
                    self.assertEqual(q['age'],p['age']);self.assertEqual(q['center'],[p['center'][0]+dx,p['center'][1]+dy])

    def test_composites_sheets_and_dry_connected_level_access(self):
        paths=opened(PACK/'review_path.png');cells={tuple(p) for p in self.scene['path_cells']};joins=cells|{tuple(p) for p in self.scene['path_join_cells']};reached={(8,33)}
        while True:
            grown=reached|{(x+dx,y+dy) for x,y in reached for dx,dy in ((0,1),(0,-1),(1,0),(-1,0)) if (x+dx,y+dy) in joins}
            if grown==reached:break
            reached=grown
        self.assertEqual(reached,joins)
        for instance in self.instances:
            directory=PACK/instance['shape']/instance['palette'];meta=load(directory/'cottage.json');structure=opened(directory/'structure.png');w,h=meta['prefab_size']
            for phase,timing in enumerate(self.schedule):
                frame=structure.copy()
                for path in (f"doors/frame_{timing['door_frame']+1:02}.png",f'lantern/frame_{phase+1:02}.png',f'smoke/frame_{phase+1:02}.png'):
                    frame.alpha_composite(opened(directory/path))
                self.assertEqual(frame.tobytes(),opened(directory/f'preview_frames/frame_{phase+1:02}.png').tobytes())
            sheet=opened(directory/'door_sheet.png');self.assertEqual(sheet.size,(w*5,h))
            for phase in range(5):
                frame=structure.copy();frame.alpha_composite(opened(directory/f'doors/frame_{phase+1:02}.png'));frame.alpha_composite(opened(directory/'lantern/frame_01.png'))
                self.assertEqual(frame.tobytes(),sheet.crop((phase*w,0,(phase+1)*w,h)).tobytes())
                if phase in (0,4):self.assertEqual(frame.tobytes(),opened(directory/('closed.png' if phase==0 else 'open.png')).tobytes())
            self.assertEqual(instance['ground_elevation_pixels'],instance['threshold_elevation_pixels']);self.assertEqual(instance['ground_elevation_pixels'],0)
            self.assertEqual(paths.getpixel(tuple(instance['foot']))[3],255)
            x,y=instance['position'];self.assertGreaterEqual(y,864)
            self.assertIsNone(paths.crop((x+12,y+72,x+w-12,y+120)).getbbox())
        self.assertTrue(all(y>=34 for x,y in cells))

    def test_scene_reconstruction_and_preserved_existing_world(self):
        scene=self.scene;gm=load(GROUND/'tileset.json');grass=[opened(GROUND/p) for p in gm['grass']['images']];ground=Image.new('RGBA',(768,1296));paths=opened(PACK/'review_path.png')
        for y,row in enumerate(scene['grass_variants']):
            for x,index in enumerate(row):ground.paste(grass[index],(x*24,y*24))
        for phase,record in enumerate(scene['frames']):
            previous=opened(PREVIOUS/f'scene_frames/frame_{phase+1:02}.png');expected=ground.copy();expected.paste(previous,(0,0));expected.alpha_composite(paths)
            for instance in scene['instances']:
                frame=opened(PACK/instance['shape']/instance['palette']/f'preview_frames/frame_{phase+1:02}.png');expected.alpha_composite(frame,tuple(instance['position']))
            actual=opened(PACK/record['image']);self.assertEqual(expected.tobytes(),actual.tobytes())
            delta=ImageChops.difference(previous.convert('RGB'),actual.crop((0,0,720,864)).convert('RGB'))
            allowed=paths.getchannel('A').crop((0,0,720,864))
            self.assertIsNone(ImageChops.multiply(delta,ImageChops.invert(allowed).convert('RGB')).getbbox())
            # The complete old mill, bridge, waterways, terrace and original cottages stay identical.
            self.assertEqual(previous.crop((0,0,720,792)).tobytes(),actual.crop((0,0,720,792)).tobytes())

    def test_lossless_looping_gifs_and_all_eight_palette_cards(self):
        for name,crop,scale in (('review_scene',None,2),('courtyard_closeup',self.scene['review']['courtyard_crop'],2)):
            with Image.open(PACK/f'{name}.gif') as gif:
                self.assertEqual(gif.n_frames,18);self.assertEqual(gif.info['loop'],0)
                for phase,record in enumerate(self.scene['frames']):
                    expected=Image.open(PACK/record['image']).convert('RGB')
                    if crop:expected=expected.crop(crop)
                    expected=expected.resize((expected.width*scale,expected.height*scale),Image.Resampling.NEAREST)
                    gif.seek(phase);self.assertEqual(gif.info['duration'],200);self.assertEqual(expected.tobytes(),gif.convert('RGB').tobytes())
                gif.seek(0);self.assertEqual(gif.convert('RGB').tobytes(),Image.open(PACK/f'{name}.png').convert('RGB').tobytes())
        for name in ('sizes_review','palettes_review'):
            with Image.open(PACK/f'{name}.gif') as gif:
                self.assertEqual(gif.n_frames,18);self.assertEqual(gif.info['loop'],0)
                for phase in range(18):
                    gif.seek(phase);self.assertEqual(gif.info['duration'],200)
                    if name=='sizes_review':
                        entries=[(PACK/'compact/slate',16),(BASE,440),(PACK/'wide/slate',944)]
                        for directory,x in entries:
                            frame=opened(directory/f'preview_frames/frame_{phase+1:02}.png');tile=Image.new('RGBA',frame.size,'#70935a');tile.alpha_composite(frame)
                            expected=tile.convert('RGB').resize((frame.width*4,576),Image.Resampling.NEAREST)
                            self.assertEqual(expected.tobytes(),gif.convert('RGB').crop((x,104,x+expected.width,680)).tobytes())
                    else:
                        for row,shape in enumerate(('compact','wide')):
                            for col,palette in enumerate(self.meta['palettes']):
                                frame=opened(PACK/shape/palette/f'preview_frames/frame_{phase+1:02}.png');tile=Image.new('RGBA',(144,144),'#70935a');tile.alpha_composite(frame,((144-frame.width)//2,0))
                                expected=tile.convert('RGB').resize((432,432),Image.Resampling.NEAREST);x=col*456+12;y=92+row*484
                                self.assertEqual(expected.tobytes(),gif.convert('RGB').crop((x,y,x+432,y+432)).tobytes())

if __name__=='__main__':unittest.main()
