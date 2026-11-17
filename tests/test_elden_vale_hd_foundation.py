"""Consumer contracts for the staged regional pack."""
import json
from pathlib import Path
import unittest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/overworld/elden_vale/hd/art.json'

class FoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack=json.loads(PACK.read_text())

    def test_regional_geometry_and_binary_alpha(self):
        for kind in ('tiles','props'):
            for name,record in self.pack[kind].items():
                with self.subTest(name=name):
                    image=Image.open(ROOT/record['image']).convert('RGBA')
                    self.assertEqual(image.size,tuple(2*n for n in record['logical_size']))
                    self.assertLessEqual(set(image.getchannel('A').tobytes()),{0,255})
        region=json.loads((ROOT/'assets/maps/overworld/elden_vale/region.json').read_text())
        # The original pack remains an immutable staged export. Its registered
        # regional adaptations are selected by the live overlay manifest.
        self.assertEqual(self.pack['integration_status'],'not_integrated')
        live=json.loads((ROOT/region['hd_art_manifest']).read_text())
        self.assertEqual(live['integration_status'],'integrated')
        self.assertTrue(region['terrain_hd']['enabled'])

    def test_destroyed_bridge_registration_and_gap(self):
        bridge=self.pack['props']['broken_bridge_wide']
        self.assertEqual(bridge['logical_size'],[288,144])
        self.assertEqual(bridge['deck_bottom_px']-bridge['deck_top_px'],72)
        self.assertEqual(bridge['foot_anchor'],[144,94])
        a,b=bridge['central_gap_x_px']
        image=Image.open(ROOT/bridge['image'])
        self.assertIsNone(image.getchannel('A').crop((2*a,0,2*b,image.height)).getbbox())

    def test_vegetation_supports_do_not_drift(self):
        self.assertEqual(len(self.pack['vegetation']),51)
        for plant in self.pack['vegetation']:
            idle=Image.open(ROOT/plant['idle']).convert('RGBA')
            rect=(0,idle.height-4,idle.width,idle.height)
            for frame in plant['frames']:
                with self.subTest(plant=plant['id'],frame=frame['file']):
                    image=Image.open(ROOT/frame['file']).convert('RGBA')
                    self.assertEqual(image.size,idle.size)
                    self.assertEqual(image.crop(rect).tobytes(),idle.crop(rect).tobytes())
