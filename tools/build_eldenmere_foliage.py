"""Build source-derived foliage with fixed bark/shadows and local leaf-cluster motion."""
from pathlib import Path
from PIL import Image, ImageDraw
from build_eldenmere_stream import read_json, write_json, rgba, enlarged

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/foliage'
OUTPUT=ROOT/'assets/terrain/eldenmere/foliage'
PREVIOUS=OUTPUT.parent/'cottage_shapes'


def opened(path):return Image.open(path).convert('RGBA')


def save_loop(path,images,recipe):
    # Keep previous pixels and encode differences; decoded frames remain lossless.
    images[0].save(path,save_all=True,append_images=images[1:],duration=recipe['duration_ms'],
                   loop=0,disposal=1,optimize=True)


def nearest(pixel,colors):
    return min(colors,key=lambda c:sum((a-b)**2 for a,b in zip(pixel,c[:3])))


def extract_native(reference,plant,palette):
    sample=reference.crop(plant['source_crop']).resize(tuple(plant['sample_size']),Image.Resampling.NEAREST)
    image=Image.new('RGBA',tuple(plant['frame_size']));ox,oy=plant['sample_position']
    leaves=[rgba(c) for c in palette['leaves'].values()];wood=[rgba(c) for c in palette['wood'].values()]
    for y in range(sample.height):
        for x in range(sample.width):
            r,g,b=sample.getpixel((x,y))
            if r>160 and b>120 and r>g+70 and b>g+70:continue
            bark=r>=g+5 and r>=b+10
            colors=wood if bark else [rgba(palette['shadow']['base'])] if y+oy>=plant['shadow_top'] else leaves
            image.putpixel((x+ox,y+oy),nearest((r,g,b),colors))
    image.save(SOURCE/f"parts/{plant['id']}_native.png")
    return image


