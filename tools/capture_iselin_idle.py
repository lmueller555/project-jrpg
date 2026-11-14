"""Capture the approved idle through the production renderer; isolated save."""
from pathlib import Path
import json
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.capture_sanctuary_rescue import make_game
from regent_actors import StoryActor
import pygame


def capture():
    with tempfile.TemporaryDirectory() as directory:
        game=make_game(directory,seed=False,embedded=False)
        try:
            game.on_title=False;game.opening_fade=0
            game.player.story_visible=True
            actor=StoryActor(json.loads((ROOT/'assets/characters/iselin/actor.json').read_text()),game.world)
            actor.position.update(game.player.position+pygame.Vector2(25,0))
            actor.story_visible=True;game.world.npcs.append(actor)
            game.draw()
            assert game.canvas.patches
            pygame.image.save(game.window,str(ROOT/'docs/reviews/iselin_first_assets/implemented_scene.png'))
        finally:
            game.music.stop();pygame.quit()


if __name__=='__main__':capture()
