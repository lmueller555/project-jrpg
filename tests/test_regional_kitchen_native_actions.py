"""The blue regional kitchen gardener has complete reproducible native poses."""
from hashlib import sha256
from pathlib import Path
import json,shutil,subprocess,sys,tempfile,unittest
from PIL import Image
from tools.build_regional_kitchen_actions_hd import products,SPEC
R=Path(__file__).resolve().parents[1];S=R/'assets/source/characters/regional_npc_hd/regional_gardener/actions_hd';O=R/'assets/characters/regional_npc_hd/regional_gardener/actions_hd'
class KitchenNativeActions(unittest.TestCase):
 def setUp(self):self.m=json.loads((O/'animation.json').read_text())
 def test_scoped_dormant_source_never_enables_sanctuary_gardener(self):
  self.assertEqual(self.m['actor_id'],'regional_gardener');self.assertFalse(self.m['runtime_activation']);self.assertEqual(self.m['draw_anchor_logical'],[20,38]);self.assertEqual(self.m['logical_canvas'],[40,44]);self.assertEqual(self.m['artwork_pixels_per_world_pixel'],2)
 def test_all_program_and_wildlife_actions_have_complete_native_sources(self):
  self.assertEqual(set(self.m['sequences']),set(SPEC));self.assertIn('water_right',SPEC);self.assertIn('weed_front',SPEC)
  for key,seq in self.m['sequences'].items():
   for f in seq['frames']:
    self.assertEqual((S/'masters'/f['file']).read_bytes(),(O/f['file']).read_bytes());im=Image.open(O/f['file']).convert('RGBA');self.assertEqual(im.size,(80,88));self.assertTrue(im.getbbox());self.assertFalse(set(im.getchannel('A').tobytes())-{0,255})
 def test_reference_identity_is_exact_approved_blue_bank(self):
  for dr in ('front','back','left','right'):self.assertEqual((S/'references'/f'idle_{dr}.png').read_bytes(),(R/f'assets/characters/npc_roster_hd/adult_woman_01/idle_{dr}.png').read_bytes())
 def test_cycles_keep_both_weight_phases_and_precise_existing_pace(self):
  for pose in ('carry','carry_can'):
   for dr in ('front','back','left','right'):
    seq=self.m['sequences'][pose+'_'+dr];self.assertEqual(len(seq['frames']),8);self.assertEqual(sum(f['duration_ms'] for f in seq['frames']),680)
    a,b=[Image.open(O/seq['frames'][i]['file']).crop((16,55,64,80)).tobytes() for i in (0,4)];self.assertNotEqual(a,b)
 def test_full_source_authoring_reproduces_all_native_masters(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/'source';shutil.copytree(S,root);subprocess.run([sys.executable,str(root/'author.py')],check=True)
   for f in (S/'masters').glob('*.png'):self.assertEqual(f.read_bytes(),(root/'masters'/f.name).read_bytes(),f.name)
 def test_all_exports_and_hashes_reproduce_without_writes(self):
  for file,data in products().items():self.assertEqual((R/file).read_bytes(),data,file)
