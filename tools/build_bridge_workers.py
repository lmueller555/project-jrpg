"""Build the authored bridge-crew animations and unchanged shared props."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/characters/bridge_workers'
SOURCE = ROOT/'assets/source/characters/bridge_workers/common'
ROLES = ('mason', 'tender')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metadata():
    return {
        'version': 1,
        'status': 'implemented',
        'canvas': [40, 44],
        'anchor': [20, 38],
        'exporter': 'tools/build_bridge_workers.py',
        'roles': {role: {'manifest': f'{role}/animation.json',
                         'sha256': digest(OUT/role/'animation.json')}
                  for role in ROLES},
        'props': {name: {'file': name+'.png',
                         'source': (SOURCE/(name+'.png')).relative_to(ROOT).as_posix(),
                         'sha256': digest(SOURCE/(name+'.png'))}
                  for name in ('stone', 'cup', 'kettle', 'bench', 'tray', 'tool', 'barrier', 'keep_mark', 'reject_mark')},
        'stone_anchor': [6, 9],
        'registration': 'Per-frame item offsets, palm contacts and depth layers belong to each authored sequence.',
        'appearance': {'mason': 'male_01', 'tender': 'male_03'},
        'body_art': 'Authored full-body frames; approved directional idle/walk art remains read-only.',
    }


def build(check=False):
    for role in ROLES:
        command = [sys.executable, str(ROOT/'tools'/f'build_bridge_{role}.py')]
        if check:command.append('--check')
        subprocess.run(command, cwd=ROOT, check=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ('stone.png', 'cup.png', 'kettle.png', 'bench.png', 'tray.png', 'tool.png', 'barrier.png', 'keep_mark.png', 'reject_mark.png'):
        source, target = SOURCE/name, OUT/name
        if check:
            if not target.exists() or target.read_bytes() != source.read_bytes():
                raise ValueError(f'Changed shared bridge prop: {target.relative_to(ROOT)}')
        elif not target.exists() or target.read_bytes() != source.read_bytes():
            shutil.copyfile(source, target)
    expected = json.dumps(metadata(), indent=2)+'\n'
    path = OUT/'art.json'
    if check:
        if not path.exists() or path.read_text() != expected:
            raise ValueError('Bridge worker registration is stale; run tools/build_bridge_workers.py')
    else:path.write_text(expected)
    print(('Verified' if check else 'Built')+' both authored bridge manifests and unchanged shared bridge props')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    build(args.check)
