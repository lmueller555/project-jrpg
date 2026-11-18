"""Capture the live Caelan travel bank and production world rendering for review.

The clocks below seek the actual Player.sprite() selector. World stills use the
production town/cave renderer with a staged, passive Mira travel actor. These
are isolated art studies, not claimed quest playthroughs or collision tests.
"""
from __future__ import annotations

from hashlib import sha256
import json
from math import lcm
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFont, ImageSequence

from main import Game, camera_for
from party_travel import _TravelActor

OUT=ROOT/'docs/reviews/caelan_overworld_refresh'
SOURCE=ROOT/'assets/source/characters/caelan/overworld_refresh'
BASE=ROOT/'assets/characters/caelan'
DIRECTIONS=('front','back','left','right')
BG='#e8edf2'
INK='#26343e'
MUTED='#536674'
FONT=ROOT/'assets/ui/fonts/DejaVuSans.ttf'


def font(size=17):return ImageFont.truetype(str(FONT),size)


def digest(path):return sha256(path.read_bytes()).hexdigest()


def native_image(surface):
    return Image.frombytes('RGBA',surface.get_size(),pygame.image.tobytes(surface,'RGBA'))


def runtime_frame(game,direction,gait,clock=0):
    player=game.player
    player.facing=direction
    player.moving=gait!='idle'
    player.running=gait=='run'
    player.walk_ms=clock
    return native_image(player.sprite())


def paste_sprite(card,image,center,baseline,scale):
    enlarged=image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST)
    card.paste(enlarged,(round(center-image.width*scale/2),round(baseline-34*scale)),enlarged)


def standing(game):
    card=Image.new('RGB',(960,650),BG);draw=ImageDraw.Draw(card)
    draw.text((22,15),'CAELAN / OVERWORLD REDRAW',font=font(24),fill=INK)
    draw.text((22,49),'Existing design, refined profiles and materials — actual 24 × 36 game sprites',font=font(16),fill=MUTED)
    draw.text((20,122),'Before',font=font(18),fill=INK)
    draw.text((20,368),'Updated',font=font(18),fill=INK)
    for index,direction in enumerate(DIRECTIONS):
        x=220+index*205
        draw.text((x,83),direction.capitalize(),font=font(17),fill=INK,anchor='mt')
        old=Image.open(SOURCE/'legacy'/f'idle_{direction}.png').convert('RGBA')
        current=runtime_frame(game,direction,'idle')
        for y,image in ((321,old),(566,current)):
            draw.line((x-77,y,x+77,y),fill='#b7c2ca',width=1)
            paste_sprite(card,image,x,y,6)
        card.paste(current,(x-12,600),current)
    draw.text((20,606),'Native size',font=font(15),fill=MUTED)
    card.save(OUT/'standing.png')


