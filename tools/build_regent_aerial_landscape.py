"""Register authored aerial plates against Elden Vale's real geography.

Only bounded source crops/composition and nearest resizing are used. Original
imagegen artwork, geographic guide and exact prompts remain in source control.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/regent_aerial/landscape'
TARGET = ROOT/'assets/story/regent_aerial/landscape'
REGION_BOUNDS = [-177, -112, 354, 236]
GATE_BOUNDS = [7.4193548387, 84.2580645161, 39.6387096774, 26.4258064516]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n')


def opaque_rectangle(image):
    """Largest wholly opaque native rectangle, not a silhouette bounding box."""
    alpha=image.getchannel('A');width,height=alpha.size;pixels=alpha.load()
    histogram=[0]*width;best_area=0;best=None
    for y in range(height):
        for x in range(width):
            histogram[x]=histogram[x]+1 if pixels[x,y]==255 else 0
        stack=[]
        for x in range(width+1):
            current=histogram[x] if x<width else 0;start=x
            while stack and stack[-1][1]>current:
                previous,value=stack.pop();area=(x-previous)*value
                if area>best_area:
                    best_area=area;best=[previous,y-value+1,x-previous,value]
                start=previous
            if not stack or stack[-1][1]<current:
                stack.append((start,current))
    if best is None:
        raise ValueError('Foreground canopy has no opaque coverage')
    return best


def export(target):
    target.mkdir(parents=True, exist_ok=True)
    original = {str(p.relative_to(SOURCE)):digest(p) for p in SOURCE.rglob('*') if p.is_file()}
    region = Image.open(SOURCE/'region_generated.png').convert('RGB')
    if region.size != (1536,1024):
        raise ValueError('Aerial region must retain its authored 1536x1024 registration')
    # The only region revision restores the blue water beneath four short wall
    # stubs. Bounded copies preserve every other approved geography pixel.
    banks = Image.open(SOURCE/'region_banks_generated.png').convert('RGB')
    patches = [(224,55,256,83), (1278,54,1314,84),
               (224,890,250,919), (1284,890,1315,921)]
    for bounds in patches:
        region.paste(banks.crop(bounds), bounds[:2])
    region.save(target/'region.png', optimize=True)
    gate = Image.open(SOURCE/'gate_oblique_generated.png').convert('RGB')
    if gate.size != (1536,1024):
        raise ValueError('Aerial gate must retain its authored canvas')
    # Only the source's thin baked bar is replaced with an authored open-road
    # crop. Gate leaves and actors belong to the cinematic renderer.
    gate_open = Image.open(SOURCE/'gate_open_generated.png').convert('RGB')
    bar_patch = (736,418,857,438)
    gate.paste(gate_open.crop(bar_patch),bar_patch[:2])
    gate.save(target/'gate_oblique.png', optimize=True)
    # The true orthographic source shows roof and post tops without facades.
    overhead_source = SOURCE/'gate_overhead_generated.png'
    overhead = Image.open(overhead_source).convert('RGB')
    if overhead.size != (1536,1024):
        raise ValueError('The overhead gate must retain its authored canvas')
    overhead.save(target/'gate_overhead.png', optimize=True)
    # The authored foreground uses a soft source alpha. Snap only its alpha,
    # preserving its painted RGB and naturally irregular leaf silhouette.
    canopy=Image.open(SOURCE/'foreground_canopy_generated.png').convert('RGBA')
    canopy.putalpha(canopy.getchannel('A').point(lambda value:255 if value>=128 else 0))
    canopy=canopy.resize((960,640),Image.Resampling.NEAREST)
    coverage=opaque_rectangle(canopy)
    if coverage[2]*2<480 or coverage[3]*2<320:
        raise ValueError('Foreground canopy cannot fully cover the native viewport at 2x')
    if canopy.getchannel('A').getextrema()!=(0,255):
        raise ValueError('Foreground canopy must have opaque leaves and transparent edges')
    canopy.save(target/'foreground_canopy.png',optimize=True)
    manifest = {
        'version':1,
        'region':{'file':'region.png','bounds_tiles':REGION_BOUNDS,
                  'anchors':{'eldenmere':[820,367],'upper_millrace':[804,205],
                             'west_broken_bridge':[281,613],'north_gate':[855,68],
                             'south_gate':[891,903]}},
        'gate_overhead':{'file':'gate_overhead.png',
                         'bounds_tiles':[-2,76,60,40],
                         'anchors':{'west_post':[718,514],'east_post':[819,513],
                                    'aperture':[768.5,513.5],
                                    'hut_peak':[602,460],
                                    'road_aldric':[793.6,716.8],'road_caravan':[870.4,755.2]}},
        'gate_oblique':{'file':'gate_oblique.png','bounds_tiles':GATE_BOUNDS,
                        'anchors':{'west_post':[720,455],'east_post':[875,455],
                                   'aperture':[797.5,455],'hut_peak':[610,350],
                                   'road_aldric':[836.25,765],'road_caravan':[952.5,823.125]}},
        'foreground_canopy':{'file':'foreground_canopy.png','canvas':[960,640],
                             'coverage_rect':coverage,'coverage_rect_format':'xywh',
                             'alpha_threshold':128,'suggested_near_scale':2},
        'geography':{'source':'assets/maps/overworld/elden_vale/region.json',
                     'source_sha256':digest(ROOT/'assets/maps/overworld/elden_vale/region.json'),
                     'orientation':'north up; x east, y south',
                     'region_wall_water_patch_rects':patches,
                     'gate_open_road_patch_rect':bar_patch,
                     'west_bridge':'broken; no other boundary-river crossing'}
    }
    write_json(target/'manifest.json',manifest)
    write_json(target/'provenance.json',{
        'version':1,'exporter':'tools/build_regent_aerial_landscape.py',
        'exporter_sha256':digest(Path(__file__)), 'source_sha256':original,
        'exports':{p.name:digest(p) for p in sorted(target.glob('*.png'))},
        'manifest_sha256':digest(target/'manifest.json'),
        'operations':['bounded authored-source crops/composition',
                      'binary canopy alpha cleanup and nearest 960x640 registration','PNG export'],
    })
    if original != {str(p.relative_to(SOURCE)):digest(p) for p in SOURCE.rglob('*') if p.is_file()}:
        raise AssertionError('Original aerial sources changed during export')
    return sorted(p.name for p in target.iterdir())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory(prefix='regent-aerial-landscape-') as temporary:
            out=Path(temporary);names=export(out)
            for name in names:
                if not (TARGET/name).exists() or (TARGET/name).read_bytes() != (out/name).read_bytes():
                    raise SystemExit('Aerial landscape export differs: '+name)
            if sorted(p.name for p in TARGET.iterdir()) != names:
                raise SystemExit('Unexpected aerial landscape exports')
        print('Verified three registered aerial landscape plates, opaque foreground canopy and provenance')
    else:
        export(TARGET)
        print('Exported three registered aerial landscape plates and foreground canopy')


if __name__=='__main__':
    main()
