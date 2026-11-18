import json,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
class WorkerAActivityTests(unittest.TestCase):
 def test_dependency_preserves_registration_and_cadence(self):
  a=json.loads((ROOT/'assets/characters/named_hd/sanctuary_worker_a/activities.json').read_text())
  self.assertEqual(set(a['poses']),{'injured','offer_arm','arm_rest'})
  for name,p in a['poses'].items():
   self.assertEqual(p['artwork_pixels_per_world_pixel'],2)
   expected=(48,72) if name=='injured' else (128,128)
   self.assertEqual(p['anchor'],[12,30] if name=='injured' else [32,40])
   self.assertEqual(sum(f['duration_ms'] for f in p['frames']),1000 if name=='injured' else 800)
   for f in p['frames']:
    im=Image.open(ROOT/f['file']);self.assertEqual(im.size,expected);self.assertEqual(set(im.getchannel('A').getdata()),{0,255})
  for left,right in zip(a['poses']['offer_arm']['frames'],reversed(a['poses']['arm_rest']['frames'])):
   self.assertEqual((ROOT/left['file']).read_bytes(),(ROOT/right['file']).read_bytes())
if __name__=='__main__':unittest.main()
