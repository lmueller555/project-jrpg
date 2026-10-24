"""Capture full in-game water animation with the complete title soundtrack."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
from PIL import Image
import pygame

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import main

OUTPUT=ROOT/'docs/reviews/title_water_music'


def capture():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    game=main.Game(window_size=(640,360),fullscreen=False)
    score=json.loads((ROOT/'assets/ui/title/music_score.json').read_text())
    duration=score['duration_seconds']
    command=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
             '-s','640x360','-r','10','-i','-',
             '-i',str(ROOT/'assets/ui/title/eldenmere_theme.ogg'),
             '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',
             '-c:a','aac','-b:a','160k','-shortest','-movflags','+faststart',
             str(OUTPUT/'title_with_music.mp4')]
    encoder=subprocess.Popen(command,stdin=subprocess.PIPE)
    try:
        for index in range(math.ceil(duration*10)):
            game.update(.1,(0,0),False);game.draw()
            encoder.stdin.write(pygame.image.tobytes(game.window,'RGB'))
            if index==10:
                pygame.image.save(game.window,str(OUTPUT/'title_screen.png'))
        encoder.stdin.close()
        if encoder.wait()!=0:raise RuntimeError('Title preview video encoding failed')
        # Water close-up: same shipped water layer over the original scenery.
        # All pixels outside that layer remain constant for clear inspection.
        frames=[]
        for index in range(24):
            scene=game.title.background.copy()
            game.title.water.draw(scene,index*.1)
            image=Image.frombytes('RGB',(640,360),pygame.image.tobytes(scene,'RGB'))
            image=image.crop((65,268,320,360)).resize((765,276),Image.Resampling.NEAREST)
            frames.append(image)
        sample=Image.new('RGB',(765,276*len(frames)))
        for i,frame in enumerate(frames):sample.paste(frame,(0,i*276))
        palette=sample.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
        indexed=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
        indexed[0].save(OUTPUT/'water_closeup.gif',save_all=True,append_images=indexed[1:],
                        duration=100,loop=0,disposal=2,optimize=False)
        print(f'Captured {duration:.2f}s title video with full music and a looping water close-up.')
    finally:
        if encoder.poll() is None:encoder.kill();encoder.wait()
        pygame.quit()


if __name__=='__main__':capture()
