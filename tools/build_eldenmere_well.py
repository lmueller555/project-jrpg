"""Export the new well and apply its local square to the runtime town.

Approved source buildings, terrain, characters and narrative are read-only.
"""
from pathlib import Path
import json

from PIL import Image

import build_eldenmere_town as town
from build_eldenmere_blockout import cells
from build_eldenmere_terrain import BITS, OFFSETS, normalize_mask

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/well'
OUTPUT=ROOT/'assets/terrain/eldenmere/well'
NAV=ROOT/'assets/maps/eldenmere/well_square'


def read(path):return json.loads(path.read_text())
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def save(path,image):path.parent.mkdir(parents=True,exist_ok=True);image.save(path)
def rgba(value):return tuple(bytes.fromhex(value[1:]))+(255,)


def export_art():
    recipe=read(SOURCE/'recipe.json')
    materials=read(ROOT/recipe['palette_source'])['materials']
    groups=('stone','wood','iron','roof','water','grass','glass')
    colors=[rgba('#45382d'),rgba('#34362f')]
    colors.extend(rgba(c) for name in groups for c in materials[name].values())
    reference=Image.open(SOURCE/recipe['source']).convert('RGBA')
    alpha=reference.getchannel('A').point(lambda a:255 if a>=recipe['alpha_threshold'] else 0)
    reference.putalpha(alpha);crop=alpha.getbbox()
    sample=reference.crop(crop).resize(tuple(recipe['native_size']),Image.Resampling.NEAREST)
    sprite=Image.new('RGBA',tuple(recipe['frame_size']))
    ox,oy=recipe['native_offset']
    cache={}
    for y in range(sample.height):
        for x in range(sample.width):
            pixel=sample.getpixel((x,y))
            if not pixel[3]:continue
            rgb=pixel[:3]
            if rgb not in cache:cache[rgb]=min(colors,key=lambda c:sum((a-b)**2 for a,b in zip(rgb,c[:3])))
            sprite.putpixel((ox+x,oy+y),cache[rgb])
    mask=Image.new('L',sprite.size)
    x,y,w,h=recipe['water_sample_rect']
    water_colors={rgba(c) for c in materials['water'].values()}
    pixels=[]
    for yy in range(y,y+h):
        for xx in range(x,x+w):
            if sprite.getpixel((xx,yy)) in water_colors:
                mask.putpixel((xx,yy),255);pixels.append((xx,yy))
    if len(pixels)<4:raise ValueError('Well water landmarks need adjustment')
    save(SOURCE/'parts/native_structure.png',sprite)
    save(SOURCE/'parts/water_mask.png',mask)
    save(OUTPUT/'structure.png',sprite)
    frames=[]
    for phase in range(recipe['water_frame_count']):
        image=sprite.copy()
        # Small moving glints only in the shaft water. Roof, stonework, rope,
        # hanging bucket and hand-operated crank stay still until used.
        for xx,yy in pixels:
            if (xx+phase*2)%13 in (0,1) and (yy+phase)%5==0:
                image.putpixel((xx,yy),rgba(materials['water']['reflection']))
            elif (xx+phase*2)%13==4 and (yy+phase)%5==1:
                image.putpixel((xx,yy),rgba(materials['water']['base']))
        save(OUTPUT/f'frames/frame_{phase+1:02}.png',image);frames.append(image)
    write(OUTPUT/'well.json',{
        'id':recipe['id'],'status':recipe['status'],'tile_size':24,
        'frame_size':recipe['frame_size'],'position':recipe['position'],
        'ground_rect':recipe['ground_rect'],'sort_y':recipe['sort_y'],
        'frames':[f'frames/frame_{i+1:02}.png' for i in range(len(frames))],
        'frame_duration_ms':recipe['water_duration_ms'],'cycle_duration_ms':len(frames)*recipe['water_duration_ms'],
        'drawing_position':recipe['drawing_position'],'source_crop':crop,
        'source_recipe':'../../../source/terrain/eldenmere/well/recipe.json',
        'animation':'gentle water glints inside the shaft; structure and windlass fixed',
        'palette_source':recipe['palette_source'],'draw_water_interaction':False
    })
    background=Image.new('RGBA',sprite.size,'#e8edf2');background.alpha_composite(sprite)
    save(OUTPUT/'well_review.png',background.convert('RGB').resize((504,576),Image.Resampling.NEAREST))
    print(f'Exported well: {sprite.size}, {len(pixels)} water pixels, six 200ms phases')


