"""Compose native reserve, cave approach, hall and relief art over retained geometry."""
from __future__ import annotations
import argparse
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from PIL import Image,ImageChops,ImageDraw,ImageEnhance
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.build_eldenmere_hd import Export,source_cell,fit,update_visual,pixels
from tools.build_eldenmere_exteriors_hd import split_registration
from tools.build_sanctuary_home_hd import SOURCE as HOME_ART_SOURCE, door_poses
from tools.eldenmere_hd_materials import Materials,image,read
SRC=ROOT/'assets/source/maps/sanctuary_reserve_hd'
PACK='assets/maps/sanctuary_reserve_hd'
RESERVE='elden_vale_sanctuary'

class ReserveExport(Export):
    def png(self,name,im):
        path=PACK+'/'+name+'.png';stream=BytesIO();im.save(stream,format='PNG');raw=stream.getvalue()
        self.out[path]=raw;self.records[path]={'file':path,'size_pixels':list(im.size),'sha256':sha256(raw).hexdigest(),'pixel_space':'logical_ui' if name.endswith('/overview') else 'artwork'}
        return path

def antler_products(ex, reserve, spec):
    """Native shared projection; cosmetic contact masks never define collision."""
    pack=read(spec['manifest'])
    source=image(pack['assets']['antlers_complete']['image'])
    master=source.resize(tuple(spec['projection_artwork']),Image.Resampling.NEAREST)
    origin=spec['origin_logical'];collision=Image.open(ROOT/reserve['collision']).convert('L')
    footprints={r['id']:r['rect'] for r in reserve['collision_footprints']}
    support=spec['contact_logical'];x,y,w,h=support
    fx,fy,fw,fh=footprints[spec['existing_footprint']]
    if not (fx<=x and fy<=y and x+w<=fx+fw and y+h<=fy+fh):raise ValueError('Antler contact leaves retained ridge')
    # A conservative authored anatomical enclosure protects the snout/teeth.
    # Only the lower earth/root fringe outside physical ridge ground is removed.
    bone=Image.new('L',master.size);draw=ImageDraw.Draw(bone)
    draw.polygon([tuple(p) for p in spec['bone_polygon_artwork']],fill=255)
    ground=Image.new('RGBA',master.size);raised=master.copy()
    # The irregular skyline is an occlusion contour, not a collision mask.
    # Faces above a retained support remain continuous down to that support.
    fringe=Image.new('L',master.size);fd=ImageDraw.Draw(fringe)
    contour=[tuple(p) for p in spec['fringe_contour_artwork']]
    fd.polygon([(0,master.height),*contour,(master.width,master.height)],fill=255)
    ridge=[footprints[key] for key in spec['ridge_footprints']]
    for yy in range(min(p[1] for p in contour),master.height):
        for xx in range(master.width):
            wx=int(origin[0]+xx/2);wy=int(origin[1]+yy/2)
            solid=any(rx<=wx<rx+rw and ry<=wy<ry+rh for rx,ry,rw,rh in
                      (footprints[key] for key in spec['ridge_footprints']))
            solid=solid and collision.getpixel((wx,wy))==255
            if solid:
                ground.putpixel((xx,yy),master.getpixel((xx,yy)));raised.putpixel((xx,yy),(0,0,0,0))
            elif not bone.getpixel((xx,yy)) and fringe.getpixel((xx,yy)):
                supported_face=any(rx<=wx<rx+rw and wy<ry for rx,ry,rw,rh in ridge)
                if not supported_face:raised.putpixel((xx,yy),(0,0,0,0))
    layers=[]
    def emit(name,im,position,layer,**meta):
        path=ex.png('landmarks/'+name,im)
        record={'id':'pale_antlers_'+name,'image':path,'logical_size':[im.width/2,im.height/2],
                'position':list(position),'layer':layer,'collision':'none','artwork_pixels_per_world_pixel':2,
                'interaction_cues':False,**meta}
        if layer=='overhead':
            # Runtime consumes grayscale authored coverage, not an inferred contact mask.
            record['occlusion_mask']=ex.png('landmarks/'+name+'_mask',im.getchannel('A'))
        layers.append(record)
    # Dressing is rooted against the retained ridge, never a new physical object.
    for r in spec['dressing']:
        a=pack['assets'][r['asset']];im=image(a['image']).resize(tuple(2*n for n in r['logical_size']),Image.Resampling.NEAREST)
        px,py=r['position'];mask=Image.new('L',im.size);md=ImageDraw.Draw(mask)
        for fid in spec['ridge_footprints']:
            rx,ry,rw,rh=footprints[fid]
            # Keep the face above its support; clip its ground edge to real solid pixels.
            md.rectangle(((rx-px)*2,0,(rx+rw-px)*2-1,(ry+rh-py)*2-1),fill=255)
        im.putalpha(ImageChops.multiply(im.getchannel('A'),mask))
        emit(r['id'],im,r['position'],'ground',source_asset=r['asset'])
    split=spec['split_y_artwork'];columns=spec['split_x_artwork']
    emit('skull_contact',ground.crop((0,split,master.width,master.height)),
         (origin[0],origin[1]+split/2),'ground',contact_logical=support)
    for index,(left,right) in enumerate(zip(columns,columns[1:])):
        emit('beam_'+str(index),raised.crop((left,0,right,split)),
             (origin[0]+left/2,origin[1]),'overhead',assembly_position_artwork=[left,0])
    emit('raised_skull',raised.crop((0,split,master.width,master.height)),
         (origin[0],origin[1]+split/2),'overhead',assembly_position_artwork=[0,split])
    reserve['landmark_layers']=layers
    reserve['landmark_visibility_points']=list(reserve['public_approaches'].values())
    reserve['art_integrations']={**reserve.get('art_integrations',{}),'pale_antlers':{
        'projection_artwork':spec['projection_artwork'],'origin_logical':origin,
        'contact_logical':support,'geometry':'retained collision; raised anatomy is nonblocking',
        'source_manifest':spec['manifest']}}
    return [spec['manifest'],pack['assets']['antlers_complete']['image'],
            *[pack['assets'][r['asset']]['image'] for r in spec['dressing']]]


