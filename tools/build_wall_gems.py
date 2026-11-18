"""Build tiny embedded microcrystals in transparent branching mineral seams.

Individual facets are only one to four native pixels wide. Existing limestone
remains visible between them; a seam is neither one large gem nor a stone slab.
Only facet brightness changes through the six pulse frames.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/limestone_cave/wall_gems.json'
PACK='assets/terrain/limestone_cave/wall_gems'


def png(image):
    result=BytesIO();image.save(result,format='PNG');return result.getvalue()


def tone(color,gain):
    return tuple(max(0,min(255,round(channel*gain))) for channel in color)


def products():
    spec=json.loads(SOURCE.read_text())
    wall_path=ROOT/spec['wall_texture']
    limestone_path=ROOT/spec['limestone_recipe']
    wall=Image.open(wall_path).convert('RGBA')
    output={};modules={}

    def emit(path,value):
        output[path]=(png(value) if isinstance(value,Image.Image) else
                      (json.dumps(value,indent=2)+'\n').encode())

    def module(variant,palette,level):
        image=Image.new('RGBA',tuple(variant['size']))
        draw=ImageDraw.Draw(image)
        # Narrow crevices belong to the rock. Most of the module is transparent
        # so placing a seam does not replace the actual wall beneath it.
        for path in variant['fissures']:
            draw.line([tuple(point) for point in path],fill='#414842',width=1)
        progress=level/(spec['pulse_frames']-1)
        mid=tone(palette['mid'],.62+.38*progress)
        bright=tone(palette['bright'],.66+.34*progress)
        deep=tone(palette['deep'],.82+.18*progress)
        glint=tone(palette['glint'],.74+.26*progress)
        for ordinal,(x,y,w,h) in enumerate(variant['crystals']):
            if w==1:
                draw.line((x,y,x,y+h-1),fill=mid)
                draw.point((x,y),fill=bright)
            else:
                # At this scale a lit edge, middle facet and shaded foot are
                # sufficient. Larger surrounding outlines would inflate them.
                draw.rectangle((x,y,x+w-1,y+h-1),fill=mid)
                draw.line((x,y,x+w-1,y),fill=bright)
                draw.line((x+w-1,y+1,x+w-1,y+h-1),fill=deep)
                if ordinal%3==0:draw.point((x,y),fill=glint)
            # Tiny fixed limestone lips interrupt a grain edge without making
            # a ring or joining adjacent colored grains into a large crystal.
            if w>1 and h>2 and ordinal%3==1:
                draw.point((x,y+h-1),fill='#85877a')
            if ordinal%2==0:draw.point((x-1,y+1),fill='#72786e')
        return image

    for name,palette in spec['colors'].items():
        for index,variant in enumerate(spec['variants']):
            rects=variant['crystals'];limits=spec['grain_limits']
            if not all(1<=w<=limits['max_width'] and 1<=h<=limits['max_height']
                       for x,y,w,h in rects):
                raise ValueError('Microcrystal exceeds its native scale limit')
            for ordinal,(x,y,w,h) in enumerate(rects):
                for ox,oy,ow,oh in rects[ordinal+1:]:
                    if not(x+w<ox or ox+ow<x or y+h<oy or oy+oh<y):
                        raise ValueError('Microcrystal facets must remain separated')
            frames=[]
            for level in range(spec['pulse_frames']):
                path=f'{PACK}/{name}/variant_{index}/frame_{level:02}.png'
                emit(path,module(variant,palette,level));frames.append(path)
            left=min(r[0] for r in rects);top=min(r[1] for r in rects)
            right=max(r[0]+r[2] for r in rects);bottom=max(r[1]+r[3] for r in rects)
            modules[f'wall_gem.{name}.{index}']={
                'frames':frames,'size':variant['size'],'anchor':variant['anchor'],
                'color':palette['light'],'gem_color':name,'label':palette['label'],
                'emission_bounds':[left,top,right-left,bottom-top],
                'core_components':rects,'crystal_sizes':[[r[2],r[3]] for r in rects],
                'crystal_count':len(rects),'footprints':[],
                'mount':'embedded_wall','representation':spec['representation'],
                'pulse_frames':spec['pulse_frames']}

    # Every seam and Caelan is enlarged exactly three times. No grain is
    # presented as a huge isolated decorative gem or given a separate scale.
    board=Image.new('RGB',(1560,570),'#26322f');draw=ImageDraw.Draw(board)
    title=ImageFont.load_default(size=20);small=ImageFont.load_default(size=16)
    draw.text((20,14),'WALL MICROCRYSTALS / native 1-4 px facets / all art enlarged 3x',
              fill='#e9e1ce',font=title)
    for col,(name,palette) in enumerate(spec['colors'].items()):
        x=20+col*256
        draw.text((x,52),palette['label'],fill='#ece5d3',font=title)
        for row,variant in enumerate(spec['variants']):
            seam=module(variant,palette,5)
            panel=Image.new('RGBA',tuple(variant['size']))
            for yy in range(panel.height):
                for xx in range(panel.width):
                    pixel=wall.getpixel(((xx+row*13)%wall.width,(yy+22)%wall.height))
                    panel.putpixel((xx,yy),pixel if pixel[3] else (137,139,122,255))
            panel.alpha_composite(seam)
            scaled=panel.resize((panel.width*3,panel.height*3),Image.Resampling.NEAREST)
            board.paste(scaled,(x,87+row*108))
    ca_path=ROOT/'assets/source/characters/caelan/overworld_refresh/legacy/idle_front.png'
    ca=Image.open(ca_path).convert('RGBA')
    ca=ca.resize((ca.width*3,ca.height*3),Image.Resampling.NEAREST)
    board.paste(ca,(1430,420),ca)
    draw.text((20,432),'Many tiny facets follow broken mineral seams, with bare limestone between them.',
              fill='#d0d8cd',font=small)
    draw.text((20,460),'Individual crystals: mostly 2 x 3 native pixels; largest 4 x 5 pixels.',
              fill='#d0d8cd',font=small)
    draw.text((20,488),'24 / 28 / 32 crystals per seam; fixed grain geometry through the pulse.',
              fill='#d0d8cd',font=small)
    draw.text((1320,540),'Caelan / same scale',fill='#e9e1ce',font=small)
    emit(f'{PACK}/colors_review.png',board)
    output[f'{PACK}/README.md']=(
        '# Embedded wall microcrystals\n\n'
        'Status: pending visual review; not merged into the live game.\n\n'
        'Red, Blue, Green, White, Orange and Purple microcrystals follow\n'
        'irregular branching seams in limestone. The transparent modules leave\n'
        'the existing rock visible between separated mineral grains. There are\n'
        'no large gemstones, bezels, standing shards or floor footprints.\n\n'
        'Every color has three fields containing 24, 28 or 32 tiny facets.\n'
        'Individual grains measure 1-4 by 1-5 native pixels, mostly 2 by 3.\n'
        '`core_components`, `crystal_sizes` and `crystal_count` record this\n'
        'scale. `emission_bounds` encloses the complete field, while each\n'
        'component records one separated grain. Anchors identify field centers.\n\n'
        'Six frames vary brightness only. Neutral hairline crevices and small\n'
        'rock lips stay fixed. The production six-second pulse controls the\n'
        'facets and the colored illumination on nearby stone and floor.\n\n'
        'Rebuild with `python tools/build_wall_gems.py`; append `--check` for\n'
        'deterministic validation. The source recipe is\n'
        '`assets/source/terrain/limestone_cave/wall_gems.json`.\n'
    ).encode()
    inputs={str(path.relative_to(ROOT)):sha256(path.read_bytes()).hexdigest()
            for path in (SOURCE,wall_path,limestone_path,ca_path)}
    manifest={'version':2,'id':spec['id'],'approval_status':spec['approval_status'],
              'tile_size':24,'representation':spec['representation'],
              'grain_limits':spec['grain_limits'],'pulse_frames':spec['pulse_frames'],
              'colors':spec['colors'],'source_recipe':str(SOURCE.relative_to(ROOT)),
              'modules':modules,'inputs':inputs,
              'artifacts':{path:sha256(raw).hexdigest() for path,raw in output.items()}}
    emit(f'{PACK}/assets.json',manifest)
    return output


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true');args=parser.parse_args(argv)
    output=products();changed=[]
    for relative,raw in output.items():
        path=ROOT/relative
        if not path.exists() or path.read_bytes()!=raw:
            changed.append(relative)
            if not args.check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    if args.check and changed:raise SystemExit('Stale wall microcrystal exports: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' {len(output)} wall microcrystal exports')
    return 0


if __name__=='__main__':raise SystemExit(main())
