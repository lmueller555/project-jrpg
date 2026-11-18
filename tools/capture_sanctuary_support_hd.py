"""Capture actual mixed native cast, release boundary and pause in Sanctuary arrival.
Uses disposable saves. Optional SANCTUARY_REFERENCE_ROOT for sparse packages.
"""
import os,sys,tempfile,json
from pathlib import Path
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
NEW=Path(__file__).resolve().parents[1]
# Sparse authoring packages can point at an existing full checkout; merged tree defaults to itself.
BASE=Path(os.environ.get('SANCTUARY_REFERENCE_ROOT',str(NEW)))
sys.path.insert(0,str(BASE))
# Load only modified actor/controller module from sparse package.
import importlib.util
spec=importlib.util.spec_from_file_location('sanctuary_arrival',NEW/'sanctuary_arrival.py')
module=importlib.util.module_from_spec(spec);sys.modules['sanctuary_arrival']=module;spec.loader.exec_module(module)
module.ROOT=BASE
import pygame
import sanctuary_arrival
# Overlay only the changed actor record, with absolute file paths; scene code,
# map, collision, timing and world draw all remain the real production runtime.
from main import Game
from cutscene_gallery import _regent_checkpoint,_station
from rendering import WorldCanvas
art=json.loads((NEW/'assets/story/sanctuary_arrival/art.json').read_text())['actors']
def paths(x):
 if isinstance(x,dict):return {k:paths(v) for k,v in x.items()}
 if isinstance(x,list):return [paths(v) for v in x]
 if isinstance(x,str) and x.startswith('assets/'):return str(NEW/x)
 return x
with tempfile.TemporaryDirectory() as tmp:
 g=Game(fullscreen=False,start_on_title=False,save_path=Path(tmp)/'save.json',settings_path=Path(tmp)/'settings.json')
 _regent_checkpoint(g,'sanctuary_arrival_pending');g._sync_story_party();_station(g,g._scene_by_id('elden_vale_sanctuary'),(444,642),'back')
 g.sanctuary_arrival.art['actors']=paths(art)
 g.sanctuary_arrival.start(force=True)
 a=g.sanctuary_arrival.actors['runner'];seen=set();out=NEW/'docs/reviews/sanctuary_support_hd';observations=[]
 for step in range(4500):
  if g.sanctuary_arrival.dialogue is not None:
   g.handle_events([pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE,repeat=False),pygame.event.Event(pygame.KEYUP,key=pygame.K_SPACE)])
  g.update(.1,(0,0),False)
  care=g.sanctuary_arrival.care
  tag=None
  if a.carrying and a.moving and 'carry' not in seen:tag='carry'
  if a.pose=='runner_place' and 590<=a.pose_ms<700 and 'before' not in seen:tag='before'
  if a.pose=='runner_place' and 700<=a.pose_ms<800 and 'after' not in seen:tag='after'
  if care.runner_delivered and 'delivered' not in seen:tag='delivered'
  if tag:
   seen.add(tag);c=WorldCanvas((480,320));g.world.draw(c,(760-240,340-160),g.player,0,include_ui=False,party_actors=tuple(g.sanctuary_arrival.actors.values()));pygame.image.save(c.native,str(out/f'arrival_mixed_{tag}.png'))
   observations.append({'state':tag,'step':step,'position':list(a.position),'pose_ms':a.pose_ms,'carrying':a.carrying,'placed':care.runner_linen_placed,'delivered':care.runner_delivered})
   if tag=='before':
    clock=care.runner_elapsed_ms;g.sanctuary_arrival.paused=True;g.update(1.,(0,0),False);assert care.runner_elapsed_ms==clock;g.sanctuary_arrival.paused=False
  if g.sanctuary_arrival.completed:break
 else:raise AssertionError('arrival did not complete')
 assert seen=={'carry','before','after','delivered'},seen
 assert observations[1]['carrying'] and not observations[1]['placed']
 assert not observations[2]['carrying'] and observations[2]['placed']
 print('completed mixed arrival',step,seen)
 (out/'arrival_mixed_observations.json').write_text(json.dumps({'completed':True,'steps':step,'pause_frozen':True,'observations':observations},indent=2)+'\n')
 pygame.quit()
