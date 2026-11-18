"""Sample approved full-body guard source at native 2x, never enlarge legacy PNGs."""
import argparse
import json
from pathlib import Path
import build_road_guards as author
ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'assets/characters/road_guards_hd'
def build_outputs():
    old=(author.TARGET,author.CANVAS,author.ANCHOR,author.PORTRAIT)
    try:
        author.TARGET=TARGET;author.CANVAS=(80,88);author.ANCHOR=(40,76)
        author.PORTRAIT=TARGET/'portrait.png'
        outputs,_=author.build_outputs()
    finally:author.TARGET,author.CANVAS,author.ANCHOR,author.PORTRAIT=old
    review=outputs.pop(author.SOURCE/'native_review.png')
    outputs[TARGET/'review.png']=review
    meta=json.loads(outputs[TARGET/'animation.json'])
    meta.update(artwork_pixels_per_world_pixel=2,logical_size=[40,44],draw_anchor=[20,38],artwork_draw_anchor=[40,76])
    outputs[TARGET/'animation.json']=author.json_bytes(meta)
    # Keep exact approved portrait rather than produce any reinterpretation.
    outputs[TARGET/'portrait.png']=(ROOT/'assets/portraits/eldenmere/road_guard_neutral.png').read_bytes()
    provenance=json.loads(outputs.pop(TARGET/'provenance.json'))
    provenance['exporter']='tools/build_road_guards_hd.py'
    provenance['exports']={p.relative_to(ROOT).as_posix():author.sha(data) for p,data in outputs.items()}
    outputs[TARGET/'provenance.json']=author.json_bytes(provenance)
    return outputs
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    for path,data in build_outputs().items():
        if args.check:
            if not path.exists() or path.read_bytes()!=data:raise SystemExit('Different export: '+str(path))
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
