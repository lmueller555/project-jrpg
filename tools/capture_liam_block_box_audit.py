"""Capture live native Game frames for the scoped block-box correction.

The long initial cooldown is skipped and the two random decisions are selected.
No actor is posed or teleported once the routine starts. Native pixels are
preserved; contact strips crop the production view without enlarging it.
"""
import os
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
import argparse
import gc
import hashlib
import json
from pathlib import Path
import random
import sys

from PIL import Image, ImageDraw
import pygame
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import main

OUT=ROOT/'docs/reviews/liam_block_box_audit'
CROP=(72,310,300,510)
KEYS=('kneel_box_3','take_0','take_1','take_2','take_3',
      'rise_with_block_0','rise_with_block_3','return_block_0','return_block_1',
      'return_block_2','return_block_3','rise_return_0')


def capture(out=OUT):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    game=main.Game(fullscreen=False,start_on_title=False,save_path=None)
    r=game.block_routines[0];game.world=r.home;game.player.position.update(230,300)
    r.shared.cooldown_ms=999999;r.daisy.duration_ms=999999
    r.daisy.cooldowns={'food':999999,'water':999999};r._rng=random.Random(14)
    r.begin(accident=False,forget=False)
    shots={};records=[];clips={'take':[],'return_block':[]};clip_ids={};carry={};counts={}
    for tick in range(5000):
        index=r._frame()[0] if r.liam.action in r.meta['actions'] else -1
        key=f'{r.state}_{index}'
        count=sum(b['state']=='box' for b in r.blocks)
        need=(key in KEYS and key not in shots) or count not in counts
        carrying=r.held is not None and r.liam.moving and r.liam.action is None
        need|=carrying and r.liam.facing not in carry
        clip=r.state in clips and tick%3==0
        if clip:clip_ids.setdefault(r.state,r.current['id'])
        clip=clip and clip_ids[r.state]==r.current['id']
        if need or clip:
            game.draw()
            im=Image.frombytes('RGB',game.canvas.native.get_size(),pygame.image.tobytes(game.canvas.native,'RGB'))
            if key in KEYS and key not in shots:
                shots[key]=im
                records.append({'key':key,'liam':list(r.liam.position),'facing':r.liam.facing,
                    'action':r.liam.action,'box_state':r.box['state'],
                    'held':r.held['id'] if r.held else None,'blocks':[b['state'] for b in r.blocks]})
            counts.setdefault(count,im.crop(CROP))
            if carrying:carry.setdefault(r.liam.facing,im.crop(CROP))
            if clip:clips[r.state].append(im.crop(CROP))
        if r.completed_cycles:break
        game.update(1/30,(0,0),False)
    else:raise RuntimeError(r.state)
    sheet=Image.new('RGB',(1280,660),'#1b2027');d=ImageDraw.Draw(sheet)
    for i,key in enumerate(KEYS):
        x=i%4*320;y=i//4*220;sheet.paste(shots[key].crop(CROP),(x+46,y+20));d.text((x+8,y+5),key,fill='white')
    sheet.save(out/'after_contacts.png')
    for key in ('take_2','return_block_2'):
        shots[key].save(out/('after_'+key+'.png'))
    for name,frames in clips.items():
        frames[0].save(out/(name+'_native.png'),save_all=True,append_images=frames[1:],duration=100,loop=0)
    sheet=Image.new('RGB',(228*3,220*2),'#1b2027');d=ImageDraw.Draw(sheet)
    for i,count in enumerate(range(5,-1,-1)):
        x=i%3*228;y=i//3*220;sheet.paste(counts[count],(x,y+20));d.text((x+5,y+4),f'{count} in box',fill='white')
    sheet.save(out/'after_counts.png')
    sheet=Image.new('RGB',(228*len(carry),220),'#1b2027');d=ImageDraw.Draw(sheet)
    for i,(direction,im) in enumerate(carry.items()):
        sheet.paste(im,(228*i,20));d.text((228*i+5,4),direction+' carry',fill='white')
    sheet.save(out/'after_carry_views.png')
    from tools.liam_block_art import layers,structure
    front=structure()[1]
    subset=all((lambda im: (lambda c: c.tobytes()==im.tobytes())(Image.alpha_composite(im,front)))(layers(mask)[0]) for mask in range(32))
    # Compare actual live normal/reduced box pixels at the same action instant.
    game.audio.reduced_motion=False;game.draw();normal=game.canvas.native.copy()
    game.audio.reduced_motion=True;game.draw();reduced=game.canvas.native
    camera=main.camera_for(game.player.position,r.home.size)
    box=pygame.Rect((pygame.Vector2(r.box['position'])-camera)*2,(64,48))
    same=pygame.image.tobytes(normal.subsurface(box),'RGB')==pygame.image.tobytes(reduced.subsurface(box),'RGB')
    report={'baseline_commit':'5630648b4fe9cb79ae7b1ad867b4aa5b6e0cc836',
        'native_frame_size':list(game.canvas.native.get_size()),'selected_outcomes':{'accident':False,'forget':False},
        'long_initial_wait_skipped':True,'simulated_seconds':tick/30,'completed_cycles':r.completed_cycles,
        'final_states':[b['state'] for b in r.blocks],'production_carry_views':list(carry),
        'literal_front_subset_all_32_states':subset,'reduced_motion_box_pixels_identical':same,
        'frames':records,'events':list(r.events),
        'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.png'))}}
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    game.music.stop();pygame.quit();del game;gc.collect()
    print('Captured live box audit:',out)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUT)
    capture(parser.parse_args().output)
