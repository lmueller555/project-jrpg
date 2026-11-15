"""Capture actual dining composition/cue states with temporary saves only."""
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
    with tempfile.TemporaryDirectory(prefix='dining-review-') as temp:
        p=Path(temp)
        g=Game(fullscreen=False,start_on_title=True,save_path=p/'save.json',settings_path=p/'settings.json')
        try:
            g.on_title=False;g.world=g._scene_by_id('sanctuary_dining')
            canvas=WorldCanvas(g.world.size)
            for name,stage,position in [('room','done',(228,252)),
                                        ('glint','explore',(228,294)),
                                        ('near','explore',(168,220))]:
                g.opening.stage=stage;g.player.position.update(position)
                g.player.facing='back';g._update_object_cues(.12)
                if name=='glint':
                    period,offset=g.world.object_cues.timing('breakfast')
                    g.world.object_cues.clock=period-offset+g.world.object_cues.GLINT_SECONDS/2
                g.world.draw(canvas,(0,0),g.player,0,False)
                pygame.image.save(canvas.native,str(folder/(name+'.png')))
        finally:g.music.stop();pygame.quit()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path)
    capture(parser.parse_args().output)
