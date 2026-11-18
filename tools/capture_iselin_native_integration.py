"""Capture the integrated native actor through real game/controller paths.

Travel stations and selected Gallery shots are labelled review fixtures.
All saves/settings are temporary; no complete played quest is claimed.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

import pygame
from PIL import Image,ImageDraw,ImageFont
from cutscene_gallery import _regent_checkpoint,_station
from save_game import SaveStore
from tools.capture_iselin_native_front_walk import gif,labelled
from tools.capture_sanctuary_rescue import make_game,seed_victory,press

OUT=ROOT/'docs/reviews/iselin_native_integration'
DIRECTIONS=('front','left','right','back')
ROUTES={'front':((384,432),(384,598)), 'left':((550,480),(384,480)),
        'right':((384,480),(550,480)), 'back':((384,598),(384,432))}


def approved_assets():
    baseline=json.loads((OUT/'approved_assets.json').read_text())
    for path,digest in baseline['sha256'].items():
        assert sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    return baseline


def native(actor):
    assert actor.draw_anchor==(12,30)
    assert set(actor.idles)==set(DIRECTIONS)
    assert set(actor.walks)==set(DIRECTIONS)
    assert not callable(getattr(actor,'detailed_sprite',None))
    for direction in DIRECTIONS:
        assert actor.idles[direction].get_size()==(24,36)
        assert actor.walk_durations[direction]==(35,)*16
        assert all(frame.get_size()==(24,36) for frame in actor.walks[direction])


def image(game):
    game.draw()
    return Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB'))


def save_frame(game,output,name,records,fixture,**facts):
    filename=name+'.png'
    image(game).save(output/filename)
    records.append({'file':filename,'fixture':fixture,**facts})


def stop(game):
    game.opening_audio.reset();game.regional_audio.reset()
    game.music.stop();pygame.quit()


def travel(output,directory,records):
    game=make_game(directory,seed=False,embedded=False)
    observations={}
    try:
        actor=game.regent_quest.iselin
        native(actor)
        for visitor in game.regent_quest.actors.values():visitor.story_visible=False
        game.world=game.town;game.opening_fade=0
        for direction,(start,goal) in ROUTES.items():
            horizontal=start[1]==goal[1]
            game.player.position.update((550,432) if horizontal else (432,598))
            game.player.facing=direction;game.player.moving=game.player.running=False
            mira=game.mill_quest.mira;mira.quest_mode=True;mira.moving=False
            mira.position.update((550,528) if horizontal else (336,598));mira.facing=direction
            mira.end_conversation()
            game.regent_quest._place(actor,game.town,start)
            actor.story_visible=True;actor.facing=direction;actor.walk_ms=0
            game.camera.reset();game.camera.focus(((start[0]+goal[0])/2,(start[1]+goal[1])/2),duration=0)
            samples=[];frames=[]
            avoid=game.world.probe_rect(game.player.position)
            for phase,count,destination in (('IDLE',8,start),('WALK',64,goal),('STOP',8,goal)):
                for _ in range(count):
                    game.regent_quest._move(actor,destination,.035,74)
                    assert actor.moving==(phase=='WALK'),(direction,phase)
                    assert actor.facing==direction
                    assert game.world.can_stand(actor.position,actor.probe_size,actor,avoid)
                    frame=image(game)
                    assert not game.canvas.patches
                    index=len(samples)
                    samples.append({'phase':phase,'sample':index,'position':list(actor.position),
                                    'walk_ms':actor.walk_ms,'moving':actor.moving,
                                    'frame_sha256':sha256(pygame.image.tobytes(actor.sprite(0),'RGBA')).hexdigest()})
                    crop=(240,120,720,500) if horizontal else (240,0,720,560)
                    frames.append(labelled(frame.crop(crop),f'LIVE ISELIN / {direction.upper()} / {phase}',
                                           'Game.draw + RegentQuest._move; staged clear route.'))
                    if index==39:frame.save(output/f'travel_{direction}.png')
            gif(output/f'travel_{direction}.gif',frames,[30,40]*40)
            observations[direction]={'route_start':start,'route_goal':goal,'samples':samples,
                                     'gif_ms':2800,'native_override':False}
        # Use the real Game pause path, then the real Regent conversation owner.
        before=(tuple(actor.position),actor.walk_ms)
        game.pause.open();game.update(.25,(0,0),False)
        assert (tuple(actor.position),actor.walk_ms)==before
        save_frame(game,output,'pause',records,'Game pause freezes the actual live actor.')
        game.pause.close()
        for offset in ((28,28),(-28,28),(0,36)):
            position=actor.position+offset
            if game.world.can_stand(position):game.player.position.update(position);break
        else:raise AssertionError('No clear dialogue inspection station')
        assert game.regent_quest._speak('iselin_after')
        game.camera.focus((actor.position+game.player.position)/2,duration=0)
        save_frame(game,output,'conversation',records,'Actual Regent dialogue fixture; no objective callback.')
        game.social.cancel_script();game.regent_quest.on_dialogue_cancelled('regent_iselin_after')
    finally:stop(game)
    return observations


def meal(output,directory,records):
    game=make_game(directory,seed=False,embedded=False)
    try:
        _regent_checkpoint(game,'welcome')
        owner=game.regent_quest;actor=owner.iselin
        _station(game,owner.dining,(184,252),'back')
        record=owner.points['meal_seats']['iselin']
        owner._place(actor,owner.dining,record['approach']);owner._meal_ready=True
        game.camera.reset()
        owner.scene_actions._meal_clock=.1;owner.scene_actions._apply_seating()
        assert actor.facing=='left' and actor.story_sprite.get_size()==(24,36)
        save_frame(game,output,'meal_approach',records,'Actual native dining action at100ms.')
        owner.scene_actions._meal_clock=1;owner.scene_actions._apply_seating()
        assert actor.story_sprite.get_size()==(24,36)
        assert not hasattr(actor,'story_detail')
        save_frame(game,output,'meal_seated',records,'Actual seated action; native left profile.',
                   anchor=list(actor.story_draw_anchor),sprite_size=list(actor.story_sprite.get_size()))
        owner.scene_actions.release()
        assert not hasattr(actor,'story_sprite')
        native(actor)
        save_frame(game,output,'meal_released',records,'Actual action.release restores ordinary native idle.')
    finally:stop(game)


def gallery(output,directory,records):
    game=make_game(directory,seed=False,embedded=False,title=True)
    try:
        assert game.open_gallery()
        assert game.launch_gallery_scene('regent_arrival'),game.gallery.error
        child=game.gallery_session.game;scene=child.regent_arrival
        for name,seconds in (('aerial_gate',4),('gate_greeting',1),('gate_admission',2),
                             ('relief',1),('town_parking',2)):
            scene.phase_index=next(i for i,p in enumerate(scene.data['phases']) if p['id']==name)
            scene.phase_time=seconds;scene.dialogue_index=scene.page_index=0
            save_frame(game,output,'arrival_'+name,records,'Production Gallery renderer; explicitly selected authored shot.',
                       shot=name,phase_seconds=seconds)
        scene.phase_index=next(i for i,p in enumerate(scene.data['phases']) if p['id']=='gate_admission')
        actor=next(a for a in scene.phase['actors'] if a['id']=='iselin')
        start=None
        for index in range(800):
            seconds=index/60;scene.phase_time=seconds
            if scene.actor_pose(actor)!='walk_left_back':continue
            scene.phase_time=seconds+.56
            if scene.actor_pose(actor)=='walk_left_back':start=seconds;break
        assert start is not None,'No complete diagonal cycle in authored gate travel'
        frames=[]
        for index in range(16):
            scene.phase_time=start+index*.035
            assert scene.actor_pose(actor)=='walk_left_back'
            frames.append(image(game))
        gif(output/'arrival_diagonal.gif',frames,[30,40]*8)
        before=(scene.phase_index,scene.phase_time,scene.elapsed)
        scene.paused=True;child.update(.25,(0,0),False)
        assert (scene.phase_index,scene.phase_time,scene.elapsed)==before
        save_frame(game,output,'arrival_paused',records,'Actual Gallery/scene pause freezes its authored clock.')
        scene.paused=False;scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        child.update(.25,(0,0),False)
        assert (scene.phase_index,scene.phase_time,scene.elapsed)==before
        scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        game.gallery_session.close()
        assert game.launch_gallery_scene('sanctuary_arrival'),game.gallery.error
        for _ in range(20):game.update(.05,(0,0),False)
        child=game.gallery_session.game
        clone=child.sanctuary_arrival.actors['iselin'];native(clone)
        save_frame(game,output,'sanctuary_clone',records,'Production Sanctuary Gallery after1s of ordinary updates.',
                   frame_size=list(clone.sprite(0).get_size()),anchor=list(clone.draw_anchor))
        game.gallery_session.close()
    finally:stop(game)


def continue_and_report(output,directory,records):
    path=Path(directory)/'journey.json'
    payload=json.loads((OUT/'legacy_escorting_save.json').read_text())
    assert SaveStore(path).write(payload)
    game=make_game(directory,seed=False,embedded=False,title=True)
    try:
        assert game.begin_journey(True),game.save_error
        assert game.regent_quest.stage=='escorting'
        assert game.quests.to_dict()==payload['quests']
        native(game.regent_quest.iselin)
        game.opening_fade=0;game.camera.focus(game.regent_quest.iselin.position,duration=0)
        save_frame(game,output,'continue_legacy',records,'Actual Continue from pre-integration saved journey; camera staged on restored actor.',
                   stage=game.regent_quest.stage,quest_facts_preserved=True)
    finally:stop(game)
    game=make_game(directory,embedded=False)
    try:
        seed_victory(game);game.sanctuary_rescue.restore({'version':1,'stage':'evacuated'})
        game.sanctuary_cave.lucan_departed=True;game._sync_story_party()
        game.world=game._scene_by_id('elden_vale_sanctuary')
        owner=game.regent_quest
        assert owner.resolution.commit('resolution_report');owner._setup_stage()
        game.player.position.update(game.overworld_travel._landing(game.world,owner.iselin.position+pygame.Vector2(0,30)))
        assert owner.resolution.interact()
        save_frame(game,output,'post_rescue_report',records,'Seeded victory/evacuation; actual native report dialogue.')
        for _ in range(300):
            if not game.social.active:break
            press(game);game.social.update((0,0))
        assert owner.stage=='resolution_return'
        assert game._validate_journey(game.journey_snapshot()) is not None
    finally:stop(game)


def diagonal_board(output):
    folder=ROOT/'assets/story/regent_arrival/actors/iselin'
    manifest=json.loads((folder/'animation.json').read_text())
    frames=manifest['loops']['walk_left_back']
    board=Image.new('RGB',(704,932),'#e8edf2');draw=ImageDraw.Draw(board)
    font=ImageFont.truetype(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'),15)
    draw.text((12,10),'EXPORTED CINEMATIC DIAGONAL / ANATOMY INSPECTION',font=font,fill='#263c35')
    hashes={}
    for index,record in enumerate(frames):
        path=folder/record['file'];sprite=Image.open(path).convert('RGBA')
        x=12+(index%4)*174;y=42+(index//4)*220
        draw.text((x,y),f'{index+1:02}',font=font,fill='#263c35')
        enlarged=sprite.resize((160,192),Image.Resampling.NEAREST)
        board.paste(enlarged,(x,y+20),enlarged)
        hashes[str(path.relative_to(ROOT))]=sha256(path.read_bytes()).hexdigest()
    board.save(output/'scene_diagonal_frames.png')
    return {'file':'scene_diagonal_frames.png',
            'fixture':'Numbered exported cinematic drawings, enlarged2x; anatomy inspection independent of horse occlusion. Not a gameplay screenshot.',
            'source_sha256':hashes}


def capture(output=OUT):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    baseline=approved_assets();records=[]
    with tempfile.TemporaryDirectory(prefix='iselin-native-integration-') as directory:
        directory=Path(directory)
        travel_records=travel(output,directory/'travel',records)
        meal(output,directory/'meal',records)
        gallery(output,directory/'gallery',records)
        continue_and_report(output,directory/'continue',records)
    records.append(diagonal_board(output))
    approved_assets()
    metadata={'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'renderer':'Production Game.draw, Gallery and World controllers; fixture boundaries named per record.',
              'persistence':'Temporary save/settings only. No full played battle/road/quest walkthrough claimed.',
              'approved_pngs_preserved':len(baseline['sha256']),'frames':records,'travel':travel_records,
              'output_sha256':{p.name:sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())
                               if p.suffix in ('.png','.gif')}}
    (output/'capture.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print('Captured integrated native actor travel, lifecycle, scene views and pre-integration Continue.')
    return metadata


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    capture(parser.parse_args().out)
