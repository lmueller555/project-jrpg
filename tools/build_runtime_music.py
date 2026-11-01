"""Export the user-provided music as Pygame-compatible Ogg Vorbis assets.

Build dependencies: FFmpeg, NumPy and Pygame. The game only needs the exported
OGGs and its existing Pygame dependency. Original uploads are never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MUSIC = ROOT / 'assets/music'
RATE = 48000
SOURCES = (
    dict(identifier='eldenmere', source='Eldenmere Theme.m4a',
         git_sha='57758f45b93257789f1fff434fecce4a43ef8a4c',
         target='eldenmere_theme.ogg', title='Eldenmere Theme', trim_tail=False),
    dict(identifier='battle', source='Kindled Courage.m4a',
         git_sha='8acead411b5d07b89666355cdc559928c90f442e',
         target='kindled_courage.ogg', title='Kindled Courage', trim_tail=True),
    dict(identifier='victory', source='Triumphal Fanfare.m4a',
         git_sha='ab0adebed97a04f13d9a1c5604d76a287bb63ab9',
         target='triumphal_fanfare.ogg', title='Triumphal Fanfare', trim_tail=False,
         loop=False),
    dict(identifier='opening_leitmotif', source='Dare to Dream Leitmotif.m4a',
         git_sha='c057902f21e2d84ac786f5f4ee37ac98f3c073e2',
         target='dare_to_dream_leitmotif.ogg', title='Dare to Dream Leitmotif',
         trim_tail=False, boundary_declick_ms=5),
    # Homebrew's native experimental Vorbis encoder prepends 56 decoded frames.
    dict(identifier='royalty', source='Royalty of the Realm.m4a',
         git_sha='1ead236be4b4a5e5a8a1ec2d83af3e4be1eaf1ac',
         target='royalty_of_the_realm.ogg', title='Royalty of the Realm', trim_tail=False,
         encoder='vorbis', runtime_frame_delta=56),
)


def git_blob_sha(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path),
    ]))


def decode(path):
    raw = subprocess.check_output([
        'ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0',
        '-ar', str(RATE), '-ac', '2', '-f', 'f32le', '-acodec', 'pcm_f32le', '-',
    ])
    audio = np.frombuffer(raw, dtype='<f4').reshape(-1, 2)
    if not np.all(np.isfinite(audio)):
        raise ValueError(f'Non-finite decoded audio: {path.name}')
    return audio


def trimmed_battle(audio):
    # Measure the final near-silent tail in 5 ms RMS blocks. Keep 25 ms after
    # the last block above -60 dBFS, preserving the actual final phrase/reverb.
    block = round(.005 * RATE)
    complete = audio[:len(audio) // block * block].reshape(-1, block, 2)
    rms = np.sqrt(np.mean(complete.astype('float64') ** 2, axis=(1, 2)))
    active = np.flatnonzero(rms > .001)
    if not len(active):
        raise ValueError('Battle source has no audible music')
    last_active_end = int((active[-1] + 1) * block)
    end = min(len(audio), last_active_end + round(.025 * RATE))
    result = audio[:end].copy()
    # Five milliseconds at the quiet boundaries remove clicks; there is no
    # phrase rearrangement, musical crossfade, normalization or time stretching.
    amount = round(.005 * RATE)
    result[:amount] *= np.linspace(0, 1, amount)[:, None]
    result[-amount:] *= np.linspace(1, 0, amount)[:, None]
    return result, dict(threshold_dbfs=-60, measurement_window_ms=5,
                        last_active_end_frame=last_active_end,
                        safety_tail_ms=25, boundary_declick_ms=5,
                        removed_tail_frames=len(audio) - len(result),
                        removed_tail_seconds=(len(audio) - len(result)) / RATE)


def encode(audio, target, title, *, encoder='libvorbis'):
    target.parent.mkdir(parents=True, exist_ok=True)
    # Keep the destination stable until encoding succeeds.
    handle, temporary = tempfile.mkstemp(prefix=target.stem + '-', suffix='.ogg', dir=target.parent)
    os.close(handle)
    temporary = Path(temporary)
    try:
        command = [
            'ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(RATE), '-ac', '2',
            '-i', 'pipe:0', '-map_metadata', '-1', '-c:a', encoder, '-q:a', '8',
            '-fflags', '+bitexact', '-flags:a', '+bitexact', '-metadata', f'title={title}',
        ]
        if encoder == 'vorbis':command.extend(('-strict', '-2'))
        command.append(str(temporary))
        subprocess.run(command, input=audio.astype('<f4', copy=False).tobytes(), check=True)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def verify_asset(path, expected_frames, *, loop=True):
    stream = probe(path)['streams'][0]
    if (stream['codec_name'], stream['sample_rate'], stream['channels']) != ('vorbis', '48000', 2):
        raise ValueError(f'Unexpected runtime format: {path.name}')
    decoded = decode(path)
    if len(decoded) != expected_frames:
        raise ValueError(f'Decoded frame count changed: {path.name}')
    peak = float(np.max(np.abs(decoded)))
    if peak >= 1:
        raise ValueError(f'Runtime export clips: {path.name}')
    # This verifies this project's actual SDL_mixer codec support. A lossless
    # Opus remux of the uploaded M4A is rejected by the current Pygame build.
    os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
    os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
    import pygame
    pygame.mixer.init(frequency=RATE, size=-16, channels=2)
    try:
        sound = pygame.mixer.Sound(str(path))
        if abs(sound.get_length() - expected_frames / RATE) > 1 / RATE:
            raise ValueError(f'Pygame duration mismatch: {path.name}')
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.play(loops=-1 if loop else 0)
        if not pygame.mixer.music.get_busy():
            raise ValueError(f'Pygame could not stream: {path.name}')
        pygame.mixer.music.pause()
        pygame.mixer.music.unpause()
        pygame.mixer.music.stop()
    finally:
        pygame.mixer.quit()
    rms = float(np.sqrt(np.mean(decoded.astype('float64') ** 2)))
    return dict(codec='vorbis', sample_rate=RATE, channels=2,
                decoded_frames=len(decoded), duration_seconds=len(decoded) / RATE,
                peak_dbfs=20 * math.log10(max(peak, 1e-12)),
                rms_dbfs=20 * math.log10(max(rms, 1e-12)),
                sample_step_across_repeat=float(np.max(np.abs(decoded[-1] - decoded[0]))),
                pygame_full_decode=True, pygame_stream_with_repeat=loop,
                pygame_stream_one_shot=not loop,
                sha256=sha256(path), bytes=path.stat().st_size)


def build(identifiers=None):
    """Rebuild all assigned cues, or replace selected cues without touching others."""
    selected = None if identifiers is None else set(identifiers)
    known = {source['identifier'] for source in SOURCES}
    if selected is not None and (not selected or not selected <= known):
        raise ValueError('Select at least one known music track')
    catalog_path = MUSIC / 'tracks.json'
    audit_path = MUSIC / 'runtime/provenance.json'
    if selected is None:
        tracks, records = {}, []
    else:
        tracks = json.loads(catalog_path.read_text(encoding='utf-8'))['tracks']
        records = json.loads(audit_path.read_text(encoding='utf-8'))['tracks']
    for source in SOURCES:
        if selected is not None and source['identifier'] not in selected:
            continue
        path = MUSIC / source['source']
        original = path.read_bytes()
        if git_blob_sha(original) != source['git_sha']:
            raise ValueError(f'Source differs from the approved upload: {source["source"]}')
        stream = probe(path)['streams'][0]
        audio = decode(path)
        export = audio
        boundaries = dict(removed_tail_frames=0, removed_tail_seconds=0,
                          boundary_declick_ms=0)
        if source['trim_tail']:
            export, boundaries = trimmed_battle(audio)
        elif source.get('boundary_declick_ms'):
            # The leitmotif's first sample is audible while its tail is quiet.
            # Taper only five milliseconds at both ends; preserve every frame,
            # the complete musical phrase and its natural reverb/ending.
            amount = round(source['boundary_declick_ms'] * RATE / 1000)
            export = audio.copy()
            export[:amount] *= np.linspace(0, 1, amount)[:, None]
            export[-amount:] *= np.linspace(1, 0, amount)[:, None]
            boundaries['boundary_declick_ms'] = source['boundary_declick_ms']
        target = MUSIC / 'runtime' / source['target']
        encode(export, target, source['title'], encoder=source.get('encoder', 'libvorbis'))
        loop = source.get('loop', True)
        verified = verify_asset(target, len(export) + source.get('runtime_frame_delta', 0), loop=loop)
        if path.read_bytes() != original:
            raise AssertionError('An original upload changed during export')
        tracks[source['identifier']] = dict(file='runtime/' + source['target'], gain=.45)
        if source['identifier'] == 'opening_leitmotif':
            tracks[source['identifier']]['loop'] = True
        if not loop:
            tracks[source['identifier']]['loop'] = False
        record = dict(identifier=source['identifier'], source=source['source'],
                            source_git_blob_sha=source['git_sha'],
                            source_sha256=hashlib.sha256(original).hexdigest(),
                            source_codec=stream['codec_name'],
                            source_decoded_frames=len(audio),
                            source_decoded_seconds=len(audio) / RATE,
                            loop=loop,
                            runtime='runtime/' + source['target'],
                            runtime_frame_delta=source.get('runtime_frame_delta', 0),
                            boundaries=boundaries, verification=verified)
        existing = next((index for index, item in enumerate(records)
                         if item['identifier'] == source['identifier']), None)
        if existing is None:
            records.append(record)
        else:
            records[existing] = record
    catalog_path.write_text(json.dumps(dict(version=1, tracks=tracks), indent=2) + '\n')
    audit = dict(version=1, source='User-provided uploads', export_codec='Ogg Vorbis',
                 quality=8, musical_rearrangement=False, normalization=False,
                 looping='World/battle/opening repeat the authored cue; victory plays once; no sample-accurate musical-loop claim',
                 tracks=records)
    audit_path.write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--track', action='append', choices=[source['identifier'] for source in SOURCES],
                        help='Rebuild only this cue; repeat to select more than one')
    arguments = parser.parse_args()
    build(arguments.track)
