"""Staged inn/item-shop art with fixed glass merchandise and candidate plot plans."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from PIL import Image,ImageChops,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.build_eldenmere_exteriors_hd import cutout,building_structure,door_sources,effect_sources,smoke_layer,glow_layer,prop_native,prop_frame
from tools.build_world_water_hd import load,gray,clipped,encoded,rgba,save_loop
SOURCE=ROOT/'assets/source/terrain/eldenmere/business_exteriors_hd';BASE=ROOT/'assets/source/terrain/eldenmere/exteriors_hd';PACK='assets/terrain/eldenmere/business_exteriors_hd';REVIEW='docs/reviews/eldenmere_business_exteriors_hd'

def recipe():return json.loads((SOURCE/'recipe.json').read_text())
def display_art(source,rect,size,rec):
    raw=cutout(source,rect).resize(tuple(size),Image.Resampling.NEAREST);out=Image.new('RGBA',raw.size);p=rec['palette'];names=('wood','glass','steel','iron','stone','potion_red','potion_blue','potion_green','potion_violet','outline');ramp=[rgba(c) for name in names for c in p[name].values()];cache={}
    for y in range(raw.height):
        for x in range(raw.width):
            c=raw.getpixel((x,y))
            if not c[3]:continue
            if c not in cache:cache[c]=min(ramp,key=lambda v:sum((v[i]-c[i])**2 for i in range(3)))
            out.putpixel((x,y),cache[c])
    return out

def awning_layer(base,rect,phase,rec):
    result=Image.new('RGBA',base.size)
    if rect is None:return result
    x,y,w,h=[v*2 for v in rect];mask=Image.new('L',base.size);glass={rgba(c) for c in rec['palette']['glass'].values()};patch=Image.new('RGBA',base.size)
    # Restrict breeze to cloth interior at its actual lower edge, preserving
    # mounting beam, piping, wall and the adjacent framed glass display.
    for yy in range(y+h-8,y+h):
        for xx in range(x,x+w):
            c=base.getpixel((xx,yy))
            if c in glass:mask.putpixel((xx,yy),255);patch.putpixel((xx,yy),c)
    dx=[0,0,1,1,1,0,0,-1,-1,0,0,1,1,0,0,-1,-1,0][phase];shifted=Image.new('RGBA',base.size);shifted.alpha_composite(patch,(dx,0));return clipped(shifted,mask)

def products():
    rec=recipe();out={};exports=[]
    for r in rec['sources']+rec['placement_checks']:
        if sha256((SOURCE/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Changed business source '+r['file'])
    for r in rec['dependencies']:
        if sha256((ROOT/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Changed business dependency '+r['file'])
    def export(path,image):
        raw=encoded(image);out[path]=raw;exports.append({'file':path,'artwork_size':list(image.size),'sha256':sha256(raw).hexdigest()})
    def doc(path,value):out[path]=(json.dumps(value,indent=2)+'\n').encode()
    sources={r['file']:load(SOURCE/r['file']) for r in rec['sources'] if r['role']=='authored_art'};old=json.loads((BASE/'recipe.json').read_text());base_sources={p:load(BASE/p) for p in ('doors_authored.png','effects_authored.png')};door_templates=door_sources(base_sources,old)['cottage'];_,glyphs=effect_sources(base_sources,old)
    prop_records=[];props={}
    for r in rec['props']:
        idle=prop_native(r,sources,rec);sequence=[prop_frame(idle,r,i,rec['palette']) for i in range(18)] if r['animation']=='hanging' else [idle];props[r['id']]=sequence;prefix='props/'+r['id'];export(PACK+'/'+prefix+'/idle.png',idle);paths=[]
        for i,image in enumerate(sequence):path=prefix+f'/frame_{i:02}.png';export(PACK+'/'+path,image);paths.append(path)
        prop_records.append({k:v for k,v in r.items() if k!='source_rect'}|{'idle':prefix+'/idle.png','frames':paths,'duration_ms':200 if len(paths)>1 else None,'cycle_ms':3600 if len(paths)>1 else None,'draw_anchor_logical':[v/2 for v in r['anchor_artwork']],'interaction_cues':False,'collision':'not_registered'})
    display_raw={};section_records=[]
    for i,variant in enumerate(('maintained','weathered')):
        image=display_art(sources['displays_authored.png'],rec['display_source_cells'][i],(156,96),rec);display_raw[variant]=image;export(PACK+'/displays/'+variant+'.png',image)
        for name,(a,b,c,d) in rec['display_sections'].items():
            rect=[round(a*156),round(b*96),round((c-a)*156),round((d-b)*96)];section_records.append({'variant':variant,'id':name,'rect_artwork':rect,'contents':rec['display_contents'][name],'file':'displays/'+variant+'.png'})
    records=[];closed_images={};ambient_images={};door_composites={};display_plates={}
    for r in rec['designs']:
        name=r['id'];prefix='buildings/'+name;structure,window_mask=building_structure(r,sources,rec);plate=None
        if r['display_rect_logical']:
            x,y,w,h=[v*2 for v in r['display_rect_logical']];plate=structure.crop((x,y,x+w,y+h));plate.alpha_composite(display_raw[r['display_variant']]);structure.paste((0,0,0,0),(x,y,x+w,y+h));window_mask.paste(0,(x,y,x+w,y+h));export(PACK+'/'+prefix+'/display.png',plate);display_plates[name]=plate
        export(PACK+'/'+prefix+'/structure.png',structure);export(PACK+'/'+prefix+'/window_mask.png',window_mask);doors=[];composed=[];dx,dy,dw,dh=[v*2 for v in r['door_rect_logical']];sign_pos=tuple(v*2 for v in r['sign_position_logical']);sign_sequence=props[r['sign']]
        for i,template in enumerate(door_templates):
            # Door source art and its five drawn states use the preceding pack's
            # exact palette/registration conventions, preserving 100 ms timing.
            from tools.build_eldenmere_exteriors_hd import quantize
            door,_=quantize(template.resize((dw,dh),Image.Resampling.NEAREST),rec,r['roof']);path=prefix+f'/doors/frame_{i:02}.png';export(PACK+'/'+path,door);doors.append({'file':path,'duration_ms':100});image=structure.copy();image.alpha_composite(door,(dx,dy))
            if plate is not None:image.alpha_composite(plate,(x,y))
            image.alpha_composite(sign_sequence[0],sign_pos);composed.append(image)
        export(PACK+'/'+prefix+'/closed.png',composed[0]);export(PACK+'/'+prefix+'/open.png',composed[-1]);closed_images[name]=composed[0];door_composites[name]=composed
        seq=[];layers=[]
        for phase in range(18):
            base=structure.copy();base.alpha_composite(load_image_bytes(out[PACK+'/'+doors[0]['file']]),(dx,dy))
            if plate is not None:base.alpha_composite(plate,(x,y))
            glow=glow_layer(structure,window_mask,phase,rec);smoke=smoke_layer(r,phase,glyphs);awning=awning_layer(base,r['awning_rect_logical'],phase,rec);sign_layer=Image.new('RGBA',base.size);sign_layer.alpha_composite(sign_sequence[phase],sign_pos);base.alpha_composite(glow);base.alpha_composite(awning);base.alpha_composite(sign_layer);base.alpha_composite(smoke);seq.append(base);layer={}
            for key,image in [('windowlight',glow),('awning',awning),('sign',sign_layer),('smoke',smoke)]:path=prefix+f'/{key}/frame_{phase:02}.png';export(PACK+'/'+path,image);layer[key]=path
            path=prefix+f'/ambient/frame_{phase:02}.png';export(PACK+'/'+path,base);layers.append({'file':path,'duration_ms':200,'layers':layer})
        ambient_images[name]=seq
        record={k:r[k] for k in ('id','building_type','variant','logical_size','ground_rect_logical','door_rect_logical','charm')};record.update(artwork_pixels_per_world_pixel=2,artwork_size=list(structure.size),draw_anchor_logical=[0,0],depth_baseline_logical=sum(r['ground_rect_logical'][i] for i in (1,3)),structure=prefix+'/structure.png',closed=prefix+'/closed.png',open=prefix+'/open.png',window_mask=prefix+'/window_mask.png',door={'position_logical':r['door_rect_logical'][:2],'logical_size':r['door_rect_logical'][2:],'frames':doors,'loop':False,'hold_closed':0,'hold_open':4,'closing_order':[4,3,2,1,0]},sign={'prop':r['sign'],'position_logical':r['sign_position_logical'],'fixed_mount':True},display={'file':prefix+'/display.png','rect_logical':r['display_rect_logical'],'variant':r['display_variant'],'contents':rec['display_contents'],'glass_reflections':'Stationary source-drawn strokes above merchandise, behind fixed mullions.','animation':'none','inventory_binding':'decorative_only','interaction_cues':False} if plate is not None else None,awning_rect_logical=r['awning_rect_logical'],ambient={'frames':layers,'cycle_ms':3600,'smoke_optional':r['smoke'],'reduced_motion':prefix+'/closed.png'},collision='not_registered; ground footprint is a proposal for later explicit integration',door_approach_local_logical=[r['door_rect_logical'][0]-4,r['door_rect_logical'][1],r['door_rect_logical'][2]+8,r['logical_size'][1]-r['door_rect_logical'][1]+12],interaction_cues=False)
        records.append(record)
    # Family board preserves native 2x density for direct proportional comparison.
    board=Image.new('RGB',(900,1040),'#e8e9df');draw=ImageDraw.Draw(board)
    for i,r in enumerate(rec['designs']):
        image=closed_images[r['id']];px=i%2*450+(450-image.width)//2;py=i//2*520;board.paste(image,(px,py),image);draw.text((i%2*450+8,py+492),r['id'],fill='#243529')
    export(REVIEW+'/businesses_native.png',board)
    # Isolated ambience keeps each 3.6s clock and fixed merchandise inspectable.
    for name,sequence in ambient_images.items():
        gif=[]
        for i,image in enumerate(sequence):
            bg=Image.new('RGB',image.size,'#2c7c50');bg.paste(image,(0,0),image);export(REVIEW+f'/ambient/{name}/frame_{i:02}.png',bg);gif.append(bg)
        out[REVIEW+'/'+name+'.gif']=save_loop(gif,200)
    for variant,image in display_raw.items():export(REVIEW+'/display_'+variant+'_closeup.png',image.resize((624,384),Image.Resampling.NEAREST))
    prop_board=Image.new('RGB',(6*160,160),'#e8e9df');draw=ImageDraw.Draw(prop_board)
    for i,r in enumerate(prop_records):
        image=props[r['id']][0];view=image.resize((image.width*2,image.height*2),Image.Resampling.NEAREST);prop_board.paste(view,(i*160+(160-view.width)//2,4),view);draw.text((i*160+3,138),r['id'],fill='#243529')
    export(REVIEW+'/props.png',prop_board)
    ground=ROOT/'assets/terrain/eldenmere/grass_dirt_hd';gm=json.loads((ground/'tileset.json').read_text());grass=[load(ground/p) for p in gm['materials']['grass']];dirt=load(ground/gm['materials']['dirt'][0]);scenes=[]
    for variant in ('maintained','weathered'):
        scene=Image.new('RGBA',(960,640))
        for yy in range(14):
            for xx in range(20):scene.alpha_composite(dirt if 10<=yy<=11 else grass[(xx//4+yy//3)%4],(xx*48,yy*48))
        placements=[{'id':'inn_'+variant,'position_artwork':[24,32]},{'id':'item_shop_'+variant,'position_artwork':[560,128]}]
        for p in placements:scene.alpha_composite(closed_images[p['id']],tuple(p['position_artwork']))
        actors=[{'file':'assets/characters/caelan/review_hd/idles/idle_front.png','position_artwork':[438,444]},{'file':'assets/characters/iselin/idle_front_42x72.png','position_artwork':[490,444]}]
        for a in actors:scene.alpha_composite(load(ROOT/a['file']),tuple(a['position_artwork']))
        export(REVIEW+'/street_'+variant+'_native.png',scene);scenes.append({'id':variant,'size_artwork':[960,640],'ground_rule':'Dirt rows 10..11; grass arrangement (x//4+y//3)%4 elsewhere.','buildings':placements,'actors':actors})
    # This logical-resolution diagram is explicitly planning evidence, not a
    # display of native 2x artwork or a modified production map.
    context=load(SOURCE/'town_context_reference.png');draw=ImageDraw.Draw(context)
    for p in rec['candidate_placements']:
        image=closed_images[p['design']].resize(tuple(next(r['logical_size'] for r in records if r['id']==p['design'])),Image.Resampling.NEAREST);context.alpha_composite(image,tuple(p['position_logical']));x,y,w,h=p['ground_rect_world_logical'];draw.rectangle((x,y,x+w-1,y+h-1),outline='#65d9e4',width=2);draw.line([tuple(v) for v in p['proposed_path_centerline_logical']],fill='#dd995d',width=4);draw.text((x,y-16),p['id']+' candidate',fill='white')
    draw.rectangle((0,0,1535,30),fill='#e8e9df');draw.text((12,10),'PLANNING ONLY / logical-scale context / cyan footprints / orange future paths / not applied to gameplay',fill='#243529');export(REVIEW+'/placement_overview.png',context)
    service_plan={'status':'specification_only_not_implemented','inn':{'interior':'Ground-floor common room and counter; upstairs guest-room presentation consistent with the four exterior windows. Preserve porch/door clearance.','keeper':'Create an innkeeper and dialogue-driven Rest/Leave choices during integration.','rest':'Show the full party price and require an explicit choice; charge and restore eligible active-party HP/MP together. Define status recovery, guest access and timing deliberately.','failure_cases':['insufficient funds changes neither currency nor party state','cancel/leave changes no state','do not charge for failed or interrupted transition'],'save':'Add currency and completed rest persistence through the existing versioned save system; autosave only after the successful transaction/scene settles.'},'item_shop':{'interior':'Counter and reachable merchant; stock shelves and a display-facing wall consistent with the exterior.','existing_consumable_ids':['potion','ether','revival_salts','smoke_bomb','rest_kit'],'gear':'Add ordinary weapon and armor catalog entries, prices and equipment rules before sale. Never offer quest/key items or Mira’s unique gift blade as ordinary stock.','transactions':'One authoritative atomic purchase/sale path; validate price, integer quantity, funds, inventory limits and eligibility before mutation. Persist inventory/currency through current saves.','window':'Decorative stock behind glass; no pickups, grants, prices, glints or inventory ownership changes from examining the exterior.'},'shared_prerequisites':['currency model and balance decisions','merchant UI and dialogue integration','new interiors and reachable NPC stations','native 2x map and door integration','revalidate current collision/navigation/quests/NPC routes before applying candidate plots','actual traversal, reload, game-over, transaction and reduced-motion checks']}
    meta={'version':1,'id':rec['id'],'artwork_state':'rebuilt','integration_status':'not_integrated','visual_approval':rec['visual_approval'],'artwork_pixels_per_world_pixel':2,'path_conventions':{'asset_files':'pack_relative','recipe_and_base_references':'repository_relative'},'rect_space':'artwork unless logical-suffixed','anchor_space':'logical unless artwork-suffixed','buildings':records,'props':prop_records,'display_sections':section_records,'candidate_placements':rec['candidate_placements'],'placement_status':rec['placement_status'],'palette':'palette.json','recipe':'assets/source/terrain/eldenmere/business_exteriors_hd/recipe.json','activation':'Staged assets and planning evidence only; no live maps, interiors, currency, transactions, inventory, equipment, rest healing or save changes.'}
    doc(PACK+'/manifest.json',meta);doc(PACK+'/palette.json',{'materials':rec['palette'],'roof_palettes':rec['roof_palettes']});doc(REVIEW+'/integration_spec.json',service_plan);doc(REVIEW+'/placement_plan.json',{'status':rec['placement_status'],'baseline_commit':rec['baseline_commit'],'context':rec['context_reference'],'plots':rec['candidate_placements'],'collision_snapshot_checks':rec['placement_checks'],'note':'Baseline planning evidence only. Revalidate against the then-current map before integration.'});doc(REVIEW+'/layout.json',{'presentation':'Offline native-density art fixtures, plus a separately labeled logical-scale planning diagram.','scenes':scenes});doc(REVIEW+'/exports.json',{'builder':rec['builder'],'recipe_sha256':sha256((SOURCE/'recipe.json').read_bytes()).hexdigest(),'sources':rec['sources'],'dependencies':rec['dependencies'],'outputs':exports});return out

def load_image_bytes(raw):
    from io import BytesIO
    with Image.open(BytesIO(raw)) as im:return im.convert('RGBA')
def build(check=False):
    outputs=products();stale=[]
    for path,raw in outputs.items():
        p=ROOT/path
        if not p.exists() or p.read_bytes()!=raw:
            stale.append(path)
            if not check:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    if check and stale:raise SystemExit('Stale business exports: '+', '.join(stale))
    return outputs
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args();print(f'{len(build(args.check))} business exports '+('verified' if args.check else 'built'))
