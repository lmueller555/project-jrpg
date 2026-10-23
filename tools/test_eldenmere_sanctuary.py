"""Check native appearance, town registration, preserved surroundings and review views."""
import json
from pathlib import Path
import unittest
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/sanctuary'
SOURCE=ROOT/'assets/source/terrain/eldenmere/sanctuary'
BASE=ROOT/'assets/maps/eldenmere/terrain_foundation'


def load(path):return json.loads(path.read_text())


def opened(path):
    with Image.open(path) as im:return im.convert('RGBA')


class SanctuaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=load(PACK/'sanctuary.json')
        cls.recipe=load(SOURCE/'recipe.json')

    def test_native_frame_hard_alpha_materials_and_complete_source_parts(self):
        sprite=opened(PACK/'closed.png')
        self.assertEqual(sprite.size,(216,216))
        self.assertEqual(self.meta['ground_rect'],[12,84,192,120])
        self.assertEqual(self.meta['ground_tiles'],[8,5])
        self.assertEqual(set(sprite.getchannel('A').get_flattened_data()),{0,255})
        left,top,right,bottom=sprite.getbbox()
        self.assertGreater(left,0);self.assertLess(right,216)
        self.assertGreater(top,0);self.assertLess(bottom,216)
        expected=Image.new('RGBA',(216,216))
        for band in self.recipe['bands']:
            part=opened(SOURCE/'parts'/f"{band['id']}.png")
            self.assertEqual(list(part.size),band['sample_size'])
            expected.alpha_composite(part,tuple(band['position']))
        self.assertEqual(sprite.tobytes(),expected.tobytes())
        self.assertEqual(sprite.tobytes(),opened(SOURCE/'parts/exterior_native.png').tobytes())
        palette=load(PACK/'palette.json')['materials']
        colors={(*bytes.fromhex(c[1:]),255) for ramp in palette.values() for c in ramp.values()}
        self.assertTrue(all(p in colors for p in sprite.get_flattened_data() if p[3]))
        bronze={(*bytes.fromhex(c[1:]),255) for c in palette['bronze'].values()}
        self.assertGreater(sum(p in bronze for p in sprite.crop((39,53,58,80)).get_flattened_data()),15)
        glass={(*bytes.fromhex(c[1:]),255) for c in palette['glass'].values()}
        for rect in ((39,152,54,183),(74,152,89,183),(167,152,183,183)):
            self.assertGreater(sum(p in glass for p in sprite.crop(rect).get_flattened_data()),15)
        self.assertEqual(self.meta['door']['clear_width'],32)
        self.assertFalse(self.meta['door']['animated'])
        self.assertFalse(self.meta['bell']['animated'])
        self.assertFalse(self.meta['chimney_smoke_included'])

    def test_town_changes_only_inside_registered_sanctuary_bounds(self):
        before=opened(BASE/'town_native.png').convert('RGB')
        after=opened(PACK/'town_native.png').convert('RGB')
        self.assertEqual(after.size,(1536,1344))
        diff=ImageChops.difference(before,after).getbbox();self.assertIsNotNone(diff)
        x,y=self.meta['position'];w,h=self.meta['prefab_size']
        self.assertGreaterEqual(diff[0],x);self.assertGreaterEqual(diff[1],y)
        self.assertLessEqual(diff[2],x+w);self.assertLessEqual(diff[3],y+h)
        gx,gy,gw,gh=self.meta['ground_rect']
        self.assertEqual([x+gx,y+gy,gw,gh],[264,168,192,120])
        sprite=opened(PACK/'closed.png')
        actual=after.crop((x,y,x+w,y+h))
        for expected,p in zip(sprite.get_flattened_data(),actual.get_flattened_data()):
            if expected[3]==255:self.assertEqual(p,expected[:3])

    def test_actual_doorway_approach_is_reachable_and_caelan_is_preserved(self):
        meta=self.meta;foot=meta['character']['foot']
        door=meta['door_world_rect'];self.assertEqual(foot[0],door[0]+door[2]/2)
        self.assertGreaterEqual(foot[1]-6,door[1]+door[3])
        blocked=opened(BASE/'navigation/blocking.png').convert('L')
        self.assertIsNone(blocked.crop((foot[0]-12,foot[1]-6,foot[0]+12,foot[1]+6)).getbbox())
        reached=opened(BASE/'navigation/reachable_centres.png').convert('L')
        self.assertEqual(reached.getpixel(tuple(foot)),255)
        hero=opened(ROOT/meta['character']['image']);self.assertEqual(hero.size,(24,36))
        image=opened(PACK/'scene_frames/frame_01.png')
        ox,oy=foot[0]-12,foot[1]-30
        for y in range(36):
            for x in range(24):
                p=hero.getpixel((x,y))
                if p[3]==255:self.assertEqual(image.getpixel((ox+x,oy+y)),p)
        self.assertFalse(meta['door_interaction_implemented'])
        self.assertFalse(meta['interior_transition_implemented'])

    def test_enlarged_review_is_exact_native_crop_and_images_are_opaque(self):
        native=opened(PACK/'scene_frames/frame_01.png').convert('RGB')
        x,y,w,h=self.meta['review_crop']
        expected=native.crop((x,y,x+w,y+h))
        self.assertEqual(opened(PACK/'entrance_native.png').convert('RGB').tobytes(),expected.tobytes())
        review=opened(PACK/'sanctuary_review.png').convert('RGB')
        self.assertEqual(review.size,(1632,1744))
        self.assertEqual(review.crop((0,84,1632,1716)).tobytes(),expected.resize((1632,1632),Image.Resampling.NEAREST).tobytes())
        for filename in ('sanctuary_review.png','exterior_review.png','town_review.png'):
            with Image.open(PACK/filename) as image:
                self.assertEqual(image.mode,'RGB')


if __name__=='__main__':unittest.main()
