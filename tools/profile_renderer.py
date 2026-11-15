"""Measure production draw paths using temporary saves; optional private captures."""
from pathlib import Path
import argparse
import gc
import json
import os
import statistics
try:
    import resource
except ImportError:
    resource=None
import sys
import tempfile
import time

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(os.environ.get('JRPG_PROFILE_ROOT',Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(ROOT))
import pygame
from main import Game


def profile(frames=30,capture=None):
    records={}
    with tempfile.TemporaryDirectory(prefix='renderer-profile-') as directory:
        folder=Path(directory)
        g=Game(fullscreen=False,window_size=(960,640),start_on_title=False,
               save_path=folder/'save.json',settings_path=folder/'settings.json')
        try:
            def measure(name,draw,game=None,step=None):
                if game is None:game=g
                for _ in range(4):
                    if step is not None:step()
                    draw()
                samples=[]
                for _ in range(frames):
                    game.elapsed_ms+=16
                    if step is not None:step()
                    start=time.perf_counter();draw();samples.append((time.perf_counter()-start)*1000)
                records[name]={'median_ms':round(statistics.median(samples),3),
                               'p95_ms':round(sorted(samples)[max(0,int(len(samples)*.95)-1)],3),
                               'frames':frames}
                if capture:
                    capture.mkdir(parents=True,exist_ok=True)
                    pygame.image.save(game.window,str(capture/(name+'.png')))
            for name,scene,position in [('town','eldenmere.playable',(732,1032)),
                                        ('dining','sanctuary_dining',(228,252)),
                                        ('cave','sanctuary_cave',(1460,1520))]:
                g.world=g._scene_by_id(scene);g.player.position.update(position)
                g.opening_fade=0;g.camera.reset();measure(name,g.draw)
            g.world=g.overworld_world;g.player.position.update(g.world.data['spawn']);g.camera.reset()
            measure('overworld',g.draw)
            records['overworld']['cache']=g.world.cache_stats
            g.combat.start_mill()
            if g.combat.transition is not None:g.combat.transition.elapsed=g.combat.transition.duration
            measure('battle',g.draw)
            # Release combat resources by using a fresh isolated parent for
            # Gallery; no gameplay checkpoint or persistent journey is changed.
            g.music.stop()
        finally:
            g.music.stop();pygame.quit()
        del g;gc.collect()
        parent=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
                    save_path=folder/'gallery.json',settings_path=folder/'gallery-settings.json')
        try:
            parent.open_gallery()
            for entry,shot,seconds in [('regent_arrival','gate_greeting',1.),
                                       ('ice_reaper_opening',None,18.)]:
                assert parent.launch_gallery_scene(entry),parent.gallery.error
                child=parent.gallery_session.game
                if shot:
                    scene=child.regent_arrival
                    scene.phase_index=next(i for i,p in enumerate(scene.data['phases']) if p['id']==shot)
                    scene.phase_time=seconds
                else:child.opening_cinematic.elapsed=seconds
                measure(entry,parent.draw,child)
                if shot:
                    scene.phase_index=next(i for i,p in enumerate(scene.data['phases']) if p['id']=='aerial_gate')
                    scene.phase_time=1.
                    def advance():scene.phase_time+=1/60
                    measure('aerial_camera_motion',parent.draw,child,advance)
                else:
                    def advance():child.opening_cinematic.elapsed+=1/60
                    measure('ice_reaper_camera_motion',parent.draw,child,advance)
                parent.gallery_session.close();parent.gallery_session=None
        finally:
            if parent.gallery_session is not None:parent.gallery_session.close()
            parent.music.stop();pygame.quit()
    try:
        from rendering import cache_info
        records['transformed_asset_cache']=cache_info()
    except ImportError:pass
    if resource is not None:
        divisor=2**20 if sys.platform=='darwin' else 1024
        records['peak_rss_mib']=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/divisor,1)
    records['method']='960x640 SDL dummy; warm draws, excludes simulation update; temporary saves only'
    return records


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--frames',type=int,default=30)
    parser.add_argument('--capture',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.frames<1:parser.error('--frames must be positive')
    result=profile(args.frames,args.capture)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
