import json,os,unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from rendering import WorldCanvas
from sanctuary_arrival import CastActor
ROOT=Path(__file__).resolve().parents[1]
class CaretakerNativeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):pygame.init();pygame.display.set_mode((1,1))
 @classmethod
 def tearDownClass(cls):pygame.quit()
 def test_shared_identity_has_complete_dependent_banks(self):
  a=json.loads((ROOT/'assets/story/sanctuary_arrival/art.json').read_text())['actors']['caretaker']
  b=json.loads((ROOT/'assets/story/sanctuary_rescue/art.json').read_text())['actors']['caretaker']
  self.assertEqual(a,b);self.assertEqual(set(a['poses']),{'unhook','receive'})
  class World:
   def image(self,path):
    p=ROOT/path
    if not p.exists() and path.startswith('assets/characters/npcs/'):return pygame.Surface((24,36),pygame.SRCALPHA)
    return pygame.image.load(str(p)).convert_alpha()
  actor=CastActor('caretaker',World(),art=a)
  self.assertEqual(actor.draw_anchor,(12,30));self.assertEqual(actor.probe_size,(24,12))
  for d in ['front','back','left','right']:
   actor.facing=d;actor.moving=False;self.assertEqual(actor.sprite(0).native.get_size(),(48,72))
   actor.moving=True;self.assertEqual(sum(actor.walk_durations[d]),560)
   for i in range(8):
    actor.walk_ms=i*70;self.assertIs(actor.sprite(0),actor.walks[d][i]);self.assertIsInstance(actor.sprite(0),WorldCanvas)
  actor.moving=False
  for pose in ['unhook','receive']:
   actor.pose=pose;self.assertEqual(actor.sprite(0).native.get_size(),(80,96));self.assertEqual(actor.draw_anchor,(20,40))
if __name__=='__main__':unittest.main()
