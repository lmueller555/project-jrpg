"""Make the scoped65ms mechanical cue compatible with default battle mixers."""
import hashlib
import json
from pathlib import Path
import subprocess
import wave

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/audio/sfx/ice_reaper_rescue/source/fps_weapon_change.ogg'
OUTPUT=ROOT/'assets/audio/sfx/mira/bolt_clack.wav'


def build():
    # SDL_mixer can decode this96kHz source as zero frames at44100/48000.
    # Resample this cue only; no mixer, source, or other skill is changed.
    pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(SOURCE),'-t','0.065',
        '-ar','44100','-ac','2','-f','s16le','-'])
    if not pcm or not any(pcm):raise ValueError('Empty Mira clack')
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(OUTPUT),'wb') as output:
        output.setparams((2,2,44100,0,'NONE','not compressed'));output.writeframes(pcm)
    metadata=dict(source=SOURCE.relative_to(ROOT).as_posix(),
        source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        file=OUTPUT.name,sha256=hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        duration_seconds=.065,sample_rate=44100,channels=2,format='PCM signed16LE',
        license='MIT; Kenney Starter Kit FPS, retained source/fps_LICENSE.md',
        license_file='assets/audio/sfx/ice_reaper_rescue/source/fps_LICENSE.md',
        processing='First65ms, ffmpeg resampling to44100; runtime applies its existing short fade and cue gain')
    OUTPUT.with_suffix('.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return metadata


if __name__=='__main__':print(json.dumps(build()))
