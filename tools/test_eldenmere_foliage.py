"""Check fixed foliage structure, restrained cluster motion and synchronized delivery."""
from pathlib import Path
import json
import unittest
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/foliage'
SOURCE=ROOT/'assets/source/terrain/eldenmere/foliage'
PREVIOUS=PACK.parent/'cottage_shapes'
GROUND=PACK.parent/'grass_dirt'


def load(p):return json.loads(p.read_text())
def opened(p):return Image.open(p).convert('RGBA')


class FoliageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe=load(SOURCE/'recipe.json');cls.scene=load(PACK/'review_scene.json');cls.palette=load(PACK/'palette.json')['materials']
        cls.plants={p['id']:load(PACK/p['id']/'foliage.json') for p in cls.recipe['plants']}

    def test_native_dimensions_materials_source_rest_pose_and_ground_registration(self):
        self.assertEqual(set(self.plants),{'tree','shrub'})
        self.assertEqual(self.palette['wood'],load(PACK.parent/'cottage/palette.json')['materials']['wood'])
        self.assertEqual(self.palette['shadow']['base'],'#4f7851')
        colors={tuple(bytes.fromhex(c[1:])) for ramp in self.palette.values() for c in ramp.values()}
        for name,meta in self.plants.items():
            size=[96,120] if name=='tree' else [24,24];self.assertEqual(meta['frame_size'],size)
            self.assertEqual(meta['tile_size'],[24,24]);self.assertEqual(meta['ground_rect'][2:],[24,24])
            directory=PACK/name
            self.assertEqual(opened(directory/'idle.png').tobytes(),opened(SOURCE/f'parts/{name}_native.png').tobytes())
            for path in directory.rglob('*.png'):
                image=opened(path);self.assertLessEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
                self.assertTrue(all(not p[3] or p[:3] in colors for p in image.get_flattened_data()),path)
            x,y,w,h=meta['ground_rect'];shadow=opened(directory/'shadow.png')
            self.assertIsNotNone(shadow.crop((x,y,x+w,y+h)).getbbox())
            self.assertGreater(sum(bool(p) for p in opened(directory/'trunk.png').getchannel('A').get_flattened_data()),3)

    def test_fixed_bark_and_shadow_and_motion_stays_in_leaf_clusters(self):
        for name,meta in self.plants.items():
            directory=PACK/name;trunk=opened(directory/'trunk.png');shadow=opened(directory/'shadow.png');rest=opened(directory/'idle.png')
            allowed=Image.new('L',rest.size);unique=set()
            for record in meta['wind']['frames']:
                for cluster,offset in zip(meta['clusters'],record['cluster_offsets'],strict=True):
                    part=opened(directory/cluster['image']);layer=Image.new('L',rest.size)
                    layer.paste(part.getchannel('A'),(cluster['position'][0]+offset[0],cluster['position'][1]+offset[1]));allowed=ImageChops.lighter(allowed,layer)
            fixed=ImageChops.lighter(trunk.getchannel('A'),shadow.getchannel('A'))
            for record in meta['wind']['frames']:
                image=opened(directory/record['image']);unique.add(image.tobytes())
                difference=ImageChops.difference(image.convert('RGB'),rest.convert('RGB'))
                self.assertIsNone(ImageChops.multiply(difference,fixed.convert('RGB')).getbbox())
                self.assertIsNone(ImageChops.multiply(difference,ImageChops.invert(allowed).convert('RGB')).getbbox())
                self.assertEqual(image.size,rest.size)
            self.assertGreaterEqual(len(unique),6)

    def test_exact_leaf_patch_motion_and_frame_reconstruction(self):
        leaf_colors={(*bytes.fromhex(c[1:]),255) for c in self.palette['leaves'].values()}
        for name,meta in self.plants.items():
            directory=PACK/name;trunk=opened(directory/'trunk.png');shadow=opened(directory/'shadow.png');canopy=opened(directory/meta['canopy_backing'])
            width,height=meta['frame_size'];self.assertEqual(meta['wind']['cycle_duration_ms'],5400);self.assertEqual(meta['wind']['direction'],'E')
            self.assertFalse(meta['wind']['whole_plant_moves']);self.assertTrue(meta['wind']['loop'])
            sheet=opened(directory/'sheet.png');self.assertEqual(sheet.size,(width*9,height))
            frames=meta['wind']['frames'];self.assertEqual(sum(f['duration_ms'] for f in frames),5400)
            for phase,record in enumerate(frames):
                expected=shadow.copy();expected.alpha_composite(canopy);self.assertEqual(record['duration_ms'],600)
                observed=opened(directory/record['image'])
                for cluster,offset in zip(meta['clusters'],record['cluster_offsets'],strict=True):
                    self.assertIn(offset[0],(0,1));self.assertIn(offset[1],(0,-1))
                    image=opened(directory/cluster['image']);x,y=[a+b for a,b in zip(cluster['position'],offset,strict=True)]
                    self.assertTrue(0<=x and 0<=y and x+image.width<=width and y+image.height<=height)
                    checked=0
                    for yy in range(image.height):
                        for xx in range(image.width):
                            color=image.getpixel((xx,yy))
                            if color[3]:
                                self.assertIn(color,leaf_colors)
                                if not trunk.getpixel((x+xx,y+yy))[3]:
                                    self.assertEqual(observed.getpixel((x+xx,y+yy)),color);checked+=1
                    self.assertGreater(checked,2);expected.alpha_composite(image,(x,y))
                expected.alpha_composite(trunk);self.assertEqual(expected.tobytes(),observed.tobytes())
                self.assertEqual(sheet.crop((phase*width,0,(phase+1)*width,height)).tobytes(),observed.tobytes())
                next_offsets=frames[(phase+1)%9]['cluster_offsets']
                for a,b in zip(record['cluster_offsets'],next_offsets,strict=True):
                    self.assertTrue(all(abs(x-y)<=1 for x,y in zip(a,b,strict=True)))

    def test_plants_only_cover_grass_and_agree_with_existing_breeze(self):
        gm=load(GROUND/'tileset.json');grass={pixel for path in gm['grass']['images'] for pixel in opened(GROUND/path).get_flattened_data()}
        previous=opened(PREVIOUS/'scene_frames/frame_01.png')
        for instance in self.scene['instances']:
            self.assertEqual(instance['ground_elevation_pixels'],0)
            meta=self.plants[instance['plant']];x,y=instance['position'];union=Image.new('L',tuple(meta['frame_size']))
            for record in meta['wind']['frames']:union=ImageChops.lighter(union,opened(PACK/instance['plant']/record['image']).getchannel('A'))
            for yy in range(union.height):
                for xx in range(union.width):
                    if union.getpixel((xx,yy)):self.assertIn(previous.getpixel((x+xx,y+yy)),grass)
            gx,gy,w,h=meta['ground_rect']
            for yy in range(y+gy,y+gy+h):
                for xx in range(x+gx,x+gx+w):self.assertIn(previous.getpixel((xx,yy)),grass)
        self.assertEqual(self.scene['wind_direction'],'E')
        self.assertEqual(load(PACK.parent/'cottage/cottage.json')['smoke']['direction'],'east')

    def test_scene_timing_reconstruction_and_previous_pixels_preserved(self):
        scene=self.scene;self.assertEqual(scene['cycle_duration_ms'],10800);self.assertEqual(len(scene['frames']),54)
        for tick,record in enumerate(scene['frames']):
            self.assertEqual(record['duration_ms'],200);self.assertEqual(record['base_phase'],tick%18)
            previous=opened(PREVIOUS/f'scene_frames/frame_{tick%18+1:02}.png');expected=previous.copy();allowed=Image.new('L',expected.size)
            for instance,phase in zip(scene['instances'],record['foliage_phases'],strict=True):
                self.assertEqual(phase,(tick//3+instance['phase_offset'])%9)
                image=opened(PACK/instance['plant']/f'frames/frame_{phase+1:02}.png');position=tuple(instance['position'])
                expected.alpha_composite(image,position);coverage=Image.new('L',expected.size);coverage.paste(image.getchannel('A'),position)
                allowed=ImageChops.lighter(allowed,coverage)
            actual=opened(PACK/record['image']);self.assertEqual(actual.size,(768,1296));self.assertEqual(expected.tobytes(),actual.tobytes())
            difference=ImageChops.difference(actual.convert('RGB'),previous.convert('RGB'))
            self.assertIsNone(ImageChops.multiply(difference,ImageChops.invert(allowed).convert('RGB')).getbbox())

    def test_review_gifs_exact_pixels_durations_and_scale_reference(self):
        for name,crop,scale in (('review_scene',None,2),('garden_closeup',self.scene['review']['closeup_rect'],4)):
            with Image.open(PACK/f'{name}.gif') as gif:
                self.assertEqual(gif.n_frames,54);self.assertEqual(gif.info['loop'],0)
                total=0
                for phase,record in enumerate(self.scene['frames']):
                    expected=Image.open(PACK/record['image']).convert('RGB')
                    if crop:expected=expected.crop(crop)
                    expected=expected.resize((expected.width*scale,expected.height*scale),Image.Resampling.NEAREST)
                    gif.seek(phase);self.assertEqual(gif.info['duration'],200);total+=gif.info['duration']
                    self.assertEqual(expected.tobytes(),gif.convert('RGB').tobytes())
                self.assertEqual(total,10800);gif.seek(0)
                self.assertEqual(gif.convert('RGB').tobytes(),Image.open(PACK/f'{name}.png').convert('RGB').tobytes())
        hero=opened(ROOT/'assets/characters/caelan/idle_front.png')
        with Image.open(PACK/'foliage_review.gif') as gif:
            self.assertEqual(gif.n_frames,9);self.assertEqual(gif.info['loop'],0)
            for phase in range(9):
                gif.seek(phase);self.assertEqual(gif.info['duration'],600)
                for name,scale,(x,y) in (('tree',6,(24,88)),('shrub',12,(824,88))):
                    frame=opened(PACK/name/f'frames/frame_{phase+1:02}.png');tile=Image.new('RGBA',frame.size,'#70935a');tile.alpha_composite(frame)
                    expected=tile.convert('RGB').resize((frame.width*scale,frame.height*scale),Image.Resampling.NEAREST)
                    self.assertEqual(expected.tobytes(),gif.convert('RGB').crop((x,y,x+expected.width,y+expected.height)).tobytes())
                scale_tile=Image.new('RGBA',(88,44),'#70935a');scale_tile.alpha_composite(hero,(4,6));scale_tile.alpha_composite(opened(PACK/'shrub'/f'frames/frame_{phase+1:02}.png'),(52,18))
                self.assertEqual(scale_tile.convert('RGB').resize((528,264),Image.Resampling.NEAREST).tobytes(),gif.convert('RGB').crop((644,492,1172,756)).tobytes())

if __name__=='__main__':unittest.main()