def plaza_cells(recipe):
    x,y,w,h=recipe['plaza_rect_tiles']
    return {(xx,y+row) for row,inset in enumerate(recipe['plaza_row_insets']) for xx in range(x+inset,x+w-inset)}


def apply_square(base,grass):
    """Merge a rounded dirt square and connector using the existing 47 blobs."""
    recipe=read(SOURCE/'recipe.json')
    foundation=read(ROOT/'assets/maps/eldenmere/terrain_foundation/scene.json')
    workshop=read(ROOT/'assets/source/terrain/eldenmere/workshop/recipe.json')
    dirt={tuple(r['cell']) for r in foundation['ground']['dirt_cells']}
    dirt|=cells(workshop['apron_tiles'])
    additions=plaza_cells(recipe)|cells(recipe['south_connector_tiles'])
    added=additions-dirt;dirt|=additions
    affected={(x+dx,y+dy) for x,y in added for dx in (-1,0,1) for dy in (-1,0,1)}
    pack=ROOT/'assets/terrain/eldenmere/grass_dirt';meta=read(pack/'tileset.json')
    tiles={r['mask']:town.opened(pack/r['image']) for r in meta['tiles']}
    fills=[town.opened(pack/p) for p in meta['dirt_interiors']['images']]
    result=base.copy()
    for x,y in sorted(affected):
        pos=(x*24,y*24);result.paste(grass.crop((*pos,pos[0]+24,pos[1]+24)),pos)
        if (x,y) not in dirt:continue
        raw=sum(BITS[n] for n,(dx,dy) in OFFSETS.items() if (x+dx,y+dy) in dirt)
        mask=normalize_mask(raw)
        tile=fills[(x+2*y)%len(fills)] if mask==255 else tiles[mask]
        result.alpha_composite(tile,pos)
    paving=town.opened(ROOT/recipe['paving_source'])
    for pos in recipe['paving_positions']:result.alpha_composite(paving,tuple(pos))
    write(NAV/'layout.json',{
        'id':recipe['id'],'status':recipe['status'],'plaza_rect_tiles':recipe['plaza_rect_tiles'],
        'well_ground_rect':recipe['ground_rect'],'well_position':recipe['position'],
        'south_connector_tiles':recipe['south_connector_tiles'],
        'added_dirt_cells':[list(p) for p in sorted(added)],
        'retiled_cells':[list(p) for p in sorted(affected)],
        'paving_source':recipe['paving_source'],'paving_positions':recipe['paving_positions'],
        'approaches':recipe['approaches'],'gathering_rect':recipe['gathering_rect'],
        'original_plan':'assets/maps/eldenmere/terrain_foundation/adapted_plan.json',
        'source_recipe':'assets/source/terrain/eldenmere/well/recipe.json'
    })
    return result


def entity():
    recipe=read(SOURCE/'recipe.json')
    meta=read(OUTPUT/'well.json')
    return {'id':'well','position':recipe['position'],'sort_y':recipe['sort_y'],
            'frames':[town.opened(OUTPUT/p) for p in meta['frames']]}


def collision_and_routes(collision):
    recipe=read(SOURCE/'recipe.json');x,y,w,h=recipe['ground_rect']
    collision=collision.copy();collision.paste(255,(x,y,x+w,y+h))
    allowed=town.opened(ROOT/'assets/terrain/eldenmere/workshop/navigation/allowed_routes.png').convert('L')
    for key in ('plaza_rect_tiles','south_connector_tiles'):
        x,y,w,h=recipe[key];allowed.paste(255,(x*24,y*24,(x+w)*24,(y+h)*24))
    save(NAV/'allowed_routes.png',allowed)
    return collision


if __name__=='__main__':export_art()
