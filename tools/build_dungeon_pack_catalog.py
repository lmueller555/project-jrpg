"""Inventory every dungeon module in lossless, native-scale review boards.

The catalog reads the existing limestone pack and four independent additions.
It never rewrites an input. Every floor variation and named module receives a
labelled cell; animated pages have matching GIFs, and a lossless PDF retains
all pages without reducing the pixel art to a contact-sheet thumbnail.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import zlib
import zipfile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/limestone_cave/catalog.json'
OUT = 'assets/terrain/limestone_cave/catalog'
CAELAN = 'assets/characters/caelan/idle_front.png'
BG = '#222f2b'
PAPER = '#ede4cf'
MUTED = '#b5c4b7'


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False)+'\n').encode()


def png(image):
    stream = BytesIO();image.save(stream, format='PNG');return stream.getvalue()


def lossless_pdf(images):
    """A deterministic PDF whose RGB page images use lossless Flate streams."""
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'']
    kids = []
    for image in images:
        image = image.convert('RGB');w,h = image.size
        page_id = len(objects)+1;content_id = page_id+1;image_id = page_id+2
        kids.append(f'{page_id} 0 R')
        objects.append((f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w/2:g} {h/2:g}] '
                        f'/Resources << /XObject << /Im0 {image_id} 0 R >> >> '
                        f'/Contents {content_id} 0 R >>').encode())
        stream = f'q {w/2:g} 0 0 {h/2:g} 0 0 cm /Im0 Do Q'.encode()
        objects.append(f'<< /Length {len(stream)} >>\nstream\n'.encode()+stream+b'\nendstream')
        raw = zlib.compress(image.tobytes(), 9)
        objects.append((f'<< /Type /XObject /Subtype /Image /Width {w} /Height {h} '
                        f'/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode '
                        f'/Length {len(raw)} >>\nstream\n').encode()+raw+b'\nendstream')
    objects[1] = f'<< /Type /Pages /Count {len(kids)} /Kids [{" ".join(kids)}] >>'.encode()
    result = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n');offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(result));result.extend(f'{index} 0 obj\n'.encode()+obj+b'\nendobj\n')
    xref = len(result);result.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:result.extend(f'{offset:010d} 00000 n \n'.encode())
    result.extend((f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n').encode())
    return bytes(result)


def category(source, name, kind):
    if kind == 'floor':return 'floors'
    first = name.split('.')[0]
    if source == 'base':
        return {'wall':'walls', 'formation':'formations', 'tunnel':'formations',
                'patch':'ground_details', 'socket':'ground_details',
                'shoreline':'ground_details', 'transition':'transitions'}.get(first, first)
    if source == 'structure':
        return 'walls' if first == 'wall' else 'passages' if first in ('tunnel','alcove') else 'ledges_and_routes'
    if source == 'water':
        return 'pool_materials' if first == 'water' else 'banks' if first in ('bank','crust') else 'streams' if first == 'stream' else 'seepage_and_ripples'
    if source == 'geology':
        return 'entrance' if first in ('entrance','transition') else 'loose_geology'
    if source == 'micro_adapters':
        return 'corner_seams' if 'corner' in name else 'density_patterns' if name.endswith(('.sparse','.dense')) else 'directional_seams'
    return 'colored_seams'


def products():
    spec = json.loads(SOURCE.read_text());scale = spec['scale'];width = spec['page_width']
    used = {SOURCE, ROOT/CAELAN};outputs = {};entries = {};groups = defaultdict(list)
    images = {};archive_paths = set()
    def opened(path):
        used.add(ROOT/path)
        if path not in images:
            with Image.open(ROOT/path) as image:images[path] = image.convert('RGBA')
        return images[path]
    def add(source, name, record, kind):
        frames = record['frames'];image = opened(frames[0])
        size = list(record.get('size', image.size))
        if list(image.size) != size:raise ValueError('Wrong catalog dimensions: '+name)
        for path in frames:
            if opened(path).size != tuple(size):raise ValueError('Animation changes canvas: '+name)
        key = source+':'+name;group = category(source, name, kind)
        entries[key] = {'id':key, 'source':source, 'module':name, 'kind':kind,
                        'category':group, 'status':spec['sources'][source]['status'],
                        'frames':frames, 'size':size,
                        'anchor':record.get('anchor',[size[0]//2,size[1]-1]),
                        'footprints':record.get('footprints',[]),
                        'frame_duration_ms':record.get('frame_duration_ms',700),
                        'reduced_motion_frame':record.get('reduced_motion_frame',0)}
        groups[(source,group)].append(key)
    for source,record in spec['sources'].items():
        file = ROOT/record['manifest'];used.add(file);data = json.loads(file.read_text())
        archive_paths.add(record['manifest'])
        def auxiliary(value):
            if isinstance(value,dict):
                for item in value.values():auxiliary(item)
            elif isinstance(value,list):
                for item in value:auxiliary(item)
            elif isinstance(value,str) and value.startswith('assets/') and (ROOT/value).is_file():
                archive_paths.add(value);used.add(ROOT/value)
        auxiliary(data['modules'])
        for name,material in data.get('materials',{}).items():
            for index,path in enumerate(material.get('tiles',[])):
                add(source,f'floor.{name}.{index:02}',{'frames':[path],'anchor':[0,0]},'floor')
                archive_paths.add(path)
        for name,module in data['modules'].items():add(source,name,module,'module')
    font = ImageFont.load_default(size=23);label_font = ImageFont.load_default(size=15)
    small = ImageFont.load_default(size=14);title_font = ImageFont.load_default(size=28)
    hero = opened(CAELAN);hero = hero.resize((hero.width*scale,hero.height*scale),Image.Resampling.NEAREST)
    pages = [];page_images = []
    for (source,group),keys in groups.items():
        maxw = max(entries[key]['size'][0]*scale for key in keys)
        maxh = max(entries[key]['size'][1]*scale for key in keys)
        columns = min(8,max(1,(width-40)//max(160,maxw+34)))
        cellw = (width-40)//columns;cellh = max(112,maxh+75);capacity = columns*4
        for chunk_start in range(0,len(keys),capacity):
            subset = keys[chunk_start:chunk_start+capacity]
            number = len(pages)+1;rows = math.ceil(len(subset)/columns)
            height = 112+rows*cellh+48
            path = f'{OUT}/page_{number:02}_{source}_{group}.png'
            for index,key in enumerate(subset):
                entries[key]['page'] = path
                entries[key]['cell'] = [20+(index%columns)*cellw,112+(index//columns)*cellh,cellw,cellh]
            def draw_page(phase=0):
                board = Image.new('RGB',(width,height),BG);draw = ImageDraw.Draw(board)
                draw.text((20,15),spec['sources'][source]['label']+' / '+group.replace('_',' '),font=title_font,fill=PAPER)
                status = 'EXISTING PACK' if spec['sources'][source]['status']=='existing' else 'NEW ADDITIONS / pending review'
                draw.text((20,55),f'{status}   |   every sprite enlarged exactly {scale}x   |   page {number}',font=small,fill=MUTED)
                board.paste(hero,(width-90,17),hero)
                for key in subset:
                    entry = entries[key];x,y,cw,ch = entry['cell'];name = entry['module']
                    # Long module IDs wrap to two lines without shrinking art.
                    parts = name.replace('_',' ').split('.')
                    line = '';lines = []
                    for word in parts:
                        candidate = line+' / '+word if line else word
                        if draw.textlength(candidate,font=label_font)>cw-16 and line:
                            lines.append(line);line=word
                        else:line=candidate
                    lines.append(line)
                    for i,line in enumerate(lines[:2]):draw.text((x+6,y+i*18),line,font=label_font,fill=PAPER)
                    frames = entry['frames'];index = phase%len(frames)
                    if source in ('wall_micro','micro_adapters') and len(frames)>1:
                        breath = (0,1,2,3,4,5,4,3,2,1);index = breath[phase%len(breath)]%len(frames)
                    art = opened(frames[index]);art = art.resize((art.width*scale,art.height*scale),Image.Resampling.NEAREST)
                    left = x+(cw-art.width)//2;top = y+42+(maxh-art.height)//2
                    for yy in range(top,top+art.height,16):
                        for xx in range(left,left+art.width,16):
                            tone = '#2c3b34' if ((xx-left)//16+(yy-top)//16)%2 else '#34423b'
                            draw.rectangle((xx,yy,min(left+art.width-1,xx+15),min(top+art.height-1,yy+15)),fill=tone)
                    board.paste(art,(left,top),art)
                    text = f'{entry["size"][0]} x {entry["size"][1]} px'
                    if len(frames)>1:text+=f' / {len(frames)} frames'
                    draw.text((x+6,y+ch-23),text,font=small,fill=MUTED)
                draw.text((20,height-31),'Native pixel art / Caelan uses the same enlargement / every variation is indexed in catalog.json',font=small,fill=MUTED)
                return board
            board = draw_page();outputs[path] = png(board);page_images.append(board)
            page = {'image':path,'keys':subset,'source':source,'category':group,
                    'label':spec['sources'][source]['label']+' / '+group.replace('_',' '),
                    'scale':scale}
            if any(len(entries[key]['frames'])>1 for key in subset):
                count = 10 if source in ('wall_micro','micro_adapters') else max(len(entries[key]['frames']) for key in subset)
                frames = [draw_page(i) for i in range(count)]
                duration = 600 if count==10 else min(entries[key]['frame_duration_ms'] for key in subset if len(entries[key]['frames'])>1)
                stream = BytesIO();frames[0].save(stream,format='GIF',save_all=True,append_images=frames[1:],duration=duration,loop=0,optimize=True)
                animated = path.removesuffix('.png')+'.gif';outputs[animated] = stream.getvalue();page['animation'] = animated
            pages.append(page)
    overview = Image.new('RGB',(1440,92+math.ceil(len(pages)/4)*286),BG);draw = ImageDraw.Draw(overview)
    draw.text((20,16),'Complete dungeon pack / catalog index',font=title_font,fill=PAPER)
    draw.text((20,54),'Every floor variation and module appears at readable 2x scale in the linked pages and lossless PDF.',font=small,fill=MUTED)
    for index,(page,board) in enumerate(zip(pages,page_images)):
        x = 12+index%4*358;y = 92+index//4*286
        thumbnail = board.copy();thumbnail.thumbnail((342,240),Image.Resampling.NEAREST)
        overview.paste(thumbnail,(x,y))
        draw.text((x+4,y+244),f'{index+1:02}  '+page['source']+' / '+page['category'].replace('_',' '),font=small,fill=PAPER)
    outputs[f'{OUT}/overview.png'] = png(overview)
    outputs[f'{OUT}/full_catalog.pdf'] = lossless_pdf(page_images)
    archive = BytesIO()
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as package:
        for name in sorted(archive_paths):
            info = zipfile.ZipInfo(name,date_time=(2020,1,1,0,0,0))
            info.create_system=3;info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            package.writestr(info,(ROOT/name).read_bytes())
    outputs[f'{OUT}/native_assets.zip'] = archive.getvalue()
    summary = {'entries':len(entries),'floor_variations':sum(e['kind']=='floor' for e in entries.values()),
               'modules':sum(e['kind']=='module' for e in entries.values()),
               'animated_modules':sum(len(e['frames'])>1 for e in entries.values()),
               'pages':len(pages),'by_source':dict(Counter(e['source'] for e in entries.values())),
               'new_entries':sum(e['status']=='new' for e in entries.values())}
    lines = ['# Complete dungeon asset pack catalog','',
             'The catalog includes the existing pack and proposed additions. Additions remain unmerged pending review.','',
             '[Full lossless PDF](full_catalog.pdf) · [Native asset archive](native_assets.zip) · [Catalog overview](overview.png)','',
             f'{summary["entries"]} entries; {summary["floor_variations"]} floor variations; {summary["modules"]} modules; {summary["animated_modules"]} animated modules.','',
             'Every floor variation and module has one labelled cell at 2× nearest-pixel enlargement. Caelan uses the same scale. The PDF preserves the pixels losslessly.','',
             '| Page | Category | Assets | Animation |','| --- | --- | ---: | --- |']
    for i,page in enumerate(pages,1):
        im = Path(page['image']).name;anim = f'[GIF]({Path(page["animation"]).name})' if 'animation' in page else '—'
        lines.append(f'| [{i:02}]({im}) | {page["label"]} | {len(page["keys"])} | {anim} |')
    lines+=['','Rebuild with `python tools/build_dungeon_pack_catalog.py`; append `--check` for read-only fingerprint verification.','']
    outputs[f'{OUT}/README.md'] = '\n'.join(lines).encode()
    catalog = {'version':1,'approval_status':spec['approval_status'],'scale':scale,
               'sources':{key:value['manifest'] for key,value in spec['sources'].items()},
               'entries':entries,'pages':pages,'summary':summary,
               'overview':f'{OUT}/overview.png','pdf':f'{OUT}/full_catalog.pdf',
               'archive':f'{OUT}/native_assets.zip','archive_files':sorted(archive_paths),
               'inputs':{str(path.relative_to(ROOT)):sha256(path.read_bytes()).hexdigest() for path in sorted(used)},
               'artifacts':{path:sha256(data).hexdigest() for path,data in outputs.items()}}
    outputs[f'{OUT}/catalog.json'] = json_bytes(catalog)
    return outputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args(argv)
    changed = [];outputs = products()
    for name,data in outputs.items():
        path = ROOT/name
        if not path.exists() or path.read_bytes()!=data:
            changed.append(name)
            if not args.check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    if args.check and changed:raise SystemExit('Stale dungeon catalog: '+', '.join(changed))
    print(('Verified' if args.check else 'Built')+f' {len(outputs)} catalog artifacts')


if __name__=='__main__':main()
