"""Render hall, bedroom, doors and the existing wake poses with temporary saves."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import argparse
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from main import Game
from rendering import WorldCanvas


def capture(folder):
    folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='home-review-') as temp:
        p=Path(temp);g=Game(fullscreen=False,start_on_title=True,save_path=p/'save.json',settings_path=p/'settings.json')
        try:
            g.on_title=False;g.opening.stage='done'
            def shot(name):
                canvas=WorldCanvas(g.world.size)
                g.world.draw(canvas,(0,0),g.player,0,False)
                g.opening.draw_world(canvas,(0,0))
                pygame.image.save(canvas.native,str(folder/(name+'.png')))
            for room,position in [('hall',(168,276)),('bedroom',(144,276))]:
                g.world=g._scene_by_id('sanctuary_'+room);g.player.position.update(position)
                g._update_object_cues(.12);shot(room)
            g.player.position.update(60,90);g._update_object_cues(.12);shot('drawing_near')
            g.player.position.update(180,90);g._update_object_cues(.12);shot('window_near')
            g.opening.start_new_game();shot('sleeping')
            g.opening._queue_wake()
            for i in range(4):
                g.opening._update_actions(.18 if not i else .25);shot('wake_'+str(i))
            g.opening._clear();g.opening.stage='done'
            g.world=g._scene_by_id('sanctuary_hall');g.player.position.update(168,276)
            for door in g.world.doors:
                if door.frames:door.progress=4
            shot('hall_doors_open')
            serene=next(a for a in g.persistent_npcs if a.data['id']=='mother_serene')
            for world in g.scenes.values():
                while serene in world.npcs:world.npcs.remove(serene)
            g.world.npcs.append(serene);g._routine_worlds[serene]=g.world
            for step,position in [('consult_list',(120,178)),('arrange_hall',(264,214))]:
                serene.select_step(step,position=position,scene_id='sanctuary_hall',facing='back')
                serene.state_ms=500
                shot('serene_'+step)
        finally:g.music.stop();pygame.quit()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path)
    capture(parser.parse_args().output)
