"""Reproducible staged water/shore art. Source drawings provide visible pixels;
retained legacy masks preserve coverage only. No live maps are written."""
from __future__ import annotations
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import statistics
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.build_eldenmere_grass_dirt_hd import normalize, BITS, OFFSETS, rgba, encoded
SOURCE=ROOT/'assets/source/terrain/water_hd'
PACK='assets/terrain/water_hd';REVIEW='docs/reviews/world_water_hd'
FAMILIES=('temperate','cold','peat','lake');BANKS=('grass','earth','sand','rock','marsh')
MASKS=sorted({normalize(m) for m in range(256)})

def load(path):
    with Image.open(path) as im:return im.convert('RGBA')
def gray(path):
    with Image.open(path) as im:return im.convert('L')
def recipe():return json.loads((SOURCE/'recipe.json').read_text())
def grid_cell(im,col,row,cols,rows):
    # Small inset excludes source sheet dividers while preserving native clusters.
    x0,y0=col*im.width//cols,row*im.height//rows;x1,y1=(col+1)*im.width//cols,(row+1)*im.height//rows
    return im.crop((x0+3,y0+3,x1-3,y1-3))
def quantize(im,ramp,target=None,border=0,contrast=1.0):
    im=im.convert('RGBA');out=Image.new('RGBA',im.size);colors=[rgba(c) for c in ramp.values()]
    median=[statistics.median(im.getchannel(c).tobytes()) for c in ('R','G','B')]
    base=rgba(target or ramp.get('base',next(iter(ramp.values()))));cache={}
    for y in range(im.height):
        for x in range(im.width):
            c=im.getpixel((x,y))
            if c[3]<128:continue
            if c not in cache:
                corrected=[base[i]+(c[i]-median[i])*contrast for i in range(3)]
                cache[c]=min(colors,key=lambda p:sum((p[i]-corrected[i])**2 for i in range(3)))
            out.putpixel((x,y),base if min(x,y,im.width-x-1,im.height-y-1)<border else cache[c])
    return out

def clipped(im,mask):
    result=im.copy();result.putalpha(ImageChops.multiply(result.getchannel('A'),mask));out=Image.new('RGBA',im.size);out.alpha_composite(result);return out

