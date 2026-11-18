import json,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
class CaretakerActivityTests(unittest.TestCase):
 def test_shared_receive_keeps_unhook_source_and_timing(self):
  a=json.loads((ROOT/'assets/characters/named_hd/sanctuary_caretaker/activities.json').read_text())['poses']
  self.assertEqual([f['file'] for f in a['receive']['frames']],[f['file'] for f in a['unhook']['frames'][2:10]])
  for pose in a.values():
   self.assertEqual(pose['anchor'],[20,40]);self.assertEqual(pose['artwork_pixels_per_world_pixel'],2)
   self.assertEqual(sum(f['duration_ms'] for f in pose['frames']),1600)
   for f in pose['frames']:
    im=Image.open(ROOT/f['file']);self.assertEqual(im.size,(80,96));self.assertEqual(set(im.getchannel('A').getdata()),{0,255})
if __name__=='__main__':unittest.main()
