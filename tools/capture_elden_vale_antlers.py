"""Actual production Pale Antlers review with disposable journeys and settings.

Exploration uses live maps/contacts with no replacement art. A separate, labelled
arrival preview seeds story prerequisites, then runs the real director and rail.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from time import perf_counter
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image
from main import Game
from rendering import WorldCanvas
from npc_routines import find_path
from overworld_travel import TOWN_EXIT,WORLD_ID
from tools.capture_overworld_sanctuary import regional_path
from tools.capture_sanctuary_reserve import path,state
from tools.capture_elden_vale_hd_integration import gif
RESERVE='elden_vale_sanctuary'
DEFAULT=ROOT/'docs/reviews/elden_vale_pale_antlers'

def ownership(game):
    """Stable identities, not the changing subset currently outside in town.

    Ambient routine phases restart on launch by the existing save contract.
    A resident transferring into its house must not appear lost to this check.
    """
    identifiers={a.data['id'] for a in game.persistent_npcs}
    identifiers.update(r['id'] for r in game.town.data.get('npcs',[]))
    scenes={id(s):s for s in [game.town,*game.scenes.values(),game.overworld_world]}
    result={identifier:sum(getattr(a,'data',{}).get('id')==identifier
        for scene in scenes.values() for a in scene.npcs) for identifier in identifiers}
    assert all(count==1 for count in result.values()),('Lost/duplicate authored actor',result)
    return result

def fingerprint():
    names={Path(__file__).resolve(),*[ROOT/n for n in ['main.py','overworld_world.py','landmark_layers.py','rendering.py','camera_director.py','sanctuary_arrival.py','sanctuary_care.py','sanctuary_rope.py',
        'tools/elden_vale_landmark_bindings.py','tools/build_elden_vale_hd_integration.py','tools/build_eldenmere_hd.py','tools/build_sanctuary_reserve_hd.py','assets/characters/caelan/scene_actions.json']]}
    for folder in ['assets/maps/eldenmere/playable','assets/maps/overworld/elden_vale','assets/maps/elden_vale_sanctuary','assets/maps/elden_vale_sanctuary_hall','assets/maps/elden_vale_sanctuary_relief','assets/maps/sanctuary_reserve_hd/landmarks',
        'assets/story/sanctuary_opening','assets/story/sanctuary_reserve']:
        names.update(p for p in (ROOT/folder).rglob('*') if p.is_file())
    pending=[p for p in names if p.suffix=='.json'];seen=set()
    def refs(value):
        if isinstance(value,str) and value.startswith('assets/') and (ROOT/value).is_file():yield ROOT/value
        elif isinstance(value,dict):
            for v in value.values():yield from refs(v)
        elif isinstance(value,list):
            for v in value:yield from refs(v)
    while pending:
        p=pending.pop()
        if p in seen:continue
        seen.add(p)
        for ref in refs(json.loads(p.read_text())):
            names.add(ref)
            if ref.suffix=='.json':pending.append(ref)
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(names)}

def capture(folder):
    folder.mkdir(parents=True,exist_ok=True);before=fingerprint()
    report={'source':'Initialized Game using production maps, asset bindings, collision and renderer. No replacement scenery or in-memory landmark registry.',
        'exploration_fixture':'Opening director disabled; initial New Game town spawn. No quest/party/equipment seeding until separately labelled companion and story fixtures.',
        'display_size':[960,640],'source_sha256':before,'views':{},'movement':[], 'transfers':[],
        'limitations':['Not an uninterrupted opening-to-MQ03 quest playthrough. Arrival/care/rail use the production preview prerequisite fixture.',
                       'Timing is hardware-specific SDL-dummy world rendering, excluding simulation/display/UI.',
                       'Atlas/minimap remains preexisting artwork; Rising Rain remains inactive.']}
    with tempfile.TemporaryDirectory(prefix='elden-antlers-review-') as temporary:
        temporary=Path(temporary)
        def new_game(name):
            g=Game(window_size=(960,640),fullscreen=False,start_on_title=True,
                save_path=temporary/(name+'.json'),settings_path=temporary/(name+'_settings.json'))
            g.on_title=False;g.opening.restore({'version':1,'stage':'disabled'})
            g.opening_fade=g.transfer_cooldown=0;g.audio.set_music(0);g.audio.set_effects(0)
            return g
        g=new_game('exploration')
        try:
            def photo(name,game=None):
                game=game or g;game.location_seconds=game.saves.notice_seconds=0
                game.quest_ui.current_notice=None;game.quest_ui.notices.clear()
                game.draw();pygame.image.save(game.window,str(folder/(name+'.png')))
                report['views'][name]={'scene':game.world.data['id'],'player':list(game.player.position),'camera':list(game.camera.position()),'source':'Game.draw; production bindings'}
            def follow(points,*,running=False,transfer=None,label=None,frames=None):
                scene=g.world.data['id'];trace=[];seconds=0
                for goal in points:
                    goal=pygame.Vector2(goal)
                    for _ in range(2400):
                        if transfer and g.world.data['id']==transfer:break
                        assert g.world.data['id']==scene,('Unexpected transfer',scene,g.world.data['id'])
                        delta=goal-g.player.position
                        if delta.length()<.6:break
                        old=g.player.position.copy();dt=min(1/30,delta.length()/(108 if running else 72))
                        g.update(dt,delta,running);seconds+=dt
                        if transfer and g.world.data['id']==transfer:break
                        assert g.player.position!=old,('Stalled',scene,list(old),list(goal))
                        assert g.world.can_stand(g.player.position),('Unsafe',scene,list(g.player.position))
                        trace.append(list(g.player.position))
                        if frames is not None and len(trace)%3==0 and len(frames)<100:
                            g.draw();frames.append(Image.frombytes('RGB',g.window.get_size(),pygame.image.tobytes(g.window,'RGB')))
                    else:raise AssertionError(('Movement budget',scene,list(goal)))
                    if transfer and g.world.data['id']==transfer:break
                if transfer:
                    assert g.world.data['id']==transfer,('Missing transfer',scene,transfer)
                    report['transfers'].append([scene,transfer]);g.update(.5,(0,0),False)
                if label:report['movement'].append({'label':label,'scene':scene,'running':running,'seconds':seconds,'trace':trace})
            def travel(point,**kwargs):follow(path(g.world,g.player.position,point),**kwargs)
            def save_continue(label):
                expected=g.journey_snapshot();owners=ownership(g);assert g.save_progress(),g.save_error
                restored=Game(window_size=(960,640),fullscreen=False,start_on_title=True,
                    save_path=temporary/'exploration.json',settings_path=temporary/'exploration_settings.json')
                try:
                    assert restored.begin_journey(True)
                    actual=restored.journey_snapshot()
                    for key in ('quests','party','dialogue_flags','player','overworld'):assert actual[key]==expected[key],(label,key)
                    assert ownership(restored)==owners
                    restored.update(.7,(0,0),False);restored.camera.reset()
                    photo('continue_'+label,restored)
                    report.setdefault('save_continue',{})[label]={'position':actual['player'],'exact_keys':['quests','party','dialogue_flags','player','overworld'],'actor_ownership_preserved':True}
                finally:restored.music.stop()
            def door(identifier):
                origin=g.world;d=next(d for d in origin.doors if d.data['id']==identifier)
                x,y=d.data['anchor'];direction=-1 if d.data['entry_side']=='north' else 1
                travel((x,y-direction*24))
                follow([(x,y+direction*24)],transfer=g._scene(d.data['destination']).data['id'] if hasattr(g,'_scene') else json.loads((ROOT/d.data['destination']).read_text())['id'])
            baseline=copy.deepcopy(state(g));owners=ownership(g)
            # Actual town departure, production road, miniature entry and return.
            g.camera.reset();photo('town_start')
            for n,point in enumerate([(600,180),(540,120),(720,360)]):
                if g.world.can_stand(point):travel(point);photo('town_gap_'+str(n))
            route=find_path(g.town,g.player.position,TOWN_EXIT,g.town.probe_size,None);assert route
            follow(route,transfer=WORLD_ID,label='town_departure')
            world=g.world;road=next(r for r in world.region['roads'] if r['id']=='sanctuary_approach')
            follow(regional_path(world,g.player.position,world._tile_point(road['points'][0])),label='regional_to_sanctuary_road')
            points=[world._tile_point(p) for p in road['points']]
            for name,first,last in [('regional_woodland',0,len(points)//2),('regional_approach',len(points)//2,len(points)-4)]:
                follow(points[first:last],label=name);photo(name)
            # Reach the existing northern shoulder around the east side of the
            # miniature, without entering its contact rectangle or focusing camera.
            approach_position=g.player.position.copy()
            shoulder=[world._tile_point(p) for p in [(94,-64),(94,-68),(93,-70)]]
            follow(regional_path(world,g.player.position,shoulder[0]),label='regional_shoulder_arrival')
            follow([world._tile_point((94,-66))],label='miniature_east_approach');g.camera.reset();photo('miniature_from_east')
            follow([world._tile_point(p) for p in [(94,-64),(86,-64),(86,-66)]],label='miniature_west_approach');g.camera.reset();photo('miniature_from_west')
            follow([world._tile_point(p) for p in [(86,-64),(94,-64)]],label='miniature_forecourt_crossing')
            miniature,anchor=world._prop_image('ridge_sanctuary')
            assert miniature.get_size()==(96,80) and anchor==(48,78)
            site=next(s for s in world.region['landmarks'] if s['id']=='ridge_sanctuary')
            report['miniature_registration']={'logical_canvas':list(miniature.get_size()),'draw_anchor':list(anchor),
                'tile_position':site['tile_position'],'unchanged_entry_rect_tiles':site['entry_rect_tiles'],
                'return_tile_position':site['return_tile_position'],'actual_east_west_approach_movement':True}
            follow(shoulder[1:],label='regional_northern_shoulder');g.camera.reset();photo('regional_north_reveal')
            follow(list(reversed(shoulder[:-1])),label='regional_shoulder_return')
            follow(regional_path(world,g.player.position,approach_position),label='regional_back_to_entry_road')
            follow(points[-4:],transfer=RESERVE,label='miniature_entry')
            g.camera.reset();photo('reserve_arrival')
            reserve=g.world;loop=reserve.data['loop_waypoints']
            native={}
            for scene in [g.town,world,reserve]:
                count=0
                for item in scene.landmarks.records:
                    loaded=scene.landmarks.image(item)
                    assert isinstance(loaded,WorldCanvas)
                    raw=pygame.image.load(str(ROOT/item['image'])).convert_alpha()
                    assert pygame.image.tobytes(loaded.native,'RGBA')==pygame.image.tobytes(raw,'RGBA'),item['id']
                    count+=1
                native[scene.data['id']]={'source_records_compared':count,'native_rgba_mismatches':0}
            report['native_source_preservation']=native
            for reverse,running in [(False,False),(True,True)]:
                for index,point in enumerate(reversed(loop) if reverse else loop):
                    travel(point,running=running,label=('circuit_reverse_run_' if reverse else 'circuit_walk_')+str(index))
                photo('circuit_reverse_end' if reverse else 'circuit_walk_end')
            for name,point in [('north_reveal',(960,168)),('east_raised_skull',(1100,270)),('cave_apron',(1008,406)),('grove',(292,244)),('survey',(858,630)),('cloister',(776,366))]:
                travel(point);g.camera.reset();photo(name)
                if name=='north_reveal':save_continue('near_bone')
            for name,point in reserve.data['public_approaches'].items():
                travel(point,label='protected_approach_'+name)
            travel((1100,300));g.camera.reset();save_continue('beneath_span')
            for running,reverse in [(False,False),(False,True),(True,False),(True,True)]:
                end=(1100,220 if not reverse else 300);frames=[]
                travel(end,running=running,label='span_'+str(running)+'_'+str(reverse),frames=frames)
                if frames:gif(folder/('span_'+('run' if running else 'walk')+('_return' if reverse else '')+'.gif'),frames,100)
            # Compare immediate overhead cutaways independently of animated ground.
            travel((1100,270));g.camera.reset()
            diagonal=[]
            for direction in [(1,-1),(-1,1),(-1,-1),(1,1)]:
                trace=[];blocked=0
                for _ in range(6):
                    previous=g.player.position.copy();g.update(1/30,direction,False)
                    assert reserve.can_stand(g.player.position)
                    blocked+=g.player.position==previous;trace.append(list(g.player.position))
                diagonal.append({'direction':list(direction),'trace':trace,'blocked_updates':blocked})
            report['diagonal_full_foot_checks']=diagonal
            travel((1100,270));g.camera.reset()
            def overhead(actors):
                out=WorldCanvas((480,320),pygame.SRCALPHA);out.fill((0,0,0,0))
                reserve.landmarks.draw(out,g.camera.position(),'overhead',actors=actors)
                return pygame.image.tobytes(out.native,'RGBA')
            normal=overhead([g.player]);assert normal!=overhead([]),'Cutaway not exercised'
            g.audio.set_reduced_motion(True);g.update(0,(0,0),False);photo('reduced_motion_span')
            assert overhead([g.player])==normal;g.elapsed_ms+=2400;assert overhead([g.player])==normal
            report['reduced_motion_cutaway_stable']=True;g.audio.set_reduced_motion(False)
            def world_pixels():
                out=WorldCanvas((480,320));reserve.draw(out,g.camera.position(),g.player,g.elapsed_ms,False)
                return pygame.image.tobytes(out.native,'RGB')
            report['freeze_resume']={}
            for mode in ['pause','focus_loss']:
                before_state=(g.elapsed_ms,tuple(g.player.position),world_pixels())
                if mode=='pause':g.pause.is_open=True
                else:g._music_focused=False
                g.update(.4,(1,0),True)
                assert (g.elapsed_ms,tuple(g.player.position),world_pixels())==before_state
                g.pause.is_open=False;g._music_focused=True;report['freeze_resume'][mode]=True
            elapsed=g.elapsed_ms;g.update(.1,(0,0),False);assert g.elapsed_ms>elapsed
            # Hall/relief doors, without choosing restoration or advancing quests.
            door('sanctuary_hall');photo('hall');door('relief_room');photo('relief_room');door('hall');door('reserve_exit')
            travel((1008,406));start=g.player.position.copy()
            for _ in range(50):g.update(1/30,(0,-1),False)
            rail=pygame.Rect(g.world.data['cave_barrier']['footprint'])
            assert g.world is reserve and g.player.position.y>=rail.bottom+reserve.probe_size[1]/2-2
            photo('closed_rail');report['closed_cave_forward_input_blocked']=True
            # Cache/performance: world-only renderer with live production art.
            report['render_budget_samples']={}
            for name,point in [('north',(960,168)),('east',(1100,270)),('forecourt',(534,370))]:
                travel(point);g.camera.reset();out=WorldCanvas((480,320))
                for _ in range(12):reserve.draw(out,g.camera.position(),g.player,g.elapsed_ms,False)
                samples=[]
                for _ in range(20):
                    t=perf_counter();reserve.draw(out,g.camera.position(),g.player,g.elapsed_ms,False);samples.append((perf_counter()-t)*1000)
                # Matched same-revision timing control only, never a capture or
                # saved map: omit landmark passes while retaining all other art.
                live_draw=reserve.landmarks.draw;control=[]
                try:
                    reserve.landmarks.draw=lambda *args,**kwargs:None
                    for _ in range(20):
                        t=perf_counter();reserve.draw(out,g.camera.position(),g.player,g.elapsed_ms,False);control.append((perf_counter()-t)*1000)
                finally:reserve.landmarks.draw=live_draw
                assert reserve._ground_cache.bytes<=reserve._ground_cache.budget
                assert reserve.landmarks.sources.bytes<=reserve.landmarks.sources.budget
                report['render_budget_samples'][name]={'world_draw_ms_mean':sum(samples)/len(samples),'world_draw_ms_max':max(samples),
                    'ground_bytes':reserve._ground_cache.bytes,'ground_budget':reserve._ground_cache.budget,
                    'landmark_source_bytes':reserve.landmarks.sources.bytes,'landmark_source_budget':reserve.landmarks.sources.budget,
                    'last_viewport_working_bytes':reserve.landmarks.working_bytes,
                    'same_revision_landmark_pass_disabled_control_ms_mean':sum(control)/len(control),
                    'control_scope':'Timing-only omission of landmark drawing, same current map/camera/cache; not a historical step-1 executable or a gameplay screenshot.'}
            # Real detailed passive follower; explicitly temporary fixture roster.
            party_before=g.party.to_dict();assert g.party.recruit('mira',temporary=True)
            travel((1100,270));assert g.party_travel.stage_companion('mira',(1100,302),facing='back')
            follower,=g.party_travel.actors();g.camera.reset();photo('companion_span')
            trace=[]
            for _ in range(45):
                g.update(1/30,(0,-1),True);assert reserve.can_stand(g.player.position) and reserve.can_stand(follower.position)
                trace.append({'player':list(g.player.position),'mira':list(follower.position)})
            report['temporary_companion_fixture']={'recruited':'mira','trace':trace};g.party.restore(party_before);g.party_travel.reset()
            assert state(g)==baseline,'Exploration changed quest/inventory/flags/abilities/music'
            exit_point=reserve.data['reserve_exit']['position'];travel(exit_point,transfer=WORLD_ID,label='reserve_exit')
            world=g.world;photo('regional_return')
            rect=world.town_entry_rect;outside=(rect.centerx,rect.bottom+36)
            follow(regional_path(world,g.player.position,outside),label='regional_return_to_town')
            follow([(rect.centerx,rect.bottom-2)],transfer=g.town.data['id'],label='town_return')
            assert state(g)==baseline;assert ownership(g)==owners
            report['production_roundtrip_progression_and_ownership_preserved']=True
            print('Production exploration, circuit, transfers and saves passed.',flush=True)
        finally:g.music.stop();pygame.quit()
        # Separately staged prerequisites, actual arrival/care/rail director.
        g=new_game('arrival_preview')
        try:
            g.sanctuary_arrival.prepare_preview();assert g.sanctuary_arrival.start(force=True)
            owner=g.sanctuary_arrival;seen=set();visited_beats=set();care_seen=set();rail_samples=[];frames=[]
            for tick in range(8000):
                if owner.completed:break
                visited_beats.add(owner.beat)
                g.update(.05,(0,0),False)
                care=owner.care.action
                if care and care not in care_seen:
                    photo('care_'+care,g);care_seen.add(care)
                if owner.dialogue:
                    if owner.beat not in seen:photo('arrival_beat_'+str(owner.beat),g);seen.add(owner.beat)
                    g.handle_events([pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE,repeat=False),pygame.event.Event(pygame.KEYUP,key=pygame.K_SPACE)])
                if owner._rail_pending:
                    rail_samples.append(owner.rail.progress)
                    if tick%3==0 and len(frames)<100:
                        g.draw();frames.append(Image.frombytes('RGB',g.window.get_size(),pygame.image.tobytes(g.window,'RGB')))
            else:raise AssertionError(('Arrival did not finish',owner.to_dict(),owner.error))
            assert owner.completed and owner.rail.opened and rail_samples
            assert any(0<p<1 for p in rail_samples),'Rail animation was not observed'
            g.update(.8,(0,0),False);photo('arrival_return_to_exploration',g)
            if frames:gif(folder/'keeper_rail.gif',frames,150)
            report['story_preview_fixture']={'prerequisite_seeding':'SanctuaryArrival.prepare_preview, the production gallery checkpoint fixture; not a quest playthrough.',
                'actual_director_completed':True,'beats_traversed':sorted(visited_beats),'dialogue_beats_captured':sorted(seen),'care_actions_seen':sorted(care_seen),
                'keeper_rail_progress_samples':rail_samples,'returned_control':not owner.active,'post_scene':g.world.data['id']}
            # Enter/return through the existing E links after the actual rail
            # operation. No cave progression, battle or rewards are seeded.
            travel((1008,406),label='post_arrival_cave_apron')
            def press(key):g.handle_events([pygame.event.Event(pygame.KEYDOWN,key=key,repeat=False),pygame.event.Event(pygame.KEYUP,key=key)])
            for _ in range(300):
                g.update(.05,(0,0),False)
                if g.social.active:press(pygame.K_SPACE)
                if g.sanctuary_cave._available():break
            press(pygame.K_e)
            for _ in range(600):
                g.update(.05,(0,0),False)
                if g.social.active:press(pygame.K_SPACE)
                if g.world.data['id']=='sanctuary_cave' and g.sanctuary_cave._available():break
            assert g.world.data['id']=='sanctuary_cave','Post-arrival cave E entry failed'
            photo('cave_entry_after_rail',g)
            travel((288,1720),label='cave_return_approach')
            g.update(.6,(0,0),False);press(pygame.K_e);g.update(.6,(0,0),False)
            assert g.world.data['id']==RESERVE,'Cave E return failed'
            photo('cave_return_after_rail',g)
            report['story_preview_fixture']['cave_entry_return_via_production_E_links']=True
            print('Production arrival/care/rail preview completed.',flush=True)
        finally:g.music.stop();pygame.quit()
    assert fingerprint()==before,'Production input changed during review; rerun captures.'
    report['capture_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.suffix in ('.png','.gif')}
    (folder/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path,nargs='?',default=DEFAULT)
    capture(p.parse_args().output)
