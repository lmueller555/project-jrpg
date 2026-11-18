"""Special injured pose is its own dormant dependency, not a healthy walk."""
import json,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
class WorkerBActivityTests(unittest.TestCase):
 def test_injury_contract(self):
  p=ROOT/'assets/characters/named_hd/sanctuary_worker_b'
  a=json.loads((p/'injured.json').read_text())
  self.assertEqual(a['artwork_pixels_per_world_pixel'],2)
  self.assertEqual(a['anchor'],[16,30]);self.assertEqual(a['logical_size'],[32,36])
  self.assertTrue(a['loop']);self.assertEqual([f['duration_ms'] for f in a['frames']],[1000])
  im=Image.open(ROOT/a['frames'][0]['file'])
  self.assertEqual(im.size,(64,72));self.assertEqual(set(im.getchannel('A').getdata()),{0,255})
  self.assertLessEqual(im.getbbox()[3],68)
if __name__=='__main__':unittest.main()
