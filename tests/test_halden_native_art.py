"""Native named appearance contract; no household behavior or collision changes."""
import hashlib,json,os,unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from rendering import WorldCanvas
from halden_visit import Halden
ROOT=Path(__file__).resolve().parents[1]
NAME='halden'
class NamedArtTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):pygame.init();pygame.display.set_mode((1,1))
 @classmethod
 def tearDownClass(cls):pygame.quit()
 def world(self):
  class W:
   def image(self,path):return pygame.image.load(str(ROOT/path)).convert_alpha()
  return W()
 def test_preserved_logical_identity_and_registration(self):
  actor=Halden(self.world());self.assertEqual(actor.data['id'],NAME);self.assertEqual(actor.probe_size,(12,8));self.assertEqual(actor.draw_anchor,(12,30));self.assertEqual(actor.roster_art.foot_anchor,(12,34.5))
  for d in ['front','back','left','right']:
   actor.facing=d;im=actor.sprite(0);self.assertIsInstance(im,WorldCanvas);self.assertEqual(im.get_size(),(24,36));self.assertEqual(im.native.get_size(),(48,72))
 def test_all_drawings_and_manifest_timing(self):
  actor=Halden(self.world());actor.moving=True
  for d in ['front','back','left','right']:
   actor.facing=d;bank=ROOT/f'assets/characters/named_hd/{NAME}/walk_{d}'
   meta=json.loads((bank/'animation.json').read_text());self.assertEqual(len(meta['frames']),8);self.assertEqual(sum(x['duration_ms'] for x in meta['frames']),560)
   hashes=[]
   for i,f in enumerate(meta['frames']):
    actor.walk_ms=i*70;image=actor.sprite(0);expected=pygame.image.load(str(bank/f['file'])).convert_alpha();self.assertEqual(pygame.image.tobytes(image.native,'RGBA'),pygame.image.tobytes(expected,'RGBA'));hashes.append(hashlib.sha256(pygame.image.tobytes(image.native,'RGBA')).hexdigest())
   self.assertEqual(len(set(hashes)),8)
   actor.walk_ms=560;self.assertEqual(pygame.image.tobytes(actor.sprite(0).native,'RGBA'),pygame.image.tobytes(actor.roster_art.walks[d][0][0].native,'RGBA'))
 def test_conversation_uses_own_facing_and_resumes(self):
  actor=Halden(self.world());actor.facing='right';actor.moving=True;actor.walk_ms=210;actor.request_conversation('left');self.assertIs(actor.sprite(0),actor.idles['left']);actor.end_conversation();self.assertIs(actor.sprite(0),actor.roster_art.walks['right'][3][0])
 def test_original_detailed_portrait_retained(self):
  self.assertEqual((ROOT/f'assets/characters/named_hd/{NAME}/portrait.png').read_bytes(),(ROOT/f'assets/portraits/eldenmere/{NAME}_neutral.png').read_bytes())
if __name__=='__main__':unittest.main()
