"""Capture current world, workshop and cinematic equipment in an isolated renderer."""
from pathlib import Path
import os,sys,json,hashlib
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy');os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import pygame
from PIL import Image
from main import Game
from ice_reaper_action import IceReaperActionStage
OUT=ROOT/'docs/reviews/mira_rig_continuity'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    pygame.init();pygame.display.set_mode((960,640))
    game=Game(window_size=(960,640),fullscreen=False,start_on_title=False,_preview_window=pygame.Surface((960,640)))
    before=game._progress_signature();mira=game.world.npcs[0]
    evidence={'scope':'Isolated rendered world/workshop and seekable production cinematic art. No played victory or quest completion is claimed.','captures':[]}
    try:
        frames=[]
        camera=(528,240)
        for time in (0,1000,2000,2400,3600,5000,6500,7600):
            game.world.draw(game.canvas,camera,game.player,time,include_ui=False)
            image=pygame.transform.scale(game.canvas,(960,640))
            name=f'workshop_{time:04}.png';pygame.image.save(image,str(OUT/name));frames.append(Image.frombytes('RGB',(960,640),pygame.image.tobytes(image,'RGB')))
            evidence['captures'].append({'file':name,'scene':'eldenmere','clock_ms':time})
        frames[0].save(OUT/'workshop.gif',save_all=True,append_images=frames[1:],duration=350,loop=0)
        Image.open(ROOT/'assets/characters/mira/walk_directions_review.png').save(OUT/'directions.png')
        stage=IceReaperActionStage(ROOT/'assets/story/ice_reaper_rescue',strict=True)
        cine=[]
        cinematic_canvas=pygame.Surface((480,320))
        for time in (9.3,10.8,11.8,12.5,13.3,14.35,17.0):
            stage.draw(cinematic_canvas,time,reduced_motion=False)
            image=pygame.transform.scale(cinematic_canvas,(960,640));name=f'cinematic_{round(time*100):04}.png'
            pygame.image.save(image,str(OUT/name));cine.append(Image.frombytes('RGB',(960,640),pygame.image.tobytes(image,'RGB')))
            evidence['captures'].append({'file':name,'scene':'Ice Reaper study','seconds':time})
        cine[0].save(OUT/'cinematic.gif',save_all=True,append_images=cine[1:],duration=500,loop=0)
        assert before==game._progress_signature();assert not game.save_store.enabled
        evidence['progress_unchanged']=True
        evidence['fingerprints']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('battle_model.py','mill_quest.py','world_encounters.py','ice_reaper_action.py','assets/source/characters/mira/arm_rig/registration.json')}
        (OUT/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
        print('Captured',len(evidence['captures']),'production-rendered continuity stills')
    finally:game.music.stop();game.opening_audio.reset();pygame.quit()
if __name__=='__main__':main()
