import sys, pathlib, json
sys.path.insert(0,str(pathlib.Path.cwd()/'tests'))
sys.path.insert(0,str(pathlib.Path.cwd()))
from test_mill_trigger_geometry import MillTriggerGeometryTests
from npc_routines import find_path
import pygame
f=MillTriggerGeometryTests();f.setUp()
try:
 f.reach_intake()
 rect=f.visible('bypass');goal=(rect.left-12,rect.bottom-10);g=f.g
 report={'target':goal,'start':list(g.player.position),'can_stand':g.world.can_stand(goal),'helper_path_exists':find_path(g.world,g.player.position,goal,g.world.probe_size,None) is not None,'method':'Unmodified production Game.update after the existing helper walks to adjacent even-grid point; no teleport or gameplay patch.'}
 f.walk((goal[0]+1,goal[1]+1))
 for _ in range(120):
  delta=pygame.Vector2(goal)-g.player.position
  if delta.length()<.04:break
  f.tick(min(.01,delta.length()/72),delta)
 assert g.player.position.distance_to(goal)<.04
 report['actual_position']=list(g.player.position)
 f.event('prepare');f.read();f.until(lambda:f.c.prepared)
 report['actual_prepare_completed']=f.c.prepared
 print(json.dumps(report,indent=2))
finally:
 f.g.music.stop();f.tearDown();f.doCleanups()
