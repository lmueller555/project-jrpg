"""Capture actual Daisy simulation; only skip the initial long rug wait."""
import os
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy';os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
from pathlib import Path
from collections import Counter
import sys
import random

import pygame
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import main
from capture_liam_house import card
from build_liam_family_front_walks import write

OUT=ROOT/'docs/reviews/daisy_house_routines'


def save_gif(path,frames,duration):
    """Lossless shared palette with opaque delta frames for faster review loading."""
    colors=Counter()
    for frame in frames:colors.update({color:count for count,color in frame.getcolors(frame.width*frame.height)})
    assert len(colors)<=256,(path,len(colors))
    palette=Image.new('P',(1,1));rgb=[v for color in colors for v in color]
    palette.putpalette(rgb+[0]*(768-len(rgb)))
    indices={color:index for index,color in enumerate(colors)}
    indexed=[]
    for frame in frames:
        image=Image.frombytes('P',frame.size,bytes(indices[color] for color in frame.getdata()))
        image.putpalette(palette.getpalette());indexed.append(image)
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=duration,loop=0,disposal=1,optimize=False)


def setup(seed=4):
    game=main.Game(fullscreen=False,start_on_title=False)
    game.world=game._scene_by_id('liam_house');game.player.position.update(230,300)
    a=next(n for n in game.world.npcs if n.data['id']=='daisy');a._rng=random.Random(seed)
    return game,a


def shot(game,title,a,wide=False,slow=False):
    camera=main.camera_for(game.player.position,game.world.size)
    game.world.draw(game.canvas,camera,game.player,game.elapsed_ms)
    image=Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB'))
    food=a.bowls['food']['state'].replace('_','-');water=a.bowls['water']['state'].replace('_','-')
    if wide:
        return card(image,title,'Real in-game walk speed | initial rug wait skipped for review',2)
    box=(128,252,224,292) if slow else (76,240,224,312)
    x,y,r,b=box;image=image.crop((x-camera[0],y-camera[1],r-camera[0],b-camera[1]))
    sub=(f'Four-pose slow detail | Food: {food}; water: {water}' if slow else
         f'Food: {food}; water: {water} | GIF replay resets preview only')
    return card(image,title,sub,8 if slow else 6)


def capture_visit(kind,name,empty=False):
    game,a=setup();frames=[];seen=[]
    if empty:game.world.set_entity_state(a.bowls[kind]['id'],'empty')
    a.begin_activity(kind,game.world)
    title={'food':'Daisy / eating','water':'Daisy / drinking','wander':'Daisy / wandering and returning to her rug'}[kind]
    if empty:title='Daisy / inspecting an empty bowl'
    for tick in range(1200):
        frames.append(shot(game,title,a,kind=='wander'))
        if not seen or seen[-1]!=a.state:seen.append(a.state)
        game.update(.1,(0,0),False)
        if a.state=='rest':
            for _ in range(8):
                frames.append(shot(game,title,a,kind=='wander'));game.update(.1,(0,0),False)
            break
    else:raise RuntimeError((kind,a.state,tuple(a.position)))
    save_gif(OUT/f'{name}.gif',frames,100)
    frames[len(frames)//2].save(OUT/f'{name}.png')
    report={'frames':len(frames),'frame_duration_ms':100,'states_seen':seen,
            'final_bowls':{k:v['state'] for k,v in a.bowls.items()},'final_position':list(a.position)}
    pygame.quit();return report


def capture_slow(kind,name):
    game,a=setup();a.begin_activity(kind,game.world)
    action='eat' if kind=='food' else 'drink'
    for _ in range(3000):
        game.update(1/60,(0,0),False)
        if a.state==action:break
    frames=[]
    for index in range(4):
        while a.frame_index!=index:game.update(1/60,(0,0),False)
        frames.append(shot(game,f'Daisy / {"eating" if kind=="food" else "drinking"} — slow detail',a,slow=True))
    save_gif(OUT/f'{name}_slow.gif',frames,540 if kind=='food' else 300)
    pygame.quit()


def capture():
    OUT.mkdir(parents=True,exist_ok=True)
    reports={}
    for kind,name in (('wander','wandering'),('food','eating'),('water','drinking')):
        reports[name]=capture_visit(kind,name)
    reports['empty_bowl']=capture_visit('food','empty_bowl',True)
    capture_slow('food','eating');capture_slow('water','drinking')
    write(OUT/'captures.json',{'status':'review','initial_wait_skipped_only':True,'reports':reports})
    print('Captured complete wandering, eating, drinking, empty-bowl visits and four-pose slow details.')


if __name__=='__main__':capture()
