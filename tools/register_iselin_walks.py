"""Register approved walk manifests without changing any authored pixels."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='assets/characters/iselin'
ACTOR_SCOPE='Four directional idles and 16-frame walks at ordinary world scale; cinematic poses remain separate.'


def walk_references():
    return {direction:{'manifest':f'{BASE}/walk_{direction}/animation.json'}
            for direction in ('front','left','right','back')}


def products():
    animation=json.loads((ROOT/BASE/'animation.json').read_text())
    actor=json.loads((ROOT/BASE/'actor.json').read_text())
    animation['walks']=walk_references();actor['scope']=ACTOR_SCOPE
    return {f'{BASE}/animation.json':animation,f'{BASE}/actor.json':actor}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    for path,record in products().items():
        destination=ROOT/path;data=json.dumps(record,indent=2)+'\n'
        if args.check:
            if destination.read_text()!=data:raise SystemExit('Stale walk registration: '+path)
        else:destination.write_text(data)
    print('Verified Iselin walk registration.' if args.check else 'Registered four Iselin walks.')


if __name__=='__main__':main()
