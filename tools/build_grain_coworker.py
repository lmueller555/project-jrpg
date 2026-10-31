"""Register full, image-authored grain coworker action frames.

This exporter crops whole authored figures, thresholds alpha, nearest-scales
all poses uniformly and registers their soles. It never draws or transforms
individual limbs; approved generic NPC idles/walks stay read-only.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/characters/grain_workers/coworker'
OUT = ROOT/'assets/characters/grain_workers/coworker'
SIZE = (40,44)
ANCHOR = (20,38)
SCALE = 1/8
ROWS = [(0,289),(289,578),(578,855),(855,1155)]
SEQUENCES = [
    ('work_left',[(0,col) for col in range(4)],True,360),
    # A weighted hold stays planted. Other authored high-support alternatives
    # remain in the retained sheet, rather than creating a three-pixel fidget.
    ('assist_right',[(1,1)],False,800),
    ('assist_low_right',[(1,1),(2,1),(2,2),(2,3)],False,200),
    ('recover_right',[(2,3),(2,1),(1,1),(1,1)],False,100),
    ('stretch_front',[(3,col) for col in range(4)],False,550),
]


def sha(data):return hashlib.sha256(data).hexdigest()
def png(image):
    stream=io.BytesIO();image.save(stream,format='PNG',optimize=True);return stream.getvalue()
def dump(data):return (json.dumps(data,indent=2)+'\n').encode()


def registered(source, row, col):
    y0,y1=ROWS[row]
    x0=round(source.width*col/4);x1=round(source.width*(col+1)/4)
    frame=source.crop((x0,y0,x1,y1)).convert('RGBA')
    frame.putalpha(frame.getchannel('A').point(lambda value:255 if value>=128 else 0))
    frame=frame.resize((round(frame.width*SCALE),round(frame.height*SCALE)),Image.Resampling.NEAREST)
    bounds=frame.getbbox()
    if not bounds:raise ValueError('Empty authored figure')
    sole=frame.getchannel('A').crop((0,bounds[3]-2,frame.width,bounds[3])).getbbox()
    if not sole:raise ValueError('Missing authored soles')
    foot_x=round((sole[0]+sole[2]-1)/2)
    origin=(ANCHOR[0]-foot_x,ANCHOR[1]+1-bounds[3])
    result=Image.new('RGBA',SIZE)
    result.alpha_composite(frame,origin)
    if (origin[0]+bounds[0]<0 or origin[0]+bounds[2]>SIZE[0]
            or origin[1]+bounds[1]<0 or origin[1]+bounds[3]>SIZE[1]):
        raise ValueError('Authored figure leaves its registered canvas')
    return result


def build_payload():
    source_path=SOURCE/'work_generated.png'
    source=Image.open(source_path).convert('RGBA')
    if source.size != (1362,1155):raise ValueError('Unexpected retained source sheet dimensions')
    payload={};images={};sequences={}
    for key,cells,loop,duration in SEQUENCES:
        frames=[]
        for index,(row,col) in enumerate(cells):
            filename=f'{key}_{index}.png'
            image=registered(source,row,col)
            payload[OUT/filename]=png(image);images[(key,index)]=image
            record={'file':filename,'duration_ms':duration}
            if key=='work_left':
                record['hands']=[[[-7,-11],[-6,-10]],[[-10,-12],[-7,-11]],
                                 [[-11,-12],[-7,-10]],[[-8,-11],[-6,-10]]][index]
            elif key=='assist_right':
                record['hands']=[[9,-14],[7,-11]]
            elif key=='assist_low_right':
                record['hands']=[[[9,-14],[7,-11]],[[9,-10],[7,-8]],
                                 [[11,-5],[8,-4]],[[11,-7],[8,-7]]][index]
            frames.append(record)
        sequences[key]={'loop':loop,'frames':frames}
    manifest={'version':1,'canvas':list(SIZE),'anchor':list(ANCHOR),'sequences':sequences}
    payload[OUT/'animation.json']=dump(manifest)
    source_names=['work_generated.png','identity_reference.png','prompt.txt']
    provenance={'version':1,'exporter':'tools/build_grain_coworker.py',
        'sources':[{'file':str((SOURCE/name).relative_to(ROOT)),'sha256':sha((SOURCE/name).read_bytes())} for name in source_names],
        'registration':{'canvas':list(SIZE),'anchor':list(ANCHOR),'uniform_source_scale':SCALE,'rows':ROWS},
        'exports':[{'file':str(path.relative_to(ROOT)),'sha256':sha(data)} for path,data in payload.items()],
        'notes':['All action figures are whole authored image-generation frames. No procedural limb paint or limb warping.',
                 'The sack and cover are separate controller-owned objects; no duplicate load is baked into these bodies.',
                 'Approved male_03 directional idles and walks are reused by the runtime without edits.']}
    payload[OUT/'provenance.json']=dump(provenance)
    review=Image.new('RGBA',(4*160,len(SEQUENCES)*190),'#29413b')
    draw=ImageDraw.Draw(review)
    for row,(key,cells,_,_) in enumerate(SEQUENCES):
        for col in range(4):
            index=min(col,len(cells)-1)
            review.alpha_composite(images[(key,index)].resize((160,176),Image.Resampling.NEAREST),(col*160,row*190))
            draw.text((col*160+4,row*190+177),f'{key} {index}',fill='#dcd8c6')
    payload[SOURCE/'native_review.png']=png(review)
    previews=[]
    for index in range(4):
        sheet=Image.new('RGBA',(len(SEQUENCES)*80,100),'#29413b')
        for n,(key,cells,_,_) in enumerate(SEQUENCES):
            sheet.alpha_composite(images[(key,min(index,len(cells)-1))].resize((80,88),Image.Resampling.NEAREST),(n*80,0))
        previews.append(sheet.convert('RGB'))
    stream=io.BytesIO();previews[0].save(stream,format='GIF',save_all=True,append_images=previews[1:],duration=360,loop=0,disposal=2)
    payload[SOURCE/'action_review.gif']=stream.getvalue()
    return payload


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    payload=build_payload()
    if args.check:
        changed=[str(path.relative_to(ROOT)) for path,data in payload.items() if not path.exists() or path.read_bytes()!=data]
        if changed:raise SystemExit('Changed or missing authored exports: '+', '.join(changed))
        print(f'Verified {len(payload)} grain coworker exports')
    else:
        for path,data in payload.items():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        print(f'Exported {len(payload)} grain coworker files')

if __name__=='__main__':main()
