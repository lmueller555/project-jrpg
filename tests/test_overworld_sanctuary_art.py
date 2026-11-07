"""Native sanctuary art stays compact, transparent and source-reproducible."""
from io import BytesIO
import hashlib
import json
from pathlib import Path
import unittest

from PIL import Image

from tools.build_overworld_sanctuary_art import exports


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT/'assets/terrain/overworld/elden_vale/sanctuary'


class SanctuaryArtTests(unittest.TestCase):
    def test_miniature_is_smaller_than_town_and_has_a_clean_native_silhouette(self):
        mini = Image.open(FOLDER/'ridge_sanctuary.png').convert('RGBA')
        with Image.open(ROOT/'assets/terrain/overworld/elden_vale/props/eldenmere.png') as town:
            town_size = town.size
        self.assertEqual(mini.size, (96, 80))
        self.assertLess(mini.width, town_size[0]);self.assertLess(mini.height, town_size[1])
        alpha = mini.getchannel('A').tobytes()
        self.assertEqual(set(alpha), {0, 255})
        self.assertGreater(alpha.count(255), 2000)
        for corner in ((0,0),(95,0),(0,79),(95,79)):
            self.assertEqual(mini.getpixel(corner), (0,0,0,0))

    def test_source_recipe_reproduces_the_shipped_pixels_and_registration(self):
        generated = exports()
        manifest = json.loads(generated['art.json'])
        self.assertEqual(set(manifest['props']), {'ridge_sanctuary'})
        for key, record in manifest['props'].items():
            actual = Image.open(ROOT/record['image']).convert('RGBA')
            rebuilt = Image.open(BytesIO(generated[key+'.png'])).convert('RGBA')
            self.assertEqual(actual.size, rebuilt.size)
            self.assertEqual(actual.tobytes(), rebuilt.tobytes())
            self.assertEqual(len(record['foot_anchor']), 2)
            self.assertTrue(0 <= record['foot_anchor'][0] <= actual.width)
            self.assertTrue(0 <= record['foot_anchor'][1] <= actual.height)

    def test_art_manifest_does_not_introduce_collision_or_scene_transfers(self):
        manifest = json.loads((FOLDER/'art.json').read_text())
        self.assertEqual(manifest['tiles'], {})
        for record in manifest['props'].values():
            self.assertEqual(set(record), {'image', 'foot_anchor'})

    def test_landmark_tree_and_crystal_ridge_share_native_reserve_sources(self):
        manifest = json.loads((FOLDER/'art.json').read_text())
        self.assertEqual(manifest['authoring'],'native_pixel_asset_assembly')
        self.assertEqual(manifest['props']['ridge_sanctuary']['foot_anchor'],[32,74])
        components=manifest['components']
        self.assertTrue(any(record['library']=='grove' and
                            'landmark_canopy' in record.get('modules',[])
                            for record in components))
        crystals=[record for record in components if record['library']=='crystals']
        self.assertEqual({record['module'].rsplit('.',1)[1] for record in crystals},
                         {'amethyst','cyan','opal'})
        sources=manifest['source_assets']
        self.assertFalse(any('generated_miniature' in record['path'] for record in sources))
        self.assertEqual(len({record['path'] for record in sources}),len(sources))
        for record in sources:
            with self.subTest(source=record['path']):
                self.assertEqual(hashlib.sha256((ROOT/record['path']).read_bytes()).hexdigest(),
                                 record['sha256'])

    def test_grounding_uses_regional_texture_and_keeps_gaps_open_to_the_world(self):
        manifest=json.loads((FOLDER/'art.json').read_text())
        grass_path='assets/terrain/overworld/elden_vale/polish/tiles/grass_meadow.png'
        self.assertEqual(manifest['grounding']['materials']['grass'],grass_path)
        self.assertIn(grass_path,{record['path'] for record in manifest['source_assets']})
        miniature=Image.open(FOLDER/'ridge_sanctuary.png').convert('RGBA')
        grass=Image.open(ROOT/grass_path).convert('RGBA')
        for x,y in ((10,48),(20,67),(88,67)):
            with self.subTest(footing=(x,y)):
                self.assertEqual(miniature.getpixel((x,y)),grass.getpixel((x%24,y%24)))
        for point in ((10,61),(50,73)):
            self.assertEqual(miniature.getpixel(point),(0,0,0,0),
                             'A continuous ground plate would hide the surrounding region')


if __name__ == '__main__':unittest.main()
