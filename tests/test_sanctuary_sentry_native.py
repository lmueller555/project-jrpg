"""One role's roster travel binding; all other support activity art unchanged."""
import json,os,unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from rendering import WorldCanvas
from sanctuary_arrival import CastActor
ROOT=Path(__file__).resolve().parents[1]
class SanctuarySentryNativeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):pygame.init();pygame.display.set_mode((1,1))
 @classmethod
 def tearDownClass(cls):pygame.quit()
 def test_manifest_targets_only_corresponding_roster_identity(self):
  art=json.loads((ROOT/'assets/story/sanctuary_arrival/art.json').read_text())['actors']['sentry']
  self.assertEqual(art['portrait_file'],'assets/characters/npc_roster_hd/adult_woman_02/portrait.png');self.assertEqual(art['poses'],{});self.assertEqual(art['anchor'],[12,30]);self.assertEqual(art['travel_artwork_pixels_per_world_pixel'],2)
  class World:
   def image(self,path):
    p=ROOT/path
    # CastActor loads its legacy fallback first; fake it only when sparse tests
    # don't materialize that unrelated tree. New assets must exist as real files.
    if not p.exists() and path.startswith('assets/characters/npcs/'):
     return pygame.Surface((24,36),pygame.SRCALPHA)
    return pygame.image.load(str(p)).convert_alpha()
  actor=CastActor('sentry',World(),variant='female_02',art=art)
  self.assertEqual(actor.probe_size,(24,12));self.assertEqual(actor.draw_anchor,(12,30))
  for d in ['front','back','left','right']:
   actor.facing=d;actor.moving=False;self.assertIsInstance(actor.sprite(0),WorldCanvas);self.assertEqual(actor.sprite(0).native.get_size(),(48,72))
   actor.moving=True
   for i in range(8):
    actor.walk_ms=i*70;self.assertIs(actor.sprite(0),actor.walks[d][i])
   actor.walk_ms=560;self.assertIs(actor.sprite(0),actor.walks[d][0]);self.assertEqual(sum(actor.walk_durations[d]),560)
if __name__=='__main__':unittest.main()
