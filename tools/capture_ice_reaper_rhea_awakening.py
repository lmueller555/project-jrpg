"""Review the 21-second Rhea awakening with a mapped, preserved action timeline.

The first fifteen seconds remain unchanged. A one-second closed-eye hold is
inserted in the close-up; all subsequent choreography runs one second later.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]

import numpy as np
import capture_ice_reaper_continuity as continuity
from capture_ice_reaper_guard_correction import compare

OUTPUT=ROOT/'docs/reviews/ice_reaper_rhea_awakening'
PREVIOUS=ROOT/'docs/reviews/ice_reaper_rune_shoulder'
STRIPS={
    'awakening_filmstrip':(15.2,15.7,16.,16.4,16.62,16.9,17.15,17.3,17.6),
    'rune_reveal_filmstrip':(17.3,17.45,17.6,17.75,17.9,18.05,18.25,18.4,18.6),
    'shoulder_filmstrip':(19.3,19.6,20.,20.4,20.8),
    'rescue_filmstrip':(7.3,7.5,8.,8.5,8.99,9.2),
}
KEYFRAMES={
    0:'brush',1:'wide',4.2:'alarm',6:'aim',7.3:'dash',8.5:'slow_slash',
    9.2:'shield_impact',10.4:'orbit',12:'mira_loading',13.8:'scope',14.7:'shard_destruction',
    15.2:'rhea_closed',16:'rhea_strained',16.45:'rhea_angry_opening',16.62:'eye_gleam',
    16.9:'rhea_angry_hold',17.15:'awakening_pullback',17.3:'release',18.6:'rune_complete',
    19.3:'left_shoulder',20:'between_shoulders',20.8:'right_shoulder',
}


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seed_baseline(output):
    path=output/'timing_baseline.json'
    if path.exists(): return json.loads(path.read_text())
    # This is a review fixture, not a runtime import. It preserves the committed
    # version preceding this pass even when the working tree is being revised.
    import pygame
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    source=subprocess.check_output(['git','show',f'{commit}:ice_reaper_action.py'],cwd=ROOT,text=True)
    module=types.ModuleType('_rhea_awakening_reference_stage')
    module.__file__=str(ROOT/'ice_reaper_action.py')
    sys.modules[module.__name__]=module
    exec(compile(source,module.__file__,'exec'),module.__dict__)
    Stage=module.IceReaperActionStage
    pygame.init();pygame.display.set_mode((480,320))
    try:
        stage=Stage(ROOT/'assets/story/ice_reaper_rescue',strict=True)
        baseline={'version':1,'source_commit':commit,'early_render':{},'late_track':[]}
        for time in (5.5,7.3,8.5,8.99,9.2,10.4,12.,13.8,14.7,15.):
            frame=pygame.Surface((480,320));stage.draw(frame,time)
            baseline['early_render'][str(time)]=hashlib.sha256(pygame.image.tobytes(frame,'RGB')).hexdigest()
        for index in range(978,1200):
            time=index/60;camera=Stage.camera(time);positions=Stage.actor_positions(time)
            baseline['late_track'].append(dict(old_time=time,
                camera=[list(camera.position),list(camera.target),camera.focal,list(camera.center)],
                positions={key:list(value) for key,value in positions.items()},
                headings={key:list(Stage.actor_heading(key,time)) for key in positions}))
        path.write_text(json.dumps(baseline,indent=2)+'\n')
        return baseline
    finally: pygame.quit()


def close_enough(actual,expected,label):
    if not np.allclose(actual,expected,rtol=0,atol=1e-8):
        raise AssertionError(f'Timing-preserved {label} changed: {actual} != {expected}')


def verify_scope(output):
    import pygame
    from ice_reaper_action import IceReaperActionStage as Stage
    baseline=seed_baseline(output)
    pygame.init();pygame.display.set_mode((480,320))
    try:
        stage=Stage(ROOT/'assets/story/ice_reaper_rescue',strict=True)
        early={}
        for value,expected in baseline['early_render'].items():
            elapsed=float(value);frame=pygame.Surface((480,320));stage.draw(frame,elapsed)
            actual=hashlib.sha256(pygame.image.tobytes(frame,'RGB')).hexdigest()
            if actual!=expected: raise AssertionError(f'Earlier scene changed at {elapsed}')
            early[value]=actual
        samples=[];positions_checked=0;headings_checked=0
        for old in baseline['late_track']:
            elapsed=old['old_time']+1
            canonical=Stage.story_time(elapsed)
            close_enough(canonical,old['old_time'],'story clock')
            camera=Stage.camera(canonical)
            close_enough(camera.position,old['camera'][0],'camera position')
            close_enough(camera.target,old['camera'][1],'camera target')
            close_enough(camera.focal,old['camera'][2],'camera lens')
            close_enough(camera.center,old['camera'][3],'camera center')
            positions=Stage.actor_positions(canonical)
            for actor,expected in old['positions'].items():
                close_enough(positions[actor],expected,f'{actor} position')
                positions_checked+=1
            for actor,expected in old['headings'].items():
                close_enough(Stage.actor_heading(actor,canonical),expected,f'{actor} heading')
                headings_checked+=1
            samples.append(dict(actual_time=elapsed,choreography_time=canonical))
        awakening=getattr(stage,'rhea_closeup',None)
        if awakening is None:
            raise AssertionError('The new awakening close-up was not preloaded')
        expression={str(time):awakening.state(time) for time in (15.2,15.7,16.,16.4,16.45,16.62,16.9,17.15)}
        for time in (15.2,15.7,16.):
            if not awakening.state(time)['eyes_closed']:
                raise AssertionError(f'Rhea opens her eyes before the additional closed-eye hold at {time}')
        if not any(awakening.state(time)['gleam_strength']>.1 for time in (16.45,16.55,16.62,16.7)):
            raise AssertionError('The angry eye opening has no emphatic gleam')
        complete=stage.rune_seal.state(Stage.story_time(18.6))
        if complete['progress']<.999: raise AssertionError('The shifted rune does not complete at 18.6s')
    finally: pygame.quit()
    record=dict(version=1,comparison='Previous twenty-second rune and shoulder review',
        insert=dict(start=15.1,end=16.1,seconds=1),early_scene_pixels_unchanged=early,
        shifted_camera_samples=len(samples),other_actor_position_checks=positions_checked,
        actor_heading_checks=headings_checked,late_clock_samples=samples,
        awakening=expression,rune_completion_at18_6=complete,
        note='Action helpers retain the previous choreography clock. Production draw maps actual elapsed time through story_time; later geometry and camera are preserved with a one-second shift.')
    (output/'preservation_verification.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def capture(output=OUTPUT,*,fps=60,reuse=False):
    output.mkdir(parents=True,exist_ok=True)
    seed_baseline(output)
    scope=verify_scope(output)
    old_previous,old_strips=continuity.PREVIOUS,continuity.STRIPS
    old_keyframes=continuity.production.KEYFRAME_TIMES
    try:
        continuity.PREVIOUS,continuity.STRIPS=PREVIOUS,STRIPS
        continuity.production.KEYFRAME_TIMES=KEYFRAMES
        continuity.review(output,fps=fps,reuse=reuse)
    finally:
        continuity.PREVIOUS,continuity.STRIPS=old_previous,old_strips
        continuity.production.KEYFRAME_TIMES=old_keyframes
    report_path=output/'verification.json';report=json.loads(report_path.read_text())
    if report['frames']!=round(21*fps) or abs(report['duration_seconds']-21)>1e-9:
        raise AssertionError('The production preview must contain 21 seconds')
    times=(15.2,16.,16.62,16.9,17.15,17.3,18.6,19.3,20.,20.3,20.8)
    current=continuity.video_frames(output/'preview.mp4',times,fps)
    previous=continuity.video_frames(PREVIOUS/'preview.mp4',(15.8,19.3),fps)
    posters=((15.2,'rhea_closed.png'),(16.,'rhea_strained.png'),(16.62,'rhea_angry_gleam.png'),
             (16.9,'rhea_angry.png'),(17.15,'awakening_pullback.png'),(18.6,'rune_complete.png'),
             (19.3,'left_shoulder.png'),(20.,'between_shoulders.png'),(20.8,'right_shoulder.png'))
    for time,name in posters: current[round(time*fps)].save(output/name,optimize=True)
    compare(previous[round(15.8*fps)],current[round(16.62*fps)],output/'closeup_comparison.png',16.62,
            'Previous: face insert and thin ice edges','Updated: angry awakening inside cracked ice')
    compare(previous[round(19.3*fps)],current[round(20.3*fps)],output/'shifted_shoulder_comparison.png',20.3,
            'Previous: 19.3s','Updated: 20.3s, same choreography')
    for name in ('ice_reaper_rune.py','rhea_awakening_closeup.py'):
        report['runtime_sources'][name]=digest(ROOT/name)
    manifest=ROOT/'assets/story/ice_reaper_rhea_closeup/animation.json'
    if not manifest.exists(): manifest=ROOT/'assets/story/ice_reaper_rhea_closeup/manifest.json'
    if manifest.exists(): report['awakening_art_manifest_sha256']=digest(manifest)
    report['awakening_preservation']=scope
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(duration=report['duration_seconds'],fps=fps,frames=report['frames'],
        early_frames_unchanged=len(scope['early_scene_pixels_unchanged']),
        shifted_camera_samples=scope['shifted_camera_samples'])))
    return scope


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--fps',type=int,choices=(30,60),default=60)
    parser.add_argument('--reuse',action='store_true')
    args=parser.parse_args();capture(args.output.resolve(),fps=args.fps,reuse=args.reuse)
