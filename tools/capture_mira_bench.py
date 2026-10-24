"""Capture Mira's real runtime routine at exact pose/environment boundaries."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'

from collections import Counter
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont
import pygame

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import main

OUTPUT=ROOT/'docs/reviews/mira_bench'


def font(size):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',size)


def save_gif(path,frames,durations):
    # Fixed shared palette prevents frame-to-frame color flicker. These small
    # crops fit within GIF's palette, so all native world colors are retained.
    colors=Counter()
    for frame in frames:colors.update(frame.get_flattened_data())
    if len(colors)>256:
        raise ValueError(f'Review needs a lossless palette: {len(colors)} colors')
    palette=list(colors)
    lookup={color:i for i,color in enumerate(palette)}
    rgb=[v for color in palette for v in color]
    rgb.extend([0]*(768-len(rgb)))
    indexed=[]
    for frame in frames:
        item=Image.new('P',frame.size)
        item.putpalette(rgb)
        item.putdata([lookup[c] for c in frame.get_flattened_data()])
        indexed.append(item)
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=durations,
                    loop=0,disposal=1,optimize=False)
    return len(colors)


def panel(scene,box,scale,title,subtitle,caption):
    crop=scene.crop(box)
    crop=crop.resize((crop.width*scale,crop.height*scale),Image.Resampling.NEAREST)
    output=Image.new('RGB',(crop.width,crop.height+108),'#e8edf2')
    output.paste(crop,(0,68))
    d=ImageDraw.Draw(output)
    # Bilevel font masks keep exported pixel previews within an exact palette.
    d.fontmode='1'
    d.text((16,8),title,font=font(22),fill='#24382f')
    d.text((16,37),subtitle,font=font(15),fill='#526761')
    d.text((16,output.height-30),caption,font=font(18),fill='#24382f')
    return output


def capture():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    game=main.Game(fullscreen=False,start_on_title=False)
    game.player.position.update(652,480)
    game.player.facing='back'
    mira=game.world.npcs[0]
    times={0,mira.duration_ms}
    cursor=0
    for _,_,record in mira.frames:
        cursor+=record['duration_ms'];times.add(cursor)
    times.update(range(0,mira.duration_ms,200))
    times=sorted(times)
    durations=[b-a for a,b in zip(times,times[1:])]
    closeups=[];scenes=[]
    camera=(528,240)
    captions={'pause':'Pause / hand on hip', 'inspect':'Lean in / inspect fitting',
              'reach':'Bring wrench to fitting', 'tighten':'Tighten / three deliberate wrench strokes',
              'reset':'Reset wrench for the next stroke', 'release':'Release wrench',
              'test':'Wrench lowered / test the fitting by hand', 'straighten':'Lower hands / straighten up'}
    for time in times[:-1]:
        game.update((time-game.elapsed_ms)/1000,(0,0),False)
        # Integer event boundaries avoid floating-point rounding delaying a pose.
        game.elapsed_ms=time
        game.world.draw(game.canvas,camera,game.player,game.elapsed_ms)
        scene=Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB'))
        action=mira.frame(game.elapsed_ms)[2]['action']
        closeups.append(panel(scene,(16,148,136,244),6,'Mira / outdoor bench routine',
                               '24 x 36 character | 6x enlargement | 8-second loop',captions[action]))
        scenes.append(panel(scene,(0,0,216,264),3,'Mira / workshop scene',
                            'Actual game rendering | 3x enlargement',captions[action]))
    poster=times.index(2400)
    closeups[poster].save(OUTPUT/'bench_closeup.png')
    scenes[poster].save(OUTPUT/'workshop_scene.png')
    for name,frames in [('bench_closeup',closeups),('workshop_scene',scenes)]:
        colors=save_gif(OUTPUT/f'{name}.gif',frames,durations)
        print(f'{name}: {len(frames)} capture frames, {sum(durations)} ms, {colors} exact colors')
    pygame.quit()


if __name__=='__main__':capture()
