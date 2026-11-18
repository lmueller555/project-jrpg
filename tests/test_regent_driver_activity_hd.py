from pathlib import Path
import unittest,json,hashlib,subprocess,sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];ID='regent_driver';OUT=ROOT/'assets/story/royal_activity_hd'/ID;SRC=ROOT/'assets/source/story/royal_activity_hd'/ID;REV=ROOT/'docs/reviews/royal_activity_hd'/ID
class ActivityArt(unittest.TestCase):
 def test_geometry(self):
  m=json.loads((OUT/'animation.json').read_text());self.assertEqual(m['id'],ID);self.assertEqual(m['draw_anchor'],[24,60]);self.assertEqual(m['artwork_pixels_per_world_pixel'],2)
  for pose in m['poses'].values():
   for f in pose['frames']:
    with Image.open(OUT/f['file']) as im:self.assertEqual(im.size,(48,72));self.assertLessEqual(set(im.getchannel('A').tobytes()),{0,255});self.assertTrue(im.getbbox())
 def test_scope_and_timing(self):
  m=json.loads((OUT/'animation.json').read_text());self.assertEqual(set(m['poses']),{'regent_clerk':{'read','seated'},'regent_driver':{'seated'},'regent_survivor':{'alarm_front','rest_front'}}[ID])
  if ID=='regent_clerk':self.assertEqual([f['duration_ms'] for f in m['poses']['read']['frames']],[140,110,100,140,180,200]);self.assertFalse(m['poses']['read']['loop'])
 def test_flattened_master(self):
  for name,pose in json.loads((OUT/'animation.json').read_text())['poses'].items():
   with Image.open(SRC/(name+'_native_master.png')) as strip:
    for i,f in enumerate(pose['frames']):
     with Image.open(OUT/f['file']) as im:self.assertEqual(im.tobytes(),strip.crop((48*i,0,48*(i+1),72)).tobytes())
 def test_refs(self):
  for path,digest in json.loads((SRC/'reference_hashes.json').read_text()).items():self.assertEqual(hashlib.sha256((SRC/'reference'/Path(path).name).read_bytes()).hexdigest(),digest)
 def test_rebuild(self):
  def snap():return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for folder in [OUT,REV] for p in folder.rglob('*') if p.is_file()}
  before=snap();subprocess.run([sys.executable,str(ROOT/f'tools/build_{ID}_activity_hd.py')],check=True,capture_output=True);self.assertEqual(before,snap())
if __name__=='__main__':unittest.main()
