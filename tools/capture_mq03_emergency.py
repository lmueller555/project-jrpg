"""Review MQ03's emergency from an explicitly labelled earlier-quest fixture.

Only completed MQ01/MQ02 and the previously seen arrival are initialized. No
MQ03 objective, stage, actor position or party membership is forged. The visit,
interruption, Mira's return and Sanctuary journey use the production game.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw

from main import Game, VIEW_SIZE, camera_for
from halden_visit import town_path
from npc_routines import find_path
from overworld_travel import TOWN_EXIT, WORLD_ID
from quests import OPENING_QUEST, MILL_QUEST, REGENT_QUEST, LANTERN_QUEST
from tools.capture_overworld_sanctuary import regional_path, frame
from tools.capture_sanctuary_reserve import path as clear_path, walk as travel_walk

OUT = ROOT/'docs/reviews/mq03_emergency'
RESERVE = 'elden_vale_sanctuary'


def digest(file):return hashlib.sha256(file.read_bytes()).hexdigest()


def source_hashes():
    names = {
        'main.py', 'regent_quest.py', 'regent_emergency.py', 'regent_actions.py',
        'regent_actors.py', 'party_state.py', 'party_travel.py', 'mill_quest.py',
        'overworld_travel.py', 'quests.py', 'save_game.py', 'social.py',
        'assets/quests/eldenmere.json', 'docs/narrative/game_01/CH01_MQ03.md',
        'tools/capture_mq03_emergency.py', 'tools/capture_overworld_sanctuary.py',
        'tools/capture_regent_quest.py',
        'tools/capture_sanctuary_reserve.py', 'assets/maps/eldenmere/playable/map.json',
        'assets/maps/elden_vale_sanctuary/map.json',
    }
    for folder in ('assets/story/regent', 'assets/story/regent_emergency',
                   'assets/source/story/regent_emergency'):
        names.update(file.relative_to(ROOT).as_posix() for file in (ROOT/folder).rglob('*') if file.is_file())
    names.update(file.relative_to(ROOT).as_posix() for file in (ROOT/'tools').glob('*regent*emergency*.py'))
    pending = [ROOT/name for name in names if (ROOT/name).is_file()]
    seen = set()
    while pending:
        file = pending.pop()
        if file in seen:continue
        seen.add(file)
        if file.suffix != '.json':continue
        def collect(value):
            if isinstance(value, dict):
                for item in value.values():collect(item)
            elif isinstance(value, list):
                for item in value:collect(item)
            elif isinstance(value, str) and value.startswith('assets/'):
                other = ROOT/value
                if other.is_file() and other not in seen:pending.append(other)
        collect(json.loads(file.read_text()))
    return {file.relative_to(ROOT).as_posix():digest(file) for file in sorted(seen)}


def earlier_quest_fixture(game):
    """Initialize only a supported legacy completed-mill journey, before MQ03."""
    assert game.accept_quest(OPENING_QUEST)
    for key in ('halden','elira','venn'):assert game.quests.complete_objective(OPENING_QUEST,key)
    game._sync_inventory()
    game.halden_visit.restore();game.elira_visit.restore();game.venn_visit.restore()
    assert game.quests.turn_in(OPENING_QUEST,'mother_serene')
    assert game.quests.unlock(MILL_QUEST)
    game.opening_conclusion.restore({'version':1,'stage':'done'})
    assert game.accept_quest(MILL_QUEST)
    for objective in game.quests.definitions[MILL_QUEST]['objectives']:
        assert game.quests.complete_objective(MILL_QUEST,objective['id'])
    assert game.quests.turn_in(MILL_QUEST,'mira_worker')
    assert game.mill_quest.restore({'version':1,'inspected':['mechanism','race','intake'],
        'prepared':True,'spell_done':True,'encouraged':True,'restored':True,
        'verified':True,'resolved':True}) is not False
    game.opening.restore({'version':1,'stage':'disabled'})
    if game.quests.status(REGENT_QUEST)=='locked':assert game.quests.unlock(REGENT_QUEST)
    game.regent_arrival.restore(None)
    game.regent_quest.restore(None)
    game._sync_story_party()
    game.world=game.town;game.player.position.update(game.town.data['spawn'])
    game.opening_fade=game.transfer_cooldown=0
    game.social.blocked.clear();game.quests.drain_events()
    assert game.quests.status(REGENT_QUEST)=='available'
    assert game.regent_quest.stage=='idle'
    assert not game.quests.states[REGENT_QUEST]['completed_objectives']
    assert game.save_progress()
    assert game._read_saved_journey() is not None,'Earlier-quest fixture must itself be valid'


class Driver:
    """Real input, movement and acknowledgement with disposable state."""
    def __init__(self, directory, *, initialize=True):
        self.directory=Path(directory)
        self.save=self.directory/'journey.json';self.settings=self.directory/'settings.json'
        self.game=self.new_game(False)
        self.observer=None
        self.transitions=[];self.stages=[];self.dialogue=[]
        if initialize:earlier_quest_fixture(self.game)

    def new_game(self,title):
        game=Game(fullscreen=False,start_on_title=title,save_path=self.save,settings_path=self.settings)
        game.audio.set_music(0);game.audio.set_effects(0);pygame.event.clear()
        return game

    @property
    def quest(self):return self.game.regent_quest

    def tick(self,seconds=.05,direction=(0,0),running=False):
        before=self.game.world.data['id']
        self.game.update(seconds,direction,running)
        after=self.game.world.data['id']
        if before!=after:self.transitions.append([before,after])
        if not self.stages or self.stages[-1]!=self.quest.stage:self.stages.append(self.quest.stage)
        if self.observer:self.observer(seconds)

    def until(self,predicate,seconds=80):
        for _ in range(round(seconds/.05)):
            if predicate():return
            self.tick()
        raise AssertionError(('Timed out',self.quest.stage,self.game.social.script_identifier,
            self.game.world.data['id'],list(self.game.player.position)))

    def read_current(self,on_page=None):
        social=self.game.social;identifier=social.script_identifier
        assert social.active,('No dialogue',self.quest.stage)
        seen=set()
        for _ in range(200):
            if not social.active or social.script_identifier!=identifier:return
            page=social.page
            assert not social.choosing,'Emergency dialogue is linear'
            key=page['source_line'],tuple(page['lines'])
            if key not in seen:
                seen.add(key)
                line=dict(social._source_lines[page['source_line']])
                self.dialogue.append({'script':identifier,'line':page['source_line'],**line})
                if on_page:on_page(identifier,line,page)
            social.advance()
        raise AssertionError(('Dialogue did not finish',identifier))

    def clear(self,world,desired):
        point=pygame.Vector2(desired)
        for radius in (0,6,12,18,24,30,36):
            for dx,dy in ((0,radius),(-radius,0),(radius,0),(0,-radius)):
                candidate=point+(dx,dy)
                if world.can_stand(candidate):return candidate
        raise AssertionError(('Blocked station',world.data['id'],list(point)))

    def walk(self,goal,*,transfer=None,running=False):
        world=self.game.world
        if world.data['id']==WORLD_ID:
            route=regional_path(world,self.game.player.position,goal)
        elif world is self.game.town and self.game.player.position.distance_to(goal)>180:
            route=town_path(world,self.game.player.position,goal,SimpleNamespace(probe_size=world.probe_size),None)
        else:route=clear_path(world,self.game.player.position,goal)
        assert route is not None,('No route',world.data['id'],list(self.game.player.position),list(goal))
        for corner in route:
            for _ in range(2400):
                if self.game.world is not world:
                    assert self.game.world.data['id']==transfer,('Unexpected transfer',self.game.world.data['id'])
                    return
                delta=pygame.Vector2(corner)-self.game.player.position
                if delta.length()<.45:break
                before=self.game.player.position.copy()
                seconds=min(.04,delta.length()/(108 if running else 72))
                self.tick(seconds,delta,running)
                assert not self.game.combat.active,'The review route entered combat'
                assert self.game.world is not world or self.game.world.can_stand(self.game.player.position)
                if self.game.player.position==before:
                    # Door fades and a queued spoken scene can briefly own input.
                    if self.game.social.active or self.quest.locks_player or self.game.opening_fade:
                        raise AssertionError(('Movement owned during route',self.quest.stage,self.game.social.script_identifier))
                    raise AssertionError(('Walking stalled',world.data['id'],list(before),list(corner)))
            else:raise AssertionError(('Walk budget',world.data['id'],corner))
        if transfer:
            door=next((door for door in world.doors
                       if pygame.Vector2(door.data['anchor']).distance_to(goal)<2),None)
            direction=(0,-1) if door and door.data['entry_side']=='north' else (0,1)
            for _ in range(50):
                if self.game.world is not world:break
                self.tick(.04,direction)
            assert self.game.world.data['id']==transfer,('Missing transfer',transfer)

    def travel(self,destination):
        if self.game.world is destination:return
        queue=deque([(self.game.world,[])]);seen={self.game.world.path};steps=None
        while queue:
            world,route=queue.popleft()
            if world is destination:steps=route;break
            for door in world.doors:
                other=self.game._load_scene(ROOT/door.data['destination'])
                if other.path not in seen:
                    seen.add(other.path);queue.append((other,route+[(door,other)]))
        assert steps is not None,('No room route',destination.data['id'])
        for door,other in steps:
            self.until(lambda:not self.game.opening_fade and not self.game.transfer_cooldown)
            self.walk(door.data['anchor'],transfer=other.data['id'])
            self.until(lambda:not self.game.opening_fade and not self.game.transfer_cooldown)

    def station(self,key):
        world=self.quest.world_for_station(key)
        self.travel(world);self.walk(self.clear(world,self.quest.points[key]))

    def interact(self,kind,on_page=None):
        self.game.social.blocked.clear()
        if not self.game.social.active:assert self.quest.interact(),('No interaction',kind,self.quest.stage)
        assert self.game.social.script_identifier=='regent_'+kind,(kind,self.game.social.script_identifier)
        self.read_current(on_page)

    def meal(self,on_page=None):
        self.station('preparations');self.interact('preparations',on_page)
        self.station('arrival')
        self.game.social.blocked.clear()
        if not self.game.social.active:assert self.quest.interact()
        assert str(self.game.social.script_identifier).startswith('regent_arrival')
        self.read_current(on_page)
        self.station('courtyard');self.until(lambda:self.quest.stage=='welcome' and self.quest._group_ready)
        self.interact('welcome',on_page)
        assert self.quest.stage=='hosted'
        self.until(lambda:self.quest._group_ready)

    def attack_report(self,on_page=None):
        self.interact('discussion',on_page)
        assert self.quest.stage=='interruption'
        self.until(lambda:self.quest.stage=='attack_report' and self.game.social.active)
        assert self.game.social.script_identifier=='regent_attack_report'

    def departure(self,on_page=None):
        if self.quest.stage=='attack_report':self.interact('attack_report',on_page)
        assert self.quest.stage=='departure'
        if not self.game.social.active:
            self.tick()
        if not self.game.social.active:self.station('aftermath')
        self.interact('departure',on_page)
        assert self.quest.stage=='rejoin_mira'

    def rejoin_mira(self,on_page=None):
        self.travel(self.game.town)
        mira=self.game.mill_quest.mira
        self.walk(self.clear(self.game.town,mira.position+(0,28)))
        self.tick(.02,mira.position-self.game.player.position)
        self.interact('mira_departure',on_page)
        assert self.quest.stage=='sanctuary_travel'

    def arrive(self):
        self.reach_reserve()
        self.until(lambda:self.quest.stage=='sanctuary_arrival_pending')
        self.until(lambda:not self.game.opening_fade and not self.game.transfer_cooldown)

    def continue_saved(self,*,settle=True):
        assert self.game.save_progress()
        self.game=self.new_game(True)
        assert self.game.has_saved_journey,'Saved emergency journey rejected'
        assert self.game.begin_journey(True),'Continue failed'
        if settle:self.until(lambda:not self.game.opening_fade and not self.game.transfer_cooldown)
        return self.game

    def reach_reserve(self):
        self.travel(self.game.town)
        self.walk(TOWN_EXIT,transfer=WORLD_ID)
        self.until(lambda:not self.game.opening_fade and not self.game.transfer_cooldown)
        world=self.game.world
        road=next(record for record in world.region['roads'] if record['id']=='sanctuary_approach')
        self.walk(world._tile_point(road['points'][0]))
        points=[world._tile_point(point) for point in road['points']]
        sample=SimpleNamespace(sample=lambda game,seconds:self.observer(seconds) if self.observer else None)
        assert travel_walk(self.game,points,WORLD_ID,transfer=RESERVE,movie=sample)
        self.transitions.append([WORLD_ID,RESERVE])
        self.tick()


class Movie:
    def __init__(self,path):
        executable=shutil.which('ffmpeg')
        if not executable:raise RuntimeError('FFmpeg is required for the review movie')
        self.frames=0;self.fps=20
        self.process=subprocess.Popen([executable,'-y','-loglevel','error','-f','rawvideo',
            '-pix_fmt','rgb24','-s','960x640','-r','20','-i','-','-an','-c:v','libx264',
            '-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],stdin=subprocess.PIPE)

    def frame(self,game):
        self.process.stdin.write(frame(game).tobytes());self.frames+=1

    def finish(self):
        self.process.stdin.close()
        assert self.process.wait()==0,'Video encoding failed'


def cast_visibility(game):
    """Count actual visible pixels, toggling one actor only for comparison."""
    world=game.world;quest=game.regent_quest
    companions=tuple(game.party_travel.actors())
    actors=[('caelan',game.player),(quest.aldric.data['id'],quest.aldric),
            (quest.lucan.data['id'],quest.lucan),(quest.clerk.data['id'],quest.clerk)]
    actors.extend((actor.identifier,actor) for actor in companions if actor.identifier=='mira')
    camera=camera_for(game.player.position,world.size)
    result={}
    for identifier,actor in actors:
        shown=pygame.Surface(VIEW_SIZE);bare=shown.copy()
        world.draw(shown,camera,game.player,game.elapsed_ms,False,party_actors=companions)
        existed=hasattr(actor,'story_visible');previous=getattr(actor,'story_visible',True)
        actor.story_visible=False
        try:world.draw(bare,camera,game.player,game.elapsed_ms,False,party_actors=companions)
        finally:
            if existed:actor.story_visible=previous
            else:del actor.story_visible
        sprite=(game.player.sprite() if actor is game.player else
                getattr(actor,'story_sprite',None) or actor.sprite(game.elapsed_ms))
        mask=pygame.mask.from_surface(sprite)
        position=getattr(actor,'story_position',None) or actor.position
        anchor=(getattr(actor,'story_draw_anchor',None) or
                (world.data['player_draw_anchor'] if actor is game.player else actor.draw_anchor))
        origin=(round(position[0])-anchor[0]-camera[0],round(position[1])-anchor[1]-camera[1])
        opaque=visible=0
        for y in range(sprite.get_height()):
            for x in range(sprite.get_width()):
                if not mask.get_at((x,y)):continue
                point=origin[0]+x,origin[1]+y
                if not shown.get_rect().collidepoint(point):continue
                opaque+=1;visible+=shown.get_at(point)!=bare.get_at(point)
        result[identifier]={'opaque_pixels':opaque,'visible_pixels':visible}
    return result


def capture(output=OUT,movie_enabled=True):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    before=source_hashes()
    report={'fixture_scope':'completed MQ01/MQ02 and previously seen arrival only',
            'no_mq03_progress_seeded':True,'ordinary_travel':True,
            'disposable_save_and_settings':True,'source_sha256':before,
            'views':{},'dialogue_acknowledged':False,'continued_after_report':False,
            'continued_at_arrival':False,'survivor_route':[]}
    artifacts=[];movie=Movie(output/'emergency_journey.mp4') if movie_enabled else None
    motion_budget=0.;frame_budget=0.;motion_scene=None;last_survivor=None;selected=set()
    with tempfile.TemporaryDirectory(prefix='mq03-emergency-review-') as directory:
        driver=Driver(directory)
        inventory=driver.game.inventory.to_dict()
        resources=driver.game.party.characters['mira'].to_dict()

        def observe(seconds):
            nonlocal motion_budget,frame_budget,last_survivor
            for world in driver.game.scenes.values():
                for actor in world.npcs:
                    if 'survivor' not in actor.data['id']:continue
                    location=(world.data['id'],*[round(v,2) for v in actor.position])
                    if location!=last_survivor:
                        report['survivor_route'].append({'scene':location[0],'position':list(location[1:])})
                        last_survivor=location
            if movie is None or motion_budget<=0:return
            if motion_scene is not None and driver.game.world.data['id']!=motion_scene:return
            counted=min(seconds,motion_budget);motion_budget-=counted;frame_budget+=counted
            if frame_budget<.05-1e-7:return
            while frame_budget>=.05-1e-7:
                movie.frame(driver.game);frame_budget-=.05

        driver.observer=observe

        def hold(seconds,record=True):
            nonlocal motion_budget
            prior=motion_budget
            if record:motion_budget=seconds
            for _ in range(round(seconds/.05)):driver.tick(.05)
            motion_budget=prior if prior>motion_budget else motion_budget

        def photograph(name):
            game=driver.game;game.location_seconds=0
            game.quest_ui.current_notice=None;game.quest_ui.notices.clear()
            file=name+'.png';frame(game).save(output/file)
            if file not in artifacts:artifacts.append(file)
            report['views'][name]={'file':file,'stage':driver.quest.stage,
                'scene':game.world.data['id'],'position':list(game.player.position),
                'dialogue':game.social.script_identifier,'source':'production Game.draw'}

        def page(identifier,line,current):
            text=line.get('text','');speaker=line.get('speaker','')
            tag=None
            if identifier=='regent_welcome' and speaker=='lucan':tag='meal_with_lucan'
            elif identifier=='regent_discussion':
                if not any(item.startswith('discussion_') for item in selected):tag='discussion_opening'
                if speaker=='serene' and any(word in text.lower() for word in ('dead','return to the planet','return to our planet')):tag='sanctuary_duty'
                if 'growl' in text.lower():tag='growling_warning'
            elif identifier=='regent_attack_report':
                if 'survivor' in speaker and any(word in text.lower() for word in ('cave','get everyone')):tag='survivor_report'
                elif speaker=='lucan' and any(word in text.lower() for word in ('told','know','ahead','informed')):tag='lucan_surprised'
                elif speaker=='serene' and any(word in text.lower() for word in ('asking','agreement','permission')):tag='serene_discovers_betrayal'
                elif speaker=='aldric' and any(word in text.lower() for word in ('authority','orders','ahead')):tag='aldric_exposed'
            elif identifier=='regent_departure':
                if speaker=='serene':tag='serene_cares_for_survivor'
                elif speaker=='caelan':tag='caelan_volunteers'
            elif identifier=='regent_mira_departure':
                if speaker in ('mira','mira_worker') and any(word in text.lower() for word in ('coming','kit','rivet')):tag='mira_rejoins'
                elif speaker=='caelan':tag='mira_emergency_explained'
            if tag and tag not in selected:
                selected.add(tag);hold(1.5);photograph(tag)

        try:
            driver.meal(page)
            photograph('after_meal')
            driver.interact('discussion',page)
            assert driver.quest.stage=='interruption'
            motion_budget=8.
            driver.until(lambda:driver.quest.stage=='attack_report' and driver.game.social.active)
            motion_budget=0.
            photograph('survivor_arrived')
            driver.interact('attack_report',page)
            assert driver.quest.stage=='departure'
            # Checkpoint after the report must not replay the physical entrance.
            driver.continue_saved()
            assert driver.quest.stage=='departure'
            driver.tick()
            assert driver.game.social.script_identifier!='regent_attack_report'
            report['continued_after_report']=True
            driver.departure(page)
            motion_budget=7.;motion_scene=driver.game.town.data['id']
            driver.rejoin_mira(page)
            motion_budget=0.;motion_scene=None
            assert driver.game.party.current_event_id=='mq03_sanctuary'
            photograph('mira_in_party')
            hold(1.5)
            driver.continue_saved()
            assert driver.quest.stage=='sanctuary_travel'
            motion_budget=5.;motion_scene=WORLD_ID
            driver.arrive()
            motion_budget=0.;motion_scene=None
            hold(2.)
            photograph('sanctuary_arrival')
            report['arrival_visibility']=cast_visibility(driver.game)
            driver.continue_saved(settle=False)
            assert driver.quest.stage=='sanctuary_arrival_pending'
            report['immediate_continue_visibility']=cast_visibility(driver.game)
            assert all(record['visible_pixels']>0 for record in report['immediate_continue_visibility'].values())
            driver.until(lambda:not driver.game.opening_fade and not driver.game.transfer_cooldown)
            report['continued_at_arrival']=True
            hold(2.)
            photograph('arrival_continued')
            if movie and movie.frames/20<48:hold(48-movie.frames/20)
            game=driver.game;quest=driver.quest
            cast=['caelan']
            for actor in (quest.aldric,quest.lucan,quest.clerk):
                assert quest._world(actor) is game.world
                assert sum(actor in world.npcs for world in game.scenes.values())==1
                cast.append(actor.data['id'])
            mira_actors=[actor for actor in game.party_travel.actors() if actor.identifier=='mira']
            assert len(mira_actors)==1
            cast.append('mira')
            assert not any(getattr(actor,'party_travelling',False) is False
                           for actor in game.world.npcs if actor is game.mill_quest.mira)
            report.update(arrival_stage=quest.stage,mq03_status=game.quests.status(REGENT_QUEST),
                mq04_status=game.quests.status(LANTERN_QUEST),
                mira_resources_preserved=resources==game.party.characters['mira'].to_dict(),
                mira_resources_before=resources,mira_resources_after=game.party.characters['mira'].to_dict(),
                no_lucan_combat_recruitment='lucan' not in game.party.members,
                one_mira_representation=len(mira_actors)==1,cast_at_arrival=sorted(cast),
                cave_barrier_closed=not game.world.can_stand((1008,365)),
                no_battle_or_reward=not game.combat.active and inventory==game.inventory.to_dict(),
                dialogue_acknowledged=True,transitions=driver.transitions,
                observed_stages=driver.stages,dialogue=driver.dialogue,
                party=game.party.to_dict(),quest=quest.to_dict())
            assert game._read_saved_journey() is not None
            if movie:
                movie.finish()
                report['movie']={'file':'emergency_journey.mp4','fps':20,'frames':movie.frames,
                                 'seconds':movie.frames/20,'size':[960,640]}
                movie=None;artifacts.append('emergency_journey.mp4')
            else:report['movie']={'file':None,'fps':20,'frames':0,'seconds':0,'size':[960,640]}
            names=[name for name in ('sanctuary_duty','growling_warning','survivor_report',
                   'lucan_surprised','serene_discovers_betrayal','mira_rejoins','sanctuary_arrival',
                   'arrival_continued') if name in report['views']]
            board=Image.new('RGB',(1440,math.ceil(len(names)/3)*344),'#15382d')
            draw=ImageDraw.Draw(board)
            for index,name in enumerate(names):
                x,y=index%3*480,index//3*344
                with Image.open(output/report['views'][name]['file']) as photograph_image:
                    board.paste(photograph_image.resize((480,320),Image.Resampling.NEAREST),(x,y+24))
                draw.text((x+8,y+6),name.replace('_',' '),fill='#e7ecd2')
            board.save(output/'contact_sheet.png');artifacts.append('contact_sheet.png')
            assert source_hashes()==before,'MQ03 source changed during capture; regenerate after freeze'
            report['artifact_sha256']={name:digest(output/name) for name in artifacts}
            (output/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            (output/'README.md').write_text('''# MQ03 — The Sanctuary emergency

![Actual MQ03 gameplay](contact_sheet.png)

[Watch the emergency and journey excerpts](emergency_journey.mp4)

This production Game review starts from an explicitly initialized legacy journey
with completed MQ01/MQ02 and a previously seen arrival. No MQ03 objective, stage,
current-quest actor position or recruitment is seeded. The separate welcome,
meal, revised discussion, survivor report, betrayal, Mira's rejoining exchange
and Sanctuary journey are earned through acknowledged dialogue and ordinary
movement. Long transit and some reading are omitted from the focused silent
movie; all observed dialogue is retained in the verification record.

The survivor enters physically, Lucan learns of the secret deployment, and
Serene remains with the injured worker. Mira retains her previous resources.
Aldric, Lucan, the page, Caelan and Mira gather at the actual reserve entrance.
Save/Continue is exercised after the report and at arrival. MQ03 remains active,
MQ04 remains locked, and the arrival cutscene and miniboss are deliberately left
for subsequent story work. The cave rail remains closed.

[Verification](verification.json) records actual stages, source lines, transfers,
survivor positions, party identity, resources and source/artifact fingerprints.
All save/settings files are temporary and leave player journeys untouched.
Regenerate with `python tools/capture_mq03_emergency.py`; verify with
`python tools/capture_mq03_emergency.py --check`.
''')
        finally:
            if movie:movie.finish()
            pygame.quit()
    check(output)
    print(json.dumps({'movie':report['movie'],'stage':report['arrival_stage'],
                      'views':len(report['views']),'cast':report['cast_at_arrival']}))


def check(output):
    report=json.loads((output/'verification.json').read_text())
    assert report['source_sha256']==source_hashes(),'MQ03 sources changed; regenerate the review'
    for name,expected in report['artifact_sha256'].items():
        assert digest(output/name)==expected,('Review artifact changed',name)
    assert report['fixture_scope']=='completed MQ01/MQ02 and previously seen arrival only'
    assert report['arrival_stage']=='sanctuary_arrival_pending'
    assert report['mq03_status']=='active' and report['mq04_status']=='locked'
    assert report['mira_resources_preserved'] and report['no_lucan_combat_recruitment']
    assert report['one_mira_representation'] and report['cast_at_arrival']==['aldric','caelan','lucan','mira','regent_clerk']
    for key in ('arrival_visibility','immediate_continue_visibility'):
        assert set(report[key])==set(report['cast_at_arrival'])
        assert all(record['visible_pixels']>0 for record in report[key].values())
    assert report['ordinary_travel'] and report['dialogue_acknowledged']
    assert {'eldenmere.playable','sanctuary_hall','sanctuary_dining'} <= {
        record['scene'] for record in report['survivor_route']}
    assert len(report['survivor_route'])>20
    assert any(record['script']=='regent_attack_report' and record['speaker']=='lucan'
               and "wasn't told" in record['text'].lower().replace('’',"'")
               for record in report['dialogue'])
    assert report['continued_after_report'] and report['continued_at_arrival']
    assert report['cave_barrier_closed'] and report['no_battle_or_reward']
    if report['movie']['file']:assert 45<=report['movie']['seconds']<=90
    print('MQ03 emergency dialogue, Mira rejoin, ordinary travel, saves and review fingerprints verified.')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--no-movie',action='store_true')
    args=parser.parse_args(argv)
    if args.check:check(args.out)
    else:capture(args.out,not args.no_movie)


if __name__=='__main__':main()
