"""Capture the actual gate repair, with only quest prerequisites seeded."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from PIL import Image,ImageDraw,ImageFont
from main import Game
from quests import OPENING_QUEST
from venn_visit import PIN_APPROACH
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/reviews/venn_magicks'
LABELS={'align_pin':'Approach the gate','raise_hand':'Raise the casting hand','ease_water':'Draw existing water upstream',
 'hold_water':'Hold the water aside','work_pin':'Hold with one hand, straighten the pin with the other',
 'open':'Keep the water held while lifting the gate','release_water':'Release the flow and wash the twigs downstream',
 'finish':'Lower the hand and relax',None:'Water flows through the repaired channel'}
def capture():
    OUT.mkdir(parents=True,exist_ok=True)
    g=Game(fullscreen=False,start_on_title=False,save_path=None);g.audio.set_music(0);g.audio.set_effects(0)
    g.accept_quest(OPENING_QUEST);g.quests.complete_objective(OPENING_QUEST,'halden')
    g._sync_inventory();g.halden_visit.restore();g.deliver_quest_item(OPENING_QUEST,'venn','venn')
    v=g.venn_visit;v.inspected={'pin','channel'};g.world=g.town;g.player.position.update(PIN_APPROACH)
    g.player.facing='right';g.quest_ui.reset();g.quests.drain_events()
    assert v._select_method('magicks')
    frames=[];stages={};font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
    crop=(1384,608);size=(104,144)
    def frame():
        canvas=pygame.Surface(size);g.town.draw(canvas,crop,g.player,g.elapsed_ms,include_ui=False)
        native=Image.frombytes('RGB',size,pygame.image.tobytes(canvas,'RGB'))
        out=Image.new('RGB',(624,916),'#e8edf2');out.paste(native.resize((624,864),Image.Resampling.NEAREST),(0,52))
        d=ImageDraw.Draw(out);d.text((12,8),'VENN IRRIGATION / MAGICK REPAIR',font=font,fill='#243529')
        d.text((12,29),LABELS[v.phase],font=font,fill='#243529')
        return out
    for tick in range(900):
        g.update(1/60,(0,0),False)
        if tick%5==0:
            im=frame();frames.append(im)
            if v.phase in v.magick_art.poses and v.phase not in stages and v.phase_time>v.magick_art.duration(v.phase)*.6:stages[v.phase]=im
        if v.action is None:
            for _ in range(12):g.update(1/12,(0,0),False);frames.append(frame())
            break
    assert v.repaired and v.action is None
    for name,im in stages.items():im.save(OUT/(name+'.png'))
    palette_source=Image.new('RGB',(624*3,916))
    for i,im in enumerate([frames[0],frames[len(frames)//2],frames[-1]]):palette_source.paste(im,(624*i,0))
    palette=palette_source.quantize(colors=256)
    indexed=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    for name,rate in [('repair.gif',80),('repair-slow.gif',200)]:
        indexed[0].save(OUT/name,save_all=True,append_images=indexed[1:],duration=rate,loop=0,disposal=1,optimize=False)
        with Image.open(OUT/name) as gif:
            elapsed=0
            for i in range(gif.n_frames):
                gif.seek(i);source=round(elapsed/rate)
                assert gif.convert('RGB').tobytes()==indexed[source].convert('RGB').tobytes()
                elapsed+=gif.info['duration']
            assert elapsed==rate*len(indexed)
    pygame.quit();print(len(frames),'real-game frames captured')
if __name__=='__main__':capture()
