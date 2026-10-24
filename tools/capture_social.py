"""Capture a real approach, safe work interruption, dialogue and re-approach."""
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
from PIL import Image
import pygame

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import main

OUTPUT=ROOT/'docs/reviews/proximity_dialogue'


def capture():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    game=main.Game(fullscreen=False,start_on_title=False)
    actor=game.persistent_npcs[0]
    game.world=game._scene_by_id('sanctuary_dining')
    actor.select_step('sort_provisions')
    actor.state_ms=1100 # Deliberately approach while Serene holds a jar.
    game.player.position.update(288,258)
    game.player.facing='back'
    frames=[]
    events=[]
    ticks=0

    def run(count,direction=(0,0)):
        nonlocal ticks
        for _ in range(count):
            game.handle_events()
            game.update(1/60,direction,False)
            if ticks%6==0:
                game.draw()
                frames.append(Image.frombytes('RGB',main.VIEW_SIZE,pygame.image.tobytes(game.canvas,'RGB')))
            ticks+=1

    def click():
        # Window corner outside the textbox proves click-anywhere behavior.
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(950,10)))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=(950,10)))
        game.handle_events()
        events.append({'at_ms':round(ticks*1000/60),'input':'left click at window corner',
                       'conversation_open':game.social.active,'page':game.social.page_index})

    run(30)
    for _ in range(120):
        run(1,(0,-1))
        if game.social.locked:break
    events.append({'at_ms':round(ticks*1000/60),'event':'proximity requested conversation'})
    for _ in range(300):
        run(1)
        if game.social.active:break
    if not game.social.active:raise AssertionError('Approach failed to open dialogue')
    events.append({'at_ms':round(ticks*1000/60),'event':'jar safely returned; dialogue opened'})
    game.draw()
    pygame.image.save(game.window,str(OUTPUT/'serene_dialogue.png'))
    for _ in range(3):
        run(150)
        click()
    run(60) # Remain close: dialogue must stay closed while work resumes.
    if game.social.locked:raise AssertionError('Conversation immediately repeated')
    run(45,(0,1))
    for _ in range(120):
        run(1,(0,-1))
        if game.social.locked:break
    for _ in range(300):
        run(1)
        if game.social.active:break
    if not game.social.active or game.social.conversation['id']!='serene_repeat':
        raise AssertionError('Re-approach did not select repeat conversation')
    run(150)
    game.draw()
    pygame.image.save(game.window,str(OUTPUT/'serene_repeat.png'))
    # One palette across the entire capture prevents frame-to-frame drift.
    sample=Image.new('RGB',(480,320*len(frames[::10])))
    for index,frame in enumerate(frames[::10]):sample.paste(frame,(0,index*320))
    palette=sample.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    indexed=[frame.quantize(palette=palette,dither=Image.Dither.NONE).resize((960,640),Image.Resampling.NEAREST)
             for frame in frames]
    indexed[0].save(OUTPUT/'serene_social.gif',save_all=True,append_images=indexed[1:],
                    duration=100,loop=0,disposal=2,optimize=False)
    with Image.open(OUTPUT/'serene_social.gif') as gif:
        for index in range(gif.n_frames):
            gif.seek(index)
            assert gif.tile[0][1]==(0,0,960,640)
            assert gif.disposal_method==2
    (OUTPUT/'capture.json').write_text(json.dumps({'source':'main.Game, real update/draw and posted mouse events',
                                                 'fps':10,'scale':2,'events':events},indent=2)+'\n')
    pygame.quit()
    print(f'Captured {len(frames)} frames; approach, safe handoff, 3 dialogue pages, resumption, repeat.')


if __name__=='__main__':capture()
