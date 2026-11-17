"""Capture the shared hearth through production Game/World rendering, no real saves."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import argparse
from pathlib import Path
import sys
import tempfile
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from PIL import Image,ImageDraw
from main import Game
from rendering import WorldCanvas

ROOT=Path(__file__).resolve().parents[1]
ROOMS=('liam_house','halden','elira','venn','home_a','home_b','home_c','mira','mill','school','sanctuary_dining')


def capture(output):
    output.mkdir(parents=True,exist_ok=True)
    observations={'rooms':{},'timing_ms':300,'cycles':3,'resolution':'960x640 native'}
    with tempfile.TemporaryDirectory(prefix='hearth-review-') as directory:
        path=Path(directory)
        game=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
                  save_path=path/'journey.json',settings_path=path/'settings.json')
        try:
            game.on_title=False;game.opening.restore({'version':1,'stage':'disabled'});game.opening_fade=0
            view=WorldCanvas((480,320))
            crops=[]
            for name in ROOMS:
                game.world=game._scene_by_id(name);game.player.position.update(280,150)
                hearth=next(e for e in game.world.entities if e['id']=='hearth')
                x,y=hearth['position'];phases=[]
                for phase in range(4):
                    game.world.draw(view,(0,0),game.player,phase*300,False,party_actors=[])
                    im=Image.frombytes('RGB',view.native.get_size(),pygame.image.tobytes(view.native,'RGB'))
                    phases.append(im.crop((x*2-12,y*2-8,x*2+108,y*2+152)))
                observations['rooms'][name]={'frames':hearth['frames'],'position':hearth['position'],
                    'sort_y':hearth['sort_y'],'sort_priority':hearth['sort_priority'],
                    'reduced_motion_frame':hearth['reduced_motion_frame']}
                if name=='liam_house':
                    for phase,im in enumerate(phases):im.save(output/f'liam_phase_{phase}.png')
                    loop=phases*3
                    loop[0].save(output/'three_loops.gif',save_all=True,append_images=loop[1:],duration=300,loop=0,optimize=False,disposal=2)
                row=Image.new('RGB',(480,184),'#e8edf2');draw=ImageDraw.Draw(row);draw.text((6,4),name,fill='#24302d')
                for phase,im in enumerate(phases):row.paste(im,(phase*120,24))
                crops.append(row)
            sheet=Image.new('RGB',(960,184*6),'#e8edf2')
            for i,row in enumerate(crops):sheet.paste(row,((i%2)*480,(i//2)*184))
            sheet.save(output/'live_families.png')
            game.world=game._scene_by_id('liam_house');game.player.position.update(280,150);game.camera.reset()
            game.elapsed_ms=600;game.draw();pygame.image.save(game.canvas.native,str(output/'liam_native.png'))
            game.audio.set_reduced_motion(True)
            game.update(0,(0,0),False)
            checks=[]
            for elapsed in (0,300,600,900,1200,1000000):
                game.elapsed_ms=elapsed;game.draw()
                rect=pygame.Rect(326*2,24*2,96,144)
                checks.append(pygame.image.tobytes(game.canvas.native.subsurface(rect),'RGB'))
            assert len(set(checks))==1
            observations['reduced_motion_stable_samples']=len(checks)
            pygame.image.save(game.canvas.native,str(output/'liam_reduced_motion.png'))
            # Diagnostic overlap uses real Caelan art at the existing depth baseline.
            game.audio.set_reduced_motion(False)
            game.update(0,(0,0),False)
            for name,position in (('behind',(350,80)),('front',(350,92))):
                game.player.position.update(position);game.camera.reset();game.elapsed_ms=600;game.draw()
                pygame.image.save(game.canvas.native,str(output/('liam_actor_'+name+'.png')))
            (output/'observations.json').write_text(json.dumps(observations,indent=2)+'\n')
        finally:game.music.stop();pygame.quit()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    capture(parser.parse_args().output)
