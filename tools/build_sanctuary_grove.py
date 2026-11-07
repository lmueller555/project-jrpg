"""Author the Sanctuary's rooted memorial tree and native pixel understory.

Branch graphs and leaf-cluster recipes are independent reusable assets. All
canopy poses retain their silhouette and the woody base is immutable. No scene
painting, resized tree sprite or live Pillow dependency is involved.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
from functools import lru_cache
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/terrain/sanctuary_fantasy/grove.json'
OUTPUT = ROOT/'assets/terrain/sanctuary_fantasy/grove'


def png(image):
    buffer = BytesIO(); image.save(buffer, format='PNG'); return buffer.getvalue()


def shade_path(draw, points, palette, width=9):
    """Carve long grain along a tapered branch, with light on its left edge."""
    for index, (a, b) in enumerate(zip(points, points[1:])):
        thickness = max(2, round(width*(1-index/(len(points)+.2))))
        draw.line((tuple(a), tuple(b)), fill=palette['wood_deep'], width=thickness+3)
        draw.line((tuple(a), tuple(b)), fill=palette['wood_shadow'], width=thickness)
        da = (a[0]-1, a[1]); db = (b[0]-1, b[1])
        draw.line((da, db), fill=palette['wood_mid'], width=max(1, thickness-3))
        draw.line(((a[0]-thickness//3,a[1]),(b[0]-max(1,thickness//3),b[1])),
                  fill=palette['wood_light'], width=1)


@lru_cache(maxsize=1)
def foliage_material():
    recipe=json.loads(SOURCE.read_text())
    source=Image.open(ROOT/'assets/terrain/eldenmere/foliage/tree/idle.png').convert('RGBA')
    old=json.loads((ROOT/'assets/terrain/eldenmere/foliage/palette.json').read_text())
    ramp=[tuple(bytes.fromhex(color[1:])) for color in old['materials']['leaves'].values()]
    return [source.crop(crop) for crop in recipe['leaf_texture_crops']],ramp


def leaf_cluster(canvas, center, radii, palette, index, phase=0):
    """Assemble source-native irregular leaf material inside jagged lobes."""
    cx, cy = center; rx, ry = radii
    outline = [(cx-rx,cy-1),(cx-rx+2,cy-ry//2),(cx-rx//2-2,cy-ry//2-2),
               (cx-rx//2,cy-ry+2),(cx-3,cy-ry),(cx+2,cy-ry+3),
               (cx+rx//2,cy-ry+1),(cx+rx//2+3,cy-ry//2),
               (cx+rx-2,cy-ry//2+1),(cx+rx,cy+1),(cx+rx-3,cy+ry//2),
               (cx+rx//2+2,cy+ry//2+2),(cx+rx//2,cy+ry-1),
               (cx+2,cy+ry),(cx-3,cy+ry-2),(cx-rx//2,cy+ry),
               (cx-rx//2-3,cy+ry//2),(cx-rx+1,cy+ry//2-1)]
    mask = Image.new('1', canvas.size)
    ImageDraw.Draw(mask).polygon(outline, fill=1)
    layer=Image.new('RGBA',canvas.size)
    patches,old=foliage_material()
    light_names=('leaf_deep','leaf_shadow','leaf_mid','leaf_light','leaf_silver','leaf_tip')
    for y in range(max(0,cy-ry),min(canvas.height,cy+ry+1)):
        for x in range(max(0,cx-rx),min(canvas.width,cx+rx+1)):
            if not mask.getpixel((x,y)):continue
            # Texture pieces preserve source leaf shapes at native scale.
            # Each lobe has its own offsets and sources instead of a repeated
            # global stipple or a regular diagonal mesh.
            column=(x-cx+rx)//13;row=(y-cy+ry)//11
            patch=patches[(index+column*3+row*2)%len(patches)]
            pixel=patch.getpixel(((x-cx+rx+index*3)%patch.width,
                                  (y-cy+ry+index*5)%patch.height))
            level=old.index(pixel[:3]) if pixel[3] and pixel[:3] in old else 1
            if y>cy+ry*.35:level=max(0,level-1)
            if x>cx+rx*.65:level=max(0,level-1)
            if level>=4 and (x+y+index)%11==0:
                level=max(1,level-((index+phase)%3==0))
            layer.putpixel((x,y),(*bytes.fromhex(palette[light_names[level]][1:]),255))
    canvas.alpha_composite(layer)


def landmark(recipe, palette, phase):
    spec = recipe['landmark']; size = tuple(spec['canvas'])
    roots, trunk, canopy = [Image.new('RGBA',size) for _ in range(3)]
    roots_draw = ImageDraw.Draw(roots)
    # A cool ground root fan makes the existing24x24 physical base visible.
    roots_draw.polygon(((99,154),(107,150),(121,151),(127,158),(125,171),
                        (116,175),(103,173),(96,169)),fill=palette['wood_deep'])
    for path in spec['roots']:
        shade_path(roots_draw,path,palette,7)
    roots_draw.line(((98,168),(105,168),(109,164)),fill=palette['moss'],width=2)
    roots_draw.line(((121,164),(127,168),(131,168)),fill=palette['moss'],width=2)
    draw = ImageDraw.Draw(trunk)
    for index, path in enumerate(spec['branches']):
        shade_path(draw,path,palette,11 if index<2 else 6)
    # Intertwining bark bands cross without merging into one straight column.
    for points in (((102,143),(109,137),(118,133)),((117,150),(111,145),(105,142)),
                   ((104,126),(108,119),(113,114)),((112,106),(103,101),(97,95))):
        draw.line(points,fill=palette['wood_deep'],width=2)
        draw.line([(x-1,y-1) for x,y in points],fill=palette['wood_light'])
    draw.line(((103,154),(105,149),(103,144)),fill=palette['wood_tip'])
    draw.line(((120,150),(121,144),(119,139)),fill=palette['moss'])
    # Knotted hollows and irregular grain give the crossing limbs rounded
    # volume. Their long highlights follow the wood, not ribbon-like edges.
    for points in (((101,151),(99,144),(101,138),(100,132)),
                   ((116,155),(118,149),(116,143),(117,138)),
                   ((105,130),(102,123),(101,116)),
                   ((94,111),(90,105),(88,98)),
                   ((124,100),(129,96),(137,93))):
        draw.line(points,fill=palette['wood_deep'],width=1)
        draw.line([(x+2,y) for x,y in points],fill=palette['wood_mid'],width=1)
    for x,y in ((102,131),(118,144),(90,101)):
        draw.polygon(((x,y-4),(x+3,y-1),(x+2,y+3),(x,y+5),(x-2,y+1)),fill=palette['wood_deep'])
        draw.line(((x-2,y),(x-1,y-3),(x+1,y-4),(x+3,y-1)),fill=palette['wood_light'])
        draw.point((x,y+2),fill=palette['wood_shadow'])
    # The crown leans west of the fixed trunk, leaving room for the hall.
    for index,(x,y,rx,ry) in enumerate(spec['clusters']):
        leaf_cluster(canopy,(round(x*.8)+4,y),(max(8,round(rx*.8)),ry),
                     palette,index,phase)
    # Three intentional crown windows show the branching skeleton and sky.
    holes = Image.new('L',size,255); hd = ImageDraw.Draw(holes)
    for points in (((65,100),(70,95),(75,100),(74,110),(68,112)),
                   ((91,76),(94,73),(98,76),(98,84),(94,87),(91,83)),
                   ((126,111),(132,106),(138,109),(136,117),(129,119))):
        hd.polygon(points,fill=0)
    from PIL import ImageChops
    canopy.putalpha(ImageChops.darker(canopy.getchannel('A'),holes))
    return {'roots':roots,'trunk':trunk,'canopy':canopy}


def sapling(recipe,palette,variant,phase):
    size=tuple(recipe['saplings']['canvas']); image=Image.new('RGBA',size)
    draw=ImageDraw.Draw(image)
    # Root stones, a low root fan and soft moss account for the inherited base.
    draw.polygon(((12,60),(15,53),(22,50),(31,53),(36,59),(32,68),
                  (24,71),(15,68)),fill=palette['leaf_deep'])
    draw.line(((13,65),(22,60),(34,66)),fill=palette['wood_mid'],width=3)
    if variant=='arching':
        paths=[[(24,63),(22,52),(19,41),(17,31),(11,26)],
               [(20,43),(28,34),(34,30)],[(20,38),(23,25),(22,17)]]
        clusters=[(12,24,10,8),(26,19,11,9),(34,32,11,8),(17,38,12,9)]
    else:
        paths=[[(24,63),(26,50),(24,36),(25,22)],
               [(25,43),(13,32),(10,28)],[(24,35),(35,26),(37,20)]]
        clusters=[(25,16,12,9),(12,27,11,9),(36,22,10,9),(25,34,13,9)]
    for path in paths:shade_path(draw,path,palette,4)
    for index,(x,y,rx,ry) in enumerate(clusters):
        leaf_cluster(image,(x,y),(rx,ry),palette,index,phase)
    return image


def understory(palette,name,phase):
    image=Image.new('RGBA',(24,24));draw=ImageDraw.Draw(image)
    draw.polygon(((2,19),(5,16),(10,15),(16,15),(21,19),(17,22),(7,22)),fill=palette['leaf_deep'])
    for x,y in ((5,19),(10,20),(16,18),(19,20)):
        draw.line(((x,y),(x-2,y-4)),fill=palette['moss'])
        draw.point((x+1,y-2),fill=palette['leaf_mid'])
    if name.startswith('blossom'):
        flower=palette['blossom'] if name.endswith('white') else palette['leaf_cyan']
        for index,(x,y) in enumerate(((6,12),(12,8),(18,13))):
            draw.line(((x,20),(x-1,y+1)),fill=palette['leaf_mid'])
            draw.line(((x-3,y),(x+2,y)),fill=palette['blossom_shadow'])
            draw.line(((x,y-3),(x,y+2)),fill=flower)
            draw.line(((x-2,y-1),(x+1,y+1)),fill=flower)
            draw.point((x,y),fill=palette['blossom'] if (phase+index)%3 else palette['amethyst'])
    elif name=='moss_fan':
        for x,y in ((4,12),(7,8),(10,6),(13,9),(17,11),(20,15)):
            draw.line(((12,21),(x,y)),fill=palette['leaf_shadow'])
            for yy in range(y+2,18,3):
                xx=round(x+(12-x)*(yy-y)/(21-y))
                draw.line(((xx-2,yy-1),(xx,yy),(xx+2,yy-2)),fill=palette['leaf_light'])
    else:
        for points in (((12,20),(5,15),(6,12),(13,17)),((12,20),(15,10),(19,12),(16,20)),
                       ((12,20),(9,9),(12,7),(14,17)),((12,20),(20,16),(21,20))):
            draw.polygon(points,fill=palette['moss']);draw.line(points[:2],fill=palette['leaf_light'])
    return image


def petal(palette,name,phase):
    image=Image.new('RGBA',(8,8));draw=ImageDraw.Draw(image)
    color=palette[{'white':'blossom','cyan':'leaf_cyan','amethyst':'amethyst'}[name]]
    shapes=[((3,1),(5,2),(5,4),(3,6),(2,4)),((2,2),(6,3),(4,5),(2,5)),
            ((3,1),(4,3),(4,6),(3,5))]
    draw.polygon(shapes[phase],fill=color)
    draw.point((3,3),fill=palette['blossom_shadow'])
    return image


def products():
    recipe=json.loads(SOURCE.read_text());palette=recipe['palette']
    for record in recipe['sources']:
        if sha256((ROOT/record['path']).read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('Grove source reference changed: '+record['path'])
    output={};modules={};images={}
    def export(path,image):
        output[OUTPUT/path]=png(image)
        return (OUTPUT/path).relative_to(ROOT).as_posix()
    def module(name,frames,anchor,footprints=(),layer='entity',duration=800):
        images[name]=frames
        modules[name]={'id':'sanctuary.grove.'+name,'size':list(frames[0].size),
                       'anchor':list(anchor),'footprints':list(footprints),'layer':layer,
                       'frames':[{'image':export(name+f'/frame_{index:02}.png',image),
                                  'duration_ms':duration} for index,image in enumerate(frames)],
                       'collision':'ground_base_only' if footprints else 'none'}
    poses=[landmark(recipe,palette,phase) for phase in recipe['landmark']['leaf_phases']]
    anchor=recipe['landmark']['anchor'];footprint=recipe['landmark']['footprint']
    module('landmark_roots',[poses[0]['roots']],anchor,layer='ground_detail')
    module('landmark_trunk',[poses[0]['trunk']],anchor,[footprint])
    module('landmark_canopy',[pose['canopy'] for pose in poses],anchor,layer='overhead_canopy')
    for variant in recipe['saplings']['variants']:
        module('sapling_'+variant,[sapling(recipe,palette,variant,phase) for phase in range(6)],
               recipe['saplings']['anchor'],[recipe['saplings']['footprint']])
    for name in recipe['understory']:
        module(name,[understory(palette,name,phase) for phase in range(3)],(12,21),layer='ground_detail')
    for name in recipe['petals']:
        module('petal_'+name,[petal(palette,name,phase) for phase in range(3)],(4,4),layer='particle',duration=500)
    # Combined views are derived review conveniences; placed modules remain
    # roots/trunk/canopy so the compositor can assign physical depth correctly.
    combined=[]
    for pose in poses:
        image=Image.new('RGBA',tuple(recipe['landmark']['canvas']))
        for layer in ('roots','trunk','canopy'):image.alpha_composite(pose[layer])
        combined.append(image)
    module('landmark_combined',combined,anchor,[footprint],layer='review_composite')
    hero=Image.open(ROOT/'assets/characters/caelan/idle_front.png').convert('RGBA')
    board=Image.new('RGB',(1200,700),palette['ground']);draw=ImageDraw.Draw(board)
    font=ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'),18)
    small=ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'),15)
    draw.rectangle((0,0,1199,72),fill=palette['outline'])
    draw.text((20,12),'Sanctuary memorial grove / authored native pixel modules',font=font,fill=palette['blossom'])
    draw.text((20,42),'Fixed roots and bark; west-leaning silver-green canopy; six local leaf poses',font=small,fill=palette['leaf_silver'])
    # All figures below share the same integer scale and visible ground line.
    scene=Image.new('RGBA',(340,190),palette['ground'])
    scene.alpha_composite(combined[0],(0,8))
    scene.alpha_composite(hero,(202,146))
    scene.alpha_composite(images['sapling_arching'][0],(237,110))
    scene.alpha_composite(images['sapling_upright'][0],(288,110))
    board.paste(scene.convert('RGB').resize((1020,570),Image.Resampling.NEAREST),(20,85))
    draw.text((25,664),'Landmark and Caelan at3× native scale. Caelan34px; tree170px. Sapling bases preserve24×24feet.',font=small,fill=palette['blossom'])
    for index,name in enumerate(recipe['understory']):
        image=images[name][0]
        board.paste(image.resize((96,96),Image.Resampling.NEAREST),(1070,88+index*135),image.resize((96,96),Image.Resampling.NEAREST))
        draw.text((1055,189+index*135),name.replace('_',' '),font=small,fill=palette['blossom'])
    export('materials_review.png',board)
    manifest={'version':1,'id':recipe['id'],'status':recipe['status'],'tile_size':24,
              'palette':palette,'modules':modules,'source_recipe':SOURCE.relative_to(ROOT).as_posix(),
              'source_recipe_sha256':sha256(SOURCE.read_bytes()).hexdigest(),
              'source_assets':recipe['sources'],'wind':{'whole_tree_moves':False,
               'fixed_silhouette':True,'frame_duration_ms':800,'cycle_duration_ms':4800},
              'reference_character_visible_height':34,'landmark_visible_height':170,
              'authoring':recipe['authoring']}
    output[OUTPUT/'assets.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    return output


def build(check=False):
    output=products()
    for path,body in output.items():
        if check:
            if not path.exists() or path.read_bytes()!=body:
                raise ValueError('Stale Sanctuary grove asset: '+str(path.relative_to(ROOT)))
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
    print(('Verified' if check else 'Built')+' native Sanctuary memorial grove modules')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