def accent_sources(rec):
    source=load(SOURCE/'accents_authored.png');result={}
    ramp={**rec['stone_palette'],**rec['soil_palette'],**{'green_'+k:v for k,v in rec['grass_palette'].items()},**{'water_'+k:v for k,v in rec['water_palettes']['temperate'].items()},'outline':'#171e1a'}
    colors=[rgba(v) for v in ramp.values()]
    for i,(name,size) in enumerate(zip(rec['accent_names'],rec['accent_sizes_artwork'])):
        cell=grid_cell(source,i%3,i//3,3,3);alpha=Image.new('L',cell.size)
        # Magenta removal is a technical cutout, not invented sprite geometry.
        for y in range(cell.height):
            for x in range(cell.width):
                r,g,b,a=cell.getpixel((x,y));alpha.putpixel((x,y),0 if r>g+45 and b>g+35 and r>120 and b>100 else 255)
        box=alpha.getbbox()
        if box is None:raise ValueError('Empty accent '+name)
        cell.putalpha(alpha);cell=cell.crop(box);cell.thumbnail(tuple(size),Image.Resampling.NEAREST)
        im=Image.new('RGBA',tuple(size));im.alpha_composite(cell,((size[0]-cell.width)//2,size[1]-cell.height))
        for y in range(im.height):
            for x in range(im.width):
                c=im.getpixel((x,y))
                if c[3]:im.putpixel((x,y),min(colors,key=lambda p:sum((p[i]-c[i])**2 for i in range(3))))
        result[name]=im
    return result

def geometry(rec):
    result={kind:{} for kind in ('water','bank','shallow')}
    for r in rec['geometry']:result[r['kind']][r['mask']]=gray(SOURCE/r['file']).resize((48,48),Image.Resampling.NEAREST)
    return result

def materials(rec):
    water=load(SOURCE/'water_authored.png');banks=load(SOURCE/'banks_authored.png');surfaces={};ground={}
    for row,name in enumerate(FAMILIES):
        for variant in range(2):
            cell=grid_cell(water,variant,row,2,4).resize((96,96),Image.Resampling.NEAREST)
            for depth in ('shallow','deep'):
                ramp=rec['water_palettes'][name];base=ramp['shallow' if depth=='shallow' else 'base'];pattern=quantize(cell,ramp,base,2,1.3)
                for phase in range(4):
                    x,y=phase%2*48,phase//2*48;tile=pattern.crop((x,y,x+48,y+48))
                    # Quiet paired ports allow all arrangements while retaining a larger field.
                    for yy in range(48):
                        for xx in range(48):
                            if min(xx,yy,47-xx,47-yy)<2:tile.putpixel((xx,yy),rgba(base))
                    surfaces[name,depth,variant,phase]=tile
    for row,name in enumerate(BANKS):
        for variant in range(2):ground[name,variant]=quantize(grid_cell(banks,variant,row,2,5).resize((48,48),Image.Resampling.NEAREST),rec['bank_palettes'][name],border=2,contrast=1.15)
    return surfaces,ground

def tinted_glyph(glyph,color):
    im=Image.new('RGBA',glyph.size,rgba(color));return clipped(im,glyph.getchannel('A'))

def water_frames(rec,surfaces,accents):
    result={}
    for key,base in surfaces.items():
        name,depth,variant,spatial_phase=key;frames=[]
        for phase in range(6):
            im=base.copy();role=rec['ripple_roles'][phase]
            if role:
                glyph=tinted_glyph(accents['ripple'],rec['water_palettes'][name][role]);dx,dy=rec['ripple_offsets_artwork'][phase]
                for x,y in ([(6,9)] if (variant+spatial_phase)%2==0 else [(21,29)]):im.alpha_composite(glyph,(x+dx,y+dy))
            frames.append(im)
        result[key]=frames
    return result

def mix_banks(a,b,selector,contact_color):
    """Select actual bank material per pixel, with a fixed narrow soil meeting lip."""
    out=Image.composite(b,a,selector);expanded=selector.filter(ImageFilter.MaxFilter(3));eroded=selector.filter(ImageFilter.MinFilter(3));seam=ImageChops.subtract(expanded,eroded)
    coverage=ImageChops.lighter(a.getchannel('A'),b.getchannel('A'));seam=ImageChops.multiply(seam,coverage)
    out.paste(Image.new('RGBA',out.size,rgba(contact_color)),(0,0),seam);return out

def depth_control(mask):
    # Three discrete depth steps; never a fuzzy alpha edge or changed shoreline.
    result=Image.new('L',mask.size);current=mask.copy()
    for value in (85,170,255):
        current=current.filter(ImageFilter.MinFilter(5));result=ImageChops.lighter(result,current.point(lambda p:value if p else 0))
    return result

def compose_water(shallow,deep,mask,control=None):
    if control is None:return clipped(deep,mask)
    mixed=Image.composite(deep,shallow,control)
    # Register depth steps back to the family's drawn palette, avoiding an
    # accidental explosion of intermediate RGB colors in the scene/GIF.
    ramp=set(shallow.getdata())|set(deep.getdata());cache={}
    for y in range(mixed.height):
        for x in range(mixed.width):
            c=mixed.getpixel((x,y))
            if c not in cache:cache[c]=min(sorted(ramp),key=lambda p:sum((p[i]-c[i])**2 for i in range(3)))
            mixed.putpixel((x,y),cache[c])
    return clipped(mixed,mask)

def current_frame(route,phase,glyph,ramp,size=48):
    """Move a drawn current glyph along each directed half-path through the hub.
    Ports are deliberately quiet at the outer two artwork pixels."""
    out=Image.new('RGBA',(size,size));center=size//2;vectors={'N':(0,-1),'E':(1,0),'S':(0,1),'W':(-1,0)}
    branches=[(route['input'],True)] if route['input'] in vectors else []
    branches += [(p,False) for p in route['outputs'] if p in vectors]
    ink=tinted_glyph(glyph,ramp['reflection'])
    # A slim source-derived glyph, not a generated line rig.
    ink=ink.resize((6,2),Image.Resampling.NEAREST)
    for port,incoming in branches:
        vx,vy=vectors[port];piece=ink if port in ('N','S') else ink.transpose(Image.Transpose.ROTATE_90)
        for offset in (0,):
            distance=((phase*4+offset)%24)
            radius=(24-distance) if incoming else distance
            px=center+vx*radius-piece.width//2;py=center+vy*radius-piece.height//2
            out.alpha_composite(piece,(px,py))
        # One period covers each half path; loop resets at a quiet port.
    alpha=out.getchannel('A');ImageDraw.Draw(alpha).rectangle((0,0,47,1),fill=0);ImageDraw.Draw(alpha).rectangle((0,46,47,47),fill=0);ImageDraw.Draw(alpha).rectangle((0,0,1,47),fill=0);ImageDraw.Draw(alpha).rectangle((46,0,47,47),fill=0)
    return clipped(out,alpha)

def save_loop(images,duration=200):
    # One common GIF palette prevents fixed terrain pixels from flickering.
    rgb=[im.convert('RGB') for im in images];master=Image.new('RGB',(rgb[0].width,rgb[0].height*len(rgb)))
    for i,im in enumerate(rgb):master.paste(im,(0,i*im.height))
    colors=sorted(set(master.getdata()))
    if len(colors)>256:raise ValueError('Review exceeds lossless GIF palette budget; use PNG frames or reduce palette deliberately.')
    lookup={c:i for i,c in enumerate(colors)};palette=[v for c in colors for v in c]+[0]*(768-len(colors)*3);frames=[]
    for im in rgb:
        frame=Image.frombytes('P',im.size,bytes(lookup[c] for c in im.getdata()));frame.putpalette(palette);frames.append(frame)
    stream=BytesIO()
    frames[0].save(stream,format='GIF',save_all=True,append_images=frames[1:],duration=duration,loop=0,optimize=False,disposal=2)
    return stream.getvalue()

def products():
    rec=recipe();out={};records=[]
    for r in rec['sources']+rec['geometry']:
        if sha256((SOURCE/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Changed water source '+r['file'])
    def export(path,im):
        raw=encoded(im);out[path]=raw;records.append({'file':path,'artwork_size':list(im.size),'sha256':sha256(raw).hexdigest()})
    def doc(path,data):out[path]=(json.dumps(data,indent=2)+'\n').encode()
    geo=geometry(rec);surfaces,ground=materials(rec);accents=accent_sources(rec);frames=water_frames(rec,surfaces,accents)
    water_records=[]
    for key,sequence in frames.items():
        family,depth,variant,spatial_phase=key;paths=[]
        for phase,im in enumerate(sequence):path=f'surfaces/{family}/{depth}_{variant}_{spatial_phase}/frame_{phase:02}.png';export(PACK+'/'+path,im);paths.append({'file':path,'duration_ms':200})
        still=f'surfaces/{family}/{depth}_{variant}_{spatial_phase}/still.png';export(PACK+'/'+still,surfaces[key])
        water_records.append({'family':family,'depth':depth,'arrangement':variant,'texture_phase':spatial_phase,'frames':paths,'still':still,'logical_size':[24,24],'animation_frame_space':'temporal','arrangement_rule':'Either arrangement is compatible; choose deterministically in coherent groups.','texture_phase_rule':'(world_tile_x%2)+2*(world_tile_y%2), common origin; four phases span a 96x96 artwork pattern.'})
    for name,im in accents.items():export(PACK+'/accents/'+name+'.png',im)
    effects=[]
    for name in ('ripple','eddy','foam','impact'):
        paths=[]
        for phase in range(6):
            canvas=Image.new('RGBA',(32,24));role=rec['ripple_roles'][phase]
            if role:
                glyph=tinted_glyph(accents[name],rec['water_palettes']['temperate'][role]);dx,dy=rec['ripple_offsets_artwork'][phase];canvas.alpha_composite(glyph,((32-glyph.width)//2+dx,(24-glyph.height)//2+dy))
            path=f'effects/{name}/frame_{phase:02}.png';export(PACK+'/'+path,canvas);paths.append(path)
        effects.append({'id':name,'frames':paths,'logical_size':[16,12],'draw_anchor_logical':[8,6],'clip':'receiving water mask','palette_role':'Recolor to receiving water family; omit in reduced motion.'})
    shapes=[];bank_images={};bank_records=[]
    for index,mask in enumerate(MASKS):
        shapes.append({'mask':mask,'index':index,'rect':[index%8*48,index//8*48,48,48],'water_mask':f'masks/water_{mask:03}.png','bank_mask':f'masks/bank_{mask:03}.png','shallow_mask':f'masks/shallow_{mask:03}.png','depth_control':f'depth_controls/{mask:03}.png'})
        for kind,items in geo.items():export(PACK+f'/masks/{kind}_{mask:03}.png',items[mask])
        export(PACK+f'/depth_controls/{mask:03}.png',depth_control(geo['water'][mask]))
    for name in BANKS:
        for variant in range(2):
            atlas=Image.new('RGBA',(384,288))
            for r in shapes:
                mask=r['mask'];im=clipped(ground[name,variant],geo['bank'][mask]);bank_images[name,variant,mask]=im
                path=f'banks/{name}/{variant}/mask_{mask:03}.png';export(PACK+'/'+path,im);atlas.alpha_composite(im,tuple(r['rect'][:2]))
                bank_records.append({'family':name,'arrangement':variant,'mask':mask,'file':path,'atlas':f'atlases/banks_{name}_{variant}.png','rect':r['rect'],'logical_size':[24,24]})
            export(PACK+f'/atlases/banks_{name}_{variant}.png',atlas)
    # Twenty oriented pieces per bank and coverage layer, using canonical representatives.
    quarter_records=[]
    from tools.build_eldenmere_grass_dirt_hd import QUARTERS,STATES
    for orientation,(x,y,h,v,d) in QUARTERS.items():
        for state,flags in STATES.items():
            mask=normalize(sum(BITS[n] for n,on in zip((h,v,d),flags) if on));box=(x,y,x+24,y+24);q={'id':orientation+'_'+state,'water':f'quarters/water/{orientation}_{state}.png','banks':{}}
            export(PACK+'/'+q['water'],geo['water'][mask].crop(box))
            for name in BANKS:
                q['banks'][name]=[]
                for variant in range(2):
                    path=f'quarters/{name}_{variant}/{orientation}_{state}.png';export(PACK+'/'+path,bank_images[name,variant,mask].crop(box));q['banks'][name].append(path)
            quarter_records.append(q)
    junctions=[]
    for a,b in rec['mixed_bank_pairs']:
        for axis in ('x','y'):
            selector=Image.new('L',(48,48));draw=ImageDraw.Draw(selector);draw.rectangle((24,0,47,47) if axis=='x' else (0,24,47,47),fill=255)
            atlas=Image.new('RGBA',(384,288))
            for r in shapes:atlas.alpha_composite(mix_banks(bank_images[a,0,r['mask']],bank_images[b,0,r['mask']],selector,rec['mix_contact_color']),tuple(r['rect'][:2]))
            path=f'junctions/{a}_{b}_{axis}.png';export(PACK+'/'+path,atlas);junctions.append({'materials':[a,b],'axis':axis,'atlas':path,'selection':'Per-pixel material selector, with a one-artwork-pixel soil lip on each side of the meeting line.','contact_color':rec['mix_contact_color']})
    current_records=[];current_images={}
    routes=[{'id':'straight_'+p,'input':{'N':'S','E':'W','S':'N','W':'E'}[p],'outputs':[p]} for p in ('N','E','S','W')]
    for incoming in ('N','E','S','W'):
        for outgoing in ('N','E','S','W'):
            if incoming!=outgoing and (incoming,outgoing) not in (('N','S'),('S','N'),('E','W'),('W','E')):routes.append({'id':'bend_'+incoming+'_'+outgoing,'input':incoming,'outputs':[outgoing]})
    # Mouth/widen/narrow use the same coherent direction with a different source glyph footprint.
    for kind in ('mouth','widen','narrow'):
        for p in ('N','E','S','W'):routes.append({'id':kind+'_'+p,'input':{'N':'S','E':'W','S':'N','W':'E'}[p],'outputs':[p]})
    for route in routes:
        paths=[]
        for phase in range(6):
            im=current_frame(route,phase,accents['ripple'],rec['water_palettes']['temperate']);path=f'currents/{route["id"]}/frame_{phase:02}.png';export(PACK+'/'+path,im);paths.append(path);current_images[route['id'],phase]=im
        current_records.append({**route,'frames':paths,'logical_size':[24,24],'palette_role':'reflection; recolor into receiving water family','coverage':'Clip to receiving water mask. Geometry widening/narrowing is defined by adjacent blob masks, not this current overlay.'})
    # Review scenes are reconstructible offline fixtures, not active map changes.
    gm=json.loads((ROOT/'assets/terrain/eldenmere/grass_dirt_hd/tileset.json').read_text());grass=[load(ROOT/'assets/terrain/eldenmere/grass_dirt_hd'/p) for p in gm['materials']['grass']];earth=[load(ROOT/'assets/terrain/eldenmere/grass_dirt_hd'/p) for p in gm['materials']['dirt']]
    def neighborhood(cells,x,y):return normalize(sum(BITS[n] for n,(dx,dy) in OFFSETS.items() if (x+dx,y+dy) in cells))
    layouts=[];scene_sequences=[]
    specs=[('eldenmere','temperate','grass'),('mountain','cold','rock'),('lake','lake','sand'),('marsh','peat','marsh')]
    for name,family,bank in specs:
        occupied={(x,y) for y in range(2,10) for x in range(2,14) if ((x-7.5)/6)**2+((y-5.5)/4)**2<1}
        occupied-={(7,5),(8,5),(7,6),(8,6)};occupied|={(x,9) for x in range(8,16)}|{(14,8),(14,7),(1,1),(0,0)}
        cells=[];sequence=[]
        for phase in range(6):
            scene=Image.new('RGBA',(768,576))
            for y in range(12):
                for x in range(16):
                    tile=grass[(x//3+y//3)%4].copy() if bank=='grass' else (earth[0].copy() if bank=='earth' else ground[bank,(x//3+y//3)%2].copy())
                    if (x,y) in occupied:
                        mask=neighborhood(occupied,x,y);variant=(x//3+y//3)%2;water=compose_water(frames[family,'shallow',variant,x%2+2*(y%2)][phase],frames[family,'deep',variant,x%2+2*(y%2)][phase],geo['water'][mask],depth_control(geo['water'][mask]));tile.alpha_composite(water)
                        shallow=tinted_glyph(Image.merge('RGBA',(geo['shallow'][mask],)*4),rec['water_palettes'][family]['shallow']);tile.alpha_composite(shallow);tile.alpha_composite(bank_images[bank,variant,mask])
                        if phase==0:cells.append({'cell':[x,y],'mask':mask,'bank':bank,'arrangement':variant,'texture_phase':x%2+2*(y%2),'family':family})
                    scene.alpha_composite(tile,(x*48,y*48))
            # Separate accent placement: submerged bits remain beneath emergent rock/plant assets.
            placements=[('submerged_pebbles',(195,190)),('wet_rock',(245,220)),('reed_roots',(500,454))] if name=='eldenmere' else [('submerged_pebbles',(195,190)),('wet_rock',(245,220))] if name=='mountain' else [('mud_gravel',(570,430)),('rushes',(500,446))] if name=='marsh' else [('mud_gravel',(570,430)),('wet_rock',(245,220))]
            for accent,pos in placements:scene.alpha_composite(accents[accent],pos)
            actor=load(ROOT/'assets/characters/caelan/review_hd/idles/idle_front.png');scene.alpha_composite(actor,(70,260))
            export(REVIEW+f'/{name}/frame_{phase:02}.png',scene);sequence.append(scene)
        out[REVIEW+'/'+name+'.gif']=save_loop(sequence);export(REVIEW+'/'+name+'_native.png',sequence[0]);layouts.append({'id':name,'size_artwork':[768,576],'cells':cells,'accent_placements':[{'id':n,'position_artwork':list(p)} for n,p in placements],'character':{'file':'assets/characters/caelan/review_hd/idles/idle_front.png','position_artwork':[70,260]},'ground':'grass' if bank=='grass' else bank});scene_sequences.append(sequence)
    # Broad field exposes repetition at native density without decorative cover.
    repeated=[]
    for phase in range(6):
        field=Image.new('RGBA',(768,384))
        for y in range(8):
            for x in range(16):field.alpha_composite(frames['temperate','deep',(x//4+y//3)%2,x%2+2*(y%2)][phase],(x*48,y*48))
        repeated.append(field)
    export(REVIEW+'/repeated_water_native.png',repeated[0]);out[REVIEW+'/repeated_water.gif']=save_loop(repeated)
    # Representative banks and source/material studies.
    board=Image.new('RGB',(5*200,2*218),'#e8e9df');draw=ImageDraw.Draw(board)
    for col,bank in enumerate(BANKS):
        for row,mask in enumerate((4,7)):
            tile=grass[0].copy();tile.alpha_composite(compose_water(frames['temperate','shallow',0,0][0],frames['temperate','deep',0,0][0],geo['water'][mask],depth_control(geo['water'][mask])));tile.alpha_composite(bank_images[bank,0,mask]);board.paste(tile.resize((192,192),Image.Resampling.NEAREST),(col*200,row*218));draw.text((col*200+3,row*218+195),bank+' / '+('straight' if row==0 else 'corner'),fill='#243529')
    export(REVIEW+'/shore_study.png',board)
    board=Image.new('RGB',(4*200,2*218),'#e8e9df');draw=ImageDraw.Draw(board)
    for col,family in enumerate(FAMILIES):
        for row,depth in enumerate(('shallow','deep')):board.paste(frames[family,depth,0,0][0].convert('RGB').resize((192,192),Image.Resampling.NEAREST),(col*200,row*218));draw.text((col*200+3,row*218+195),family+' / '+depth,fill='#243529')
    export(REVIEW+'/water_study.png',board)
    for bank in BANKS:
        atlas=Image.new('RGBA',(384,288))
        for r in shapes:
            tile=grass[0].copy();tile.alpha_composite(clipped(frames['temperate','deep',0,0][0],geo['water'][r['mask']]));tile.alpha_composite(bank_images[bank,0,r['mask']]);atlas.alpha_composite(tile,tuple(r['rect'][:2]))
        export(REVIEW+f'/blob_{bank}.png',atlas)
    meta={'version':1,'id':rec['id'],'artwork_state':'rebuilt','integration_status':'not_integrated','visual_approval':rec['visual_approval'],'artwork_pixels_per_world_pixel':2,'logical_tile_size':[24,24],'artwork_tile_size':[48,48],'rect_space':'artwork','anchor_space':'logical','draw_anchor_logical':[12,24],'path_space':'pack_relative','shape_count':47,'lookup_256':[MASKS.index(normalize(m)) for m in range(256)],'neighbor_bits':BITS,'diagonal_rule':'A diagonal requires both adjoining cardinals.','shapes':shapes,'water_surfaces':water_records,'bank_tiles':bank_records,'bank_families':list(BANKS),'water_families':list(FAMILIES),'quarters':quarter_records,'mixed_bank_junctions':junctions,'current_overlays':current_records,'effect_overlays':effects,'accents':[{'id':n,'file':'accents/'+n+'.png','logical_size':[im.width/2,im.height/2],'draw_anchor_logical':[im.width/4,im.height/2],'depth_baseline_logical':im.height/2,'placement':'submerged water bed' if n=='submerged_pebbles' else 'bank/water effect' if n in ('ripple','eddy','foam','impact') else 'grounded shore decoration','collision':'none; no runtime registration','interaction_cues':False} for n,im in accents.items()],'animation':{'frame_count':6,'duration_ms':200,'cycle_ms':1200,'clock':'Shared phase for connected water, currents, channels and spillways.','reduced_motion':'Use the explicit surface still images and omit animated effects.'},'layer_order':['ground','masked_water_and_depth','optional_submerged_bed','stationary_shallow_margin','stationary_bank','masked_currents_and_foam','depth_sorted_rocks_plants_actors'],'depth_control':'L-mode 0/85/170/255 depth selection, not collision or alpha. Intersect with water coverage.','supported_bank_pairs':rec['mixed_bank_pairs'],'mix_contact_color':rec['mix_contact_color'],'unsupported':['open-ocean surf','frozen surfaces','magical water','arbitrary mixed-bank material joins'],'palette':'palette.json','recipe':'assets/source/terrain/water_hd/recipe.json','activation':'No runtime registration; actual movement/collision/occlusion acceptance deferred.'}
    doc(PACK+'/tileset.json',meta);doc(PACK+'/palette.json',{'water':rec['water_palettes'],'banks':rec['bank_palettes'],'accent_sources':'Existing stone, soil, emerald and temperate-water ramps; thin contour #171e1a.'});doc(REVIEW+'/layout.json',{'presentation':'Offline illustrative compositions, not gameplay captures.','scenes':layouts});doc(REVIEW+'/exports.json',{'builder':rec['builder'],'recipe_sha256':sha256((SOURCE/'recipe.json').read_bytes()).hexdigest(),'sources':rec['sources'],'outputs':records});return out

def build(check=False):
    result=products();stale=[]
    for path,raw in result.items():
        p=ROOT/path
        if not p.exists() or p.read_bytes()!=raw:
            stale.append(path)
            if not check:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    if check and stale:raise SystemExit('Stale water exports: '+', '.join(stale))
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args();print(f'{len(build(args.check))} water/shore exports '+('verified' if args.check else 'built'))