def stone_threshold(shell, data, door, materials, courtyard):
    """Camera-facing cutaway: structural ends sit outside the retained clear slot."""
    _,y,clear_width,_=data['exit_clearance']
    # The reserve's wide entrance and the narrower relief passage have
    # different transfer widths. Include only the lip outside the sensor,
    # not the whole probe-clear area as if it were all an entrance.
    width=min(clear_width,2*(door['entry_half_width']+2))
    x=round(door['anchor'][0])-width//2
    # A quiet, broad ashlar sill makes the same passage recognizable from across
    # the hall. Neither its painted landing nor jambs add occupied geometry.
    left,right=x*2,(x+width)*2; top=y*2; bottom=(door['entry_y']+8)*2
    d=ImageDraw.Draw(shell)
    d.rectangle((left,top,right-1,bottom),fill='#666b65')
    floor=materials.paving((width*2,bottom-top),(x,y))
    shell.alpha_composite(floor,(left,top))
    if courtyard:
        # The reserve courtyard uses these same pale flags, in outdoor light.
        landing=ImageEnhance.Brightness(materials.paving((width*2,12),(535,371))).enhance(1.12)
    else:
        # Returning to the hall exposes its actual stone-floor palette.
        landing=materials.paving((width*2,12),(192,164))
    shell.alpha_composite(landing,(left,bottom-11))
    d=ImageDraw.Draw(shell)
    sill=door['entry_y']*2-3
    d.rectangle((left,sill,right-1,sill+5),fill='#555c58',outline='#303c38')
    d.line((left+1,sill,right-2,sill),fill='#ded6b6',width=2)
    d.line((left+2,sill+3,right-3,sill+3),fill='#a19f8c')
    for xx in range(left+24,right-1,24):d.line((xx,sill+1,xx,sill+4),fill='#777c70')
    # Short cut wall tops connect the jambs to the room boundary, rather than
    # presenting two free-standing posts in the off-map void.
    for a,b in ((left-38,left-15),(right+14,right+37)):
        d.rectangle((a,top-3,b,top+6),fill='#59675a',outline='#303c38')
        d.line((a+1,top-3,b-1,top-3),fill='#b8b99e',width=2)
    # Two masonry wall returns terminate at the actual opening edges; no
    # converging perspective and no lintel across the player-facing cutaway.
    for a,b in ((left-15,left-1),(right,right+14)):
        d.rectangle((a,top-14,b,bottom-4),fill='#303c38')
        d.rectangle((a+1,top-13,b-1,bottom-6),fill='#72796b')
        d.rectangle((a+1,top-13,b-1,top-6),fill='#c2bea5')
        d.line((a+2,top-12,b-2,top-12),fill='#e2d9b9')
        for yy in range(top-4,bottom-6,9):
            d.line((a+1,yy,b-1,yy),fill='#444f48')
            d.line((a+2,yy+1,b-2,yy+1),fill='#9a9f89')
        d.line((a+2,top-4,a+2,bottom-7),fill='#9da18d')
    return shell


