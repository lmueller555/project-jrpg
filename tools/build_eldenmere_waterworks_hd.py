"""Staged HD channels and spillways, preserving legacy logical ports and rise.
New water drawings and the staged HD masonry supply all visible pixels."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from PIL import Image, ImageChops, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.build_world_water_hd import load,gray,clipped,encoded,rgba,recipe as water_recipe,materials,accent_sources,tinted_glyph,current_frame,save_loop
SOURCE=ROOT/'assets/source/terrain/eldenmere/waterworks_hd';PACK='assets/terrain/eldenmere/waterworks_hd';REVIEW='docs/reviews/eldenmere_waterworks_hd'
PORTS={'N':1,'E':2,'S':4,'W':8};OPPOSITE={'N':'S','S':'N','E':'W','W':'E'}

def recipe():return json.loads((SOURCE/'recipe.json').read_text())
def geometry(rec):
    return {(r['id'],r['kind']):gray(SOURCE/r['file']).resize(tuple(n*2 for n in r['logical_size']),Image.Resampling.NEAREST) for r in rec['geometry']}

def register_material(im,base):
    result=im.copy()
    # Common ports are quiet material, preserving all current route connections.
    for y in range(result.height):
        for x in range(result.width):
            if min(x,y,result.width-1-x,result.height-1-y)<2:result.putpixel((x,y),rgba(base))
    return result

def channel_frame(record,bank,mask,water,phase,glyph,ramp):
    im=clipped(water,mask)
    if record['kind']=='channel':route=record
    else:
        direction=record['direction'];route={'input':OPPOSITE[direction],'outputs':[direction]}
    current=clipped(current_frame(route,phase,glyph,ramp),mask)
    if record['kind']=='outlet':
        airborne=Image.new('RGBA',(48,48));drop=tinted_glyph(glyph,ramp['reflection']).resize((2,6),Image.Resampling.NEAREST);airborne.alpha_composite(drop,(23,28+phase*2))
        rotation={'S':None,'E':Image.Transpose.ROTATE_90,'N':Image.Transpose.ROTATE_180,'W':Image.Transpose.ROTATE_270}[record['direction']]
        if rotation is not None:airborne=airborne.transpose(rotation)
        current.alpha_composite(airborne)
    im.alpha_composite(current);im.alpha_composite(bank)
    return im,current

def spillway_frame(structure,mask,water,phase,accents,ramp):
    im=clipped(water,mask);fx=Image.new('RGBA',(48,96));glyph=tinted_glyph(accents['ripple'],ramp['reflection']).resize((4,8),Image.Resampling.NEAREST)
    # Sparse source-derived streaks descend, rather than sliding the fall texture.
    for y in range(-24,96,24):fx.alpha_composite(glyph,(22,y+phase*4))
    # Upper/lower channel ports share the same directed clock as normal channels.
    flow=current_frame({'input':'N','outputs':['S']},phase,accents['ripple'],ramp)
    fx.alpha_composite(flow,(0,0));fx.alpha_composite(flow,(0,48))
    impact=tinted_glyph(accents['impact'],ramp['reflection' if phase%2==0 else 'flow']);fx.alpha_composite(impact,(15+phase%2,61+phase%2))
    eddy=tinted_glyph(accents['eddy'],ramp['flow']);fx.alpha_composite(eddy,(15,68+(phase//2)%2))
    alpha=fx.getchannel('A');draw=ImageDraw.Draw(alpha);draw.rectangle((0,0,47,1),fill=0);draw.rectangle((0,94,47,95),fill=0)
    fx=clipped(clipped(fx,alpha),mask);im.alpha_composite(fx);im.alpha_composite(structure);return im,fx

def products():
    rec=recipe();wr=water_recipe();out={};exports=[]
    for r in rec['geometry']:
        if sha256((SOURCE/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Changed waterworks geometry '+r['file'])
    for r in rec['source_dependencies']:
        if sha256((ROOT/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Changed dependency '+r['file'])
    def export(path,im):
        raw=encoded(im);out[path]=raw;exports.append({'file':path,'artwork_size':list(im.size),'sha256':sha256(raw).hexdigest()})
    def doc(path,data):out[path]=(json.dumps(data,indent=2)+'\n').encode()
    geo=geometry(rec);surfaces,bank_materials=materials(wr);accents=accent_sources(wr);water=surfaces['temperate','deep',0,0];ramp=wr['water_palettes']['temperate'];banks={};masks={};channel_records=[];channel_images={};flow_images={}
    for style,source_style in rec['channel_treatments'].items():
        material=bank_materials['earth',0] if style=='earth' else load(ROOT/f'assets/terrain/eldenmere/terraces_hd/modules/{source_style}/wall_front_01.png')
        base=wr['bank_palettes']['earth']['base'] if style=='earth' else wr['stone_palette']['base'];material=register_material(material,base)
        for record in rec['routes']:
            prefix=f"shape_{record['ports']:02}" if record['kind']=='channel' else record['id'];key=style,prefix;mask=geo[prefix,'water'];masks[prefix]=mask
            if key not in banks:
                bank=clipped(material,geo[prefix,'bank']);banks[key]=bank;export(PACK+f'/banks/{style}/{prefix}.png',bank)
            bank=banks[key];frames=[];effects=[]
            for phase in range(6):
                im,fx=channel_frame(record,bank,mask,water,phase,accents['ripple'],ramp);path=f'channels/{style}/{record["id"]}/frame_{phase:02}.png';export(PACK+'/'+path,im);frames.append(path);channel_images[style,record['id'],phase]=im
                # Flow layer is shared by all structural treatments.
                fxpath=f'flow/{record["id"]}/frame_{phase:02}.png'
                if PACK+'/'+fxpath not in out:export(PACK+'/'+fxpath,fx)
                effects.append(fxpath);flow_images[record['id'],phase]=fx
            still=clipped(water,mask);still.alpha_composite(bank);stillpath=f'channels/{style}/{record["id"]}/still.png';export(PACK+'/'+stillpath,still)
            channel_records.append({**record,'style':style,'frames':frames,'flow_frames':effects,'still':stillpath,'bank':f'banks/{style}/{prefix}.png','water_mask':f'masks/{prefix}.png','logical_size':[24,24],'draw_anchor_logical':[12,24],'water_width_logical':8,'port_bits':PORTS,'effect_bounds_space':'logical','special_placement':'Intake overlaps a matching straight stream bank; outlet receiver remains within the declared logical effect bounds.' if record['kind']!='channel' else 'Match cardinal ports; input is singular, outputs may split.'})
    for prefix,mask in masks.items():export(PACK+f'/masks/{prefix}.png',mask)
    # Per-phase atlases make route inventories inspectable without fixed animation strips.
    for style in rec['channel_treatments']:
        for phase in range(6):
            atlas=Image.new('RGBA',(384,240))
            for index,r in enumerate(rec['routes']):atlas.alpha_composite(channel_images[style,r['id'],phase],(index%8*48,index//8*48))
            export(PACK+f'/atlases/{style}_{phase:02}.png',atlas)
    spill_records=[];spill_images={};structures={}
    for style in rec['spillway_treatments']:
        wall=load(ROOT/f'assets/terrain/eldenmere/terraces_hd/modules/{style}/wall_front_01.png');material=Image.new('RGBA',(48,96));material.alpha_composite(wall);material.alpha_composite(wall,(0,48));material=register_material(material,wr['stone_palette']['base']);structure=clipped(material,geo['spillway_south','structure']);structures[style]=structure
        export(PACK+f'/spillways/{style}/structure.png',structure);mask=geo['spillway_south','water'];export(PACK+f'/spillways/{style}/water_mask.png',mask)
        waterfull=Image.new('RGBA',(48,96));waterfull.alpha_composite(water);waterfull.alpha_composite(water,(0,48));paths=[];effects=[]
        for phase in range(6):
            im,fx=spillway_frame(structure,mask,waterfull,phase,accents,ramp);path=f'spillways/{style}/frame_{phase:02}.png';export(PACK+'/'+path,im);paths.append(path);spill_images[style,phase]=im
            effect=f'spillways/{style}/flow_{phase:02}.png';export(PACK+'/'+effect,fx);effects.append(effect)
        still=clipped(waterfull,mask);still.alpha_composite(structure);export(PACK+f'/spillways/{style}/still.png',still)
        spill_records.append({'id':'spillway_south_'+style,'style':style,'frames':paths,'flow_frames':effects,'structure':f'spillways/{style}/structure.png','water_mask':f'spillways/{style}/water_mask.png','still':f'spillways/{style}/still.png','logical_size':[24,48],'artwork_size':[48,96],'elevation_change_logical':24,'upper_landing':'N','lower_landing':'S','draw_anchor_logical':[12,48],'ports':{'N':{'water_interval_logical':[8,16],'elevation_logical':24},'S':{'water_interval_logical':[8,16],'elevation_logical':0}},'orientation':'south only','collision':'Not inferred from alpha; separate geometry and navigation required at integration.'})
    # Route board: same geometry, new drawn material treatments.
    sequence=[]
    for phase in range(6):
        board=Image.new('RGB',(8*100,3*5*112+30),'#e8e9df');draw=ImageDraw.Draw(board)
        draw.text((8,8),'HD waterworks / 3 treatments x 40 directed modules / NOT INTEGRATED',fill='#243529')
        for si,style in enumerate(rec['channel_treatments']):
            for index,r in enumerate(rec['routes']):
                x=index%8*100;y=(si*5+index//8)*112+30;tile=Image.new('RGBA',(48,48),rgba('#2c7c50'));tile.alpha_composite(channel_images[style,r['id'],phase]);board.paste(tile.convert('RGB').resize((96,96),Image.Resampling.NEAREST),(x,y));draw.text((x,y+98),style[:4]+' '+r['id'].replace('channel_','').replace('from_',''),fill='#243529')
        export(REVIEW+f'/route_board/frame_{phase:02}.png',board);sequence.append(board)
    out[REVIEW+'/routes.gif']=save_loop(sequence);export(REVIEW+'/route_board.png',sequence[0])
    # Terrace + channel + fall scene with explicit upstream/downstream connections.
    gm=json.loads((ROOT/'assets/terrain/eldenmere/grass_dirt_hd/tileset.json').read_text());grass=[load(ROOT/'assets/terrain/eldenmere/grass_dirt_hd'/p) for p in gm['materials']['grass']];earth=[load(ROOT/'assets/terrain/eldenmere/grass_dirt_hd'/p) for p in gm['materials']['dirt']];scene_frames=[]
    placements=[]
    def route_id(ports,input_):return f'channel_{sum(PORTS[p] for p in ports):02}_from_{input_.lower()}'
    for phase in range(6):
        scene=Image.new('RGBA',(960,640))
        for y in range(14):
            for x in range(20):scene.alpha_composite(grass[(x//3+y//4)%4],(x*48,y*48))
        for i,style in enumerate(rec['spillway_treatments']):
            ox=48+i*288;oy=96;channel_style='weathered' if style=='mossy' else 'maintained' if style=='maintained' else 'earth'
            # Upper terrace top, a horizontal front wall and stream intake.
            for y in range(3):
                for x in range(5):scene.alpha_composite(earth[0],(ox+x*48,oy+y*48))
            wall=load(ROOT/f'assets/terrain/eldenmere/terraces_hd/modules/{style}/wall_front_01.png')
            for x in (0,1,3,4):scene.alpha_composite(wall,(ox+x*48,oy+144))
            cells=[(1,0,'inlet_s'),(1,1,route_id(('N','E'),'N')),(2,1,route_id(('W','S'),'W')),(2,2,route_id(('N','S'),'N')),(2,5,route_id(('N','S'),'N')),(2,6,'outlet_s')]
            # A real natural-stream bank underlays the intake; its central
            # opening is supplied by the intake water mask, preserving coverage.
            for sx,mask_id in enumerate((4,68,64)):
                natural_mask=gray(ROOT/f'assets/terrain/water_hd/masks/water_{mask_id:03}.png');natural_bank=load(ROOT/f'assets/terrain/water_hd/banks/earth/0/mask_{mask_id:03}.png');world_phase=((ox//48+sx)%2)+2*((oy//48)%2);source_water=load(ROOT/f'assets/terrain/water_hd/surfaces/temperate/deep_0_{world_phase}/frame_{phase:02}.png');source=clipped(source_water,natural_mask);source.alpha_composite(natural_bank);scene.alpha_composite(source,(ox+sx*48,oy))
            for x,y,rid in cells:scene.alpha_composite(channel_images[channel_style,rid,phase],(ox+x*48,oy+y*48))
            scene.alpha_composite(spill_images[style,phase],(ox+96,oy+144))
            actor=load(ROOT/'assets/characters/caelan/review_hd/idles/idle_front.png');scene.alpha_composite(actor,(ox+170,oy+40))
            if phase==0:placements.append({'style':style,'channel_style':channel_style,'origin_artwork':[ox,oy],'channel_cells':[{'cell':[x,y],'route':rid} for x,y,rid in cells],'spillway_position_artwork':[ox+96,oy+144],'wall_cells':[[x,3] for x in (0,1,3,4)],'upper_ground_rect_artwork':[ox,oy,240,144],'source_stream_tiles':[{'cell':[sx,0],'mask':mask_id} for sx,mask_id in enumerate((4,68,64))],'character_position_artwork':[ox+170,oy+40]})
        export(REVIEW+f'/scene/frame_{phase:02}.png',scene);scene_frames.append(scene)
    out[REVIEW+'/terrace_waterworks.gif']=save_loop(scene_frames);export(REVIEW+'/scene_native.png',scene_frames[0]);export(REVIEW+'/spillways_closeup.png',scene_frames[0].crop((120,210,840,420)).resize((1440,420),Image.Resampling.NEAREST))
    meta={'version':1,'id':rec['id'],'artwork_state':'rebuilt','integration_status':'not_integrated','visual_approval':rec['visual_approval'],'artwork_pixels_per_world_pixel':2,'logical_tile_size':[24,24],'artwork_tile_size':[48,48],'rect_space':'artwork','anchor_space':'logical','path_space':'pack_relative','port_bits':PORTS,'port_convention':'Four cardinal channel bits; distinct from eight-neighbor shoreline bits.','channel_treatments':rec['channel_treatments'],'channel_routes':channel_records,'route_count_per_treatment':40,'water_family_baked':'temperate','other_water_families':'Use fixed bank/structure and mask layers with matching water-family surfaces and recolored flow glyphs. Baked previews use temperate water.','water_pack':rec['water_pack'],'terrace_pack':rec['terrace_pack'],'flow_step_artwork':4,'flow_period_artwork':24,'animation':{'frame_count':6,'duration_ms':200,'cycle_ms':1200,'clock':'Shared with connected natural water.','reduced_motion':'Use explicit still files; banks and structures unchanged.'},'spillways':spill_records,'integration':'No active maps, renderer, collision, navigation, simulation or save changes. Preserve declared footprint, ports, rise and actual-game acceptance when integrating.','palette':'../../water_hd/palette.json','recipe':'assets/source/terrain/eldenmere/waterworks_hd/recipe.json'}
    doc(PACK+'/tileset.json',meta);doc(REVIEW+'/layout.json',{'presentation':'Offline illustrative terrace connection review, not live gameplay.','size_artwork':[960,640],'placements':placements});doc(REVIEW+'/exports.json',{'builder':rec['builder'],'recipe_sha256':sha256((SOURCE/'recipe.json').read_bytes()).hexdigest(),'dependencies':rec['source_dependencies'],'outputs':exports});return out

def build(check=False):
    result=products();stale=[]
    for path,raw in result.items():
        p=ROOT/path
        if not p.exists() or p.read_bytes()!=raw:
            stale.append(path)
            if not check:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    if check and stale:raise SystemExit('Stale waterworks exports: '+', '.join(stale))
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args();print(f'{len(build(args.check))} waterworks exports '+('verified' if args.check else 'built'))
