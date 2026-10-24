"""Capture actual title input, settings, animation and the playable transition."""
import os
import sys
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
from PIL import Image
import pygame

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import main

OUTPUT=ROOT/'docs/reviews/title_screen'


def capture():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    game=main.Game(window_size=(1280,720),fullscreen=False)
    frames=[]

    def run(count):
        for _ in range(count):
            game.handle_events()
            for _ in range(6):game.update(1/60,(0,0),False)
            game.draw()
            frames.append(Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB')))

    def hover(index):
        point=tuple(v*2 for v in game.title.rows[index].center)
        pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION,pos=point,rel=(0,0),buttons=(0,0,0)))
        game.handle_events()
        return point

    run(20)
    pygame.image.save(game.window,str(OUTPUT/'title_screen.png'))
    point=hover(2)
    run(8)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point))
    run(12)
    pygame.image.save(game.window,str(OUTPUT/'settings.png'))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
    run(8)
    point=hover(0)
    run(8)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point))
    run(16)
    assert not game.on_title
    pygame.image.save(game.window,str(OUTPUT/'new_game.png'))

    sample=Image.new('RGB',(640,360*len(frames[::6])))
    for index,frame in enumerate(frames[::6]):
        sample.paste(frame.resize((640,360),Image.Resampling.NEAREST),(0,index*360))
    palette=sample.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    indexed=[frame.resize((640,360),Image.Resampling.NEAREST).quantize(palette=palette,dither=Image.Dither.NONE)
             for frame in frames[::2]]
    indexed[0].save(OUTPUT/'title_menu.gif',save_all=True,append_images=indexed[1:],
                    duration=200,loop=0,disposal=2,optimize=False)
    with Image.open(OUTPUT/'title_menu.gif') as gif:
        for index in range(gif.n_frames):
            gif.seek(index)
            assert gif.tile[0][1]==(0,0,640,360)
            assert gif.disposal_method==2
    pygame.quit()
    print('Captured 1280x720 stills and a 640x360 menu/transition loop.')


if __name__=='__main__':capture()
