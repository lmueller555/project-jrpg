"""Paired architecture review from the initialized production Game, not isolated art.

The static fixture places Caelan on declared safe review positions. Each image is
produced by Game.draw with live maps/actors/doors/materials and CameraDirector.
Entrance views use ordinary player tracking. Survey views use an explicitly
labelled static CameraDirector focus to fit tall buildings, retaining Caelan at
the entrance. These are composition fixtures, not an uninterrupted playthrough.
The fixture is emitted so later PRs can reuse exact player/camera/clock positions.

    python tools/capture_eldenmere_architecture_audit.py /tmp/before
    python tools/capture_eldenmere_architecture_audit.py /tmp/after \\
        --fixture /tmp/before/fixture.json --movement

--source-root can render another checkout (e.g. the unchanged merge baseline).
Disposable journeys/settings only; no user save library or production data writes.
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

BUILDINGS = ('sanctuary', 'mira', 'mill', 'school', 'halden', 'elira', 'venn',
             'home_a', 'home_b', 'home_c', 'liam_house', 'inn', 'item_shop')
# Explicit fixture positions and paths, not inferred from revised artwork.
CROSSINGS = {
    'upper_bridge': {'player': [852, 480], 'route': [[744,480],[936,480]], 'axis': 'x'},
    'main_bridge': {'player': [828, 1032], 'route': [[720,1032],[936,1032]], 'axis': 'x'},
    'mill_landing': {'player': [971, 354], 'route': [[971,390],[971,354]], 'axis': 'y'},
}


# Full-foot bridge limits: 48-unit surface minus a 12-unit-high foot probe.
# The 48-unit mill apron is wide, but its unchanged east doorway blocker at
# x984 requires the edge approach to fan in before y360. This does NOT claim
# x978 can walk straight through the narrow throat (it could not in baseline).
CROSSING_REVIEW_ROUTES = {
    'upper_bridge': {name: [[744,y],[936,y]] for name,y in
                     (('far',462),('center',480),('near',498))},
    'main_bridge': {name: [[720,y],[936,y]] for name,y in
                    (('far',1014),('center',1032),('near',1050))},
    'mill_landing': {name: [[x,390],[x,372],[971,372],[971,354]] for name,x in
                     (('west',960),('center',971),('east',984))},
}


def default_fixture(root):
    town = json.loads((root/'assets/maps/eldenmere/playable/map.json').read_text())
    doors = {r['id']: r for r in town['doors']}
    entities = {r['id']: r for r in town['entities']}
    result = {'version': 1, 'buildings': {}, 'crossings': CROSSINGS,
              'clock_ms': 0, 'window_size': [960,640]}
    for name in BUILDINGS:
        d, e = doors[name], entities[name]
        x, y = d['anchor']; ex, ey = e['position']; w, h = e['logical_size']
        # Declared view center, not a replacement camera implementation.
        result['buildings'][name] = {'player': [x,y+24],
            'survey_focus': [ex+w/2, ey+h/2+12], 'door_anchor': d['anchor'],
            'entity_rect': [ex,ey,w,h], 'depth_baseline': e['sort_y'],
            'interior': json.loads((root/d['destination']).read_text())['id']}
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(output, root, fixture=None, movement=False):
    root = root.resolve(); output = output.resolve(); output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0,str(root))
    import pygame
    from PIL import Image, ImageDraw, ImageFont
    from main import Game
    from tools.capture_sanctuary_reserve import path as safe_path
    from overworld_travel import WORLD_ID
    fixture = json.loads(json.dumps(fixture or default_fixture(root)))
    fixture.setdefault('crossing_review_routes', CROSSING_REVIEW_ROUTES)
    (output/'fixture.json').write_text(json.dumps(fixture,indent=2)+'\n')
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    report = {'revision': revision, 'source_root': str(root),
              'method': 'Game.draw production maps/bindings, native WorldCanvas 960x640, CameraDirector',
              'fixture': 'Static placements are disclosed review fixtures; movement uses Game.update. No replacement art or isolated art composites.',
              'limitations': ['Not an uninterrupted story playthrough.',
                             'Survey views explicitly focus the production camera to fit tall buildings.',
                             'Collision overlays are diagnostic annotations, not gameplay screenshots.',
                             'Contact boards are downscaled indexes; native PNGs are authoritative.'],
              'views': {}, 'movement': [], 'failures': [], 'save_continue': {},
              'sources': {}}
    for name in ('assets/maps/eldenmere/playable/map.json',
                 'assets/source/maps/eldenmere/town_hd/recipe.json',
                 'assets/maps/overworld/elden_vale/region.json',
                 'assets/maps/elden_vale_sanctuary/map.json', 'main.py','rendering.py'):
        if (root/name).is_file(): report['sources'][name] = digest(root/name)

    with tempfile.TemporaryDirectory(prefix='eldenmere-architecture-review-') as temporary:
        temporary=Path(temporary)
        save_path=temporary/'journey.json'; settings_path=temporary/'settings.json'
        g=Game(window_size=(960,640),fullscreen=False,start_on_title=True,
               save_path=save_path,settings_path=settings_path)
        try:
            g.on_title=False; g.opening.restore({'version':1,'stage':'disabled'})
            g.opening_fade=g.transfer_cooldown=0; g.audio.set_music(0); g.audio.set_effects(0)
            def station(scene, position, *, focus=None, reduced=False, clock=0):
                g.world=g._scene_by_id(scene); g.player.position.update(position)
                g.player.facing='back';g.player.moving=g.player.running=False;g.player.walk_ms=0
                g.party_travel.reset();g.transfer_cooldown=g.opening_fade=0
                g.elapsed_ms=clock; g.audio.set_reduced_motion(reduced)
                if hasattr(g.world,'update_grass'):g.world.update_grass(0,reduced_motion=reduced)
                else:g.world.reduced_motion=reduced
                g.camera.reset()
                if focus is not None:g.camera.focus(focus,0)
                g.location_seconds=g.saves.notice_seconds=0
                g.quest_ui.current_notice=None;g.quest_ui.notices.clear()
                return g.world.can_stand(g.player.position)

            def shot(name, *, focus=None, overlay=None):
                if focus is not None:g.camera.focus(focus,0)
                g.draw()
                filename=name+'.png'
                pygame.image.save(g.canvas.native,str(output/filename))
                report['views'][name]={'file': filename,'scene':g.world.data['id'],
                    'player':list(g.player.position),'facing':g.player.facing,
                    'camera':list(g.camera.position()),'scripted_camera':g.camera.scripted,
                    'elapsed_ms':g.elapsed_ms,'reduced_motion':g.audio.reduced_motion,
                    'safe_feet':g.world.can_stand(g.player.position),
                    'doors':{d.data['id']:{'state':d.state,'progress':d.progress} for d in g.world.doors},
                    'sha256':digest(output/filename)}
                if overlay:
                    im=Image.open(output/filename).convert('RGBA');layer=Image.new('RGBA',im.size)
                    d=ImageDraw.Draw(layer);cx,cy=g.camera.position()
                    def rect(bounds,color):
                        x,y,w,h=bounds;d.rectangle([round((x-cx)*2),round((y-cy)*2),round((x+w-cx)*2),round((y+h-cy)*2)],outline=color,width=2)
                    rect(overlay['entity_rect'],(60,225,255,255))
                    ax,ay=overlay['door_anchor'];d.ellipse(((ax-cx)*2-5,(ay-cy)*2-5,(ax-cx)*2+5,(ay-cy)*2+5),outline='yellow',width=2)
                    by=(overlay['depth_baseline']-cy)*2;d.line((0,by,960,by),fill=(255,0,255,170),width=2)
                    collision=Image.open(root/g.world.data['collision']).convert('L')
                    mask=collision.crop((cx,cy,cx+480,cy+320)).resize((960,640),Image.Resampling.NEAREST).point(lambda v:40 if v else 0)
                    red=Image.new('RGBA',im.size,(255,50,45,0));red.putalpha(mask)
                    im=Image.alpha_composite(im,red);im=Image.alpha_composite(im,layer)
                    ImageDraw.Draw(im).text((10,10),'DIAGNOSTIC: collision red; canvas cyan; depth magenta; threshold yellow',fill='white')
                    im.convert('RGB').save(output/(name+'_collision_overlay.png'))

            for name,spec in fixture['buildings'].items():
                for reduced in (False,True):
                    suffix='reduced' if reduced else 'normal'
                    station('eldenmere.playable',spec['player'],reduced=reduced)
                    for door in g.town.doors:door.update(None,10)
                    shot('building_'+name+'_entrance_'+suffix)
                    shot('building_'+name+'_survey_'+suffix,focus=spec['survey_focus'],overlay=spec if not reduced else None)
                # Real reversible Door controller, surrounding scene retained.
                station('eldenmere.playable',spec['player'],focus=spec['survey_focus'])
                door=next(d for d in g.town.doors if d.data['id']==name)
                door.update(None,10)
                for state,near,seconds in [('opening',True,.15),('open',True,.4),('closing',False,.15),('closed',False,.4)]:
                    door.update(spec['player'] if near else None,seconds)
                    shot('building_'+name+'_door_'+state)
                interior=g._scene_by_id(spec['interior'])
                station(spec['interior'],interior.data['spawn'])
                shot('interior_'+name+'_arrival_normal')
                station(spec['interior'],interior.data['spawn'],reduced=True)
                shot('interior_'+name+'_arrival_reduced')
            # Additional retained Serene household rooms, plus future actual inn floor.
            for room in ('sanctuary_bedroom','sanctuary_dining','inn_upstairs','inn_guest_floor'):
                if room not in g.town.data['interior_scenes']:continue
                scene=g._scene_by_id(room);station(room,scene.data['spawn']);shot('interior_'+room+'_arrival')
            for name,spec in fixture['crossings'].items():
                for reduced in (False,True):
                    for phase in range(6):
                        station('eldenmere.playable',spec['player'],reduced=reduced,clock=phase*200)
                        shot('crossing_'+name+('_reduced_' if reduced else '_normal_')+str(phase))
            # Native real-scene rail-edge views use the maximum full-foot bridge
            # centers; the mill apron edges remain below its existing throat.
            for name,lanes in fixture['crossing_review_routes'].items():
                for lane,route in lanes.items():
                    if name=='mill_landing':point=[route[0][0],372]
                    else:point=[850,route[0][1]]
                    for reduced in (False,True):
                        station('eldenmere.playable',point,reduced=reduced)
                        g.player.facing='front'
                        shot('crossing_'+name+'_lane_'+lane+('_reduced' if reduced else '_normal'))
            # Exact production regional/detailed consumers, not synthetic montage.
            for name,scene,point in [('antlers_regional',WORLD_ID,[93*24,-70*24]),
                                     ('antlers_detailed','elden_vale_sanctuary',[1100,270]),
                                     ('antlers_town_north','eldenmere.playable',[384,320]),
                                     ('antlers_town_north_lane','eldenmere.playable',[600,180]),
                                     ('southern_lane','eldenmere.playable',[528,1488])]:
                station(scene,point);shot(name)
                report['views'][name]['landmarks']=[r['id'] for r in g.world.landmarks.records]
            if movement:
                def follow(points, running=False, expected=None, frames=None):
                    origin=g.world;trace=[]
                    for goal in points:
                        goal=pygame.Vector2(goal)
                        for n in range(2400):
                            if expected and g.world.data['id']==expected:return trace
                            assert g.world is origin,('Unexpected scene',g.world.data['id'])
                            delta=goal-g.player.position
                            if delta.length()<.5:break
                            before=g.player.position.copy();dt=min(1/30,delta.length()/(108 if running else 72))
                            g.update(dt,delta,running)
                            if expected and g.world.data['id']==expected:return trace
                            assert g.player.position!=before,('Stalled',list(before),list(goal))
                            assert g.world.can_stand(g.player.position),('Unsafe',list(g.player.position))
                            trace.append(list(g.player.position))
                            if frames is not None and len(trace)%3==0:
                                g.draw();frames.append(Image.frombytes('RGB',(960,640),pygame.image.tobytes(g.canvas.native,'RGB')))
                        else:raise AssertionError('Movement budget')
                    if expected:raise AssertionError(('Missing transfer',expected))
                    return trace
                for name,lanes in fixture['crossing_review_routes'].items():
                    for lane,declared_route in lanes.items():
                        for running in (False,True):
                            for reverse in (False,True):
                                route=list(reversed(declared_route)) if reverse else declared_route
                                label=name+'_lane_'+lane+('_run' if running else '_walk')+('_return' if reverse else '')
                                try:
                                    station('eldenmere.playable',route[0]);frames=[]
                                    assert g.town.can_stand(g.player.position),('Blocked route fixture',route[0])
                                    trace=follow(route[1:],running,frames=frames)
                                    report['movement'].append({'label':label,'trace':trace,'passed':True,
                                        'player_probe':list(g.town.probe_size),'declared_route':route})
                                    if frames:
                                        frames[len(frames)//2].save(output/(label+'_native.png'))
                                        frames[0].save(output/(label+'.gif'),save_all=True,append_images=frames[1:],duration=100,loop=0)
                                except AssertionError as error:report['failures'].append({'label':label,'error':str(error)})
                for name,spec in fixture['crossings'].items():
                    for running in (False,True):
                        for reverse in (False,True):
                            route=list(reversed(spec['route'])) if reverse else spec['route']
                            label=name+('_run' if running else '_walk')+('_return' if reverse else '')
                            try:
                                station('eldenmere.playable',route[0]);frames=[]
                                trace=follow(route[1:],running,frames=frames)
                                report['movement'].append({'label':label,'trace':trace,'passed':True})
                                if frames:
                                    frames[0].save(output/(label+'.gif'),save_all=True,append_images=frames[1:],duration=100,loop=0)
                            except AssertionError as error:report['failures'].append({'label':label,'error':str(error)})
                    station('eldenmere.playable',spec['player'])
                    expected=g.journey_snapshot();assert g.save_progress(),g.save_error
                    other=Game(window_size=(960,640),fullscreen=False,start_on_title=True,save_path=save_path,settings_path=settings_path)
                    try:
                        assert other.begin_journey(True),other.save_error
                        actual=other.journey_snapshot()
                        keys=('quests','party','inventory','player','overworld')
                        checked=[k for k in keys if k in expected]
                        assert all(expected[k]==actual[k] for k in checked),(name,checked)
                        assert other.world.can_stand(other.player.position)
                        report['save_continue'][name]={'passed':True,'exact_keys':checked,'player':actual['player']}
                    finally:other.music.stop()
                # Every door uses normal movement in both directions; no NPC deletion.
                for name,spec in fixture['buildings'].items():
                    try:
                        station('eldenmere.playable',spec['player']);d=next(d for d in g.town.doors if d.data['id']==name)
                        g.update(.5,(0,0),False)
                        follow([d.data['anchor']],expected=spec['interior'])
                        g.update(.6,(0,0),False)
                        out=next(d for d in g.world.doors if d.data['id']=='courtyard')
                        follow(safe_path(g.world,g.player.position,out.data['anchor']),expected='eldenmere.playable')
                        report['movement'].append({'label':'door_roundtrip_'+name,'passed':True,'returned':list(g.player.position)})
                    except AssertionError as error:report['failures'].append({'label':'door_roundtrip_'+name,'error':str(error)})
                # Existing public lane and expanded south contact are real updates.
                try:
                    station('eldenmere.playable',[528,1260]);g.transfer_cooldown=0
                    trace=follow([[528,1620]],expected=WORLD_ID)
                    assert any(y>1490 for x,y in trace)
                    report['movement'].append({'label':'expanded_south_departure','passed':True,'trace':trace})
                    returning=[]
                    for _ in range(180):
                        g.update(1/60,(0,-1),False);returning.append(list(g.player.position))
                        if g.world is g.town:break
                    assert g.world is g.town,'Regional north input did not return to town'
                    assert list(g.player.position)==g.town.data['overworld_exit']['return_position']
                    g.update(.6,(0,0),False);assert g.world is g.town,'Immediate return bounce'
                    g.camera.reset();shot('actual_southern_return')
                    report['movement'].append({'label':'expanded_south_return','passed':True,'trace':returning,
                        'safe_feet':g.town.can_stand(g.player.position),'facing':g.player.facing})

                except AssertionError as error:report['failures'].append({'label':'expanded_south_departure','error':str(error)})
            (output/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
            # A labelled downscaled contact board is an index, never native evidence.
            for family,prefix in [('exteriors','building_'),('interiors','interior_'),('crossings','crossing_')]:
                names=[n for n in report['views'] if n.startswith(prefix) and
                       (n.endswith('_survey_normal') if family=='exteriors' else n.endswith('_arrival_normal') if family=='interiors' else n.endswith('_normal_0'))]
                board=Image.new('RGB',(960,((len(names)+2)//3)*238),(20,30,28));draw=ImageDraw.Draw(board)
                for i,name in enumerate(names):
                    frame=Image.open(output/(name+'.png'));frame.thumbnail((320,214),Image.Resampling.NEAREST)
                    x,y=i%3*320,i//3*238;board.paste(frame,(x,y));draw.text((x+4,y+216),name.replace('building_','').replace('_survey_normal','').replace('_arrival_normal',''),fill='white')
                if names:board.save(output/(family+'_contact_board_DOWNSCALED.png'))
            (output/'README.md').write_text('# Actual Game architecture review\n\n'
                f'Source commit: `{revision}`. Native PNGs are unmodified `Game.draw` world buffers at 960×640.\n\n'
                'Static fixture positions, camera bounds, clocks, door states and hashes are in observations.json. '
                'fixture.json fixes the same review positions across PRs. Entrance images use ordinary tracking; '
                'survey images use an explicitly labelled CameraDirector focus to fit tall buildings, with Caelan still at the entrance. '
                'Collision overlays and downscaled contact boards are diagnostic/index images, not native gameplay evidence. '
                'Journeys and settings are disposable. Regional and detailed antlers use their real production scenes.\n\n'
                f'Views: {len(report["views"])}. Movement checks: {len(report["movement"])}. Failures: {len(report["failures"])}.\n')
            print(json.dumps({'output':str(output),'revision':revision,'views':len(report['views']),'movement':len(report['movement']),'failures':report['failures']},indent=2))
        finally:
            g.music.stop();pygame.quit();gc.collect()
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--fixture',type=Path)
    parser.add_argument('--movement',action='store_true')
    args=parser.parse_args()
    capture(args.output,args.source_root,json.loads(args.fixture.read_text()) if args.fixture else None,args.movement)

if __name__=='__main__':main()
