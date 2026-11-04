"""Capture the real five-second Gallery preview and its observed music cue.

SDL dummy has no audio loopback. The clip reconstructs the first five seconds
of the verified runtime OGG at the volume observed during production playback.
Temporary journey/settings paths never touch ordinary user saves.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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


FPS = 30
SIZE = (960, 640)
DEFAULT_OUTPUT = ROOT/'docs/reviews/ice_reaper_opening'
MUSIC = ROOT/'assets/music/runtime/wintermute2.ogg'
KEYFRAMES = {0: 'brush', 15: 'clearing', 30: 'wide', 60: 'reaper',
             82: 'camera_move', 108: 'rhea', 132: 'alarm'}


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(output):
    output.mkdir(parents=True, exist_ok=True)
    capture_thumbnails(['ice_reaper_opening'])
    frames, snapshots, gains, completion = [], [], [], []
    with tempfile.TemporaryDirectory(prefix='ice-reaper-capture-') as folder:
        folder = Path(folder)
        journey, settings = folder/'journey.json', folder/'settings.json'
        parent = Game(window_size=(960, 800), fullscreen=False,
                      start_on_title=True, save_path=journey, settings_path=settings)
        try:
            parent.audio.set_music(1)
            parent.audio.set_effects(0)
            settings_before = settings.read_bytes()
            if not parent.open_gallery() or not parent.launch_gallery_scene('ice_reaper_opening'):
                raise RuntimeError(parent.gallery.error if parent.gallery else 'Gallery did not open')
            session = parent.gallery_session
            child, scene = session.game, session.game.opening_cinematic
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
                '-s', f'{SIZE[0]}x{SIZE[1]}', '-r', str(FPS), '-i', 'pipe:0',
                '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                '-threads', '2', '-pix_fmt', 'yuv420p', str(video),
            ]
            with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
                assert encoder.stdin is not None
                for frame in range(FPS*5):
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
                    image = pygame.transform.scale(child.ui_surface, SIZE)
                    encoder.stdin.write(pygame.image.tobytes(image, 'RGB'))
                    gains.append(pygame.mixer.music.get_volume())
                    frames.append(dict(
                        frame=frame, time=frame/FPS, scene_time=scene.elapsed,
                        shot=scene.shot, camera=list(scene.camera_position),
                        zoom=scene.camera_zoom, brush=scene.brush_progress,
                        dialogue=scene.dialogue['text'] if scene.dialogue else None))
                    if frame in KEYFRAMES:
                        name = f'{frame:03}_{KEYFRAMES[frame]}.png'
                        pygame.image.save(image, str(output/name))
                        snapshots.append(name)
                    parent.update(1/FPS, (0, 0), False)
                encoder.stdin.close()
                if encoder.wait():
                    raise RuntimeError('FFmpeg could not encode the cinematic frames')
            if completion != [dict(elapsed=5., reason='completed')]:
                raise AssertionError(f'Incorrect cinematic completion: {completion}')
            if not session.closed or parent.gallery_session is not None or not parent.on_gallery:
                raise AssertionError('The preview did not return to Gallery at five seconds')
            if journey.exists() or settings.read_bytes() != settings_before:
                raise AssertionError('Preview changed journey or settings files')
            if max(gains)-min(gains) > 1/128:
                raise AssertionError('Unexpected soundtrack volume change during capture')
            movie = output/'preview.mp4'
            subprocess.run([
                'ffmpeg', '-y', '-v', 'error', '-i', str(video), '-i', str(MUSIC),
                '-map', '0:v:0', '-map', '1:a:0', '-t', '5.000',
                '-c:v', 'copy', '-af', f'volume={gains[0]}',
                '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(movie),
            ], check=True)
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
    if (int(video_stream['nb_frames']) != FPS*5
            or abs(float(video_stream['duration'])-5) > .001
            or abs(float(audio_stream['duration'])-5) > .025):
        raise AssertionError('The encoded review clip is not five seconds')
    sheet = Image.new('RGB', (960, 4*342), '#132338')
    draw = ImageDraw.Draw(sheet)
    for index, name in enumerate(snapshots):
        x, y = (index%2)*480, (index//2)*342
        with Image.open(output/name) as image:
            sheet.paste(image.resize((480, 320), Image.Resampling.NEAREST), (x, y+22))
        draw.text((x+8,y+5), name, fill='#eee7d6')
    sheet.save(output/'keyframes.png', optimize=True)
    report = dict(
        version=1, preview='ice_reaper_opening', duration_seconds=5,
        full_cinematic_duration_seconds=45, fps=FPS, frames=len(frames),
        completion=completion, save_and_settings_unchanged=True,
        music=dict(cue='wintermute2', file=MUSIC.relative_to(ROOT).as_posix(),
                   sha256=file_hash(MUSIC), observed_gain=gains[0], segment=[0,5],
                   capture_method='Reconstructed from runtime OGG; SDL dummy has no loopback'),
        scene_sha256=file_hash(ROOT/'assets/story/ice_reaper_opening/scene.json'),
        runtime_sources={name:file_hash(ROOT/name) for name in
                         ('opening_cinematic.py', 'ice_reaper_opening.py', 'cutscene_gallery.py')},
        source_art_review='awaiting_user_review', snapshots=snapshots, timeline=frames,
        video_sha256=file_hash(output/'preview.mp4'),
        encoded=dict(duration=probe['format']['duration'],
                     video_frames=video_stream['nb_frames'],
                     audio_duration=audio_stream['duration']))
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('duration_seconds','frames','completion','encoded')}))
    print('Review clip:', output/'preview.mp4')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    capture(args.output.resolve())
