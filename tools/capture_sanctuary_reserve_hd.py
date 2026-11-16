"""Native reserve review: initialized fixture, actual walking, doors and story director."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import argparse
import gc
import json
from pathlib import Path
import resource
import sys
import tempfile
from time import perf_counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from PIL import Image
from main import Game
from rendering import WorldCanvas
from tools.capture_sanctuary_reserve import path,walk
RESERVE='elden_vale_sanctuary';HALL=RESERVE+'_hall';RELIEF=RESERVE+'_relief'

def capture(folder):
    folder.mkdir(parents=True,exist_ok=True);report={'fixture':'Disposable initialized exploration fixture; subsequent walking and door transitions use actual Game movement.'};timings={}
    with tempfile.TemporaryDirectory(prefix='reserve-hd-review-') as directory:
        p=Path(directory);g=Game(fullscreen=False,start_on_title=True,window_size=(960,640),save_path=p/'journey.json',settings_path=p/'settings.json')
        try:
            g.on_title=False;g.opening.stage='disabled';g.opening_fade=g.transfer_cooldown=0
            g.world=g._scene_by_id(RESERVE);g.player.position.update(g.world.data['spawn']);g.update(.1,(0,0),False)
            def shot(name):
                g.camera.reset();g.saves.notice_seconds=g.location_seconds=0;g.draw();pygame.image.save(g.window,str(folder/(name+'.png')))
                world=g.world;view=WorldCanvas((480,320));camera=g.camera.position()
                measurements=[]
                for _ in range(30):
                    start=perf_counter();world.draw(view,camera,g.player,g.elapsed_ms,False);measurements.append((perf_counter()-start)*1000)
                timings[name]={'warm_draw_ms':sum(measurements)/len(measurements),'ground_cache_bytes':world._ground_cache.bytes,'ground_cache_budget':world._ground_cache.budget}
            def travel(goal):walk(g,path(g.world,g.player.position,goal),g.world.data['id'])
            def settle():
                for _ in range(40):g.update(.04,(0,0),False)
            def door(identifier):
                origin=g.world;d=next(d for d in origin.doors if d.data['id']==identifier);x,y=d.data['anchor'];direction=-1 if d.data['entry_side']=='north' else 1
                travel((x,y-direction*24))
                for _ in range(100):
                    g.update(.04,(0,direction),False)
                    if g.world is not origin:break
                if g.world is origin:raise AssertionError('Door did not transfer: '+identifier)
                report.setdefault('door_transitions',[]).append([origin.data['id'],g.world.data['id']]);settle()
            def key(value):g.handle_events([pygame.event.Event(pygame.KEYDOWN,key=value,repeat=False),pygame.event.Event(pygame.KEYUP,key=value)])
            shot('arrival')
            # Fixed camera shows actual travel through the entrance, with one GIF palette.
            start=g.player.position.copy();target=start+pygame.Vector2(0,-144)
            for running in (False,True):
                if running:travel(start)
                frames=[];trace=[]
                for _ in range(120):
                    delta=target-g.player.position
                    if delta.length()<1:break
                    seconds=min(1/30,delta.length()/(126 if running else 72));g.update(seconds,delta,running)
                    if not g.world.can_stand(g.player.position):raise AssertionError('Invalid movement')
                    view=WorldCanvas((480,320));g.world.draw(view,(204,400),g.player,g.elapsed_ms,False)
                    frames.append(Image.frombytes('RGB',view.native.get_size(),pygame.image.tobytes(view.native,'RGB')));trace.append(list(g.player.position))
                palette=frames[0].quantize(colors=256);seq=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
                name='entrance_run' if running else 'entrance_walk'
                seq[0].save(folder/(name+'.gif'),save_all=True,append_images=seq[1:],duration=33,loop=0,optimize=False,disposal=1);report[name]=trace
            for name,goal in [('grove',(292,244)),('caretaker',(212,480)),('cloister',(776,366)),('cave_approach',(1008,406)),('survey',(858,630))]:
                travel(goal);g.update(.2,(0,0),False);shot(name)
                if name=='caretaker':
                    actor=g.sanctuary_reserve.actors['reserve_caretaker']
                    for _ in range(450):
                        if actor._pose()[1].get('effect')=='pour':break
                        g.update(.04,(0,0),False)
                    shot('caretaker_pour');report['caretaker_pose']=actor._pose()[0]
            door('sanctuary_hall');travel((288,178));g.update(.2,(0,0),False);shot('hall_remembrance')
            travel((476,278));shot('hall_records');door('relief_room');travel((104,150));shot('relief_room')
            g.attributes.set_current(hp=17,mp=2);key(pygame.K_e)
            for _ in range(30):
                if g.social.choosing:break
                key(pygame.K_SPACE)
            shot('relief_rest_offer');report['rest_offer']=g.social.script_identifier
            g.social.cancel_script();door('hall');door('reserve_exit');travel((1008,406));shot('cave_closed')
            g.audio.set_reduced_motion(True);g.update(.1,(0,0),False);shot('reduced_motion')
            g.audio.set_reduced_motion(False)
            g.sanctuary_arrival.prepare_preview();g.sanctuary_arrival.start(force=True)
            captured=set()
            for _ in range(2400):
                owner=g.sanctuary_arrival
                if owner.completed:break
                g.update(.2,(0,0),False)
                if owner.dialogue:
                    if owner.beat in (0,1,7) and owner.beat not in captured:
                        shot('arrival_story_'+str(owner.beat));captured.add(owner.beat)
                    key(pygame.K_SPACE)
            report['story_preview_completed']=g.sanctuary_arrival.completed
            if not g.sanctuary_arrival.completed:raise AssertionError('Story preview did not finish')
            shot('cave_open_after_arrival')
            report['timings']=timings;report['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            report['profile_scope']='30 warm world-renderer draws per view; excludes simulation and display UI, SDL dummy backend.'
            (folder/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
        finally:g.music.stop();pygame.quit();gc.collect()
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);capture(parser.parse_args().output)
