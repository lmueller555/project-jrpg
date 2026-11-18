import json,os,unittest
from pathlib import Path
from types import SimpleNamespace
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from rendering import WorldCanvas,load_art
from sanctuary_arrival import CastActor
from sanctuary_care import SanctuaryCare
ROOT=Path(__file__).resolve().parents[1]
class AttendantNativeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):pygame.init();pygame.display.set_mode((1,1))
 @classmethod
 def tearDownClass(cls):pygame.quit()
 def actor(self):
  a=json.loads((ROOT/'assets/story/sanctuary_arrival/art.json').read_text())['actors']['runner']
  class World:
   def image(self,path):
    p=ROOT/path
    if not p.exists() and path.startswith('assets/characters/npcs/'):return pygame.Surface((24,36),pygame.SRCALPHA)
    return pygame.image.load(str(p)).convert_alpha()
  world=World();actor=CastActor('runner',world,art=a);carry=a['carrying'];meta={'artwork_pixels_per_world_pixel':2}
  actor.carry_idles={d:load_art(world,p,meta) for d,p in carry['carry_idles'].items()}
  actor.carry_walks={d:[load_art(world,f['file'],meta) for f in fs] for d,fs in carry['carry_walks'].items()}
  return actor,a
 def test_native_idle_carry_walk_and_empty_recovery(self):
  actor,a=self.actor();self.assertEqual(a['portrait_file'],'assets/characters/npc_roster_hd/adult_woman_01/portrait.png')
  for d in ['front','back','left','right']:
   actor.facing=d
   for carrying in [False,True]:
    actor.carrying=carrying;actor.moving=False;self.assertEqual(actor.sprite(0).native.get_size(),(48,72));actor.moving=True
    for i in range(8):
     actor.walk_ms=i*70;self.assertIs(actor.sprite(0),(actor.carry_walks if carrying else actor.walks)[d][i])
  actor.moving=False;actor.pose='runner_place';self.assertEqual(actor.sprite(0).native.get_size(),(128,128));self.assertEqual(actor.draw_anchor,(32,40))
 def test_single_release_preserves_700ms_and_1200ms_boundaries(self):
  actor,a=self.actor();actor.carrying=True;sounds=[]
  scene=SimpleNamespace(actors={'runner':actor},blocking=SimpleNamespace(busy=lambda _:False),_play_care_sound=lambda:sounds.append(True))
  care=SanctuaryCare(scene,{'poses':a['poses']});care._runner(0)
  care._runner(.699);self.assertTrue(actor.carrying);self.assertFalse(care.runner_linen_placed)
  care._runner(.001);self.assertFalse(actor.carrying);self.assertTrue(care.runner_linen_placed);self.assertEqual(len(sounds),1)
  care._runner(.5);self.assertTrue(care.runner_delivered);self.assertIsNone(actor.pose);self.assertEqual(len(sounds),1)
  care.reset(1);self.assertTrue(care.runner_delivered)
if __name__=='__main__':unittest.main()
