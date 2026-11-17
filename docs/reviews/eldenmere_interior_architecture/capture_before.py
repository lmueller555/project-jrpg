"""Unmodified production Game window captures on the frozen main baseline.
Same disclosed room-arrival fixtures, facing, 400 ms clock, window and camera reset
as capture_eldenmere_interior_architecture. No changes to maps or runtime.
"""
from pathlib import Path
from hashlib import sha256
import json,os,sys,tempfile,subprocess
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root));import pygame
from main import Game
rooms=('sanctuary_hall','sanctuary_bedroom','sanctuary_dining','mira','mill','school','halden','elira','venn','home_a','home_b','home_c','liam_house','inn','item_shop')
report={'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'method':__doc__,'views':{}}
with tempfile.TemporaryDirectory() as tmp:
 g=Game(fullscreen=False,window_size=(960,640),start_on_title=True,save_path=Path(tmp)/'journey.json',settings_path=Path(tmp)/'settings.json')
 try:
  g.on_title=False;g.opening.restore({'version':1,'stage':'disabled'});g.opening_fade=g.transfer_cooldown=0;g.audio.set_music(0);g.audio.set_effects(0)
  for name in rooms:
   g.world=g._scene_by_id(name);point=g.world.data['spawn'];assert g.world.can_stand(point)
   g.player.position.update(point);g.player.facing='back';g.elapsed_ms=400;g.camera.reset()
   for reduced in (False,True):
    g.audio.set_reduced_motion(reduced);g.world.update_grass(0,reduced_motion=reduced);g.location_seconds=0;g.draw()
    path=out/('room_'+name+('_reduced' if reduced else '_normal')+'.png');pygame.image.save(g.window,path)
    report['views'][path.stem]={'scene':name,'position':list(point),'facing':g.player.facing,'reduced_motion':reduced,'clock_ms':400,'sha256':sha256(path.read_bytes()).hexdigest()}
 finally:g.music.stop();pygame.quit()
(out/'before_metadata.json').write_text(json.dumps(report,indent=2)+'\n')
print(len(report['views']),'baseline native room views')
