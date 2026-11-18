import json,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
class AttendantActivityTests(unittest.TestCase):
 def test_directional_custody_and_release_timing(self):
  a=json.loads((ROOT/'assets/characters/named_hd/sanctuary_attendant/activities.json').read_text())
  self.assertEqual(a['carry_anchor'],[12,30]);self.assertEqual(a['carry_artwork_pixels_per_world_pixel'],2)
  for d,frames in a['carry_walks'].items():
   self.assertEqual(sum(f['duration_ms'] for f in frames),560);self.assertEqual(len(frames),8)
   for f in frames:
    im=Image.open(ROOT/f['file']);self.assertEqual(im.size,(48,72));self.assertEqual(set(im.getchannel('A').getdata()),{0,255})
  p=a['poses']['runner_place'];self.assertEqual(p['anchor'],[32,40]);self.assertEqual(p['facing'],'left');self.assertEqual(p['cue_ms']['linen_deposit'],700)
  self.assertEqual(sum(f['duration_ms'] for f in p['frames']),1200)
  self.assertEqual([i for i,f in enumerate(p['frames']) if f.get('held_prop')=='linen'],list(range(7)))
  for f in p['frames']:
   im=Image.open(ROOT/f['file']);self.assertEqual(im.size,(128,128));self.assertEqual(set(im.getchannel('A').getdata()),{0,255})
if __name__=='__main__':unittest.main()
