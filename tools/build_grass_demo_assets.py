"""Build isolated native grass materials and rooted interactive blade poses.

The prototype extends the existing pack's pixel scale and plant vocabulary.
Explicit material motifs and blade graphs supply the new art; no live map or
original approved image is modified. Runtime consumes the checked-in frames.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/grass_demo/recipe.json'
OUTPUT = ROOT/'assets/terrain/grass_demo'


def png(image):
    stream = BytesIO(); image.save(stream, format='PNG'); return stream.getvalue()


def native_material(family, seed, palette):
    """Draw quiet common growth plus distinct low-contrast accent coverage.

    Variants 00/01 are deliberately calm common materials. Variants 02/03
    supply larger coverage and occasional tufts for clustered placement.
    """
    image = Image.new('RGB', (24,24), palette['base'])
    draw = ImageDraw.Draw(image)
    ordinal = {'lawn':(17,41,63,89),'meadow':(113,151,179,211),
               'woodland':(239,263,293,331)}[family].index(seed)
    hints = ([(3,5),(12,18),(20,10)],[(6,17),(17,4),(21,21),(9,8)],
             [(4,19),(18,6),(19,18)],[(5,6),(17,16),(7,20)])[ordinal]

    def fine_blades(points, height=2):
        for index,(x,y) in enumerate(points):
            draw.line([(x,y),(x-1,y-height)],fill=palette['soft_mid'])
            draw.point((x+1,y-1),fill=palette['soft_light'])
            if index%2:draw.point((x-2,y),fill=palette['soft_mid'])

    def patch(x,y,rx,ry,color):
        draw.polygon([(x-rx,y-1),(x-rx+1,y-ry+1),(x-1,y-ry),
                      (x+2,y-ry+1),(x+rx,y-1),(x+rx-1,y+ry-1),
                      (x+1,y+ry),(x-2,y+ry-1),(x-rx,y+1)],fill=color)
        draw.point((x-rx+1,y+2),fill=palette['base'])
        draw.point((x+rx-1,y-2),fill=palette['base'])

    def tuft(x,y,height=4,width=3):
        patch(x,y,width+1,2,palette['soft_mid'])
        for dx,h in ((-width,max(2,height-2)),(-1,height),(1,height-1),(width,2)):
            draw.line([(x+dx//2,y+1),(x+dx,y-h)],fill=palette['mid'])
            draw.point((x+dx,y-h+1),fill=palette['soft_light'])
        draw.point((x,y-2),fill=palette['light'])

    if family == 'lawn':
        if ordinal<2:
            fine_blades(hints)
            if ordinal==1:draw.line([(11,13),(13,12),(15,13)],fill=palette['soft_mid'])
        elif ordinal==2:
            patch(13,12,7,5,palette['soft_mid'])
            patch(10,11,3,2,palette['soft_light'])
            fine_blades([(5,19),(20,6)])
        else:
            tuft(6,8,3,2);tuft(17,17,3,2)
            fine_blades([(17,4),(4,18)])
    elif family == 'meadow':
        if ordinal==0:
            fine_blades([(4,7),(11,19),(19,10),(15,4)],3)
            draw.line([(6,14),(7,11)],fill=palette['soft_light'])
        elif ordinal==1:
            patch(16,14,5,4,palette['soft_mid'])
            fine_blades([(5,5),(8,18),(19,8)],3)
            draw.line([(15,15),(14,12)],fill=palette['soft_light'])
        elif ordinal==2:
            patch(9,12,6,5,palette['soft_mid'])
            patch(12,11,4,3,palette['moss'])
            fine_blades([(4,10),(7,15),(14,12),(20,5)],3)
            draw.line([(10,10),(11,7)],fill=palette['soft_light'])
        else:
            tuft(7,15,5,3);tuft(18,7,4,2)
            fine_blades([(19,20),(4,5)])
    else:
        if ordinal<2:
            patch(8 if ordinal==0 else 16,10 if ordinal==0 else 15,6,4,palette['soft_mid'])
            fine_blades(hints[:2])
            leaves=[(17,18)] if ordinal==0 else [(5,8),(18,6)]
        else:
            x,y=(8,15) if ordinal==2 else (15,8)
            patch(x,y,6,5,palette['moss'])
            patch(x+1,y,3,2,palette['mid'])
            fine_blades(hints[:2])
            leaves=[(18,7),(18,19),(7,5)] if ordinal==2 else [(6,7),(6,18),(15,19)]
            if ordinal==3:
                draw.line([(3,12),(5,11),(7,12),(9,11)],fill=palette['soil_shadow'])
                draw.point((5,10),fill=palette['soil'])
        for lx,ly in leaves:
            draw.line([(lx-1,ly+1),(lx+1,ly-1)],fill=palette['leaf'])
            draw.point((lx-1,ly),fill=palette['leaf'])
            draw.point((lx,ly),fill=palette['leaf_light'])
    ImageDraw.Draw(image).rectangle((0,0,23,23),outline=palette['base'])
    return image


def blade_frame(blades, palette, variant, *, wind=0, direction=None, strength=0):
    """Draw bent leaves around immutable roots on shared rear/front canvases."""
    layers = {key:Image.new('RGBA',(24,32)) for key in ('rear','front')}
    for index,(rx,ry,tx,ty,width,layer) in enumerate(blades):
        height = ry-ty
        dx,dy = wind,0
        if direction in ('east','west'):
            dx = round((1 if direction=='east' else -1)*(3+height*.24)*strength)
            dy = round(height*.2*strength)
        elif direction is not None:
            side = -1 if tx < 12 else 1
            dx = round(side*(4+height*.22)*strength)
            dy = round(height*(.28 if direction=='north' else .42)*strength)
        tip = (max(0,min(23,tx+dx)),max(2,min(25,ty+dy)))
        # Curved midsection retains a rooted bend rather than translating clumps.
        bend = .48 if variant!='arching' else .64
        mx = round(rx+(tip[0]-rx)*bend)
        my = round(ry-(ry-tip[1])*.53)
        draw = ImageDraw.Draw(layers[layer])
        shade = palette['shadow'] if layer=='rear' else palette['mid']
        draw.polygon([(rx-width,ry-2),(mx-width,my),tip,
                      (mx+1,my+1),(rx+1,ry-2)],fill=shade)
        draw.line([(rx,ry-2),(mx,my),tip], fill=palette['light'])
        if index%3 == 1:
            draw.point(tip, fill=palette['highlight'])
        if variant=='seeded' and layer=='rear' and index in (1,2,3):
            draw.line([(tip[0]-1,tip[1]+1),(tip[0]+1,tip[1]+2)],fill=palette['highlight'])
            draw.point((tip[0],tip[1]-1),fill=palette['leaf'])
    # The final rooted rows are identical in every idle/parted pose. Front and
    # rear roots are authored separately so they never double their opacity.
    for layer in layers.values():
        draw = ImageDraw.Draw(layer);draw.rectangle((0,26,23,31),fill=(0,0,0,0))
    back = ImageDraw.Draw(layers['rear'])
    back.line([(7,27),(12,28),(18,27)],fill=palette['deep'])
    front = ImageDraw.Draw(layers['front'])
    front.line([(6,27),(8,26),(11,28),(14,26),(18,27)],fill=palette['mid'])
    front.point((10,27),fill=palette['light']);front.point((16,27),fill=palette['light'])
    return layers


def products():
    recipe=json.loads(SOURCE.read_text())
    for source in recipe['sources']:
        if sha256((ROOT/source['path']).read_bytes()).hexdigest()!=source['sha256']:
            raise ValueError('Original grass reference changed: '+source['path'])
    output={};material_images={};plant_images={}
    palette=recipe['palette']
    hero=Image.open(ROOT/'assets/characters/caelan/idle_front.png').convert('RGBA')
    hero_bounds=hero.getchannel('A').getbbox()
    character_height=hero_bounds[3]-hero_bounds[1]
    if recipe['opaque_height_limit'] != (character_height+1)//2:
        raise ValueError('Grass height cap must equal half the visible character height')
    manifest={'version':1,'id':recipe['id'],'status':recipe['status'],'tile_size':24,
              'palette':palette,'materials':{},'tall_grass':{
                  'frame_size':recipe['frame_size'],'anchor':recipe['anchor'],
                  'contact_rect':recipe['contact_rect'],
                  'height_limits':recipe['height_limits'],
                  'opaque_height_limit':recipe['opaque_height_limit'],
                  'reference_character_visible_height':character_height,'variants':{}},
              'source_recipe':SOURCE.relative_to(ROOT).as_posix(),
              'source_recipe_sha256':sha256(SOURCE.read_bytes()).hexdigest(),
              'source_assets':recipe['sources']}
    def export(relative,image):
        path=OUTPUT/relative;output[path]=png(image)
        return path.relative_to(ROOT).as_posix()
    def validate_height(layers):
        for layer,image in layers.items():
            bounds=image.getchannel('A').getbbox()
            if bounds is None or recipe['anchor'][1]-bounds[1] > recipe['height_limits'][layer]:
                raise ValueError('Grass exceeds the authored '+layer+' height limit')
        combined=layers['rear'].copy()
        combined.alpha_composite(layers['front'])
        bounds=combined.getchannel('A').getbbox()
        if bounds[3]-bounds[1] > recipe['opaque_height_limit']:
            raise ValueError('Combined grass silhouette exceeds half-character height')
    for family,spec in recipe['families'].items():
        images=[native_material(family,seed,palette) for seed in spec['seeds']]
        material_images[family]=images
        paths=[export(f'ground/{family}_{index:02}.png',image)
               for index,image in enumerate(images)]
        manifest['materials'][family]={'label':spec['label'],'tiles':paths}
    for variant,blades in recipe['variants'].items():
        record={'idle':[],'parted':{}}
        for index,wind in enumerate(recipe['idle_wind']):
            images=blade_frame(blades,palette,variant,wind=wind)
            validate_height(images)
            pose={key:export(f'tall/{variant}/idle_{index:02}_{key}.png',image)
                  for key,image in images.items()}
            pose['duration_ms']=recipe['idle_duration_ms'];record['idle'].append(pose)
            plant_images[(variant,'idle',index)]=images
        for direction in ('north','east','south','west'):
            record['parted'][direction]=[]
            for index,strength in enumerate(recipe['part_strengths']):
                images=blade_frame(blades,palette,variant,direction=direction,strength=strength)
                validate_height(images)
                pose={key:export(f'tall/{variant}/{direction}_{index:02}_{key}.png',image)
                      for key,image in images.items()}
                record['parted'][direction].append(pose)
                plant_images[(variant,direction,index)]=images
        manifest['tall_grass']['variants'][variant]=record
    output[OUTPUT/'assets.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    # Large retained review keeps every comparison at nearest-neighbor scale.
    board=Image.new('RGB',(1110,870),'#e4e9df');draw=ImageDraw.Draw(board)
    font=ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'),18)
    small=ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'),15)
    draw.text((20,12),'Emerald grass prototype — half-height blades / rooted reactions',font=font,fill='#273c2e')
    current=Image.open(ROOT/recipe['sources'][0]['path']).convert('RGB')
    draw.text((20,48),'Current',font=small,fill='#273c2e')
    board.paste(current.resize((144,144),Image.Resampling.NEAREST),(20,72))
    for row,(family,images) in enumerate(material_images.items()):
        y=72+row*192;draw.text((198,y-23),recipe['families'][family]['label'],font=small,fill='#273c2e')
        for index,image in enumerate(images):
            board.paste(image.resize((144,144),Image.Resampling.NEAREST),(198+index*164,y))
    draw.text((866,48),'Unoccupied silhouettes',font=small,fill='#273c2e')
    for index,variant in enumerate(recipe['variants']):
        x=866+(index%2)*128;y=72+(index//2)*192
        tile=Image.new('RGBA',(24,32),palette['base'])
        layers=plant_images[(variant,'idle',1)]
        tile.alpha_composite(layers['rear']);tile.alpha_composite(layers['front'])
        board.paste(tile.convert('RGB').resize((96,128),Image.Resampling.NEAREST),(x,y))
        draw.text((x,y+134),variant.title(),font=small,fill='#273c2e')
    hero_foot_row=hero_bounds[3]-1
    baseline=38
    hero_y=baseline-hero_foot_row
    grass_y=baseline-recipe['anchor'][1]
    tiny=ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'),12)
    for col,variant in enumerate(recipe['variants']):
        x=20+col*268;y=670
        draw.text((x,y-24),variant.title()+' — common baseline',font=small,fill='#273c2e')
        beside=Image.new('RGBA',(48,44),palette['base'])
        beside.alpha_composite(hero,(0,hero_y))
        layers=plant_images[(variant,'idle',1)]
        beside.alpha_composite(layers['rear'],(24,grass_y))
        beside.alpha_composite(layers['front'],(24,grass_y))
        ImageDraw.Draw(beside).line([(0,baseline+1),(47,baseline+1)],fill=palette['shadow'])
        board.paste(beside.convert('RGB').resize((96,88),Image.Resampling.NEAREST),(x,y))
        draw.text((x,y+94),'Beside',font=tiny,fill='#273c2e')
        for index,state in enumerate(('idle','east')):
            tile=Image.new('RGBA',(32,44),palette['base'])
            layers=plant_images[(variant,state,1)]
            tile.alpha_composite(layers['rear'],(4,grass_y))
            tile.alpha_composite(hero,(4,hero_y))
            tile.alpha_composite(layers['front'],(4,grass_y))
            ImageDraw.Draw(tile).line([(0,baseline+1),(31,baseline+1)],fill=palette['shadow'])
            px=x+104+index*72
            board.paste(tile.convert('RGB').resize((64,88),Image.Resampling.NEAREST),(px,y))
            draw.text((px,y+94),'Standing' if index==0 else 'Parted',font=tiny,fill='#273c2e')
    draw.text((20,824),f'Caelan visible height: {hero_bounds[3]-hero_bounds[1]}px. Upright grass: 16–17px; front tips at most 5px above roots.',font=small,fill='#273c2e')
    output[OUTPUT/'materials_review.png']=png(board)
    return output


def build(check=False):
    output=products();expected=set(output)
    obsolete=[p for p in OUTPUT.rglob('*.png') if p not in expected]
    if check and obsolete:raise ValueError('Obsolete grass prototype exports remain')
    for path,body in output.items():
        if check:
            if not path.exists() or path.read_bytes()!=body:
                raise ValueError('Stale grass prototype export: '+str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
    if not check:
        for path in obsolete:path.unlink()
    print(('Verified' if check else 'Built')+' grass prototype materials and rooted poses')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