def travel(game):
    duration=lcm(4*140,4*100)
    frames=[]
    for clock in range(0,duration,20):
        card=Image.new('RGB',(900,780),BG);draw=ImageDraw.Draw(card)
        draw.text((22,14),'CAELAN / LIVE TRAVEL FRAMES',font=font(22),fill=INK)
        draw.text((22,43),'Walking: 140 ms per pose   ·   Running: 100 ms per pose',font=font(16),fill=MUTED)
        for col,label in enumerate(('Idle','Walk','Run')):
            draw.text((190+col*285,76),label,font=font(18),fill=INK,anchor='mt')
        for row,direction in enumerate(DIRECTIONS):
            baseline=256+row*170
            draw.text((16,baseline-110),direction.capitalize(),font=font(17),fill=INK)
            for col,gait in enumerate(('idle','walk','run')):
                x=190+col*285
                draw.line((x-83,baseline,x+83,baseline),fill='#b7c2ca',width=1)
                paste_sprite(card,runtime_frame(game,direction,gait,clock),x,baseline,4)
        frames.append(card)
    frames[0].save(OUT/'travel.png')
    # A shared palette avoids per-frame quantization changes in the still skin/hair.
    palette_board=Image.new('RGB',(900*4,780))
    for i,clock in enumerate((0,140,280,420)):
        palette_board.paste(frames[clock//20],(i*900,0))
    palette=palette_board.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    indexed=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(OUT/'travel.gif',save_all=True,append_images=indexed[1:],duration=20,loop=0,disposal=1,optimize=False)
    with Image.open(OUT/'travel.gif') as gif:
        total=sum(frame.info['duration'] for frame in ImageSequence.Iterator(gif))
    assert total==duration,(total,duration)
    sheet=Image.new('RGB',(24*5*9,36*5*4+28*4+45),BG);draw=ImageDraw.Draw(sheet)
    draw.text((12,8),'All 36 runtime travel drawings',font=font(20),fill=INK)
    for row,direction in enumerate(DIRECTIONS):
        names=[('idle',0)]+[(gait,phase) for gait in ('walk','run') for phase in range(4)]
        for col,(gait,phase) in enumerate(names):
            x=col*120;y=45+row*208
            label=direction+' '+gait+(' '+str(phase+1) if gait!='idle' else '')
            draw.text((x+3,y),label,font=font(12),fill=INK)
            image=runtime_frame(game,direction,gait,phase*(140 if gait=='walk' else 100))
            image=image.resize((120,180),Image.Resampling.NEAREST)
            sheet.paste(image,(x,y+22),image)
    sheet.save(OUT/'native_contact_sheet.png')
    return duration


def find_pair(world,point):
    offsets=sorted(((dx,dy) for dy in range(-80,81,8) for dx in range(-80,81,8)),key=lambda p:p[0]**2+p[1]**2)
    for dx,dy in offsets:
        leader=(point[0]+dx,point[1]+dy)
        follower=(leader[0]+32,leader[1]+4)
        if world.can_stand(leader) and world.can_stand(follower):return leader,follower
    raise ValueError('No valid nearby art-review pair station')


def world_still(game,world,label,direction,point):
    leader,mira_position=find_pair(world,point)
    game.player.position.update(leader)
    game.player.moving=game.player.running=False
    game.player.facing=direction
    mira=_TravelActor('mira');mira.position.update(mira_position);mira.facing=direction;mira.visible=True
    camera=camera_for(game.player.position,world.size)
    world.draw(game.canvas,camera,game.player,1500,include_ui=False,party_actors=(mira,))
    image=native_image(game.canvas).convert('RGB')
    card=Image.new('RGB',(960,900),BG);draw=ImageDraw.Draw(card)
    draw.text((18,9),label+' / production renderer, current Caelan and Mira',font=font(20),fill=INK)
    card.paste(image.resize((960,640),Image.Resampling.NEAREST),(0,40))
    x=round((leader[0]+mira_position[0])/2-camera[0]);y=round(leader[1]-camera[1])
    box=(x-48,y-40,x+48,y+8)
    crop=image.crop(box).resize((384,192),Image.Resampling.NEAREST)
    card.paste(crop,(20,692))
    for i,line in enumerate(('4× crop of the same lit native pixels.', 'No character scaling changes in gameplay.', 'Staged positions; existing collision and lighting.', 'Caelan with current Mira.')):
        draw.text((420,712+i*28),line,font=font(16),fill=MUTED)
    return card,dict(scene=world.data['id'],direction=direction,player=list(leader),mira=list(mira_position),camera=list(camera),clock_ms=1500)


def action_sheet():
    records=[('Breakfast seated','assets/story/sanctuary_opening/poses/caelan_seated.png'),
             ('Breakfast standing','assets/story/sanctuary_opening/poses/caelan_stand/frame_04.png'),
             ('Carrying','assets/story/halden/caelan/hold_left.png'),
             ('Pickup contact','assets/story/halden/caelan/lift_back_2.png'),
             ('Handover','assets/story/venn/caelan/give_right.png'),
             ('Bench sitting','assets/characters/caelan/participation_sit_front.png')]
    card=Image.new('RGB',(960,420),BG);draw=ImageDraw.Draw(card)
    draw.text((18,12),'CAELAN / SCOPED WORLD POSES',font=font(22),fill=INK)
    draw.text((18,44),'Runtime pose samples; full action/prop sequencing is reviewed separately.',font=font(15),fill=MUTED)
    for i,(label,path) in enumerate(records):
        image=Image.open(ROOT/path).convert('RGBA')
        # Keep a constant image scale; crop transparent padding for the card only.
        image=image.crop(image.getbbox())
        image=image.resize((image.width*5,image.height*5),Image.Resampling.NEAREST)
        x=80+i*160
        card.paste(image,(round(x-image.width/2),110),image)
        draw.text((x,329),label,font=font(14),fill=INK,anchor='mt')
    card.save(OUT/'actions.png')


def interaction_studies():
    """Seed prerequisites, then seek production owner updates and rendering."""
    from quests import OPENING_QUEST
    from cutscene_gallery import _households, _station
    from halden_visit import SOURCES
    from elira_visit import STOOL_APPROACH, TABLE_APPROACH
    from venn_visit import PIN_APPROACH
    captures=[];panels=[]
    games=[]
    def fresh():
        game=Game(window_size=(960,640),fullscreen=False,start_on_title=False,
                  _preview_window=pygame.Surface((960,640)))
        game.audio.set_music(0);game.audio.set_effects(0)
        games.append(game)
        assert not game.save_store.enabled and not game.saves.enabled
        return game
    def capture(game,owner,name,label,point=None):
        game.camera.reset();game.draw()
        camera=game.camera.position()
        point=point or getattr(game.player,'story_position',None) or game.player.position
        x,y=point[0]-camera[0],point[1]-camera[1]
        source=native_image(game.canvas).convert('RGB')
        crop=source.crop((round(x)-56,round(y)-64,round(x)+56,round(y)+32))
        card=Image.new('RGB',(352,344),BG)
        card.paste(crop.resize((336,288),Image.Resampling.NEAREST),(8,48))
        draw=ImageDraw.Draw(card)
        draw.text((10,8),label,font=font(15),fill=INK)
        draw.text((10,29),'Production owner + renderer · 3× crop',font=font(12),fill=MUTED)
        file=name+'.png';card.save(OUT/file);panels.append(card)
        captures.append(dict(file=file,scene=game.world.data['id'],owner=owner,
                             action=getattr(getattr(game,owner),'action',None),
                             phase=getattr(getattr(game,owner),'phase',None),
                             action_seconds=getattr(getattr(game,owner),'action_time',
                                                    getattr(getattr(game,owner),'phase_time',0)),
                             contact=getattr(getattr(game,owner),'contact',False),
                             logical_position=list(game.player.position),
                             drawn_position=list(getattr(game.player,'story_position',game.player.position)),
                             draw_anchor=list(getattr(game.player,'story_draw_anchor',(12,30))),
                             camera=list(camera)))
    try:
        game=fresh();h=game.halden_visit
        assert game.accept_quest(OPENING_QUEST)
        _station(game,h.home,(SOURCES[0][0],SOURCES[0][1]+18))
        assert game.deliver_quest_item(OPENING_QUEST,'halden','halden')
        h.restore();assert h.interact()
        h.update(.18);capture(game,'halden_visit','halden_lift_preparation','Halden: before pickup cue')
        h.update(.179);capture(game,'halden_visit','halden_lift_precontact','Halden: before ownership cue')
        assert h.carried is None
        h.update(.002);capture(game,'halden_visit','halden_lift_contact','Halden: pickup at contact')
        assert h.carried==0
        h.update(.4)
        for direction in ('front','back'):
            game.player.facing=direction;game.player.moving=False
            h.update(0)
            capture(game,'halden_visit','halden_carry_'+direction,'Halden: carrying '+direction)
        game=fresh();_households(game,('halden',));v=game.venn_visit
        partner=v.family['father']
        _station(game,v.home,partner.position+(0,24),'back')
        v.partner=partner;v._begin_supplies();assert v.action=='supplies'
        v.update(.3);capture(game,'venn_visit','venn_give_precontact','Venn: offering supplies')
        assert not v.contact
        v.update(.15);capture(game,'venn_visit','venn_give_contact','Venn: supplies transferred')
        assert v.contact and v.delivered
        v.update(.5)
        capture(game,'venn_visit','venn_give_recovery','Venn: handover finished')
        assert not hasattr(game.player,'story_sprite')
        game=fresh();_households(game,('halden',));v=game.venn_visit
        assert game.deliver_quest_item(OPENING_QUEST,'venn','venn')
        v.inspected={'pin','channel'}
        _station(game,game.town,PIN_APPROACH,'right')
        assert v._select_method('tools')
        v.update(0)
        for phase,dt in enumerate((.05,.2,.2,.2)):
            v.update(dt)
            capture(game,'venn_visit','venn_tools_'+str(phase),'Venn: tools phase '+str(phase+1))
        game=fresh();_households(game,('halden',));e=game.elira_visit
        assert game.deliver_quest_item(OPENING_QUEST,'elira','elira')
        _station(game,e.home,STOOL_APPROACH)
        assert e.restore({'version':1,'lantern':'shelf'})
        assert e.interact();e.update(0)
        e.update(1.1);capture(game,'elira_visit','elira_lantern_reach','Elira: reach to shelf',(154,76))
        assert e.lantern=='shelf'
        e.update(.08);capture(game,'elira_visit','elira_lantern_take','Elira: lantern acquired',(154,76))
        assert e.lantern=='carried'
        e.update(1.4)
        capture(game,'elira_visit','elira_lantern_carry','Elira: carrying lantern')
        for direction in ('front','left','right'):
            game.player.facing=direction;game.player.moving=False
            e.update(0)
            capture(game,'elira_visit','elira_lantern_carry_'+direction,'Elira: carrying '+direction)
        _station(game,e.home,TABLE_APPROACH,'front')
        assert e.interact();e.update(0);e.update(.3)
        capture(game,'elira_visit','elira_lantern_place','Elira: lower to table')
        e.update(.6);assert e.lantern=='table'
        capture(game,'elira_visit','elira_lantern_finished','Elira: deposited and released')
        assert not hasattr(game.player,'story_sprite')
    finally:
        for game in games:
            game.combat.reset();game.elemental_bosses.stop_audio();game.opening_audio.reset();game.regional_audio.reset();game.music.stop()
    board=Image.new('RGB',(352*4,344*((len(panels)+3)//4)),BG)
    for i,panel in enumerate(panels):board.paste(panel,((i%4)*352,(i//4)*344))
    board.save(OUT/'interactions.png')
    return captures


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    pygame.init();pygame.display.set_mode((960,640))
    game=Game(window_size=(960,640),fullscreen=False,start_on_title=False,_preview_window=pygame.Surface((960,640)))
    before=game._progress_signature()
    evidence={'scope':'Isolated production Player sprite selection and world-renderer stills. No quest playthrough, reward, or collision correction is claimed.','captures':[]}
    try:
        standing(game)
        evidence['travel_loop_ms']=travel(game)
        for filename,world,label,direction,point in (
            ('town.png',game.town,'Eldenmere','front',(384,344)),
            ('cave.png',game._scene_by_id('sanctuary_cave'),'Sanctuary cave','right',(456,1280))):
            card,record=world_still(game,world,label,direction,point);card.save(OUT/filename)
            evidence['captures'].append({'file':filename,**record})
        action_sheet()
        assert game._progress_signature()==before
        assert not game.save_store.enabled and not game.saves.enabled
        evidence['travel_progress_unchanged']=True
        evidence['disk_persistence_disabled']=True
        evidence['interaction_fixture_scope']='Public prerequisites are seeded in separate isolated Games, then production owners update action clocks and transfer ownership. No full quest playthrough is claimed.'
        evidence['interactions']=interaction_studies()
        paths=[ROOT/'main.py',ROOT/'party_travel.py',ROOT/'sanctuary_cave_world.py',
               SOURCE/'registration.json',SOURCE/'travel_authored.png',SOURCE/'actions_authored.png',
               Path(__file__).resolve()]
        paths+=list(BASE.glob('idle_*.png'))
        paths+=[BASE/f'{gait}_{direction}'/f'frame_{phase:02}.png' for gait in ('walk','run') for direction in DIRECTIONS for phase in range(1,5)]
        paths += [ROOT/name for name in ('halden_visit.py','venn_visit.py','elira_visit.py','tools/build_caelan_overworld.py','tools/build_caelan_overworld_dependents.py')]
        for folder in ('assets/story/halden/caelan','assets/story/venn/caelan','assets/story/elira'):
            paths += [path for path in (ROOT/folder).glob('*.png') if folder.endswith('/caelan') or path.name.startswith(('give_','hold_','carry_','step_','reach_','take_','down_','place_'))]
        paths+=list((OUT).glob('halden_*.png'))
        paths+=list((OUT).glob('elira_*.png'))
        paths+=list((OUT).glob('venn_*.png'))
        paths+=[ROOT/'assets/characters/mira'/f'idle_{direction}.png' for direction in DIRECTIONS]
        evidence['fingerprints']={path.relative_to(ROOT).as_posix():digest(path) for path in sorted(set(paths))}
        (OUT/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
        print('Captured standing, 2800 ms travel loop, all 36 frames, town/cave stills, and 20 interaction snapshots')
    finally:
        game.combat.reset();game.elemental_bosses.stop_audio();game.opening_audio.reset();game.regional_audio.reset();game.music.stop();pygame.quit()


if __name__=='__main__':main()
