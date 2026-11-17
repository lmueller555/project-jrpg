"""Live renderer and actual cardinal door transfers, from a disclosed hall fixture."""
import os,json,sys,tempfile
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from main import Game
from tools.capture_sanctuary_reserve import path,walk

def capture(folder):
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory() as temp:
  g=Game(fullscreen=False,window_size=(960,640),start_on_title=True,save_path=Path(temp)/'save.json',settings_path=Path(temp)/'settings.json')
  try:
   g.on_title=False;g.opening.stage='disabled';g.opening_fade=g.transfer_cooldown=0;g.audio.set_music(0);g.audio.set_effects(0)
   g.world=g._scene_by_id('elden_vale_sanctuary_hall');g.player.position.update(288,310)
   results=[]
   def shot(name):
    g.camera.reset();g.location_seconds=g.saves.notice_seconds=0;g.draw();pygame.image.save(g.window,str(folder/(name+'.png')))
   for identifier in ('relief_room','hall','reserve_exit','sanctuary_hall'):
    origin=g.world;door=next(d for d in origin.doors if d.data['id']==identifier);x,y=door.data['anchor'];direction=-1 if door.data['entry_side']=='north' else 1
    walk(g,path(g.world,g.player.position,(x,y-direction*24)),g.world.data['id'])
    shot(identifier+'_approach')
    for _ in range(100):
     g.update(.04,(0,direction),False)
     if g.world is not origin:break
    assert g.world is not origin,identifier
    results.append({'door':identifier,'from':origin.data['id'],'to':g.world.data['id'],'position':list(g.player.position)})
    for _ in range(40):g.update(.04,(0,0),False)
    shot(identifier+'_arrival')
   g.audio.set_reduced_motion(True);g.update(.1,(0,0),False);shot('reduced_motion_hall')
   (folder/'movement.json').write_text(json.dumps({'fixture':'Start in hall; each transfer uses Game.update cardinal walking, no direct enter calls.','transfers':results},indent=2)+'\n')
  finally:g.music.stop();pygame.quit()
if __name__=='__main__':capture(sys.argv[1])
