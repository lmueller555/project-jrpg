"""The authored grove stays rooted, readable and native at character scale."""
from hashlib import sha256
import json
from pathlib import Path
import unittest

from PIL import Image

from tools.build_sanctuary_grove import products


ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/sanctuary_fantasy/grove'


class SanctuaryGroveAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((PACK/'assets.json').read_text())
        cls.modules=cls.manifest['modules']

    def frames(self,name):
        return [Image.open(ROOT/record['image']).convert('RGBA')
                for record in self.modules[name]['frames']]

    def test_landmark_scale_and_compatible_physical_tree_base(self):
        with Image.open(ROOT/'assets/characters/caelan/idle_front.png') as hero:
            bounds=hero.convert('RGBA').getchannel('A').getbbox()
        hero_height=bounds[3]-bounds[1]
        image=self.frames('landmark_combined')[0];bounds=image.getchannel('A').getbbox()
        visible_height=bounds[3]-bounds[1]
        self.assertEqual(hero_height,34)
        self.assertTrue(130<=visible_height<=170)
        self.assertGreater(visible_height,hero_height*3)
        self.assertEqual(image.size,(192,176))
        self.assertEqual(self.modules['landmark_trunk']['anchor'],[112,164])
        legacy=json.loads((ROOT/'assets/terrain/eldenmere/foliage/tree/foliage.json').read_text())
        x,y,w,h=legacy['ground_rect']
        expected=[x-48,y-108,w,h]
        self.assertEqual(self.modules['landmark_trunk']['footprints'],[expected])
        for name in ('sapling_arching','sapling_upright'):
            self.assertEqual(self.modules[name]['footprints'],[expected])

    def test_six_canopy_poses_preserve_alpha_roots_and_crown_windows(self):
        frames=self.frames('landmark_canopy')
        self.assertEqual(len(frames),6)
        self.assertGreaterEqual(len({image.tobytes() for image in frames}),3)
        alpha=frames[0].getchannel('A').tobytes()
        for index,image in enumerate(frames):
            with self.subTest(pose=index):
                self.assertEqual(image.getchannel('A').tobytes(),alpha)
                self.assertEqual(image.getpixel((94,80))[3],0)
                self.assertEqual(image.getpixel((130,113))[3],0)
                self.assertIsNone(image.crop((0,150,192,176)).getchannel('A').getbbox())
        # Roots and trunk are fixed objects, rather than being shifted with
        # the leaf animation. Their derived combined poses retain exact bases.
        self.assertEqual(len(self.frames('landmark_trunk')),1)
        self.assertEqual(len(self.frames('landmark_roots')),1)
        combined=self.frames('landmark_combined')
        base=combined[0].crop((0,150,192,176)).tobytes()
        for image in combined:self.assertEqual(image.crop((0,150,192,176)).tobytes(),base)

    def test_module_pixels_are_hard_alpha_and_canopies_do_not_own_collision(self):
        for name,record in self.modules.items():
            for index,image in enumerate(self.frames(name)):
                with self.subTest(module=name,pose=index):
                    self.assertEqual(list(image.size),record['size'])
                    self.assertLessEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
        for name in ('landmark_roots','landmark_canopy','blossom_white','blossom_cyan',
                     'moss_fan','moss_rosette','petal_white','petal_cyan','petal_amethyst'):
            self.assertEqual(self.modules[name]['footprints'],[])
        for name in ('petal_white','petal_cyan','petal_amethyst'):
            self.assertEqual(self.modules[name]['size'],[8,8])
            self.assertEqual(len(self.modules[name]['frames']),3)

    def test_approved_source_references_and_all_exports_remain_reproducible(self):
        for record in self.manifest['source_assets']:
            with self.subTest(source=record['path']):
                self.assertEqual(sha256((ROOT/record['path']).read_bytes()).hexdigest(),record['sha256'])
        for path,body in products().items():
            with self.subTest(export=path.relative_to(ROOT)):
                self.assertEqual(path.read_bytes(),body)


if __name__=='__main__':unittest.main()
