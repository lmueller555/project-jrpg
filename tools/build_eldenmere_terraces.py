"""Assemble native fieldstone modules, four-tread stairs and a water-only loop."""

from copy import deepcopy
from pathlib import Path
from random import Random

from PIL import Image, ImageDraw

from build_eldenmere_stream import read_json, write_json, rgba, enlarged, save_loop

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/terrain/eldenmere/terraces'
OUTPUT = ROOT / 'assets/terrain/eldenmere/terraces'
GROUND = OUTPUT.parent / 'grass_dirt'
IRRIGATION = OUTPUT.parent / 'irrigation'


def quantize(sample, palette, moss=True):
    """Retain generated shapes, map their pixels to named material ramps."""
    result = Image.new('RGBA', sample.size)
    stones = [rgba(v) for v in palette['stone'].values()]
    greens = [rgba(v) for v in palette['grass'].values()]
    for y in range(sample.height):
        for x in range(sample.width):
            c = sample.getpixel((x, y))[:3]
            ramp = greens if moss and c[1] > c[0] + 4 and c[1] > c[2] + 8 else stones
            result.putpixel((x, y), min(ramp, key=lambda p: sum((a-b)**2 for a,b in zip(c,p))))
    return result


def extract_parts(recipe, palette):
    reference = Image.open(SOURCE / recipe['source']).convert('RGB')
    parts = SOURCE / 'parts'; parts.mkdir(exist_ok=True)
    wall = quantize(reference.crop(recipe['wall_crop']).resize(tuple(recipe['wall_sample_size']), Image.Resampling.NEAREST), palette)
    stairs = quantize(reference.crop(recipe['stairs_crop']).resize((48,48), Image.Resampling.NEAREST), palette, False)
    wall.save(parts / 'wall_material.png'); stairs.save(parts / 'stairs_material.png')
    glyphs = []
    for name,size,key in [('fall',(2,6),'fall_glyph_crop'),('ripple',(12,3),'ripple_glyph_crop')]:
        sample = reference.crop(recipe[key]).resize(size, Image.Resampling.NEAREST)
        glyph = Image.new('RGBA',size)
        for y in range(size[1]):
            for x in range(size[0]):
                c = sample.getpixel((x,y))
                if sum(c) / 3 > recipe['glyph_thresholds'][name] and c[1] >= c[0]:
                    glyph.putpixel((x,y),(255,255,255,255))
        if glyph.getbbox() is None:
            raise ValueError(f'Empty source glyph: {name}')
        glyph.save(parts / f'{name}_mask.png'); glyphs.append(glyph)
    return wall, stairs, glyphs


def seam_color(y, stone):
    if y == 0: return stone['shadow']
    if y in (1,2,3): return stone['cap']
    if y == 4: return stone['highlight']
    if y in (5,11,17,23): return stone['joint']
    return stone['base']


