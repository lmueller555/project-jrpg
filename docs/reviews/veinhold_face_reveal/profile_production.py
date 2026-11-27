"""Run from the repository root after sources freeze, without other renders."""
from collections import defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import statistics
import sys
import time
from types import SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
import pygame
from fire_veinhold_opening import FireVeinholdOpening


def distribution(values):
    ordered = sorted(values)
    return {'frames':len(values), 'mean_ms':round(statistics.mean(values), 3),
            'p95_ms':round(ordered[min(len(ordered)-1, int(len(ordered)*.95))], 3),
            'max_ms':round(max(values), 3),
            'above_16_667_ms':sum(value > 1000/60 for value in values)}


def main():
    pygame.init()
    pygame.display.set_mode((960,640))
    game = SimpleNamespace(audio=SimpleNamespace(reduced_motion=False, effects_volume=.4),
                           _music_focused=True, to_canvas=lambda point:point)
    scene = FireVeinholdOpening(game)
    try:
        before = time.perf_counter()
        scene.start()
        startup = (time.perf_counter()-before)*1000
        scene.update(24.5)
        time.sleep(.5)
        scene.update(.5)
        perspective = scene._assets['island_orbit']['perspective']
        running = next(iter(scene._running.values()))
        frontal = next(iter(scene._face_reveals.values()))
        owners = {'perspective':perspective, 'running':running, 'frontal':frontal}
        waits_before = {name:owner.cache_info['waits'] for name,owner in owners.items()}
        timings, seen = defaultdict(list), defaultdict(lambda:defaultdict(list))
        peaks = {name:0 for name in owners}
        peaks['combined'] = 0
        timeline = []
        start = time.perf_counter()
        for frame in range(22*60):
            before = time.perf_counter()
            scene.update(0. if frame == 0 else 1/60)
            image = scene.render_frame()
            elapsed = (time.perf_counter()-before)*1000
            assert image.get_size() == (960,640)
            state = scene.state_at(scene.elapsed)
            timings[state['phase']].append(elapsed)
            caches = {name:owner.cache_info for name,owner in owners.items()}
            for name,cache in caches.items():
                peaks[name] = max(peaks[name], cache['bytes'])
                assert cache['surfaces'] <= cache['capacity'], (name,cache)
            peaks['combined'] = max(peaks['combined'], sum(cache['bytes'] for cache in caches.values()))
            assert caches['frontal']['bytes'] <= caches['frontal']['byte_capacity']
            if state['phase'] in ('bridge_running','face_reveal'):
                for actor in state['runners']:
                    seen[state['phase']][actor['id']].append(actor['frame_index'])
            if frame in (0,299,300,539,540,599,600,839,840,1019,1020,1109,1110,1319):
                timeline.append({'frame':frame,'time':scene.elapsed,'phase':state['phase'],'caches':caches})
            remaining = start+(frame+1)/60-time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)
        wall = time.perf_counter()-start
        for phase,count in (('bridge_running',180),('face_reveal',300)):
            for name,indices in seen[phase].items():
                assert len(indices) == count, (phase,name,len(indices))
                assert all((b-a)%24 == 1 for a,b in zip(indices,indices[1:])), (phase,name)
        waits = {name:owner.cache_info['waits']-waits_before[name] for name,owner in owners.items()}
        before = time.perf_counter()
        scene.update(1/60)
        cleanup = (time.perf_counter()-before)*1000
        assert scene.elapsed == 47. and not scene.active
        assert all(owner.cache_info['surfaces'] == owner.cache_info['bytes'] == 0 for owner in owners.values())
        assert not scene.flight_audio.voices and not scene.alert_audio.voices
        result = {
            'method':'Production controller update and native 960x640 render_frame, paced at 60 Hz for '
                     'all 22 continuation seconds. SDL dummy audio/video; excludes UI scaling, encoding '
                     'and preceding 25-second eagle shot. Run without other render/test contention.',
            'startup_ms':round(startup,3), 'wall_seconds':round(wall,4),
            'overall':distribution([value for group in timings.values() for value in group]),
            'segments':{name:distribution(values) for name,values in timings.items()},
            'foreground_decode_waits':waits, 'peak_cache_bytes':peaks,
            'running_frames':{phase:{name:{'displayed':len(values),'unique':len(set(values)),
                                           'one_authored_phase_per_tick':True}
                                      for name,values in actors.items()} for phase,actors in seen.items()},
            'cleanup_ms':round(cleanup,3),'timeline':timeline,
            'environment':{'python':sys.version.split()[0],'pygame':pygame.version.ver,
                           'video_driver':pygame.display.get_driver(),'effects_volume':.4},
        }
        paths = [ROOT/name for name in ('fire_veinhold_opening.py','cinematic_bridge_run.py',
            'cinematic_face_reveal.py','cinematic_perspective.py','prologue_alert_audio.py',
            'prologue_flight_audio.py','assets/story/fire_veinhold_opening/scene.json',
            'assets/story/fire_veinhold_opening/shot06/scene.json')]
        paths.extend(path for path in (ROOT/'assets/story/fire_veinhold_opening/shot07').rglob('*') if path.is_file())
        result['source_sha256'] = {path.relative_to(ROOT).as_posix():sha256(path.read_bytes()).hexdigest()
                                   for path in sorted(paths)}
        folder = ROOT/'docs/reviews/veinhold_face_reveal'
        (folder/'production_profile.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({key:value for key,value in result.items() if key not in ('timeline','source_sha256')},indent=2))
    finally:
        scene.reset()
        pygame.quit()


if __name__ == '__main__':
    main()
