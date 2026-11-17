"""Capture real native room frames through Daisy's two complete feeding visits."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import json
from pathlib import Path
import sys
import pygame
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import main
OUT=ROOT/'docs/reviews/liam_interior_audit'


def capture():
    OUT.mkdir(parents=True,exist_ok=True)
    g=main.Game(fullscreen=False,start_on_title=False);g.world=g._scene_by_id('liam_house');g.player.position.update(230,300)
    a=next(n for n in g.world.npcs if n.data['id']=='daisy');camera=(-24,16)
    report={'camera_logical':list(camera),'render_pixels_per_world_unit':2,'captures':[]}
    def frame():
        g.world.draw(g.canvas,camera,g.player,g.elapsed_ms)
        return Image.frombytes('RGB',g.canvas.native.get_size(),pygame.image.tobytes(g.canvas.native,'RGB'))
    frame().save(OUT/'after_room.png')
    for kind,action in (('food','eat'),('water','drink')):
        frames=[];states=[];levels=[]
        for visit in range(2):
            a.begin_activity(kind,g.world)
            for tick in range(400):
                image=frame()
                # Actual room crop at native scene density, without isolated-asset compositing.
                crop=image.crop((248,450,508,570))
                if tick%2==0:frames.append(crop)
                if a.state not in states:states.append(a.state)
                g.elapsed_ms+=100;a.update(.1,g.world)
                if a.state==action and tick%5==0:
                    image.save(OUT/f'after_{action}_{visit}.png')
                if a.state=='rest':
                    level=a.bowls[kind]['state'];levels.append(level)
                    frame().save(OUT/f'after_{kind}_{level}.png')
                    frames.extend([frame().crop((248,450,508,570))]*4)
                    break
            else:raise RuntimeError((kind,a.state))
        frames[0].save(OUT/f'{kind}_depletion.gif',save_all=True,append_images=frames[1:],duration=200,loop=0,disposal=2,optimize=True)
        report['captures'].append({'kind':kind,'completed_levels':levels,'visited_states':states,'gif_frame_duration_ms':200,'gif_initial_wait_skipped':True})
    (OUT/'bowl-captures.json').write_text(json.dumps(report,indent=2)+'\n')
    pygame.quit();print('Captured native room food/water depletion, contact and unchanged support.')

if __name__=='__main__':capture()
