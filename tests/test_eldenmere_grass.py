"""Approved town grass preserves the assembled navigation/story contract."""
from hashlib import sha256
import json
from pathlib import Path
import unittest

from PIL import Image


ROOT=Path(__file__).resolve().parents[1]


def read(path):return json.loads((ROOT/path).read_text())


class EldenmereGrassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=read('assets/maps/eldenmere/playable/map.json')
        cls.recipe=read('assets/source/maps/eldenmere/grass/recipe.json')
        cls.pack=read(cls.recipe['pack'])
        cls.live_pack=read(cls.data['grass']['manifest'])
        cls.courtyard=read('assets/source/maps/eldenmere/courtyard_hd/baseline_map.json')

    def test_rollout_preserves_collision_and_all_non_art_metadata(self):
        # Original hashes predate later regional story rooms. Compare today's
        # gameplay contract to the retained pre-HD town, allowing visual records.
        excluded=('entities','overview','ground_frames','grass','doors',
                  'ground_overlays','art_integrations','pause_on_focus_loss')
        protected={k:v for k,v in self.data.items() if k not in excluded}
        previous={k:v for k,v in self.courtyard.items() if k not in excluded}
        self.assertEqual(protected,previous)
        self.assertEqual(sha256((ROOT/self.data['collision']).read_bytes()).hexdigest(),self.recipe['collision_sha256'])
        def registration(entry):
            return {k:v for k,v in entry.items() if k not in ('frames','logical_size',
                    'artwork_pixels_per_world_pixel','reduced_motion_image','reduced_motion_frame')}
        self.assertEqual([registration(e) for e in self.data['entities']],
                         [registration(e) for e in self.courtyard['entities']])
        self.assertEqual([registration(e) for e in self.data['doors']],
                         [registration(e) for e in self.courtyard['doors']])
        self.assertTrue({'school','liam_house'}.issubset({entity['id'] for entity in self.data['entities']}))

    def test_all_materials_are_used_with_exact_approved_pixels_in_clear_tiles(self):
        cells=self.data['grass']['material_cells']
        used={family:set() for family in self.pack['materials']}
        coverage=Image.open(ROOT/self.recipe['coverage'][0]['image']).convert('L')
        ground=Image.open(ROOT/self.data['ground_frames'][0]).convert('RGB')
        tested={family:set() for family in used}
        for y,row in enumerate(cells):
            for x,(family,index) in enumerate(row):
                used[family].add(index)
                if index in tested[family]:continue
                box=(x*24,y*24,(x+1)*24,(y+1)*24)
                if coverage.crop(box).getextrema()!=(255,255):continue
                image=Image.open(ROOT/self.pack['materials'][family]['tiles'][index]).convert('RGB')
                with self.subTest(family=family,index=index):self.assertEqual(ground.crop(box).tobytes(),image.tobytes())
                tested[family].add(index)
        self.assertEqual(used,{family:{0,1,2,3} for family in used})
        self.assertEqual(tested,used)

    def test_tall_grass_avoids_water_roads_props_doors_and_character_approaches(self):
        coverage=Image.open(ROOT/self.recipe['coverage'][0]['image']).convert('L')
        collision=Image.open(ROOT/self.data['collision']).convert('L')
        allowed=Image.open(ROOT/self.data['navigation_allowed']).convert('L')
        protected=[self.data['spawn'],*[entry['position'] for entry in self.data['landmarks']],
                   *self.data['destinations'].values(),*[entry['position'] for entry in self.data['npcs']]]
        instances=self.data['grass']['instances'];seen=set()
        self.assertGreater(len(instances),100)
        self.assertFalse(set(self.recipe['remove_legacy_entities'])&{entry['id'] for entry in self.data['entities']})
        for record in instances:
            with self.subTest(clump=record['id']):
                x,y=record['position'];box=(x-12,y-12,x+12,y+6)
                self.assertNotIn((x,y),seen);seen.add((x,y))
                self.assertEqual(coverage.crop(box).getextrema(),(255,255))
                self.assertIsNone(collision.crop(box).getbbox())
                self.assertIsNone(allowed.crop(box).getbbox())
                self.assertFalse(any(abs(x-p[0])<self.recipe['protected_radius'] and abs(y-p[1])<self.recipe['protected_radius'] for p in protected))
                self.assertIn(record['variant'],self.live_pack['tall_grass']['variants'])

    def test_animated_coverage_inputs_are_native_binary_masks_with_recorded_fingerprints(self):
        self.assertEqual(len(self.recipe['coverage']),len(self.data['ground_frames']))
        for record in self.recipe['coverage']:
            with self.subTest(source=record['image']):
                path=ROOT/record['image']
                self.assertEqual(sha256(path.read_bytes()).hexdigest(),record['sha256'])
                image=Image.open(path)
                self.assertEqual(image.size,tuple(self.data['size_pixels']))
                self.assertLessEqual(set(image.get_flattened_data()),{0,255})


if __name__=='__main__':unittest.main()
