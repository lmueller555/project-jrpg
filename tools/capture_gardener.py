"""Capture the actual gardener simulation: route overview, fill and watering."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'

import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont, ImageSequence
import pygame

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import main

OUTPUT=ROOT/'docs/reviews/sanctuary_gardener'


def font(size):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',size)


def panel(scene,scale,title,subtitle,caption):
    scene=scene.resize((scene.width*scale,scene.height*scale),Image.Resampling.NEAREST)
    image=Image.new('RGB',(scene.width,scene.height+108),'#e8edf2')
    image.paste(scene,(0,68));d=ImageDraw.Draw(image);d.fontmode='1'
    d.text((16,8),title,font=font(22),fill='#24382f')
    d.text((16,37),subtitle,font=font(15),fill='#526761')
    d.text((16,image.height-30),caption,font=font(18),fill='#24382f')
    return image


def gif(path,frames):
    colors=set()
    for frame in frames:
        counts=frame.getcolors(256)
        if counts is None:raise ValueError('Review frame exceeds the exact GIF palette')
        colors.update(c for _,c in counts)
    if len(colors)>256:raise ValueError('Review sequence exceeds the exact GIF palette')
    ordered=sorted(colors);lookup={c:i for i,c in enumerate(ordered)}
    rgb=[v for c in ordered for v in c];rgb.extend([0]*(768-len(rgb)))
    indexed=[]
    for frame in frames:
        # Pillow's direct RGB->supplied-palette lookup can approximate nearby
        # shades. First extract the exact local colors, then remap their indices
        # into the shared palette (at most 256 entries, no per-pixel Python loop).
        local=frame.quantize(colors=256,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
        local_rgb=local.getpalette()
        table=[lookup.get(tuple(local_rgb[i:i+3]),0) for i in range(0,768,3)]
        item=local.point(table);item.putpalette(rgb)
        if item.convert('RGB').tobytes()!=frame.tobytes():raise ValueError('Review color changed during encoding')
        indexed.append(item)
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=100,
                    loop=0,disposal=1,optimize=False)
    cursor=0
    with Image.open(path) as exported:
        for actual in ImageSequence.Iterator(exported):
            pixels=actual.convert('RGB').tobytes()
            for _ in range(actual.info['duration']//100):
                if frames[cursor].tobytes()!=pixels:raise ValueError('Encoded GIF differs from the runtime capture')
                cursor+=1
    if cursor!=len(frames):raise ValueError('Encoded GIF timing changed')
    print(f'{path.name}: {len(frames)} captures, {len(frames)/10:.1f}s, {len(colors)} exact colors',flush=True)


def render(game,camera):
    game.world.draw(game.canvas,camera,game.player,game.elapsed_ms)
    return Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB'))


def caption(actor):
    state=actor.state
    if state=='rest':return 'Resting beside the flowers / empty bucket'
    if state=='pickup':return 'Pick up the empty bucket'
    if state=='to_brook':return 'Walk down the stairs and along the lane to the brook'
    if state=='fill':return f'Lower, fill and lift the bucket / water {actor.water_units} of 4'
    if state=='return_to_sanctuary':return 'Carry the full bucket back up the sanctuary stairs'
    if state=='return_to_rest':return 'Return with the empty bucket'
    if state=='setdown':return 'Set down the empty bucket'
    bed=state.split('_',1)[1].replace('_',' ')
    if state.startswith('water_'):return f'Water {bed} / two small pours'
    if state.startswith('inspect_'):return f'Inspect {bed}'
    return 'Carry water to the next flower patch'


def capture():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    game=main.Game();game.player.position.update(516,900)
    actor=game.town.npcs[1]
    # Trim only the beginning of the initial rest. All travel and work are 1x.
    game.update(7.5,(0,0),False)
    route=[];filling=[];watering=[];events=[];previous=None
    first_cycle=None
    for index in range(750):
        state=actor.state
        if state!=previous:
            events.append({'time_ms':round(game.elapsed_ms),'state':state,'position':list(actor.position),'water_units':actor.water_units})
            previous=state
        # Two adjacent runtime views form the wider route overview; actor and
        # scenery depth/collision/animation all come from the game's renderer.
        left=render(game,(192,240))
        right=render(game,(672,240))
        overview=Image.new('RGB',(672,288))
        overview.paste(left.crop((0,0,480,288)),(0,0))
        overview.paste(right.crop((0,0,192,288)),(480,0))
        text=caption(actor)
        route.append(panel(overview,2,'Sanctuary gardener / complete watering trip',
                           'Actual game simulation | 2x scene | travel and work at real speed',text))
        if state=='fill':
            close=render(game,(738,366)).crop((0,0,96,80))
            filling.append(panel(close,6,'Gardener / collecting water','6x enlargement | bucket contact, filling and lifting',text))
        if state.startswith(('inspect_','water_')):
            camera=(round(actor.position.x)-60,round(actor.position.y)-54)
            close=render(game,camera).crop((0,0,120,80))
            watering.append(panel(close,6,'Gardener / four flower patches',
                                  '6x enlargement | consecutive stops shown as a review montage',text))
        if actor.completed_cycles and first_cycle is None:first_cycle=game.elapsed_ms
        if first_cycle is not None and game.elapsed_ms-first_cycle>=1000:break
        game.update(.1,(0,0),False)
        if index%150==0:print(f'Captured {index/10:.0f}s / {actor.state}',flush=True)
    if not actor.completed_cycles:raise RuntimeError('Gardener did not complete her trip')
    filling[len(filling)//2].save(OUTPUT/'filling.png')
    watering[16].save(OUTPUT/'watering.png')
    route[-12].save(OUTPUT/'route.png')
    gif(OUTPUT/'filling.gif',filling)
    gif(OUTPUT/'watering.gif',watering)
    gif(OUTPUT/'route.gif',route)
    (OUTPUT/'capture.json').write_text(json.dumps({
        'status':'review','capture_start_ms':7500,'first_cycle_complete_ms':round(first_cycle),
        'watered_beds':actor.watered_beds,'final_water_units':actor.water_units,
        'events':events,'capture_interval_ms':100,'route_frames':len(route)
    },indent=2)+'\n')
    pygame.quit()


if __name__=='__main__':capture()
