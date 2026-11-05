"""Capture the complete 32-second Ice Reaper cinematic through Game/Gallery.

The approved first 21 seconds are checked at every native frame. Review images
are decoded from the delivered MP4, with uninterrupted score and runtime SFX.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]

import pygame
import capture_ice_reaper_opening as production
from capture_ice_reaper_scene_awakening import decode_frames,filmstrip

OUTPUT=ROOT/'docs/reviews/ice_reaper_duel'
BASELINE=OUTPUT/'approved_opening_baseline.json'
KEYFRAMES={
    0:'brush',1:'wide',4.2:'alarm',8.5:'rescue',13.8:'launcher',16.62:'awakening',
    20.7:'shoulder_sweep',21.5:'rhea_speaks',22.5:'green_portrait',23.6:'caelan_interrupted',
    24.2:'staff_sweep',24.5:'wind_blast',25.1:'companions_land',25.5:'reaper_reaction',
    26.0:'sword_conjure',26.65:'fireballs',27.3:'orbit_quarter',27.9:'orbit_half',
    28.5:'orbit_threequarters',29.15:'orbit_complete',29.5:'charge_view',30.1:'windup',
    30.6:'charge',31.1:'lens_charge',31.8:'fade',
}
POSTERS={21.5:'rhea_dialogue.png',23.6:'caelan_dialogue.png',24.2:'staff_sweep.png',
         24.5:'wind_blast.png',25.1:'companions_land.png',26.0:'sword_conjure.png',
         26.65:'fireballs.png',27.9:'orbit_reverse.png',29.15:'orbit_complete.png',
         30.1:'windup.png',31.1:'charge.png',31.98:'fade.png'}
STRIPS={
    'duel_filmstrip':(21.5,23.6,24.2,24.5,25.1,25.5,26.0,26.65,27.3,27.9,28.5,29.15,30.1,31.1,31.98),
    'wind_filmstrip':(24.0,24.2,24.4,24.6,24.8,25.1),
    'orbit_filmstrip':(26.7,27.3,27.9,28.5,29.15,29.5),
    'charge_filmstrip':(29.55,30.1,30.3,30.6,31.1,31.8),
}


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture(output=OUTPUT,*,fps=60):
    from ice_reaper_opening import IceReaperOpening
    if fps!=60:raise ValueError('The final review uses 60 FPS')
    output.mkdir(parents=True,exist_ok=True)
    baseline=json.loads(BASELINE.read_text())
    if len(baseline['samples'])!=1260:raise ValueError('Missing complete approved opening baseline')
    expected={item['frame']:item for item in baseline['samples']}
    sources=('opening_cinematic.py','ice_reaper_opening.py','ice_reaper_action.py',
             'rhea_scene_awakening.py','ice_reaper_duel.py','ice_reaper_duel_fx.py',
             'ice_reaper_audio.py','cutscene_gallery.py','tools/capture_ice_reaper_opening.py',
             'tools/capture_ice_reaper_duel.py')
    source_hashes={name:digest(ROOT/name) for name in sources}
    asset_roots=('assets/story/ice_reaper_duel','assets/audio/sfx/ice_reaper_duel')
    asset_hashes={str(path.relative_to(ROOT)):digest(path) for folder in asset_roots
                  for path in sorted((ROOT/folder).rglob('*')) if path.is_file()}
    portrait=ROOT/'assets/story/ice_reaper_opening/portraits/rhea_awakening.png'
    asset_hashes[str(portrait.relative_to(ROOT))]=digest(portrait)
    preserved={};continuation={}
    original_draw=IceReaperOpening._draw_scene
    original_keys=production.KEYFRAME_TIMES
    original_thumbnails=production.capture_thumbnails
    original_popen=subprocess.Popen

    def checked_scene(scene,canvas,camera):
        original_draw(scene,canvas,camera)
        index=round(scene.elapsed*fps)
        if 0<=index<1260:
            actual=hashlib.sha256(pygame.image.tobytes(canvas,'RGB')).hexdigest()
            if actual!=expected[index]['sha256']:
                raise AssertionError(f'Approved opening changed at frame {index} ({scene.elapsed})')
            reference=expected[index]
            if (pygame.Vector2(scene.camera_position).distance_to(reference['presentation_camera'])>1e-9
                    or abs(scene.camera_zoom-reference['presentation_zoom'])>1e-9):
                raise AssertionError(f'Approved presentation camera changed at frame {index}')
            preserved[index]=actual
        elif 1260<=index<1920:
            stage=scene.action_stage
            if not hasattr(stage,'duel'):
                raise AssertionError('The continuation is not attached to the production stage')
            continuation[index]=dict(frame=index,time=scene.elapsed,
                dialogue=scene.dialogue['text'] if scene.dialogue else None,
                fade=scene.fade_alpha,
                trace=getattr(stage.duel,'last_draw_trace',[]))

    def bounded_encoder(command,*args,**kwargs):
        if isinstance(command,(list,tuple)) and command and Path(command[0]).name=='ffmpeg' and 'rawvideo' in command:
            command=list(command)
            for option,value in (('-preset','medium'),('-crf','21'),('-maxrate','2.5M'),('-bufsize','5M')):
                if option in command:command[command.index(option)+1]=value
        return original_popen(command,*args,**kwargs)

    try:
        IceReaperOpening._draw_scene=checked_scene
        production.KEYFRAME_TIMES=KEYFRAMES
        production.capture_thumbnails=lambda _ids:None
        subprocess.Popen=bounded_encoder
        production.capture(output,fps=fps)
    finally:
        IceReaperOpening._draw_scene=original_draw
        production.KEYFRAME_TIMES=original_keys
        production.capture_thumbnails=original_thumbnails
        subprocess.Popen=original_popen
    if len(preserved)!=1260 or len(continuation)!=660:
        raise AssertionError(f'Incomplete production capture: {len(preserved)} opening, {len(continuation)} continuation')
    if source_hashes!={name:digest(ROOT/name) for name in sources}:
        raise AssertionError('Runtime changed during capture; recapture frozen sources')
    if asset_hashes!={name:digest(ROOT/name) for name in asset_hashes}:
        raise AssertionError('Cinematic assets changed during capture')
    reportpath=output/'verification.json';report=json.loads(reportpath.read_text())
    if report['duration_seconds']!=32 or report['frames']!=1920:
        raise AssertionError('The complete cinematic must contain 1,920 frames and last 32 seconds')
    if (output/'preview.mp4').stat().st_size>11*1024*1024:
        raise AssertionError('Full review movie exceeds the GitHub upload budget')
    dialogue={record['dialogue'] for record in continuation.values() if record['dialogue']}
    if not {'Thanks guys, now leave her to me...','Rhea...are you su-'}<=dialogue:
        raise AssertionError('Both requested dialogue lines must appear in production playback')
    report['full_cinematic_duration_seconds']=32
    report['runtime_sources'].update(source_hashes)
    report['continuation_asset_hashes']=asset_hashes
    report['approved_opening_preservation']=dict(frames=1260,all_native_frames_exact=True,
        baseline_sha256=digest(BASELINE),source_commit=baseline['source_commit'])
    report['encoder_policy']=dict(preset='medium',crf=21,maxrate='2.5M',bufsize='5M',audio='AAC 192k')
    reportpath.write_text(json.dumps(report,indent=2)+'\n')
    (output/'continuation_verification.json').write_text(json.dumps(dict(version=1,
        opening_frames_preserved=1260,continuation_frames_checked=660,
        samples=[continuation[index] for index in sorted(continuation)]),indent=2)+'\n')
    times=sorted({*POSTERS,*(time for values in STRIPS.values() for time in values)})
    decoded=decode_frames(output/'preview.mp4',times,fps)
    for time,name in POSTERS.items():decoded[round(time*fps)].save(output/name,optimize=True)
    for name,values in STRIPS.items():filmstrip(decoded,values,fps,output/f'{name}.png',name.replace('_',' ').title())
    (output/'README.md').write_text(
        '# Ice Reaper — complete duel cinematic\n\n'
        '[Watch the full 32-second cinematic](preview.mp4), captured through production Game/Gallery playback at 60 FPS.\n\n'
        'The approved rescue and Rhea awakening lead into her dialogue, a staff-driven gust carrying Caelan and Lucan toward Mira, '
        'the Reaper’s ice sword and fireballs rising from the rune’s pointed patterns. A complete orbit returns behind Rhea; '
        'a rapid push frames the Reaper’s windup and charge into the lens before the closing fade.\n\n'
        '[New sequence filmstrip](duel_filmstrip.png) · [Wind beat](wind_filmstrip.png) · [Full orbit](orbit_filmstrip.png) · '
        '[Charge](charge_filmstrip.png) · [Whole-scene keyframes](keyframes.png) · [Capture record](verification.json)\n\n'
        'All 1,260 approved opening frames remain pixel-exact at native resolution. The movie contains 1,920 frames and '
        '32 seconds of uninterrupted Wintermute 2 with timed effects. Review audio reconstructs the runtime files and gains '
        'because SDL dummy has no loopback. Saves and settings are unchanged. The final fade returns this unplaced Gallery study '
        'to the Gallery; playable boss encounter integration is outside this preview.\n\n'
        'This continuation is awaiting review and remains unmerged.\n')
    print(json.dumps(dict(duration=32,fps=fps,frames=1920,preserved_opening=1260,
                         video_bytes=(output/'preview.mp4').stat().st_size)))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args();capture(args.output.resolve())
