"""Review the integrated scene-sprite awakening in the complete 21-second clip.

Capture uses the production Game/Gallery path. The first fifteen seconds are
checked against pre-integration native frames; every later frame must match the
approved isolated awakening study. Existing review folders are not rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import subprocess

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/'tools')]

from PIL import Image, ImageDraw, ImageFont
import pygame
import capture_ice_reaper_opening as production

OUTPUT = ROOT/'docs/reviews/ice_reaper_scene_awakening'
EARLY_BASELINE = OUTPUT/'early_scene_baseline.json'
STUDY_BASELINE = OUTPUT/'approved_study_baseline.json'
KEYFRAMES = {
    0:'brush',1:'wide',4.2:'alarm',6:'aim',7.3:'dash',8.5:'slow_slash',
    9.2:'shield_impact',10.4:'orbit',12:'mira_loading',13.8:'scope',14.7:'shard_destruction',
    15.25:'rhea_closed',16.05:'rhea_strained',16.62:'eye_gleam',17.05:'rhea_angry',
    17.32:'shatter',17.6:'fast_retreat',17.95:'first_shoulder',19.1:'sweep_midpoint',
    20.25:'opposite_shoulder',20.8:'final_hold',
}
POSTERS = {
    15.25:'rhea_closed.png',16.05:'rhea_strained.png',16.62:'eye_gleam.png',
    17.05:'rhea_angry.png',17.32:'shatter.png',17.6:'fast_retreat.png',
    17.95:'first_shoulder.png',19.1:'sweep_midpoint.png',20.25:'opposite_shoulder.png',
    20.8:'final.png',
}
STRIPS = {
    'awakening_filmstrip':(15.25,16.05,16.62,17.05,17.32,17.6,17.95,19.1,20.25),
    'sweep_filmstrip':(17.95,18.5,19.1,19.7,20.25,20.8),
    'rescue_filmstrip':(7.3,7.5,8.5,8.99,9.2,10.4),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frame_hash(canvas):
    return hashlib.sha256(pygame.image.tobytes(canvas,'RGB')).hexdigest()


def assert_trace(stage, local):
    if hasattr(stage,'rhea_closeup'):
        raise AssertionError('Rejected portrait overlay remains attached to the production stage')
    trace = stage.last_draw_trace
    rhea = [item for item in trace if item.get('actor')=='rhea']
    layers = [item['prison_layer'] for item in trace if 'prison_layer' in item]
    if len(rhea) != 1:
        raise AssertionError(f'Production drew {len(rhea)} Rhea instances at local time {local}')
    expected = ['back','front'] if local < 2.35-1e-9 else []
    if layers != expected:
        raise AssertionError(f'Wrong original-prison draw layers at {local}: {layers}')
    return dict(rhea_draws=len(rhea),prison_layers=layers,representation=rhea[0]['representation'])


def verify_early(stage):
    baseline = json.loads(EARLY_BASELINE.read_text())
    result = {}
    canvas = pygame.Surface((480,320))
    for label,expected in baseline['native_rgb_hashes'].items():
        stage.draw(canvas,float(label))
        actual = frame_hash(canvas)
        if actual != expected:
            raise AssertionError(f'The earlier cinematic changed at {label} seconds')
        result[label] = actual
    return dict(baseline_sha256=digest(EARLY_BASELINE),
                source_commit=baseline['source_commit'],unchanged_native_frames=result)


def decode_frames(video, times, fps):
    indices = sorted({round(time*fps) for time in times})
    expression = '+'.join(f'eq(n\\,{index})' for index in indices)
    with tempfile.TemporaryDirectory(prefix='integrated-rhea-frames-') as folder:
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(video),'-vf',
                        f'select={expression}','-fps_mode','vfr',
                        str(Path(folder)/'%04d.png')],check=True)
        files = sorted(Path(folder).glob('*.png'))
        if len(files) != len(indices):
            raise AssertionError('Delivered movie does not contain every review frame')
        return {index:Image.open(path).convert('RGB').copy()
                for index,path in zip(indices,files)}


def filmstrip(frames, times, fps, path, title):
    width,height = 480,320
    board = Image.new('RGB',(width*3,38+math.ceil(len(times)/3)*(height+28)),'#142331')
    draw = ImageDraw.Draw(board)
    fontpath = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    font = ImageFont.truetype(str(fontpath),18) if fontpath.exists() else ImageFont.load_default()
    draw.text((12,8),title,font=font,fill='#f5e7c2')
    for index,time in enumerate(times):
        x,y = index%3*width,38+index//3*(height+28)
        draw.text((x+9,y+4),f'{time:.2f} seconds',font=font,fill='#e4edf2')
        image = frames[round(time*fps)].resize((width,height),Image.Resampling.NEAREST)
        board.paste(image,(x,y+28))
    board.save(path,optimize=True)


def capture(output=OUTPUT, *, fps=60):
    from ice_reaper_action import IceReaperActionStage as Stage
    output.mkdir(parents=True,exist_ok=True)
    baseline = json.loads(STUDY_BASELINE.read_text())
    samples = baseline['samples']
    if fps != 60 or len(samples) != 354:
        raise ValueError('Final integrated review requires 60 FPS and all 354 approved study frames')
    pygame.init();pygame.display.set_mode((480,320))
    try:
        stage = Stage(ROOT/'assets/story/ice_reaper_rescue',strict=True)
        early = verify_early(stage)
    finally:
        pygame.quit()
    sourcefiles = ('ice_reaper_action.py','rhea_scene_awakening.py','ice_reaper_opening.py',
                   'ice_reaper_audio.py','ice_reaper_rune.py','cutscene_gallery.py',
                   'tools/capture_ice_reaper_scene_awakening.py')
    sources = {name:digest(ROOT/name) for name in sourcefiles}
    art = {str(path.relative_to(ROOT)):digest(path)
           for path in sorted((ROOT/'assets/story/rhea_scene_awakening_study').rglob('*')) if path.is_file()}
    actual = {}
    original_draw = Stage.draw
    original_keyframes = production.KEYFRAME_TIMES
    original_thumbnails = production.capture_thumbnails

    def checked_draw(stage,canvas,elapsed,reduced_motion=False):
        original_draw(stage,canvas,elapsed,reduced_motion)
        if elapsed < 15.1-1e-8:
            return
        local = max(0.,elapsed-15.1)
        index = round(local*fps)
        if not 0 <= index < len(samples):
            return
        expected = samples[index]
        native = frame_hash(canvas)
        if native != expected['sha256']:
            raise AssertionError(f'Integrated native frame {index} differs from the approved study at {elapsed}')
        trace = assert_trace(stage,expected['local_time'])
        camera = stage.awakening.camera(expected['local_time'])
        if pygame.Vector3(camera.position).distance_to(expected['camera']) > 1e-8:
            raise AssertionError(f'Integrated camera differs from the approved study at local frame {index}')
        actual[index] = dict(frame=index,absolute_time=elapsed,local_time=expected['local_time'],
                             sha256=native,camera=list(camera.position),**trace)

    try:
        Stage.draw = checked_draw
        production.KEYFRAME_TIMES = KEYFRAMES
        # The integration review captures the real Gallery session without
        # rewriting historical Gallery thumbnail/contact-sheet review files.
        production.capture_thumbnails = lambda _ids: None
        production.capture(output,fps=fps)
    finally:
        Stage.draw = original_draw
        production.KEYFRAME_TIMES = original_keyframes
        production.capture_thumbnails = original_thumbnails
    if len(actual) != 354:
        raise AssertionError(f'Production playback checked {len(actual)} of 354 approved awakening frames')
    if sources != {name:digest(ROOT/name) for name in sourcefiles}:
        raise AssertionError('Runtime changed during capture; recapture the final source')
    if art != {name:digest(ROOT/name) for name in art}:
        raise AssertionError('Approved sprite artwork changed during capture')
    reportpath = output/'verification.json'
    report = json.loads(reportpath.read_text())
    if report['duration_seconds'] != 21 or report['frames'] != 1260:
        raise AssertionError('Complete scene review must contain 1,260 frames and last 21 seconds')
    if len(report['effects']['cues']) != 13:
        raise AssertionError('Existing thirteen runtime sound cues were not retained')
    for name,sha in sources.items():
        report['runtime_sources'][name] = sha
    report['expression_art_hashes'] = art
    preservation = dict(version=1,early_scene=early,
                        approved_study_baseline_sha256=digest(STUDY_BASELINE),
                        approved_native_frames_checked=len(actual),
                        actual_production_draw_trace_checked=len(actual),
                        one_rhea_each_frame=True,only_original_prison=True,
                        no_portrait_overlay=True,study_camera_positions_match=True,
                        samples=[actual[index] for index in sorted(actual)])
    (output/'preservation_verification.json').write_text(json.dumps(preservation,indent=2)+'\n')
    report['awakening_preservation'] = dict(approved_native_frames_checked=len(actual),
                                          early_native_frames_unchanged=len(early['unchanged_native_frames']),
                                          one_rhea_each_frame=True,no_portrait_overlay=True)
    reportpath.write_text(json.dumps(report,indent=2)+'\n')
    times = sorted({*POSTERS,*(time for times in STRIPS.values() for time in times)})
    decoded = decode_frames(output/'preview.mp4',times,fps)
    for time,name in POSTERS.items():
        decoded[round(time*fps)].save(output/name,optimize=True)
    for name,times in STRIPS.items():
        filmstrip(decoded,times,fps,output/f'{name}.png',name.replace('_',' ').title())
    (output/'README.md').write_text(
        '# Ice Reaper — integrated scene-sprite awakening\n\n'
        '[Watch the full updated 21-second cinematic](preview.mp4), captured through the production '
        'Game/Gallery path at 60 FPS.\n\n'
        'Rhea awakens using the existing full-body scene sprite and original prison. The camera '
        'pushes closer as she strains, then opens her angry green eyes. When the prison shatters, '
        'the camera retreats rapidly behind the Ice Reaper while Rhea turns toward her. '
        'It then travels from one shoulder to the other, keeping Rhea and the forming rune central. '
        'The separate illustrated portrait and its second ice enclosure are absent.\n\n'
        '[Awakening filmstrip](awakening_filmstrip.png) · [Shoulder sweep](sweep_filmstrip.png) · '
        '[Full-scene keyframes](keyframes.png) · [Preservation checks](preservation_verification.json) · '
        '[Capture/audio record](verification.json)\n\n'
        'Every one of the 354 integrated awakening frames matches the approved isolated study at native resolution. '
        'Actual production tracing checks one Rhea drawing per frame and only the original prison layers. '
        'Fourteen native samples before 15.1 seconds preserve the earlier rescue and launcher sequence. '
        'The 21-second score and thirteen sound cues remain uninterrupted; audio is reconstructed from '
        'the runtime track/effect files at production gains because SDL dummy has no loopback. '
        'Journey/settings remain unchanged. Historical review folders are preserved.\n\n'
        'The integrated change is awaiting whole-scene review and has not been merged.\n')
    print(json.dumps(dict(duration=21,fps=fps,frames=1260,approved_awakening_frames=len(actual),
                          early_native_frames=len(early['unchanged_native_frames']),
                          video_bytes=(output/'preview.mp4').stat().st_size)))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args = parser.parse_args()
    capture(args.output.resolve())
