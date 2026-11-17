#!/usr/bin/env python3
"""Stage Rising Rain artwork and deterministic offline previews; no game activation."""
from __future__ import annotations
import argparse
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/overworld/elden_vale/rising_rain_hd'
OUT=ROOT/'assets/terrain/overworld/elden_vale/rising_rain_hd'
REVIEW=ROOT/'docs/reviews/elden_vale_rising_rain_hd'
TIMELINE=[('signs',0,2000),('arrival',2000,4500),('peak',4500,9000),('departure',9000,12000)]

def png(image):
    buffer=BytesIO();image.save(buffer,format='PNG',optimize=True);return buffer.getvalue()
def packed(data):return (json.dumps(data,indent=2)+'\n').encode()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def clean(image,threshold=160):
    image=image.convert('RGBA');alpha=image.getchannel('A').point(lambda a:255 if a>=threshold else 0)
    image=image.convert('RGB').quantize(colors=48,dither=Image.Dither.NONE).convert('RGBA');image.putalpha(alpha)
    return image

def cell(sheet,index,rows):
    col,row=index%4,index//4
    return sheet.crop((round(col*sheet.width/4),round(row*sheet.height/rows),round((col+1)*sheet.width/4),round((row+1)*sheet.height/rows)))

def fit(image,size,threshold=160):
    image=clean(image,threshold);box=image.getbbox()
    if box is None:raise ValueError('Empty drawn cell')
    image=image.crop(box);factor=min((size[0]-4)/image.width,(size[1]-4)/image.height)
    image=image.resize((max(1,round(image.width*factor)),max(1,round(image.height*factor))),Image.Resampling.NEAREST)
    canvas=Image.new('RGBA',size);canvas.alpha_composite(image,((size[0]-image.width)//2,size[1]-2-image.height))
    return canvas

def phase_at(time_ms):
    if not math.isfinite(time_ms) or time_ms<0:raise ValueError('Preview time must be finite and nonnegative')
    return next((name for name,start,end in TIMELINE if start<=time_ms<end),'aftermath')

def action_state(clip,time_ms):
    """Pure seekable preview state. No receipts, saves or game-controller mutation."""
    if not math.isfinite(time_ms) or time_ms<0:raise ValueError('Invalid preview time')
    frame=min(len(clip['frames'])-1,int(time_ms//clip['frame_duration_ms']))
    owner='station'
    state='folded' if clip['action']=='gather' else ('folded' if clip['action']=='deploy' else 'lowered')
    for cue in clip['ownership_cues']:
        if frame>=cue['frame']:owner,state=cue['owner'],cue['state']
    return {'frame':frame,'owner':owner,'state':state,'visible_instances':1}

def build(check=False):
    products={};dependencies={};images={}
    def depend(path):dependencies[str(path.relative_to(ROOT))]=sha(path)
    def emit(path,image):products[path]=png(image)
    depend(Path(__file__));depend(SOURCE/'identity_reference.png');depend(SOURCE/'generation_brief.json')
    manifest={'id':'elden_vale.rising_rain.hd','integration_status':'not_integrated','visual_approval':'not_reviewed_by_user',
              'artwork_pixels_per_world_pixel':2,'anchor_space':'logical','path_space':'repository_relative',
              'effects':{},'props':{},'actions':{},'wildlife':{},'cartography':{},
              'preview_timeline_ms':TIMELINE,'preview_duration_ms':12000,
              'cadence':'Preview only; production recurrence and first-encounter triggers unimplemented.',
              'lifecycle':{'pause_focus':'freeze clocks without catchup','exit':'clear transient instances',
                           'resume':'reconstruct eligibility; no pending particle bursts','reduced_motion':'dedicated stills'},
              'gameplay_effects':[]}
    def asset(name,image,kind,**extra):
        path=OUT/kind/f'{name}.png';emit(path,image);images[name]=image
        record={'image':str(path.relative_to(ROOT)),'logical_size':[image.width/2,image.height/2],
                'draw_anchor_logical':[image.width/4,image.height/2-1],
                'collision':'none; staged visual only','interaction_cues':False,**extra}
        manifest[kind][name]=record
        return record
    weather_path=SOURCE/'weather_master.png';depend(weather_path);weather=Image.open(weather_path)
    effects=[('bead_rest',(8,10)),('bead_gather',(8,12)),('bead_detach',(8,14)),('bead_lift',(8,16)),
             ('ascent_0',(24,48)),('ascent_1',(24,48)),('ascent_2',(24,48)),('ascent_3',(24,48)),
             ('curtain_sparse',(96,192)),('curtain_dense',(96,192)),('canopy_strands',(192,128)),('high_veil',(384,128)),
             ('wet_ground',(64,24)),('wet_fence',(48,16)),('still_beads',(48,48)),('still_veil',(384,128))]
    for index,(name,size) in enumerate(effects):
        mist=name in ('canopy_strands','high_veil','still_veil','wet_ground')
        record=asset(name,fit(cell(weather,index,4),size,32 if mist else 120),'effects',
                     opacity=64 if mist else 180,alpha_policy='hard mask plus explicit whole-layer opacity',
                     source_cell=index,reduced_motion=name in ('still_beads','still_veil','wet_ground'))
    prop_path=SOURCE/'props_master.png';depend(prop_path);sheet=Image.open(prop_path)
    specs=[('cloth_folded',(24,16)),('cloth_carried',(24,24)),('cloth_panel',(72,40)),('cloth_panel_angled',(72,40)),
           ('post_left',(24,80)),('post_right',(24,80)),('ties',(16,16)),('leaf_raised',(24,24)),
           ('leaf_lowered',(24,16)),('cloth_blue_folded',(24,16)),('cloth_blue_bundle',(24,24)),('washing_basket',(40,32))]
    for index,(name,size) in enumerate(specs):
        record=asset(name,fit(cell(sheet,index,3),size),'props',source_cell=index,
                     ground_anchor_logical=[size[0]/4,(size[1]-2)/2],depth_baseline_logical=(size[1]-2)/2)
        record['grip_anchor_logical']=[size[0]/4,1] if name.startswith('cloth') else [6,11]
        if name.startswith('post'):
            box=images[name].getbbox()
            record['peg_anchor_logical']=[(box[2]-2 if name=='post_left' else box[0]+2)/2,(box[1]+(box[3]-box[1])*.16)/2]
            record['fixed_support']=True
        if name=='leaf_lowered':record['grip_anchor_logical']=[11,4]
        if name=='leaf_raised':record['grip_anchor_logical']=[6,11]
    # A separate carried-open panel is a technical uniform sample of the drawn panel.
    asset('cloth_held_open',fit(cell(sheet,3,3),(40,24)),'props',grip_anchor_logical=[18,4])
    asset('leaf_cup_right',images['leaf_lowered'].transpose(Image.Transpose.FLIP_LEFT_RIGHT),'props',grip_anchor_logical=[1,4],source_asset='leaf_lowered; mirrored flat prop, no actor mirroring')
    manifest['assemblies']={'collection_station':{
        'coordinate_space':'logical; relative to preview actor canvas origin',
        'pegs':[[9.5,32],[34.5,32]],'panel_origin':[2.5,29],
        'parts':['post_left','post_right','cloth_panel'],'supports':'fixed; only panel changes owner',
        'far_corner':'pre-tethered before securing near corner; no remote left-post grab'}}
    clip_specs={
        'gather':('npcs/female_01',68,[{'frame':4,'owner':'actor','state':'carried'}]),
        'deploy':('npcs/male_02',68,[{'frame':1,'owner':'actor','state':'folded'},{'frame':3,'owner':'actor','state':'opening'},{'frame':5,'owner':'station','state':'deployed'}]),
        'leaf':('liam',52,[{'frame':2,'owner':'actor','state':'raised'},{'frame':7,'owner':'station','state':'lowered'}])}
    grips={
        'gather':[[54,81],[54,75],[60,81],[59,85],[56,78],[54,73],[55,73],[55,74]],
        'deploy':[[53,78],[54,75],[56,68],[65,67],[66,66],[67,64],[63,68],[54,81]],
        'leaf':[[53,90],[57,86],[55,83],[55,81],[57,77],[57,78],[54,83],[53,87]]}
    # A single scale per strip preserves body size while the actor bends/reaches.
    for action,(actor_id,body_height,cues) in clip_specs.items():
        identity=ROOT/'assets/characters'/actor_id/'idle_right.png';depend(identity)
        path=SOURCE/f'{action}_master.png';depend(path);sheet=Image.open(path)
        crops=[clean(cell(sheet,index,2)) for index in range(8)]
        scale=body_height/(crops[0].getbbox()[3]-crops[0].getbbox()[1])
        folder=ROOT/'assets/characters'/actor_id/'rising_rain_hd'/action
        clip={'action':action,'actor':actor_id,'integration_status':'not_integrated','artwork_pixels_per_world_pixel':2,
              'logical_size':[48,56],'draw_anchor_logical':[24,52],'foot_anchor_logical':[24,52],
              'body_height_artwork':body_height,'source_scale':scale,'frame_duration_ms':220,'loop':False,
              'ownership_cues':cues,'frames':[],'prop_space':'logical, local to 48x56 canvas',
              'facing':'right','approach':'reuse existing right walk at its current legacy density in preview only',
              'completion':'gather remains carrying; deploy leaves panel; leaf returns to station',
              'registration':'one source scale; sole centers aligned; no anatomy deformation'}
        stations={'gather':[30.5,43],'deploy':[28.5,39],'leaf':[28.5,44]}
        clip['station_grip_logical']=stations[action]
        clip['placement_peg_logical']=[34.5,32] if action=='deploy' else None
        for cue in clip['ownership_cues']:
            cue['contact_position_logical']=None if cue['state']=='opening' else (clip['placement_peg_logical'] if action=='deploy' and cue['state']=='deployed' else stations[action])
        for index,crop in enumerate(crops):
            box=crop.getbbox();x0,y0,x1,y1=box
            # Feet anchor uses a small sole band, independent of reaching arms.
            band=crop.getchannel('A').crop((0,y1-max(3,round((y1-y0)*.04)),crop.width,y1)).getbbox()
            foot_x=(band[0]+band[2])/2
            crop=crop.crop(box).resize((round((x1-x0)*scale),round((y1-y0)*scale)),Image.Resampling.NEAREST)
            target=Image.new('RGBA',(96,112));origin=[round(48-(foot_x-x0)*scale),104-crop.height]
            if origin[0]<0 or origin[1]<0 or origin[0]+crop.width>96:raise ValueError('Action pose clipped')
            target.alpha_composite(crop,origin)
            frame_path=folder/f'frame_{index:02}.png';emit(frame_path,target)
            clip['frames'].append({'image':str(frame_path.relative_to(ROOT)),'duration_ms':220,
                                   'grip_logical':[n/2 for n in grips[action][index]],'source_cell':index})
            images[f'{action}_{index}']=target
        native_sheet=Image.new('RGBA',(8*96,112))
        for index in range(8):
            native_sheet.alpha_composite(images[f'{action}_{index}'],(index*96,0))
            clip['frames'][index]['sheet_rect_artwork']=[index*96,0,96,112]
        sheet_path=folder/'spritesheet.png';emit(sheet_path,native_sheet);clip['sheet']=str(sheet_path.relative_to(ROOT))
        bank_path=folder/'animation.json';products[bank_path]=packed(clip)
        manifest['actions'][action]={'bank':str(bank_path.relative_to(ROOT)),**clip}
    bird_path=SOURCE/'bird_master.png';depend(bird_path);sheet=Image.open(bird_path)
    raw=[clean(cell(sheet,index,4)) for index in range(16)]
    bird_reference=ROOT/'assets/characters/regional_wildlife/bird_land_right_0.png';depend(bird_reference)
    reference_box=Image.open(bird_reference).getbbox()
    target_height=2*(reference_box[3]-reference_box[1])
    box=raw[0].getbbox();scale=target_height/(box[3]-box[1]);bird_folder=ROOT/'assets/characters/regional_wildlife/rising_rain_hd'
    def breast_center(image):
        points=[]
        pixels=image.load()
        for y in range(image.height):
            for x in range(image.width):
                r,g,b,a=pixels[x,y]
                if a and r>180 and g>150 and b>110 and b>r*.6:points.append((x,y))
        if not points:raise ValueError('Missing bird body landmark')
        return [sum(p[i] for p in points)/len(points) for i in (0,1)]
    reference_breast=breast_center(raw[0]);breast_y=48-(box[3]-reference_breast[1])*scale
    bird_frames=[]
    for index,crop in enumerate(raw):
        box=crop.getbbox();x0,y0,x1,y1=box;bx,by=breast_center(crop)
        crop=crop.crop(box).resize((round((x1-x0)*scale),round((y1-y0)*scale)),Image.Resampling.NEAREST)
        origin=[round(32-(bx-x0)*scale),round(breast_y-(by-y0)*scale)]
        if min(origin)<0 or origin[0]+crop.width>64 or origin[1]+crop.height>64:raise ValueError('Bird wing clipped')
        image=Image.new('RGBA',(64,64));image.alpha_composite(crop,origin)
        path=bird_folder/f'frame_{index:02}.png';emit(path,image);bird_frames.append(str(path.relative_to(ROOT)));images[f'bird_{index}']=image
    bird={'artwork_pixels_per_world_pixel':2,'integration_status':'not_integrated','logical_size':[32,32],
          'anchor_logical':[16,24],'body_anchor_logical':[16,breast_y/2],'facing':'right','clips':{'perch':{'frames':bird_frames[:1],'duration_ms':800,'loop':True},
          'alert':{'frames':bird_frames[1:4],'duration_ms':180,'loop':False},
          'takeoff':{'frames':bird_frames[4:8],'duration_ms':100,'loop':False},
          'flight':{'frames':bird_frames[8:16],'duration_ms':100,'loop':True}},
          'reduced_motion':bird_frames[0],'existing_actor_ids':'unchanged; no animal placement or save changes'}
    native_sheet=Image.new('RGBA',(256,256))
    bird['sheet_rects_artwork']={}
    for index,path in enumerate(bird_frames):
        x,y=(index%4)*64,(index//4)*64;native_sheet.alpha_composite(images[f'bird_{index}'],(x,y))
        bird['sheet_rects_artwork'][path]=[x,y,64,64]
    sheet_path=bird_folder/'spritesheet.png';emit(sheet_path,native_sheet);bird['sheet']=str(sheet_path.relative_to(ROOT))
    products[bird_folder/'animation.json']=packed(bird);manifest['wildlife']=bird
    # Cartography retains its own 64px UI slot; world-density scaling does not apply.
    symbols=ROOT/'assets/cartography/elden_vale/rising_rain_hd'
    donors={'pale_antlers':ROOT/'assets/terrain/overworld/elden_vale/signature_landscape_hd/antlers/antlers_regional.png',
            'causeway_ruin':ROOT/'assets/terrain/overworld/elden_vale/signature_landscape_hd/causeway/arch_complete.png'}
    for name,path in donors.items():
        depend(path);image=fit(Image.open(path),(64,64));symbol_path=symbols/f'{name}.png';emit(symbol_path,image);images[name]=image
        manifest['cartography'][name]={'image':str(symbol_path.relative_to(ROOT)),'display_size':[64,64],
                                      'coordinate_space':'cartography artwork pixels','activation':'staged only; atlas unchanged'}
    symbol_path=symbols/'rising_rain_optional.png';image=fit(images['ascent_3'],(64,64),80);emit(symbol_path,image)
    manifest['cartography']['rising_rain_optional']={'image':str(symbol_path.relative_to(ROOT)),
        'display_size':[64,64],'optional':True,'activation':'no live forecast or event indicator implied'}
    # Review artwork and deterministic preview timelines.
    board=Image.new('RGBA',(1024,((len(images)+7)//8)*150),'#d7dfd0');draw=ImageDraw.Draw(board)
    for index,(name,image) in enumerate(images.items()):
        factor=min(1,116/image.width,116/image.height);shown=image.resize((round(image.width*factor),round(image.height*factor)),Image.Resampling.NEAREST)
        x,y=index%8*128,index//8*150;board.alpha_composite(shown,(x+(128-shown.width)//2,y+120-shown.height));draw.text((x+2,y+128),name,fill='black')
    products[REVIEW/'asset_board.png']=png(board)
    for action,clip in manifest['actions'].items():
        strip=Image.new('RGBA',(8*192,248),'#c8d4c0');draw=ImageDraw.Draw(strip)
        for index,frame in enumerate(clip['frames']):
            image=images[f'{action}_{index}'].resize((192,224),Image.Resampling.NEAREST)
            strip.alpha_composite(image,(index*192,0));draw.text((index*192+8,230),f'{index}  {index*220}ms',fill='black')
        products[REVIEW/f'{action}_poses.png']=png(strip)
    # Delegate reusable preview composition to functions below; no runtime import.
    for name,data in make_previews(manifest,images,depend).items():products[REVIEW/name]=data
    products[OUT/'manifest.json']=packed(manifest)
    products[SOURCE/'recipe.json']=packed({'id':manifest['id'],'sources':dependencies,'density':2,
        'processing':'cell crops, quantization, hard alpha, one uniform action scale, sole registration, technical composition',
        'mist':'hard source masks at alpha threshold 32, explicit whole-layer opacity 64/255; not accidental soft alpha',
        'scope':'staged weather, props, reference-based actions, bird, map icons; no live weather controller or new rewards'})
    stale=[]
    for path,data in products.items():
        if check:
            if not path.exists() or path.read_bytes()!=data:stale.append(str(path.relative_to(ROOT)))
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    if stale:raise SystemExit('Stale exports: '+', '.join(stale))
    print(f'{"Verified" if check else "Exported"} {len(products)} Rising Rain products')

def gif_bytes(frames,duration,loop=False):
    # One palette across frames prevents stationary scenery from changing colors.
    study=Image.new('RGB',(8*240,math.ceil(len(frames)/8)*160))
    for i,image in enumerate(frames):study.paste(image.convert('RGB').resize((240,160),Image.Resampling.NEAREST),(i%8*240,i//8*160))
    palette=study.quantize(colors=256,dither=Image.Dither.NONE)
    indexed=[image.convert('RGB').quantize(palette=palette,dither=Image.Dither.NONE) for image in frames]
    buffer=BytesIO();options={'loop':0} if loop else {}
    indexed[0].save(buffer,format='GIF',save_all=True,append_images=indexed[1:],duration=duration,disposal=2,optimize=False,**options)
    return buffer.getvalue()

def weather_instances(time_ms,reduced_motion=False):
    phase=phase_at(time_ms)
    if reduced_motion:return [{'asset':'still_beads','position':[150,390]},{'asset':'still_veil','position':[360,100]}]
    if phase in ('signs','aftermath'):return []
    intensity=min(1,max(0,(time_ms-2000)/2500)) if phase!='departure' else max(0,(12000-time_ms)/3000)
    result=[]
    # Seeded-by-index placements and elapsed time, no random reroll or hidden clock.
    for index in range(round(180*intensity)):
        x=35+(index*137)%880
        # Protect a broad central travel/interaction band in the offline study.
        if 380<x<550:continue
        age=(time_ms-2000+index*173)%6000
        y=590-age*.07
        result.append({'asset':'bead_lift' if index%3 else 'ascent_'+str((int(time_ms//250)+index)%4),
                       'position':[x,y],'id':index,'opacity':130 if index%3 else 110})
    if phase in ('peak','departure'):
        veil_amount=min(intensity,max(0,(time_ms-4500)/1000))
        result.extend([{'asset':'curtain_sparse','position':[120,300-(time_ms-4500)*.025],'opacity':round(110*veil_amount)},
                       {'asset':'curtain_dense','position':[690,280-(time_ms-4500)*.02],'opacity':round(80*veil_amount)},
                       {'asset':'high_veil','position':[300+12*math.sin(time_ms/2500),100-(time_ms-4500)*.005],'opacity':round(72*veil_amount)}])
    return result

def make_previews(manifest,images,depend):
    products={}
    grass_path=ROOT/'assets/terrain/eldenmere/grass_dirt_hd/materials/lawn_00.png';depend(grass_path)
    grass=Image.open(grass_path).convert('RGBA')
    antler_path=ROOT/'assets/terrain/overworld/elden_vale/signature_landscape_hd/antlers/antlers_regional.png';depend(antler_path)
    antlers=Image.open(antler_path).convert('RGBA')
    tree_path=ROOT/'assets/terrain/vegetation_hd/plants/broadleaf_full/idle.png';depend(tree_path)
    tree=fit(Image.open(tree_path),(144,180))
    def background(dark=False):
        scene=Image.new('RGBA',(960,640))
        for y in range(0,640,48):
            for x in range(0,960,48):scene.paste(grass,(x,y))
        scene.alpha_composite(antlers,(130,-80))
        for x,y in [(20,220),(780,200),(80,400)]:scene.alpha_composite(tree,(x,y))
        if dark:
            overlay=Image.new('RGBA',scene.size,(15,28,36,125));scene.alpha_composite(overlay)
        return scene
    def fx(scene,asset,position,opacity=None):
        image=images[asset].copy();alpha=manifest['effects'][asset]['opacity'] if opacity is None else opacity
        image.putalpha(image.getchannel('A').point(lambda value:value*alpha//255))
        scene.alpha_composite(image,(round(position[0]),round(position[1])))
    for label,dark in [('meadow',False),('dark_woodland',True)]:
        frames=[]
        for time_ms in range(0,12000,250):
            scene=background(dark)
            fx(scene,'wet_ground',(210,540));fx(scene,'wet_fence',(650,530))
            if phase_at(time_ms)=='signs':
                for index in range(5):fx(scene,'bead_'+['rest','gather','detach','lift'][min(3,time_ms//500)],(160+index*90,570))
            for instance in weather_instances(time_ms):fx(scene,instance['asset'],instance['position'],instance.get('opacity'))
            # Ordinary figures remain readable in a protected gap; no always-on-top effect cues.
            for action,x in [('gather',400),('leaf',510)]:scene.alpha_composite(images[f'{action}_0'],(x,480))
            ImageDraw.Draw(scene).text((12,12),f'OFFLINE RISING RAIN - {phase_at(time_ms)} / {time_ms}ms',fill='white')
            frames.append(scene)
        products[f'{label}.gif']=gif_bytes(frames,250,True)
        if not dark:products['meadow_slow.gif']=gif_bytes(frames,500,True)
        for index,phase in [(4,'signs'),(12,'arrival'),(24,'peak'),(44,'departure')]:products[f'{label}_{phase}.png']=png(frames[index])
    reduced=background()
    for instance in weather_instances(6000,True):fx(reduced,instance['asset'],instance['position'])
    ImageDraw.Draw(reduced).text((12,12),'DEDICATED REDUCED MOTION STILL - no drifting particles',fill='white')
    products['reduced_motion.png']=png(reduced)
    bench_path=ROOT/'assets/terrain/overworld/elden_vale/hd/props/bench.png';depend(bench_path)
    bench=Image.open(bench_path).convert('RGBA')
    actor_origin=(160,130)
    def draw_prop(scene,name,grip,anchor=None):
        image=images[name]
        if anchor is None:anchor=manifest['props'][name].get('grip_anchor_logical',[image.width/4,1])
        scene.alpha_composite(image,(round(grip[0]-2*anchor[0]),round(grip[1]-2*anchor[1])))
    for action,clip in manifest['actions'].items():
        frames=[]
        for index in range(8):
            state=action_state(clip,index*220);scene=Image.new('RGBA',(480,320),'#d9e3cc')
            # Fixed posts use the same pixels and origins through every deployment pose.
            pegs=[(179,194),(229,194)]
            if action=='deploy':
                for name,peg in zip(('post_left','post_right'),pegs):
                    anchor=manifest['props'][name]['peg_anchor_logical'];draw_prop(scene,name,peg,anchor)
            hand=clip['frames'][index]['grip_logical'];grip=[actor_origin[i]+2*hand[i] for i in (0,1)]
            def station_item(target):
                station=clip['station_grip_logical']
                point=[actor_origin[k]+2*station[k] for k in (0,1)]
                draw_prop(target,'leaf_lowered' if action=='leaf' else 'cloth_folded',point)
            if state['owner']=='station' and state['state']=='deployed':
                scene.alpha_composite(images['cloth_panel'],(165,188))
            if index==0:
                approach_background=scene.copy();approach_background.alpha_composite(bench,(210,222))
                if state['owner']=='station' and state['state']!='deployed':station_item(approach_background)
            scene.alpha_composite(images[f'{action}_{index}'],actor_origin)
            if state['owner']=='actor':
                name={'carried':'cloth_carried','opening':'cloth_held_open','folded':'cloth_folded','raised':'leaf_cup_right'}[state['state']]
                draw_prop(scene,name,grip)
                if action=='leaf' and index in (4,5):
                    bead=images['bead_lift'];scene.alpha_composite(bead,(round(grip[0])-3,round(grip[1])-12))
            scene.alpha_composite(bench,(210,222))
            if state['owner']=='station' and state['state']!='deployed':station_item(scene)
            ImageDraw.Draw(scene).text((10,10),f'{action}: pose {index} / owner={state["owner"]}',fill='black')
            frames.append(scene)
        # Existing walk poses are compatibility-only approach references, not new gait assets.
        approach=[]
        actor_folder=ROOT/'assets/characters'/clip['actor']
        for step in range(4):
            path=actor_folder/'walk_right'/f'frame_{step+1:02}.png';depend(path)
            legacy=Image.open(path).convert('RGBA');legacy=legacy.resize((legacy.width*2,legacy.height*2),Image.Resampling.NEAREST)
            scene=approach_background.copy()
            scene.alpha_composite(legacy,(148+step*12,234-legacy.getbbox()[3]))
            ImageDraw.Draw(scene).text((10,10),'APPROACH / existing legacy walk compatibility reference',fill='black');approach.append(scene)
        # Per-frame duration list distinguishes approach cadence from the authored work.
        products[f'{action}.gif']=gif_bytes(approach+frames,[120]*4+[220]*8)
        products[f'{action}_slow.gif']=gif_bytes(frames,440)
        contact=Image.new('RGBA',(480*4,320*2))
        for i,frame in enumerate(frames):contact.alpha_composite(frame,((i%4)*480,(i//4)*320))
        products[f'{action}_contacts.png']=png(contact)
    bird=manifest['wildlife'];fly_frames=[]
    for i in range(16):
        scene=Image.new('RGBA',(320,200),'#cbd9c4')
        image=images[f'bird_{i}'].resize((128,128),Image.Resampling.NEAREST);scene.alpha_composite(image,(80,40))
        ImageDraw.Draw(scene).text((10,10),f'bird pose {i}: perch / alert / takeoff / flight',fill='black');fly_frames.append(scene)
    departure=[]
    log_path=ROOT/'assets/terrain/vegetation_hd/plants/fallen_log_weathered/idle.png';depend(log_path)
    log=fit(Image.open(log_path),(120,48))
    for i in range(27):
        scene=Image.new('RGBA',(320,200),'#cbd9c4');scene.alpha_composite(log,(54,140))
        pose=i if i<8 else 8+(i-8)%8
        image=images[f'bird_{pose}'].resize((128,128),Image.Resampling.NEAREST)
        progress=max(0,i-3);scene.alpha_composite(image,(20+12*progress,44-6*progress))
        ImageDraw.Draw(scene).text((8,8),'OFFLINE takeoff trajectory / no animal route activation',fill='black')
        departure.append(scene)
    products['bird_departure.gif']=gif_bytes(departure,[800]+[180]*3+[100]*23)
    sheet=Image.new('RGBA',(4*320,4*200))
    for i,frame in enumerate(fly_frames):sheet.alpha_composite(frame,(i%4*320,i//4*200))
    products['bird_poses.png']=png(sheet)
    products['bird_flight.gif']=gif_bytes(fly_frames[8:],100,True)
    products['bird_flight_slow.gif']=gif_bytes(fly_frames[8:],200,True)
    symbols=Image.new('RGBA',(480,160),'#d9d0ab');draw=ImageDraw.Draw(symbols)
    for index,name in enumerate(('pale_antlers','causeway_ruin')):
        symbols.alpha_composite(images[name].resize((128,128),Image.Resampling.NEAREST),(index*220,0));draw.text((index*220,140),name,fill='black')
    products['map_symbols.png']=png(symbols)
    station=Image.new('RGBA',(640,320),'#d9e3cc')
    for name,point in [('post_left',(220,120)),('post_right',(270,120))]:
        draw_prop(station,name,point,manifest['props'][name]['peg_anchor_logical'])
    station.alpha_composite(images['cloth_panel'],(206,114))
    station.alpha_composite(images['washing_basket'],(310,130))
    ImageDraw.Draw(station).text((12,12),'COLLECTION STATION / fixed supports and separate panel',fill='black')
    products['collection_station.png']=png(station)
    return products

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
