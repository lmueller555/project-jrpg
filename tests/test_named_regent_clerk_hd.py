from pathlib import Path
import unittest,json,hashlib,subprocess,sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];BANK=ROOT/'assets/characters/named_hd/regent_clerk';SRC=ROOT/'assets/source/characters/named_hd/regent_clerk';REVIEW=ROOT/'docs/reviews/named_hd/regent_clerk'
class PageArt(unittest.TestCase):
 def test_design(self):
  m=json.loads((BANK/'design.json').read_text());self.assertEqual(m['id'],'regent_clerk');self.assertEqual(m['draw_anchor'],[12,30]);self.assertEqual(m['foot_anchor'],[12,34]);self.assertEqual(m['artwork_pixels_per_world_pixel'],2)
 def test_idle(self):
  for dr in ['front','right','back','left']:
   with Image.open(BANK/f'idle_{dr}.png') as im:self.assertEqual(im.size,(48,72));self.assertEqual(im.getbbox()[1],0);self.assertEqual(im.getbbox()[3],70);self.assertLessEqual(set(im.getchannel('A').tobytes()),{0,255})
 def test_walk(self):
  for dr in ['front','right','back','left']:
   f=BANK/f'walk_{dr}';m=json.loads((f/'animation.json').read_text());self.assertEqual(m['draw_anchor'],[24,60]);self.assertEqual(m['foot_anchor'],[24,68]);self.assertEqual(sum(x['duration_ms'] for x in m['frames']),560);frames=[]
   with Image.open(f/'spritesheet.png') as strip:
    for i,x in enumerate(m['frames']):
     with Image.open(f/x['file']) as im:self.assertEqual(im.size,(48,72));frames.append(im.tobytes());self.assertEqual(im.tobytes(),strip.crop((48*i,0,48*i+48,72)).tobytes());self.assertLessEqual(set(im.getchannel('A').tobytes()),{0,255})
   self.assertEqual(len(set(frames)),8)
 def test_portrait(self):self.assertEqual((BANK/'portrait.png').read_bytes(),(SRC/'reference/portrait.png').read_bytes())
 def test_no_unused_motion(self):self.assertFalse(list(BANK.glob('run*')))
 def test_gif_timing(self):
  for dr in ['front','right','back','left']:
   for name,total in [('native.gif',560),('normal.gif',560),('slow.gif',1120)]:
    with Image.open(REVIEW/dr/name) as im:
     duration=0
     for i in range(im.n_frames):im.seek(i);duration+=im.info['duration']
     self.assertEqual(duration,total)
 def test_reproducibility(self):
  def snap():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in [BANK,REVIEW] for p in folder.rglob('*') if p.is_file()}
  before=snap();subprocess.run([sys.executable,str(ROOT/'tools/build_named_regent_clerk_hd.py')],check=True,capture_output=True);self.assertEqual(before,snap())
if __name__=='__main__':unittest.main()
