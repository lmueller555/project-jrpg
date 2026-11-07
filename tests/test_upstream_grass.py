"""The live Mill quest exterior uses approved grass without moving quest stations."""
from hashlib import sha256
import json
from pathlib import Path
import unittest

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT/'assets/maps/eldenmere/upstream/map.json'
PACK = ROOT/'assets/terrain/grass/assets.json'


class UpstreamGrassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MAP.read_text())
        cls.pack = json.loads(PACK.read_text())

    def test_collision_and_original_quest_scene_contract_remain_exact(self):
        # These are the approved pre-rollout navigation and scene payloads.
        # Ground PNG paths stay fixed, while the new material/grass metadata is
        # additive. A vegetation art change must not move any route or prop.
        self.assertEqual(sha256((ROOT/self.data['collision']).read_bytes()).hexdigest(),
                         '17b3787d84ab064915511d7f36fedf3ba5bad5bfce9c4f886385aeb910a1b578')
        original = {key:value for key,value in self.data.items()
                    if key not in ('grass', 'terrain_materials', 'build')}
        encoded = json.dumps(original, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(sha256(encoded).hexdigest(),
                         '16dda0d4a14ca788426e640b15dc02bc6d6e86752958282d14977c2f7577d464')

    def test_clear_exposed_ground_tiles_are_actual_approved_material_pixels(self):
        materials = self.data['terrain_materials']
        self.assertEqual(materials['manifest'], 'assets/terrain/grass/assets.json')
        families = {family for row in materials['cells'] for family,_ in row}
        self.assertEqual(families, {'lawn', 'meadow', 'woodland'})
        # Independent exposed positions avoid paths, shrubs, channels and props.
        for x,y in ((9,15), (12,16), (26,12)):
            family,index = materials['cells'][y][x]
            with self.subTest(position=(x,y), family=family):
                with Image.open(ROOT/self.data['ground_frames'][0]) as ground, \
                        Image.open(ROOT/self.pack['materials'][family]['tiles'][index]) as tile:
                    actual = ground.crop((x*24,y*24,x*24+24,y*24+24)).convert('RGB')
                    self.assertIsNone(ImageChops.difference(actual,tile.convert('RGB')).getbbox())

    def test_irregular_grass_patches_stay_clear_of_collision_and_working_stations(self):
        grass = self.data['grass']
        self.assertEqual(grass['manifest'], 'assets/terrain/grass/assets.json')
        instances = grass['instances']
        self.assertGreaterEqual(len(instances), 35)
        self.assertEqual(len({item['id'] for item in instances}),len(instances))
        self.assertEqual({item['variant'] for item in instances},set(self.pack['tall_grass']['variants']))
        with Image.open(ROOT/self.data['collision']) as image:
            blocking = image.convert('L')
            for item in instances:
                x,y = item['position']
                with self.subTest(instance=item['id']):
                    self.assertIsNone(blocking.crop((x-12,y-18,x+12,y+7)).getbbox())
                    for px,py in ((180,510),(180,546),(480,240),(480,288),(480,336),(480,384)):
                        self.assertGreater((x-px)**2+(y-py)**2, 50**2)
                    self.assertFalse(6*24 <= x <= 9*24 and 9*24 <= y,
                                     'The entrance dirt lane must remain clear')
                    self.assertFalse(8*24 <= x <= 20*24 and 12*24 <= y <= 15*24,
                                     'The cross path must remain clear')

    def test_retained_recipe_and_production_manifest_hashes_match(self):
        build = self.data['build']
        self.assertEqual(sha256((ROOT/build['grass_recipe']).read_bytes()).hexdigest(),
                         build['grass_recipe_sha256'])
        self.assertEqual(sha256(PACK.read_bytes()).hexdigest(),build['grass_manifest_sha256'])


if __name__ == '__main__':
    unittest.main()
