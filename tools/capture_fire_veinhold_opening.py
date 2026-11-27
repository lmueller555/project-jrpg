"""Capture a real Gallery prologue clip or its complete film at native detail.

Video passes through Game.draw at the requested cadence (60 FPS by default).
Audio is reconstructed offline from the production WAVs and scene clock; it is
not SDL loopback or a claim of hardware listening review. No saves/settings are
persisted. --shot-id accepts an authored ID or its Gallery entry ID.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from time import perf_counter
import wave

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from PIL import Image, ImageDraw
import pygame

from main import Game
from fire_veinhold_opening import available_shots, sequence_duration
from prologue_flight_audio import (ASSETS, CUES, DOWNSTROKE_PHASE,
                                   PrologueFlightAudio, wing_phase_at, FLAP_WINDOWS)

FPS = 60
OUT = ROOT/'docs/reviews/veinhold_bridge_run'


def clip_spec(shot_id=None):
    """Resolve authored/Gallery identifiers without constructing a Game."""
    shots = available_shots()
    if shot_id in (None, 'all', 'complete', 'fire_veinhold_opening'):
        return {'entry':'fire_veinhold_opening', 'shot_id':None, 'stem':'complete',
                'offset':0., 'duration':sequence_duration()}
    offset = 0.
    for index, shot in enumerate(shots, 1):
        entry = shot.get('gallery_id', f'fire_veinhold_shot_{index:02d}')
        if shot_id in (shot['id'], entry):
            return {'entry':entry, 'shot_id':shot['id'], 'stem':f'shot{index:02d}',
                    'offset':offset, 'duration':float(shot['duration'])}
        offset += float(shot['duration'])
    raise ValueError('Unknown implemented prologue clip: '+str(shot_id))


def _samples(name):
    with wave.open(str(ASSETS/name), 'rb') as stream:
        if stream.getframerate() != 48000 or stream.getnchannels() != 2:
            raise ValueError('Flight audio export must be stereo 48 kHz')
        return np.frombuffer(stream.readframes(stream.getnframes()), '<i2').reshape(-1, 2)/32768.


def audio_preview(path, seconds=25., start_seconds=0.):
    """Reconstruct the same global-clock mix for a whole film or late clip."""
    rate = 48000
    count = round(seconds*rate)
    times = start_seconds+np.arange(count)/rate
    wind = _samples('wind_loop.wav')
    gain = np.fromiter((PrologueFlightAudio._wind_gain(float(t)) for t in times),
                       dtype=np.float64, count=count)
    # A fresh preview gets the same short loop fade; authored global time still
    # controls the waveform phase and all later effects.
    gain *= np.minimum(1., np.arange(count)/rate/.09)
    pan = .12*np.sin(times*.55)
    wind_indices = np.floor(times*rate).astype(np.int64) % len(wind)
    mix = wind[wind_indices]*gain[:, None]
    mix[:, 0] *= np.minimum(1., 1-pan)
    mix[:, 1] *= np.minimum(1., 1+pan)
    events = [dict(cue) for cue in CUES]
    # Only the original powered windows contribute feather Foley, even when
    # the cinematic grows beyond the eagle's opening shot.
    for before in np.arange(0., min(13.25, start_seconds+seconds), .001):
        now = before+.001
        if not any(start <= now < end for start, end in FLAP_WINDOWS):
            continue
        first, last = wing_phase_at(before), wing_phase_at(now)
        boundary = np.floor(first-DOWNSTROKE_PHASE)+1+DOWNSTROKE_PHASE
        if first < boundary <= last:
            at = before+(now-before)*(boundary-first)/(last-first)
            events.append({'id':'wing', 'time':float(at), 'file':'wing_feather.wav',
                           'gain':.22, 'pan':-.08})
    audible = []
    for event in events:
        sample = _samples(event['file']).copy()
        sample[:, 0] *= event['gain']*min(1., 1-event['pan'])
        sample[:, 1] *= event['gain']*min(1., 1+event['pan'])
        start = round((event['time']-start_seconds)*rate)
        end = min(count, start+len(sample))
        if end <= 0 or start >= count:
            continue
        source_start = max(0, -start)
        target_start = max(0, start)
        mix[target_start:end] += sample[source_start:source_start+end-target_start]
        audible.append(event)
    alert_details = None
    machinery_details = None
    running_details = None
    if start_seconds+seconds > 25:
        from prologue_alert_audio import mix_alert_audio
        mix += mix_alert_audio(start_seconds, seconds, sample_rate=rate)
        machinery_details = {'start_global_seconds':25., 'retreat_start_global_seconds':34.}
    if start_seconds+seconds > 30:
        alert_details = {'alarm_start_global_seconds':30., 'rush_start_global_seconds':34.,
                         'bridge_settle_global_seconds':35.}
    if start_seconds < 42. and start_seconds+seconds > 39.:
        from prologue_alert_audio import running_contact_events
        running_details = {'start_global_seconds':39., 'end_global_seconds':42.,
                           'method':'Contact cues from the production runner manifest and alert mixer.',
                           'events':[dict(cue) for cue in running_contact_events()
                                     if cue['time'] < start_seconds+seconds
                                     and cue['time']+cue['duration'] > start_seconds]}
    peak = float(np.max(np.abs(mix))) if count else 0.
    if peak >= 1.:
        raise AssertionError('Preview audio clipped')
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(2);stream.setsampwidth(2);stream.setframerate(rate)
        stream.writeframes(np.round(mix*32767).astype('<i2').tobytes())
    return {'method':'Offline reconstruction from production WAVs, phase and cue metadata; not live loopback.',
            'effects_volume':1., 'live_capture_mixer':'Muted; this soundtrack is reconstructed separately.',
            'global_start_seconds':start_seconds, 'events':sorted(audible, key=lambda cue:cue['time']),
            'machinery':machinery_details, 'alert':alert_details,
            'running':running_details, 'peak':peak}


def _sample_frames(spec, fps, count):
    if spec['shot_id'] is None:
        cues = (0., 15., 25., 27.5, 30., 32., 34., 34.5, 35., 37.,
                39., 39.5, 40.5, 41.5)
        return {min(count-1, round(value*fps)) for value in cues if value < spec['duration']} | {count-1}
    return set(np.linspace(0, count-1, 6).round().astype(int))


def _orbit_camera_sheet(scene, path):
    """Inspect all 15-degree checkpoints, including the shared terminal pose."""
    contact = Image.new('RGB', (960, 4*184), '#10271f')
    draw = ImageDraw.Draw(contact)
    # The camera eases, so equal angular checkpoints do not have equal time
    # spacing. Select actual authored samples rather than inventing new views.
    angles = [scene.state_at(index/60)['camera'].get('orbit_degrees', index*.6)
              for index in range(301)]
    indices = [min(range(301), key=lambda index:abs(angles[index]-angle))
               for angle in range(0,181,15)]
    for number, index in enumerate(indices):
        frame = scene.render_frame(index/60)
        picture = Image.frombytes('RGB', frame.get_size(), pygame.image.tobytes(frame, 'RGB'))
        picture = picture.resize((240,160), Image.Resampling.NEAREST)
        x, y = (number % 4)*240, (number//4)*184
        contact.paste(picture, (x,y))
        draw.text((x+6,y+164), f'{index:03d} / {index/60:.3f}s / {angles[index]:.1f}°', fill='#f8f0d9')
    contact.save(path)
    # Gallery close already released this owner. Review seeks above must not
    # leave its cache populated after the disposable session has ended.
    for reel in getattr(scene, '_perspectives', {}).values():
        reel.close()


@contextmanager
def _production_picture_tap(scene):
    """Copy the production picture before draw() adds its pause/Skip controls.

    Game.draw still drives the actual renderer and UI. This avoids rendering a
    second picture for encoding or silently recording the decorated UI surface.
    """
    original = scene.render_frame
    had_override = 'render_frame' in vars(scene)
    previous_override = vars(scene).get('render_frame')
    picture = {}
    def tapped(*args, **kwargs):
        frame = original(*args, **kwargs)
        picture['frame'] = frame.copy()
        picture['calls'] = picture.get('calls', 0)+1
        return frame
    scene.render_frame = tapped
    try:
        yield picture
    finally:
        if had_override:
            scene.render_frame = previous_override
        else:
            del scene.render_frame


def capture(out=OUT, reduced_motion=False, shot_id=None, fps=FPS):
    if type(fps) is not int or not 1 <= fps <= 120:
        raise ValueError('Capture FPS must be an integer from 1 to 120')
    spec = clip_spec(shot_id)
    out = Path(out).resolve();out.mkdir(parents=True, exist_ok=True)
    suffix = '_reduced_motion' if reduced_motion else ''
    stem = spec['stem']+suffix
    started = perf_counter()
    with tempfile.TemporaryDirectory(prefix='prologue-capture-') as temporary:
        folder = Path(temporary)
        parent = Game(window_size=(960, 720), fullscreen=False,
                      save_path=folder/'journey.json', settings_path=folder/'settings.json')
        parent.audio.music_volume = 0
        parent.audio.effects_volume = 0
        parent.audio.reduced_motion = reduced_motion
        assert parent.open_gallery()
        launch_started = perf_counter()
        assert parent.launch_gallery_scene(spec['entry']), parent.gallery.error
        launch_ms = (perf_counter()-launch_started)*1000
        session = parent.gallery_session
        top = session.viewport_rect.top
        parent.window = pygame.display.set_mode((960, 640+top))
        session._layout()
        assert session.game.ui_surface.get_size() == (960, 640)
        scene = session.game.cinematic
        states, stills, draw_times, update_times = [], [], [], []
        peak_cache_bytes = peak_decoded_bytes = peak_runner_cache_bytes = 0
        count = round(fps*scene.duration)
        still_indices = _sample_frames(spec, fps, count)
        silent = folder/'silent.mp4'
        encoder = subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y',
            '-f','rawvideo','-pix_fmt','rgb24','-s','960x640','-r',str(fps),'-i','-',
            '-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p',
            str(silent)], stdin=subprocess.PIPE)
        with _production_picture_tap(scene) as picture:
            try:
                for index in range(count):
                    if session.closed:
                        raise AssertionError('Production replay completed before the requested final frame')
                    before = perf_counter()
                    picture.clear()
                    parent.draw()
                    draw_times.append(perf_counter()-before)
                    if 'frame' not in picture:
                        raise AssertionError('Production Game.draw did not render a cinematic picture')
                    assert picture['calls'] == 1, 'Capture must use one production render per displayed frame'
                    frame = picture['frame']
                    assert frame.get_size() == (960, 640)
                    caches = [reel.cache_info for reel in getattr(scene, '_perspectives', {}).values()]
                    peak_cache_bytes = max(peak_cache_bytes, sum(info['bytes'] for info in caches))
                    peak_decoded_bytes = max(peak_decoded_bytes,
                                            sum(info.get('decoded_bytes', info['bytes']) for info in caches))
                    runner_caches = [runner.cache_info for runner in getattr(scene, '_running', {}).values()]
                    peak_runner_cache_bytes = max(peak_runner_cache_bytes,
                                                  sum(info['bytes'] for info in runner_caches))
                    encoder.stdin.write(pygame.image.tobytes(frame, 'RGB'))
                    if index in still_indices:
                        pygame.image.save(frame, str(out/f'{stem}_{index:04d}.png'))
                        if len(stills) == 2:
                            pygame.image.save(parent.window, str(out/f'{stem}_gallery_replay.png'))
                        stills.append((index, frame.copy()))
                        state = scene.state_at(scene.elapsed)
                        states.append({'capture_frame':index, 'local_seconds':index/fps,
                                       'global_seconds':spec['offset']+index/fps, 'state':state})
                    before = perf_counter()
                    parent.update(1/fps, (0, 0), False)
                    update_times.append(perf_counter()-before)
                encoder.stdin.close()
                assert encoder.wait() == 0
            finally:
                if encoder.poll() is None:
                    encoder.kill();encoder.wait()
        # Permit one floating-point endpoint update without recording an extra
        # duplicate display frame or extending the authored movie.
        if not session.closed:
            assert scene.duration-scene.elapsed < 1e-6
            parent.update(1/fps, (0, 0), False)
        assert session.closed and parent.gallery_session is None
        assert session.playback.finished and not parent.gallery.error, parent.gallery.error
        assert parent.on_gallery
        assert not list(folder.glob('*.json')), 'Capture wrote a journey/settings file'
        runtime_cache_stats = [dict(reel.cache_info)
                               for reel in getattr(scene, '_perspectives', {}).values()]
        runtime_runner_stats = [dict(runner.cache_info)
                                for runner in getattr(scene, '_running', {}).values()]
        if spec['shot_id'] == 'island_orbit':
            _orbit_camera_sheet(scene, out/f'{stem}_camera_contact_sheet.png')
        parent.draw()
        pygame.image.save(parent.window, str(out/f'{stem}_gallery_return.png'))
        parent.music.stop();parent.opening_audio.reset();parent.regional_audio.reset()
        audio = audio_preview(folder/'audio.wav', scene.duration, spec['offset'])
        target = out/f'{stem}.mp4'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(silent),
            '-i',str(folder/'audio.wav'),'-c:v','copy','-c:a','aac','-b:a','160k',
            '-shortest','-movflags','+faststart',str(target)], check=True)
        contact = Image.new('RGB', (960, math.ceil(len(stills)/3)*240), '#10271f')
        draw = ImageDraw.Draw(contact)
        for number, (index, frame) in enumerate(stills):
            picture = Image.frombytes('RGB', frame.get_size(), pygame.image.tobytes(frame, 'RGB'))
            picture.thumbnail((320, 214))
            x, y = (number % 3)*320, (number//3)*240
            contact.paste(picture, (x, y))
            draw.text((x+8, y+222), f'{index/fps:.2f}s (reel {spec["offset"]+index/fps:.2f}s)', fill='#f8f0d9')
        contact.save(out/f'{stem}_filmstrip.png')
        runtime_files = ('main.py','gallery_session.py','fire_veinhold_opening.py',
                         'cinematic_smoke.py','cinematic_facility.py',
                         'cinematic_perspective.py','cinematic_bridge_run.py','prologue_flight_audio.py',
                         'prologue_alert_audio.py','cutscene_gallery.py')
        timings = (np.asarray(draw_times)+np.asarray(update_times))*1000
        metadata = {'fps':fps, 'frames':count, 'duration':scene.duration, 'render_size':[960,640],
                    'entry':spec['entry'], 'authored_offset_seconds':spec['offset'],
                    'reduced_motion':reduced_motion,
                    'source':'Production Game.draw renderer tapped before pause/Skip controls in the save-disabled Gallery session',
                    'natural_completion':True, 'no_persistent_files_written':True,
                    'performance':{'method':'SDL dummy, draw+update wall time including the clean-picture copy; excludes encoder writes and review stills.',
                        'gallery_launch_ms':launch_ms,
                        'peak_decoded_frame_cache_bytes':peak_decoded_bytes,
                        'peak_frame_cache_bytes_with_pending_reservations':peak_cache_bytes,
                        'perspective_cache_at_completion':runtime_cache_stats,
                        'peak_runner_image_cache_bytes':peak_runner_cache_bytes,
                        'runner_cache_at_completion':runtime_runner_stats,
                        'mean_frame_ms':float(np.mean(timings)), 'p95_frame_ms':float(np.percentile(timings,95)),
                        'max_frame_ms':float(np.max(timings)),
                        'frames_above_60fps_budget':int(np.count_nonzero(timings > 1000/60)),
                        'capture_wall_seconds':perf_counter()-started},
                    'audio':audio, 'states':states,
                    'source_sha256':{path.relative_to(ROOT).as_posix():sha256(path.read_bytes()).hexdigest()
                        for path in sorted(scene.scene_path.parent.rglob('*')) if path.is_file()},
                    'runtime_sha256':{name:sha256((ROOT/name).read_bytes()).hexdigest()
                        for name in runtime_files if (ROOT/name).is_file()},
                    'video_sha256':sha256(target.read_bytes()).hexdigest()}
        (out/f'{stem}_capture.json').write_text(json.dumps(metadata, indent=2)+'\n')
        # Diagnostic seeks may reopen a renderer after Gallery completion.
        # Release every scene owner before leaving this disposable runtime.
        scene.reset()
    pygame.quit()
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--reduced-motion', action='store_true')
    parser.add_argument('--shot-id', help='Authored ID, Gallery ID, or complete (the default).')
    parser.add_argument('--fps', type=int, default=FPS)
    args = parser.parse_args()
    print(capture(args.out, args.reduced_motion, args.shot_id, args.fps))
