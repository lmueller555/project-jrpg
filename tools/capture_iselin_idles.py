"""Production-render all idle facings using temporary saves."""
import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.capture_sanctuary_rescue import make_game
from regent_actors import StoryActor
import pygame

with tempfile.TemporaryDirectory() as directory:
    game=make_game(directory,seed=False,embedded=False)
    try:
        game.on_title=False;game.opening_fade=0;game.player.story_visible=True
        for index,direction in enumerate(('front','left','right','back')):
            record=json.loads((ROOT/'assets/characters/iselin/actor.json').read_text())
            record['facing']=direction
            actor=StoryActor(record,game.world)
            actor.position.update(game.player.position+pygame.Vector2(25*(index+1),0))
            actor.story_visible=True;game.world.npcs.append(actor)
        game.draw()
        assert len(game.canvas.patches)>=4
        pygame.image.save(game.window,str(ROOT/'docs/reviews/iselin_first_assets/directional_scene.png'))
    finally:game.music.stop();pygame.quit()
