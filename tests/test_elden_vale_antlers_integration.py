"""Active cross-scale antlers retain source anatomy and independent geometry."""
import copy,json,os
from pathlib import Path
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from PIL import Image,ImageDraw,ImageChops
from overworld_world import OverworldWorld,REGION_FILE
from tools.elden_vale_landmark_bindings import support_rectangles
ROOT=Path(__file__).resolve().parents[1]

class ActiveAntlersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):pygame.init();pygame.display.set_mode((960,640))
    @classmethod
    def tearDownClass(cls):pygame.quit()
    def test_registry_explicitly_adapts_staged_assets_and_activates_complete_arrangement(self):
        world=OverworldWorld()
        antlers=[r for r in world.landmarks.records if r['id'].startswith('regional_')]
        self.assertEqual(len(antlers),5)
        self.assertEqual(sum(r['layer']=='overhead' for r in antlers),4)
        self.assertTrue(all(r['artwork_pixels_per_world_pixel']==2 and r['collision']=='none' for r in world.landmarks.records))
        image,anchor=world._prop_image('ridge_sanctuary')
        self.assertEqual(image.get_size(),(96,80));self.assertEqual(anchor,(48,78))
        self.assertFalse(world._bridge_repaired())
        self.assertTrue(all(not world.can_stand(gate['position']) for gate in world.gates))
    def test_embedded_parts_preserve_every_bone_pixel_and_common_master_offsets(self):
        region=json.loads(REGION_FILE.read_text());manifest=json.loads((ROOT/region['hd_art_manifest']).read_text())
        original=Image.open(ROOT/'assets/terrain/overworld/elden_vale/signature_landscape_hd/antlers/antlers_regional.png').convert('RGBA')
        composed=Image.new('RGBA',original.size)
        for key,record in manifest['landmarks'].items():
            if key.startswith('regional_'):composed.alpha_composite(Image.open(ROOT/record['image']).convert('RGBA'),tuple(record['assembly_position_artwork']))
        plan=region['signature_landscape'];mask=Image.new('L',original.size)
        ImageDraw.Draw(mask).polygon([(round(x*768/1568),round((760+y)*.5)) for x,y in plan['bone_polygon_source_artwork']],fill=255)
        self.assertIsNone(ImageChops.multiply(ImageChops.difference(original,composed).getchannel('A'),mask).getbbox())
        for band in ('R','G','B'):
            self.assertIsNone(ImageChops.multiply(ImageChops.difference(original,composed).getchannel(band),mask).getbbox())
        self.assertIsNotNone(ImageChops.difference(original.getchannel('A'),composed.getchannel('A')).getbbox())
    def test_support_validation_rejects_a_shift_onto_walkable_ground(self):
        recipe=json.loads((ROOT/'assets/source/maps/overworld/elden_vale/recipe.json').read_text());plan=copy.deepcopy(recipe['signature_landscape'])
        self.assertEqual(len(support_rectangles(recipe,plan)),2)
        plan['master_origin_logical'][0]-=200
        with self.assertRaisesRegex(ValueError,'leaves existing solid ridge'):support_rectangles(recipe,plan)
    def test_town_has_no_antler_placement_or_visibility_configuration(self):
        town=json.loads((ROOT/'assets/maps/eldenmere/playable/map.json').read_text())
        recipe=json.loads((ROOT/'assets/source/maps/eldenmere/town_hd/recipe.json').read_text())
        self.assertEqual(town['landmark_layers'],[])
        self.assertNotIn('distant_landmarks',recipe)
        self.assertFalse(any('signature_landscape_hd' in r['file'] for r in recipe['dependencies']))

    def test_every_ground_contact_texel_is_on_named_existing_solid(self):
        region=json.loads(REGION_FILE.read_text());manifest=json.loads((ROOT/region['hd_art_manifest']).read_text())
        plan=region['signature_landscape'];solids=support_rectangles(region,plan)
        record=manifest['landmarks']['regional_skull_contact']
        alpha=Image.open(ROOT/record['image']).convert('RGBA').getchannel('A')
        ox,oy=plan['master_origin_logical'];oy+=250
        for py in range(alpha.height):
            for px in range(alpha.width):
                if not alpha.getpixel((px,py)):continue
                x,y=ox+(px+.5)/2,oy+(py+.5)/2
                self.assertTrue(any(fx<=x<fx+w and fy<=y<fy+h for fx,fy,w,h in solids),(x,y))
