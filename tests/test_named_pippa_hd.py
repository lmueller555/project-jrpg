"""ID-local native art contract. No global binding or unrelated actor changes."""
import unittest,json,hashlib,subprocess,sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];ID='pippa';CROWN=18;HEIGHT=52
BANK=ROOT/f'assets/characters/named_hd/{ID}';SRC=ROOT/f'assets/source/characters/named_hd/{ID}';REV=ROOT/f'docs/reviews/named_hd/{ID}'
class NamedArtTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.data=json.loads((SRC/'pose_drawings.json').read_text())
 def test_identity_and_geometry(self):
  m=json.loads((BANK/'design.json').read_text());self.assertEqual(m['id'],ID);self.assertEqual(m['frame_size'],[48,72]);self.assertEqual(m['logical_size'],[24,36]);self.assertEqual(m['draw_anchor'],[12,30]);self.assertEqual(m['foot_anchor'],[12,34]);self.assertEqual(m['artwork_pixels_per_world_pixel'],2)
 def test_portrait_exact_identity(self):
  self.assertEqual((BANK/'portrait.png').read_bytes(),(SRC/'reference/portrait.png').read_bytes());im=Image.open(BANK/'portrait.png');self.assertEqual(im.size,(72,72));im.close()
 def test_idle_child_height_and_alpha(self):
  for dr in self.data['idle']:
   im=Image.open(BANK/f'idle_{dr}.png');b=im.getbbox();self.assertEqual(im.size,(48,72));self.assertEqual(b[1],CROWN);self.assertEqual(b[3],70);self.assertEqual(b[3]-b[1],HEIGHT);self.assertTrue(set(im.getchannel('A').tobytes())<={0,255});self.assertGreater(b[0],0);self.assertLess(b[2],48)
 def test_walk_registration_source_and_strip(self):
  for dr,poses in self.data['walk'].items():
   bank=BANK/f'walk_{dr}';meta=json.loads((bank/'animation.json').read_text());self.assertEqual(meta['draw_anchor'],[24,60]);self.assertEqual(meta['foot_anchor'],[24,68]);self.assertEqual(meta['artwork_pixels_per_world_pixel'],2);self.assertEqual(len(meta['frames']),8);self.assertEqual(sum(f['duration_ms'] for f in meta['frames']),560)
   strip=Image.open(bank/'spritesheet.png');self.assertEqual(strip.size,(384,72));self.assertEqual(strip.tobytes(),Image.open(SRC/f'walk_{dr}_native_master.png').tobytes())
   hashes=set()
   for i,(k,f) in enumerate(zip(poses,meta['frames'])):
    im=Image.open(bank/f['file']);self.assertEqual(im.size,(48,72));self.assertEqual(im.getbbox()[1],CROWN+k['b']);self.assertTrue(set(im.getchannel('A').tobytes())<={0,255});self.assertEqual(im.tobytes(),strip.crop((48*i,0,48*(i+1),72)).tobytes());hashes.add(im.tobytes())
    for key in ['rt','lt']:self.assertTrue(im.getpixel(tuple(k[key]))[3])
   self.assertEqual(len(hashes),8)
 def test_saved_preview_timing(self):
  for dr in self.data['walk']:
   for name,total in [('native.gif',560),('normal.gif',560),('slow.gif',1120)]:
    im=Image.open(REV/dr/name);duration=0
    for i in range(im.n_frames):im.seek(i);duration+=im.info['duration']
    self.assertEqual(duration,total);im.close()
 def test_no_run_or_generic_activity_added(self):
  self.assertFalse(list(BANK.glob('run*')));self.assertFalse((BANK/'activity').exists())
 def test_reference_provenance(self):
  p=json.loads((SRC/'provenance.json').read_text())
  for name,digest in p['references'].items():self.assertEqual(hashlib.sha256((SRC/'reference'/name).read_bytes()).hexdigest(),digest)
  guide=json.loads((SRC/'guide_provenance.json').read_text())
  for dr,data in guide['directions'].items():self.assertEqual(hashlib.sha256((SRC/'reference/gait_guides'/f'{dr}.png').read_bytes()).hexdigest(),data['sha256'])
 def test_reproducible_rebuild(self):
  def snapshot():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in [BANK,REV] for p in folder.rglob('*') if p.is_file()}
  before=snapshot();subprocess.run([sys.executable,str(ROOT/f'tools/build_named_{ID}_hd.py')],check=True,stdout=subprocess.DEVNULL);self.assertEqual(before,snapshot())
if __name__=='__main__':unittest.main()
