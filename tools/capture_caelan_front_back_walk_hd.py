"""Stationary hall-scale candidate playback; no activation or user-save writes."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import sys
import tempfile
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from main import Game
from rendering import WorldCanvas,artwork

ROOT=Path(__file__).resolve().parents[1]
BANK=ROOT/'assets/characters/caelan/review_hd/walk_right'
REVIEW=ROOT/'docs/reviews/caelan_right_walk_hd'


def capture(direction):
    global BANK,REVIEW
    BANK=ROOT/f'assets/characters/caelan/review_hd/walk_{direction}'
    REVIEW=ROOT/f'docs/reviews/caelan_{direction}_walk_hd'
    with tempfile.TemporaryDirectory(prefix='caelan-walk-review-') as directory:
        p=Path(directory);g=Game(fullscreen=False,start_on_title=True,
                              save_path=p/'save.json',settings_path=p/'settings.json')
        try:
            world=g._scene_by_id('sanctuary_hall');world.npcs.clear()
            g.player.position.update(168,282);g.player.facing='front' if direction=='front' else 'back'
            canvas=WorldCanvas(world.size);frames=[]
            for index in range(16):
                sprite=artwork(pygame.image.load(str(BANK/f'frame_{index+1:02}.png')).convert_alpha(),2)
                g.player.sprite=lambda s=sprite:s
                world.draw(canvas,(0,0),g.player,0,False)
                raw=canvas.native.subsurface((80,440,512,192))
                frame=Image.frombytes('RGB',raw.get_size(),pygame.image.tobytes(raw,'RGB'))
                frames.append(frame)
            packed=Image.new('RGB',(512*4,192*4))
            for i,frame in enumerate(frames):packed.paste(frame,(i%4*512,i//4*192))
            palette=packed.quantize(colors=256,dither=Image.Dither.NONE)
            indexed=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
            indexed[0].save(REVIEW/'hall_preview.gif',save_all=True,append_images=indexed[1:],
                            duration=[30,40]*8,loop=0,disposal=2,optimize=False)
            frames[0].save(REVIEW/'hall_contact.png')
        finally:g.music.stop();pygame.quit()


if __name__=='__main__':
    for direction in ('front','back'):capture(direction)
