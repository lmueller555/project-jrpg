"""Export Daisy's four dog idles from the retained generated turnaround.

32x36 transparent dog frames leave room for a quadruped body and plumed tail;
visible standing height remains slightly below Liam's 26 native pixels.
"""
import json
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/characters/daisy'
OUT=ROOT/'assets/characters/daisy'
REVIEW=ROOT/'docs/reviews/daisy'
FRAME=(32,36)
ANCHOR=(16,34)
BACKGROUND='#e8edf2'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
PALETTE={
    'outline':['#1a0e16'],
    'gray_fur':['#5f6267','#888b8d','#b3b6b6'],
    'white_fur':['#c5c5bd','#eee8d9','#fff4df'],
    'black_spots':['#25272b'],
    'nose':['#171a20'],
}
EYES={'pupil':'#1a0e16','iris':'#6e5034'}
VIEWS={
    'front':{'source_bounds':[141,62,541,560],'occupied_rect':[9,11,20,24],
             'eyes':[[14,16],[18,16]],'nose':[16,18],
             'layers':{'head_and_ears':[0,21],'body_and_tail':[21,30],'paws':[30,36]}},
    'left':{'source_bounds':[619,66,1282,560],'occupied_rect':[1,12,30,23],
            'eyes':[[5,17]],'nose':[1,18],
            'layers':{'upper_silhouette':[0,21],'body_and_tail':[21,29],'paws':[29,36]}},
    'right':{'source_bounds':[47,635,689,1131],'occupied_rect':[1,12,30,23],
             'eyes':[[27,17]],'nose':[30,18],
             'layers':{'upper_silhouette':[0,21],'body_and_tail':[21,29],'paws':[29,36]}},
    'back':{'source_bounds':[843,635,1279,1139],'occupied_rect':[5,11,22,24],
            'eyes':[],'layers':{'head_and_ears':[0,21],'body_and_tail':[21,29],'paws':[29,36]}},
}


def rgba(color):return tuple(bytes.fromhex(color[1:]))+(255,)


def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n')


def export(source,spec):
    x,y,w,h=spec['occupied_rect']
    sample=source.crop(tuple(spec['source_bounds'])).resize((w,h),Image.Resampling.NEAREST)
    colors=[rgba(color) for shades in PALETTE.values() for color in shades]
    result=Image.new('RGBA',FRAME)
    for row in range(h):
        for col in range(w):
            p=sample.getpixel((col,row))
            if p[3]<128:continue
            color=min(colors,key=lambda c:sum((c[i]-p[i])**2 for i in range(3)))
            result.putpixel((x+col,y+row),color)
    for ex,ey in spec['eyes']:
        result.putpixel((ex,ey),rgba(EYES['pupil']))
        result.putpixel((ex,ey+1),rgba(EYES['iris']))
    if spec.get('nose'):result.putpixel(tuple(spec['nose']),rgba(PALETTE['nose'][0]))
    return result


def font(size):return ImageFont.truetype(FONT,size)


