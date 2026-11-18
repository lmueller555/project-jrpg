"""Identity activation depends on the separate seated injury drawing."""
import hashlib,json,os,unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from rendering import WorldCanvas
from sanctuary_arrival import CastActor
ROOT=Path(__file__).resolve().parents[1]
class WorkerBNativeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):pygame.init();pygame.display.set_mode((1,1))
 @classmethod
 def tearDownClass(cls):pygame.quit()
 def test_complete_stationary_identity_and_activity(self):
  bank=ROOT/'assets/characters/named_hd/sanctuary_worker_b'
  art=json.loads((bank/'manifest.json').read_text())
  live=json.loads((ROOT/'assets/story/sanctuary_arrival/art.json').read_text())['actors']['worker_b']
  self.assertEqual(live,art);self.assertEqual(art['activation_requires'],['injured'])
  self.assertEqual(set(art['poses']),{'injured'});self.assertTrue(art['stationary'])
  class World:
   def image(self,path):
    p=ROOT/path
    if not p.exists() and path.startswith('assets/characters/npcs/'):return pygame.Surface((24,36),pygame.SRCALPHA)
    return pygame.image.load(str(p)).convert_alpha()
  actor=CastActor('worker_b',World(),art=art)
  self.assertEqual(actor.draw_anchor,(12,30));self.assertEqual(actor.probe_size,(24,12))
  for d in ['front','back','left','right']:
   actor.facing=d;actor.moving=False
   self.assertIsInstance(actor.sprite(0),WorldCanvas);self.assertEqual(actor.sprite(0).native.get_size(),(48,72))
   self.assertEqual(len(actor.walks[d]),1);self.assertEqual(actor.walk_durations[d],(200,))
  actor.pose='injured';actor.moving=False
  self.assertEqual(actor.sprite(0).native.get_size(),(64,72))
  self.assertEqual(actor.pose_animations['injured']['anchor'],(16,30))
  self.assertEqual((bank/'portrait.png').read_bytes(),(ROOT/'assets/story/sanctuary_arrival/art/portraits/worker_b.png').read_bytes())
if __name__=='__main__':unittest.main()