def wall_modules(material, palette):
    stone = palette['stone']; tiles = {}
    for variant,offset in enumerate((0,12,24)):
        tile = material.crop((offset,0,offset+24,24))
        draw = ImageDraw.Draw(tile)
        # Identical boundary profiles permit arbitrary mixing of straight variants.
        for y in range(24):
            for x in (0,23): tile.putpixel((x,y),rgba(seam_color(y,stone)))
        for y,key in ((0,'shadow'),(1,'cap'),(4,'highlight'),(5,'joint')):
            draw.line((0,y,23,y), fill=stone[key])
        # A few grass blades overhang coping; they never touch module seams.
        if variant == 1:
            draw.line((16,0,19,0), fill=palette['grass']['shadow'])
            draw.point((17,1),fill=palette['grass']['base'])
        tiles[f'wall_front_{variant:02}'] = tile
    for side in ('left','right'):
        mirror = side == 'right'
        corner = tiles['wall_front_00'].copy(); d = ImageDraw.Draw(corner)
        d.rectangle((0,5,3,23),fill=stone['shadow'])
        d.line((0,0,0,23),fill=stone['joint'])
        for y in (5,11,17,23): d.line((0,y,3,y),fill=stone['joint'])
        d.line((1,1,3,1),fill=stone['light'])
        tiles[f'wall_outer_{side}'] = corner.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if mirror else corner
        inner = tiles['wall_front_00'].copy(); d = ImageDraw.Draw(inner)
        d.rectangle((0,0,4,23),fill=stone['shadow'])
        d.rectangle((0,0,2,23),fill=stone['cap'])
        d.line((3,0,3,23),fill=stone['light'])
        d.line((5,6,5,23),fill=stone['joint'])
        for y in (7,15,23): d.line((0,y,4,y),fill=stone['joint'])
        tiles[f'wall_inner_{side}'] = inner.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if mirror else inner
        end = tiles['wall_front_02'].copy(); d = ImageDraw.Draw(end)
        d.line((0,1,0,23),fill=stone['joint']); d.line((1,2,1,22),fill=stone['light'])
        tiles[f'wall_end_{side}'] = end.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if mirror else end
        edge = Image.new('RGBA',(24,24)); d = ImageDraw.Draw(edge)
        d.rectangle((0,0,5,23),fill=stone['shadow']); d.rectangle((0,0,2,23),fill=stone['cap'])
        d.line((3,0,3,23),fill=stone['light'])
        for y in (7,15,23): d.line((0,y,5,y),fill=stone['joint'])
        tiles[f'wall_side_{side}'] = edge.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if mirror else edge
    back = Image.new('RGBA',(24,24)); d = ImageDraw.Draw(back)
    d.rectangle((0,0,23,3),fill=stone['cap']); d.line((0,4,23,4),fill=stone['shadow'])
    d.line((0,0,23,0),fill=stone['light']); d.line((11,0,11,3),fill=stone['shadow'])
    tiles['wall_back'] = back
    for side in ('left','right'):
        corner = tiles[f'wall_side_{side}'].copy(); corner.alpha_composite(back)
        tiles[f'wall_back_{side}'] = corner
    return tiles


def stairs_module(material, palette):
    stairs = material.copy(); d = ImageDraw.Draw(stairs); stone = palette['stone']
    # Four source-derived broad treads, with quiet worn centers and fixed cheeks.
    for y in (8,18,28,38):
        d.line((7,y,40,y),fill=stone['highlight'])
        d.line((7,y+1,40,y+1),fill=stone['light'])
        d.line((7,y+7,40,y+7),fill=stone['shadow'])
        d.line((7,y+8,40,y+8),fill=stone['joint'])
    # Keep top landing and foot open instead of outlining the staircase in black.
    return stairs


def spillway_layers(wall, palette):
    structure = Image.new('RGBA',(24,48)); structure.paste(wall,(0,0))
    mask = Image.new('RGBA',(24,48)); stone = palette['stone']; d = ImageDraw.Draw(structure)
    d.rectangle((6,0,17,6),fill=stone['shadow'])
    d.line((6,0,6,7),fill=stone['cap']); d.line((17,0,17,7),fill=stone['cap'])
    for y in range(48):
        for x in range(24):
            basin = ((x-11.5)/9)**2 + ((y-35)/5)**2 <= 1
            rim = ((x-11.5)/11)**2 + ((y-35)/7)**2 <= 1
            water = (8<=x<16 and y<6 or 10<=x<14 and 6<=y<=35 or basin or 8<=x<16 and y>=35)
            if rim and not basin and not (8<=x<16 and y>=35):
                structure.putpixel((x,y),rgba(stone['cap' if y<35 else 'shadow']))
                if y in (29,40) and 4<x<19:
                    structure.putpixel((x,y),rgba(stone['light']))
            if water:
                mask.putpixel((x,y),(255,255,255,255))
                structure.putpixel((x,y),(0,0,0,0))
            if y>=42 and x in (6,7,16,17):
                structure.putpixel((x,y),rgba(palette['dirt']['edge' if x in (6,17) else 'shadow']))
    return structure,mask