def board(path,items,scale,title,subtitle):
    stride=32*scale+40;width=stride*len(items)+24;height=36*scale+176
    image=Image.new('RGB',(width,height),BACKGROUND);d=ImageDraw.Draw(image);d.fontmode='1'
    d.text((24,16),title,font=font(28),fill='#26343e')
    d.text((24,58),subtitle,font=font(20),fill='#52616c')
    baseline=112+35*scale
    d.line((20,baseline,width-20,baseline),fill='#b5c1c4')
    for i,(label,sprite) in enumerate(items):
        # Pad humans horizontally so all review frames have the same anchor.
        canvas=Image.new('RGBA',FRAME)
        canvas.alpha_composite(sprite,((32-sprite.width)//2,0))
        big=canvas.resize((32*scale,36*scale),Image.Resampling.NEAREST)
        image.paste(big,(24+i*stride,112),big)
        d.text((24+i*stride,36*scale+132),label,font=font(21),fill='#26343e')
    image.save(path)


def build():
    OUT.mkdir(parents=True,exist_ok=True);REVIEW.mkdir(parents=True,exist_ok=True)
    source=Image.open(SOURCE/'idle_turnaround_concepts.png').convert('RGBA')
    palette={'status':'review','materials':PALETTE,'eyes':EYES}
    write(OUT/'palette.json',palette)
    sprites={};records=[]
    allowed={rgba(color) for shades in PALETTE.values() for color in shades}
    allowed.update(rgba(color) for color in EYES.values())
    for direction,spec in VIEWS.items():
        native=export(source,spec);x,y,w,h=spec['occupied_rect']
        assert native.size==FRAME and native.getbbox()==(x,y,x+w,y+h),(direction,native.getbbox())
        assert native.getbbox()[3]==35
        assert set(native.getchannel('A').tobytes())=={0,255}
        assert all(p[3]==0 or p in allowed for p in getattr(native,'get_flattened_data',native.getdata)())
        for ex,ey in spec['eyes']:
            assert native.getpixel((ex,ey))==rgba(EYES['pupil'])
            assert native.getpixel((ex,ey+1))==rgba(EYES['iris'])
        if direction=='back':
            assert rgba(EYES['iris']) not in set(getattr(native,'get_flattened_data',native.getdata)())
        native.save(OUT/f'idle_{direction}.png');sprites[direction]=native
        combined=Image.new('RGBA',FRAME);layers=[]
        for name,(first,last) in spec['layers'].items():
            layer=Image.new('RGBA',FRAME);layer.paste(native.crop((0,first,32,last)),(0,first))
            path=SOURCE/f'idle_{direction}_layers/{name}.png';path.parent.mkdir(parents=True,exist_ok=True)
            layer.save(path);combined.alpha_composite(layer);layers.append(path.relative_to(ROOT).as_posix())
        assert combined.tobytes()==native.tobytes()
        record={'character':'daisy','display_name':'Daisy','species':'dog','sex':'female',
                'family':'liam_family','status':'review','animation':f'idle.{direction}',
                'image':f'idle_{direction}.png','frame_size':list(FRAME),'rect':[0,0,32,36],
                'occupied_rect':spec['occupied_rect'],'visible_height_px':h,'foot_anchor':list(ANCHOR),
                'palette':'palette.json','eyes':{'top_pixels':spec['eyes'],'height':2,'iris_offset_y':1},
                'source':'assets/source/characters/daisy/idle_turnaround_concepts.png',
                'export_recipe':'assets/source/characters/daisy/export.json','layers_from_repo_root':layers}
        write(OUT/f'idle_{direction}.json',record);records.append(record)
        card=Image.new('RGB',(832,1040),BACKGROUND);d=ImageDraw.Draw(card);d.fontmode='1'
        d.text((24,20),f'Daisy / {direction} idle',font=font(28),fill='#26343e')
        d.text((24,62),f'32x36 frame | {h} px tall | 24x native pixels',font=font(20),fill='#52616c')
        big=native.resize((768,864),Image.Resampling.NEAREST);card.paste(big,(32,108),big)
        d.text((24,990),'Gray fur / white and black spots / floppy ears',font=font(22),fill='#52616c')
        card.save(REVIEW/f'idle_{direction}.png')
    sheet=Image.new('RGBA',(128,36))
    for i,direction in enumerate(VIEWS):sheet.alpha_composite(sprites[direction],(i*32,0))
    sheet.save(OUT/'idle_directions.png')
    write(OUT/'idle_directions.json',{'character':'daisy','status':'review','image':'idle_directions.png',
          'frame_size':list(FRAME),'foot_anchor':list(ANCHOR),
          'frames':[{**record,'rect':[i*32,0,32,36]} for i,record in enumerate(records)],
          'spot_continuity':{'left_flank':'larger black patch',
                             'right_flank':'two smaller black spots and a white hip patch',
                             'shared':'gray floppy ears, white muzzle/chest/toes and fluffy light-tipped tail'}})
    write(SOURCE/'export.json',{'source':'idle_turnaround_concepts.png','alpha_threshold':128,
          'resampling':'nearest','frame_size':list(FRAME),'foot_anchor':list(ANCHOR),'views':VIEWS})
    board(REVIEW/'idle_directions.png',[(name.title(),sprites[name]) for name in VIEWS],12,
          'Daisy / four directional idle designs','Front / left / right / back | shared 12x scale | design review')
    liam=Image.open(ROOT/'assets/characters/liam/idle_front.png').convert('RGBA')
    board(REVIEW/'liam_comparison.png',[
        ('Liam / 26 px',liam),('Daisy front / 24 px',sprites['front']),('Daisy side / 23 px',sprites['left'])],16,
        'Daisy and Liam / shared scale','16x native pixels | same paw/foot baseline | Daisy is slightly shorter')
    print('Exported Daisy: front, left, right and back; 32x36 frames, 23-24 visible pixels.')


if __name__=='__main__':build()
