"""Dormant native source-body packages preserve logical work semantics."""
from io import BytesIO
import json
from pathlib import Path
import unittest
from PIL import Image,ImageChops
from tools.build_regional_worker_activity_hd import products,ROLES
ROOT=Path(__file__).resolve().parents[1]

def installed():
    return [r for r in ROLES if (ROOT/f'assets/source/characters/regional_npc_hd/{r}/activity_hd/recipe.json').is_file()]

class RegionalNativeWorkSourceTests(unittest.TestCase):
    def test_each_package_is_dormant_explicitly_scoped_and_physically_registered(self):
        self.assertTrue(installed())
        for role in installed():
            folder=ROOT/f'assets/characters/regional_npc_hd/{role}/activity_hd'
            meta=json.loads((folder/'manifest.json').read_text())
            self.assertFalse(meta['runtime_activation']);self.assertEqual(meta['actor_id'],role)
            self.assertEqual(meta['integration_status'],'staged_not_integrated')
            self.assertEqual(meta['logical_canvas'],[48,52]);self.assertEqual(meta['draw_anchor_logical'],[24,46])
            self.assertEqual(meta['artwork_pixels_per_world_pixel'],2)
            self.assertTrue(meta['activation_gates'])
            self.assertNotEqual(role,'sanctuary_gardener')
    def test_native_frames_are_unclipped_hard_alpha_and_not_legacy_pixel_enlargements(self):
        for role in installed():
            folder=ROOT/f'assets/characters/regional_npc_hd/{role}/activity_hd'
            meta=json.loads((folder/'manifest.json').read_text());changed=0
            bank=ROOT/'assets/characters'/ROLES[role][1]
            for record in meta['frames']:
                im=Image.open(folder/record['file']).convert('RGBA')
                self.assertEqual(im.size,(96,104));self.assertFalse(set(im.getchannel('A').tobytes())-{0,255})
                box=im.getbbox();self.assertTrue(box);self.assertGreaterEqual(box[0],1);self.assertGreaterEqual(box[1],1)
                self.assertLess(box[2],96);self.assertLess(box[3],104)
                old=Image.open(bank/record['logical_attachment_metadata']['file']).convert('RGBA')
                enlarged=Image.new('RGBA',(96,104));enlarged.alpha_composite(old.resize((80,88),Image.Resampling.NEAREST),(8,16))
                changed+=im.tobytes()!=enlarged.tobytes()
            self.assertGreater(changed,len(meta['frames'])*.6,role)
    def test_work_timings_loops_hands_and_prop_metadata_remain_logical(self):
        for role in installed():
            folder=ROOT/f'assets/characters/regional_npc_hd/{role}/activity_hd'
            meta=json.loads((folder/'manifest.json').read_text())
            old=json.loads((ROOT/'assets/characters'/ROLES[role][1]/'animation.json').read_text())
            self.assertEqual(set(meta['sequences']),set(old['sequences']))
            for key,sequence in meta['sequences'].items():
                self.assertEqual(sequence['loop'],old['sequences'][key]['loop'])
                self.assertEqual(len(sequence['frames']),len(old['sequences'][key]['frames']))
                for frame,previous in zip(sequence['frames'],old['sequences'][key]['frames']):
                    self.assertEqual(frame,{**previous,'file':'poses/'+previous['file']})
    def test_master_sampling_and_every_export_are_reproducible(self):
        for role in installed():
            for path,data in products(role).items():self.assertEqual((ROOT/path).read_bytes(),data,path)
