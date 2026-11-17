"""Source schedules protect real portals and all separately owned landmark views."""
import json
from pathlib import Path
import unittest
from PIL import Image
from tools.eldenmere_architecture_contracts import validate_schedule, reference_diagrams
ROOT=Path(__file__).resolve().parents[1]
def read(path):return json.loads((ROOT/path).read_text())
class ArchitectureContractsTests(unittest.TestCase):
    def setUp(self):
        self.schedule=read('assets/source/maps/eldenmere/town_hd/architecture_schedule.json')
        self.town=read('assets/maps/eldenmere/playable/map.json')
    def test_thirteen_complete_source_records_match_production_registration(self):
        self.assertTrue(validate_schedule(self.schedule,self.town))
        for record in self.schedule['buildings']:
            for key in ('identity','interior_scenes','logical_canvas','ground_footprint_local_logical','depth_baseline_world_logical','entrance','roof_eave_envelope_local_logical','floors','protected_features_and_stations'):
                self.assertTrue(record[key],(record['id'],key))
    def test_three_crossings_declare_occupied_surface_corridor_and_banks(self):
        a,b,mill=self.schedule['crossings']
        self.assertEqual(a['deck_coverage_local_logical'],[0,12,144,48])
        self.assertEqual(b['deck_coverage_local_logical'],[0,12,168,48])
        self.assertEqual(mill['doorstep_world_logical'],[971,342])
        self.assertTrue(all(r['collision_change'] is None for r in (a,b,mill)))
        self.assertTrue(all(r['walking_corridor_world_logical'][2]>=24 for r in (a,b,mill)))
    def test_inn_reserves_two_actual_floors_without_changing_existing_scene(self):
        inn=next(r for r in self.schedule['buildings'] if r['id']=='inn')
        self.assertEqual(inn['floors'][1]['scenes'],['inn_guest_floor'])
        self.assertEqual(inn['stairs']['reserved_footprint_logical'],[336,204,60,84])
        self.assertEqual(inn['stairs']['clear_landing_logical'],[336,288,60,24])
        self.assertEqual(inn['entrance']['destination'],self.town['interior_scenes']['inn'])
    def test_mira_mill_school_retained_hearths_have_corresponding_right_flues(self):
        for r in self.schedule['buildings']:
            if r['id'] in ('mira','mill','school'):
                self.assertEqual(len(r['chimney']['hearths']),1)
                self.assertGreater(r['chimney']['position_logical'][0],r['logical_canvas'][0]/2)
    def test_town_excludes_antlers_but_separately_owned_views_and_shared_art_remain(self):
        self.assertEqual(self.town['landmark_layers'],[])
        rec=read('assets/source/maps/eldenmere/town_hd/recipe.json')
        self.assertNotIn('distant_landmarks',rec)
        regional=read('assets/maps/overworld/elden_vale/hd_integration/manifest.json')
        self.assertEqual(len([x for x in regional['landmarks'] if x.startswith('regional_')]),5)
        reserve=read('assets/maps/elden_vale_sanctuary/map.json')
        self.assertTrue(reserve['landmark_layers'])
        signature=read('assets/terrain/overworld/elden_vale/signature_landscape_hd/manifest.json')
        self.assertTrue((ROOT/signature['assets']['antlers_distant']['image']).is_file())
    def test_projection_reference_is_reproducible_and_native_sized(self):
        for path,expected in reference_diagrams().items():
            self.assertEqual(expected.size,(960,640))
            self.assertEqual(expected.tobytes(),Image.open(ROOT/path).convert('RGB').tobytes())
