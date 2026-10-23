"""Assemble compact/wide cottages from approved bays and exact animation layers."""
from copy import deepcopy
from pathlib import Path
from random import Random
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, enlarged, save_loop

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/cottage_shapes'
OUTPUT=ROOT/'assets/terrain/eldenmere/cottage_shapes'
BASE=OUTPUT.parent/'cottage'
PREVIOUS=OUTPUT.parent/'cottage_variants'
GROUND=OUTPUT.parent/'grass_dirt'


def opened(path):
    return Image.open(path).convert('RGBA')


def shifted(image,size,offset):
    result=Image.new('RGBA',tuple(size));result.paste(image,tuple(offset));return result


def repair_left_features(structure,wall,shape):
    """Remove the unused window before deleting its bay, including its five-pixel tail."""
    result=structure.copy();x,y,right,bottom=shape['remove_left_features_rect']
    patch=Image.new('RGBA',(right-x,bottom-y));plaster=wall.crop(shape['plaster_sample_rect'])
    for xx in range(0,patch.width,plaster.width):patch.paste(plaster,(xx,0))
    stone=wall.crop(shape['stone_sample_rect'])
    for xx in range(0,patch.width,stone.width):patch.paste(stone,(xx,plaster.height))
    result.paste(patch,(x,y))
    return result,patch


def structure_parts(directory,shape):
    base=opened(directory/'structure.png');width,height=shape['prefab_size']
    parts=[];provenance={}
    if shape['id']=='compact':
        repaired,_=repair_left_features(base,opened(directory/'parts/wall_blank.png'),shape)
        left,right=shape['remove_band']
        parts=[('west',repaired.crop((0,0,left,height)),[0,0]),
               ('east',repaired.crop((right,0,120,height)),[left,0]),
               ('flower_box',opened(directory/'closed.png').crop(shape['flower_source_rect']),shape['flower_position'])]
        provenance={'removed_band':shape['remove_band'],'removed_left_features':shape['remove_left_features_rect'],
                    'repair_material':'parts/wall_blank.png','flower_source':{'image':'closed.png','rect':shape['flower_source_rect']}}
    else:
        x=shape['insert_x']
        parts=[('west',base.crop((0,0,x,height)),[0,0]),('east',base.crop((x,0,120,height)),[x+24,0]),
               ('roof_insert',opened(directory/'parts/roof_repeat.png'),shape['roof_insert_position']),
               ('wall_insert',opened(directory/'parts/wall_blank.png'),shape['wall_insert_position']),
               ('extra_window',opened(directory/'parts/window_right.png'),shape['extra_window_position'])]
        provenance={'insert_x':x,'insert_width':24,'roof_source':'parts/roof_repeat.png',
                    'wall_source':'parts/wall_blank.png','window_source':'parts/window_right.png'}
    image=Image.new('RGBA',(width,height))
    for _,part,position in parts:image.alpha_composite(part,tuple(position))
    return image,parts,provenance


