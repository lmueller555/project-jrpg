"""Review the sanctuary through real travel, movement, dialogue and save/continue.

Uses disposable saves/settings. Scene changes are performed by production
contacts and doors; the fixture never assigns the active world or teleports
the player to a review position.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image

from main import Game
from npc_routines import find_path
from overworld_travel import TOWN_EXIT, WORLD_ID
from tools.capture_overworld_sanctuary import Movie, frame, regional_path

OUT = ROOT/'docs/reviews/sanctuary_reserve'
RESERVE_ID = 'elden_vale_sanctuary'
HALL_ID = 'elden_vale_sanctuary_hall'


def path(world, start, goal, step=6):
    """A full-foot cardinal route, checking every pixel of each short edge."""
    start = tuple(round(v/step)*step for v in start)
    end = tuple(round(v/step)*step for v in goal)
    if not world.can_stand(start) or not world.can_stand(end):
        raise AssertionError(('Blocked review endpoint', world.data['id'], start, end))
    queue = [(math.dist(start,end),0,start)];costs = {start:0};parents = {}
    while queue:
        _,cost,point = heapq.heappop(queue)
        if point == end:
            points = [point]
            while point in parents:point = parents[point];points.append(point)
            result = list(reversed(points))
            compact = []
            for p in result:
                if len(compact)>1:
                    a,b = compact[-2:]
                    if a[0]==b[0]==p[0] or a[1]==b[1]==p[1]:compact[-1]=p;continue
                compact.append(p)
            if tuple(goal)!=end:compact.append(tuple(goal))
            return compact
        if cost>costs[point]:continue
        for dx,dy in ((step,0),(-step,0),(0,step),(0,-step)):
            other = point[0]+dx,point[1]+dy
            if not all(world.can_stand((point[0]+dx*i/step,point[1]+dy*i/step))
                       for i in range(1,step+1)):continue
            next_cost = cost+step
            if next_cost>=costs.get(other,math.inf):continue
            costs[other]=next_cost;parents[other]=point
            heapq.heappush(queue,(next_cost+math.dist(other,end),next_cost,other))
    raise AssertionError(('No full-foot route',world.data['id'],start,end))


def walk(game, points, scene, *, movie=None, transfer=None):
    """Use ordinary movement and stop at an expected production transfer."""
    for target in points:
        target = pygame.Vector2(target)
        for _ in range(1800):
            if transfer is not None and game.world.data['id']==transfer:return True
            if game.world.data['id']!=scene:
                raise AssertionError(('Unexpected transfer',scene,game.world.data['id']))
            delta = target-game.player.position
            if delta.length()<.7:break
            before = game.player.position.copy()
            seconds = min(.04,delta.length()/72)
            game.update(seconds,delta,False)
            if movie is not None:movie.sample(game,seconds)
            if transfer is not None and game.world.data['id']==transfer:return True
            if game.player.position==before:
                raise AssertionError(('Stalled walking',scene,tuple(before),tuple(target)))
            assert game.world.can_stand(game.player.position),tuple(game.player.position)
        else:raise AssertionError(('Walking exceeded budget',scene,tuple(target)))
    return transfer is not None and game.world.data['id']==transfer


def state(game):
    return {'quests':game.quests.to_dict(),'inventory':game.inventory.to_dict(),
            'flags':sorted(game.social.flags),'music':game.music.desired_track,
            'abilities':game.character_abilities.to_dict()}


def photograph(game, output, name):
    game.location_seconds=0
    game.quest_ui.current_notice=None;game.quest_ui.notices.clear()
    frame(game).save(output/name)
    return {'file':name,'scene':game.world.data['id'],'position':list(game.player.position),
            'size':list(game.window.get_size()),'source':'production Game.draw'}


def whole_scene(game, output):
    """Stitch bounded production World.draw views, with no painted scenery."""
    world=game.world;image=pygame.Surface(world.size)
    for y in range(0,world.size[1],320):
        for x in range(0,world.size[0],480):
            tile=pygame.Surface((480,320))
            world.draw(tile,(x,y),game.player,game.elapsed_ms,include_ui=False)
            image.blit(tile,(x,y))
    pygame.image.save(image,output)


def finish_dialogue(game):
    count=0
    while game.social.active:
        assert not game.social.choosing,'Review inspections must not award a choice'
        game.social.advance();count+=1
        assert count<100,'Dialogue did not finish'
    game.update(.05,(0,0),False)
    return count


def restore(game, save_path, settings_path):
    before=(game.world.data['id'],tuple(game.player.position),state(game))
    assert game.save_progress(),'Disposable save failed'
    other=Game(window_size=(960,640),fullscreen=False,start_on_title=True,
               save_path=save_path,settings_path=settings_path)
    assert other.has_saved_journey,'Save not accepted by Continue'
    assert other.begin_journey(True),'Continue failed'
    after=(other.world.data['id'],tuple(other.player.position),state(other))
    assert after==before,('Save/continue changed location or progression',before,after)
    other.audio.set_music(0);other.audio.set_effects(0)
    other.update(.6,(0,0),False)
    return other


def capture(output=OUT, movie_enabled=True):
    output.mkdir(parents=True,exist_ok=True)
    source=ROOT/'assets/maps/elden_vale_sanctuary/map.json'
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    report={'source':'Production Game movement, contacts, doors and renderer',
            'disposable_save_and_settings':True,'quest_or_equipment_seeding':False,
            'reserve_map_sha256':digest,'views':{},'inspections':{},'walked_loop':False}
    movie=None
    with tempfile.TemporaryDirectory(prefix='sanctuary-reserve-review-') as temporary:
        save=Path(temporary)/'journey.json';settings=Path(temporary)/'settings.json'
        game=Game(window_size=(960,640),fullscreen=False,start_on_title=False,
                  save_path=save,settings_path=settings)
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade=game.transfer_cooldown=0;pygame.event.clear()
        route=find_path(game.town,game.player.position,TOWN_EXIT,game.town.probe_size,None)
        assert route is not None,'Town exit is unreachable'
        assert walk(game,route,game.town.data['id'],transfer=WORLD_ID),'Town contact did not transfer'
        game.update(.4,(0,0),False)
        baseline=state(game);world=game.world
        road=next(r for r in world.region['roads'] if r['id']=='sanctuary_approach')
        walk(game,regional_path(world,game.player.position,world._tile_point(road['points'][0])),WORLD_ID)
        road_points=[world._tile_point(p) for p in road['points']]
        walk(game,road_points[:-4],WORLD_ID)
        if movie_enabled:movie=Movie(output/'reserve_walk.mp4')
        try:
            assert walk(game,road_points[-4:],WORLD_ID,movie=movie,transfer=RESERVE_ID),'Miniature contact did not enter'
            game.update(.4,(0,0),False)
            report['views']['arrival']=photograph(game,output,'arrival.png')
            if movie:movie.hold(game,1)
            reserve=game.world
            for key,point in reserve.data.get('blocked_probes',{}).items():
                assert not reserve.can_stand(point),('Solid object accepts player feet',key,point)
            report['blocked_probes']=reserve.data.get('blocked_probes',{})

            def visit(key, name=None):
                target=game.sanctuary_reserve.targets[key]
                walk(game,path(game.world,game.player.position,target['approach']),game.world.data['id'],movie=movie)
                delta=pygame.Vector2(target['position'])-game.player.position
                game.update(.01,delta,False)
                game.update(.05,(0,0),False)
                assert game.sanctuary_reserve._nearby()[0]==key,('Wrong inspection target',key,game.sanctuary_reserve._nearby())
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e,repeat=False))
                game.handle_events()
                pygame.event.post(pygame.event.Event(pygame.KEYUP,key=pygame.K_e))
                game.handle_events()
                assert game.social.script_identifier=='sanctuary_reserve_'+key,('E did not start inspection',key)
                if name:
                    report['views'][key]=photograph(game,output,name)
                    if movie:movie.hold(game,.8)
                report['inspections'][key]={'approach':list(game.player.position),'pages':finish_dialogue(game)}
                assert state(game)==baseline,('Inspection changed progression',key)

            visit('boundary','boundary.png')
            visit('caretaker','caretaker.png')
            visit('visitor_slate','visitors.png')
            visit('grove','grove.png')
            waypoints=reserve.data['loop_waypoints']
            for point in waypoints:
                walk(game,path(reserve,game.player.position,point),RESERVE_ID,movie=movie)
            report['walked_loop']=True
            report['loop_waypoints']=waypoints
            visit('cave','cave.png')
            visit('survey','survey.png')
            whole_scene(game,output/'reserve_overview.png')
            report['views']['overview']={'file':'reserve_overview.png','size':list(reserve.size),
                                        'source':'bounded production World.draw views'}
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_m,repeat=False));game.handle_events()
            assert game.map_open,'M did not open local reserve map'
            report['views']['map']=photograph(game,output,'local_map.png')
            pygame.event.post(pygame.event.Event(pygame.KEYUP,key=pygame.K_m));game.handle_events()
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_m,repeat=False));game.handle_events()
            pygame.event.post(pygame.event.Event(pygame.KEYUP,key=pygame.K_m));game.handle_events()
            assert not game.map_open
            if movie:
                movie.hold(game,1);movie.finish()
                report['movie']={'file':'reserve_walk.mp4','fps':movie.fps,'frames':movie.frames,
                                 'seconds':movie.frames/movie.fps}
                movie=None
            game=restore(game,save,settings)
            report['continue_reserve']=True
            hall_door=next(d for d in game.world.doors if d.data['id']=='sanctuary_hall')
            approach=game.world.data['public_approaches']['hall']
            walk(game,path(game.world,game.player.position,approach),RESERVE_ID)
            assert walk(game,[hall_door.data['anchor']],RESERVE_ID,transfer=HALL_ID),'Hall door did not enter'
            game.update(.4,(0,0),False)
            report['views']['hall']=photograph(game,output,'hall.png')
            visit('records','hall_records.png')
            visit('remembrance')
            visit('cabinet')
            game=restore(game,save,settings);report['continue_hall']=True
            door=next(d for d in game.world.doors if d.data['id']=='reserve_exit')
            walk(game,path(game.world,game.player.position,(288,328)),HALL_ID)
            assert walk(game,[door.data['anchor']],HALL_ID,transfer=RESERVE_ID),'Hall return did not transfer'
            game.update(.4,(0,0),False)
            exit_point=game.world.data['reserve_exit']['position']
            assert walk(game,path(game.world,game.player.position,exit_point),RESERVE_ID,transfer=WORLD_ID),'Reserve return did not transfer'
            game.update(.4,(0,0),False)
            report['views']['return']=photograph(game,output,'overworld_return.png')
            assert state(game)==baseline,'Reserve visit changed quest, inventory, flags, music or abilities'
            region=game.world
            rect=region.town_entry_rect
            target=(rect.centerx,rect.bottom-2)
            exterior=(rect.centerx,rect.bottom+36)
            walk(game,regional_path(region,game.player.position,exterior),WORLD_ID)
            assert walk(game,[target],WORLD_ID,transfer=game.town.data['id']),'Town return did not transfer'
            game.update(.4,(0,0),False)
            assert state(game)==baseline,'Town return changed story progression'
            assert not game.combat.active
            report['round_trip_complete']=True;report['progression_unchanged']=True
            report['saved_journey_valid']=bool(game.save_progress() and game._read_saved_journey() is not None)
            assert report['saved_journey_valid']
            assert hashlib.sha256(source.read_bytes()).hexdigest()==digest,'Reserve geometry changed during capture'
        finally:
            if movie is not None:movie.finish()
            pygame.quit()
    contact=Image.new('RGB',(960,640),'#18362b')
    for index,name in enumerate(('arrival.png','grove.png','cave.png','hall.png')):
        with Image.open(output/name) as picture:
            contact.paste(picture.resize((480,320),Image.Resampling.NEAREST),((index%2)*480,(index//2)*320))
    contact.save(output/'scene_contact.png')
    (output/'verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    (output/'README.md').write_text('''# Elden Vale Sanctuary — in-game reserve review

![Actual reserve and hall views](scene_contact.png)

![Full reserve, stitched from the production renderer](reserve_overview.png)

[Approach and reserve circuit](reserve_walk.mp4) · [Local map](local_map.png)

The capture walks normally from Eldenmere's southern exit, along the overworld
sanctuary approach and onto the miniature. It visits the boundary, caretaker,
grove visitors, confluence clearing, complete woodland loop, cave approach and
survey board, then enters the hall and reads its three observations. The hall
door and southern reserve exit return through production contacts.

Disposable save/continue checks resume inside both the reserve and hall. The
round trip ends back in Eldenmere without changing quests, inventory, dialogue
flags, abilities or music. Solid-foot probes check the hall, cliff, cave depth,
stone seam, trees, basin, benches and boundary wall. No dungeon is implemented.

[Verification](verification.json) records actual positions, inspections, map
hash and the closed walking circuit. Player save/settings files remain untouched.
Reproduce with `python tools/capture_sanctuary_reserve.py`.
''')
    print(json.dumps({'output':str(output),'round_trip_complete':True,
                      'inspections':len(report['inspections']),'movie':report.get('movie')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    parser.add_argument('--no-movie',action='store_true')
    args=parser.parse_args();capture(args.out,not args.no_movie)
