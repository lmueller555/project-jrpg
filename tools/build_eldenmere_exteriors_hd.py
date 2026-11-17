"""Build staged HD Eldenmere exteriors, authored door states and charm props.
All visible pixels derive from new retained drawings; live world data is read-only."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from functools import lru_cache
from pathlib import Path
import sys
from PIL import Image,ImageChops,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.build_world_water_hd import load,gray,clipped,encoded,rgba,save_loop
SOURCE=ROOT/'assets/source/terrain/eldenmere/exteriors_hd';PACK='assets/terrain/eldenmere/exteriors_hd';REVIEW='docs/reviews/eldenmere_exteriors_hd'

def recipe():return json.loads((SOURCE/'recipe.json').read_text())
def cutout(source,rect):
    im=source.crop(tuple(rect));a=Image.new('L',im.size);spill=Image.new('L',im.size)
    for y in range(im.height):
        for x in range(im.width):
            r,g,b,alpha=im.getpixel((x,y));key=r>210 and b>190 and g<80 and r>g+100 and b>g+100;a.putpixel((x,y),0 if key or alpha<128 else 255);spill.putpixel((x,y),255 if r>g+45 and b>g+35 and g<110 else 0)
    background=ImageChops.invert(a)
    for _ in range(4):background=ImageChops.lighter(background,ImageChops.multiply(background.filter(ImageFilter.MaxFilter(3)),spill))
    a=ImageChops.invert(background);im.putalpha(a);box=a.getbbox()
    if box is None:raise ValueError('Empty exterior source rectangle')
    return im.crop(box)

def split_registration(raw,r):
    """Keep upper roof plane whole; register lower facade around fixed portal."""
    w,h=raw.size;left,top,right,bottom=r['source_door_normalized'];sx=[0,round(left*w),round(right*w),w];sy=[0,round(top*h),round(bottom*h),h]
    bx,by,br,bb=[v*2 for v in r['body_bounds_logical']];dx,dy,dw,dh=[v*2 for v in r['door_rect_logical']];tx=[bx,dx,dx+dw,br];ty=[by,dy,dy+dh,bb];out=Image.new(raw.mode,tuple(v*2 for v in r['logical_size']))
    def place(box,target):
        x,y,right,bottom=target
        if right>x and bottom>y:out.paste(raw.crop(box).resize((right-x,bottom-y),Image.Resampling.NEAREST),(x,y))
    place((0,0,w,sy[1]),(bx,by,br,ty[1]))
    for row in (1,2):
        for col in range(3):place((sx[col],sy[row],sx[col+1],sy[row+1]),(tx[col],ty[row],tx[col+1],ty[row+1]))
    return out

def quantize(raw,rec,roof='slate',window_mask=None,roof_y=None,prop=None):
    p=rec['palette'];groups={k:[rgba(v) for v in ramp.values()] for k,ramp in p.items()};roof_colors=[rgba(c) for c in rec['roof_palettes'][roof].values()];ordinary=sum([groups[k] for k in ('stone','wood','iron','glass','plaster','flowers')],[])+roof_colors;out=Image.new('RGBA',raw.size);windows=Image.new('L',raw.size);cache={};outline=groups['outline'][0]
    green=lambda c:(c[1]>c[0]+8 and c[1]>c[2]+20) or (c[1]>=c[0]-12 and c[1]>c[2]+40)
    import statistics
    leaf_pixels=[c for c in raw.getdata() if c[3] and green(c)];leaf_median=[statistics.median(c[i] for c in leaf_pixels) if leaf_pixels else 0 for i in range(3)];leaf_base=rgba(p['leaves']['base'])
    for y in range(raw.height):
        for x in range(raw.width):
            c=raw.getpixel((x,y))
            if not c[3]:continue
            value=window_mask.getpixel((x,y)) if window_mask is not None else 0;pane=value>0;warm_allowed=value>200;upper=roof_y is not None and y<roof_y;key=c,pane,upper,warm_allowed
            if key not in cache:
                r,g,b,a=c;ramp=ordinary;light=False;corrected=c[:3]
                if max(r,g,b)<62:ramp=[outline]
                elif green(c):ramp=groups['leaves'];corrected=[leaf_base[i]+c[i]-leaf_median[i] for i in range(3)]
                elif prop and prop.startswith('awning_'):
                    if prop.endswith('blue') and b>r+8:ramp=[rgba(p['fabric'][k]) for k in ('blue_shadow','blue')]
                    elif prop.endswith('rust') and r>g+30:ramp=[rgba(p['fabric'][k]) for k in ('rust_shadow','rust')]
                elif pane and (b>r+5 or warm_allowed and r>190 and g>145 and r>g+25 and g>b+35):ramp=groups['lamplight'] if warm_allowed and r>g+25 and g>b+35 else groups['glass'];light=True
                elif upper and ((b>=g and b>=r-5) or roof=='terracotta' and r>g+45):ramp=roof_colors
                elif b>g+25 and r>g+25:ramp=groups['flowers']
                color=min(ramp,key=lambda v:sum((v[i]-corrected[i])**2 for i in range(3)));cache[key]=color,light
            color,light=cache[key];out.putpixel((x,y),color)
            if light:windows.putpixel((x,y),255)
    boundary=ImageChops.subtract(out.getchannel('A'),out.getchannel('A').filter(ImageFilter.MinFilter(3)));out.paste(Image.new('RGBA',out.size,outline),(0,0),boundary);windows=ImageChops.subtract(windows,boundary)
    return out,windows

def _audit_design(name):
    from tools.eldenmere_architecture_art import DESIGN_IDS,IDENTITIES
    return name in DESIGN_IDS or name in IDENTITIES

@lru_cache(maxsize=13)
def _audit_metadata(name):
    from tools.eldenmere_architecture_art import generate_architecture
    return generate_architecture(name).metadata

def building_structure(r,sources,rec):
    if _audit_design(r['id']):
        from tools.eldenmere_architecture_art import building_structure as native_architecture
        return native_architecture(r,sources,rec)
    raw=cutout(sources[r['source']],r['source_rect']);cover=Image.new('L',raw.size);draw=ImageDraw.Draw(cover)
    for a,b,c,d in r['window_regions_normalized']:draw.rectangle((int(a*raw.width),int(b*raw.height),int(c*raw.width),int(d*raw.height)),fill=255 if r['kind']=='home' else 128)
    warped=split_registration(raw,r);window_cover=split_registration(cover,r);native,windows=quantize(warped,rec,r['roof'],window_cover,roof_y=r['door_rect_logical'][1]*2-12)
    dx,dy,dw,dh=[v*2 for v in r['door_rect_logical']];native.paste((0,0,0,0),(dx,dy,dx+dw,dy+dh));windows.paste(0,(dx,dy,dx+dw,dy+dh))
    if r['id']=='mill':
        fence=prop_native(next(p for p in rec['props'] if p['id']=='fence_panel'),sources,rec).resize((48,36),Image.Resampling.NEAREST);native.alpha_composite(fence,(0,276))
    return native,windows

def door_sources(sources,rec):
    source=sources['doors_authored.png'];result={}
    for row,style in enumerate(('cottage','workshop','sanctuary')):
        seq=[]
        for col in range(5):
            cell=cutout(source,(col*source.width//5+3,row*source.height//3+3,(col+1)*source.width//5-3,(row+1)*source.height//3-3));a,b,c,d=rec['door_source_inner_normalized'][row];portal=cell.crop((round(a*cell.width),round(b*cell.height),round(c*cell.width),round(d*cell.height)));seq.append(portal)
        result[style]=seq
    return result

def effect_sources(sources,rec):
    source=sources['effects_authored.png'];pieces=[]
    for i in range(4):pieces.append(cutout(source,(i%2*source.width//2+3,i//2*source.height//2+3,(i%2+1)*source.width//2-3,(i//2+1)*source.height//2-3)))
    wheel=pieces[0];wheel.thumbnail((86,86),Image.Resampling.NEAREST);canvas=Image.new('RGBA',(96,96));canvas.alpha_composite(wheel,((96-wheel.width)//2,(96-wheel.height)//2));wheel,_=quantize(canvas,rec)
    glyphs=[];colors=[rgba(c) for c in rec['palette']['smoke'].values()]
    for piece in pieces[1:]:
        piece.thumbnail((12,18),Image.Resampling.NEAREST);im=Image.new('RGBA',(12,18));im.alpha_composite(piece,((12-piece.width)//2,18-piece.height))
        for y in range(18):
            for x in range(12):
                c=im.getpixel((x,y))
                if c[3]:im.putpixel((x,y),min(colors,key=lambda v:sum((v[i]-c[i])**2 for i in range(3))))
        glyphs.append(im)
    return wheel,glyphs

def smoke_layer(r,phase,glyphs):
    im=Image.new('RGBA',tuple(v*2 for v in r['logical_size']))
    if _audit_design(r['id']):
        emitter=_audit_metadata(r['id'])['smoke_emitter_logical']
        if emitter is None:return im
        emit_x,emit_y=[round(value*2) for value in emitter]
    else:
        if not r['smoke']:return im
        bx,by,br,bb=r['body_bounds_logical'];emit_x=round((bx+(br-bx)*r['chimney_normalized_x'])*2);emit_y=round(by*2+r['chimney_normalized_y']/r['source_door_normalized'][1]*(r['door_rect_logical'][1]*2-by*2))
    for i,age_offset in enumerate((0,6,12)):
        age=(phase+age_offset)%18
        if age>=16:continue
        im.alpha_composite(glyphs[i],(emit_x-6+age//4,emit_y-age*2-18))
    return im

def glow_layer(structure,mask,phase,rec):
    result=Image.new('RGBA',structure.size);colors=[rgba(c) for c in rec['palette']['lamplight'].values()];ink=colors[0]
    result.paste(Image.new('RGBA',result.size,ink),(0,0),mask);return result

def prop_native(r,sources,rec):
    raw=cutout(sources['props_authored.png'],r['source_rect']);raw.thumbnail((r['artwork_size'][0]-8,r['artwork_size'][1]-10),Image.Resampling.NEAREST);out=Image.new('RGBA',tuple(r['artwork_size']));x=(out.width-raw.width)//2;y=4 if r['mount']=='wall' else out.height-4-raw.height;out.alpha_composite(raw,(x,y));return quantize(out,rec,prop=r['id'])[0]

def prop_frame(native,r,phase,palette):
    if r['animation']=='static':return native.copy()
    offsets=[0,0,1,1,1,0,0,-1,-1,0,0,1,1,0,0,-1,-1,0];dx=offsets[phase];out=Image.new('RGBA',native.size)
    if r['animation']=='hanging':fixed=12
    elif r['id']=='laundry_line':fixed=native.height # Posts/line remain fixed; cloth gets a separate interior rustle.
    else:fixed=max(16,native.getbbox()[3]-8)
    out.alpha_composite(native.crop((0,0,native.width,fixed)),(0,0));out.alpha_composite(native.crop((0,fixed,native.width,native.height)),(dx,fixed))
    if r['id']=='laundry_line':
        # Move only a small cloth interior, retaining poles, rope and attachment.
        rect=(native.width//3,16,native.width*2//3,native.height-10);patch=native.crop(rect);out.alpha_composite(patch,(rect[0]+dx,rect[1]))
    if r['id'].startswith('sign_'):
        iron={rgba(v) for v in palette['iron'].values()}|{rgba(palette['outline']['base'])}
        for y in range(native.height//2):
            for x in range(native.width):
                if native.getpixel((x,y)) in iron:out.putpixel((x,y),native.getpixel((x,y)))
    return out

def products():
    rec=recipe();out={};exports=[]
    for r in rec['sources']:
        if sha256((SOURCE/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Changed exterior source '+r['file'])
    def export(path,im):
        raw=encoded(im);out[path]=raw;exports.append({'file':path,'artwork_size':list(im.size),'sha256':sha256(raw).hexdigest()})
    def doc(path,data):out[path]=(json.dumps(data,indent=2)+'\n').encode()
    sources={r['file']:load(SOURCE/r['file']) for r in rec['sources']};doors=door_sources(sources,rec);wheel,glyphs=effect_sources(sources,rec);records=[];images={};ambient={};native_doors={};prop_records=[];props={}
    for i,glyph in enumerate(glyphs):export(PACK+f'/effects/smoke_{i}.png',glyph)
    export(PACK+'/mill/wheel_idle.png',wheel);hub=Image.new('RGBA',(96,96));hub_mask=Image.new('L',(96,96));ImageDraw.Draw(hub_mask).ellipse((40,40,55,55),fill=255);hub=clipped(wheel,hub_mask);export(PACK+'/mill/fixed_hub.png',hub);wheels=[]
    for phase in range(48):
        frame=wheel.rotate(-phase*7.5,resample=Image.Resampling.NEAREST,center=(48,48));frame.alpha_composite(hub);wheels.append(frame);export(PACK+f'/mill/wheel/frame_{phase:02}.png',frame)
    for r in rec['designs']:
        name=r['id'];prefix='buildings/'+name;structure,window_mask=building_structure(r,sources,rec);export(PACK+'/'+prefix+'/structure.png',structure);export(PACK+'/'+prefix+'/window_mask.png',window_mask);size=structure.size;door_paths=[];composed=[]
        dx,dy,dw,dh=[v*2 for v in r['door_rect_logical']]
        for phase,raw in enumerate(doors[r['door_style']]):
            door,_=quantize(raw.resize((dw,dh),Image.Resampling.NEAREST),rec,r['roof']);path=prefix+f'/doors/frame_{phase:02}.png';export(PACK+'/'+path,door);door_paths.append(path);native_doors[name,phase]=door;image=structure.copy();image.alpha_composite(door,(dx,dy))
            if name=='mill':image.alpha_composite(wheels[0],(176,188))
            composed.append(image)
        export(PACK+'/'+prefix+'/closed.png',composed[0]);export(PACK+'/'+prefix+'/open.png',composed[-1]);images[name]=composed;sheet=Image.new('RGBA',(size[0]*5,size[1]))
        for i,image in enumerate(composed):sheet.alpha_composite(image,(i*size[0],0))
        export(PACK+'/'+prefix+'/door_sheet.png',sheet);frames=[];fx_paths=[]
        for phase in range(18):
            smoke=smoke_layer(r,phase,glyphs);glow=glow_layer(structure,window_mask,phase,rec);frame=composed[0].copy();frame.alpha_composite(glow);frame.alpha_composite(smoke);path=prefix+f'/ambient/frame_{phase:02}.png';export(PACK+'/'+path,frame);frames.append(frame)
            sp=prefix+f'/smoke/frame_{phase:02}.png';gp=prefix+f'/windowlight/frame_{phase:02}.png';export(PACK+'/'+sp,smoke);export(PACK+'/'+gp,glow);fx_paths.append({'smoke':sp,'windowlight':gp})
        ambient[name]=frames
        record={k:r[k] for k in ('id','kind','shape','profile','logical_size','ground_rect_logical','door_rect_logical','roof','charm')};w,h=r['logical_size'];record.update(artwork_pixels_per_world_pixel=2,artwork_size=[w*2,h*2],draw_anchor_logical=[0,0],depth_baseline_logical=r['ground_rect_logical'][1]+r['ground_rect_logical'][3],structure=prefix+'/structure.png',closed=prefix+'/closed.png',open=prefix+'/open.png',door_sheet=prefix+'/door_sheet.png',window_mask=prefix+'/window_mask.png',door={'frames':[{'file':p,'duration_ms':100} for p in door_paths],'position_logical':r['door_rect_logical'][:2],'logical_size':r['door_rect_logical'][2:],'hinge':'both outer jambs' if r['door_style']=='sanctuary' else 'west','loop':False,'hold_closed':0,'hold_open':4,'closing_order':[4,3,2,1,0]},ambient={'frames':[{'file':prefix+f'/ambient/frame_{p:02}.png','duration_ms':200} for p in range(18)],'effects':fx_paths,'cycle_ms':3600,'smoke_optional':_audit_metadata(name)['smoke_emitter_logical'] is not None if _audit_design(name) else r['smoke'],'reduced_motion':prefix+'/closed.png','note':'Windowlight is steady localized warm light; omit in daylight/reduced motion. Wheel uses an independent 9.6-second clock.'},wheel={'frames':[{'file':f'mill/wheel/frame_{p:02}.png','duration_ms':200} for p in range(48)],'position_logical':[88,94],'logical_size':[48,48],'axle_center_logical':[112,118],'clockwise':True,'step_degrees':7.5,'full_turn_ms':9600,'fixed_hub':'mill/fixed_hub.png'} if name=='mill' else None,extra_static_components=[],collision='Preserve authoritative logical geometry during integration; never infer it from alpha.',interaction_cues=False,door_approach_local_logical=[r['door_rect_logical'][0]-4,r['door_rect_logical'][1],r['door_rect_logical'][2]+8,h-r['door_rect_logical'][1]+12])
        if _audit_design(name):record['architecture_audit']=_audit_metadata(name)
        records.append(record)
    for r in rec['props']:
        name=r['id'];native=prop_native(r,sources,rec);sequence=[prop_frame(native,r,p,rec['palette']) for p in range(18)] if r['animation']!='static' else [native];props[name]=sequence;export(PACK+f'/props/{name}/idle.png',native);paths=[]
        for phase,frame in enumerate(sequence):path=f'props/{name}/frame_{phase:02}.png';export(PACK+'/'+path,frame);paths.append(path)
        prop_records.append({**r,'source_rect':r['source_rect'],'idle':f'props/{name}/idle.png','frames':paths,'frame_duration_ms':200 if len(sequence)>1 else None,'cycle_ms':3600 if len(sequence)>1 else None,'draw_anchor_logical':[v/2 for v in r['anchor_artwork']],'depth_baseline_logical':r['anchor_artwork'][1]/2,'collision':'not_registered','interaction_cues':False,'passability':'No gate/prop gameplay is registered; closed appearance only.' if name=='garden_gate' else 'No automatic collision from artwork.'})
    animated_props=[r for r in prop_records if r['animation']!='static'];prop_boards=[]
    for phase in range(18):
        board=Image.new('RGB',(720,340),'#e8e9df');draw=ImageDraw.Draw(board)
        for i,r in enumerate(animated_props):
            image=props[r['id']][phase];view=image.resize((image.width*2,image.height*2),Image.Resampling.NEAREST);x=i%4*180+(180-view.width)//2;y=i//4*170+8;board.paste(view,(x,y),view);draw.text((i%4*180+4,i//4*170+148),r['id'],fill='#243529')
        export(REVIEW+f'/props_motion/frame_{phase:02}.png',board);prop_boards.append(board)
    out[REVIEW+'/props_motion.gif']=save_loop(prop_boards,200)
    # Static family boards are native-density crops, not rescaled game scenes.
    houses=[r for r in rec['designs'] if r['kind']=='home'];board=Image.new('RGB',(900,((len(houses)+2)//3)*320),'#e8e9df');draw=ImageDraw.Draw(board)
    for i,r in enumerate(houses):
        x=i%3*300+(300-images[r['id']][0].width)//2;y=i//3*320;image=images[r['id']][0];board.paste(image,(x,y),image);draw.text((i%3*300+8,y+294),r['id'],fill='#243529')
    export(REVIEW+'/cottages_native.png',board)
    board=Image.new('RGB',(900,880),'#e8e9df');draw=ImageDraw.Draw(board)
    for i,name in enumerate(('mira','mill','school','sanctuary')):
        image=images[name][0];x=i%2*450+(450-image.width)//2;y=i//2*440;board.paste(image,(x,y),image);draw.text((i%2*450+8,y+416),name,fill='#243529')
    export(REVIEW+'/landmarks_native.png',board)
    board=Image.new('RGB',(6*170,4*170),'#e8e9df');draw=ImageDraw.Draw(board)
    for i,r in enumerate(prop_records):
        image=props[r['id']][0];view=image.resize((image.width*2,image.height*2),Image.Resampling.NEAREST);x=i%6*170+(170-view.width)//2;y=i//6*170+8;board.paste(view,(x,y),view);draw.text((i%6*170+4,i//6*170+148),r['id'],fill='#243529')
    export(REVIEW+'/props_review.png',board)
    for name in ('standard_gardener','standard_craft','standard_weathered','mira','sanctuary'):
        sequence=[]
        for phase,frame in enumerate(ambient[name]):
            backdrop=Image.new('RGB',frame.size,'#2c7c50');backdrop.paste(frame,(0,0),frame);export(REVIEW+f'/ambient/{name}/frame_{phase:02}.png',backdrop);sequence.append(backdrop)
        out[REVIEW+'/'+name+'_ambience.gif']=save_loop(sequence,200)
    door_schedule=[0,1,2,3,4,4,3,2,1,0];door_times=[600,100,100,100,600,600,100,100,100,600];sequence=[]
    for tick,index in enumerate(door_schedule):
        board=Image.new('RGB',(1008,456),'#e8e9df');draw=ImageDraw.Draw(board);offset_x=0
        for i,name in enumerate(('standard_gardener','mira','sanctuary')):
            image=images[name][index];board.paste(image,(offset_x,0),image);draw.text((offset_x+5,438),name+' / state '+str(index),fill='#243529');offset_x+=image.width
        export(REVIEW+f'/doors/frame_{tick:02}.png',board);sequence.append(board)
    out[REVIEW+'/doors.gif']=save_loop(sequence,door_times)
    millframes=[];mill_structure=load_from_result(out,PACK+'/buildings/mill/structure.png');mill_structure.alpha_composite(native_doors['mill',0],(52,214))
    for phase,wheel_frame in enumerate(wheels):
        frame=mill_structure.copy();frame.alpha_composite(wheel_frame,(176,188));bg=Image.new('RGB',frame.size,'#2c7c50');bg.paste(frame,(0,0),frame);export(REVIEW+f'/mill/frame_{phase:02}.png',bg);millframes.append(bg)
    out[REVIEW+'/mill_wheel.gif']=save_loop(millframes,200)
    # Native 960x640 representative compositions; no legacy building pixels reused.
    gm=json.loads((ROOT/'assets/terrain/eldenmere/grass_dirt_hd/tileset.json').read_text());ground=ROOT/'assets/terrain/eldenmere/grass_dirt_hd';grass=[load(ground/p) for p in gm['materials']['grass']];dirt=[load(ground/p) for p in gm['materials']['dirt']];scenes=[]
    fixtures=[('cottage_lane',[('compact_gardener',[24,80]),('standard_craft',[288,80]),('wide_weathered',[600,80])],[('rain_barrel',[30,410]),('watering_can',[240,400]),('orchard_basket',[530,412]),('fence_panel',[760,455]),('garden_gate',[842,455]),('wood_shavings',[510,400])]),('workshop_yard',[('mira',[180,90])],[('firewood',[140,430]),('broom',[535,420]),('stool',[620,440]),('wood_shavings',[550,450]),('rain_barrel',[110,420]),('orchard_basket',[680,420])]),('school_and_sanctuary',[('school',[0,30]),('sanctuary',[480,20])],[('herb_pot',[470,480]),('boots',[420,460]),('flowerpot_pair',[930,490])])]
    for scene_id,placements,prop_placements in fixtures:
        scene=Image.new('RGBA',(960,640))
        for y in range(14):
            for x in range(20):scene.alpha_composite(dirt[0] if 8<=y<=10 else grass[(x//3+y//4)%4],(x*48,y*48))
        for name,pos in placements:scene.alpha_composite(images[name][0],tuple(pos))
        pp=[]
        for name,root in prop_placements:
            r=next(r for r in prop_records if r['id']==name);anchor=r['anchor_artwork'];pos=[root[i]-anchor[i] for i in (0,1)];scene.alpha_composite(props[name][0],tuple(pos));pp.append({'id':name,'root_artwork':root,'position_artwork':pos})
        actors=[{'file':'assets/characters/caelan/review_hd/idles/idle_front.png','position_artwork':[425,480]},{'file':'assets/characters/iselin/idle_front_42x72.png','position_artwork':[490,480]}]
        for actor in actors:scene.alpha_composite(load(ROOT/actor['file']),tuple(actor['position_artwork']))
        export(REVIEW+'/'+scene_id+'_native.png',scene);scenes.append({'id':scene_id,'size_artwork':[960,640],'ground_rule':'Dirt rows 8..10; grass arrangement (x//3+y//4)%4 elsewhere.','buildings':[{'id':name,'position_artwork':pos} for name,pos in placements],'props':pp,'actors':actors})
    meta={'version':1,'id':rec['id'],'artwork_state':'rebuilt','integration_status':'not_integrated','visual_approval':rec['visual_approval'],'artwork_pixels_per_world_pixel':2,'path_conventions':{'asset_files':'pack_relative','recipe_and_legacy_references':'repository_relative'},'rect_space':'artwork unless explicitly logical-suffixed','anchor_space':'logical unless explicitly artwork-suffixed','buildings':records,'props':prop_records,'bindings':rec['existing_building_audit'],'palette':'palette.json','recipe':'assets/source/terrain/eldenmere/exteriors_hd/recipe.json','activation':'No runtime, map, collision, navigation, door transitions, quest eligibility or save changes.','integration_followup':'Preserve bindings, entry anchors, width, sort_y, destinations, open/close behavior, pause/focus and reduced motion. Replace consumers explicitly; do not infer collision from silhouettes.'}
    meta['native_architecture_source']={'generator':'tools/eldenmere_architecture_art.py','recipe':'assets/source/terrain/eldenmere/exteriors_hd/architecture_audit/recipe.json','recipe_sha256':sha256((ROOT/'assets/source/terrain/eldenmere/exteriors_hd/architecture_audit/recipe.json').read_bytes()).hexdigest(),'selected_live_designs':[r['id'] for r in records if r.get('architecture_audit')],'status':'Native shells selected for live town consumers; unused legacy variants retain their existing staged path.'};doc(PACK+'/manifest.json',meta);doc(PACK+'/palette.json',{'materials':rec['palette'],'roof_palettes':rec['roof_palettes']});doc(REVIEW+'/audit.json',{'baseline_commit':rec['baseline_commit'],'live_consumers':rec['existing_building_audit'],'scope':'Existing buildings only; no new canonical shops or destinations.'});doc(REVIEW+'/layout.json',{'presentation':'Offline native-density compositions, not gameplay captures.','scenes':scenes,'door_review':{'schedule':door_schedule,'durations_ms':door_times}});doc(REVIEW+'/exports.json',{'builder':rec['builder'],'sources':rec['sources'],'recipe_sha256':sha256((SOURCE/'recipe.json').read_bytes()).hexdigest(),'outputs':exports});return out

def load_from_result(result,path):
    from io import BytesIO
    with Image.open(BytesIO(result[path])) as im:return im.convert('RGBA')
def build(check=False):
    result=products();stale=[]
    for path,raw in result.items():
        p=ROOT/path
        if not p.exists() or p.read_bytes()!=raw:
            stale.append(path)
            if not check:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    if check and stale:raise SystemExit('Stale exterior exports: '+', '.join(stale))
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args();print(f'{len(build(args.check))} exterior exports '+('verified' if args.check else 'built'))
