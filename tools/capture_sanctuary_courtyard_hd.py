"""Capture actual courtyard movement, depth, doors and reduced motion safely."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import argparse
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from PIL import Image
from main import Game
from rendering import WorldCanvas


def capture(folder):
    folder.mkdir(parents=True,exist_ok=True);observations={};camera=(120,72)
    with tempfile.TemporaryDirectory(prefix='courtyard-review-') as temp:
        p=Path(temp);g=Game(fullscreen=False,start_on_title=True,save_path=p/'save.json',settings_path=p/'settings.json')
        try:
            g.on_title=False;g.opening.restore({'version':1,'stage':'disabled'});g.opening_fade=0;g.world=g.town;g.transfer_cooldown=0
            def shot(name=None):
                g.draw() # Exercise the complete game renderer as well as the fixed review camera.
                c=WorldCanvas((480,320));g.world.draw(c,camera,g.player,g.elapsed_ms,False,party_actors=g.party_travel.actors())
                if name:pygame.image.save(c.native,str(folder/(name+'.png')))
                return Image.frombytes('RGB',c.native.get_size(),pygame.image.tobytes(c.native,'RGB'))
            g.player.position.update(384,320);shot('courtyard_native');pygame.image.save(g.canvas.native,str(folder/'gameplay_native.png'))
            for running in (False,True):
                name='run' if running else 'walk';g.player.position.update(384,400);frames=[];positions=[]
                for i in range(72):
                    dy=(-1 if g.player.position.y>310 else 0) if i<36 else (1 if g.player.position.y<400 else 0)
                    g.update(1/30,(0,dy),running);positions.append(list(g.player.position));frames.append(shot())
                frames[0].save(folder/(name+'_stairs.gif'),save_all=True,append_images=frames[1:],duration=33,loop=0);observations[name+'_stairs']=positions
            for name,position in [('behind_tree',(242,312)),('in_front_of_tree',(242,340))]:
                g.player.position.update(position);shot(name);observations[name]={'position':list(position),'can_stand':g.world.can_stand(position)}
            clump=next(c for c in g.world.grass.clumps if c.variant=='splayed_hd');x,y=clump.position
            for running in (False,True):
                name='grass_run' if running else 'grass_walk';g.world.grass.reset();g.player.position.update(x-26,y);g.world.update_grass(0,g.player);frames=[]
                for _ in range(30):g.update(1/30,(1,0),running);frames.append(shot())
                frames[0].save(folder/(name+'.gif'),save_all=True,append_images=frames[1:],duration=33,loop=0);observations[name]=g.world.grass.snapshot()
            g.player.position.update(386,310);g.update(.5,(0,0),False);shot('door_open')
            g.player.position.update(384,320);g.audio.set_reduced_motion(True);g.update(.1,(0,0),False);shot('reduced_motion')
            g.audio.set_reduced_motion(False);g.update(.2,(0,0),False);shot('ambient_light')
            (folder/'observations.json').write_text(json.dumps(observations,indent=2)+'\n')
        finally:g.music.stop();pygame.quit()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);capture(parser.parse_args().output)
