"""Register the approved cottage bed as compact, single-level children's twins."""
import hashlib
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/terrain/eldenmere/child_beds'
SOURCE=ROOT/'assets/source/terrain/eldenmere/child_beds'
ORIGINAL=ROOT/'assets/terrain/eldenmere/cottage_furniture/sprites/bed.png'
SIZE=(32,48)
FLOOR=[4,12,24,32]
QUILTS={
    'sage':['#405b49','#6e9275','#a0b9a2'],
    'blue':['#304f70','#4d77a0','#7da5c7'],
    'plum':['#51364f','#805477','#ad80a0'],
}


def read(path):
    import json
    return json.loads(path.read_text())


def write(path,data):
    import json
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n')


def rgba(color):return tuple(bytes.fromhex(color[1:]))+(255,)


def build():
    before=hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
    approved=Image.open(ORIGINAL).convert('RGBA')
    palette=read(ROOT/'assets/terrain/eldenmere/cottage_furniture/furniture.json')['palette']
    quilt_names=('quilt_shadow','quilt_base','quilt_light')
    quilt_source=[rgba(palette[name]) for name in quilt_names]
    linen={rgba(palette[name]) for name in ('linen_shadow','linen_light')}
    registered=Image.new('RGBA',SIZE)
    occupied=approved.crop((8,6,40,66)).resize((24,42),Image.Resampling.NEAREST)
    registered.alpha_composite(occupied,(4,3))
    OUT.mkdir(parents=True,exist_ok=True);SOURCE.mkdir(parents=True,exist_ok=True)
    variants={}
    for name,colors in QUILTS.items():
        layers={key:Image.new('RGBA',SIZE) for key in ('wood_frame','pillow_and_linen','folded_quilt')}
        replace=dict(zip(quilt_source,map(rgba,colors)))
        for y in range(SIZE[1]):
            for x in range(SIZE[0]):
                pixel=registered.getpixel((x,y))
                if not pixel[3]:continue
                key='folded_quilt' if pixel in replace else 'pillow_and_linen' if pixel in linen else 'wood_frame'
                layers[key].putpixel((x,y),replace.get(pixel,pixel))
        merged=Image.new('RGBA',SIZE);paths=[]
        for key,image in layers.items():
            path=SOURCE/name/(key+'.png');path.parent.mkdir(parents=True,exist_ok=True)
            image.save(path);paths.append(path.relative_to(ROOT).as_posix());merged.alpha_composite(image)
        assert merged.getbbox()==(4,3,28,45)
        assert set(merged.getchannel('A').tobytes())=={0,255}
        path=OUT/(name+'.png');merged.save(path)
        variants[name]={'image':path.relative_to(ROOT).as_posix(),'frame_size':list(SIZE),
                        'floor_rect':FLOOR,'sort_y_offset':44,'quilt_palette':colors,
                        'layers_from_repo_root':paths}
    status=read(OUT/'beds.json')['status'] if (OUT/'beds.json').exists() else 'review'
    metadata={'id':'eldenmere.compact_child_twin_beds','status':status,'tile_size':24,
              'frame_size':list(SIZE),'occupied_rect':[4,3,24,42],'floor_rect':FLOOR,
              'sort_y_offset':44,'variants':variants,
              'source_image':ORIGINAL.relative_to(ROOT).as_posix(),'approved_source_sha256':before,
              'source_crop':[8,6,32,60],'registered_size':[24,42],'registration_offset':[4,3],
              'source_recipe':(SOURCE/'recipe.json').relative_to(ROOT).as_posix(),
              'suggested_placement':{'two_beds':[[96,96],[132,96]],
                  'access_points':[[112,154],[148,154]],'single_bed':[96,96]},
              'notes':'Single-level compact twin beds; unchanged approved wood and linen colors, family quilt palettes.'}
    write(OUT/'beds.json',metadata)
    write(SOURCE/'recipe.json',{'id':metadata['id'],'status':status,'source_image':metadata['source_image'],
          'approved_source_sha256':before,'source_crop':metadata['source_crop'],
          'registered_size':[24,42],'registration_offset':[4,3],'frame_size':list(SIZE),
          'floor_rect':FLOOR,'quilt_source':[palette[n] for n in quilt_names],
          'quilt_variants':QUILTS,'resampling':'nearest','layer_order':['wood_frame','pillow_and_linen','folded_quilt']})
    board=Image.new('RGB',(672,452),'#e8edf2');d=ImageDraw.Draw(board);d.fontmode='1'
    fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    d.text((20,12),'Compact twin beds / three family quilts',font=ImageFont.truetype(fontpath,23),fill='#26343e')
    for i,(name,spec) in enumerate(variants.items()):
        image=Image.open(ROOT/spec['image']).convert('RGBA').resize((192,288),Image.Resampling.NEAREST)
        board.paste(image,(20+i*220,70),image)
        d.text((24+i*220,382),name.title(),font=ImageFont.truetype(fontpath,20),fill='#26343e')
    d.text((20,420),'32x48 frame | 24x42 visible | single level | nearest-neighbor pixels',font=ImageFont.truetype(fontpath,15),fill='#52616c')
    board.save(OUT/'variants_enlarged.png')
    assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()==before
    print('Built compact 32x48 twin beds: sage, blue and plum; approved parent bed unchanged.')


if __name__=='__main__':build()
