"""Capture the real block-play controller, with decisions selected for review."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from pathlib import Path
import random
import sys
import gc

import pygame
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import main
from capture_liam_house import card
from collections import Counter
from build_liam_family_front_walks import write

OUT=ROOT/'docs/reviews/liam_blocks'
BOX=(24,153,216,310)


def save_gif(path,frames,duration):
    """Exact adaptive palettes remapped in C to one shared lossless palette."""
    colors=Counter()
    for frame in frames:colors.update({color:count for count,color in frame.getcolors(frame.width*frame.height)})
    assert len(colors)<=256,(path,len(colors))
    indices={color:index for index,color in enumerate(colors)}
    palette=[v for color in colors for v in color];palette += [0]*(768-len(palette))
    indexed=[]
    for frame in frames:
        local=frame.convert('P',palette=Image.Palette.ADAPTIVE,colors=256)
        rgb=local.getpalette()
        lut=[indices.get(tuple(rgb[i*3:i*3+3]),0) for i in range(256)]
        shared=local.point(lut);shared.putpalette(palette)
        assert ImageChops.difference(frame,shared.convert('RGB')).getbbox() is None
        indexed.append(shared)
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=duration,loop=0,disposal=1,optimize=False)


def shot(game,r,title,wide=False):
    camera=main.camera_for((216,168),r.home.size)
    r.home.draw(game.canvas,camera,game.player,game.elapsed_ms)
    image=Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB'))
    if wide:return card(image,title,'Box between the beds | actual in-game room renderer',2)
    x,y,right,bottom=getattr(r,'review_box',BOX)
    image=image.crop((x-camera[0],y-camera[1],right-camera[0],bottom-camera[1]))
    count=sum(b['state']=='box' for b in r.blocks)
    subtitle=f'{r.state.replace("_"," ")} | {count}/5 blocks in box | Actual game speed'
    return card(image,title,subtitle,4)


def capture(name,accident,forget):
    game=main.Game(fullscreen=False,start_on_title=False);r=game.block_routines[0]
    game.world=r.home;game.player.position.update(230,300)
    r.shared.cooldown_ms=999999;r._rng=random.Random(14)
    r.daisy._rng=random.Random(4)
    r.begin(accident=accident,forget=forget)
    if accident:r.review_box=(24,120,216,310)
    frames=[];seen=[];guide_requested=False;guide_set=False;detail=[];snapshots=set();finish_frames=0
    title={'normal_cleanup':'Liam / building and putting all five blocks away',
           'forgotten_block':'Liam / tidying up, with one forgotten block',
           'daisy_accident':'Liam and Daisy / an accidental tumble'}[name]
    for tick in range(2400):
        state=r.state
        if not seen or seen[-1]!=state:seen.append(state)
        placed=sum(b['state']=='placed' for b in r.blocks)
        # Select a nearby normal wandering route so the conditional accident can
        # be reviewed. Daisy walks there from her rug; never reposition her.
        if accident and placed>=3 and not guide_requested and not r.daisy.play_owned:
            r.daisy.begin_activity('wander',r.home);guide_requested=True
        if guide_requested and not guide_set and not r.daisy.play_owned and r.daisy.state=='walk':
            r.daisy._walk_to((126,180),'wander');guide_set=True
        frame=shot(game,r,title);frames.append(frame)
        if tick==0:shot(game,r,'Block box / cottage placement',True).save(OUT/'room_overview.png')
        if state=='admire' and state not in snapshots:
            frame.save(OUT/f'{name}_building.png');snapshots.add(state)
        if state in ('daisy_approach','bump','react') or (r.dog_returning and state!='cooldown'):
            detail.append(frame)
        if state=='bump' and getattr(r,'fall_phase',-1)==0 and 'contact' not in snapshots:
            frame.save(OUT/'daisy_contact.png');snapshots.add('contact')
        if state=='bump' and getattr(r,'fall_phase',-1)==2 and 'fall' not in snapshots:
            frame.save(OUT/'daisy_fall.png');snapshots.add('fall')
        if state=='react' and r.state_ms>=700 and state not in snapshots:
            frame.save(OUT/'daisy_reaction.png');snapshots.add(state)
        if r.completed_cycles:
            finish_frames+=1
            if finish_frames==1:frame.save(OUT/f'{name}_finished.png')
            if finish_frames>=20:break
        game.update(.1,(0,0),False)
    else:
        raise RuntimeError((name,r.state,tuple(r.liam.position),tuple(r.daisy.position),r.events))
    if accident:
        assert r.accident_selected and any(e.get('knockdown') for e in r.events)
        assert r.daisy.state=='rest'
    count=sum(b['state']=='box' for b in r.blocks)
    assert count==(4 if forget else 5),(name,count)
    report={'accident':r.accident_selected,'forgotten_id':r.forgotten_id,'box_count':count,
            'elapsed_ms':round(game.elapsed_ms),'frames':len(frames),'frame_duration_ms':100,
            'states_seen':seen,'events':list(r.events),'final_blocks':[
                {'id':b['id'],'state':b['state'],'center':list(b['center'])} for b in r.blocks],
            'liam_position':list(r.liam.position),'daisy_position':list(r.daisy.position),
            'daisy_state':r.daisy.state,'nearby_walk_guided':guide_set}
    save_gif(OUT/f'{name}.gif',frames,100)
    if detail:save_gif(OUT/'daisy_accident_detail.gif',detail,100)
    print(f'Captured {name}: {len(frames)} frames, {count}/5 blocks in box.',flush=True)
    pygame.quit();del frames,detail,game,r;gc.collect();return report


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    captures={}
    for name,accident,forget in [('normal_cleanup',False,False),('forgotten_block',False,True),('daisy_accident',True,False)]:
        captures[name]=capture(name,accident,forget)
    write(OUT/'captures.json',{'status':'review','initial_wait_skipped':True,'review_decisions_selected':True,
          'actual_speed':True,'captures':captures})


if __name__=='__main__':run()
