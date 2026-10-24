"""Capture the actual gardener simulation: route overview, fill and watering."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'

import json
import random
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


def gif(path,frames,duration_ms=100):
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
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=duration_ms,
                    loop=0,disposal=1,optimize=True)
    cursor=0
    with Image.open(path) as exported:
        for actual in ImageSequence.Iterator(exported):
            pixels=actual.convert('RGB').tobytes()
            for _ in range(actual.info['duration']//duration_ms):
                if frames[cursor].tobytes()!=pixels:raise ValueError('Encoded GIF differs from the runtime capture')
                cursor+=1
    if cursor!=len(frames):raise ValueError('Encoded GIF timing changed')
    print(f'{path.name}: {len(frames)} captures, {len(frames)*duration_ms/1000:.1f}s, {len(colors)} exact colors',flush=True)


def render(game,camera):
    game.world.draw(game.canvas,camera,game.player,game.elapsed_ms)
    return Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB'))


def capture():
    # Keep the original command useful; historical brook captures are retained.
    from capture_gardener_well import capture as current_capture
    current_capture()


if __name__=='__main__':capture()
