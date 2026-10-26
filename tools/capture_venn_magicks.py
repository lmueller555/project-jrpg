"""Capture the real failed spell, acknowledgment and practical fallback.

Only quest delivery/inspection prerequisites and the user's choice are seeded.
The game owns all animation, failure, dialogue and repair transitions. Review
labels sit above a nearest-neighbor crop of the real runtime world renderer.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
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
LABELS={'raise_hand':'Raise a bent arm; body stays in its normal stance',
        'attempt':'A small spark gathers; the water does not move',
        'fizzle':'The weak spell flickers out; the gate remains jammed',
        'recover':'Lower the arm and return to idle',
        'align_pin':'Approach the gate',
        'work_pin':'Use the borrowed mallet to free the pin',
        'align_channel':'Walk along the bank to the debris',
        'clear_channel':'Use the clearing hook to pull out the twigs',
        'return_pin':'Return to the gate with the borrowed tools',
        'open':'Raise the gate with the lifting hook',
        'finish':'Water flows only after the tool repair',
        None:'The channel is repaired; return to the family'}

def capture():
    OUT.mkdir(parents=True,exist_ok=True)
    # Remove review stills from the superseded successful-spell sequence.
    for name in ['ease_water','hold_water','work_pin','open','release_water','withdraw_hand','finish']:
        (OUT/(name+'.png')).unlink(missing_ok=True)
    g=Game(fullscreen=False,start_on_title=False,save_path=None)
    g.audio.set_music(0);g.audio.set_effects(0)
    g.accept_quest(OPENING_QUEST);g.quests.complete_objective(OPENING_QUEST,'halden')
    g._sync_inventory();g.halden_visit.restore();g.deliver_quest_item(OPENING_QUEST,'venn','venn')
    v=g.venn_visit;v.inspected={'pin','channel'}
    g.world=g.town;g.player.position.update(PIN_APPROACH);g.player.facing='right'
    g.opening_fade=0;g.camera.reset();g.quest_ui.reset();g.quests.drain_events()
    assert v._select_method('magicks')
    frames=[];stages={};dialogue_time=0.;dialogue_seen=False
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
    crop=(1384,608);size=(104,144)
    def frame():
        canvas=pygame.Surface(size);g.town.draw(canvas,crop,g.player,g.elapsed_ms,include_ui=False)
        native=Image.frombytes('RGB',size,pygame.image.tobytes(canvas,'RGB'))
        out=Image.new('RGB',(624,916),'#e8edf2')
        out.paste(native.resize((624,864),Image.Resampling.NEAREST),(0,52))
        d=ImageDraw.Draw(out)
        d.text((12,8),'VENN IRRIGATION / FAILED SPELL AND TOOLS',font=font,fill='#243529')
        line=('Caelan: '+v.lines['magicks_failed'][0]['text'] if g.social.script_identifier=='venn_magicks_failed' else LABELS[v.phase])
        d.text((12,29),line,font=font,fill='#243529')
        return out
    for tick in range(1200):
        g.update(1/60,(0,0),False)
        if g.social.script_identifier=='venn_magicks_failed':
            assert not v.repaired and not v.flowing and not v.debris_cleared
            dialogue_seen=True;dialogue_time+=1/60
            if 'failure_dialogue' not in stages:
                stages['failure_dialogue']=frame()
                g.camera.reset();g.draw()
                pygame.image.save(g.ui_surface,OUT/'failure_dialogue_full.png')
            if dialogue_time>=2.2:g.social.advance();dialogue_time=0.
        if tick%5==0:
            im=frame();frames.append(im)
            if v.phase in v.magick_art.poses and v.phase_time>v.magick_art.duration(v.phase)*.45:
                stages.setdefault(v.phase,im)
            if v.action_method=='tools' and v.phase in ['work_pin','clear_channel','open'] and v.phase_time>.55:
                stages.setdefault('tools_'+v.phase,im)
        if v.repaired and v.action is None:
            for _ in range(12):g.update(1/12,(0,0),False);frames.append(frame())
            break
    assert dialogue_seen and v.magicks_failed and v.method=='magicks'
    assert v.repaired and v.action is None
    assert g.quests.objective_status(OPENING_QUEST,'venn')=='active'
    for name,im in stages.items():im.save(OUT/(name+'.png'))
    # Include every stage in palette generation so the brief blue flash survives.
    samples=list(stages.values())+[frames[0],frames[-1]]
    palette_source=Image.new('RGB',(624*len(samples),916))
    for i,im in enumerate(samples):palette_source.paste(im,(624*i,0))
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
    pygame.quit();print(len(frames),'real-game frames captured; failed spell, line and tools fallback verified')

if __name__=='__main__':capture()
