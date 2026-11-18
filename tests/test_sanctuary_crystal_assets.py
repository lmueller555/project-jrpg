"""The authored mineral modules retain physical silhouettes during shimmer."""
from hashlib import sha256
import json
from pathlib import Path
import unittest

from PIL import Image, ImageChops

from tools.build_sanctuary_crystals import products


ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/sanctuary_fantasy/crystals'


class SanctuaryCrystalAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((PACK/'assets.json').read_text())
        cls.modules=cls.manifest['modules']

    def test_six_authored_silhouettes_have_four_distinct_coordinated_colorways(self):
        crystals={key:record for key,record in self.modules.items() if record['kind']=='crystal'}
        self.assertEqual(len(crystals),24)
        shapes={key.split('.')[1] for key in crystals}
        self.assertEqual(len(shapes),6)
        self.assertEqual(set(self.manifest['palettes']),{'amethyst','cyan','opal','amber'})
        silhouettes=[]
        for shape in sorted(shapes):
            frame_bytes=set();masks=set()
            for color in self.manifest['palettes']:
                record=crystals[f'crystal.{shape}.{color}']
                with self.subTest(shape=shape,color=color):
                    with Image.open(ROOT/record['frames'][0]) as image:
                        frame_bytes.add(image.tobytes())
                        masks.add(image.getchannel('A').tobytes())
                        self.assertEqual(image.size,tuple(record['size']))
                        box=image.getbbox()
                        self.assertGreater(box[3]-box[1],15)
                        self.assertTrue(0<=record['anchor'][0]<image.width)
                        self.assertTrue(0<=record['anchor'][1]<image.height)
            self.assertEqual(len(frame_bytes),4)
            self.assertEqual(len(masks),1,'Colorways must share the authored geometry')
            silhouettes.append(next(iter(masks)))
        self.assertEqual(len(set(silhouettes)),6)
        with Image.open(ROOT/crystals['crystal.large_crown.amethyst']['frames'][0]) as image:
            bounds=image.getbbox()
            self.assertTrue(90<=bounds[3]-bounds[1]<=112)

    def test_six_shimmer_frames_keep_hard_alpha_and_root_pixels_anchored(self):
        for identifier,record in self.modules.items():
            frames=[Image.open(ROOT/path).convert('RGBA') for path in record['frames']]
            if record['kind']=='crystal':self.assertEqual(len(frames),6)
            alpha=frames[0].getchannel('A').tobytes()
            root=frames[0].crop((0,frames[0].height-5,frames[0].width,frames[0].height)).tobytes()
            for index,image in enumerate(frames):
                with self.subTest(module=identifier,frame=index):
                    self.assertEqual(image.size,tuple(record['size']))
                    self.assertLessEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
                    self.assertEqual(image.getchannel('A').tobytes(),alpha,'Shimmer changed a physical silhouette')
                    if record['kind']=='crystal':
                        self.assertEqual(image.crop((0,image.height-5,image.width,image.height)).tobytes(),root)
            if record['kind']=='crystal':
                self.assertGreater(len({image.tobytes() for image in frames}),2,'Internal facets should visibly shimmer')
            for image in frames:image.close()

    def test_surface_veins_and_floor_fragments_never_add_collision(self):
        for identifier in ('vein.amethyst','vein.cyan','vein.opal','vein.amber',
                           'ruins.arc','ruins.broken_arc','ruins.paving','memorial.offering'):
            with self.subTest(module=identifier):self.assertEqual(self.modules[identifier]['footprints'],[])
        for record in self.modules.values():
            width,height=record['size']
            for x,y,w,h in record['footprints']:
                self.assertGreater(w,0);self.assertGreater(h,0)
                self.assertTrue(0<=x<x+w<=width)
                self.assertTrue(0<=y<y+h<=height)

    def test_source_provenance_and_deterministic_exports_match_checked_in_art(self):
        for record in self.manifest['source_assets']:
            self.assertEqual(sha256((ROOT/record['path']).read_bytes()).hexdigest(),record['sha256'])
        self.assertEqual(sha256((ROOT/self.manifest['source_recipe']).read_bytes()).hexdigest(),
                         self.manifest['source_recipe_sha256'])
        for path,expected in products().items():
            with self.subTest(export=path.relative_to(ROOT)):
                self.assertEqual(path.read_bytes(),expected)


if __name__=='__main__':unittest.main()
