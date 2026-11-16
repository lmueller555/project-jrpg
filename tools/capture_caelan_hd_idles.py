"""Preview candidate idles through World rendering without runtime activation."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from main import Game
from rendering import WorldCanvas,artwork

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'docs/reviews/caelan_hd_idles'


def capture():
    with tempfile.TemporaryDirectory(prefix='caelan-idle-review-') as directory:
        p=Path(directory);g=Game(fullscreen=False,start_on_title=True,
                              save_path=p/'save.json',settings_path=p/'settings.json')
        try:
            world=g._scene_by_id('sanctuary_hall');world.npcs.clear()
            actors=[];labels=[]
            def actor(label,image,position,anchor):
                actors.append(SimpleNamespace(data={'id':label},position=pygame.Vector2(position),
                    draw_anchor=anchor,story_visible=True,sprite=lambda elapsed,s=image:s))
                labels.append((label,position))
            for direction,x in zip(('front','left','right','back'),(84,144,204,264)):
                path=ROOT/f'assets/characters/caelan/review_hd/idles/idle_{direction}.png'
                image=artwork(pygame.image.load(str(path)).convert_alpha(),2)
                actor(direction.title(),image,(x,150),(12,30))
            actor('Current Caelan',g.player.idles['front'],(96,282),(12,30))
            actor('Current Mira',world.image('assets/characters/mira/idle_front.png'),(162,282),(16,30))
            actor('Iselin',artwork(world.image('assets/characters/iselin/idle_front_42x72.png'),2),
                  (222,282),(10.5,30))
            canvas=WorldCanvas(world.size);g.player.story_visible=False
            world.draw(canvas,(0,0),g.player,0,False,party_actors=actors)
            frame=canvas.native.copy();font=pygame.font.Font(None,17)
            for label,(x,y) in labels:
                text=font.render(label,False,'#f4ebd4');rect=text.get_rect(midtop=(x*2,y*2+12))
                pygame.draw.rect(frame,'#24302d',rect.inflate(8,5));frame.blit(text,rect)
            pygame.image.save(frame,str(REVIEW/'hall_comparison.png'))
        finally:g.music.stop();pygame.quit()


if __name__=='__main__':capture()
