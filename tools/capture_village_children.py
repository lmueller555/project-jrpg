"""Pixel-exact child sprite inspection and actual family-room placement renders."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from pathlib import Path
import sys
import json
import pygame
from PIL import Image,ImageDraw,ImageSequence
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import main
from capture_liam_house import card
from capture_villager_households import room_image
from capture_liam_blocks import save_gif
from build_liam_family_front_walks import font,write

OUT=ROOT/'docs/reviews/village_children'
KIDS=('tessa','finn','rowan','ada','pippa')
DIRECTIONS=('front','left','right','back')
AGES={'tessa':10,'finn':6,'rowan':9,'ada':7,'pippa':8,'liam':8}
GENDERS={'tessa':'girl','finn':'boy','rowan':'boy','ada':'girl','pippa':'girl','liam':'boy'}
BACKGROUND='#e8edf2';INK='#26343e';MUTED='#52616c'


def opened(path):
    with Image.open(path) as im:return im.convert('RGBA')


def sprite(character,direction,verb=None,phase=0):
    folder=ROOT/'assets/characters'/character
    if verb is None:return opened(folder/f'idle_{direction}.png')
    folder=folder/f'{verb}_{direction}'
    meta=json.loads((folder/'animation.json').read_text())
    return opened(folder/meta['frames'][phase]['file'])


def header(draw,title,subtitle):
    draw.fontmode='1';draw.text((22,14),title,font=font(26),fill=INK)
    draw.text((22,53),subtitle,font=font(17),fill=MUTED)


def directions(verb=None,phase=0,slow=False):
    scale=5;left=90;step=150;rowstep=192;top=132
    image=Image.new('RGB',(860,top+4*rowstep+12),BACKGROUND);d=ImageDraw.Draw(image)
    title='Five children / directional idles' if verb is None else f'Five children / {"walking" if verb=="walk" else "running"}{" — slow review" if slow else ""}'
    subtitle=('24x36 frames | approved Liam scale | all four facings' if verb is None else
              f'Four unique poses per direction | {420 if verb=="walk" and slow else 300 if slow else 140 if verb=="walk" else 100} ms per pose | sprite pack review')
    header(d,title,subtitle)
    for i,kid in enumerate(KIDS):
        x=left+i*step;d.text((x,88),kid.title(),font=font(21),fill=INK)
        d.text((x,113),f'{AGES[kid]} / {GENDERS[kid]}',font=font(15),fill=MUTED)
    for row,direction in enumerate(DIRECTIONS):
        y=top+row*rowstep
        d.text((10,y+76),direction.title(),font=font(17),fill=MUTED)
        d.line((left-3,y+175,842,y+175),fill='#bac7c8')
        for col,kid in enumerate(KIDS):
            p=sprite(kid,direction,verb,phase).resize((120,180),Image.Resampling.NEAREST)
            image.paste(p,(left+col*step,y),p)
    return image


def heights():
    ids=('liam',)+KIDS;image=Image.new('RGB',(1000,400),BACKGROUND);d=ImageDraw.Draw(image)
    header(d,'Liam and five new classmates / scale comparison','Shared native foot baseline | frame24x36 | younger children are visibly smaller')
    y=110;scale=6
    d.line((20,y+35*scale,980,y+35*scale),fill='#bac7c8')
    for i,kid in enumerate(ids):
        x=24+i*160;p=sprite(kid,'front').resize((144,216),Image.Resampling.NEAREST)
        image.paste(p,(x,y),p);d.text((x,340),kid.title(),font=font(21),fill=INK)
        d.text((x,369),f'{AGES[kid]} / {GENDERS[kid]}',font=font(16),fill=MUTED)
    return image


def phases(verb):
    image=Image.new('RGB',(730,1110),BACKGROUND);d=ImageDraw.Draw(image)
    header(d,f'Left-facing {verb} / all four poses','Same native scale | source asset poses, not an autonomous routine')
    for row,kid in enumerate(KIDS):
        y=106+row*198;d.text((10,y+60),kid.title(),font=font(18),fill=INK)
        for phase in range(4):
            p=sprite(kid,'left',verb,phase).resize((120,180),Image.Resampling.NEAREST)
            image.paste(p,(110+phase*150,y),p)
    return image


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    directions().save(OUT/'idle_directions.png');heights().save(OUT/'height_comparison.png')
    timing={}
    for verb,name,duration in [('walk','walks',140),('run','runs',100)]:
        frames=[directions(verb,phase) for phase in range(4)]
        save_gif(OUT/f'{name}.gif',frames,duration)
        slow=[directions(verb,phase,True) for phase in range(4)]
        save_gif(OUT/f'{name}_slow.gif',slow,duration*3)
        phases(verb).save(OUT/f'{name}_left_phases.png')
        timing[name]={'frame_count':4,'duration_ms':duration,'slow_duration_ms':duration*3,'directions':list(DIRECTIONS),'characters':list(KIDS)}
        print('Captured',name,'and slow review in all four directions.',flush=True)
    game=main.Game(fullscreen=False,start_on_title=False)
    for r in game.play_routines+game.block_routines+game.bone_routines:r.cooldown_ms=999999
    registry=main.read_json(ROOT/'assets/maps/eldenmere/households/households.json');homes={}
    for family in registry['households']:
        key=family['home'];room=game._scene_by_id(key);game.world=room;game.player.position.update(178,292)
        names=', '.join(c['name'] for c in family['children'])
        subtitle=f'{names} | individual compact twin beds | actual game placement'
        if key=='home_a':subtitle='Tessa and Finn | mother works at sanctuary | two compact twin beds'
        frames=[]
        for i in range(36):
            game.elapsed_ms=i*300
            frames.append(card(room_image(game,room),family['label']+' / children at home',subtitle,2))
        frames[0].save(OUT/f'{key}.png');save_gif(OUT/f'{key}.gif',frames,300)
        homes[key]={'members':room.data['household'],'present':[a.data['id'] for a in room.npcs],
                    'children':[c['id'] for c in family['children']],
                    'beds':[{'id':e['id'],'owner_child':e['owner_child'],'position':e['position'],'floor_rect':e['floor_rect']} for e in room.entities if e.get('owner_child')]}
        print('Captured',key,'with',len(homes[key]['beds']),'compact child beds.',flush=True)
    pygame.quit()
    gif_validation={}
    for p in sorted(OUT.glob('*.gif')):
        with Image.open(p) as im:
            assert im.info['loop']==0
            duration=sum(f.info['duration'] for f in ImageSequence.Iterator(im))
            gif_validation[p.name]={'frames':im.n_frames,'duration_ms':duration,'bytes':p.stat().st_size}
    write(OUT/'captures.json',{'status':'review','sprite_previews_are_asset_loops':True,
          'children_currently_stationary_at_home':True,'gardener_stays_outdoors':True,
          'animation_timing':timing,'homes':homes,'gifs':gif_validation})
    print('All child sprite grids and family homes captured; GIF loops/timing decoded.',flush=True)


if __name__=='__main__':run()
