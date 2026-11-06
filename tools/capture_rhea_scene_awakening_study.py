"""Capture only the production full-body Rhea awakening; never launch the game.

The short clip shares the full cinematic's renderer. Capture does not alter the
Gallery, save files, production cinematic, or any asset. Review posters and
filmstrip frames are decoded from the delivered MP4.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]

from PIL import Image, ImageDraw, ImageFont
import pygame

OUTPUT = ROOT/'docs/reviews/rhea_scene_awakening_current'
NATIVE = (480, 320)
SIZE = (960, 640)
FPS = 60
MUSIC_START = 15.1
MUSIC_GAIN = .4453125
MUSIC = ROOT/'assets/music/runtime/those_i_swore_to_save.ogg'
SOUNDS = (
    dict(id='ice_creak', time=.35, gain=.12,
         file='assets/audio/sfx/ice_reaper_rhea_closeup/ice_creak.ogg'),
    dict(id='awakening', time=1.5, gain=.34,
         file='assets/audio/sfx/ice_reaper_rescue/awakening.ogg'),
    dict(id='prison_burst', time=2.2, gain=.58,
         file='assets/audio/sfx/ice_reaper_rescue/prison_burst.ogg'),
    dict(id='rune_bloom', time=2.4, gain=.43,
         file='assets/audio/sfx/ice_reaper_rescue/rune_bloom.ogg'),
)
PRODUCTION = (
    'ice_reaper_action.py', 'ice_reaper_opening.py', 'ice_reaper_audio.py',
    'ice_reaper_rune.py', 'rhea_scene_awakening.py', 'cutscene_gallery.py',
    'assets/story/ice_reaper_opening/scene.json',
)
POSTERS = {
    .15: 'closed_eyes.png', .95: 'strained.png', 1.52: 'eye_gleam.png',
    1.95: 'angry.png', 2.22: 'shatter.png', 2.5: 'fast_retreat.png',
    2.85: 'sweep_start.png', 4.: 'sweep_midpoint.png', 5.15: 'sweep_end.png',
    5.7: 'final_hold.png',
}
STRIP_TIMES = (.15, .95, 1.52, 2.22, 2.5, 2.85, 4., 5.15, 5.7)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def production_integrity():
    result = {}
    for name in PRODUCTION:
        path = ROOT/name
        committed = subprocess.check_output(['git','show', f'HEAD:{name}'], cwd=ROOT)
        current = path.read_bytes()
        if current != committed:
            raise AssertionError(f'Production file changed while creating isolated study: {name}')
        result[name] = digest(path)
    tracked_changes = subprocess.check_output(['git','diff','--name-only','HEAD'],
                                             cwd=ROOT, text=True).splitlines()
    if tracked_changes:
        raise AssertionError(f'Isolated study modified tracked files: {tracked_changes}')
    return result


def mix_audio(video, movie, duration):
    command = ['ffmpeg','-y','-v','error','-i',str(video),
               '-ss', str(MUSIC_START), '-i',str(MUSIC)]
    filters = [f'[1:a]volume={MUSIC_GAIN},atrim=duration={duration},asetpts=PTS-STARTPTS[music]']
    labels = ['[music]']
    cues = []
    for index, cue in enumerate(SOUNDS, 2):
        command += ['-i', str(ROOT/cue['file'])]
        label = f'sfx{index}'
        delay = round(cue['time']*1000)
        filters.append(f'[{index}:a]volume={cue["gain"]},adelay={delay}:all=1[{label}]')
        labels.append(f'[{label}]')
        cues.append(dict(cue, sha256=digest(ROOT/cue['file'])))
    filters.append(''.join(labels)+f'amix=inputs={len(labels)}:duration=longest:normalize=0,'
                   f'atrim=duration={duration}[mix]')
    command += ['-filter_complex',';'.join(filters),'-map','0:v:0','-map','[mix]',
                '-t',str(duration),'-c:v','copy','-c:a','aac','-b:a','192k',
                '-movflags','+faststart',str(movie)]
    subprocess.run(command, check=True)
    return cues


def decode_frames(movie, times, fps):
    indices = sorted({round(time*fps) for time in times})
    expression = '+'.join(f'eq(n\\,{index})' for index in indices)
    with tempfile.TemporaryDirectory(prefix='rhea-study-posters-') as folder:
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(movie),'-vf',
                        f'select={expression}','-fps_mode','vfr',
                        str(Path(folder)/'%04d.png')], check=True)
        files = sorted(Path(folder).glob('*.png'))
        if len(files) != len(indices):
            raise AssertionError('Review movie does not contain all requested poster frames')
        return {index:Image.open(path).convert('RGB').copy()
                for index,path in zip(indices,files)}


def filmstrip(frames, times, fps, path):
    width, height = NATIVE
    rows = math.ceil(len(times)/3)
    board = Image.new('RGB',(width*3,38+rows*(height+28)),'#142331')
    draw = ImageDraw.Draw(board)
    fontfile = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    font = ImageFont.truetype(str(fontfile),18) if fontfile.exists() else ImageFont.load_default()
    draw.text((12,8),'Rhea awakening — fast retreat, then shoulder-to-shoulder sweep',font=font,fill='#f5e7c2')
    for index,time in enumerate(times):
        x,y = index%3*width,38+index//3*(height+28)
        draw.text((x+9,y+4),f'{time:.2f} seconds',font=font,fill='#e4edf2')
        image = frames[round(time*fps)].resize(NATIVE,Image.Resampling.NEAREST)
        board.paste(image,(x,y+28))
    board.save(path,optimize=True)


def verify_approved_zoom(study, canvas):
    path = OUTPUT/'approved_zoom_baseline.json'
    baseline = json.loads(path.read_text())
    for label, expected in baseline.items():
        elapsed = float(label)
        camera = study.study_camera(elapsed)
        actual = dict(camera_position=list(camera.position),
                      camera_target=list(camera.target),focal=camera.focal)
        for key,value in actual.items():
            if value != expected[key]:
                raise AssertionError(f'Approved fast-retreat geometry changed at {elapsed}: {key}')
        study.draw(canvas,elapsed)
        frame_hash = hashlib.sha256(pygame.image.tobytes(canvas,'RGB')).hexdigest()
        if frame_hash != expected['frame_sha256']:
            raise AssertionError(f'Approved awakening/fast-retreat frame changed at {elapsed}')
    return dict(baseline=str(path.relative_to(ROOT)),sha256=digest(path),
                native_frame_samples=len(baseline),camera_samples=len(baseline),
                all_frames_and_geometry_unchanged=True,checked_times=list(map(float,baseline)))


def capture(output=OUTPUT, fps=FPS):
    from rhea_scene_awakening_study import RheaSceneAwakeningStudy
    integrity = production_integrity()
    output.mkdir(parents=True,exist_ok=True)
    pygame.init()
    pygame.display.set_mode(NATIVE)
    sourcefiles = ('tools/rhea_scene_awakening_study.py',
                   'tools/capture_rhea_scene_awakening_study.py', *PRODUCTION)
    sources = {name:digest(ROOT/name) for name in sourcefiles}
    asset_folder = ROOT/'assets/story/rhea_scene_awakening_study'
    asset_hashes = {str(path.relative_to(ROOT)):digest(path)
                    for path in sorted(asset_folder.rglob('*')) if path.is_file()}
    frames = []
    try:
        study = RheaSceneAwakeningStudy()
        if hasattr(study, 'rhea_closeup'):
            raise AssertionError('Rejected portrait overlay is still attached to the isolated study')
        duration = float(study.DURATION)
        count = round(duration*fps)
        canvas = pygame.Surface(NATIVE)
        approved_zoom = verify_approved_zoom(study,canvas)
        with tempfile.TemporaryDirectory(prefix='rhea-scene-study-') as folder:
            video = Path(folder)/'silent.mp4'
            command = ['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24',
                       '-s',f'{SIZE[0]}x{SIZE[1]}','-r',str(fps),'-i','pipe:0',
                       '-an','-c:v','libx264','-preset','fast','-crf','20',
                       '-maxrate','4M','-bufsize','8M','-threads','2',
                       '-pix_fmt','yuv420p',str(video)]
            with subprocess.Popen(command,stdin=subprocess.PIPE) as encoder:
                assert encoder.stdin is not None
                for index in range(count):
                    elapsed = index/fps
                    study.draw(canvas,elapsed)
                    rhea_draws = [item for item in study.last_draw_trace if item.get('actor')=='rhea']
                    layers = [item['prison_layer'] for item in study.last_draw_trace if 'prison_layer' in item]
                    if len(rhea_draws) != 1:
                        raise AssertionError(f'Expected one Rhea drawing at {elapsed}, got {rhea_draws}')
                    expected_layers = ['back','front'] if study.canonical_time(elapsed)<16.45 else []
                    if layers != expected_layers:
                        raise AssertionError(f'Unexpected original prison layers at {elapsed}: {layers}')
                    image = pygame.transform.scale(canvas,SIZE)
                    encoder.stdin.write(pygame.image.tobytes(image,'RGB'))
                    frames.append(dict(frame=index,time=elapsed,state=study.telemetry(elapsed),
                                       actual_rhea_draws=len(rhea_draws),actual_prison_layers=layers))
                encoder.stdin.close()
                if encoder.wait() != 0:
                    raise RuntimeError('FFmpeg failed to encode the isolated scene study')
            cues = mix_audio(video,output/'preview.mp4',duration)
    finally:
        pygame.quit()
    if sources != {name:digest(ROOT/name) for name in sourcefiles}:
        raise AssertionError('Study source changed during rendering; recapture the final renderer')
    if integrity != production_integrity():
        raise AssertionError('Production files changed during study capture')
    if asset_hashes != {name:digest(ROOT/name) for name in asset_hashes}:
        raise AssertionError('Expression artwork changed during rendering')
    times = [time for time in (*POSTERS, max(0,duration-.2)) if time < duration]
    decoded = decode_frames(output/'preview.mp4',times,fps)
    for time,name in POSTERS.items():
        if time < duration:
            decoded[round(time*fps)].save(output/name,optimize=True)
    decoded[round((duration-.2)*fps)].save(output/'final.png',optimize=True)
    strip_times = [time for time in STRIP_TIMES if time < duration]
    filmstrip(decoded,strip_times,fps,output/'filmstrip.png')
    probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries',
                      'format=duration:stream=codec_name,codec_type,width,height,avg_frame_rate,nb_frames,duration',
                      '-of','json',str(output/'preview.mp4')]))
    video_stream = next(stream for stream in probe['streams'] if stream['codec_type']=='video')
    audio_stream = next(stream for stream in probe['streams'] if stream['codec_type']=='audio')
    if int(video_stream['nb_frames']) != count:
        raise AssertionError('Encoded movie has a different number of frames')
    if video_stream['avg_frame_rate'] != f'{fps}/1':
        raise AssertionError('Encoded movie has a different frame rate')
    for label,stream in (('video',video_stream),('audio',audio_stream),('container',probe['format'])):
        if abs(float(stream['duration'])-duration) > 1/fps:
            raise AssertionError(f'Encoded {label} duration does not match the study')
    report = dict(version=1,isolated_review=True,production_sequence=True,duration_seconds=duration,fps=fps,
                  frame_count=count,native_resolution=NATIVE,video_resolution=SIZE,
                  video_sha256=digest(output/'preview.mp4'),video_bytes=(output/'preview.mp4').stat().st_size,
                  production_files_unchanged=integrity,source_hashes=sources,expression_art_hashes=asset_hashes,
                  approved_zoom_preservation=approved_zoom,
                  actual_draw_trace_checks=dict(samples=count,one_world_rhea_every_frame=True,
                                                one_original_prison_pair_before_shatter=True,
                                                no_prison_layers_after_fade=True,no_portrait_overlay=True),
                  music=dict(file=str(MUSIC.relative_to(ROOT)),sha256=digest(MUSIC),
                             source_segment=[MUSIC_START,MUSIC_START+duration],gain=MUSIC_GAIN),
                  sound_cues=cues,audio_method='Review mix from existing score/SFX assets; no live audio loopback',
                  probe=probe,frames=frames)
    (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'README.md').write_text(
        '# Rhea awakening — focused production review\n\n'
        f'[Watch only the updated awakening section](preview.mp4): {duration:g} seconds, {fps} FPS.\n\n'
        'The camera moves closer to the existing full-body scene sprite inside the original prison. '
        'Her closed eyes strain and open angrily with a green gleam. When the prison shatters, '
        'the camera rapidly retreats behind the Ice Reaper while Rhea turns to face her. '
        'After reaching the first shoulder at 2.85 seconds, the camera travels through world space '
        'to the opposite shoulder. Rhea and the forming rune remain central, with brief natural '
        'occlusion while the camera passes directly behind the Ice Reaper. It settles into a final hold.\n\n'
        '[Filmstrip](filmstrip.png) · [Angry eyes](angry.png) · [Prison shatter](shatter.png) · '
        '[Sweep start](sweep_start.png) · [Sweep midpoint](sweep_midpoint.png) · [Sweep end](sweep_end.png) · '
        '[Final composition](final.png) · [Capture record](verification.json)\n\n'
        'This short clip uses the same awakening renderer as the complete cinematic. '
        'Capturing it does not alter Gallery, sprites or saves. '
        'Earlier proposal reviews remain in their original folders. '
        'Audio uses a continuous Wintermute 2 excerpt and the existing timed effects.\n')
    print(json.dumps({key:report[key] for key in ('duration_seconds','fps','frame_count','video_bytes')}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--fps',type=int,choices=(30,60),default=FPS)
    args = parser.parse_args()
    capture(args.output.resolve(),args.fps)
