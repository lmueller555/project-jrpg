"""Technical export of 16 authored front-walk drawings; no procedural posing."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/characters/iselin/walk_front/authored.png'
BASE=ROOT/'assets/characters/iselin/walk_front'
REVIEW=ROOT/'docs/reviews/iselin_front_walk'


def build():
    master=Image.open(SOURCE).convert('RGBA');cells=[];records=[]
    for i in range(16):
        x,y=i%4,i//4
        rect=(x*master.width//4,y*master.height//4,(x+1)*master.width//4,(y+1)*master.height//4)
        cell=master.crop(rect)
        cell.putalpha(cell.getchannel('A').point(lambda a:255 if a>=128 else 0))
        bounds=cell.getbbox()
        if bounds is None:raise ValueError('Missing authored frame')
        cells.append(cell.crop(bounds));records.append({'cell':list(rect),'bounds':list(bounds)})
    scale=68/max(im.height for im in cells)
    BASE.mkdir(parents=True,exist_ok=True);REVIEW.mkdir(parents=True,exist_ok=True)
    frames=[];sheet=Image.new('RGBA',(42*16,72))
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
    board=Image.new('RGB',(752,1300),'#e8edf2');draw=ImageDraw.Draw(board)
    draw.text((18,12),'ISELIN / FRONT WALK / 16 AUTHORED POSES',font=font,fill='#263c35')
    for i,im in enumerate(cells):
        size=(round(im.width*scale),round(im.height*scale))
        if size[0]>40:raise ValueError('Clipped sprite')
        frame=Image.new('RGBA',(42,72));origin=((42-size[0])//2,70-size[1])
        frame.alpha_composite(im.resize(size,Image.Resampling.NEAREST),origin)
        frame.save(BASE/f'frame_{i+1:02}.png');frames.append(frame)
        sheet.alpha_composite(frame,(i*42,0))
        records[i].update(size=list(size),origin=list(origin))
        pos=(12+(i%4)*188,46+(i//4)*310)
        board.paste(frame.resize((168,288),Image.Resampling.NEAREST),pos,frame.resize((168,288),Image.Resampling.NEAREST))
        draw.text((pos[0]+4,pos[1]+288),f'{i+1:02}',font=font,fill='#263c35')
    if len({f.tobytes() for f in frames})!=16:raise ValueError('Repeated native poses')
    sheet.save(BASE/'spritesheet.png');board.save(REVIEW/'frames.png')
    previews=[]
    for tick in range(32):
        preview=Image.new('RGB',(440,380),'#e8edf2');d=ImageDraw.Draw(preview)
        d.text((16,12),'Normal speed',font=font,fill='#263c35')
        d.text((238,12),'Half speed',font=font,fill='#263c35')
        for index,x in ((tick%16,22),((tick//2)%16,244)):
            image=frames[index].resize((168,288),Image.Resampling.NEAREST)
            preview.paste(image,(x,48),image)
            d.text((x+12,344),f'Frame {index+1:02}/16',font=font,fill='#263c35')
        previews.append(preview)
    # GIF stores centiseconds: alternate 30/40ms to preserve the 560ms cycle.
    previews[0].save(REVIEW/'preview.gif',save_all=True,append_images=previews[1:],
                     duration=[30,40]*16,loop=0,disposal=2,optimize=False)
    metadata={'character':'iselin','animation':'walk.front','status':'approved',
              'frame_size':[42,72],'draw_anchor':[21,60],'foot_anchor':[21,68],
              'artwork_pixels_per_world_pixel':2,'loop':True,'cycle_ms':560,
              'source':SOURCE.relative_to(ROOT).as_posix(),
              'frames':[{'file':f'frame_{i+1:02}.png','rect':[i*42,0,42,72],'duration_ms':35} for i in range(16)]}
    (BASE/'animation.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (SOURCE.parent/'registration.json').write_text(json.dumps({
        'tool':'image_gen.imagegen','reference':'assets/source/characters/iselin/idle_front_master.png',
        'source_sha256':sha256(SOURCE.read_bytes()).hexdigest(),'atlas_grid':[4,4],
        'uniform_scale':scale,'hard_alpha_threshold':128,'frames':records,
        'processing':'Crop, hard alpha, uniform nearest-neighbor reduction and whole-frame registration only.',
        'approval':'User approved the front-walk preview for merge; directional/runtime walking integration remains a later pass.'},indent=2)+'\n')
    print('Exported 16 distinct 42x72 drawings, 560ms cycle, sheet and looping review.')


if __name__=='__main__':build()
