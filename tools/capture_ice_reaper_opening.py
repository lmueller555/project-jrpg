"""Capture the complete Ice Reaper Gallery study at 60 FPS.

SDL dummy has no loopback: the review audio is reconstructed from the runtime
score and action cue files, at their observed/configured gains and cue offsets.
Temporary journey/settings paths never touch ordinary user saves.
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

from PIL import Image, ImageDraw
import pygame

from main import Game
from tools.capture_gallery import capture_thumbnails


FPS = 60
SIZE = (960, 640)
DEFAULT_OUTPUT = ROOT/'docs/reviews/ice_reaper_continuity'
MUSIC = ROOT/'assets/music/runtime/wintermute2.ogg'
KEYFRAME_TIMES = {
    0: 'brush', 1: 'wide', 4.2: 'alarm', 6: 'aim', 7.3: 'dash',
    8.5: 'slow_slash', 9.2: 'shield_impact', 10.4: 'orbit',
    12: 'mira_loading', 13.8: 'scope', 14.7: 'shard_destruction',
    15.8: 'rhea_eyes', 16.7: 'release', 19.8: 'panorama',
}


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mix_review_audio(video, movie, duration, music_gain, effects_gain):
    """Reconstruct the same deterministic production cues, never claim loopback."""
    from ice_reaper_audio import CUES
    cues = [dict(cue) for cue in CUES if 0 <= cue['time'] < duration]
    command = ['ffmpeg', '-y', '-v', 'error', '-i', str(video), '-i', str(MUSIC)]
    filters = [f'[1:a]volume={music_gain},atrim=duration={duration},asetpts=PTS-STARTPTS[music]']
    labels = ['[music]']
    for index, cue in enumerate(cues, 2):
        file = ROOT/cue['file']
        if not file.is_file():
            raise FileNotFoundError(file)
        command += ['-i', str(file)]
        gain = cue['gain']*effects_gain
        delay = round(cue['time']*1000)
        label = f'sfx{index}'
        filters.append(f'[{index}:a]volume={gain},adelay={delay}:all=1[{label}]')
        labels.append(f'[{label}]')
        cue.update(sha256=file_hash(file), rendered_gain=gain)
    filters.append(''.join(labels)+f'amix=inputs={len(labels)}:duration=longest:normalize=0,'
                   f'atrim=duration={duration}[mix]')
    command += ['-filter_complex', ';'.join(filters), '-map', '0:v:0', '-map', '[mix]',
                '-t', f'{duration:.6f}', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                '-movflags', '+faststart', str(movie)]
    subprocess.run(command, check=True)
    return cues


def capture(output, fps=FPS):
    if fps not in (30, 60):
        raise ValueError('Review capture supports 30 or 60 FPS')
    output.mkdir(parents=True, exist_ok=True)
    capture_thumbnails(['ice_reaper_opening'])
    frames, snapshots, gains, completion = [], [], [], []
    keyframes = {round(time*fps): name for time, name in KEYFRAME_TIMES.items()}
    with tempfile.TemporaryDirectory(prefix='ice-reaper-capture-') as folder:
        folder = Path(folder)
        journey, settings = folder/'journey.json', folder/'settings.json'
        parent = Game(window_size=(960, 800), fullscreen=False,
                      start_on_title=True, save_path=journey, settings_path=settings)
        try:
            parent.audio.set_music(1)
            parent.audio.set_effects(1)
            # Defaults are already 100%; setters need not write a fresh file.
            parent.audio._save()
            settings_before = settings.read_bytes()
            if not parent.open_gallery() or not parent.launch_gallery_scene('ice_reaper_opening'):
                raise RuntimeError(parent.gallery.error if parent.gallery else 'Gallery did not open')
            session = parent.gallery_session
            child, scene = session.game, session.game.opening_cinematic
            duration = scene.duration
            frame_count = round(duration*fps)
            effects_gain = child.audio.effects_volume
            frozen = (child._progress_signature(), child.elapsed_ms,
                      tuple(child.player.position))
            callback = scene._on_finish
            if callback is None:
                raise AssertionError('The production preview has no completion callback')

            def completed():
                completion.append(dict(elapsed=scene.elapsed, reason=scene.finished_reason))
                if frozen != (child._progress_signature(), child.elapsed_ms,
                              tuple(child.player.position)):
                    raise AssertionError('The cinematic advanced the ordinary world')
                return callback()

            scene._on_finish = completed
            video = folder/'video.mp4'
            command = [
                'ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                '-s', f'{SIZE[0]}x{SIZE[1]}', '-r', str(fps), '-i', 'pipe:0',
                '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
                '-maxrate', '4M', '-bufsize', '8M',
                '-threads', '2', '-pix_fmt', 'yuv420p', str(video),
            ]
            with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
                assert encoder.stdin is not None
                for frame in range(frame_count):
                    if not scene.active:
                        raise AssertionError(f'Preview ended before frame {frame}')
                    if child.music.desired_track != 'wintermute2':
                        raise AssertionError('The preview selected the wrong soundtrack')
                    if frozen != (child._progress_signature(), child.elapsed_ms,
                                  tuple(child.player.position)):
                        raise AssertionError('The cinematic advanced the ordinary world')
                    parent.draw()
                    assert child.ui_surface is not None
                    if child.ui_surface.get_size() != SIZE:
                        raise AssertionError('The review must retain an exact 2x native pixel scale')
                    image = child.ui_surface
                    encoder.stdin.write(pygame.image.tobytes(image, 'RGB'))
                    gains.append(pygame.mixer.music.get_volume())
                    record = dict(
                        frame=frame, time=frame/fps, scene_time=scene.elapsed,
                        shot=scene.shot, camera=list(scene.camera_position),
                        zoom=scene.camera_zoom, brush=scene.brush_progress,
                        dialogue=scene.dialogue['text'] if scene.dialogue else None)
                    if scene.elapsed >= 5 and scene.action_stage is not None:
                        record['action'] = scene.action_stage.telemetry(scene.elapsed)
                    frames.append(record)
                    if frame in keyframes:
                        name = f'{frame:04}_{keyframes[frame]}.png'
                        pygame.image.save(image, str(output/name))
                        snapshots.append(name)
                    parent.update(1/fps, (0, 0), False)
                encoder.stdin.close()
                if encoder.wait():
                    raise RuntimeError('FFmpeg could not encode the cinematic frames')
            if completion != [dict(elapsed=duration, reason='completed')]:
                raise AssertionError(f'Incorrect cinematic completion: {completion}')
            if not session.closed or parent.gallery_session is not None or not parent.on_gallery:
                raise AssertionError('The preview did not return to Gallery at its authored duration')
            if journey.exists() or settings.read_bytes() != settings_before:
                raise AssertionError('Preview changed journey or settings files')
            if max(gains)-min(gains) > 1/128:
                raise AssertionError('Unexpected soundtrack volume change during capture')
            cues = mix_review_audio(video, output/'preview.mp4', duration, gains[0], effects_gain)
        finally:
            if parent.gallery_session is not None:
                parent.gallery_session.close(resume_music=False)
            parent.music.stop()
            pygame.quit()

    probe = json.loads(subprocess.run([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json',
        str(output/'preview.mp4'),
    ], check=True, capture_output=True, text=True).stdout)
    video_stream = next(stream for stream in probe['streams'] if stream['codec_type'] == 'video')
    audio_stream = next(stream for stream in probe['streams'] if stream['codec_type'] == 'audio')
    if (int(video_stream['nb_frames']) != frame_count
            or abs(float(video_stream['duration'])-duration) > .001
            or abs(float(audio_stream['duration'])-duration) > .025):
        raise AssertionError('The encoded review clip differs from the authored duration')
    sheet = Image.new('RGB', (960, math.ceil(len(snapshots)/2)*342), '#132338')
    draw = ImageDraw.Draw(sheet)
    for index, name in enumerate(snapshots):
        x, y = (index%2)*480, (index//2)*342
        with Image.open(output/name) as image:
            sheet.paste(image.resize((480, 320), Image.Resampling.NEAREST), (x, y+22))
        draw.text((x+8,y+5), name, fill='#eee7d6')
    sheet.save(output/'keyframes.png', optimize=True)
    report = dict(
        version=2, preview='ice_reaper_opening', duration_seconds=duration,
        full_cinematic_duration_seconds=scene.data.get('full_cinematic_duration', duration), fps=fps, frames=len(frames),
        completion=completion, save_and_settings_unchanged=True,
        music=dict(cue='wintermute2', file=MUSIC.relative_to(ROOT).as_posix(),
                   sha256=file_hash(MUSIC), observed_gain=gains[0], segment=[0,duration]),
        effects=dict(settings_gain=effects_gain, cues=cues),
        audio_capture_method='Reconstructed from runtime score and timed SFX assets; SDL dummy has no loopback',
        scene_sha256=file_hash(ROOT/'assets/story/ice_reaper_opening/scene.json'),
        runtime_sources={name:file_hash(ROOT/name) for name in
                         ('opening_cinematic.py', 'ice_reaper_opening.py', 'ice_reaper_action.py',
                          'ice_reaper_audio.py', 'cutscene_gallery.py')},
        source_art_review='awaiting_user_review', snapshots=snapshots, timeline=frames,
        video_sha256=file_hash(output/'preview.mp4'),
        encoded=dict(duration=probe['format']['duration'], video_fps=video_stream['avg_frame_rate'],
                     video_frames=video_stream['nb_frames'], audio_duration=audio_stream['duration']))
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('duration_seconds','fps','frames','completion','encoded')}))
    print('Review clip:', output/'preview.mp4')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--fps', type=int, choices=(30,60), default=FPS,
                        help='60 for final review; 30 for a quicker draft')
    args = parser.parse_args()
    capture(args.output.resolve(), fps=args.fps)
