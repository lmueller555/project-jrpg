"""Capture the real report/arrival/handoff after seeding completed household tasks."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from PIL import Image
from main import Game
from quests import OPENING_QUEST
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/reviews/opening_conclusion'

def capture():
    OUT.mkdir(parents=True,exist_ok=True)
    g=Game(fullscreen=False,start_on_title=False,save_path=None)
    g.audio.set_music(0);g.audio.set_effects(0)
    g.accept_quest(OPENING_QUEST)
    for household in ('halden','elira','venn'):g.quests.complete_objective(OPENING_QUEST,household)
    g._sync_inventory();g.halden_visit.restore();g.elira_visit.restore();g.venn_visit.restore()
    c=g.opening_conclusion;s=c.serene
    c._place(s,c.hall,(184,230));s.select_step('move_to_hall_table',position=(184,230),scene_id='sanctuary_hall')
    g.world=c.hall;g.player.position.update(184,258);g.player.facing='back'
    g.quest_ui.reset();g.quests.drain_events();g.camera.reset();frames=[]
    def tick(seconds=.12):
        g.update(seconds,(0,0),False);g.draw()
        frames.append(Image.frombytes('RGB',g.window.get_size(),pygame.image.tobytes(g.window,'RGB')))
    def read():
        for _ in range(100):
            if not g.social.active:return
            for _ in range(8):tick()
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE,repeat=False));g.handle_events()
        raise RuntimeError('Unfinished review dialogue')
    g.update(.1,(0,-1),False)
    for _ in range(100):
        if g.social.active:break
        g.update(.04,(0,-1),False)
    assert g.social.active
    g.draw();pygame.image.save(g.window,str(OUT/'report.png'));read()
    for _ in range(300):
        if c.stage=='waiting':break
        tick()
    assert c.stage=='waiting'
    tick();g.draw();pygame.image.save(g.window,str(OUT/'arrival.png'));read()
    assert c.stage=='done'
    for _ in range(48):tick()
    g.draw();pygame.image.save(g.window,str(OUT/'mira_objective.png'))
    palette_source=Image.new('RGB',(frames[0].width*3,frames[0].height))
    for i,frame in enumerate((frames[0],frames[len(frames)//2],frames[-1])):palette_source.paste(frame,(i*frame.width,0))
    palette=palette_source.quantize(colors=256)
    indexed=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(OUT/'conclusion.gif',save_all=True,append_images=indexed[1:],duration=120,loop=0,disposal=1,optimize=False)
    with Image.open(OUT/'conclusion.gif') as decoded:
        elapsed=0
        for index in range(decoded.n_frames):
            decoded.seek(index)
            source_index=round(elapsed/120)
            assert decoded.convert('RGB').tobytes()==indexed[source_index].convert('RGB').tobytes()
            elapsed+=decoded.info['duration']
        assert elapsed==len(indexed)*120
    pygame.quit();print(f'{len(frames)} real-game frames captured in {OUT}')
if __name__=='__main__':capture()