def split_layers(native,plant,palette):
    trunk=Image.new('RGBA',native.size);shadow=trunk.copy();canopy=trunk.copy()
    wood={rgba(c) for c in palette['wood'].values()};leaves=[rgba(c) for c in palette['leaves'].values()]
    for y in range(native.height):
        for x in range(native.width):
            pixel=native.getpixel((x,y))
            if not pixel[3]:continue
            destination=trunk if pixel in wood else shadow if y>=plant['shadow_top'] else canopy
            destination.putpixel((x,y),pixel)
    parts=[];used=set()
    for cluster in plant['clusters']:
        x,y,right,bottom=cluster['rect'];w,h=right-x,bottom-y
        mask=Image.new('L',(w,h));d=ImageDraw.Draw(mask)
        d.polygon(((2,0),(w-4,0),(w-1,3),(w-2,h-3),(w-5,h-1),(2,h-2),(0,h//2)),fill=255)
        part=Image.new('RGBA',(w,h))
        for yy in range(h):
            for xx in range(w):
                pixel=native.getpixel((x+xx,y+yy))
                if mask.getpixel((xx,yy)) and pixel in leaves:
                    assert (x+xx,y+yy) not in used,'Leaf clusters must have disjoint source pixels'
                    used.add((x+xx,y+yy));part.putpixel((xx,yy),pixel)
                    canopy.putpixel((x+xx,y+yy),leaves[max(0,leaves.index(pixel)-1)])
        assert part.getbbox(),f"Empty leaf cluster {plant['id']}/{cluster['id']}"
        part.save(SOURCE/f"parts/{plant['id']}_{cluster['id']}.png")
        parts.append(part)
    return trunk,shadow,canopy,parts


def plant_frame(plant,trunk,shadow,canopy,parts,phase):
    image=shadow.copy();image.alpha_composite(canopy)
    for cluster,part,(dx,dy) in zip(plant['clusters'],parts,plant['poses'][phase],strict=True):
        x,y=cluster['rect'][:2];image.alpha_composite(part,(x+dx,y+dy))
    # Woody pixels keep their exact position and color, including branches inside the crown.
    image.alpha_composite(trunk)
    return image


def export_plant(recipe,plant,reference):
    directory=OUTPUT/plant['id'];(directory/'frames').mkdir(parents=True,exist_ok=True);(directory/'clusters').mkdir(exist_ok=True)
    native=extract_native(reference,plant,recipe['palette']);trunk,shadow,canopy,parts=split_layers(native,plant,recipe['palette'])
    for name,image in (('trunk',trunk),('shadow',shadow),('canopy',canopy)):
        image.save(directory/f'{name}.png');image.save(SOURCE/f"parts/{plant['id']}_{name}.png")
    for record,part in zip(plant['clusters'],parts,strict=True):part.save(directory/f"clusters/{record['id']}.png")
    w,h=plant['frame_size'];sheet=Image.new('RGBA',(w*9,h));frames=[];records=[]
    for phase in range(9):
        frame=plant_frame(plant,trunk,shadow,canopy,parts,phase);path=f'frames/frame_{phase+1:02}.png';frame.save(directory/path)
        frames.append(frame);sheet.paste(frame,(phase*w,0))
        records.append({'image':path,'duration_ms':600,'sheet_rect':[phase*w,0,w,h],'cluster_offsets':plant['poses'][phase]})
    assert frames[0].tobytes()==native.tobytes(),'Rest pose must reproduce the source-derived native plant'
    frames[0].save(directory/'idle.png');sheet.save(directory/'sheet.png')
    write_json(directory/'foliage.json',{'id':f"eldenmere.foliage.{plant['id']}.24",'status':recipe['status'],'tile_size':[24,24],
        'frame_size':plant['frame_size'],'ground_rect':plant['ground_rect'],'idle':'idle.png','sheet':'sheet.png',
        'fixed_layers':{'trunk':'trunk.png','shadow':'shadow.png'},'canopy_backing':'canopy.png',
        'clusters':[{'id':c['id'],'image':f"clusters/{c['id']}.png",'position':c['rect'][:2]} for c in plant['clusters']],
        'draw_order':['shadow','canopy_backing','clusters','trunk'],'wind':{'direction':'E','max_displacement_pixels':[1,1],
          'whole_plant_moves':False,'loop':True,'cycle_duration_ms':5400,'frames':records},
        'recipe':'../../../../source/terrain/eldenmere/foliage/recipe.json'})
    return frames


def review_board(recipe,frames):
    hero=opened(ROOT/'assets/characters/caelan/idle_front.png');boards=[]
    for phase in range(9):
        board=Image.new('RGB',(1248,848),'#e8edf2');d=ImageDraw.Draw(board);d.fontmode='1'
        d.text((20,14),f"Eldenmere foliage / {recipe['status']} / 5.4s eastward breeze",fill='#243529',font_size=25)
        d.text((24,52),'Broadleaf tree / 96 x 120 frame / 6x',fill='#243529',font_size=19)
        d.text((824,52),'Shrub / 24 x 24 / 12x',fill='#243529',font_size=19)
        for plant,scale,position in (('tree',6,(24,88)),('shrub',12,(824,88))):
            frame=frames[plant][phase];tile=Image.new('RGBA',frame.size,'#70935a');tile.alpha_composite(frame)
            board.paste(enlarged(tile.convert('RGB'),scale),position)
        d.text((644,454),'Character and shrub below share 6x scale',fill='#243529',font_size=19)
        scale_board=Image.new('RGBA',(88,44),'#70935a');scale_board.alpha_composite(hero,(4,6));scale_board.alpha_composite(frames['shrub'][phase],(52,18))
        board.paste(enlarged(scale_board.convert('RGB'),6),(644,492))
        d.text((644,788),'Fixed bark, roots and ground shadows',fill='#243529',font_size=21)
        boards.append(board)
    boards[0].save(OUTPUT/'foliage_review.png');save_loop(OUTPUT/'foliage_review.gif',boards,recipe)


def build_scene(recipe,frames):
    old=read_json(PREVIOUS/'review_scene.json');full=[];closeups=[];records=[]
    for tick in range(recipe['scene_frame_count']):
        old_phase=tick%18;image=opened(PREVIOUS/f'scene_frames/frame_{old_phase+1:02}.png');placements=[]
        for instance in recipe['instances']:
            phase=(tick//3+instance['phase_offset'])%9;image.alpha_composite(frames[instance['plant']][phase],tuple(instance['position']))
            placements.append(phase)
        native=image.convert('RGB');path=f'scene_frames/frame_{tick+1:02}.png';native.save(OUTPUT/path)
        full.append(enlarged(native,recipe['scene_scale']));closeups.append(enlarged(native.crop(recipe['scene_closeup']),recipe['scene_closeup_scale']))
        records.append({'image':path,'base_phase':old_phase,'foliage_phases':placements,'duration_ms':200})
    scene_timing={'duration_ms':recipe['scene_duration_ms']}
    for name,images in (('review_scene',full),('garden_closeup',closeups)):
        images[0].save(OUTPUT/f'{name}.png');save_loop(OUTPUT/f'{name}.gif',images,scene_timing)
    write_json(OUTPUT/'review_scene.json',{'status':recipe['status'],'purpose':'Initial tree and shrub art review; illustrative placements, not a game level',
        'base_scene':'../cottage_shapes/review_scene.json','grid_size':old['grid_size'],'instances':recipe['instances'],
        'wind_direction':'E','foliage_cycle_duration_ms':5400,'base_cycle_duration_ms':3600,'cycle_duration_ms':10800,
        'frames':records,'loop':True,'review':{'scene_scale':recipe['scene_scale'],'closeup_rect':recipe['scene_closeup'],'closeup_scale':recipe['scene_closeup_scale']}})


def build():
    recipe=read_json(SOURCE/'recipe.json');OUTPUT.mkdir(exist_ok=True);(OUTPUT/'scene_frames').mkdir(exist_ok=True)
    reference=Image.open(SOURCE/recipe['source']).convert('RGB');frames={}
    for plant in recipe['plants']:frames[plant['id']]=export_plant(recipe,plant,reference)
    write_json(OUTPUT/'palette.json',{'status':recipe['status'],'materials':recipe['palette']})
    write_json(OUTPUT/'foliage.json',{'id':recipe['id'],'status':recipe['status'],'tile_size':[24,24],
        'plants':[{'id':p['id'],'metadata':f"{p['id']}/foliage.json"} for p in recipe['plants']],
        'wind_direction':'E','cycle_duration_ms':5400,'review':{'plants':'foliage_review.gif','scene':'review_scene.gif','garden':'garden_closeup.gif'}})
    review_board(recipe,frames);build_scene(recipe,frames)
    print(f"Built {recipe['status']} broadleaf tree and shrub: nine 600ms wind poses, fixed bark/shadows, 54-frame synchronized scene")

if __name__=='__main__':build()
