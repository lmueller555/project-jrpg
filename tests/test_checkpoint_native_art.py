"""Native action bank is synchronized with each actor's base-art opt-in."""
import os,json,unittest
from pathlib import Path
from types import SimpleNamespace
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from overworld_world import RoadGuard
from checkpoint_charm import CheckpointCharm,HOMES
from checkpoint_hd_bindings import ACTORS as ACTIVITY
from road_guard_hd_bindings import ACTORS as BASE
ROOT=Path(__file__).resolve().parents[1]
class CheckpointNativeTests(unittest.TestCase):
 def test_pose_identity_timing_and_equipment(self):
  def read(folder):return json.loads((ROOT/f'assets/characters/{folder}/animation.json').read_text())
  old,new=read('checkpoint_charm'),read('checkpoint_charm_hd')
  self.assertEqual(old['clips'],new['clips']);self.assertEqual(old['equipment'],new['equipment'])
  self.assertEqual(new['draw_anchor'],[20,38])
 def test_every_activity_clip_respects_per_actor_opt_in(self):
  pygame.init();pygame.display.set_mode((1,1))
  try:
   world=SimpleNamespace(data={'id':'elden_vale'},npcs=[])
   for index,position in enumerate(HOMES.values()):world.npcs.append(RoadGuard(world,{'id':'north_checkpoint'},position,index))
   charm=CheckpointCharm(world)
   for actor in world.npcs:
    native=actor.data['id'] in BASE and actor.data['id'] in ACTIVITY
    for key,clip in charm.clips.items():
     for time in (0,.15,.35,.7,1.2,1.8,2.1):
      image=charm._image(key,time,actor=actor)
      self.assertEqual(image.get_size(),(40,44))
      self.assertEqual(hasattr(image,'native'),native)
      if native:self.assertEqual(image.native.get_size(),(80,88))
  finally:pygame.quit()
if __name__=='__main__':unittest.main()