def export_house(recipe,shape,palette):
    source=ROOT/palette['path'];output=OUTPUT/shape['id']/palette['id']
    for folder in ('parts','doors','lantern','smoke','preview_frames'):(output/folder).mkdir(parents=True,exist_ok=True)
    structure,parts,provenance=structure_parts(source,shape);structure.save(output/'structure.png')
    records=[]
    for name,image,position in parts:
        path=f'parts/{name}.png';image.save(output/path);records.append({'id':name,'image':path,'position':position,'size':list(image.size)})
    offset=shape['animation_offset'];size=shape['prefab_size'];width,height=size
    for folder,count in (('doors',5),('lantern',18),('smoke',18)):
        for phase in range(count):
            shifted(opened(source/f'{folder}/frame_{phase+1:02}.png'),size,offset).save(output/f'{folder}/frame_{phase+1:02}.png')
    sheet=Image.new('RGBA',(width*5,height));lamp=opened(output/'lantern/frame_01.png')
    for phase in range(5):
        frame=structure.copy();frame.alpha_composite(opened(output/f'doors/frame_{phase+1:02}.png'));frame.alpha_composite(lamp)
        sheet.paste(frame,(phase*width,0))
        if phase in (0,4):frame.save(output/('closed.png' if phase==0 else 'open.png'))
    sheet.save(output/'door_sheet.png')
    schedule=read_json(BASE/'review_scene.json')['frames'];frames=[]
    for phase,timing in enumerate(schedule):
        frame=structure.copy()
        for path in (f"doors/frame_{timing['door_frame']+1:02}.png",f'lantern/frame_{phase+1:02}.png',f'smoke/frame_{phase+1:02}.png'):
            frame.alpha_composite(opened(output/path))
        frame.save(output/f'preview_frames/frame_{phase+1:02}.png');frames.append(frame)
    materials=read_json(source/'palette.json');materials['status']=recipe['status'];write_json(output/'palette.json',materials)
    meta=deepcopy(read_json(source/'cottage.json'));meta.update({'id':f"eldenmere.cottage.{shape['id']}.{palette['id']}.24",'status':recipe['status'],
        'shape':shape['id'],'palette_name':palette['name'],'prefab_size':size,'ground_rect':shape['ground_rect'],'components':records,
        'window_rects':shape['window_rects'],'window_count':len(shape['window_rects']),
        'source_from_repo_root':palette['path'],'assembly':provenance,'animation_offset_from_source':offset,
        'recipe':'../../../../../source/terrain/eldenmere/cottage_shapes/recipe.json'})
    meta.pop('reusable_inserts',None)
    meta['door']['position'][0]+=offset[0]
    for f in meta['smoke']['frames']:
        for p in f['particles']:
            p['center'][0]+=offset[0];p['center'][1]+=offset[1]
    write_json(output/'cottage.json',meta)
    return frames


def path_cells(recipe):
    cells={(8,y) for y in range(34,53)}
    for shape in recipe['shapes']:
        columns=[]
        for x,y in shape['scene_positions']:
            column=(x+60+shape['animation_offset'][0])//24;columns.append(column)
            cells.add((column,shape['path_row']-1))
        cells.update((x,shape['path_row']) for x in range(min(columns),max(columns)+1))
    return cells


def backgrounds(recipe):
    width,height=recipe['scene_size'];gm=read_json(GROUND/'tileset.json');rng=Random(recipe['scene_seed'])
    grass=[opened(GROUND/p) for p in gm['grass']['images']];ids=[[rng.randrange(4) for _ in range(width)] for _ in range(height)]
    ground=Image.new('RGBA',(width*24,height*24))
    for y,row in enumerate(ids):
        for x,index in enumerate(row):ground.paste(grass[index],(x*24,y*24))
    tiles={t['mask']:opened(GROUND/t['image']) for t in gm['tiles']};cells=path_cells(recipe);joins=cells|{tuple(p) for p in recipe['path_join_cells']}
    offsets=((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1));paths=Image.new('RGBA',ground.size)
    for x,y in sorted(cells):
        raw=sum(1<<i for i,(dx,dy) in enumerate(offsets) if (x+dx,y+dy) in joins)
        mask=gm['tiles'][gm['lookup_256'][raw]]['mask'];paths.alpha_composite(tiles[mask],(x*24,y*24))
    fill=opened(GROUND/gm['dirt_interiors']['images'][0]);x,y,w,h=recipe['connector_apron']
    paths.alpha_composite(fill.crop((8,0,8+w,h)),(x,y));paths.save(OUTPUT/'review_path.png')
    return ground,paths,ids


