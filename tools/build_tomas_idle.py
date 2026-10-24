"""Export Tomas's retained appearance at 32 visible pixels within a 24×36 frame."""
import json
from pathlib import Path

from PIL import Image, ImageDraw

from build_serene_idle import BACKGROUND, font, rgb, write_json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/characters/tomas'
OUT = ROOT/'assets/characters/tomas'


def build():
    recipe=json.loads((SOURCE/'export.json').read_text())
    palette=json.loads((OUT/'palette.json').read_text())
    source=Image.open(SOURCE/recipe['source']).convert('RGBA')
    native=Image.new('RGBA',tuple(recipe['frame_size']))
    left,_,right,_=recipe['source_bounds']
    offset,_,width,_=recipe['occupied_rect']
    for band in recipe['bands']:
        top,bottom=band['source_y']
        first,last=band['native_y']
        sampled=source.crop((left,top,right,bottom)).resize((width,last-first),Image.Resampling.NEAREST)
        for y in range(sampled.height):
            for x in range(sampled.width):
                pixel=sampled.getpixel((x,y))
                if pixel[3]<recipe['alpha_threshold']:
                    continue
                sx=left+int((x+.5)*(right-left)/width)
                sy=top+int((y+.5)*(bottom-top)/sampled.height)
                materials=band['materials']
                for window in recipe['material_windows']:
                    x0,y0,x1,y1=window['rect']
                    if x0<=sx<x1 and y0<=sy<y1:
                        materials=window['materials']
                colors=[rgb(c) for m in materials for c in palette['materials'][m]]
                color=min(colors,key=lambda c:sum((a-b)**2 for a,b in zip(c,pixel[:3])))
                native.putpixel((offset+x,first+y),(*color,255))
    for x,y in recipe['eyes']['top_pixels']:
        native.putpixel((x,y),(*rgb(palette['eyes']['pupil']),255))
        native.putpixel((x,y+1),(*rgb(palette['eyes']['iris']),255))
    assert native.size==(24,36)
    assert native.getbbox()==(6,3,18,35), 'Expected 12×32 visible bounds, baseline 34'
    assert set(native.getchannel('A').tobytes())=={0,255}
    allowed={(*rgb(c),255) for colors in palette['materials'].values() for c in colors}
    allowed.update((*rgb(c),255) for c in palette['eyes'].values())
    assert all(native.getpixel((x,y))[3]==0 or native.getpixel((x,y)) in allowed
               for y in range(36) for x in range(24))
    for x,y in recipe['eyes']['top_pixels']:
        assert native.getpixel((x,y))==(*rgb(palette['eyes']['pupil']),255)
        assert native.getpixel((x,y+1))==(*rgb(palette['eyes']['iris']),255)
    patch=(*rgb(palette['materials']['patch'][0]),255)
    patch_pixels=[(x,y) for y in range(36) for x in range(24) if native.getpixel((x,y))==patch]
    assert patch_pixels and all(x>=12 and 26<=y<31 for x,y in patch_pixels)
    reference=Image.open(ROOT/'assets/characters/caelan/idle_front.png').convert('RGBA')
    bounds,reference_bounds=native.getbbox(),reference.getbbox()
    assert bounds[3]==reference_bounds[3]==35
    assert (reference_bounds[3]-reference_bounds[1])-(bounds[3]-bounds[1])==2
    native.save(OUT/'idle_front.png')
    combined=Image.new('RGBA',native.size)
    layers=[]
    for name,(first,last) in recipe['layers'].items():
        layer=Image.new('RGBA',native.size)
        layer.paste(native.crop((0,first,24,last)),(0,first))
        layer.save(SOURCE/'layers'/f'{name}.png')
        combined.alpha_composite(layer)
        layers.append(f'../../source/characters/tomas/layers/{name}.png')
    assert combined.tobytes()==native.tobytes()

    review=Image.new('RGB',(720,1040),BACKGROUND)
    draw=ImageDraw.Draw(review)
    draw.text((32,16),'Tomas — front idle',font=font(28),fill='#26343e')
    draw.text((32,54),'24×36 frame · 32 px visible height · 24× review',font=font(20),fill='#52616c')
    enlarged=native.resize((576,864),Image.Resampling.NEAREST)
    review.paste(enlarged,(72,96),enlarged)
    draw.text((32,984),'Blond cowlick · green eyes · rust-red tunic',font=font(23),fill='#26343e')
    review.save(OUT/'idle_front_review.png')

    board=Image.new('RGB',(1280,736),BACKGROUND)
    draw=ImageDraw.Draw(board)
    draw.text((32,16),'Sanctuary family — shared scale and foot baseline',font=font(27),fill='#26343e')
    draw.text((32,56),'24×36 frames at 16× · Tomas is two native pixels shorter',font=font(21),fill='#52616c')
    for i,(label,character) in enumerate([('Caelan · 34 px','caelan'),('Tomas · 32 px · review','tomas'),('Serene · 34 px','serene')]):
        sprite=Image.open(ROOT/f'assets/characters/{character}/idle_front.png').convert('RGBA')
        enlarged=sprite.resize((384,576),Image.Resampling.NEAREST)
        x=32+i*416
        board.paste(enlarged,(x,112),enlarged)
        draw.text((x+20,704),label,font=font(22),fill='#26343e')
    board.save(OUT/'scale_comparison.png')
    path=OUT/'idle_front.json'
    status=json.loads(path.read_text()).get('status','review') if path.exists() else 'review'
    write_json(path,{
        'character':'tomas','animation':'idle.front','design_status':'approved','status':status,
        'image':'idle_front.png','frame_size':[24,36],'rect':[0,0,24,36],
        'occupied_rect':[6,3,12,32],'visible_height_px':32,'foot_anchor':[12,34],
        'height_comparison':{'character':'caelan','visible_height_px':34,'difference_px':-2},
        'palette':'palette.json','source':'../../source/characters/tomas/idle_front_concept.png',
        'export_recipe':'../../source/characters/tomas/export.json','layers':layers,
        'eyes':recipe['eyes'],
        'knee_patch':{'anatomical_side':'left','front_screen_side':'right'},
        'review':{'image':'idle_front_review.png','scale':24,'background':BACKGROUND},
        'comparison':'scale_comparison.png'
    })
    print('Exported Tomas: 24×36 frame, 32 visible rows, four layers and opaque review/comparison PNGs.')


if __name__=='__main__':
    build()
