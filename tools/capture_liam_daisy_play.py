"""Capture the production controller and renderer, skipping only its initial delay."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from pathlib import Path
import sys
import random
import pygame
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import main
from capture_liam_house import card
from capture_daisy_routines import save_gif
from build_liam_family_front_walks import write

OUT=ROOT/'docs/reviews/liam_daisy_play'


def shot(game,r,scene=None,box=None,title='Liam and Daisy / playtime',subtitle=None,scale=2):
    scene=scene or (r.town if r.state in ('line_up','chase','return_liam') else r.home)
    center=(292,540) if scene is r.town else (216,168)
    camera=main.camera_for(center,scene.size)
    scene.draw(game.canvas,camera,game.player,game.elapsed_ms)
    im=Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB'))
    if box:
        x,y,bottomx,bottomy=box
        im=im.crop((x-camera[0],y-camera[1],bottomx-camera[0],bottomy-camera[1]))
    water=r.daisy.bowls['water']['state'].replace('_','-')
    sub=subtitle or f'{r.state.replace("_"," ")} | Water: {water} | Actual game speed'
    return card(im,title,sub,scale)


def capture(drink,name,full=False):
    game=main.Game(fullscreen=False,start_on_title=False);r=game.play_routines[0]
    game.player.position.update(430,600);r._rng=random.Random(1 if drink else 0);r.begin()
    frames=[];invitation=[];chase=[];ending=[];seen=[];report={};nap_ticks=0
    for tick in range(1400):
        if not seen or seen[-1]!=r.state:seen.append(r.state)
        if full:frames.append(shot(game,r))
        if full and r.state in ('stand_daisy','invite','hop','wag'):
            invitation.append(shot(game,r,r.home,(50,208,220,300),'Liam invites Daisy to play','Four-pose hops and wag | Actual game speed',5))
        if full and r.state=='chase':
            chase.append(shot(game,r,r.town,(208,500,392,638),'Liam and Daisy / three laps','Approved four-frame runs | Actual game speed',5))
        if r.state in ('daisy_return','nap'):
            ending.append(shot(game,r,r.home,(36,204,230,308),f'Return home / {"drink first" if drink else "straight to the rug"}',f'Water: {r.daisy.bowls["water"]["state"].replace("_","-")} | Actual game speed',5))
        if r.state=='nap':
            nap_ticks+=1
            if nap_ticks==1:
                shot(game,r,r.home,(36,204,230,308),'Liam and Daisy / resting','Head on the pillow, quilt over body; Daisy on her rug',5).save(OUT/f'{name}_rest.png')
            if nap_ticks>=15:break
        game.update(.1,(0,0),False)
    else:raise RuntimeError((name,r.state,tuple(r.liam.position),tuple(r.daisy.position)))
    if full:
        for filename,clip in (('full_cycle',frames),('invitation',invitation),('chase',chase)):
            save_gif(OUT/f'{filename}.gif',clip,100);print(filename,len(clip),flush=True)
    save_gif(OUT/f'{name}.gif',ending,100)
    report={'outcome':r.drink_choice,'states_seen':seen,'elapsed_ms':round(game.elapsed_ms),
            'water_state':r.daisy.bowls['water']['state'],'liam_position':list(r.liam.position),
            'daisy_position':list(r.daisy.position),'events':list(r.events)}
    pygame.quit();return report


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    report={'status':'review','initial_wait_skipped_only':True,'captures':{}}
    report['captures']['drink_first']=capture(True,'drink_first',True)
    report['captures']['skip_drink']=capture(False,'skip_drink')
    write(OUT/'captures.json',report)
    print('Captured full cycle, invitation, chase, and both return-home outcomes.',flush=True)


if __name__=='__main__':run()
