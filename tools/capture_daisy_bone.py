"""Capture one persistent bone through the actual game renderer and routines."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from pathlib import Path
import sys
import random
import gc

import pygame
from PIL import Image,ImageDraw,ImageSequence
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import main
from capture_liam_house import card
from capture_liam_blocks import save_gif
from build_liam_family_front_walks import write,font

OUT=ROOT/'docs/reviews/daisy_bone'
BOX=(64,196,276,314)


def setup():
    game=main.Game(fullscreen=False,start_on_title=False);r=game.bone_routines[0]
    game.world=r.home;game.player.position.update(380,300)
    r.shared.cooldown_ms=999999
    for routine in game.block_routines:routine.cooldown_ms=999999
    r.daisy.cooldowns={'food':999999,'water':999999};r.cooldown_ms=999999
    r._rng=random.Random(4);r.daisy._rng=random.Random(5)
    return game,r


def render(game,r,box=None):
    camera=main.camera_for((216,168),r.home.size)
    r.home.draw(game.canvas,camera,game.player,game.elapsed_ms)
    im=Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB'))
    if box:
        x,y,right,bottom=box
        im=im.crop((x-camera[0],y-camera[1],right-camera[0],bottom-camera[1]))
    return im


def shot(game,r,title):
    subtitle=f'{r.state.replace("_"," ")} | Bone: {r.bone["state"]} | Actual game speed'
    return card(render(game,r,BOX),title,subtitle,4)


def session(game,r,kind,playful,title,carry,drop_point=None):
    assert r.begin(kind,playful=playful,drop_point=drop_point),(kind,r.state,r.daisy.state,r.daisy.play_owned)
    start_cycles=r.completed_cycles;start_elapsed=game.elapsed_ms;start_events=len(r.events)
    frames=[];states=[];snapshots=set();finish=0
    for tick in range(1800):
        if not states or states[-1]!=r.state:states.append(r.state)
        frame=shot(game,r,title);frames.append(frame)
        if r.current_action=='pickup_left' and r.bone['state']=='mouth' and 'pickup' not in snapshots:
            frame.save(OUT/'pickup_contact.png');snapshots.add('pickup')
        if r.state=='chew' and r.state_ms>=500 and 'chew' not in snapshots:
            frame.save(OUT/'rug_chewing.png');snapshots.add('chew')
        if r.state=='drop' and r.bone['state']=='ground' and 'drop' not in snapshots:
            frame.save(OUT/'drop_contact.png');snapshots.add('drop')
        if r.bone['state']=='mouth' and r.current_action is None and r.shared.dog_pose.moving:
            direction=r.shared.dog_pose.facing
            if direction not in carry:
                sprite=r.sprite()
                native=Image.frombytes('RGBA',sprite.get_size(),pygame.image.tobytes(sprite,'RGBA'))
                clean=Image.new('RGBA',native.size,'#d0d8c4');clean.alpha_composite(native)
                carry[direction]=clean.convert('RGB')
        if r.completed_cycles>start_cycles:
            finish+=1
            if finish==1:
                frame.save(OUT/('rug_finished.png' if kind=='rug' else 'bone_left_elsewhere.png'))
            if finish>=15:break
        game.update(.1,(0,0),False)
    else:raise RuntimeError((kind,r.state,r.bone,tuple(r.daisy.position)))
    assert r.bone['state']=='ground'
    report={'kind':kind,'playful':playful,'frames':len(frames),'frame_duration_ms':100,
            'elapsed_ms':round(game.elapsed_ms-start_elapsed),'states_seen':states,
            'bone_id':r.bone['id'],'final_bone_state':r.bone['state'],
            'final_bone_position':list(r.bone['position']),'daisy_position':list(r.daisy.position),
            'events':list(r.events)[start_events:]}
    return frames,report


def carry_sheet(carry):
    order=('front','left','right','back');scale=6;width=64*scale+32;height=48*scale+48
    out=Image.new('RGB',(width*2,height*2+88),'#e8edf2');d=ImageDraw.Draw(out);d.fontmode='1'
    d.text((20,12),'Daisy / carrying one bone in four directions',font=font(24),fill='#26343e')
    d.text((20,48),'Actual runtime frames | back-facing bone is hidden by her head',font=font(16),fill='#52616c')
    for i,name in enumerate(order):
        assert name in carry,('Missing carried facing',name)
        x=(i%2)*width+16;y=(i//2)*height+88
        im=carry[name].resize((64*scale,48*scale),Image.Resampling.NEAREST)
        out.paste(im,(x,y));d.text((x,y+48*scale+8),name.title(),font=font(20),fill='#26343e')
    out.save(OUT/'carrying_directions.png')


def verify_gif(path):
    with Image.open(path) as im:
        assert im.info['loop']==0
        durations=[f.info['duration'] for f in ImageSequence.Iterator(im)]
        return {'bytes':path.stat().st_size,'frames':len(durations),'duration_ms':sum(durations)}


def capture():
    OUT.mkdir(parents=True,exist_ok=True)
    game,r=setup();carry={};bone_identity=id(r.bone)
    card(render(game,r),'Daisy / her play bone beside the rug','One nonblocking bone | actual game room',2).save(OUT/'room_overview.png')
    rug,report=session(game,r,'rug',True,'Daisy / bringing her bone to the rug',carry)
    save_gif(OUT/'rug_play.gif',rug,100);del rug;gc.collect()
    print('Captured full rug play and chewing.',flush=True)
    relocate,relocate_report=session(game,r,'relocate',False,'Daisy / carrying her bone somewhere else',carry,(214,239))
    dropped_position=r.bone['position'].copy()
    assert dropped_position.distance_to((214,239))<1
    retrieval,retrieval_report=session(game,r,'rug',False,'Daisy / finding the same bone again',carry)
    assert id(r.bone)==bone_identity
    save_gif(OUT/'drop_and_retrieve.gif',relocate+retrieval,100)
    del relocate,retrieval;gc.collect()
    carry_sheet(carry)
    captures={'status':'review','actual_speed':True,'initial_wait_and_repeat_cooldown_skipped':True,
              'one_bone_identity_throughout':True,'rug_play':report,'relocation':relocate_report,
              'retrieval':retrieval_report,'previews':{name:verify_gif(OUT/name) for name in ('rug_play.gif','drop_and_retrieve.gif')}}
    write(OUT/'captures.json',captures)
    pygame.quit();print('Captured persistent drop/retrieval and all four carried directions.',flush=True)


if __name__=='__main__':capture()
