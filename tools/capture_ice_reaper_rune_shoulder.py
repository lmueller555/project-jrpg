"""Capture the complete rune construction and closer shoulder-view revision.

The camera/environment are compared with the preceding approved shot layout.
Only the Reaper's final world placement and the authored rune are allowed to
change. Review stills decode the delivered production MP4.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import types

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]

from PIL import Image
import capture_ice_reaper_continuity as continuity
from capture_ice_reaper_guard_correction import compare, pixels_hash

OUTPUT = ROOT/'docs/reviews/ice_reaper_rune_shoulder'
PREVIOUS = ROOT/'docs/reviews/ice_reaper_guard_correction'
BASELINE = PREVIOUS/'scope_baseline.json'
STRIPS = {
    'rune_reveal_filmstrip': (16.3,16.45,16.6,16.75,16.9,17.05,17.25,17.4,17.6),
    'shoulder_filmstrip': (18.3,18.6,19.,19.4,19.8),
    'rescue_filmstrip': (7.3,7.5,8.,8.5,8.99,9.2),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_actor_baseline(output):
    path = output/'actor_position_baseline.json'
    if path.exists():
        return json.loads(path.read_text())
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    source = subprocess.check_output(['git','show',f'{commit}:ice_reaper_action.py'],cwd=ROOT,text=True)
    module = types.ModuleType('_ice_reaper_previous_review')
    module.__file__ = str(ROOT/'ice_reaper_action.py')
    sys.modules[module.__name__] = module
    exec(compile(source,module.__file__,'exec'),module.__dict__)
    reference = module.IceReaperActionStage
    samples = []
    for frame in range(301,1200):
        time = frame/60
        samples.append(dict(time=time,positions={key:list(value) for key,value in reference.actor_positions(time).items()}))
    record = dict(version=1,source_commit=commit,samples=samples)
    path.write_text(json.dumps(record,indent=2)+'\n')
    return record


def verify_scope(output):
    import pygame
    import numpy as np
    from ice_reaper_action import IceReaperActionStage as Stage
    baseline = json.loads(BASELINE.read_text())
    actor_baseline = seed_actor_baseline(output)
    pygame.init();pygame.display.set_mode((480,320))
    try:
        stage = Stage(ROOT/'assets/story/ice_reaper_rescue',strict=True)
        cameras = []
        for old in baseline['camera']:
            time = old[0];camera = stage.camera(time)
            current = [time,list(camera.position),list(camera.target),camera.focal,list(camera.center)]
            if current != old:
                raise AssertionError(f'The locked camera changed at {time}')
            cameras.append(current)
        backgrounds = {}
        for value,expected in baseline['environment'].items():
            time=float(value);canvas=pygame.Surface((480,320))
            stage._background(canvas,stage.camera(time),time)
            actual=hashlib.sha256(pygame.image.tobytes(canvas,'RGB')).hexdigest()
            if actual!=expected:
                raise AssertionError(f'The environment changed at {time}')
            backgrounds[value]=actual
        lucan = {}
        for value,expected in baseline['lucan_end'].items():
            time=float(value);position=stage.actor_positions(time)['lucan'];camera=stage.camera(time)
            action,local,duration=stage._action('lucan',time)
            image,_=stage._sequence('lucan',action,local,duration,camera,position,time=time)
            current=dict(heading=list(stage.actor_heading('lucan',time)),position=list(position),frame=pixels_hash(image))
            if current!=expected:
                raise AssertionError(f'Lucan\'s correct ending changed at {time}')
            lucan[value]=current
        actor_positions = 0;early_boss = 0
        for record in actor_baseline['samples']:
            time=record['time'];positions=stage.actor_positions(time)
            for actor,expected in record['positions'].items():
                if actor=='ice_reaper' and time>=16.3:
                    continue
                actual=list(positions[actor])
                if not np.array_equal(actual,expected):
                    raise AssertionError(f'Unrelated actor position changed: {actor} at {time}')
                actor_positions += actor!='ice_reaper'
                early_boss += actor=='ice_reaper'
        tree=ast.parse((ROOT/'ice_reaper_action.py').read_text())
        methods={}; intentional_methods={}
        for name,expected in baseline['method_hashes'].items():
            # Fixed original staging anchors preserve camera OUTPUT while the
            # actor itself rises; checking its old source AST would forbid that.
            node=next(node for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and node.name==name)
            actual=hashlib.sha256(ast.dump(node).encode()).hexdigest()
            if name in ('camera','_projected_boss'):
                intentional_methods[name]=dict(previous_sha256=expected,current_sha256=actual)
                continue
            if actual!=expected:
                raise AssertionError(f'Protected environment/projection method changed: {name}')
            methods[name]=actual
        approved=set();folder=ROOT/'assets/story/ice_reaper_rescue/actors/ice_reaper'
        for file in ('recharge_06.png',*(f'ready_rear_{i:02}.png' for i in range(1,4)),*(f'ready_side_{i:02}.png' for i in range(1,4))):
            approved.add(pixels_hash(pygame.image.load(str(folder/file)).convert_alpha()))
        boss_positions={};boss_art={}
        for time in (16.3,16.7,17.2,17.8,18.3,18.6,19.,19.4,19.8):
            camera=stage.camera(time);position=stage.actor_positions(time)['ice_reaper']
            action,local,duration=stage._action('ice_reaper',time)
            image,_=stage._sequence('ice_reaper',action,local,duration,camera,position,time=time)
            signature=pixels_hash(image)
            if signature not in approved:
                raise AssertionError(f'Approved Reaper artwork changed at {time}')
            boss_positions[str(time)]=list(position);boss_art[str(time)]=signature
        rune=stage.rune_seal
        reveal={str(time):rune.state(time) for time in STRIPS['rune_reveal_filmstrip']}
        radii=[state['world_radius'] for state in reveal.values()]
        if len(set(radii))!=1:
            raise AssertionError('Rune world footprint scales during construction')
        complete_at=max(state['complete_at'] for state in reveal.values())
        if complete_at>18.15 or not rune.state(complete_at)['progress']>=.999:
            raise AssertionError('The rune is not constructed before the shoulder sweep')
    finally:
        pygame.quit()
    record=dict(version=1,comparison='Pre-rune-and-shoulder revision',
        camera_samples_unchanged=len(cameras),
        camera_track_sha256=hashlib.sha256(json.dumps(cameras).encode()).hexdigest(),
        protected_environment_projection_methods=methods,
        intentional_staging_method_changes=intentional_methods,
        environment_hashes_unchanged=backgrounds,lucan_ending_unchanged=lucan,
        other_actor_position_checks=actor_positions,early_boss_position_checks=early_boss,
        repositioned_reaper=boss_positions,approved_reaper_art=boss_art,
        fixed_footprint_rune_reveal=reveal,
        note='Direct runtime checks compare exact camera and background output. Boss placement, near-field head-depth projection, angle-selected retained artwork, and rune design/reveal are the intended changes; no screen-sliding overlay is used.')
    (output/'preservation_verification.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def capture(output=OUTPUT,*,fps=60,reuse=False):
    output.mkdir(parents=True,exist_ok=True)
    seed_actor_baseline(output)
    scope=verify_scope(output)
    old_previous,old_strips=continuity.PREVIOUS,continuity.STRIPS
    try:
        continuity.PREVIOUS,continuity.STRIPS=PREVIOUS,STRIPS
        continuity.review(output,fps=fps,reuse=reuse)
    finally:
        continuity.PREVIOUS,continuity.STRIPS=old_previous,old_strips
    times=(16.6,17.05,17.6,17.72,18.3,19.,19.3,19.8)
    current=continuity.video_frames(output/'preview.mp4',times,fps)
    previous=continuity.video_frames(PREVIOUS/'preview.mp4',(19.3,),fps)
    for time,name in ((17.6,'rune_complete.png'),(17.72,'completion_pulse.png'),(18.3,'left_shoulder.png'),(19.,'between_shoulders.png'),(19.8,'right_shoulder.png')):
        current[round(time*fps)].save(output/name,optimize=True)
    compare(previous[round(19.3*fps)],current[round(19.3*fps)],output/'shoulder_comparison.png',19.3,
            'Previous: distant full Reaper','Updated: closer over the shoulder')
    verification_path=output/'verification.json'
    verification=json.loads(verification_path.read_text())
    verification['runtime_sources']['ice_reaper_rune.py']=digest(ROOT/'ice_reaper_rune.py')
    verification['authored_rune']=dict(
        file='assets/story/ice_reaper_rune/rune.png',
        sha256=digest(ROOT/'assets/story/ice_reaper_rune/rune.png'),
        metadata_sha256=digest(ROOT/'assets/story/ice_reaper_rune/rune.json'),
        reveal=scope['fixed_footprint_rune_reveal'])
    verification_path.write_text(json.dumps(verification,indent=2)+'\n')
    print(json.dumps(dict(scope_checks='passed',camera_samples=scope['camera_samples_unchanged'],
                         backgrounds=len(scope['environment_hashes_unchanged']),
                         preserved_lucan_poses=len(scope['lucan_ending_unchanged']),
                         rune_radius=next(iter(scope['fixed_footprint_rune_reveal'].values()))['world_radius'])))
    return scope


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--fps',type=int,choices=(30,60),default=60)
    parser.add_argument('--reuse',action='store_true')
    args=parser.parse_args()
    capture(args.output.resolve(),fps=args.fps,reuse=args.reuse)
