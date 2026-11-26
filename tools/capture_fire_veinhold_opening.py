"""Capture the real Gallery eagle shot and reconstruct its authored audio.

Frames pass through Game.draw's detailed cinematic branch at30Hz. Audio is an
offline reconstruction of the same exports/scene cues, not SDL loopback or a
claim of hardware listening review. No journey/settings are persisted.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
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
from prologue_flight_audio import (ASSETS, CUES, DOWNSTROKE_PHASE,
                                   PrologueFlightAudio, wing_phase_at)

FPS = 30
OUT = ROOT/'docs/reviews/fire_veinhold_opening'


def _samples(name):
    with wave.open(str(ASSETS/name), 'rb') as stream:
        assert stream.getframerate() == 48000 and stream.getnchannels() == 2
        return np.frombuffer(stream.readframes(stream.getnframes()), '<i2').reshape(-1, 2)/32768.


def audio_preview(path, seconds=10.):
    rate = 48000
    count = round(seconds*rate)
    times = np.arange(count)/rate
    wind = _samples('wind_loop.wav')
    gain = np.array([PrologueFlightAudio._wind_gain(float(t)) for t in times])
    gain *= np.minimum(1., times/.09)
    pan = .12*np.sin(times*.55)
    mix = wind[np.arange(count) % len(wind)]*gain[:, None]
    mix[:, 0] *= np.minimum(1., 1-pan)
    mix[:, 1] *= np.minimum(1., 1+pan)
    events = [dict(cue) for cue in CUES]
    # Detect the exact same phase crossings as the production controller,
    # using a fine clock so preview timing is independent of video cadence.
    for before in np.arange(0., seconds, .001):
        now = min(seconds, before+.001)
        if not (0 <= now < 2 or 5 <= now < 8):continue
        first, last = wing_phase_at(before), wing_phase_at(now)
        boundary = np.floor(first-DOWNSTROKE_PHASE)+1+DOWNSTROKE_PHASE
        if first < boundary <= last:
            at = before+(now-before)*(boundary-first)/(last-first)
            events.append({'id':'wing', 'time':float(at), 'file':'wing_feather.wav',
                           'gain':.22, 'pan':-.08})
    for event in events:
        sample = _samples(event['file']).copy()
        sample[:, 0] *= event['gain']*min(1., 1-event['pan'])
        sample[:, 1] *= event['gain']*min(1., 1+event['pan'])
        start = round(event['time']*rate)
        end = min(count, start+len(sample))
        mix[start:end] += sample[:end-start]
    assert np.max(np.abs(mix)) < 1., 'Preview audio clipped'
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(2);stream.setsampwidth(2);stream.setframerate(rate)
        stream.writeframes(np.round(mix*32767).astype('<i2').tobytes())
    return {'method':'Offline reconstruction from production WAVs, phase and cue metadata; not live loopback.',
            'events':sorted(events, key=lambda cue:cue['time']),
            'peak':float(np.max(np.abs(mix)))}


def capture(out=OUT, reduced_motion=False):
    out = Path(out).resolve();out.mkdir(parents=True, exist_ok=True)
    suffix = '_reduced_motion' if reduced_motion else ''
    with tempfile.TemporaryDirectory(prefix='prologue-capture-') as temporary:
        folder = Path(temporary)
        parent = Game(window_size=(960, 720), fullscreen=False,
                      save_path=folder/'journey.json', settings_path=folder/'settings.json')
        parent.audio.music_volume = 0
        parent.audio.effects_volume = 0
        parent.audio.reduced_motion = reduced_motion
        assert parent.open_gallery()
        assert parent.launch_gallery_scene('fire_veinhold_shot_01'), parent.gallery.error
        session = parent.gallery_session
        # Keep the replay toolbar outside an exact960×640 production viewport.
        top = session.viewport_rect.top
        parent.window = pygame.display.set_mode((960, 640+top))
        session._layout()
        assert session.game.ui_surface.get_size() == (960, 640)
        scene = session.game.cinematic
        states, stills = [], []
        silent = folder/'silent.mp4'
        encoder = subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y',
            '-f','rawvideo','-pix_fmt','rgb24','-s','960x640','-r',str(FPS),'-i','-',
            '-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p',
            str(silent)], stdin=subprocess.PIPE)
        try:
            for index in range(FPS*10):
                parent.draw()
                encoder.stdin.write(pygame.image.tobytes(session.game.ui_surface, 'RGB'))
                if index in (0, 60, 120, 180, 240, 299):
                    stem = f'shot01{suffix}_{index:03d}'
                    frame = scene.render_frame()
                    pygame.image.save(frame, str(out/(stem+'.png')))
                    if index == 120:
                        pygame.image.save(parent.window, str(out/f'gallery_replay{suffix}.png'))
                    stills.append((index, frame.copy()))
                    states.append(scene.state_at(scene.elapsed))
                parent.update(1/FPS, (0, 0), False)
            encoder.stdin.close()
            assert encoder.wait() == 0
        finally:
            if encoder.poll() is None:encoder.kill();encoder.wait()
        assert session.closed and parent.gallery_session is None
        assert parent.on_gallery
        assert not list(folder.glob('*.json')), 'Capture wrote a journey/settings file'
        parent.draw()
        pygame.image.save(parent.window, str(out/f'gallery_return{suffix}.png'))
        parent.music.stop();parent.opening_audio.reset();parent.regional_audio.reset()
        audio = audio_preview(folder/'audio.wav')
        target = out/f'shot01{suffix}.mp4'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(silent),
            '-i',str(folder/'audio.wav'),'-c:v','copy','-c:a','aac','-b:a','160k',
            '-shortest','-movflags','+faststart',str(target)], check=True)
        contact = Image.new('RGB', (960, 2*240), '#10271f')
        draw = ImageDraw.Draw(contact)
        for number, (index, frame) in enumerate(stills):
            picture = Image.frombytes('RGB', frame.get_size(), pygame.image.tobytes(frame, 'RGB'))
            picture.thumbnail((320, 300))
            x, y = (number % 3)*320, (number//3)*240
            contact.paste(picture, (x, y))
            draw.text((x+8, y+222), f'{index/FPS:.2f}s', fill='#f8f0d9')
        contact.save(out/f'filmstrip{suffix}.png')
        metadata = {'fps':FPS, 'frames':300, 'duration':10, 'render_size':[960,640],
                    'entry':'fire_veinhold_shot_01', 'reduced_motion':reduced_motion,
                    'source':'Production Game.draw in the save-disabled Gallery session',
                    'natural_completion':True, 'no_persistent_files_written':True,
                    'audio':audio, 'states':states,
                    'source_sha256':{path.relative_to(ROOT).as_posix():sha256(path.read_bytes()).hexdigest()
                        for path in sorted(scene.scene_path.parent.rglob('*')) if path.is_file()},
                    'runtime_sha256':{name:sha256((ROOT/name).read_bytes()).hexdigest() for name in
                        ('fire_veinhold_opening.py','prologue_flight_audio.py','cutscene_gallery.py')},
                    'video_sha256':sha256(target.read_bytes()).hexdigest()}
        (out/f'capture{suffix}.json').write_text(json.dumps(metadata, indent=2)+'\n')
    pygame.quit()
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--reduced-motion', action='store_true')
    args = parser.parse_args()
    print(capture(args.out, args.reduced_motion))
