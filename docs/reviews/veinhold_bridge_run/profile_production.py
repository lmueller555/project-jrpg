"""Run from the repository root, with final assets and no concurrent renders."""
from collections import defaultdict
import hashlib
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
    pygame.display.set_mode((960, 640))
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
        pose_counts = {a['id']:len(a['animation']['frames']) for a in running.data['actors']}
        waits_before = perspective.cache_info['waits']
        timings = defaultdict(list)
        peaks = {'perspective_bytes':0, 'running_bytes':0, 'combined_bytes':0}
        seen = defaultdict(list)
        timeline = []
        start = time.perf_counter()
        for frame in range(17*60):
            before = time.perf_counter()
            scene.update(0. if frame == 0 else 1/60)
            image = scene.render_frame()
            elapsed = (time.perf_counter()-before)*1000
            assert image.get_size() == (960, 640)
            state = scene.state_at(scene.elapsed)
            timings[state['phase']].append(elapsed)
            old, new = perspective.cache_info, running.cache_info
            peaks['perspective_bytes'] = max(peaks['perspective_bytes'], old['bytes'])
            peaks['running_bytes'] = max(peaks['running_bytes'], new['bytes'])
            peaks['combined_bytes'] = max(peaks['combined_bytes'], old['bytes']+new['bytes'])
            if state['phase'] == 'bridge_running':
                for actor in running.samples(scene.elapsed-39.)['runners']:
                    seen[actor['id']].append(actor['frame_index'])
            if frame in (0, 299, 300, 539, 540, 599, 600, 839, 840, 1019):
                timeline.append({'frame':frame, 'time':scene.elapsed, 'phase':state['phase'],
                                 'perspective_cache':old, 'running_cache':new})
            remaining = start+(frame+1)/60-time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)
        wall = time.perf_counter()-start
        waits = perspective.cache_info['waits']-waits_before
        for name, indices in seen.items():
            assert len(indices) == 180, (name, len(indices))
            assert all((b-a)%pose_counts[name] == 1 for a,b in zip(indices, indices[1:])), name
        before = time.perf_counter()
        scene.update(1/60)
        cleanup = (time.perf_counter()-before)*1000
        assert scene.elapsed == 42. and not scene.active
        assert perspective.cache_info['surfaces'] == running.cache_info['surfaces'] == 0
        assert not scene.flight_audio.voices and not scene.alert_audio.voices
        result = {'method':'Production controller update + native 960x640 render_frame, paced at 60 Hz '
                           'for all 17 continuation seconds; SDL dummy audio/video; excludes UI scaling, '
                           'encoding and preceding 25-second eagle shot. Run without Blender/capture contention.',
                  'startup_ms':round(startup, 3), 'wall_seconds':round(wall, 4),
                  'overall':distribution([v for group in timings.values() for v in group]),
                  'segments':{name:distribution(values) for name, values in timings.items()},
                  'foreground_decode_waits':waits, 'peak_cache':peaks,
                  'running_frames':{name:{'displayed':len(values), 'unique':len(set(values)),
                                          'one_authored_phase_per_tick':True} for name,values in seen.items()},
                  'cleanup_ms':round(cleanup, 3), 'timeline':timeline}
        names = ('fire_veinhold_opening.py', 'cinematic_bridge_run.py', 'cinematic_perspective.py',
                 'prologue_alert_audio.py', 'prologue_flight_audio.py',
                 'assets/story/fire_veinhold_opening/scene.json',
                 'assets/story/fire_veinhold_opening/shot06/scene.json')
        result['source_sha256'] = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
        for path in sorted((ROOT/'assets/story/fire_veinhold_opening/shot06/characters').rglob('*')):
            if path.is_file():
                result['source_sha256'][path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        result['environment'] = {'python':sys.version.split()[0], 'pygame':pygame.version.ver,
                                 'video_driver':pygame.display.get_driver(), 'effects_volume':.4}
        output = ROOT/'docs/reviews/veinhold_bridge_run/production_profile.json'
        output.write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k != 'timeline'}, indent=2))
    finally:
        scene.reset()
        pygame.quit()


if __name__ == '__main__':
    main()
