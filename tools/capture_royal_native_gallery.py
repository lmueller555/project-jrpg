"""Actual production Gallery/input capture of the Page's Sanctuary actions."""
import os,sys,tempfile,json
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image
from main import Game
OUT=ROOT/'docs/reviews/named_hd/regent_clerk/production/sanctuary_page';OUT.mkdir(parents=True,exist_ok=True)
report={'source':'production Game.draw via actual Gallery scene/input','fixture':'isolated Gallery prerequisites; no user save','views':[]}
with tempfile.TemporaryDirectory() as tmp:
 parent=Game(fullscreen=False,start_on_title=True,save_path=Path(tmp)/'journey.json',settings_path=Path(tmp)/'settings.json');parent.audio.set_music(0);parent.audio.set_effects(0)
 assert parent.open_gallery();assert parent.launch_gallery_scene('sanctuary_arrival'),parent.gallery.error
 game=parent.gallery_session.game;owner=game.sanctuary_arrival;seen=set();movies={}
 def press():parent.handle_events([pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE,repeat=False),pygame.event.Event(pygame.KEYUP,key=pygame.K_SPACE)])
 for tick in range(12000):
  if parent.gallery_session is None:break
  page=owner.actors.get('page');pose=page.pose if page else None
  if pose in ['read','read_attention','read_resume']:
   im=page.sprite(game.elapsed_ms);assert im.native.get_size()==(48,72)
   if pose not in seen and (pose=='read' or page.pose_ms>=200):
    seen.add(pose);game.draw();name=pose+'.png';pygame.image.save(game.window,str(OUT/name));report['views'].append({'file':name,'beat':owner.beat,'pose_ms':page.pose_ms,'position':list(page.position)})
   if len(movies.get(pose,[]))<18:
    game.draw();movies.setdefault(pose,[]).append(Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB')))
  if all(k in seen for k in ['read','read_attention','read_resume']) and owner.beat>=6:break
  if owner.dialogue is not None and tick%12==0:press()
  parent.update(.05)
 else:raise AssertionError(('Incomplete lifecycle',owner.beat,seen))
 assert all(k in seen for k in ['read','read_attention','read_resume']),seen
 for pose,frames in movies.items():frames[0].save(OUT/(pose+'.gif'),save_all=True,append_images=frames[1:],duration=50,loop=0)
 before=owner.actors['page'].pose_ms
 parent.handle_events([pygame.event.Event(pygame.KEYDOWN,key=pygame.K_p,repeat=False),pygame.event.Event(pygame.KEYUP,key=pygame.K_p)])
 parent.update(1.0);report['pause_freezes_page_pose']=owner.actors['page'].pose_ms==before
 report['read_handoff_observed']=True;report['final_beat']=owner.beat
 (OUT/'verification.json').write_text(json.dumps(report,indent=2))
 parent.gallery_session.close()
pygame.quit();print(report)
