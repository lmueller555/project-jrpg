"""Check palette-only cottages, preserved poses and readable synchronized delivery."""
from pathlib import Path
import json
import unittest
from PIL import Image, ImageChops, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/cottage_variants'
BASE=PACK.parent/'cottage'
GROUND=PACK.parent/'grass_dirt'


def load(p):return json.loads(p.read_text())
def opened(p):return Image.open(p).convert('RGBA')


class CottageVariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=load(PACK/'variants.json');cls.scene=load(PACK/'review_scene.json')
        cls.base=load(BASE/'cottage.json');cls.palette=load(BASE/'palette.json')['materials']

    def test_material_only_changes_and_native_geometry(self):
        self.assertEqual(len(self.meta['variants']),3)
        preserved={(*bytes.fromhex(c[1:]),255) for name,ramp in self.palette.items() if name not in ('wood','plaster','roof') for c in ramp.values()}
        for variant in self.meta['variants']:
            directory=PACK/variant['id'];meta=load(directory/'cottage.json');palette=load(directory/'palette.json')['materials']
            self.assertEqual(meta['ground_rect'],[12,72,96,72]);self.assertEqual(meta['prefab_size'],[120,144])
            for name,ramp in self.palette.items():
                if name not in ('wood','plaster','roof'):self.assertEqual(palette[name],ramp)
            allowed={tuple(bytes.fromhex(c[1:])) for ramp in palette.values() for c in ramp.values()}
            # Registered pixels deliberately preserved on lights/flowers/stone may keep base shades.
            allowed|={tuple(bytes.fromhex(c[1:])) for ramp in self.palette.values() for c in ramp.values()}
            target_roof={tuple(bytes.fromhex(c[1:])) for name in ('roof','wood','roof_detail') for c in palette[name].values()}
            changed=0
            for folder in ('parts','doors','smoke','lantern','preview_frames'):
                for path in (directory/folder).glob('*.png'):
                    image=opened(path);base=opened(BASE/path.relative_to(directory))
                    self.assertEqual(image.size,base.size);self.assertEqual(image.getchannel('A').tobytes(),base.getchannel('A').tobytes())
                    self.assertLessEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
                    relative=path.relative_to(directory).as_posix()
                    origins={c['image']:tuple(c['position']) for c in self.base['components']}
                    origins.update({'parts/roof_repeat.png':(48,56),'parts/wall_blank.png':(24,101),
                                    'parts/window_left_lit.png':(19,109),'parts/window_right_lit.png':(79,109)})
                    ox,oy=origins.get(relative,(0,0))
                    for index,(a,b) in enumerate(zip(base.get_flattened_data(),image.get_flattened_data(),strict=True)):
                        if not b[3]:continue
                        self.assertIn(b[:3],allowed)
                        x,y=index%base.width+ox,index//base.width+oy
                        roof=56<=y<101 and not (82<=x<98 and y<70)
                        if a in preserved and not roof:self.assertEqual(a,b)
                        if roof:
                            self.assertIn(b[:3],target_roof)
                        changed+=a!=b
            self.assertGreater(changed,10000)
            for path in (directory/'smoke').glob('*.png'):
                self.assertEqual(path.read_bytes(),(BASE/path.relative_to(directory)).read_bytes())
            for phase in range(18):
                path=f'preview_frames/frame_{phase+1:02}.png'
                self.assertEqual(opened(directory/path).crop((82,48,98,70)).tobytes(),opened(BASE/path).crop((82,48,98,70)).tobytes())
            # Dark joints must stay distinct from tile faces; collapsing both flattens the roof.
            before=opened(BASE/'closed.png');after=opened(directory/'closed.png')
            dark=tuple(bytes.fromhex(self.palette['glass']['dark'][1:]))
            face=tuple(bytes.fromhex(self.palette['roof']['base'][1:]))
            samples={dark:[],face:[]}
            for y in range(70,97):
                for x in range(24,80):
                    color=before.getpixel((x,y))[:3]
                    if color in samples:samples[color].append(sum(after.getpixel((x,y))[:3])/3)
            self.assertGreater(min(samples[face])-max(samples[dark]),20)

    def test_inherited_pose_tracks_and_complete_frame_composites(self):
        review=load(BASE/'review_scene.json')
        for variant in self.meta['variants']:
            directory=PACK/variant['id'];meta=load(directory/'cottage.json')
            for key in ('door','smoke','lantern','components','tile_size','prefab_size','ground_rect'):
                self.assertEqual(meta[key],self.base[key])
            structure=opened(directory/'structure.png');lamp=opened(directory/'lantern/frame_01.png')
            for tick in range(18):
                expected=structure.copy();index=review['frames'][tick]['door_frame']
                for path in (f'doors/frame_{index+1:02}.png',f'lantern/frame_{tick+1:02}.png',f'smoke/frame_{tick+1:02}.png'):
                    expected.alpha_composite(opened(directory/path))
                self.assertEqual(expected.tobytes(),opened(directory/f'preview_frames/frame_{tick+1:02}.png').tobytes())
            sheet=opened(directory/'door_sheet.png')
            for index in range(5):
                expected=structure.copy();expected.alpha_composite(opened(directory/f'doors/frame_{index+1:02}.png'));expected.alpha_composite(lamp)
                self.assertEqual(expected.tobytes(),sheet.crop((index*120,0,(index+1)*120,144)).tobytes())
                if index in (0,4):self.assertEqual(expected.tobytes(),opened(directory/('closed.png' if index==0 else 'open.png')).tobytes())

    def test_connected_dry_courtyard_level_access_and_old_character_clearance(self):
        scene=self.scene;cells={tuple(p) for p in scene['path_cells']};joins=cells|{tuple(p) for p in scene['path_join_cells']}
        reached={(8,23)}
        while True:
            grown=reached|{(x+dx,y+dy) for x,y in reached for dx,dy in ((0,1),(0,-1),(1,0),(-1,0)) if (x+dx,y+dy) in joins}
            if grown==reached:break
            reached=grown
        self.assertEqual(reached,joins)
        paths=opened(PACK/'review_path.png')
        for instance in scene['instances']:
            self.assertEqual(instance['ground_elevation_pixels'],0);self.assertEqual(instance['threshold_elevation_pixels'],0)
            x,y=instance['position'];self.assertGreaterEqual(y,624)
            fx,fy=instance['foot'];self.assertEqual(paths.getpixel((fx,fy))[3],255)
            # The approach stays outside the main floor, with its final tile tucked beneath the doorstep.
            building=opened(PACK/instance['id']/'closed.png')
            for yy in range(72,120):
                for xx in range(12,108):
                    if building.getpixel((xx,yy))[3]:self.assertEqual(paths.getpixel((x+xx,y+yy))[3],0)
        female=opened(ROOT/'assets/characters/npcs/female_02/idle_front.png')
        for y in range(36):
            for x in range(24):
                if female.getpixel((x,y))[3]:self.assertEqual(paths.getpixel((192+x,538+y))[3],0)
        stream=load(PACK.parent/'stream/review_scene.json');mill=load(PACK.parent/'watermill/review_scene.json')
        wet={tuple(p['cell']) for p in mill['race']}
        self.assertFalse(cells&wet)
        self.assertTrue(all(y>=24 for x,y in cells))

    def test_scene_reconstruction_and_local_changes(self):
        scene=self.scene;gm=load(GROUND/'tileset.json');grass=[opened(GROUND/p) for p in gm['grass']['images']]
        paths=opened(PACK/'review_path.png');canvas=Image.new('RGBA',(720,864))
        for y,row in enumerate(scene['grass_extension'],start=26):
            for x,index in enumerate(row):canvas.paste(grass[index],(x*24,y*24))
        for tick,record in enumerate(scene['frames']):
            expected=canvas.copy();previous=opened(BASE/f'scene_frames/frame_{tick+1:02}.png');expected.paste(previous,(0,0));expected.alpha_composite(paths)
            for instance in scene['instances']:
                expected.alpha_composite(opened(PACK/instance['id']/f'preview_frames/frame_{tick+1:02}.png'),tuple(instance['position']))
            actual=opened(PACK/record['image']);self.assertEqual(expected.tobytes(),actual.tobytes())
            difference=ImageChops.difference(previous.convert('RGB'),actual.crop((0,0,720,624)).convert('RGB'))
            allowed=paths.getchannel('A').crop((0,0,720,624))
            self.assertIsNone(ImageChops.multiply(difference,ImageChops.invert(allowed).convert('RGB')).getbbox())

    def test_exact_scene_and_synchronized_four_palette_gifs(self):
        for name,crop,scale in (('review_scene',None,2),('courtyard_closeup',self.scene['review']['courtyard_crop'],3)):
            with Image.open(PACK/f'{name}.gif') as gif:
                self.assertEqual(gif.n_frames,18);self.assertEqual(gif.info['loop'],0)
                for tick,record in enumerate(self.scene['frames']):
                    expected=Image.open(PACK/record['image']).convert('RGB')
                    if crop:expected=expected.crop(crop)
                    expected=expected.resize((expected.width*scale,expected.height*scale),Image.Resampling.NEAREST)
                    gif.seek(tick);self.assertEqual(gif.info['duration'],200);self.assertEqual(expected.tobytes(),gif.convert('RGB').tobytes())
                gif.seek(0);self.assertEqual(gif.convert('RGB').tobytes(),Image.open(PACK/f'{name}.png').convert('RGB').tobytes())
        with Image.open(PACK/'variants_review.gif') as gif:
            self.assertEqual(gif.n_frames,18);self.assertEqual(gif.info['loop'],0)
            for tick in range(18):
                gif.seek(tick);self.assertEqual(gif.info['duration'],200)
                for column,directory in enumerate([BASE]+[PACK/v['id'] for v in self.meta['variants']]):
                    card=Image.new('RGBA',(120,144),'#70935a');card.alpha_composite(opened(directory/f'preview_frames/frame_{tick+1:02}.png'))
                    expected=card.convert('RGB').resize((480,576),Image.Resampling.NEAREST);x=column*512+16
                    self.assertEqual(expected.tobytes(),gif.convert('RGB').crop((x,104,x+480,680)).tobytes())

if __name__=='__main__':unittest.main()
