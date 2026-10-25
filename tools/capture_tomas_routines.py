"""Capture Tomas's real continuous schedule, with Serene and gardener active."""
import json
import os
from collections import Counter
from pathlib import Path
import random
import subprocess
import sys

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
from PIL import Image,ImageDraw,ImageFont
import pygame

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import main

OUT=ROOT/'docs/reviews/tomas_routines'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def panel(im,title,caption,scale):
    im=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)
    result=Image.new('RGB',(im.width,im.height+76),'#e8edf2');result.paste(im,(0,76))
    d=ImageDraw.Draw(result);d.fontmode='1'
    d.text((14,8),title,font=ImageFont.truetype(FONT,21),fill='#24382f')
    d.text((14,40),caption,font=ImageFont.truetype(FONT,16),fill='#526761')
    return result


def gif(path,frames):
    # One shared palette for the complete clip; never dither pixel sprites.
    colors=Counter()
    for im in frames:
        colors.update({color:count for count,color in im.getcolors(im.width*im.height)})
    if len(colors)<=256:
        palette=Image.new('P',(1,1))
        rgb=[v for color in colors for v in color]
        palette.putpalette(rgb+[0]*(768-len(rgb)))
    else:
        sample=Image.new('RGB',(frames[0].width,len(frames)*40))
        for i,im in enumerate(frames):
            sample.paste(im.resize((im.width,40),Image.Resampling.NEAREST),(0,i*40))
        palette=sample.quantize(colors=256)
    indexed=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=100,loop=0,disposal=2,optimize=False)


def capture():
    OUT.mkdir(parents=True,exist_ok=True);random.seed(14)
    g=main.Game(fullscreen=False,start_on_title=False)
    a=next(x for x in g.persistent_npcs if x.data['id']=='tomas')
    # Observe without blocking any actor or triggering a conversation.
    g.world=g._scene_by_id('sanctuary_bedroom');g.player.position.update(-1000,-1000)
    native=pygame.Surface((480,320));clips={'preparations':[],'tinkering':[],'courtyard':[]}
    phases=[];previous=None;video=None;frames=0
    try:
        for index in range(2400):
            world=g._routine_worlds[a];state=a.state
            if state!=previous:
                phases.append({'time_seconds':round(index/10,1),'step':state,'scene':a.scene_id,
                               'position':list(a.position)})
                print(index/10,state,a.scene_id,tuple(a.position),flush=True);previous=state
            if a.completed_cycles:break
            camera=main.camera_for(a.position,world.size,main.VIEW_SIZE)
            world.draw(native,camera,g.player,g.elapsed_ms)
            im=Image.frombytes('RGB',native.get_size(),pygame.image.tobytes(native,'RGB'))
            phase=a.current_action_record.get('phase',state).replace('_',' ')
            screen=panel(im,'Tomas / sanctuary routine',f'{world.data.get("name","Eldenmere")} | {phase} | actual game, 2x pixels',2)
            if video is None:
                video=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pixel_format','rgb24',
                    '-video_size',f'{screen.width}x{screen.height}','-framerate','10','-i','-',
                    '-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p',
                    '-movflags','+faststart',str(OUT/'full_routine.mp4')],stdin=subprocess.PIPE)
            video.stdin.write(screen.tobytes());frames+=1
            # Fixed authored close-ups use the same world renderer and state;
            # no poses, handoffs or timings are manufactured for the review.
            key=None
            if state in ('prepare','carry_to_storage','store_bundle') and index<200:
                key='preparations';box=(92,220,228,310);scale=5
            elif state in ('tinker','think_about_model'):
                key='tinkering';box=(78,220,168,300);scale=7
            elif a.scene_id==g.town.data['id']:
                key='courtyard';box=(246,246,486,426);scale=3
            if key:
                view=pygame.Surface((480,480));world.draw(view,(0,0) if key!='courtyard' else (200,150),g.player,g.elapsed_ms)
                scene=Image.frombytes('RGB',view.get_size(),pygame.image.tobytes(view,'RGB'))
                if key=='courtyard':box=(box[0]-200,box[1]-150,box[2]-200,box[3]-150)
                shot=panel(scene.crop(box),f'Tomas / {key}',f'{phase} | actual game timing',scale)
                clips[key].append(shot)
                if key=='tinkering' and phase=='turn crank':shot.save(OUT/'tinkering.png')
                if key=='preparations' and phase=='press fold':shot.save(OUT/'preparations.png')
                if key=='courtyard' and phase=='watch the village path':shot.save(OUT/'courtyard.png')
            g.update(.1,(0,0),False)
        else:raise AssertionError(f'Tomas did not finish: {a.state} {tuple(a.position)}')
    finally:
        if video:
            video.stdin.close()
            if video.wait()!=0:raise RuntimeError('Video encoding failed')
        pygame.quit()
    for name,images in clips.items():
        if not images:raise AssertionError(f'No captures for {name}')
        gif(OUT/f'{name}.gif',images)
    (OUT/'capture.json').write_text(json.dumps({'fps':10,'frames':frames,'duration_seconds':frames/10,
        'completed_cycles':a.completed_cycles,'phases':phases,'preview_frames':{k:len(v) for k,v in clips.items()}},indent=2)+'\n')


def capture_dialogue():
    """Exercise automatic close-proximity dialogue in the furnished room."""
    g=main.Game(fullscreen=False,start_on_title=False)
    g.world=g._scene_by_id('sanctuary_dining')
    g.player.position.update(184,262);g.player.facing='left'
    g.update(1/60,(-1,0),False)
    if not g.social.active or g.social.actor.data['id']!='tomas':
        raise AssertionError('Close approach did not start Tomas dialogue')
    g.draw()
    im=Image.frombytes('RGB',g.canvas.get_size(),pygame.image.tobytes(g.canvas,'RGB'))
    im.resize((960,640),Image.Resampling.NEAREST).save(OUT/'dialogue.png')
    pygame.quit()


if __name__=='__main__':
    capture()
    capture_dialogue()
