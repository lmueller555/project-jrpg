"""Production causeway/arch gameplay review; disposable saves and no scenery overrides.

Also runs the complete production Antlers/transfer/story regression into a
separate full evidence bank. No quest is seeded in the causeway exploration.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from time import perf_counter
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy');os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image
from main import Game
from rendering import WorldCanvas
from npc_routines import find_path
from overworld_travel import TOWN_EXIT,TOWN_RETURN,WORLD_ID
from tools.capture_overworld_sanctuary import regional_path
from tools.capture_sanctuary_reserve import state
from tools.capture_elden_vale_antlers import fingerprint as antler_fingerprint,ownership,capture as capture_antlers
from tools.capture_elden_vale_hd_integration import gif
DEFAULT=ROOT/'docs/reviews/elden_vale_causeway'

def fingerprint():
    result=antler_fingerprint()
    for p in [Path(__file__).resolve(),ROOT/'overworld_travel.py',ROOT/'overworld_environment.py',ROOT/'tools/build_elden_vale_overworld.py',ROOT/'tools/elden_vale_landmark_bindings.py']:
        result[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    return result

def rect_distance(rect,a,b):
    if rect.clipline(a,b):return 0.
    def point_segment(p):
        dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
        t=max(0.,min(1.,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)) if den else 0
        return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
    def point_rect(p):return math.hypot(max(rect.left-p[0],0,p[0]-rect.right),max(rect.top-p[1],0,p[1]-rect.bottom))
    return min(point_rect(a),point_rect(b),*(point_segment(p) for p in [rect.topleft,rect.topright,rect.bottomleft,rect.bottomright]))

def capture(folder,regression_folder):
    folder.mkdir(parents=True,exist_ok=True);before=fingerprint()
    report={'source':'Actual Game, final production recipe/HD bindings and collision. No fixture landmarks, support masks, replacement art or teleport traversal.',
        'initialization':'Disposable New Game town spawn; opening director disabled. No causeway quest/party/equipment seeding.',
        'source_sha256':before,'views':{},'travel':[],'portal_diagonals':[],'saves':{},
        'limitations':['Regional miniature scale does not display passive detailed followers; detailed following is separately rerun.',
                       'Causeway and northeastern Antlers do not share one ordinary viewport; context is recorded by actual regional travel, not a fabricated panorama.',
                       'The separate arrival/care/rail regression uses the explicitly labelled production prerequisite preview, not an uninterrupted quest playthrough.',
                       'SDL-dummy render timings exclude simulation/display/UI and are not an FPS guarantee.']}
    with tempfile.TemporaryDirectory(prefix='causeway-review-') as temporary:
        tmp=Path(temporary);g=Game(window_size=(960,640),fullscreen=False,start_on_title=True,save_path=tmp/'journey.json',settings_path=tmp/'settings.json')
        try:
            g.on_title=False;g.opening.restore({'version':1,'stage':'disabled'});g.opening_fade=g.transfer_cooldown=0
            g.audio.set_music(0);g.audio.set_effects(0)
            baseline=copy.deepcopy(state(g));owners=ownership(g)
            def photo(name):
                g.location_seconds=g.saves.notice_seconds=0;g.quest_ui.current_notice=None;g.quest_ui.notices.clear();g.draw()
                pygame.image.save(g.window,str(folder/(name+'.png')))
                report['views'][name]={'scene':g.world.data['id'],'player':list(g.player.position),'camera':list(g.camera.position()),'source':'production Game.draw'}
            def follow(points,*,running=False,label=None,transfer=None,frames=None):
                scene=g.world.data['id'];trace=[]
                for goal in points:
                    goal=pygame.Vector2(goal)
                    for _ in range(2400):
                        if transfer and g.world.data['id']==transfer:break
                        assert g.world.data['id']==scene,('Unexpected transfer',scene,g.world.data['id'])
                        delta=goal-g.player.position
                        if delta.length()<.5:break
                        old=g.player.position.copy();dt=min(1/30,delta.length()/(108 if running else 72))
                        g.update(dt,delta,running)
                        if transfer and g.world.data['id']==transfer:break
                        assert g.player.position!=old,('Stalled',label,list(old),list(goal))
                        assert g.world.can_stand(g.player.position),('Invalid full-foot position',label,list(g.player.position))
                        trace.append(list(g.player.position))
                        if frames is not None and len(trace)%6==0 and len(frames)<120:
                            g.draw();frames.append(Image.frombytes('RGB',g.window.get_size(),pygame.image.tobytes(g.window,'RGB')))
                    else:raise AssertionError(('Movement budget',label,list(goal)))
                    if transfer and g.world.data['id']==transfer:break
                if transfer:
                    assert g.world.data['id']==transfer;g.update(.6,(0,0),False)
                if label:report['travel'].append({'label':label,'running':running,'scene':scene,'trace':trace,'transfer':transfer})
            def travel(point,**kwargs):
                follow(regional_path(g.world,g.player.position,point),**kwargs)
                follow([point])
            route=find_path(g.town,g.player.position,TOWN_EXIT,g.town.probe_size,None);assert route
            follow(route,transfer=WORLD_ID,label='actual_town_departure')
            departure=report['travel'][-1]
            assert max(p[1] for p in departure['trace'])>=TOWN_EXIT[1]-30,'Town transferred at an obsolete interior trigger'
            report['expanded_town_contact']={'imported_exit':list(TOWN_EXIT),'imported_return':list(TOWN_RETURN),
                'greatest_actual_town_departure_y':max(p[1] for p in departure['trace']),
                'walked_through_expanded_southern_business_lane':True}
            world=g.world;assert tuple(world.probe_size)==(24,12)
            road=next(r for r in world.region['roads'] if r['id']=='south_town_road')
            route=[pygame.Vector2(x*24,y*24) for x,y in road['points'] if -9<=y<=14]
            assert len(route)>20
            props={p['id']:p for p in world.environment.authored if p['id'].startswith('causeway_')}
            assert {'causeway_arch_left','causeway_arch_right'}<=set(props),'Production causeway support registry missing'
            report['props']=props;report['probe_size']=list(world.probe_size)
            rectangles={}
            for identifier,p in props.items():
                if p.get('solid'):
                    x,y=p['position'];w,h=p['solid'];rectangles[identifier]=pygame.Rect(round(x)-w//2,round(y)-h//2,w,h)
            reserved=[[x*24,y*24] for x,y in world.region['design_layout']['causeway']['points']]
            actual=[[x*24,y*24] for x,y in road['points']]
            clearance={name:min(rect_distance(rect,a,b) for points in [reserved,actual] for a,b in zip(points,points[1:])) for name,rect in rectangles.items()}
            for name in ['causeway_arch_left','causeway_arch_right']:assert clearance[name]>=48,(name,clearance[name])
            report['explicit_support_footprints']={name:list(rect) for name,rect in rectangles.items()}
            report['minimum_rect_edge_to_road_centerline']=clearance
            # Collision comes from explicit props. Source alpha is only checked
            # as visual evidence at the declared physical contact, never used to
            # manufacture a mask or enlarge a footprint.
            contacts={};native=[]
            for name,p in props.items():
                rec=world._art['props'][p['key']];image,anchor=world._prop_image(p['key'])
                assert isinstance(image,WorldCanvas),(name,'Not native')
                raw=pygame.image.load(str(ROOT/rec['image'])).convert_alpha()
                assert pygame.image.tobytes(image.native,'RGBA')==pygame.image.tobytes(raw,'RGBA'),name
                native.append(name)
                if (name.startswith('causeway_arch_') or name=='causeway_bone_fragment') and p.get('solid'):
                    rect=rectangles[name];x,y=p['position'];local=(round((rect.centerx-(round(x)-anchor[0]))*2),round((rect.centery-(round(y)-anchor[1]))*2))
                    assert image.native.get_at(local).a>0,(name,'Declared contact looks empty',local)
                    assert not world.can_stand(rect.center),(name,'Visible pier base is not physical')
                    contacts[name]={'position':list(p['position']),'anchor':list(anchor),'collision':list(rect),'declared_contact_native_sample':list(local),'opaque_at_declared_contact':True,'base_blocks_full_probe':True}
            for item in world.landmarks.records:
                if item['id'].startswith('causeway_'):
                    image=world.landmarks.image(item);raw=pygame.image.load(str(ROOT/item['image'])).convert_alpha()
                    assert pygame.image.tobytes(image.native,'RGBA')==pygame.image.tobytes(raw,'RGBA');native.append(item['id'])
            report['support_art_registration']=contacts;report['native_source_checks']={'records':native,'rgba_mismatches':0}
            # Twelve complete generated-road sweeps. Alternate direction to
            # change lanes only on open endpoints, never teleporting between runs.
            pattern=[(-30,False),(0,True),(30,False),(-30,True),(0,False),(30,True)]
            for running in [False,True]:
                for lane,reverse in pattern:
                    points=[p+pygame.Vector2(lane,0) for p in (reversed(route) if reverse else route)]
                    travel(points[0],label='ordinary_lane_reposition')
                    follow(points[1:],running=running,label='full_route_'+('run' if running else 'walk')+'_'+str(lane)+'_'+str(reverse))
            report['full_route_sweeps']=12
            # Full support approach, explicit collision-boundary diagonals,
            # walking/running beneath the overhead lintel in both directions.
            frames=[]
            portal=[p for p in route if p.y<=96]
            for running,reverse in [(False,False),(False,True),(True,False),(True,True)]:
                points=list(reversed(portal)) if reverse else portal
                travel(points[0]);follow(points[1:],running=running,label='portal_clip_'+str(running)+'_'+str(reverse),frames=frames)
            if frames:gif(folder/'portal_walk_run.gif',frames,200)
            save_points={}
            for name in ['causeway_arch_left','causeway_arch_right']:
                rect=rectangles[name]
                point=(rect.right+14,rect.centery) if name.endswith('left') else (rect.left-14,rect.centery)
                travel(point);g.camera.reset();photo('near_'+name)
                save_points[name]=point
                case=[]
                for direction in [(-1,-1),(1,1),(-1,1),(1,-1)]:
                    trace=[];blocked=0
                    for _ in range(8):
                        old=g.player.position.copy();g.update(1/30,direction,True);assert world.can_stand(g.player.position)
                        blocked+=g.player.position==old;trace.append(list(g.player.position))
                    case.append({'direction':list(direction),'trace':trace,'blocked_updates':blocked})
                report['portal_diagonals'].append({'support':name,'cases':case})
            save_points['beneath_lintel']=(237,-136)
            for name,point in save_points.items():
                travel(point);g.camera.reset();expected=g.journey_snapshot();assert g.save_progress(),g.save_error
                restored=Game(window_size=(960,640),fullscreen=False,start_on_title=True,save_path=tmp/'journey.json',settings_path=tmp/'settings.json')
                try:
                    assert restored.begin_journey(True);snapshot=restored.journey_snapshot()
                    for key in ['player','quests','party','dialogue_flags','overworld']:assert snapshot[key]==expected[key],(name,key)
                    assert ownership(restored)==owners
                    report['saves'][name]={'exact_keys':['player','quests','party','dialogue_flags','overworld'],'player':snapshot['player'],'unique_actor_ownership':True}
                finally:restored.music.stop()
            # Compatibility diagnostic only: synthesize a historical save at an
            # off-road point now occupied by a newly authored pier. This never
            # relocates the live traversal actor or excuses corridor narrowing.
            report['legacy_inside_support_fixture']={}
            for name in ['causeway_arch_left','causeway_arch_right']:
                legacy=copy.deepcopy(g.journey_snapshot());legacy['player']['position']=list(rectangles[name].center)
                legacy_path=tmp/(name+'_historical.json');legacy_path.write_text(json.dumps(legacy))
                restored=Game(window_size=(960,640),fullscreen=False,start_on_title=True,save_path=legacy_path,settings_path=tmp/'settings.json')
                try:
                    assert restored.begin_journey(True)
                    actual=restored.journey_snapshot()
                    assert actual['player']['position']!=legacy['player']['position']
                    assert restored.world.can_stand(restored.player.position)
                    for key in ['quests','party','dialogue_flags','overworld']:assert actual[key]==legacy[key]
                    report['legacy_inside_support_fixture'][name]={'synthetic_old_position':legacy['player'],
                        'restored_position':actual['player'],'existing_generic_clear_landing_fallback_used':True,
                        'scope':'Legacy-file diagnostic only. Not an actual traversal, new migration, new save field, or permission to narrow routes.'}
                finally:restored.music.stop()
            travel(save_points['beneath_lintel']);g.camera.reset();photo('beneath_lintel')
            def overhead(actors):
                out=WorldCanvas((480,320),pygame.SRCALPHA);out.fill((0,0,0,0))
                world.landmarks.draw(out,g.camera.position(),'overhead',actors=actors)
                return pygame.image.tobytes(out.native,'RGBA')
            cut=overhead([g.player]);assert cut!=overhead([]),'Lintel cutaway not exercised'
            g.audio.set_reduced_motion(True);g.update(0,(0,0),False);assert overhead([g.player])==cut
            report['overhead_cutaway_working_bytes']=world.landmarks.working_bytes
            photo('reduced_motion_portal');g.elapsed_ms+=1500;assert overhead([g.player])==cut;g.audio.set_reduced_motion(False)
            report['reduced_motion_cutaway_stable']=True
            def world_pixels():
                out=WorldCanvas((480,320));world.draw(out,g.camera.position(),g.player,g.elapsed_ms,False)
                return pygame.image.tobytes(out.native,'RGB')
            report['freeze_resume']={}
            for mode in ['pause','focus_loss']:
                saved=(g.elapsed_ms,tuple(g.player.position),world_pixels())
                if mode=='pause':g.pause.is_open=True
                else:g._music_focused=False
                g.update(.4,(0,1),True);assert (g.elapsed_ms,tuple(g.player.position),world_pixels())==saved
                g.pause.is_open=False;g._music_focused=True;report['freeze_resume'][mode]=True
            elapsed=g.elapsed_ms;g.update(.1,(0,0),False);assert g.elapsed_ms>elapsed
            # Transient isolated flag permutations, not quest updates or saved
            # bridge repair. Always restore the live world flags afterward.
            original=world._flags;repair=world.region['bridge']['repair_flag'];flags=[]
            try:
                for extra in [set(),{'CH01_OPENING_REGION_RELEASED'},{repair},{'CH01_OPENING_REGION_RELEASED',repair}]:
                    world.set_progress(set(original)|extra)
                    assert world._bridge_repaired()==(repair in (set(original)|extra))
                    for gate in world.gates:assert not world.can_stand(gate['position'])
                    assert world.can_stand((236,-24))
                    for name in ['causeway_arch_left','causeway_arch_right']:assert not world.can_stand(rectangles[name].center)
                    flags.append({'extra_flags':sorted(extra),'bridge_repaired':world._bridge_repaired(),'gates_still_blocked':True,'portal_and_supports_unchanged':True})
            finally:world.set_progress(original)
            report['isolated_flag_independence_probe']=flags
            report['profile']={}
            for name,point in [('portal',(236,-36)),('lintel_cutaway',(237,-136)),('joined_remnant',(-408,214)),('resting_edge',(-500,438)),('buried_masonry',(-692,290)),('rooted_foundation',(-800,490))]:
                travel(point);g.camera.reset();photo(name)
                out=WorldCanvas((480,320))
                for _ in range(24):world.draw(out,g.camera.position(),g.player,g.elapsed_ms,False)
                samples=[]
                for _ in range(20):
                    t=perf_counter();world.draw(out,g.camera.position(),g.player,g.elapsed_ms,False);samples.append((perf_counter()-t)*1000)
                control=[];draw=world.landmarks.draw
                try:
                    world.landmarks.draw=lambda *args,**kwargs:None
                    for _ in range(20):
                        t=perf_counter();world.draw(out,g.camera.position(),g.player,g.elapsed_ms,False);control.append((perf_counter()-t)*1000)
                finally:world.landmarks.draw=draw
                assert world.cache_stats['render_bytes']<=world._render_cache.limit
                assert world.landmarks.sources.bytes<=world.landmarks.sources.budget
                report['profile'][name]={'world_mean_ms':sum(samples)/len(samples),'world_max_ms':max(samples),
                    'same_revision_landmark_pass_disabled_mean_ms':sum(control)/len(control),'cache':world.cache_stats,
                    'landmark_source_bytes':world.landmarks.sources.bytes,'landmark_source_budget':world.landmarks.sources.budget,
                    'last_viewport_working_bytes':world.landmarks.working_bytes,
                    'scope':'SDL dummy, world-only. Control still includes ordinary props/piers; not a historical PR2 executable or a capture.'}
            # Also test the preserved upstream expanded-town return rather than
            # accepting any region->town scene change at an obsolete landing.
            rect=world.town_entry_rect
            travel((rect.centerx,rect.bottom+36),label='causeway_return_to_town_contact')
            follow([(rect.centerx,rect.bottom-2)],transfer=g.town.data['id'],label='actual_expanded_town_return')
            assert g.player.position.distance_to(TOWN_RETURN)<48,('Obsolete town return landing',list(g.player.position),TOWN_RETURN)
            g.camera.reset();photo('expanded_town_return')
            report['expanded_town_contact']['actual_return']=list(g.player.position)
            assert state(g)==baseline;assert ownership(g)==owners
            print('Production full causeway/portal movement, contacts, saves and flags passed.',flush=True)
        finally:g.music.stop();pygame.quit()
    # All production transfers, detailed followers and arrival/care/rail/cave
    # review are rerun after causeway activation, rather than citing old results.
    regression=capture_antlers(regression_folder)
    report['production_antlers_and_transfers_regression']={
        'completed':True,'source_sha256':regression['source_sha256'],
        'movement_segments':len(regression['movement']),'movement_updates':sum(len(x['trace']) for x in regression['movement']),
        'transfers':regression['transfers'],'saves':regression['save_continue'],
        'unique_ownership_and_progression':regression['production_roundtrip_progression_and_ownership_preserved'],
        'temporary_companion_fixture':regression['temporary_companion_fixture'],
        'story_preview_fixture':regression['story_preview_fixture'],
        'native_source_preservation':regression['native_source_preservation']}
    # A native context frame from the actual production regional journey, not a
    # synthetic combined composition of two geographically distant landmarks.
    (folder/'pale_antlers_context.png').write_bytes((regression_folder/'regional_approach.png').read_bytes())
    assert fingerprint()==before,'Production input changed during capture; rerun.'
    report['capture_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.suffix in ['.png','.gif']}
    (folder/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path,nargs='?',default=DEFAULT)
    parser.add_argument('--regression-output',type=Path,default=Path('/tmp/causeway-antlers-regression'))
    args=parser.parse_args();capture(args.output,args.regression_output)
