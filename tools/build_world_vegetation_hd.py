"""Export staged reusable HD vegetation from retained new sprite drawings.
No active maps, collision, navigation or shared-grass behavior is changed."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import statistics
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.build_world_water_hd import load,gray,clipped,encoded,rgba,save_loop
SOURCE=ROOT/'assets/source/terrain/vegetation_hd';PACK='assets/terrain/vegetation_hd';REVIEW='docs/reviews/world_vegetation_hd'

def recipe():return json.loads((SOURCE/'recipe.json').read_text())
def colors(im):
    data=im.tobytes();return {tuple(data[i:i+4]) for i in range(0,len(data),4) if data[i+3]}
def is_green(c):return c[1]>=c[0]-6 and c[1]>c[2]+8 and c[1]>55

def cutout(source,record):
    cell=source.crop(tuple(record['source_rect']));mask=Image.new('L',cell.size)
    for y in range(cell.height):
        for x in range(cell.width):
            r,g,b,a=cell.getpixel((x,y));key=r>170 and b>160 and r>g+65 and b>g+65
            mask.putpixel((x,y),0 if key or a<128 else 255)
    box=mask.getbbox()
    if box is None:raise ValueError('Empty vegetation source: '+record['id'])
    cell.putalpha(mask);cell=cell.crop(box);limit=record['max_occupied_size_artwork'];limit=[v-2 for v in limit] if record['animation_kind']=='rooted_breeze' else limit;cell.thumbnail(tuple(limit),Image.Resampling.NEAREST)
    result=Image.new('RGBA',tuple(record['artwork_size']));ax,ay=record['root_anchor_artwork'];result.alpha_composite(cell,(ax-cell.width//2,ay-cell.height));return result

def register_palette(im,record,palette):
    out=Image.new('RGBA',im.size);labels=Image.new('L',im.size);leaf=[rgba(v) for v in palette['leaves'].values()];wood=[rgba(v) for v in palette['wood'].values()];stone=[rgba(v) for v in palette['stone'].values()];outline=rgba(palette['outline']['base']);family=record['family'];variant=record['variant']
    green_pixels=[c for c in colors(im) if is_green(c)];median=[statistics.median(c[i] for c in green_pixels) if green_pixels else leaf[2][i] for i in range(3)];target=leaf[2];cache={}
    for y in range(im.height):
        for x in range(im.width):
            c=im.getpixel((x,y))
            if not c[3]:continue
            key=c,y<record['root_anchor_artwork'][1]-record['max_occupied_size_artwork'][1]*.3
            if key not in cache:
                r,g,b,a=c;role=2;ramp=stone if family in ('boulder','rock_cluster') else wood;corrected=c[:3]
                if max(r,g,b)<62:ramp=[outline];role=3
                elif is_green(c):ramp=leaf;corrected=[target[i]+(c[i]-median[i])*1.05 for i in range(3)];role=1
                elif family in ('flowers','bank_flowers'):
                    flower='violet' if variant in ('violet','iris') else variant
                    petal=(flower=='white' and min(r,g,b)>130) or (flower=='yellow' and r>135 and g>110 and r>g+5 and g>b+25) or (flower=='violet' and b>g+15 and r>g+10)
                    if petal:ramp=[rgba(v) for v in palette[flower].values()];role=4
                elif family=='woodland':ramp=wood+[rgba(v) for v in palette['birch'].values()]
                elif family=='orchard' and key[1]:
                    if variant=='red_fruit' and r>g*1.8 and r>110:ramp=[rgba(v) for v in palette['fruit_red'].values()];role=4
                    elif variant=='gold_fruit' and r>160 and g>115 and r>g*1.1 and g>b*1.4:ramp=[rgba(v) for v in palette['yellow'].values()];role=4
                color=min(ramp,key=lambda p:sum((p[i]-corrected[i])**2 for i in range(3)));cache[key]=(color,role)
            color,role=cache[key];out.putpixel((x,y),color);labels.putpixel((x,y),role)
    # Preserve color in fine blades/stems: their contour uses existing canvas
    # padding. Broad tree/stone/wood silhouettes register the edge inward.
    alpha=out.getchannel('A')
    boundary=(ImageChops.subtract(alpha.filter(ImageFilter.MaxFilter(3)),alpha) if record['animation_kind']=='rooted_breeze' else ImageChops.subtract(alpha,alpha.filter(ImageFilter.MinFilter(3))))
    out.paste(Image.new('RGBA',out.size,outline),(0,0),boundary)
    for y in range(im.height):
        for x in range(im.width):
            if boundary.getpixel((x,y)):labels.putpixel((x,y),3)
    return out,labels

def tree_layers(native,labels,record,palette):
    fixed=Image.new('RGBA',native.size);back=native.copy();parts=[];box=native.getbbox();x0,y0,x1,y1=box;w,h=x1-x0,y1-y0
    woodmask=labels.point(lambda v:255 if v==2 else 0).filter(ImageFilter.MaxFilter(3));a=native.getchannel('A')
    for y in range(native.height):
        for x in range(native.width):
            if y>=record['fixed_rows_from_artwork'] or labels.getpixel((x,y)) in (2,4) or labels.getpixel((x,y))==3 and woodmask.getpixel((x,y)):
                fixed.putpixel((x,y),native.getpixel((x,y)))
    ramp=[rgba(c) for c in palette['leaves'].values()];shade={c:ramp[max(0,i-1)] for i,c in enumerate(ramp)}
    regions=[(.25,.04,.75,.25),(.04,.30,.34,.50),(.66,.30,.96,.50),(.14,.55,.44,.74),(.56,.55,.86,.74)]
    for index,(left,top,right,bottom) in enumerate(regions):
        rect=(x0+int(left*w),y0+int(top*h),x0+int(right*w),y0+int(bottom*h));part=Image.new('RGBA',(rect[2]-rect[0],rect[3]-rect[1]))
        for y in range(rect[1],rect[3]):
            for x in range(rect[0],rect[2]):
                if labels.getpixel((x,y))==1 and not fixed.getpixel((x,y))[3]:
                    c=native.getpixel((x,y));part.putpixel((x-rect[0],y-rect[1]),c);back.putpixel((x,y),shade[c])
        if part.getbbox():parts.append({'id':f'leaf_{index}','position_artwork':list(rect[:2]),'delay':index%3,'image':part})
    if not parts:raise ValueError('No moving leaf clusters: '+record['id'])
    return fixed,back,parts

def tree_frame(native,fixed,back,parts,phase):
    result=back.copy();poses=[0,1,1,0,-1,-1,0,0,0]
    for part in parts:
        x,y=part['position_artwork'];dx=poses[(phase-part['delay'])%9];result.alpha_composite(part['image'],(x+dx,y))
    result=clipped(result,native.getchannel('A'));result.alpha_composite(fixed);return result

def rooted_frame(native,record,offset):
    result=Image.new('RGBA',native.size);fixed=record['fixed_rows_from_artwork']
    for y in range(native.height):
        dx=offset if y<fixed-2 else 0
        result.alpha_composite(native.crop((0,y,native.width,y+1)),(dx,y))
    return result

def products():
    rec=recipe();out={};exports=[]
    for r in rec['sources']:
        if sha256((SOURCE/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Changed vegetation source '+r['file'])
    def export(path,im):
        raw=encoded(im);out[path]=raw;exports.append({'file':path,'artwork_size':list(im.size),'sha256':sha256(raw).hexdigest()})
    def doc(path,data):out[path]=(json.dumps(data,indent=2)+'\n').encode()
    sources={r['file']:load(SOURCE/r['file']) for r in rec['sources']};items=[];sequences={};native_images={};family_records={}
    for r in rec['designs']:
        name=r['id'];native,labels=register_palette(cutout(sources[r['source']],r),r,rec['palette']);native_images[name]=native;prefix='plants/'+name;export(PACK+'/'+prefix+'/idle.png',native);export(PACK+'/'+prefix+'/semantic_mask.png',labels)
        parts=[];fixed=None;back=None
        if r['animation_kind']=='local_leaf_clusters':
            fixed,back,parts=tree_layers(native,labels,r,rec['palette']);export(PACK+'/'+prefix+'/fixed.png',fixed);export(PACK+'/'+prefix+'/backing.png',back)
            for part in parts:export(PACK+'/'+prefix+'/clusters/'+part['id']+'.png',part['image'])
            sequence=[tree_frame(native,fixed,back,parts,p) for p in range(9)]
        elif r['animated']:
            sequence=[rooted_frame(native,r,offset) for offset in rec['animation']['offsets_artwork']];fixed=Image.new('RGBA',native.size);fixed.paste(native.crop((0,r['fixed_rows_from_artwork'],native.width,native.height)),(0,r['fixed_rows_from_artwork']));export(PACK+'/'+prefix+'/fixed.png',fixed)
        else:sequence=[native]
        if sequence[0].tobytes()!=native.tobytes():raise ValueError('Rest pose does not match drawing: '+name)
        sequences[name]=sequence;frames=[];sheet=Image.new('RGBA',(native.width*len(sequence),native.height))
        for phase,im in enumerate(sequence):
            path=prefix+f'/frames/frame_{phase:02}.png';export(PACK+'/'+path,im);sheet.alpha_composite(im,(phase*native.width,0));frames.append({'file':path,'duration_ms':600 if r['animated'] else None,'sheet_rect_artwork':[phase*native.width,0,native.width,native.height]})
        export(PACK+'/'+prefix+'/sheet.png',sheet)
        item={k:r[k] for k in ('id','family','variant','logical_size','artwork_size','draw_anchor_logical','root_anchor_artwork','ground_rect_logical','depth_baseline_logical','fixed_rows_from_artwork','animated','animation_kind','allowed_surfaces','collision','interaction_cues')}
        item.update(idle=prefix+'/idle.png',sheet=prefix+'/sheet.png',semantic_mask=prefix+'/semantic_mask.png',occupied_rect_artwork=list(native.getbbox()),frames=frames,artwork_pixels_per_world_pixel=2,path_space='pack_relative',fixed=prefix+'/fixed.png' if fixed is not None else None,backing=prefix+'/backing.png' if back is not None else None,clusters=[{'id':p['id'],'file':prefix+'/clusters/'+p['id']+'.png','position_artwork':p['position_artwork'],'phase_delay':p['delay']} for p in parts],wind={'cycle_ms':5400 if r['animated'] else None,'max_displacement_artwork':1 if r['animated'] else 0,'vertical_displacement_artwork':0,'whole_tree_moves':False,'reduced_motion':'Use idle file; root and support stay fixed.'},contact_behavior='Decorative assets only. Existing shared contact-responsive grass is unchanged; preserve its walk/run/occupied/recovery behavior during a future explicit migration.' if r['family']=='grass' else 'Scenery; no runtime response or interaction registered.')
        items.append(item);family_records.setdefault(r['family'],[]).append(item)
    # One packed idle atlas retains explicit artwork-space rectangles.
    atlas=Image.new('RGBA',(768,1200));tree_index=small_index=0
    for r in items:
        if r['animation_kind']=='local_leaf_clusters':
            x,y=tree_index%4*192,tree_index//4*240;tree_index+=1
        else:x,y=small_index%8*96,720+small_index//8*96;small_index+=1
        image=native_images[r['id']];atlas.alpha_composite(image,(x,y));r.update(atlas='idle_atlas.png',atlas_rect_artwork=[x,y,image.width,image.height])
    export(PACK+'/idle_atlas.png',atlas)
    # Family sheets show every variant at native size and enlarged crop sizes.
    for family,entries in family_records.items():
        tree=entries[0]['animation_kind']=='local_leaf_clusters';cellw,cellh=(208,270) if tree else (208,230);board=Image.new('RGB',(cellw*3,cellh),'#e8e9df');draw=ImageDraw.Draw(board)
        for i,r in enumerate(entries):
            image=native_images[r['id']];scale=1 if tree else 2;view=image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST);pos=(i*cellw+(cellw-view.width)//2,10);board.paste(view,pos,view);draw.text((i*cellw+8,cellh-20),r['id'],fill='#243529')
        export(REVIEW+'/families/'+family+'.png',board)
    # Animated trees at native density and grounded smaller plants on one stable backdrop.
    tree_board=[];small_board=[]
    for phase in range(9):
        tb=Image.new('RGB',(4*204,3*258),'#e8e9df');td=ImageDraw.Draw(tb);sb=Image.new('RGB',(6*152,4*204),'#e8e9df');sd=ImageDraw.Draw(sb);tree_index=small_index=0
        for r in items:
            image=sequences[r['id']][phase] if r['animated'] else sequences[r['id']][0]
            if r['animation_kind']=='local_leaf_clusters':
                x=tree_index%4*204+6;y=tree_index//4*258;tb.paste(image,(x,y),image);td.text((x,y+240),r['id'],fill='#243529');tree_index+=1
            elif r['animated']:
                x=small_index%6*152;y=small_index//6*204;view=image.resize((image.width*2,image.height*2),Image.Resampling.NEAREST);sb.paste(view,(x+(152-view.width)//2,y),view);sd.text((x+2,y+194),r['id'],fill='#243529');small_index+=1
        export(REVIEW+f'/trees/frame_{phase:02}.png',tb);tree_board.append(tb);export(REVIEW+f'/small_plants/frame_{phase:02}.png',sb);small_board.append(sb)
    out[REVIEW+'/trees.gif']=save_loop(tree_board,600);out[REVIEW+'/small_plants.gif']=save_loop(small_board,600);export(REVIEW+'/trees_native.png',tree_board[0]);export(REVIEW+'/small_plants_board.png',small_board[0])
    # Three regional native-scale fixtures use the existing staged terrain packs.
    ground=ROOT/'assets/terrain/eldenmere/grass_dirt_hd';gm=json.loads((ground/'tileset.json').read_text());grass=[load(ground/p) for p in gm['materials']['grass']];earth=[load(ground/p) for p in gm['materials']['dirt']];wm=json.loads((ROOT/'assets/terrain/water_hd/tileset.json').read_text());water_shapes={r['mask']:r for r in wm['shapes']}
    from tools.build_eldenmere_grass_dirt_hd import normalize,BITS,OFFSETS
    scenarios=[('eldenmere','temperate','grass',['broadleaf_full','orchard_red_fruit','woodland_paired']),('northern_woodland','cold','rock',['conifer_spruce','conifer_fir','woodland_sparse']),('wetland','peat','marsh',['broadleaf_weathered','woodland_leaning','orchard_old'])];layouts=[]
    by_id={r['id']:r for r in items}
    for scene_id,water_family,bank,trees in scenarios:
        placements=[]
        def place(name,root,phase_offset=0,layer='depth_sorted'):placements.append({'id':name,'root_artwork':list(root),'phase_offset':phase_offset,'layer':layer})
        for i,name in enumerate(trees):place(name,[(170,260),(760,240),(810,545)][i],i)
        common=[('shrub_rounded',(100,385)),('shrub_irregular',(865,425)),('fern_curled',(220,470)),('fern_splayed',(790,390)),('grass_sparse',(310,500)),('grass_splayed',(600,510)),('grass_dense',(790,560)),('flowers_white',(310,180)),('flowers_yellow',(365,170)),('flowers_violet',(650,510)),('groundcover_clover',(200,330)),('groundcover_ivy',(230,340)),('groundcover_moss',(820,365)),('boulder_mossy' if bank=='marsh' else 'boulder_angular',(105,520)),('rock_cluster_round',(665,370)),('fallen_log_weathered',(750,590)),('stump_mossy',(170,350)),('exposed_roots_twisted',(225,365))]
        for i,(name,root) in enumerate(common):place(name,root,i%9,'ground' if name.startswith(('groundcover','exposed_roots')) else 'depth_sorted')
        # Root positions sit on the water's shallow margin; tall stems rise above it.
        for i,(name,root) in enumerate([('tall_reeds_cattails',(386,428)),('tall_reeds_splayed',(435,428)),('rushes_upright',(550,428)),('rushes_splayed',(580,428)),('bank_flowers_white',(640,428)),('bank_flowers_iris',(690,428))]):place(name,root,i)
        occupied={(x,y) for y in range(5,9) for x in range(7,15)};occupied-={(7,5),(14,5),(7,8),(14,8)}
        cells=[];frames=[]
        for phase in range(9):
            scene=Image.new('RGBA',(960,640))
            for y in range(14):
                for x in range(20):
                    tile=earth[0].copy() if 8<=x<=10 else grass[(x//4+y//3)%4].copy()
                    if (x,y) in occupied:
                        mask=normalize(sum(BITS[n] for n,(dx,dy) in OFFSETS.items() if (x+dx,y+dy) in occupied));spatial=x%2+2*(y%2);water=load(ROOT/f'assets/terrain/water_hd/surfaces/{water_family}/deep_0_{spatial}/still.png');tile.alpha_composite(clipped(water,gray(ROOT/'assets/terrain/water_hd'/water_shapes[mask]['water_mask'])));tile.alpha_composite(load(ROOT/f'assets/terrain/water_hd/banks/{bank}/0/mask_{mask:03}.png'))
                        if phase==0:cells.append({'cell':[x,y],'mask':mask,'texture_phase':spatial})
                    scene.alpha_composite(tile,(x*48,y*48))
            def draw_plant(p):
                r=by_id[p['id']];image=sequences[p['id']][(phase+p['phase_offset'])%9] if r['animated'] else native_images[p['id']];ax,ay=r['root_anchor_artwork'];rx,ry=p['root_artwork'];scene.alpha_composite(image,(rx-ax,ry-ay))
            for p in placements:
                if p['layer']=='ground':draw_plant(p)
            actors=[{'file':'assets/characters/caelan/review_hd/idles/idle_front.png','root_artwork':[440,510],'anchor_artwork':[24,68]}]
            depth=[(p['root_artwork'][1],0,p) for p in placements if p['layer']!='ground']+[(a['root_artwork'][1],1,a) for a in actors]
            for _,kind,p in sorted(depth,key=lambda v:(v[0],v[1])):
                if kind:scene.alpha_composite(load(ROOT/p['file']),(p['root_artwork'][0]-p['anchor_artwork'][0],p['root_artwork'][1]-p['anchor_artwork'][1]))
                else:draw_plant(p)
            export(REVIEW+f'/scenes/{scene_id}/frame_{phase:02}.png',scene);frames.append(scene)
        out[REVIEW+'/'+scene_id+'.gif']=save_loop(frames,600);export(REVIEW+'/'+scene_id+'_native.png',frames[0]);layouts.append({'id':scene_id,'size_artwork':[960,640],'ground_rule':'Dirt columns 8..10; grass arrangement (x//4+y//3)%4 elsewhere.','water_family':water_family,'bank_family':bank,'water_cells':cells,'water_animation':'Explicit stills isolate vegetation motion.','placements':placements,'actors':actors,'depth_sort':'Ground overlays first, then ascending root y, plants before actors at equal y.'})
    # Common root baseline with unchanged approved characters for direct size review.
    comparison=Image.new('RGBA',(640,300))
    for y in range(7):
        for x in range(14):comparison.alpha_composite(grass[(x//4+y//3)%4],(x*48,y*48))
    scale_placements=[{'id':'broadleaf_full','root_artwork':[140,270]},{'id':'conifer_fir','root_artwork':[500,270]}]
    scale_actors=[{'file':'assets/characters/caelan/review_hd/idles/idle_front.png','root_artwork':[290,270],'anchor_artwork':[24,68]},{'file':'assets/characters/iselin/idle_front_42x72.png','root_artwork':[345,270],'anchor_artwork':[21,68]}]
    for p in scale_placements:
        r=by_id[p['id']];comparison.alpha_composite(native_images[p['id']],(p['root_artwork'][0]-r['root_anchor_artwork'][0],p['root_artwork'][1]-r['root_anchor_artwork'][1]))
    for a in scale_actors:comparison.alpha_composite(load(ROOT/a['file']),(a['root_artwork'][0]-a['anchor_artwork'][0],a['root_artwork'][1]-a['anchor_artwork'][1]))
    export(REVIEW+'/scale_comparison.png',comparison)
    meta={'version':1,'id':rec['id'],'artwork_state':'rebuilt','integration_status':'not_integrated','visual_approval':rec['visual_approval'],'artwork_pixels_per_world_pixel':2,'logical_tile_size':[24,24],'path_conventions':{'asset_files':'pack_relative','recipe':'repository_relative'},'rect_space':'artwork','anchor_space':'logical unless explicitly artwork-suffixed','design_count':len(items),'family_count':len(family_records),'families':{f:[r['id'] for r in entries] for f,entries in family_records.items()},'plants':items,'animation':rec['animation'],'palette':'palette.json','recipe':'assets/source/terrain/vegetation_hd/recipe.json','activation':'Staged only. No maps, runtime renderer, collision, navigation or shared grass behavior changed.','integration_followup':'Preserve existing contact-responsive shared grass and all logical geometry; verify real movement, occlusion, pause/focus and reduced motion during explicit integration.'}
    doc(PACK+'/plants.json',meta);doc(PACK+'/palette.json',rec['palette']);doc(REVIEW+'/layout.json',{'presentation':'Offline native-density asset compositions, not gameplay captures.','scenes':layouts,'scale_comparison':{'size_artwork':[640,300],'placements':scale_placements,'actors':scale_actors,'root_baseline_artwork':270}});doc(REVIEW+'/exports.json',{'builder':rec['builder'],'sources':rec['sources'],'recipe_sha256':sha256((SOURCE/'recipe.json').read_bytes()).hexdigest(),'outputs':exports});return out

def build(check=False):
    result=products();stale=[]
    for path,raw in result.items():
        p=ROOT/path
        if not p.exists() or p.read_bytes()!=raw:
            stale.append(path)
            if not check:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    if check and stale:raise SystemExit('Stale vegetation exports: '+', '.join(stale))
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args();print(f'{len(build(args.check))} vegetation exports '+('verified' if args.check else 'built'))
