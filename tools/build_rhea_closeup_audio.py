"""Build the restrained ice-pressure cue from retained licensed rescue audio.

Offline; requires ffmpeg. This does not rebuild or retime any music or the
existing rescue sound files.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ice_reaper_audio import CUES

SOURCE = ROOT/'assets/audio/sfx/ice_reaper_rescue/prison_crack.ogg'
TARGET = ROOT/'assets/audio/sfx/ice_reaper_rhea_closeup'
# Lower the recorded/designed crack by seven semitones and soften its attack.
# The final cinematic gain is deliberately low; this is pressure in the glass.
FILTER = 'asetrate=32000,aresample=48000,highpass=f=95,lowpass=f=2200,afade=t=in:d=0.12,afade=t=out:st=0.94:d=0.29,volume=0.72'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    TARGET.mkdir(parents=True, exist_ok=True)
    output = TARGET/'ice_creak.ogg'
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(SOURCE),'-map_metadata','-1',
                    '-af',FILTER,'-ar','48000','-ac','2','-c:a','libvorbis','-q:a','6',str(output)],check=True)
    probe = json.loads(subprocess.check_output(['ffprobe','-v','error',
        '-show_entries','format=duration','-of','json',str(output)]))
    manifest = dict(version=1, description='Quiet ice-pressure creak during Rhea’s closed-eye hold',
        source=dict(file=SOURCE.relative_to(ROOT).as_posix(),sha256=digest(SOURCE),
                    license='MIT-derived Kenney sources; see ../ice_reaper_rescue/source/*_LICENSE.md'),
        derivation=dict(tool='ffmpeg',filter=FILTER,music_changed=False),
        sound=dict(file=output.relative_to(ROOT).as_posix(),sha256=digest(output),
                   duration=float(probe['format']['duration']),rate=48000,channels=2),
        cue=next(dict(cue) for cue in CUES if cue['id']=='ice_creak'))
    (TARGET/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Keep the central runtime cue ledger accurate without changing its audio.
    ledger = ROOT/'assets/audio/sfx/ice_reaper_rescue/manifest.json'
    data = json.loads(ledger.read_text())
    data['cues'] = [cue for cue in CUES if cue['time'] < 21]
    ledger.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(file=output.relative_to(ROOT).as_posix(),duration=manifest['sound']['duration'],cues=len(CUES))))


if __name__=='__main__':
    build()
