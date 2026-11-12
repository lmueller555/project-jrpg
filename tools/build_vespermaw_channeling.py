"""Register a complete-anatomy channeling performance from retained drawings.

This sequence deliberately lowers the body, braces, rises into a roar, and
settles. It preserves every selected drawing's anatomical floor; no limb or
whole-body warping manufactures a pose. Runtime material and elemental layers
add a new travelling crystal/fur response independently of this body acting.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/combat/vespermaw/channeling'


def products():
    bank_path = ROOT/'assets/combat/vespermaw/animation.json'
    bank = json.loads(bank_path.read_text())
    # Each arc is chronological within its retained complete-body performance.
    # Reverse anticipation is the authored recovery, not a jump between poses.
    arcs = [('brace', 'gather_resonance', 0, 31, 24, 850),
            ('rise', 'gather_resonance', 31, 0, 18, 550),
            ('release', 'confluence_roar', 0, 23, 22, 800),
            ('settle', 'confluence_roar', 24, 31, 8, 300)]
    output = {}; frames = []; elapsed = 0
    for phase, state, first, last, count, total in arcs:
        for index in range(count):
            source_index = round(first+(last-first)*index/(count-1))
            record = bank['animations'][state]['frames'][source_index]
            source = ROOT/'assets/combat/vespermaw'/record['file']
            image = Image.open(source).convert('RGBA')
            stream = BytesIO(); image.save(stream, format='PNG', optimize=True)
            path = OUT/f'body_{len(frames):02}.png'
            output[path] = stream.getvalue()
            duration = round((index+1)*total/count)-round(index*total/count)
            # Crystal tips follow the opaque top of this actual pose. They are
            # registered inside the ridge, so highlights never drift off fur.
            tips=[]
            for x in range(39, 101, 9):
                ys=[y for y in range(25, 100) if image.getpixel((x,y))[3]]
                if ys:tips.append([x, min(ys)+3])
            frames.append({'file': path.relative_to(ROOT).as_posix(),
                           'duration_ms': duration, 'start_ms': elapsed,
                           'phase': phase, 'body_state': state,
                           'body_frame': source_index,
                           'source_sha256': sha256(source.read_bytes()).hexdigest(),
                           'anchors': {**record['anchors'], 'spine': tips[len(tips)//2]},
                           'crystal_tips': tips})
            elapsed += duration
    manifest={'version':1, 'canvas':bank['canvas'], 'anchor':bank['anchor'],
              'duration_ms':2500, 'commit_ms':1650, 'frames':frames,
              'body_bank':'assets/combat/vespermaw/animation.json',
              'body_bank_sha256':sha256(bank_path.read_bytes()).hexdigest(),
              'performance':'brace and crouch, deliberate rise, open-jaw release, settling breath',
              'materials':['fire','ice','water'],
              'new_independent_body_drawings':False,
              'layering':'complete registered body; fur palette and travelling material reveal; ridge/eye highlights; distinct elemental motes'}
    output[OUT/'performance.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true')
    check=parser.parse_args().check
    for path,data in products().items():
        if check:
            if not path.exists() or path.read_bytes()!=data:raise SystemExit('Stale channel performance: '+str(path))
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
