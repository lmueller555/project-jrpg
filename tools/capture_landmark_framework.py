"""Disposable actual-Game landmark fixtures; never writes production placements.

Not finished regional composition or an uninterrupted quest playthrough. New
scenery exists only on initialized world instances for these renderer probes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from time import perf_counter
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pygame
from PIL import Image, ImageChops
from main import Game
from landmark_layers import LandmarkLayers
from rendering import WorldCanvas
from tools.capture_elden_vale_hd_integration import place, shot, owner_counts, gif

MANIFEST = ROOT/'assets/terrain/overworld/elden_vale/signature_landscape_hd/manifest.json'
DEFAULT = ROOT/'docs/reviews/elden_vale_landmark_framework'

def record(name, position, layer):
    source = json.loads(MANIFEST.read_text())['assets'][name]
    return {'id': 'fixture_'+name, 'image':source['image'],
            'logical_size':source['logical_size'], 'artwork_pixels_per_world_pixel':2,
            'position':list(position), 'layer':layer, 'collision':'none',
            **({'occlusion_mask':source['occlusion_mask']} if source.get('occlusion_mask') else {})}

def changed(a, b):
    raw = ImageChops.difference(a.convert('RGB'), b.convert('RGB')).tobytes()
    return sum(any(raw[i:i+3]) for i in range(0, len(raw), 3))

def capture(folder):
    folder.mkdir(parents=True, exist_ok=True)
    tracked = [Path(__file__).resolve(), ROOT/'rendering.py', ROOT/'camera_director.py',
               ROOT/'main.py', ROOT/'overworld_world.py', ROOT/'landmark_layers.py', MANIFEST,
               ROOT/'assets/maps/overworld/elden_vale/region.json',
               ROOT/'assets/maps/elden_vale_sanctuary/map.json', ROOT/'assets/maps/elden_vale_sanctuary/collision.png']
    for asset in json.loads(MANIFEST.read_text())['assets'].values():
        tracked.append(ROOT/asset['image'])
        if asset.get('occlusion_mask'):tracked.append(ROOT/asset['occlusion_mask'])
    hashes = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}
    report = {'fixture':'Disposable initialized Game; fixture placements only in memory. Fixed starts are explicit, subsequent motion uses Game.update.',
              'actual_renderer':True, 'display_size':[960,640], 'source_hashes':hashes,
              'limitations':['Not production activation, final placement approval, or uninterrupted story playthrough.',
                             'Timing excludes simulation/display/UI and is hardware-specific SDL-dummy world rendering.']}
    with tempfile.TemporaryDirectory(prefix='landmark-framework-') as tmp:
        temporary = Path(tmp)
        game = Game(window_size=(960,640), fullscreen=False, start_on_title=True,
                    save_path=temporary/'journey.json', settings_path=temporary/'settings.json')
        try:
            game.on_title=False;game.opening.restore({'version':1,'stage':'disabled'})
            game.opening_fade=game.transfer_cooldown=0
            game.audio.set_music(0);game.audio.set_effects(0)
            world=game.overworld_world
            place(game,(10,-1))
            report['town_actor_owners']=owner_counts(game)
            report['regional_probe_size']=list(world.probe_size)
            original = world.landmarks
            # Reuse a real lintel drawing, centered over the player for a cutaway
            # stress fixture. No supports, collision or permanent arch placement.
            source=record('arch_lintel',(0,0),'overhead')
            with Image.open(ROOT/source['image']) as opened:
                alpha=opened.convert('RGBA').getchannel('A')
                candidates=[(x/2,y/2) for y in range(alpha.height) for x in range(alpha.width) if alpha.getpixel((x,y))>200]
            center=min(candidates,key=lambda p:(p[0]-96)**2+(p[1]-40)**2)
            feet=tuple(game.player.position)
            source['position']=[feet[0]-center[0],feet[1]-18-center[1]]
            world.landmarks=LandmarkLayers(ROOT,[source])
            report['overhead_fixture']=source
            normal=shot(game,folder,'regional_local_cutaway')
            game.audio.set_reduced_motion(True);game.draw()
            reduced=shot(game,folder,'regional_reduced_motion')
            # World-only visibility output is time independent; terrain animation
            # differences do not contaminate the cutaway-only assertion.
            def isolated():
                canvas=WorldCanvas((480,320),pygame.SRCALPHA);canvas.fill((0,0,0,0))
                world.landmarks.draw(canvas,game.camera.position(),'overhead',actors=[game.player])
                return pygame.image.tobytes(canvas.native,'RGBA')
            first=isolated();game.elapsed_ms+=1200;assert isolated()==first
            report['reduced_motion_cutaway_stable']=True
            game.audio.set_reduced_motion(False)
            no_actor=WorldCanvas((480,320),pygame.SRCALPHA);no_actor.fill((0,0,0,0))
            world.landmarks.draw(no_actor,game.camera.position(),'overhead')
            assert pygame.image.tobytes(no_actor.native,'RGBA')!=first, 'Fixture did not exercise local cutaway'
            report['cutaway_exercised']=True
            expected_native=pygame.Surface((960,640),pygame.SRCALPHA)
            rect=pygame.Rect(source['position'],source['logical_size'])
            expected_native.blit(pygame.image.load(str(ROOT/source['image'])),
                (round((source['position'][0]-game.camera.position()[0])*2),round((source['position'][1]-game.camera.position()[1])*2)))
            assert pygame.image.tobytes(expected_native,'RGBA')==pygame.image.tobytes(no_actor.native,'RGBA')
            report['native_source_rgba_mismatches']=0
            pygame.image.save(no_actor.native,str(folder/'lintel_native_detail.png'))
            # A real player sprite at a story override must receive assistance
            # at that override, not at the stale exploration position.
            game.player.story_position=pygame.Vector2(feet[0]+24,feet[1])
            game.camera.reset();shot(game,folder,'story_position_cutaway')
            report['story_position_fixture']={'exploration':list(feet),'story':list(game.player.story_position)}
            game.player.story_position=None;game.camera.reset()
            report['freeze_resume']={}
            def world_pixels():
                target=WorldCanvas((480,320))
                world.draw(target,game.camera.position(),game.player,game.elapsed_ms,False)
                return pygame.image.tobytes(target.native,'RGB')
            for mode in ('pause','focus_loss'):
                before=(game.elapsed_ms,tuple(game.player.position),world_pixels())
                if mode=='pause':game.pause.is_open=True
                else:game._music_focused=False
                game.update(.4,(1,0),True)
                assert (game.elapsed_ms,tuple(game.player.position),world_pixels())==before
                game.pause.is_open=False;game._music_focused=True
                report['freeze_resume'][mode]={'time_and_position_preserved':True,'native_cutaway_render_unchanged':True}
            elapsed=game.elapsed_ms;game.update(.05,(0,0),False)
            assert game.elapsed_ms>elapsed
            report['freeze_resume']['resumes']=True
            # Walk and run beneath the same disposable span, both directions.
            frames=[];traces=[]
            start=game.player.position.copy()
            for running,direction in [(False,(0,-1)),(False,(0,1)),(True,(0,-1)),(True,(0,1))]:
                trace=[]
                for tick in range(18):
                    before=game.player.position.copy();game.update(1/30,direction,running)
                    assert world.can_stand(game.player.position)
                    assert game.player.position!=before, ('Stalled fixture traversal',running,direction)
                    trace.append(list(game.player.position))
                    if tick%2==0:
                        game.draw();frames.append(Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB')))
                traces.append({'running':running,'direction':list(direction),'trace':trace})
            gif(folder/'span_walk_run.gif',frames,67);report['span_traversal']=traces
            # Save under a fixture overhead. No scene metadata or save fields added.
            expected=game.journey_snapshot();assert game.save_progress(),game.save_error
            restored=Game(window_size=(960,640),fullscreen=False,start_on_title=True,
                          save_path=temporary/'journey.json',settings_path=temporary/'settings.json')
            try:
                assert restored.begin_journey(True)
                actual=restored.journey_snapshot()
                for key in ('quests','party','dialogue_flags','player','overworld'):
                    assert actual[key]==expected[key],key
                assert owner_counts(restored)==report['town_actor_owners']
                report['save_continue_preserved']=['quests','party','dialogue_flags','player','overworld','actor ownership']
            finally:restored.music.stop()
            # Large source origin lies far outside ordinary root lookup, but its
            # full rectangle and visible pixels must still render.
            place(game,(10,-1));camera=game.camera.position()
            giant=record('antlers_complete',(camera[0]-560,camera[1]-190),'overhead')
            world.landmarks=LandmarkLayers(ROOT,[giant])
            assert list(world.landmarks.visible(pygame.Rect(camera,(480,320)),'overhead'))
            shot(game,folder,'offscreen_origin_visible_branch')
            report['large_bounds_fixture']=giant
            # Retained sources do not grow with changing player/camera positions.
            canvas=WorldCanvas((480,320));samples=[];maximum_work=0
            for n in range(240):
                camera_n=(camera[0]+n%120,camera[1]+n//120)
                started=perf_counter();world.landmarks.draw(canvas,camera_n,'overhead',actors=[game.player])
                samples.append((perf_counter()-started)*1000)
                maximum_work=max(maximum_work,world.landmarks.working_bytes)
                assert world.landmarks.sources.bytes<=world.landmarks.sources.budget
            report['landmark_cache']={'positions':240,'source_bytes':world.landmarks.sources.bytes,
                'source_budget':world.landmarks.sources.budget,'maximum_working_bytes':maximum_work,
                'draw_ms_mean':sum(samples)/len(samples),'draw_ms_max':max(samples)}
            world.landmarks=original
            game.world=game.town;game.player.position.update(game.town.data['spawn']);game.camera.reset()
            town_camera=game.camera.position()
            town_record=record('antlers_distant',(town_camera[0]+120,town_camera[1]-20),'distant')
            game.town.landmarks=LandmarkLayers(ROOT,[town_record])
            shot(game,folder,'town_distant_fixture')
            report['town_distant_fixture']=town_record
            game.town.landmarks=LandmarkLayers(ROOT)
            # Detailed full assembly retains all offsets. These are candidate
            # composition views, NOT grounded production placement acceptance.
            reserve=game._scene_by_id('elden_vale_sanctuary');game.world=reserve
            master=(592,-230)
            names=['embedded_skull','beam_left','beam_central','beam_right']
            assets=json.loads(MANIFEST.read_text())['assets']
            pieces=[]
            for name in names:
                offset=assets[name]['assembly_position_artwork']
                pieces.append(record(name,(master[0]+offset[0]/2,master[1]+offset[1]/2),'ground' if name=='embedded_skull' else 'overhead'))
            reserve.landmarks=LandmarkLayers(ROOT,pieces)
            report['detailed_candidate']={'master_origin':list(master),'placements':pieces,'views':{}}
            for name,point in [('study_skull_glimpse',(864,456)),('eastern_loop',(1100,336)),('northern_loop',(960,168))]:
                assert reserve.can_stand(point),('Protected candidate viewpoint blocked',point)
                game.player.position.update(point);game.camera.reset()
                shot(game,folder,'detailed_'+name)
                report['detailed_candidate']['views'][name]={'player':list(point),'camera':list(game.camera.position())}
            # Project the complete master once, then segment on even native
            # boundaries so reconstruction remains exact at density 2.
            full=pygame.image.load(str(ROOT/assets['antlers_complete']['image']))
            full=pygame.transform.scale(full,(980,660))
            projected=[]
            boxes={'embedded_skull':(0,474,980,186),'beam_left':(0,0,330,474),
                   'beam_central':(330,0,320,474),'beam_right':(650,0,330,474)}
            for name in names:
                box=pygame.Rect(boxes[name]);raw=full.subsurface(box).copy()
                filename=name+'_projected.png';pygame.image.save(raw,str(temporary/filename))
                item=record(name,(726+box.x/2,-41+box.y/2),'ground' if name=='embedded_skull' else 'overhead')
                item.update(image=filename,logical_size=[box.w//2,box.h//2])
                item.pop('occlusion_mask',None)
                if name!='embedded_skull':
                    mask=pygame.Surface(raw.get_size());alpha=pygame.surfarray.array_alpha(raw)
                    rgb=pygame.surfarray.pixels3d(mask);rgb[:]=alpha[:,:,None];del rgb
                    maskname=name+'_projected_mask.png';pygame.image.save(mask,str(temporary/maskname))
                    item['occlusion_mask']=maskname
                projected.append(item)
            reserve.landmarks=LandmarkLayers(temporary,projected)
            report['detailed_projection_study']={'uniform_scale':.625,'master_origin':[726,-41],
                'master_size':[490,330],'contact':[948.5,274,45,12.5],
                'native_segment_rects':boxes,
                'note':'Disposable nearest-neighbour whole-master projection; even-pixel segmentation reconstructs it exactly. Existing art and production metadata unchanged.',
                'views':{}}
            for name,point in [('northern_loop',(960,168)),('cave_apron',(1008,406)),('skull_glimpse',(864,456))]:
                assert reserve.can_stand(point),point
                game.player.position.update(point);game.camera.reset();shot(game,folder,'projected_'+name)
                report['detailed_projection_study']['views'][name]={'player':list(point),'camera':list(game.camera.position())}
            # Recruitment is a disposable fixture only, not a quest assertion.
            game.player.position.update(444,642);game.camera.reset()
            assert game.party.recruit('mira',temporary=True)
            assert game.party_travel.stage_companion('mira',(444,666),facing='back')
            follower,=game.party_travel.actors()
            companion_span=record('arch_lintel',(444-center[0],648-18-center[1]),'overhead')
            reserve.landmarks=LandmarkLayers(ROOT,[companion_span])
            shot(game,folder,'detailed_companion_cutaway')
            companion_trace=[]
            for _ in range(60):
                game.update(1/30,(0,-1),False)
                assert reserve.can_stand(game.player.position) and reserve.can_stand(follower.position)
                companion_trace.append({'player':list(game.player.position),'mira':list(follower.position)})
            report['companion_fixture']={'temporary_recruit':'mira','trace':companion_trace,
                'note':'Actual passive party follower under disposable span; no production roster or save changes.'}
            report['production_collision_sha256']=hashes['assets/maps/elden_vale_sanctuary/collision.png']
            for relative,digest in hashes.items():
                assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest,('Input changed during capture; rerun',relative)
            report['captures']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.suffix in ('.png','.gif')}
            (folder/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
            return report
        finally:
            game.music.stop();pygame.quit()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path,nargs='?',default=DEFAULT)
    capture(parser.parse_args().output)
