"""Compose the complete HD town, southern business lane, upstream and town interiors.

Current map records retain gameplay ownership. Retained baselines supply logical
geometry and pre-expansion collision, never enlarged legacy artwork.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
import os
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from PIL import Image, ImageChops, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.eldenmere_hd_materials import Materials, image, mask_for, read
from tools.build_eldenmere_exteriors_hd import cutout
from tools.build_sanctuary_dining_hd import export_sprite
from tools.build_sanctuary_home_hd import architecture
SRC=ROOT/'assets/source/maps/eldenmere/town_hd'
PACK='assets/maps/eldenmere/town_hd'

def document(data):return (json.dumps(data,indent=2)+'\n').encode()
def pixels(rect):return tuple(v*2 for v in rect)
def fit(raw,size,bounds=None):return export_sprite(raw,pixels(size),pixels(bounds) if bounds else (2,2,size[0]*2-2,size[1]*2-2))
def source_cell(sheet,index,cols,rows):
    x,y=index%cols,index//cols
    raw=cutout(sheet,(x*sheet.width//cols+3,y*sheet.height//rows+3,(x+1)*sheet.width//cols-3,(y+1)*sheet.height//rows-3))
    # Generated source sheets need inspected silhouette extraction: remove the
    # disconnected edges of neighboring cells before registering the main object.
    mask=pygame.mask.from_surface(pygame.image.frombytes(raw.tobytes(),raw.size,'RGBA'))
    component=max(mask.connected_components(),key=lambda m:m.count())
    bounds=component.get_bounding_rects()[0]
    return raw.crop(tuple(bounds.topleft)+tuple(bounds.bottomright))

class Export:
    def __init__(self):self.out={};self.records={}
    def png(self,name,im):
        path=PACK+'/'+name+'.png';stream=BytesIO();im.save(stream,format='PNG');raw=stream.getvalue();self.out[path]=raw
        space='logical_geometry' if name.endswith(('/collision','/navigation_allowed')) else 'logical_ui' if name.endswith('/overview') else 'logical' if name=='blank' else 'artwork'
        self.records[path]={'file':path,'size_pixels':list(im.size),'pixel_space':space,'sha256':sha256(raw).hexdigest()};return path
    def json(self,path,data):self.out[path]=document(data)
    def load(self,path):
        return Image.open(BytesIO(self.out[path])).convert('RGBA') if path in self.out else image(path)
    def art(self,path,size):return {'file':path,'logical_size':list(size),'artwork_pixels_per_world_pixel':2}
    def chunks(self,name,base,phases):
        """Export only changed temporal chunks, keeping shared dry ground static."""
        chunk=384;records=[]
        for y in range(0,base.height,chunk):
            for x in range(0,base.width,chunk):
                box=(x,y,min(x+chunk,base.width),min(y+chunk,base.height));frames=[];seen={}
                for tick,phase in enumerate(phases):
                    im=base.crop(box);im.alpha_composite(phase.crop(box));digest=sha256(im.tobytes()).digest()
                    if digest not in seen:seen[digest]=self.png(f'{name}/chunks/{x//chunk}_{y//chunk}_{tick}',im)
                    frames.append(seen[digest])
                if len(set(frames))==1:frames=frames[:1]
                records.append({'id':f'{name}.{x//chunk}.{y//chunk}','position':[x//2,y//2],'logical_size':[(box[2]-x)//2,(box[3]-y)//2],'image':frames[0],'frames':frames,'frame_duration_ms':200,'artwork_pixels_per_world_pixel':2})
        return records

def update_visual(entity,frames,size,**extra):
    entity.update(frames=frames,logical_size=list(size),artwork_pixels_per_world_pixel=2,**extra)

def products():
    rec=json.loads((SRC/'recipe.json').read_text());old=json.loads((SRC/'baseline_maps.json').read_text());ex=Export();materials=Materials()
    for r in rec['sources']:
        if sha256((SRC/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Changed source '+r['file'])
    for r in rec.get('dependencies',[]):
        if sha256((ROOT/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Changed dependency '+r['file'])
    current_town=read('assets/maps/eldenmere/playable/map.json')
    for field in ('collision','navigation_allowed'):
        expected=Image.open(SRC/(field+'.png')).convert('L')
        actual=Image.open(ROOT/current_town[field]).convert('L')
        if actual.crop((0,0,*expected.size)).tobytes()!=expected.tobytes():
            raise ValueError('Review changed '+field+' registration before rebuilding the town')
    paths={'town':'assets/maps/eldenmere/playable/map.json','upstream':old['town']['exterior_scenes']['upstream'],**{k:v for k,v in old['town']['interior_scenes'].items() if k in old}}
    maps={name:read(path) for name,path in paths.items()}
    specialist=image(str((SRC/'specialists_authored.png').relative_to(ROOT)));furniture=image(str((SRC/'interiors_authored.png').relative_to(ROOT)))
    masters={name:source_cell(specialist,i,4,3) for i,name in enumerate(('bridge_deck','bridge_rail','workbench','timber_rack','well','well_rim','pail','crank','stool_watering_can','spare_cog_fittings','sluice','provisions'))}
    masters.update({name:source_cell(furniture,i,4,4) for i,name in enumerate(('writing_board','pupil_desk','teacher_desk','bookcase','village_map','coat_pegs','festival_corner','child_drawings','block_box','food_bowl','water_bowl','reading_bench','repair_table','shop_counter','stock_shelf','bedside_table'))})
    quest_sheet=image(str((SRC/'quest_props_authored.png').relative_to(ROOT)))
    masters.update({name:source_cell(quest_sheet,i,4,3) for i,name in enumerate(('lantern','lantern_frame','papers','craft_table','toy_red','toy_blue','toy_yellow','toy_green','toy_oak','empty_box','toolbox','sack'))})
    memorial=rec['memorial_lantern_source']
    raw=source_cell(image(memorial['file']),memorial['cell'],memorial['columns'],memorial['rows'])
    a,b,c,d=memorial['crop_normalized'];masters['memorial_lantern']=raw.crop((round(a*raw.width),round(b*raw.height),round(c*raw.width),round(d*raw.height)))
    # Extract the desk separately from its two source-sheet stools.
    raw=masters['pupil_desk'].copy();w,h=raw.size
    raw.paste((0,0,0,0),(round(w*.16),round(h*.66),round(w*.84),h));masters['pupil_desk']=raw
    masters['medicine']=masters['shop_counter'].crop((0,0,round(masters['shop_counter'].width*.3),round(masters['shop_counter'].height*.38)))
    masters['debris']=image('assets/terrain/vegetation_hd/plants/fallen_log_weathered/idle.png')
    def prop(name,size,bounds=None):return fit(masters[name],size,bounds)
    def sluice(size,bounds=None,progress=0):
        im=prop('sluice',size,bounds)
        if progress<=0:return im
        x0,y0,x1,y1=im.getbbox();w,h=x1-x0,y1-y0
        box=(round(x0+w*.25),round(y0+h*.49),round(x0+w*.77),round(y0+h*.91))
        leaf=im.crop(box);im.paste((0,0,0,0),box)
        im.alpha_composite(leaf,(box[0],box[1]-round(progress*h*.32)))
        return im
    hdhome=read('assets/terrain/eldenmere/sanctuary_home_hd/manifest.json');hddining=read('assets/terrain/eldenmere/sanctuary_dining_hd/manifest.json')
    shared={r['id']:r for r in hddining['props']+hdhome['props']}
    def furnishing(name,size):
        if name in masters:return prop(name,size)
        r=shared[name];native=image(r['image']);return native.copy() if native.size==pixels(size) else fit(native,size)
    # One composed manifest covers both scenes; individual instance IDs/roots persist.
    grass_manifest=read(old['town']['grass']['manifest'])
    grass_manifest['tall_grass']['variants']={k:v for k,v in grass_manifest['tall_grass']['variants'].items() if k.endswith('_hd')}
    grass_path=PACK+'/grass.json';ex.json(grass_path,grass_manifest)
    old_variants={'fan':'splayed_hd','slender':'sparse_hd','arching':'dense_hd','seeded':'dense_hd'}
    for name in ('town','upstream'):
        for r in maps[name]['grass']['instances']:r['variant']=old_variants.get(r['variant'],r['variant'])
        maps[name]['grass']['manifest']=grass_path
    # Every existing exterior is bound independently to its exact existing portal.
    ext_pack='assets/terrain/eldenmere/exteriors_hd/';ext=read(ext_pack+'manifest.json');designs={r['id']:r for r in ext['buildings']}
    town=maps['town'];entities={e['id']:e for e in town['entities']}
    for binding in ext['bindings']:
        name=binding['entity']
        if name=='sanctuary':continue # Already approved, separately retained source/registration.
        r=designs[binding['new_design']];dx,dy,dw,dh=r['door_rect_logical'];frames=[]
        for i,f in enumerate(r['ambient']['frames']):
            im=image(ext_pack+f['file']).copy();im.paste((0,0,0,0),pixels((dx,dy,dx+dw,dy+dh)))
            # The mill's wheel is a separately controlled 9.6-second clock.
            if name=='mill':im.paste(image(ext_pack+r['structure']).crop((176,188,272,284)),(176,188))
            frames.append(ex.png(f'exteriors/{name}/ambient_{i}',im))
        still=image(ext_pack+r['structure']).copy();update_visual(entities[name],frames,r['logical_size'],frame_duration_ms=200,reduced_motion_image=ex.png(f'exteriors/{name}/still',still))
        door=next(d for d in town['doors'] if d['id']==name);door.update(frames=[ext_pack+f['file'] for f in r['door']['frames']],artwork_pixels_per_world_pixel=2,logical_size=r['door']['logical_size'])
    wheel={'id':'mill.wheel','position':[1024,298],'sort_y':entities['mill']['sort_y'],'sort_priority':.1,'phase_offset':0,'frame_duration_ms':200,'frames':[ext_pack+f'mill/wheel/frame_{i:02}.png' for i in range(48)],'logical_size':[48,48],'artwork_pixels_per_world_pixel':2,'reduced_motion_frame':0}
    town['entities']=[e for e in town['entities'] if e['id']!='mill.wheel']+[wheel];entities['mill.wheel']=wheel
    plants={r['id']:r for r in read('assets/terrain/vegetation_hd/plants.json')['plants']}
    def vegetation(entity,plant):
        r=plants[plant];update_visual(entity,['assets/terrain/vegetation_hd/'+f['file'] for f in r['frames']],r['logical_size'],frame_duration_ms=600,reduced_motion_frame=0)
    for e in town['entities']:
        if e['id'].startswith('school.'):
            if 'tree' in e['id']:vegetation(e,'broadleaf_spreading')
            elif 'shrub' in e['id']:vegetation(e,'shrub_rounded')
            elif 'flowers' in e['id']:vegetation(e,'flowers_white' if 'west' in e['id'] else 'flowers_yellow')
            elif 'bench' in e['id']:update_visual(e,[ex.png('props/school_bench',furnishing('spare_bench',(48,30)))],(48,30))
        if e['id'].startswith('workshop.'):
            name=e['id'].split('.',1)[1];size=Image.open(ROOT/next(x for x in old['town']['entities'] if x['id']==e['id'])['frames'][0]).size
            update_visual(e,[ex.png('props/'+name,prop(name,size))],size)
    # Preserve separate fitting support in every Mira work pose.
    town.setdefault('art_replacements',{})
    animation=read('assets/characters/mira/work_bench/animation.json')
    for r in animation['frames']:
        path='assets/characters/mira/work_bench/'+r['fitting_file'];im=image(path);size=im.size;bounds=im.getbbox()
        replacement=ex.png('props/fitting_'+Path(path).stem,prop('spare_cog_fittings',size,bounds));town['art_replacements'][path]=ex.art(replacement,size)
    # Native well structure registered around the unchanged rope/crank/shaft geometry.
    raw=masters['well'];w,h=raw.size;fixed=Image.new('RGBA',(224,224));split=round(h*.54)
    fixed.alpha_composite(fit(raw.crop((0,0,w,split)),(80,43),(2,3,78,43)),(0,0))
    bottom=fit(raw.crop((0,split,w,h)),(80,47),(2,0,78,47));fixed.alpha_composite(bottom,(0,86))
    rim=Image.new('RGBA',fixed.size);rim.alpha_composite(fixed.crop((0,134,160,186)),(0,134))
    fixed_path=ex.png('well/fixed',fixed);rim_path=ex.png('well/front_rim',rim);well_spec={'fixed':ex.art(fixed_path,(112,112)),'front_rim':ex.art(rim_path,(112,112)),'pails':{}}
    anim=read('assets/characters/npcs/female_02/gardener/animations.json')
    for key,r in anim['buckets'].items():
        legacy='assets/characters/npcs/female_02/gardener/'+r['file'];size=image(legacy).size
        neutral=image('assets/characters/npcs/female_02/gardener/bucket_0_0.png')
        new=prop('pail',size,neutral.getbbox())
        # Levels remain semantic journey state; the pail silhouette/support is fixed.
        level=int(key.rsplit('_',1)[1]);box=new.getbbox()
        if level and box:
            x0,y0,x1,y1=box;mask=Image.new('L',new.size);base_y=y1-5
            ImageDraw.Draw(mask).rectangle((x0+3,base_y-level*2,x1-4,base_y),fill=255)
            new.paste((89,142,159,255),(0,0),ImageChops.multiply(mask,new.getchannel('A')))
        angle=int(key.split('_')[1])
        if angle:new=new.rotate(-angle,resample=Image.Resampling.NEAREST,center=pixels(r['grip']))
        path=ex.png('well/'+key,new);well_spec['pails'][key]=ex.art(path,size);town['art_replacements'][legacy]=ex.art(path,size)
    town['well_art']=well_spec
    update_visual(entities['well'],[ex.png('well/idle',fixed.crop((0,0,168,192)))],(84,96))
    # Town ground is reconstructed from current logical layers, including later yards.
    geo=read('assets/source/maps/eldenmere/courtyard_hd/geometry.json');dirt={tuple(r['cell']) for r in geo['dirt']}
    square=read('assets/maps/eldenmere/well_square/layout.json');dirt.update(map(tuple,square['added_dirt_cells']))
    # Later school/Liam/workshop occupancy is retained as logical cells.
    dirt.update(map(tuple,rec['supplemental_dirt_cells']))
    for line in rec['road_centerlines']:
        (x0,y0),(x1,y1)=line
        for y in range(min(y0,y1)//24,max(y0,y1)//24+1):
            for x in range(min(x0,x1)//24,max(x0,x1)//24+1):dirt.update(((x,y),(x,y-1) if y0==y1 else (x-1,y)))
    size=rec['town_size_logical'];base=materials.ground(size,dirt);under=base.copy()
    for r in geo['masonry']:base.alpha_composite(image('assets/terrain/eldenmere/terraces_hd/modules/maintained/'+r['tile']+'.png'),pixels(r['position']))
    for r in geo['stairs']:
        x,y=r['position'];base.paste(under.crop((x*2,y*2,x*2+96,y*2+96)),(x*2,y*2));base.alpha_composite(image('assets/terrain/eldenmere/terraces_hd/stairs/maintained.png'),(x*2,y*2))
    positions=[[372,288],*read('assets/source/terrain/eldenmere/well/recipe.json')['paving_positions']]
    cover=Image.open(ROOT/'assets/source/maps/eldenmere/courtyard_hd/flagstone_coverage.png').convert('L').resize((64,32),Image.Resampling.NEAREST)
    for x,y in positions:
        stone=materials.paving((64,32),(x,y));stone.putalpha(cover);base.alpha_composite(stone,(x*2,y*2))
    # Brook, cardinal channels and fixed-height falls share one temporal clock.
    sys.path.insert(0,str(ROOT/'tools'))
    from tools.build_eldenmere_blockout import geometry
    plan=read('assets/maps/eldenmere/terrain_foundation/adapted_plan.json');geom=geometry(plan);scene=read('assets/maps/eldenmere/terrain_foundation/scene.json');watercells={(x+dx,y) for x,y,_ in geom['stream'] for dx in (-1,0,1)}
    watercells.update((x,y) for y in range(56,size[1]//24+1) for x in (34,35,36))
    phases=[]
    for tick in range(6):
        phase=Image.new('RGBA',base.size)
        for im,pos in materials.water(watercells,tick):phase.alpha_composite(im,pos)
        for r in scene['channels']:phase.alpha_composite(materials.channel(r['route'],tick,r['mode']),tuple(v*48 for v in r['cell']))
        for r in scene['spillways']:
            im=materials.spillway(tick,r['mode'])
            phase.alpha_composite(im,pixels(r['position']))
        phases.append(phase)
    # Bridge decks belong beneath actors; near rails remain the foreground pass.
    for r in plan['crossings']:
        if r['kind']!='stream_bridge':continue
        x,y,w,h=r['rect'];pos=(x*48,y*48-24);deck=Image.new('RGBA',(w*48,144));deck.alpha_composite(prop('bridge_deck',(w*24,48)),(0,24));deck.alpha_composite(prop('bridge_rail',(w*24,14)),(0,2))
        rail=Image.new('RGBA',deck.size);rail.alpha_composite(prop('bridge_rail',(w*24,18)),(0,104))
        for phase in phases:phase.alpha_composite(deck,pos)
        layer=next(f for f in town['foreground'] if f['id']==r['id']);layer.update(image=ex.png('bridges/'+r['id']+'_front',rail),artwork_pixels_per_world_pixel=2,logical_size=[w*24,72])
    # New southern businesses; all original world coordinates remain unchanged.
    business_pack='assets/terrain/eldenmere/business_exteriors_hd/';business={r['id']:r for r in read(business_pack+'manifest.json')['buildings']}
    collision=Image.new('L',tuple(size),0);original_collision=Image.open(SRC/'collision.png').convert('L');collision.paste(original_collision,(0,0));allowed=Image.new('L',tuple(size));allowed.paste(Image.open(SRC/'navigation_allowed.png').convert('L'),(0,0));cd=ImageDraw.Draw(collision);ad=ImageDraw.Draw(allowed)
    # Preserve every old pixel; extension receives continuing river blockers.
    cd.rectangle((816,1344,887,size[1]-1),fill=255)
    for name in ('inn','item_shop'):
        town['entities']=[e for e in town['entities'] if e['id']!=name];town['doors']=[d for d in town['doors'] if d['id']!=name];town['landmarks']=[l for l in town['landmarks'] if l['id']!=name]
    for spec in rec['businesses']:
        name=spec['id'];r=business[spec['design']];x,y=spec['position'];dx,dy,dw,dh=r['door_rect_logical'];gx,gy,gw,gh=r['ground_rect_logical'];frames=[]
        for i,f in enumerate(r['ambient']['frames']):
            im=image(business_pack+f['file']).copy();im.paste((0,0,0,0),pixels((dx,dy,dx+dw,dy+dh)));frames.append(ex.png(f'exteriors/{name}/ambient_{i}',im))
        still=image(business_pack+r['closed']).copy();still.paste((0,0,0,0),pixels((dx,dy,dx+dw,dy+dh)))
        town['entities'].append({'id':name,'position':[x,y],'sort_y':y+gy+gh,'phase_offset':0,'frame_duration_ms':200,'frames':frames,'logical_size':r['logical_size'],'artwork_pixels_per_world_pixel':2,'reduced_motion_image':ex.png('exteriors/'+name+'/still',still)})
        anchor=[x+dx+dw/2,y+gy+gh+6];room_path=PACK+'/rooms/'+name+'/map.json'
        town['doors'].append({'id':name,'host':name,'anchor':anchor,'entry_y':anchor[1],'entry_side':'north','entry_half_width':dw/2,'open_radius':30,'close_radius':38,'frame_duration_ms':100,'frames':[business_pack+f['file'] for f in r['door']['frames']],'position':[x+dx,y+dy],'requires_open':True,'destination':room_path,'spawn':[216,294],'arrival_facing':'back','arrival_door':'courtyard','logical_size':[dw,dh],'artwork_pixels_per_world_pixel':2})
        town['interior_scenes'][name]=room_path;town['landmarks'].append({'id':name,'name':spec['name'],'position':anchor});town['destinations'][name]=[round(anchor[0]/2)*2,anchor[1]]
        cd.rectangle((x+gx,y+gy,x+gx+gw-1,y+gy+gh-1),fill=255)
        ad.rectangle((round(anchor[0])-12,round(anchor[1])-6,round(anchor[0])+12,1500),fill=255)
        # Native paving connects each threshold to the new shared lane.
        paving=materials.paving((48,72),(round(anchor[0])-12,round(anchor[1])-6));base.alpha_composite(paving,pixels((round(anchor[0])-12,round(anchor[1])-6)))
    # Planting defines the new lane without obscuring either entrance or path.
    district=rec['district_vegetation']
    for label,plant,position in district:
        identifier='south_lane.'+label;town['entities']=[e for e in town['entities'] if e['id']!=identifier]
        r=plants[plant];e={'id':identifier,'position':position,'sort_y':position[1]+r['depth_baseline_logical'],'phase_offset':0};vegetation(e,plant);town['entities'].append(e)
        if 'tree' in label:
            x,y=position;gx,gy,gw,gh=r['ground_rect_logical'];cd.rectangle((x+gx,y+gy,x+gx+gw-1,y+gy+gh-1),fill=255)
    # Mark extension lanes only; original navigation pixels remain authoritative.
    for line in rec['road_centerlines']:
        (x0,y0),(x1,y1)=line
        ad.line((x0,max(1344,y0),x1,max(1344,y1)),fill=255,width=24)
    town['size_pixels']=size;town['size_tiles']=[v//24 for v in size];town['collision']=ex.png('town/collision',collision);town['navigation_allowed']=ex.png('town/navigation_allowed',allowed)
    town['ground_overlays']=ex.chunks('town',base,phases);town['ground_frames']=[ex.png('blank',Image.new('RGB',(1,1),'#24302d'))];town['pause_on_focus_loss']=True
    town['art_integrations']['town_hd']={'recipe':str((SRC/'recipe.json').relative_to(ROOT)),'region_logical':[0,0,*size],'density':2,'original_bounds_logical':rec['original_bounds_logical']}
    town['cartography']={'buildings':[{'id':spec['id'],'ground_rect':[spec['position'][0]+business[spec['design']]['ground_rect_logical'][0],spec['position'][1]+business[spec['design']]['ground_rect_logical'][1],*business[spec['design']]['ground_rect_logical'][2:]]} for spec in rec['businesses']],'roads':rec['road_centerlines'],'water_extensions':[[816,1344,72,288]]}
    town['expansion']={'original_size':old['town']['size_pixels'],'added_rows':12,'business_lane':'south','existing_coordinates_shifted':False}
    # Remaining rooms use the established native interior shell and shared furniture.
    original_rooms={k:v for k,v in old.items() if k not in ('town','upstream')}
    for name in ('inn','item_shop'):
        template=deepcopy(old['venn']);template.update(id=name,name='Eldenmere Inn' if name=='inn' else 'Eldenmere Item Shop',npcs=[],quests=[],destinations={},entities=[],interaction_cues=[])
        outer=next(d for d in town['doors'] if d['id']==name)
        template['doors']=[{**deepcopy(template['doors'][0]),'destination':paths['town'],'spawn':[outer['anchor'][0],outer['anchor'][1]+12],'arrival_facing':'front','arrival_door':name,'anchor':[216,306],'entry_y':306,'position':[204,276]}]
        template['npcs']=[{'id':name+'_keeper','name':'Innkeeper' if name=='inn' else 'Shopkeeper','kind':'stationary','position':[168,122] if name=='inn' else [216,152],'probe_size':[8,4],'draw_anchor':[12,30],'sprite':'assets/characters/npcs/male_01/idle_front.png'}]
        if name=='inn':
            template['rest_profile']={'scene':'inn','entity':'guest_bed','interaction_radius':16,'identifier':'inn_rest','offer':[{'speaker':'caelan','text':'A quiet place to catch our breath.'}],'prompt':"Rest here? Fully restores the party's HP and MP.",'choices':[{'text':'Rest','action':'rest'},{'text':'Not now','action':'leave'}],'complete':[{'speaker':'caelan','text':'That feels better. Ready to go.'}]}
        if name=='inn':template['interaction_cues']=[{'id':'guest_rest','entity':'guest_bed','available_when':'inn_rest','interaction_boundary':[36,156,48,12],'glint_anchor':[23,35]}]
        template['spawn']=[216,294];template['collision']=ex.png('rooms/'+name+'/collision',Image.new('L',(432,336),255))
        def entity(identifier,position,size,kind):return {'id':identifier,'position':position,'sort_y':position[1]+size[1],'frames':[],'phase_offset':0,'frame_duration_ms':600,'_kind':kind,'logical_size':size}
        if name=='inn':template['entities']=[entity('guest_bed',[36,96],[48,72],'bed'),entity('guest_bed_east',[342,96],[48,72],'bed'),entity('counter',[144,102],[48,48],'counter'),entity('table',[264,216],[48,48],'table'),entity('chair_west',[240,216],[24,36],'chair_west'),entity('chair_east',[312,216],[24,36],'chair_east'),entity('shelf',[108,40],[48,24],'shelf')]
        else:template['entities']=[entity('counter',[168,132],[96,48],'shop_counter'),entity('stock_shelf',[36,96],[48,72],'stock_shelf'),entity('bookcase',[348,96],[48,72],'bookcase')]
        maps[name]=template;paths[name]=town['interior_scenes'][name];original_rooms[name]=deepcopy(template)
    mappings={'parents_bed':'bed','liam_bed':'bed','tessa_bed':'bed','finn_bed':'bed','rowan_bed':'bed','ada_bed':'bed','pippa_bed':'bed','bookshelf':'bookcase','storage':'pantry','storage_b':'cupboard','sorting_table':'table','teacher_chair':'chair_north','chair':'chair_west','step_stool':'stool','lantern_shelf':'festival_corner','daisy_rug':'rug','liam_block_box':'block_box','daisy_food_bowl':'food_bowl','daisy_water_bowl':'water_bowl','guest_bed':'bed','guest_bed_east':'bed'}
    for name,original in original_rooms.items():
        data=maps[name];entry=data['doors'][0];logical_door=(20,12)
        layout={'windows':[[96,30],[288,30]] if data['size_pixels'][0]>=432 else [[144,30]],'entry_rect':[round(entry['anchor'][0])-10,entry['entry_y']-6,*logical_door]}
        shell=architecture(original,layout,'hall');ground=ex.png('rooms/'+name+'/ground',shell.convert('RGB'));data['ground_frames']=[ground];data['artwork_pixels_per_world_pixel']=2;data['ground_overlays']=[];data['pause_on_focus_loss']=True
        prev={e['id']:e for e in original['entities']};data.setdefault('art_replacements',{})
        for e in data['entities']:
            before=prev[e['id']];size=tuple(before.get('logical_size') or Image.open(ROOT/before['frames'][0]).size);identifier=e['id'];kind=e.pop('_kind',mappings.get(identifier,identifier))
            if identifier.startswith('pupil_chair'):kind='chair_south'
            if identifier.startswith('pupil_desk'):kind='pupil_desk'
            if kind=='shelf':kind='bookcase'
            if kind=='stool':raw=image('assets/terrain/eldenmere/exteriors_hd/props/stool/idle.png');im=fit(raw,size)
            elif kind=='hearth':im=image(shared['hearth']['image']).copy()
            elif identifier=='village_map':
                # Re-sample the approved geography's retained high-resolution
                # wall-map drawing; do not replace it with unrelated generated geography.
                im=fit(image('assets/source/world/auratia/wall_map_generated.png'),size,Image.open(ROOT/before['frames'][0]).getbbox())
            elif kind in masters:
                bounds=Image.open(ROOT/before['frames'][0]).getbbox() if before['frames'] else None
                im=prop(kind,size,bounds)
            else:im=furnishing(kind,size)
            path=ex.png('rooms/'+name+'/'+identifier,im);update_visual(e,[path],size,reduced_motion_frame=0)
            if kind=='hearth':e['frames']=[r['image'] for r in hddining['props'] if r['id']=='hearth']
            for state,legacy in before.get('state_images',{}).items():
                state_im=im.copy()
                if 'bowl' in identifier and state!='full':
                    # Preserve the drawn ceramic rim; consume only its contents.
                    w,h=state_im.size;x0,y0,x1,y1=state_im.getbbox();bw,bh=x1-x0,y1-y0
                    mask=Image.new('L',state_im.size);ImageDraw.Draw(mask).ellipse((x0+bw*.2,y0+bh*.12,x0+bw*.8,y0+bh*.5),fill=255)
                    if state=='half_full':mask.paste(0,(0,0,(x0+x1)//2,h))
                    state_im.paste((47,48,43,255),(0,0),ImageChops.multiply(mask,state_im.getchannel('A')))
                if identifier=='liam_block_box':
                    state_im=prop('empty_box',size,Image.open(ROOT/before['frames'][0]).getbbox())
                    for i in range(int(state)):
                        toy=prop(('toy_red','toy_blue','toy_yellow','toy_green','toy_oak')[i],(7,7))
                        state_im.alpha_composite(toy,((5+i*4)*2,8))
                state_path=ex.png('rooms/'+name+'/'+identifier+'_'+state,state_im)
                e['state_images'][state]=state_path
                data['art_replacements'][legacy]=ex.art(state_path,size)
            if before['frames']:
                for previous in before['frames']:data['art_replacements'][previous]=ex.art(path,size)
        for d in data['doors']:
            if not d['frames']:continue
            before_size=tuple(d.get('logical_size') or Image.open(ROOT/d['frames'][0]).size)
            d.update(frames=[ex.png(f'rooms/doors/{before_size[0]}_{before_size[1]}_{i}',image('assets/terrain/eldenmere/sanctuary_home_hd/'+f'doors/frame_{i+1:02}.png').resize(pixels(before_size),Image.Resampling.NEAREST)) for i in range(5)],logical_size=list(before_size),artwork_pixels_per_world_pixel=2)
        if name in ('inn','item_shop'):
            block=Image.new('L',(432,336),255);draw=ImageDraw.Draw(block);draw.rectangle((24,72,407,311),fill=0);draw.rectangle((204,276,227,335),fill=0)
            for e in data['entities']:
                x,y=e['position'];w,h=e['logical_size'];draw.rectangle((x+3,y+h//2,x+w-4,y+h-1),fill=255)
            data['collision']=ex.png('rooms/'+name+'/collision',block)
        if name=='elira':
            shelf=next(e for e in data['entities'] if e['id']=='lantern_shelf');size=shelf['logical_size']
            empty=prop('bridge_deck',size,(4,18,44,38))
            lantern=prop('memorial_lantern',(12,24),(1,2,11,22));full=empty.copy()
            # Match the existing first take pose exactly: one canonical object,
            # transferred from shelf local [16,5] into the same world pixels.
            full.alpha_composite(lantern,(32,10))
            for state,im in [('full',full),('empty',empty)]:
                legacy='assets/terrain/eldenmere/elira_interior/sprites/shelf_'+('with_lantern' if state=='full' else 'empty')+'.png'
                path=ex.png('rooms/elira/shelf_'+state,im);data['art_replacements'][legacy]=ex.art(path,size)
                if state=='full':shelf['frames']=[path]
        data['art_bank']=PACK+'/manifest.json'
    # Upstream remains a separate scene with identical boundaries and quest stations.
    upstream=maps['upstream'];udirt={(x,y) for x in range(6,9) for y in range(9,24)}|{(x,y) for x in range(8,20) for y in range(12,15)}|{(x,y) for x in range(17,22) for y in range(9,19)}
    ubase=materials.ground(upstream['size_pixels'],udirt);uwater={(x,y) for x in range(-1,33) for y in range(4,7)}|{(x,3) for x in [4,5,6,7,8,16,17,18,19]}|{(x,7) for x in [2,3,4,13,14,15,25,26,27]}
    uphases=[]
    for tick in range(6):
        phase=Image.new('RGBA',ubase.size)
        for im,pos in materials.water(uwater,tick,'E'):phase.alpha_composite(im,pos)
        # The race bed remains beneath the quest-controlled flow overlay.
        for y in range(7,24):phase.alpha_composite(materials.channel('channel_05_from_n',tick,'trickle'),(528*2,y*48))
        uphases.append(phase)
    for e in upstream['entities']:vegetation(e,'broadleaf_full')
    for i,(x,y) in enumerate([(290,228),(330,204),(358,416),(596,414),(60,212),(260,370),(690,338),(226,180),(678,510)]):
        identifier='upstream.shrub.'+str(i);upstream['entities']=[e for e in upstream['entities'] if e['id']!=identifier];e={'id':identifier,'position':[x,y],'sort_y':y+24,'phase_offset':i%9};vegetation(e,'shrub_rounded');upstream['entities'].append(e)
    upstream['ground_overlays']=ex.chunks('upstream',ubase,uphases);upstream['ground_frames']=town['ground_frames'];upstream['pause_on_focus_loss']=True
    upstream['art_integrations']={'town_hd':{'recipe':str((SRC/'recipe.json').relative_to(ROOT)),'density':2}}
    # Scene props retain their canvas/anchors and lifecycle; presentation is explicit.
    replacements={}
    def replacement(legacy,kind):
        if legacy in replacements:return replacements[legacy]
        previous=image(legacy);size=previous.size;bounds=previous.getbbox()
        im=prop(kind,size,bounds) if bounds else Image.new('RGBA',pixels(size))
        path=ex.png('scene_props/'+sha256(legacy.encode()).hexdigest()[:12],im)
        replacements[legacy]=ex.art(path,size);return replacements[legacy]
    encounter=read('assets/story/mill/encounter/scene.json')
    replacement('assets/story/mill/encounter/'+encounter['image'],'debris')
    # Household delivery props and the memorial lantern have existing ownership rules.
    for legacy,kind in [('assets/story/halden/sack.png','sack'),('assets/story/halden/pallet.png','bridge_deck'),('assets/story/halden/medicine.png','medicine'),('assets/story/elira/provisions.png','provisions'),('assets/terrain/eldenmere/elira_interior/sprites/lantern_unlit.png','memorial_lantern'),('assets/story/venn/provisions.png','provisions'),('assets/story/venn/toolbox.png','toolbox'),('assets/story/venn/debris.png','debris')]:
        if (ROOT/legacy).exists():replacement(legacy,kind)
    # Retain distinct workshop/lantern work surfaces and finished object ownership.
    for file in (ROOT/'assets/story').rglob('art.json'):
        if not any(part.startswith('lantern') for part in file.parts):continue
        art=json.loads(file.read_text())
        for r in art.get('props',[]):
            if not isinstance(r,dict):continue
            kind='craft_table' if 'table' in r.get('id','') else 'papers' if any(k in r.get('id','') for k in ('surface','materials','paper')) else 'empty_box' if 'box' in r.get('id','') else 'lantern_frame' if 'frame' in r.get('id','') else 'lantern'
            for legacy in r.get('states',{}).values():
                if isinstance(legacy,str) and (ROOT/legacy).exists():replacement(legacy,kind)
    blocks=read('assets/terrain/eldenmere/liam_home/blocks/blocks.json')
    for i,r in enumerate(blocks['blocks']):replacement(r['image'],('toy_red','toy_blue','toy_yellow','toy_green','toy_oak')[i])
    lip=blocks['front_overlay'];size=image(lip).size;im=prop('empty_box',size);im.paste((0,0,0,0),(0,0,im.width,round(im.height*.65)))
    replacements[lip]=ex.art(ex.png('scene_props/box_front_lip',im),size)
    # Upstream controller sprites use the same state clock, with native new materials.
    for r in read('assets/story/mill/art.json')['props']:
        files=list(r['states'].values())+[p for key in ('animation','moving_frames','restored_frames') for p in r.get(key,[])]
        for legacy in files:
            previous=image(legacy);size=previous.size;im=Image.new('RGBA',pixels(size));name=r['id']
            if name=='intake_screen':
                im.alpha_composite(sluice((58,80),progress=1 if any(k in legacy for k in ('cleared','restored')) else 0),(8,0))
                # The cut branch leaves the screen along the existing repair progression.
                progress=1 if any(k in legacy for k in ('cleared','restored')) else int(Path(legacy).stem.rsplit('_',1)[1])/5 if 'intake_move_' in legacy else 0
                branch=prop('debris',(64,26));im.alpha_composite(branch,(round(6-24*progress)*2,round(18+40*progress)*2))
            elif name=='inspection_pool':
                bank=materials.paving(pixels((30,32)),r['position']);im.alpha_composite(bank,(0,0))
                water=materials.water_tile(255,0,0,0,0,'E').resize((34,38),Image.Resampling.NEAREST)
                progress=1 if 'cleared' in legacy or 'restored' in legacy else 0
                if 'pool_' in Path(legacy).stem and Path(legacy).stem.rsplit('_',1)[-1].isdigit():progress=int(Path(legacy).stem.rsplit('_',1)[1])/6
                if progress<1:im.alpha_composite(water.crop((0,round(progress*38),34,38)),(12,16+round(progress*38)))
                trough=materials.channel('channel_10_from_w',0);im.alpha_composite(trough.resize((54,16),Image.Resampling.NEAREST),(52,32))
            elif name=='millrace_flow':
                tick=int(Path(legacy).stem.rsplit('_',1)[-1])%6 if Path(legacy).stem.rsplit('_',1)[-1].isdigit() else 0
                channel=materials.channel('channel_05_from_n',tick,'full' if 'restored' in legacy else 'trickle')
                for yy in range(0,size[1]*2,48):im.alpha_composite(channel,(0,yy))
            else:
                im=sluice(size,progress=1 if 'restored' in legacy else 0)
            path=ex.png('scene_props/'+sha256(legacy.encode()).hexdigest()[:12],im);replacements[legacy]=ex.art(path,size)
    # Irrigation gate and its clean backing remain separate for correct depth.
    gate_art=read('assets/story/venn/art.json')
    for legacy in [*gate_art['backgrounds'],*[p for seq in gate_art['animations'].values() for p in seq]]:
        previous=image(legacy);size=previous.size
        if legacy in gate_art['backgrounds']:
            im=materials.ground(size,set());im.alpha_composite(materials.channel('channel_05_from_n',0,'trickle'),(0,24))
        else:
            progress=1 if 'idle_open' in legacy else 0
            if 'opening' in legacy:
                seq=next(seq for seq in gate_art['animations'].values() if legacy in seq);progress=seq.index(legacy)/max(1,len(seq)-1)
            im=sluice(size,previous.getbbox(),progress)
            # The existing repair pin stays within the worker's natural reach.
            im.alpha_composite(prop('crank',(8,8)),(0,38))
        replacements[legacy]=ex.art(ex.png('scene_props/'+sha256(legacy.encode()).hexdigest()[:12],im),size)
    # Keep downstream route lookup/subsurface semantics at logical atlas coordinates.
    irrigation=read('assets/terrain/eldenmere/irrigation/tileset.json')
    for tick,frame in enumerate(irrigation['frames']):
        legacy='assets/terrain/eldenmere/irrigation/'+frame['image'];size=image(legacy).size;im=Image.new('RGBA',pixels(size))
        for route in irrigation['routes']:
            x,y,w,h=route['rect'];im.alpha_composite(materials.channel(route['id'],tick%6),(x*2,y*2))
        replacements[legacy]=ex.art(ex.png('scene_props/irrigation_'+str(tick),im),size)
    for tick in range(6):
        legacy=f'assets/terrain/eldenmere/terraces/spillway/frame_{tick+1:02}.png';replacements[legacy]=ex.art('assets/terrain/eldenmere/waterworks_hd/spillways/maintained/'+f'frame_{tick:02}.png',(24,48))
    for data in maps.values():data['art_replacements']={**replacements,**data.get('art_replacements',{})}
    # Overview is assembled from current native layers; no retained screenshot patch.
    for name,data in maps.items():
        if name in ('town','upstream'):
            overview=(base if name=='town' else ubase).copy();overview.alpha_composite((phases if name=='town' else uphases)[0])
        else:overview=ex.load(data['ground_frames'][0]).copy()
        for e in sorted(data['entities'],key=lambda r:(r['sort_y'],r.get('sort_priority',0))):
            path=e['frames'][0];im=ex.load(path)
            if e.get('artwork_pixels_per_world_pixel',data.get('artwork_pixels_per_world_pixel',1))==1:im=im.resize(pixels(im.size),Image.Resampling.NEAREST)
            overview.alpha_composite(im,pixels(e['position']))
            for d in data.get('doors',[]):
                if d.get('host')==e['id']:overview.alpha_composite(ex.load(d['frames'][0]),pixels(d['position']))
        for instance in data.get('grass',{}).get('instances',[]):
            variant=grass_manifest['tall_grass']['variants'][instance['variant']];pose=variant['idle'][0];x,y=instance['position']
            for layer in ('rear','front'):overview.alpha_composite(image(pose[layer]),pixels((x-12,y-28)))
        for layer in data.get('foreground',[]):overview.alpha_composite(ex.load(layer['image']),pixels(layer['position']))
        data['overview']=ex.png(name+'/overview',overview.resize(tuple(data['size_pixels']),Image.Resampling.NEAREST).convert('RGB'));ex.json(paths[name],data)
    ex.json(PACK+'/manifest.json',{'id':rec['id'],'integration_status':'integrated','artwork_pixels_per_world_pixel':2,'recipe':str((SRC/'recipe.json').relative_to(ROOT)),'recipe_sha256':sha256((SRC/'recipe.json').read_bytes()).hexdigest(),'scenes':paths,'businesses':rec['businesses'],'sources':rec['sources'],'exports':list(ex.records.values()),'services':'Building/interior integration; currency and merchant transactions remain a separate gameplay system.'})
    return ex.out

def build(check=False):
    result=products();stale=[]
    for path,raw in result.items():
        target=ROOT/path
        if not target.exists() or target.read_bytes()!=raw:
            stale.append(path)
            if not check:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    if check and stale:raise SystemExit('Stale town exports: '+', '.join(stale[:20]))
    from tools.export_caelan_scene_actions_hd import build as build_scene_poses
    build_scene_poses(check)
    print(f'{len(result)} Eldenmere exports '+('verified' if check else 'built'));return result
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');build(parser.parse_args().check)