def spillway_frame(structure,mask,phase,recipe,palette,glyphs):
    frame = Image.new('RGBA',(24,48)); water = palette['water']
    frame.paste(Image.new('RGBA',frame.size,rgba(water['base'])),(0,0),mask.getchannel('A'))
    fall,ripple = glyphs
    for y in range(48):
        for x in range(24):
            if not mask.getpixel((x,y))[3]: continue
            edge = x in ((8,15) if y<6 or y>=40 else (10,13))
            if edge: frame.putpixel((x,y),rgba(water['shallow' if y<6 or y>=42 else 'flow']))
            # Same twelve-pixel, two-pixel-per-phase current as the channel pack.
            if y<6 or y>=40:
                if x in (11,12) and (y-phase*2)%12 in (0,1):
                    frame.putpixel((x,y),rgba(water['reflection']))
            elif y<32 and 11<=x<=12:
                t=(y-phase*2)%12
                if t<fall.height and fall.getpixel((x-11,t))[3]:
                    frame.putpixel((x,y),rgba(water['reflection']))
    fx = Image.new('RGBA',frame.size); d = ImageDraw.Draw(fx)
    radius=phase+2
    d.arc((11-radius,35-radius//2,12+radius,36+radius//2),0,180,fill=water['reflection'])
    for x in range(ripple.width):
        for y in range(ripple.height):
            if ripple.getpixel((x,y))[3] and (x+phase)%3:
                fx.putpixel((6+x,33+y),rgba(water['flow']))
    for x,y in ((10-phase%2,32),(13+phase%2,33),(11,31+phase%3)):
        fx.putpixel((x,y),rgba(water['glint']))
    frame.paste(fx,(0,0),Image.frombytes('L',fx.size,bytes(min(a,b) for a,b in zip(fx.getchannel('A').tobytes(),mask.getchannel('A').tobytes()))))
    return Image.alpha_composite(frame,structure)


def channel_placements():
    result=[]
    def add(x,y,incoming,*outgoing):
        bits={'N':1,'E':2,'S':4,'W':8}
        result.append({'cell':[x,y],'route':f"channel_{sum(bits[p] for p in (incoming,*outgoing)):02}_from_{incoming.lower()}"})
    add(14,16,'N','S'); add(14,17,'N','W')
    for x in (13,12): add(x,17,'E','W')
    add(11,17,'E','W','S')
    for x in (10,9,8): add(x,17,'E','W')
    add(7,17,'E','S'); add(7,18,'N','S')
    result.append({'cell':[7,19],'route':'outlet_s'})
    add(11,18,'N','S'); add(11,19,'N','E'); add(12,19,'W','E'); add(13,19,'W','S')
    add(13,22,'N','W'); add(12,22,'E','W'); add(11,22,'E','S')
    result.append({'cell':[11,23],'route':'outlet_s'})
    return result


def scene_spec(recipe):
    previous=read_json(IRRIGATION/'review_scene.json'); rng=Random(112)
    width,height=recipe['scene_size']; grass=deepcopy(previous['grass_variants'][:16])
    grass.extend([[rng.choices(range(4),weights=(5,3,2,1))[0] for x in range(width)] for y in range(height-16)])
    structures=[]
    def place(name,x,y): structures.append({'tile':name,'position':[x*24,y*24]})
    for x in range(6,16): place('wall_back',x,16)
    for side,x in [('left',5),('right',16)]:
        place(f'wall_back_{side}',x,16)
        for y in (17,18,19): place(f'wall_side_{side}',x,y)
        place(f'wall_outer_{side}',x,20)
    for x in range(6,16):
        if x not in (8,9,13): place(f'wall_front_{x%3:02}',x,20)
    characters=deepcopy([c for c in previous['characters'] if c['name'] not in ('mira','female_02')])
    for name,cell in [('mira',(9,18)),('female_02',(8,23))]:
        path=f'assets/characters/{name}/idle_front.png' if name=='mira' else f'assets/characters/npcs/{name}/idle_front.png'
        x,y=cell
        characters.append({'name':name,'image_from_repo_root':path,'position':[x*24,y*24-14],
                           'foot':[x*24+12,y*24+20],'level':'upper' if name=='mira' else 'lower'})
    return {'status':recipe['status'],'purpose':'Terrace art and elevation review; illustrative layout, not canonical geography or gameplay',
            'base_scene':'../irrigation/review_scene.json','preserved_top_rows':16,'grid_size':[width,height],
            'grass_variants':grass,'structures':structures,'stairs':{'position':recipe['stair_position'],'size':[48,48]},
            'spillway':{'position':recipe['spillway_position'],'size':[24,48],'input':'N','output':'S'},
            'upper_ground_elevation_pixels':24,'channels':channel_placements(),'characters':characters,
            'dirt_cells':[[x,y] for x in (8,9) for y in (19,22,23)],
            'dirt_join_cells':[[x,y] for x in (8,9) for y in (20,21)],
            'frames':[{'image':f'review_scene_frame_{i+1:02}.png','duration_ms':200} for i in range(6)],
            'review':{'gif':'review_scene.gif','image':'review_scene.png','scale':recipe['scene_scale'],
                      'closeup_gif':'terrace_closeup.gif','closeup_rect':recipe['closeup_rect'],'closeup_scale':recipe['closeup_scale']}}


def render_scene(spec,tiles,stairs,spillways,phase):
    gm=read_json(GROUND/'tileset.json'); cm=read_json(IRRIGATION/'tileset.json')
    grass=[Image.open(GROUND/p).convert('RGBA') for p in gm['grass']['images']]
    dirt_tiles={t['mask']:Image.open(GROUND/t['image']).convert('RGBA') for t in gm['tiles']}
    records={r['id']:r for r in cm['routes']}
    atlas=Image.open(IRRIGATION/cm['frames'][phase]['image']).convert('RGBA')
    width,height=spec['grid_size']; image=Image.new('RGBA',(width*24,height*24))
    for y,row in enumerate(spec['grass_variants']):
        for x,variant in enumerate(row): image.paste(grass[variant],(x*24,y*24))
    old=Image.open(IRRIGATION/f'review_scene_frame_{phase+1:02}.png').convert('RGBA')
    image.paste(old.crop((0,0,width*24,spec['preserved_top_rows']*24)),(0,0))
    dirt_cells={tuple(p) for p in spec['dirt_cells']}
    connected_dirt=dirt_cells|{tuple(p) for p in spec['dirt_join_cells']}
    offsets=[(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)]
    for x,y in dirt_cells:
        raw=sum(1<<i for i,(dx,dy) in enumerate(offsets) if (x+dx,y+dy) in connected_dirt)
        mask=gm['tiles'][gm['lookup_256'][raw]]['mask']
        image.alpha_composite(dirt_tiles[mask],(x*24,y*24))
    for p in spec['structures']: image.alpha_composite(tiles[p['tile']],tuple(p['position']))
    for p in spec['channels']:
        x,y=p['cell']; a,b,w,h=records[p['route']]['rect']
        image.alpha_composite(atlas.crop((a,b,a+w,b+h)),(x*24,y*24))
    image.alpha_composite(stairs,tuple(spec['stairs']['position']))
    image.alpha_composite(spillways[phase],tuple(spec['spillway']['position']))
    # Upper characters are already in the preserved area; place only the moved pair.
    for c in spec['characters']:
        if 'level' in c:
            image.alpha_composite(Image.open(ROOT/c['image_from_repo_root']).convert('RGBA'),tuple(c['position']))
    return image.convert('RGB')


def build():
    recipe=read_json(SOURCE/'recipe.json')
    palette=deepcopy(read_json(IRRIGATION/'palette.json')['materials']); palette.update(recipe['palette'])
    OUTPUT.mkdir(parents=True,exist_ok=True)
    for directory in ('tiles','frames','spillway'): (OUTPUT/directory).mkdir(exist_ok=True)
    wall,stair_material,glyphs=extract_parts(recipe,palette)
    tiles=wall_modules(wall,palette); stairs=stairs_module(stair_material,palette)
    stairs.save(OUTPUT/'stairs_south.png')
    structure,mask=spillway_layers(tiles['wall_front_01'],palette)
    structure.save(SOURCE/'parts/spillway_structure.png'); mask.save(SOURCE/'parts/spillway_water_mask.png')
    spillways=[spillway_frame(structure,mask,p,recipe,palette,glyphs) for p in range(6)]
    for p,frame in enumerate(spillways): frame.save(OUTPUT/f'spillway/frame_{p+1:02}.png')
    for row in range(2):
        for col in range(2): tiles[f'stairs_south_{row}_{col}']=stairs.crop((col*24,row*24,(col+1)*24,(row+1)*24))
    records=[]
    for name,tile in tiles.items():
        tile.save(OUTPUT/f'tiles/{name}.png')
        index=len(records); records.append({'id':name,'image':f'tiles/{name}.png','animated':False,
                                          'rect':[index%5*24,index//5*24,24,24]})
    for row in range(2):
        index=len(records); records.append({'id':f'spillway_south_{row}','animated':True,
                                          'rect':[index%5*24,index//5*24,24,24], 'prefab_rect':[0,row*24,24,24]})
    assert len(records)==20
    combined=Image.new('RGBA',(120,576)); boards=[]
    for phase in range(6):
        atlas=Image.new('RGBA',(120,96))
        board=Image.new('RGB',(880,836),'#e8edf2'); d=ImageDraw.Draw(board); d.fontmode='1'
        d.text((16,12),f"Eldenmere fieldstone / stairs / spillway / {recipe['status']}",fill='#243529',font_size=22)
        for index,r in enumerate(records):
            tile=tiles[r['id']] if not r['animated'] else spillways[phase].crop((0,r['prefab_rect'][1],24,r['prefab_rect'][1]+24))
            atlas.paste(tile,tuple(r['rect'][:2]))
            bg=Image.open(GROUND/'grass_00.png').convert('RGBA'); bg.alpha_composite(tile)
            x,y=index%5*176+12,index//5*196+48
            board.paste(enlarged(bg.convert('RGB'),6),(x,y)); d.text((x,y+150),r['id'],fill='#243529',font_size=13)
        atlas.save(OUTPUT/f'frames/frame_{phase+1:02}.png'); combined.paste(atlas,(0,phase*96)); boards.append(board)
    combined.save(OUTPUT/'terraces.png'); boards[0].save(OUTPUT/'modules_review.png'); save_loop(OUTPUT/'modules_review.gif',boards,recipe)
    spec=scene_spec(recipe); previews=[]; closeups=[]
    for phase in range(6):
        native=render_scene(spec,tiles,stairs,spillways,phase); native.save(OUTPUT/spec['frames'][phase]['image'])
        previews.append(enlarged(native,recipe['scene_scale']))
        closeups.append(enlarged(native.crop(recipe['closeup_rect']),recipe['closeup_scale']))
    previews[0].save(OUTPUT/'review_scene.png'); closeups[0].save(OUTPUT/'terrace_closeup.png')
    save_loop(OUTPUT/'review_scene.gif',previews,recipe); save_loop(OUTPUT/'terrace_closeup.gif',closeups,recipe)
    write_json(OUTPUT/'review_scene.json',spec); write_json(OUTPUT/'palette.json',{'status':recipe['status'],'materials':palette})
    write_json(OUTPUT/'tileset.json',{'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],
        'image':'terraces.png','columns':5,'rows_per_phase':4,'tiles':records,'wall_height_pixels':24,
        'frames':[{'image':f'frames/frame_{i+1:02}.png','sheet_rect':[0,i*96,120,96],'duration_ms':200} for i in range(6)],
        'loop':True,'cycle_duration_ms':1200,'recipe':'../../../source/terrain/eldenmere/terraces/recipe.json',
        'prefabs':{'stairs_south':{'image':'stairs_south.png','size':[48,48],'treads':4,'walkable_x':[7,41],
                                  'upper_landing':'N','lower_landing':'S','elevation_change_pixels':24},
                   'spillway_south':{'size':[24,48],'input':'N','output':'S','water_width_pixels':8,
                       'frames':[f'spillway/frame_{i+1:02}.png' for i in range(6)],
                       'structure':'../../../source/terrain/eldenmere/terraces/parts/spillway_structure.png',
                       'water_mask':'../../../source/terrain/eldenmere/terraces/parts/spillway_water_mask.png'}},
        'review':{'scene':'review_scene.gif','closeup':'terrace_closeup.gif','modules':'modules_review.gif'}})
    print('Built 14 fieldstone modules, 4 stair quarters and 2 spillway quarters across six synchronized phases')


if __name__=='__main__':
    build()
