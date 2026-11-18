"""Production visitor movement, seating and emergency cue frames via ordinary play."""
import os,sys,tempfile,json
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image
from main import camera_for
from tools.capture_mq03_emergency import Driver
from tools.capture_overworld_sanctuary import frame
OUT=ROOT/'docs/reviews/royal_native_scene/visitor_motion';OUT.mkdir(parents=True,exist_ok=True);movies={};records=[];saved=set();budget={}
with tempfile.TemporaryDirectory() as tmp:
 d=Driver(tmp)
 def observe(seconds):
  g=d.game;q=d.quest;cam=camera_for(g.player.position,g.world.size)
  actors=[('regent_clerk',q.clerk),('regent_driver',q.driver),('regent_survivor',q.survivor)]
  for key,a in actors:
   if a is None or not a.story_visible or a.scene_id!=g.world.data['id']:continue
   x,y=a.position.x-cam[0],a.position.y-cam[1]
   if not (20<x<460 and 35<y<300):continue
   if a.moving and len(movies.get(key,[]))<24:
    budget[key]=budget.get(key,0)+seconds
    if budget[key]<.05:continue
    budget[key]-=.05;im=a.sprite(g.elapsed_ms);assert im.native.get_size()==(48,72)
    movies.setdefault(key,[]).append(frame(g));records.append({'actor':key,'scene':g.world.data['id'],'position':list(a.position),'phase_ms':a.walk_ms,'source':'production Game.draw'})
  action=q.scene_actions
  if action.active_cue=='survivor_alarm' and action.clock>.2 and 'alarm' not in saved:
   a=q.survivor
   if getattr(a,'story_sprite',None) is not None:
    assert a.story_sprite.native.get_size()==(48,72);frame(g).save(OUT/'survivor_alarm.png');saved.add('alarm')
 def page(identifier,line,current):
  for _ in range(10):d.tick(.05)
 d.observer=observe;d.meal(page);d.attack_report(page);d.interact('attack_report',page);d.departure(page)
 for key,frames in movies.items():
  frames[0].save(OUT/(key+'_motion.gif'),save_all=True,append_images=frames[1:],duration=50,loop=0);frames[len(frames)//2].save(OUT/(key+'_motion.png'))
 report={'fixture':'completed MQ01/MQ02 only; MQ03 ordinary dialogue and travel','actor_frames':{k:len(v) for k,v in movies.items()},'alarm_captured':'alarm' in saved,'records':records}
 (OUT/'verification.json').write_text(json.dumps(report,indent=2));print(report['actor_frames'],report['alarm_captured'])
pygame.quit()
