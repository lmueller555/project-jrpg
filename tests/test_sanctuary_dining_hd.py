"""The migrated room keeps gameplay geometry and real native artwork detail."""
import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image,ImageChops

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/sanctuary_dining_hd'
BANK=ROOT/'assets/terrain/eldenmere/sanctuary_dining_hd'


class DiningArtworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe=json.loads((SOURCE/'recipe.json').read_text())
        cls.original=cls.recipe['original_map']
        cls.data=json.loads((ROOT/cls.recipe['map']).read_text())
        cls.manifest=json.loads((BANK/'manifest.json').read_text())

    def test_collision_doors_destinations_and_world_proportions_are_unchanged(self):
        for key in ('size_pixels','size_tiles','tile_size','floor_rect','player_probe_size',
                    'player_draw_anchor','doors','destinations','spawn','collision','id'):
            self.assertEqual(self.data[key],self.original[key],key)
        self.assertEqual(hashlib.sha256((ROOT/self.data['collision']).read_bytes()).hexdigest(),
                         self.recipe['preserved_collision_sha256'])
        old={e['id']:e for e in self.original['entities']}
        for record in self.data['entities']:
            if record['id'] not in old:continue
            previous=old[record['id']]
            for key in ('sort_y','sort_priority','phase_offset','frame_duration_ms'):
                self.assertEqual(record[key],previous[key])
            if record['id']!='kettle_steam':self.assertEqual(record['position'],previous['position'])

    def test_props_are_registered_double_size_hard_alpha_with_black_contours(self):
        for record in self.manifest['props']:
            with self.subTest(object_id=record['id'],image=record['image']):
                image=Image.open(ROOT/record['image']).convert('RGBA')
                self.assertEqual(image.size,tuple(v*2 for v in record['logical_size']))
                self.assertLessEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
                self.assertIn((17,18,20,255),set(image.get_flattened_data()))
                bounds=image.getbbox();original=record['logical_bounds']
                self.assertEqual(bounds[3],original[3]*2)
                self.assertGreaterEqual(bounds[0],original[0]*2)
                self.assertLessEqual(bounds[2],original[2]*2)
                occupied=max((bounds[2]-bounds[0])/((original[2]-original[0])*2),
                             (bounds[3]-bounds[1])/((original[3]-original[1])*2))
                self.assertGreaterEqual(occupied,.85,'Opaque source matte must not shrink the drawing')

    def test_animated_architecture_is_shared_and_emitter_crop_is_registered(self):
        self.assertEqual(len(self.data['ground_frames']),1)
        self.assertEqual(len(set(self.data['ground_frames'])),1)
        with Image.open(ROOT/self.data['ground_frames'][0]) as ground:
            self.assertEqual(ground.size,(864,672))
        entities={e['id']:e for e in self.data['entities']}
        self.assertEqual(len(entities['dining_daylight']['frames'])*entities['dining_daylight']['frame_duration_ms'],5400)
        self.assertEqual(len(entities['dining_firelight']['frames'])*entities['dining_firelight']['frame_duration_ms'],1200)
        steam=entities['kettle_steam'];self.assertEqual(steam['position'],steam['registration_offset'])
        self.assertEqual(steam['source_logical_canvas'],self.original['size_pixels'])
        for path in steam['frames']:
            with Image.open(ROOT/path) as image:self.assertEqual(image.size,(12,20))

    def test_hearth_animation_keeps_structure_fixed_outside_fire_opening(self):
        frames=[Image.open(BANK/f'props/hearth_frame_{i:02}.png').convert('RGBA') for i in range(1,5)]
        mask=Image.open(BANK/self.manifest['hearth_animation']['cavity_mask']).convert('L')
        for frame in frames[1:]:
            delta=ImageChops.difference(frame,frames[0]).convert('RGB')
            self.assertIsNone(ImageChops.multiply(delta,ImageChops.invert(mask).convert('RGB')).getbbox())
        self.assertGreater(len({frame.tobytes() for frame in frames}),1)

    def test_hearth_flames_have_a_stable_root_and_stationary_log_lip(self):
        from tools.build_sanctuary_dining_hd import cell,export_sprite,registered_hearth_frames
        contract=self.recipe['hearth_animation']
        atlas=Image.open(SOURCE/'props_atlas.png').convert('RGBA')
        raw=[export_sprite(cell(atlas,item['cell'],5),tuple(v*2 for v in item['logical_size']),
                          tuple(v*2 for v in item['logical_bounds']))
             for item in self.recipe['props'] if item['id']=='hearth']
        frames,structure,mask,layers=registered_hearth_frames(raw,contract)
        root_x,root_y=contract['root_artwork']
        for index,(frame,layer) in enumerate(zip(frames,layers),1):
            with self.subTest(phase=index):
                exported=Image.open(BANK/f'props/hearth_frame_{index:02}.png').convert('RGBA')
                self.assertEqual(frame.tobytes(),exported.tobytes(),'Deterministic source-derived export')
                self.assertEqual(frame.crop((0,root_y,96,144)).tobytes(),raw[0].crop((0,root_y,96,144)).tobytes())
                self.assertIsNone(ImageChops.subtract(layer.getchannel('A'),mask).getbbox())
                bounds=layer.getbbox();self.assertEqual(bounds[3],root_y)
                self.assertLessEqual(bounds[3]-bounds[1],contract['maximum_flame_height_artwork'])
                bottom=[x for x in range(layer.width) if layer.getpixel((x,root_y-1))[3]]
                self.assertEqual((min(bottom)+max(bottom)+1)//2,root_x)
                self.assertEqual(structure.getpixel((root_x,root_y)),frame.getpixel((root_x,root_y)))

    def test_new_drawings_contain_detail_beyond_enlarged_legacy_pixels(self):
        image=Image.open(BANK/'props/table.png').convert('RGBA')
        self.assertTrue(any(len({image.getpixel((x+dx,y+dy)) for dx in (0,1) for dy in (0,1)})>1
                            for y in range(0,image.height,2) for x in range(0,image.width,2)))

    def test_retained_source_hashes_and_room_replacements_are_explicit(self):
        for name,digest in self.recipe['sources'].items():
            self.assertEqual(hashlib.sha256((SOURCE/name).read_bytes()).hexdigest(),digest)
        for record in self.manifest['props']:
            alias=self.data['art_replacements'][record['legacy_path']]
            self.assertEqual(alias['file'],record['image'])
            self.assertEqual(alias['artwork_pixels_per_world_pixel'],2)
