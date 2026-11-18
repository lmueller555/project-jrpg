"""Density-aware guard pose banks preserve costume, registration and timing."""
import os,json,unittest
from pathlib import Path
from types import SimpleNamespace
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from overworld_world import RoadGuard
from road_guard_hd_bindings import ACTORS
ROOT=Path(__file__).resolve().parents[1]
class GuardHDTests(unittest.TestCase):
 def test_per_actor_registration_and_greetings(self):
  pygame.init();pygame.display.set_mode((1,1))
  try:
   world=SimpleNamespace(data={'id':'elden_vale'})
   for gate in ('south_checkpoint','north_checkpoint'):
    for index in (0,1):
     actor=RoadGuard(world,{'id':gate,'guard_position':[100,100]},index=index)
     self.assertEqual(actor.blocker.size,(12,8));self.assertEqual(actor.draw_anchor,(20,38))
     for facing in ('front','back','left','right'):
      actor.begin_conversation(facing,100)
      for ms in (100,400,800,1100):
       image=actor.sprite(ms);self.assertEqual(image.get_size(),(40,44))
       if actor.data['id'] in ACTORS:self.assertEqual(image.native.get_size(),(80,88))
      actor.end_conversation();self.assertEqual(actor.facing,actor.watch_facing)
  finally:pygame.quit()
 def test_exact_identity_and_clip_contract(self):
  legacy=json.loads((ROOT/'assets/characters/road_guards/animation.json').read_text())
  native=json.loads((ROOT/'assets/characters/road_guards_hd/animation.json').read_text())
  self.assertEqual(legacy['clips'],native['clips']);self.assertEqual(legacy['equipment'],native['equipment'])
  self.assertEqual((ROOT/'assets/characters/road_guards_hd/portrait.png').read_bytes(),(ROOT/'assets/portraits/eldenmere/road_guard_neutral.png').read_bytes())
if __name__=='__main__':unittest.main()