def relief_door_frames(size, materials):
    """Share the hinged leaf master, never sample a finished timber passage."""
    background=Image.new('RGBA',(48,72),'#24302d')
    d=ImageDraw.Draw(background);w,h=background.size
    d.rectangle((4,6,w-5,h-5),fill='#43514b')
    d.rectangle((8,11,w-9,h-22),fill='#5b6458')
    d.rectangle((10,13,w-11,h-24),fill='#747b69')
    for yy in range(20,h-24,11):
        d.line((11,yy,w-12,yy),fill='#626d60')
        xx=17 if yy%2 else w-18
        d.line((xx,yy-8,xx,yy),fill='#626d60')
    paving=ImageEnhance.Brightness(materials.paving((w-16,22),(168,248))).enhance(.72)
    background.alpha_composite(paving,(8,h-23))
    d=ImageDraw.Draw(background)
    d.line((8,h-24,w-9,h-24),fill='#39483f')
    d.line((8,12,8,h-3),fill='#263a34',width=2)
    atlas=image((HOME_ART_SOURCE/'props_atlas.png').relative_to(ROOT).as_posix())
    colors=('#39483f','#c8c3a8','#a9ac98','#646f62')
    return [fit(frame,size) for frame in door_poses(atlas,background,colors)]



def products():
    rec=read(str((SRC/'recipe.json').relative_to(ROOT)));old=read(str((SRC/'baseline_maps.json').relative_to(ROOT)));ex=ReserveExport();materials=Materials()
    for r in rec['sources']:
        if sha256((SRC/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Changed authored source: '+r['file'])
    maps={n:read(p) for n,p in rec['scenes'].items()}
    for name,data in maps.items():
        if sha256((ROOT/data['collision']).read_bytes()).hexdigest()!=rec['collision_sha256'][name]:raise ValueError('Review changed collision for '+name)
    sheet=image(str((SRC/'landmarks_authored.png').relative_to(ROOT)))
    masters={name:source_cell(sheet,i,4,3) for i,name in enumerate(rec['sheet']['cells'])}
    plants={r['id']:r for r in read('assets/terrain/vegetation_hd/plants.json')['plants']}
    shared={r['id']:r for path in ('sanctuary_dining_hd','sanctuary_home_hd') for r in read('assets/terrain/eldenmere/'+path+'/manifest.json')['props']}
    def native(name,raw,size,bounds=None):return ex.png(name,fit(raw,size,bounds))
    def bind(e,raw,size,name=None,stretch=False):
        im=raw.resize(pixels(size),Image.Resampling.NEAREST) if stretch else fit(raw,size)
        update_visual(e,[ex.png(name or 'props/'+e['id'],im)],size,reduced_motion_frame=0)
        return im
    town=read('assets/maps/eldenmere/playable/map.json')
    reserve=maps[RESERVE];original=old[RESERVE]
    # Paths retain their authored cell coverage. RGB comes only from new packs.
    layout=read('assets/source/maps/elden_vale_sanctuary/recipe.json');pathmask=Image.new('L',tuple(original['size_pixels']));draw=ImageDraw.Draw(pathmask)
    for road in layout['ground']['roads']:
        points=list(map(tuple,road['points']));draw.line(points,fill=255,width=road['width'],joint='curve');radius=road['width']//2
        for x,y in points:draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=255)
    x,y,w,h=layout['ground']['court'];draw.rounded_rectangle((x,y,x+w-1,y+h-1),radius=24,fill=255)
    cells={(x,y) for y in range(original['size_pixels'][1]//24) for x in range(original['size_pixels'][0]//24) if pathmask.getpixel((x*24+12,y*24+12))}
    ground=materials.ground(original['size_pixels'],cells)
    # Small courtyard flags and shaded cloister floor use the common world grid.
    for yy in range(354,422,28):
        for xx in range(456,873,40):
            if (xx+yy)%5:
                paving=materials.paving((28,16),(xx,yy));ground.alpha_composite(paving,(xx*2,yy*2))
    paving=materials.paving((480,136),(655,273));paving=ImageEnhance.Brightness(paving).enhance(.62);ground.alpha_composite(paving,(1310,546))
    # Ground flowers remain small and nonblocking, replacing legacy baked flowers.
    for i,(x,y,w,h) in enumerate(layout['garden_patches']):
        for row,yy in enumerate(range(y,y+h,20)):
            for xx in range(x,x+w,28):
                r=plants[('flowers_white','flowers_yellow','flowers_violet')[i%3]] if 'flowers_white' in plants else plants['flowers_white_cluster']
                ground.alpha_composite(image('assets/terrain/vegetation_hd/'+r['idle']),((xx+row%2*6)*2,yy*2))
    grass=deepcopy(read('assets/maps/eldenmere/town_hd/grass.json'))
    ex.json(PACK+'/grass.json',grass);reserve['grass']['manifest']=PACK+'/grass.json'
    variants={'fan':'splayed_hd','slender':'sparse_hd','arching':'dense_hd','seeded':'dense_hd'}
    for r in reserve['grass']['instances']:r['variant']=variants.get(r['variant'],r['variant'])
    # Keep all IDs, roots, footprints, depth baselines and story bindings.
    originals={e['id']:e for e in original['entities']}
    stonewall='assets/terrain/eldenmere/terraces_hd/modules/maintained/'
    tree_draw=fit(masters['memorial_tree'],(192,176))
    for e in reserve['entities']:
        previous=originals[e['id']];size=image(previous['frames'][0]).size;key=e['id']
        if 'landmark_' in key:
            im=tree_draw.copy();a=Image.new('L',im.size);d=ImageDraw.Draw(a)
            part=key.rsplit('_',1)[-1]
            band={'roots':(0,278,384,352),'trunk':(0,190,384,278),'canopy':(0,0,384,190)}[part]
            d.rectangle(band,fill=255);im.putalpha(ImageChops.multiply(im.getchannel('A'),a));bind(e,im,size,stretch=True)
        elif key.startswith(('reserve_tree_','reserve_shrub_','confluence_understory_')):
            if key.startswith('reserve_tree_'):plant=('broadleaf_full','broadleaf_spreading','broadleaf_weathered')[int(key.split('_')[2])%3]
            elif key.startswith('reserve_shrub_'):plant='shrub_rounded'
            else:plant='flowers_white'
            r=plants[plant];frames=[]
            for i,f in enumerate(r['frames']):
                raw=image('assets/terrain/vegetation_hd/'+f['file'])
                frames.append(native(f'vegetation/{plant}/{size[0]}_{size[1]}_{i}',raw,size))
            update_visual(e,frames,size,frame_duration_ms=600,reduced_motion_frame=0)
        elif '_wall_' in key:
            module='wall_side_left' if '_west_' in key or '_east_' in key else 'wall_back' if '_north_' in key else 'wall_front_00'
            raw=image(stonewall+module+'.png');bind(e,raw,size,stretch=True)
        elif key=='reserve_hall':
            spec={'logical_size':size,'body_bounds_logical':[2,4,286,214],'door_rect_logical':[132,170,24,40],'source_door_normalized':[.405,.63,.59,.91]}
            bind(e,split_registration(masters['hall'],spec),size,stretch=True)
        elif key=='reserve_cloister_roof':bind(e,masters['cloister_roof'],size,stretch=True)
        elif key=='reserve_cloister_back':
            raw=image(stonewall+'wall_front_00.png');im=Image.new('RGBA',pixels(size))
            for x in range(0,im.width,raw.width):im.alpha_composite(raw,(x,0))
            bind(e,ImageEnhance.Brightness(im).enhance(.62),size,stretch=True)
        elif key=='reserve_cloister_arches':
            raw=masters['cloister_arches'].crop((0,0,masters['cloister_arches'].width,round(masters['cloister_arches'].height*.62))).resize(pixels(size),Image.Resampling.NEAREST)
            # Retain the original architectural opening coverage, independently
            # of the newly authored stone color/detail and the story cast.
            coverage=Image.open(SRC/'cloister_opening_coverage.png').convert('L').resize(pixels(size),Image.Resampling.NEAREST)
            raw.putalpha(ImageChops.multiply(raw.getchannel('A'),coverage));bind(e,raw,size,stretch=True)
        elif key.startswith('reserve_cloister_column'):bind(e,masters['column'],size,stretch=True)
        elif key=='reserve_entrance_arch':bind(e,masters['entrance'],size,stretch=True)
        elif key=='reserve_cave':bind(e,masters['cave'],size,stretch=True)
        elif key=='reserve_cave_keeper_rail':
            r=next(r for r in read('assets/terrain/eldenmere/exteriors_hd/manifest.json')['props'] if r['id']=='fence_panel');bind(e,image('assets/terrain/eldenmere/exteriors_hd/'+r['idle']),size)
        elif 'ridge_band' in key or key=='reserve_survey_seam':bind(e,masters['ridge'],size,stretch=True)
        elif 'ridge_rock' in key:bind(e,image('assets/terrain/vegetation_hd/'+plants['boulder_mossy']['idle']),size)
        elif key.startswith(('ridge_crystal','ridge_vein')):
            im=fit(masters['crystals'],size)
            # Authoritative entrance clearance remains empty in each crystal layer.
            x,y=e['position'];a=im.getchannel('A');d=ImageDraw.Draw(a);d.rectangle(((984-x)*2,(304-y)*2,(1040-x)*2,(378-y)*2),fill=0);im.putalpha(a)
            bind(e,im,size,stretch=True)
        elif key in ('ridge_old_stele','ridge_low_stele') or 'memorial_marker' in key or key=='reserve_boundary_marker':bind(e,masters['stele'],size)
        elif key.startswith('reserve_bench'):bind(e,image(shared['spare_bench']['image']),size)
        elif key.startswith('reserve_planter'):bind(e,image(shared['herbs']['image']),size)
        elif key=='reserve_survey_board':bind(e,image(shared['notices']['image']),size)
        elif key.startswith('reserve_survey_stake'):
            raw=image('assets/terrain/eldenmere/exteriors_hd/props/garden_gate/idle.png');bind(e,raw.crop((0,0,max(1,raw.width//6),raw.height)),size)
        elif 'lamp_' in key:
            raw=image('assets/maps/eldenmere/courtyard_hd/props/lantern.png');bind(e,raw,size)
        elif key=='court_basin':
            im=fit(masters['basin'],size);frames=[]
            # Move only a small water highlight cropped from the authored water.
            water=im.crop((26,22,42,26))
            for i,dx in enumerate((0,1,2,2,1,0)):
                frame=im.copy();frame.alpha_composite(water,(26+dx,22));frames.append(ex.png(f'basin/frame_{i}',frame))
            update_visual(e,frames,size,frame_duration_ms=200,reduced_motion_frame=0)
        else:raise ValueError('Unmapped exterior entity '+key)
    reserve['ground_overlays']=ex.chunks('reserve',ground,[Image.new('RGBA',ground.size)])
    reserve['ground_frames']=[ex.png('blank',Image.new('RGBA',(1,1)))];reserve['artwork_pixels_per_world_pixel']=1
    reserve['art_replacements']={k:v for k,v in town['art_replacements'].items() if '/gardener/bucket_' in k}
    # Furnishings preserve their existing physical canvases and occupied support.
    mapping={'records_cabinet':'bookcase','reading_bench_north':'spare_bench','reading_bench_south':'spare_bench','reading_stand':'bookstand','ledger_table':'table','records_chair':'chair_north','west_north_plant':'herbs','west_south_plant':'plant','east_south_plant':'plant','central_remembrance_rug':'rug','visitor_bed':'bed','bedside_water_table':'washbasin','linen_cupboard':'cupboard','care_basket':'venn_supplies','visitor_bench':'spare_bench','mended_rug':'rug','recovery_herbs':'plant','vigil_lamp':'lamp'}
    for name,data in maps.items():
        if name==RESERVE:continue
        previous={e['id']:e for e in old[name]['entities']}
        for e in data['entities']:
            prior=previous[e['id']];size=image(prior['frames'][0]).size
            raw=masters['remembrance_table'] if e['id'] in ('north_remembrance_table','ledger_table') else image('assets/maps/eldenmere/courtyard_hd/props/lantern.png') if mapping[e['id']]=='lamp' else image(shared[mapping[e['id']]]['image'])
            if e['id']=='records_cabinet':
                raw=Image.new('RGBA',pixels(size));book=image(shared['bookcase']['image'])
                raw.alpha_composite(book,(0,0));raw.alpha_composite(book,(72,0))
            # Keep both the canvas and original occupied support registration.
            bind(e,raw,size,'rooms/'+name+'/'+e['id'],stretch=e['id']=='north_remembrance_table')
        w,h=data['size_pixels'];fx,fy,fw,fh=data['walkable_floor'];shell=Image.new('RGBA',(w*2,h*2),'#24302d')
        floor=materials.paving((fw*2,fh*2),(fx,fy));shell.alpha_composite(floor,(fx*2,fy*2))
        wall=image(stonewall+'wall_front_00.png')
        for yy in range(48,fy*2,48):
            for xx in range(fx*2,(fx+fw)*2,48):shell.alpha_composite(wall,(xx,yy))
        # Registered pilasters and fixed stained-glass windows keep wall details above feet.
        for xx in (fx,round(w/2)-6,fx+fw-12):shell.alpha_composite(fit(masters['column'],(12,fy-24)),(xx*2,48))
        hall_master=masters['hall'];sw,sh=hall_master.size
        window=fit(hall_master.crop((round(sw*.395),round(sh*.13),round(sw*.61),round(sh*.54))),(24,36))
        window_path=ex.png('architecture/crystal_window',window)
        former_layout=read(old[name]['source_recipe'])
        window_positions=former_layout['windows']
        for xx,yy in window_positions:shell.alpha_composite(window,pixels((xx,yy)))
        # The existing wall medallion retains its ceremonial position and steady cyan glass.
        for detail in former_layout['fantasy'].get('wall_details',[]):
            if detail['module']=='cycle_medallion':
                ornament=fit(hall_master.crop((round(sw*.395),round(sh*.13),round(sw*.61),round(sh*.54))),(24,40))
                shell.alpha_composite(ornament,pixels(detail['position']))
        data['native_wall_details']={'window':window_path,'logical_size':[24,36],'positions':window_positions}

        for door in data['doors']:
            if door['frames']:
                size=image(old[name]['doors'][data['doors'].index(door)]['frames'][0]).size
                door['frames']=[ex.png(f'doors/{i}',frame) for i,frame in enumerate(relief_door_frames(size,materials))];door.update(artwork_pixels_per_world_pixel=2,logical_size=list(size))
            ax,ay=door['anchor'];opening=(int(ax-door['entry_half_width'])*2,min(int(ay)-8,fy+fh)*2,int(ax+door['entry_half_width'])*2,(int(ay)+8)*2)
            shell.paste(materials.paving((opening[2]-opening[0],opening[3]-opening[1]),(opening[0]//2,opening[1]//2)),opening[:2])
            if door['entry_side']=='south':
                shell=stone_threshold(shell,data,door,materials,name=='elden_vale_sanctuary_hall')
        data['ground_overlays']=ex.chunks(name,shell,[Image.new('RGBA',shell.size)]);data['ground_frames']=[ex.png('blank',Image.new('RGBA',(1,1)))];data['artwork_pixels_per_world_pixel']=1
    # Repeatable inspection cues advertise their actual authored floor approaches.
    cues={RESERVE:[('boundary','reserve_boundary_marker'),('survey','reserve_survey_board')], 'elden_vale_sanctuary_hall':[('records','ledger_table'),('remembrance','north_remembrance_table'),('cabinet','records_cabinet')]}
    for name,pairs in cues.items():
        targets=read('assets/story/sanctuary_reserve/layout.json')['targets' if name==RESERVE else 'hall_targets'];data=maps[name];data['interaction_cues']=[]
        for key,entity in pairs:
            point=targets[key]['approach'];e=next(e for e in data['entities'] if e['id']==entity);size=e['logical_size']
            data['interaction_cues'].append({'id':key,'entity':entity,'available_when':'reserve_inspect_'+key,'interaction_boundary':[point[0]-12,point[1]-6,24,12],'glint_anchor':[size[0]/2,size[1]/3]})
    relief=maps['elden_vale_sanctuary_relief'];relief['interaction_cues']=[{'id':'visitor_rest','entity':'visitor_bed','available_when':'reserve_relief_rest','interaction_boundary':[48,182,48,12],'glint_anchor':[24,40]}]
    # Petals sample current authored flower detail and retain five-unit presentation.
    flower=image('assets/terrain/vegetation_hd/'+plants['flowers_white']['idle']);glyph=flower.crop((14,10,24,20));modules={}
    for name in ('petal_white','petal_cyan','petal_amethyst'):
        frames=[ex.png('petals/'+name+'_'+str(i),glyph.rotate(i*90,Image.Resampling.NEAREST)) for i in range(4)]
        modules[name]={'frames':frames,'logical_size':[5,5],'artwork_pixels_per_world_pixel':2}
    ex.json(PACK+'/petals.json',{'modules':modules});reserve['fantasy_effects']['grove']['petal_manifest']=PACK+'/petals.json'
    landmark_dependencies=antler_products(ex,reserve,rec['pale_antlers']) if rec.get('pale_antlers') else []
    dependencies=[]
    for file in landmark_dependencies:
        dependencies.append({'path':file,'sha256':sha256((ROOT/file).read_bytes()).hexdigest()})
    for root in ('assets/terrain/eldenmere/grass_dirt_hd','assets/terrain/eldenmere/stone_paving_hd','assets/terrain/eldenmere/terraces_hd','assets/terrain/vegetation_hd','assets/terrain/eldenmere/sanctuary_home_hd','assets/terrain/eldenmere/sanctuary_dining_hd','assets/terrain/eldenmere/exteriors_hd','assets/maps/eldenmere/town_hd','assets/maps/eldenmere/courtyard_hd'):
        for p in sorted((ROOT/root).rglob('*')):
            if p.is_file() and p.suffix in ('.png','.json'):dependencies.append({'path':str(p.relative_to(ROOT)),'sha256':sha256(p.read_bytes()).hexdigest()})
    for file in ('assets/source/maps/elden_vale_sanctuary/recipe.json','assets/story/sanctuary_reserve/layout.json',
                 'assets/maps/eldenmere/playable/map.json','tools/build_sanctuary_home_hd.py',
                 (HOME_ART_SOURCE/'props_atlas.png').relative_to(ROOT).as_posix()):
        dependencies.append({'path':file,'sha256':sha256((ROOT/file).read_bytes()).hexdigest()})
    for name,data in maps.items():
        data['source_recipe']=str((SRC/'recipe.json').relative_to(ROOT));data['source_recipe_sha256']=sha256((SRC/'recipe.json').read_bytes()).hexdigest()
        data['source_assets']=[{'path':str((SRC/r['file']).relative_to(ROOT)),'sha256':r['sha256']} for r in rec['sources']]
        data['pause_on_focus_loss']=True;data['art_bank']=PACK+'/manifest.json';data['art_integrations']={**data.get('art_integrations',{}),'reserve_hd':{'density':2,'recipe':str((SRC/'recipe.json').relative_to(ROOT))}}
        if data.get('asset_instances'):
            current={e['id']:e for e in data['entities']}
            for inst in data['asset_instances']:inst.update({k:v for k,v in current[inst['id']].items() if k not in ('id','position','sort_y')})
        # Overview is a logical UI derivative of the new native assembly.
        canvas=ground.copy() if name==RESERVE else Image.new('RGBA',pixels(data['size_pixels']))
        if name!=RESERVE:
            for chunk in data['ground_overlays']:canvas.alpha_composite(ex.load(chunk['image']),pixels(chunk['position']))
        for layer in data.get('landmark_layers',[]):
            if layer['layer']!='overhead':canvas.alpha_composite(ex.load(layer['image']),tuple(round(v*2) for v in layer['position']))
        for e in sorted(data['entities'],key=lambda r:(r['sort_y'],r.get('sort_priority',0))):canvas.alpha_composite(ex.load(e['frames'][0]),pixels(e['position']))
        for layer in data.get('landmark_layers',[]):
            if layer['layer']=='overhead':canvas.alpha_composite(ex.load(layer['image']),tuple(round(v*2) for v in layer['position']))
        data['overview']=ex.png(name+'/overview',canvas.resize(tuple(data['size_pixels']),Image.Resampling.NEAREST).convert('RGB'))
        data['build']={'tool':'tools/build_sanctuary_reserve_hd.py','implementation':'native_2x_packs','source_recipe':str((SRC/'recipe.json').relative_to(ROOT)),'art_manifest':PACK+'/manifest.json','source_assets':data['source_assets']}
        ex.json(rec['scenes'][name],data)
    ex.json(PACK+'/manifest.json',{'id':rec['id'],'integration_status':'integrated','artwork_pixels_per_world_pixel':2,'recipe':str((SRC/'recipe.json').relative_to(ROOT)),'sources':rec['sources'],'dependencies':dependencies,'collision_sha256':rec['collision_sha256'],'scenes':rec['scenes'],'exports':list(ex.records.values()),'character_bodies':'Existing approved banks unchanged; caretaker pails use native replacements.'})
    return ex.out

def build(check=False):
    output=products();stale=[]
    for path,raw in output.items():
        target=ROOT/path
        if not target.exists() or target.read_bytes()!=raw:
            stale.append(path)
            if not check:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    if check and stale:raise SystemExit('Stale reserve exports: '+', '.join(stale[:12]))
    print(f'{len(output)} reserve exports '+('verified' if check else 'built'))
    return output
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');build(parser.parse_args().check)