def review_boards(recipe,frames):
    comparisons=[];palettes=[]
    base=[opened(BASE/f'preview_frames/frame_{p+1:02}.png') for p in range(18)]
    for phase in range(18):
        board=Image.new('RGB',(1536,704),'#e8edf2');d=ImageDraw.Draw(board);d.fontmode='1'
        d.text((16,14),f"Cottage sizes / {recipe['status']} / unchanged 4x pixel scale",fill='#243529',font_size=23)
        for name,image,x in (('Compact / 3 x 3',frames['compact','slate'][phase],16),
                             ('Approved base / 4 x 3',base[phase],440),('Wider / 5 x 3',frames['wide','slate'][phase],944)):
            d.text((x,60),name,fill='#243529',font_size=21)
            tile=Image.new('RGBA',image.size,'#70935a');tile.alpha_composite(image);board.paste(enlarged(tile.convert('RGB'),4),(x,104))
        comparisons.append(board)
        board=Image.new('RGB',(1824,1040),'#e8edf2');d=ImageDraw.Draw(board);d.fontmode='1'
        d.text((16,14),f"Compact and wider cottages / all four approved palettes / shapes: {recipe['status']} / 3x",fill='#243529',font_size=24)
        for row,shape in enumerate(recipe['shapes']):
            for col,palette in enumerate(recipe['palettes']):
                image=frames[shape['id'],palette['id']][phase];x=col*456+12;y=56+row*484
                d.text((x,y),f"{shape['id'].capitalize()} / {palette['id']}",fill='#243529',font_size=19)
                tile=Image.new('RGBA',(144,144),'#70935a');tile.alpha_composite(image,((144-image.width)//2,0))
                board.paste(enlarged(tile.convert('RGB'),3),(x,y+36))
        palettes.append(board)
    for name,images in (('sizes_review',comparisons),('palettes_review',palettes)):
        images[0].save(OUTPUT/f'{name}.png');save_loop(OUTPUT/f'{name}.gif',images,recipe)


def build():
    recipe=read_json(SOURCE/'recipe.json');OUTPUT.mkdir(exist_ok=True);(OUTPUT/'scene_frames').mkdir(exist_ok=True)
    frames={}
    for shape in recipe['shapes']:
        for palette in recipe['palettes']:frames[shape['id'],palette['id']]=export_house(recipe,shape,palette)
    ground,paths,grass_ids=backgrounds(recipe);instances=[]
    for shape in recipe['shapes']:
        for palette,position in zip(recipe['palettes'],shape['scene_positions'],strict=True):
            instances.append({'shape':shape['id'],'palette':palette['id'],'position':position,
                              'foot':[position[0]+60+shape['animation_offset'][0],position[1]+142],
                              'ground_elevation_pixels':recipe['ground_elevation_pixels'],'threshold_elevation_pixels':recipe['ground_elevation_pixels'],
                              'metadata':f"{shape['id']}/{palette['id']}/cottage.json"})
    scenes=[];closeups=[];records=[]
    for phase in range(18):
        scene=ground.copy();scene.paste(opened(PREVIOUS/f'scene_frames/frame_{phase+1:02}.png'),(0,0));scene.alpha_composite(paths)
        for instance in instances:scene.alpha_composite(frames[instance['shape'],instance['palette']][phase],tuple(instance['position']))
        native=scene.convert('RGB');path=f'scene_frames/frame_{phase+1:02}.png';native.save(OUTPUT/path)
        scenes.append(enlarged(native,recipe['scene_scale']));closeups.append(enlarged(native.crop(recipe['courtyard_crop']),recipe['courtyard_scale']))
        records.append({'image':path,'base_phase':phase,'duration_ms':recipe['duration_ms']})
    for name,images in (('review_scene',scenes),('courtyard_closeup',closeups)):
        images[0].save(OUTPUT/f'{name}.png');save_loop(OUTPUT/f'{name}.gif',images,recipe)
    review_boards(recipe,frames)
    write_json(OUTPUT/'shapes.json',{'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],
        'shapes':[{'id':s['id'],'prefab_size':s['prefab_size'],'ground_rect':s['ground_rect'],'window_count':len(s['window_rects'])} for s in recipe['shapes']],
        'palettes':[p['id'] for p in recipe['palettes']],'instances':instances,'frame_count':18,'duration_ms':200,
        'review':{'sizes':'sizes_review.gif','palettes':'palettes_review.gif','scene':'review_scene.gif','courtyard':'courtyard_closeup.gif'}})
    write_json(OUTPUT/'review_scene.json',{'status':recipe['status'],'purpose':'Cottage shape/palette art review; not a game level or canonical village layout',
        'base_scene':'../cottage_variants/review_scene.json','grid_size':recipe['scene_size'],'grass_variants':grass_ids,
        'path_cells':[list(p) for p in sorted(path_cells(recipe))],'path_join_cells':recipe['path_join_cells'],'connector_apron':recipe['connector_apron'],
        'instances':instances,'frames':records,'loop':True,'cycle_duration_ms':3600,'door_use_is_demonstration_only':True,
        'review':{'scene_scale':recipe['scene_scale'],'courtyard_crop':recipe['courtyard_crop'],'courtyard_scale':recipe['courtyard_scale']}})
    print(f"Built {recipe['status']} compact and wider cottages in all four palettes; approved animation layers translated intact")

if __name__=='__main__':build()
