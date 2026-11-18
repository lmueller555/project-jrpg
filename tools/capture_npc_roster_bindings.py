"""Capture seven opt-in residents and service portrait choices in actual rooms."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from main import Game
from npc_roster_art import bindings

def capture(folder):
    folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        game=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
                  save_path=root/'save.json',settings_path=root/'settings.json')
        try:
            game.on_title=False;game.opening.stage='disabled';game.opening_fade=game.transfer_cooldown=0
            records=[]
            for scene,point in [('home_a',(200,220)),('home_b',(240,220)),
                                ('home_c',(240,220)),('inn',(168,160)),('item_shop',(216,188))]:
                game.world=game._scene_by_id(scene);game.player.position.update(point)
                game.player.facing='back';game.camera.reset()
                game.draw();pygame.image.save(game.window,str(folder/f'{scene}.png'))
                for actor in game.world.npcs:
                    if actor.data['id'] in bindings():
                        records.append({'id':actor.data['id'],'design':actor.roster_art.design_id,
                                        'position':list(actor.position),'blocker':list(actor.blocker),
                                        'draw_anchor':list(actor.draw_anchor)})
                if scene in ('inn','item_shop'):
                    game.services.interact()
                    game.draw();pygame.image.save(game.window,str(folder/f'{scene}_portrait.png'))
                    game.social.cancel()
            (folder/'observations.json').write_text(json.dumps(records,indent=2)+'\n')
        finally:game.music.stop();pygame.quit()

if __name__=='__main__':capture(Path(sys.argv[1]))
