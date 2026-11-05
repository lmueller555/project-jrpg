"""Encode the approved heavy pressure release with its reviewed camera recession.

Requires NumPy and FFmpeg. The lossless editing master already contains the
approved listening level; compensate for the runtime cue gain before encoding.
"""
from pathlib import Path
import hashlib
import json
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'assets/audio/sfx/ice_reaper_breakout'
RATE = 48000
GAIN = .58


def main():
    master = TARGET / 'pressure_release_master.wav'
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(master),
                                   '-ar', str(RATE), '-ac', '2', '-f', 'f32le', '-'])
    samples = np.frombuffer(raw, dtype='<f4').reshape(-1, 2).astype(np.float64)
    # Identical envelope to the approved B scene audition: leave the rupture
    # intact, then lose 6dB as the camera retreats (0.32–0.97s into the file).
    amount = np.clip((np.arange(len(samples))/RATE - .2 - .12)/.65, 0, 1)
    amount = amount*amount*(3-2*amount)
    samples *= (1-.5*amount)[:, None] / GAIN
    assert np.isfinite(samples).all() and np.abs(samples).max() < 1
    output = TARGET / 'pressure_release.ogg'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(RATE),
                    '-ac', '2', '-i', '-', '-map_metadata', '-1', '-c:a', 'libvorbis',
                    '-q:a', '7', str(output)], input=samples.astype('<f4').tobytes(), check=True)
    manifest = dict(description='Approved Ice B — Heavy pressure release',
                    master=master.relative_to(ROOT).as_posix(),
                    master_sha256=hashlib.sha256(master.read_bytes()).hexdigest(),
                    file=output.relative_to(ROOT).as_posix(),
                    sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                    rate=RATE, channels=2, duration=len(samples)/RATE,
                    cue_time=17.1, rupture_offset=.2, rupture_scene_time=17.3,
                    runtime_gain=GAIN, recession_db=-6.0206,
                    license='CC0-1.0', source_author='Anthousai',
                    source_urls=['https://freesound.org/people/Anthousai/sounds/406217/',
                                 'https://freesound.org/people/Anthousai/sounds/406218/'])
    (TARGET/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    main()
