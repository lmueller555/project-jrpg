"""Register new hall/bedroom art against the existing Sanctuary gameplay layout."""
from pathlib import Path
import hashlib
import json
import math

from PIL import Image, ImageDraw
if __package__:
    from .build_sanctuary_dining_hd import cell,export_sprite,save
else:
    from build_sanctuary_dining_hd import cell,export_sprite,save

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/sanctuary_home_hd'
OUT=ROOT/'assets/terrain/eldenmere/sanctuary_home_hd'
DINING=ROOT/'assets/terrain/eldenmere/sanctuary_dining_hd'


def architecture(original,layout,room):
    size=tuple(v*2 for v in original['size_pixels']);w,h=size
    shell=Image.new('RGBA',size,'#24302d')
    def part(name):return Image.open(DINING/f'architecture/{name}.png').convert('RGBA')
    floor,plaster,beam,rail,side,window,threshold=[part(name) for name in
        ('floor_tile','plaster_tile','upright','rail','cutaway','window','threshold')]
    for y in range(144,h-48,96):
        for x in range(48,w-48,96):shell.alpha_composite(floor,(x,y))
    for x in range(48,w-48,96):shell.alpha_composite(plaster,(x,48))
    for y in (48,132,h-48):
        left,right=(24,w-24) if y==h-48 else (48,w-48)
        for x in range(left,right,192):shell.alpha_composite(rail.crop((0,0,min(192,right-x),12)),(x,y))
    for x in (40,w//2-6,w-60):shell.alpha_composite(beam,(x,48))
    for x in (24,w-48):
        for y in range(48,h-48,96):shell.alpha_composite(side,(x,y))
    if room=='hall':
        for x,y in layout['windows']:shell.alpha_composite(window,(x*2,y*2))
    entry=layout['entry_rect'];entry_width=entry[2]*2
    sill=threshold.resize((entry_width,16),Image.Resampling.NEAREST)
    shell.alpha_composite(sill,(entry[0]*2,entry[1]*2))
    return shell


def door_poses(atlas, recess=None, sill_colors=None):
    """Five registered leaves over one shallow, orthogonal timber passage.

    Artwork coordinates are native 2x pixels. The 24x36 world portal,
    west hinge and existing travel sensor stay fixed. The darkened adjoining
    floor is architectural context, not a miniature room or extra walkable area.
    """
    closed=export_sprite(cell(atlas,12,4),(48,72),fit=False)
    frame=export_sprite(cell(atlas,13,4),(48,72),fit=False)
    if recess is None:
        passage=Image.new('RGBA',(48,72),'#24302d')
        d=ImageDraw.Draw(passage)
        # A quiet shaded interior beyond the frame, with straight vertical returns.
        d.rectangle((4,6,43,67),fill='#574c3d')
        d.rectangle((7,10,40,43),fill='#625847')
        d.rectangle((7,39,40,43),fill='#453a2d')
        d.line((8,39,39,39),fill='#79684e')
        # Horizontal plank tops continue back from the threshold without converging.
        for row,y in enumerate(range(44,68,6)):
            d.rectangle((7,y,40,min(y+5,67)),fill=('#6c563d','#725b40')[row%2])
            d.line((7,y,40,y),fill='#42392c')
            d.line((10,y+1,38,y+1),fill='#857052')
            seam=19 if row%2 else 31
            d.line((seam,y+1,seam,y+5),fill='#54432f')
        d.rectangle((4,6,6,67),fill='#302a23')
        d.line((7,10,7,67),fill='#887050')
        d.rectangle((41,6,43,67),fill='#3f3427')
        d.line((40,10,40,67),fill='#756247')
    else:
        if recess.mode != 'RGBA' or recess.size != (48,72):
            raise ValueError('Doorway recess must match the native portal canvas')
        passage=recess.copy()
    sill,sill_light,sill_mid,sill_shadow=sill_colors or ('#40382c','#c3b18a','#a18e69','#827052')
    # Retained source cap/jambs are fixed across every pose, drawn in front.
    passage.alpha_composite(frame)
    leaf=closed.crop((4,6,44,70))
    frames=[]
    for width in (40,32,23,12,3):
        image=passage.copy()
        image.alpha_composite(leaf.resize((width,64),Image.Resampling.NEAREST),(4,6))
        # Stable sill remains visible below the opening/leaf in every state.
        edge=ImageDraw.Draw(image)
        edge.rectangle((4,68,43,71),fill=sill)
        edge.line((5,68,42,68),fill=sill_light)
        edge.line((5,69,42,69),fill=sill_mid)
        edge.line((5,70,42,70),fill=sill_shadow)
        frames.append(image)
    return frames

def build():
    recipe=json.loads((SOURCE/'recipe.json').read_text())
    atlas_path=SOURCE/'props_atlas.png'
    if hashlib.sha256(atlas_path.read_bytes()).hexdigest()!=recipe['source_sha256']:
        raise ValueError('Update the extraction recipe before changing retained source art')
    atlas=Image.open(atlas_path).convert('RGBA')
    shared=json.loads((ROOT/recipe['shared_bank']).read_text())['legacy_replacements']
    replacements=dict(shared);exports=[]
    for item in recipe['props']:
        size=tuple(v*2 for v in item['logical_size']);bounds=tuple(v*2 for v in item['logical_bounds'])
        image=export_sprite(cell(atlas,item['cell'],4),size,bounds)
        path=save(image,OUT/f"props/{item['id']}.png")
        replacements[item['legacy_path']]=path
        exports.append({**item,'image':path,'artwork_size':list(size),'artwork_pixels_per_world_pixel':2})
    door_frames=[save(image,OUT/f'doors/frame_{index+1:02}.png')
                 for index,image in enumerate(door_poses(atlas))]
    window=str((DINING/'architecture/window.png').relative_to(ROOT))
    manifest_rooms={}
    for name,spec in recipe['rooms'].items():
        original=spec['original_map'];map_path=ROOT/spec['map'];data=json.loads(map_path.read_text())
        if hashlib.sha256((ROOT/data['collision']).read_bytes()).hexdigest()!=spec['collision_sha256']:
            raise ValueError(f'{name}: collision changed; review asset registration first')
        shell=architecture(original,spec['layout'],name)
        ground=save(shell.convert('RGB'),OUT/f'{name}/ground.png')
        data['artwork_pixels_per_world_pixel']=2
        data['art_bank']=(OUT/'manifest.json').relative_to(ROOT).as_posix()
        data['ground_frames']=[ground for _ in original['ground_frames']]
        data['art_replacements']={p:{'file':r,'artwork_pixels_per_world_pixel':2} for p,r in replacements.items()}
        originals={e['id']:e for e in original['entities']}
        generated={f'{name}_daylight','bedroom_window'}
        data['entities']=[e for e in data['entities'] if e['id'] not in generated]
        for entity in data['entities']:
            if entity['id'] not in originals:continue
            entity['frames']=[replacements[p] for p in originals[entity['id']]['frames']]
            entity['artwork_pixels_per_world_pixel']=2
        # Retain one architecture frame; animate a small registered light mask.
        old=ROOT/f'assets/terrain/eldenmere/sanctuary_interior/{name}/daylight_mask.png'
        mask=Image.open(old).convert('L').resize(shell.size,Image.Resampling.NEAREST)
        bounds=mask.getbbox();lights=[]
        if bounds:
            for index in range(9):
                strength=.08+.045*(1+math.sin(index*math.tau/9))
                overlay=Image.new('RGBA',shell.size,'#f2d7a0')
                overlay.putalpha(mask.point(lambda a:round(a*strength)))
                lights.append(save(overlay.crop(bounds),OUT/f'{name}/daylight_{index:02}.png'))
            data['entities'].append({'id':name+'_daylight','position':[bounds[0]//2,bounds[1]//2],
                'sort_y':-1,'sort_priority':0,'frames':lights,'frame_duration_ms':600,'phase_offset':0,
                'reduced_motion_frame':0,'artwork_pixels_per_world_pixel':2})
        for door in data['doors']:
            if door['id'] in ('bedroom','dining') and name=='hall':
                door['frames']=door_frames;door['artwork_pixels_per_world_pixel']=2
        if name=='bedroom':
            data['entities'].append({'id':'bedroom_window','position':spec['layout']['windows'][0],
                'sort_y':0,'sort_priority':0,'frames':[window],'frame_duration_ms':300,
                'phase_offset':0,'artwork_pixels_per_world_pixel':2})
            # The original story anchor already supplied this line/approach,
            # but the compiled map omitted its destination entirely.
            anchor=next(a for a in spec['layout']['story_anchors'] if a['id']=='window')
            data['destinations']['window']=anchor['access']
            cue_specs=[('books','books',[72,72,48,12],[16,8]),
                       ('notes','notes',[168,126,48,18],[15,8]),
                       ('drawing','drawing',[36,72,32,10],[16,10]),
                       ('wardrobe','wardrobe',[204,90,48,18],[28,24]),
                       ('window','bedroom_window',[168,72,24,12],[9,12])]
            ids={key for key,_,_,_ in cue_specs}
            data['interaction_cues']=[r for r in data.get('interaction_cues',[]) if r['id'] not in ids]
            data['interaction_cues'].extend({'id':key,'entity':entity,
                'available_when':'bedroom_inspect_'+key,'interaction_boundary':boundary,
                'glint_anchor':glint} for key,entity,boundary,glint in cue_specs)
        map_path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
        manifest_rooms[name]={'map':spec['map'],'logical_size':original['size_pixels'],
                             'collision_sha256':spec['collision_sha256'],'ground':ground}
    manifest={'version':1,'status':'integrated','artwork_pixels_per_world_pixel':2,
        'rooms':manifest_rooms,'props':exports,'shared_bank':recipe['shared_bank'],
        'recipe':str((SOURCE/'recipe.json').relative_to(ROOT)),
        'source_sha256':recipe['source_sha256'],'doors':door_frames,'character_banks_migrated':False}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Exported hall and bedroom, fourteen registered prop drawings, shared furnishings and five door poses.')


if __name__=='__main__':build()
