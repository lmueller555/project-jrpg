"""Build staged 2× paving, phase-continuous stone and material-aware contact trims.

Only new pack/review paths are written. All source drawings, reference banks and
playable map data are read-only; this exporter installs no runtime integration.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import statistics
import sys
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.build_eldenmere_grass_dirt_hd import BITS,OFFSETS,QUARTERS,STATES,normalize,inside,state,rgba,tree_digest
SOURCE=ROOT/'assets/source/terrain/eldenmere/stone_paving_hd'
PACK='assets/terrain/eldenmere/stone_paving_hd'
REVIEW='docs/reviews/eldenmere_hd_stone'
GROUND='assets/terrain/eldenmere/grass_dirt_hd'
SIZE=48

def read_recipe():return json.loads((SOURCE/'recipe.json').read_text())
def load(path):
    with Image.open(path) as im:return im.convert('RGBA')
def encoded(im):
    out=BytesIO();im.save(out,format='PNG',optimize=True);return out.getvalue()
def palette_map(im,ramp,target=None,contrast=1.):
    source=im.convert('RGBA');colors=[rgba(c) for c in ramp.values()];cache={};out=Image.new('RGBA',source.size)
    medians=[statistics.median(source.getchannel(c).tobytes()) for c in ('R','G','B')]
    base=rgba(target) if target else medians
    for y in range(source.height):
        for x in range(source.width):
            pixel=source.getpixel((x,y))
            if pixel[3]<128:continue
            if pixel[:3] not in cache:
                calibrated=[base[i]+(pixel[i]-medians[i])*contrast for i in range(3)] if target else pixel[:3]
                cache[pixel[:3]]=min(colors,key=lambda c:sum((c[i]-calibrated[i])**2 for i in range(3)))
            out.putpixel((x,y),cache[pixel[:3]])
    return out

def source_pattern(rec):
    spec=rec['pattern'];size=tuple(spec['artwork_size']);raw=load(SOURCE/spec['source']).resize(size,Image.Resampling.NEAREST)
    reference=load(SOURCE/spec['boundary_reference']).resize(size,Image.Resampling.NEAREST)
    band=spec['source_perimeter_restoration_artwork_pixels'];w,h=size
    for box in ((0,0,w,band),(0,h-band,w,h),(0,band,band,h-band),(w-band,band,w,h-band)):
        raw.paste(reference.crop(box),box[:2])
    out=palette_map(raw,rec['palette']['stone'],rec['palette']['stone']['base'],spec['contrast'])
    # One-pixel paired ports; remaining drawn stone faces/joints are untouched.
    for y in range(h):
        out.putpixel((w-1,y),out.getpixel((0,y)));out.putpixel((48,y),out.getpixel((47,y)))
    for x in range(w):
        out.putpixel((x,h-1),out.getpixel((x,0)));out.putpixel((x,48),out.getpixel((x,47)))
    return out

def phase_at(x,y):return (x%2)+2*(y%2)
def coverage(mask,rec):
    points={(x,y):inside(mask,x,y,rec) for y in range(-1,49) for x in range(-1,49)}
    core=Image.new('RGBA',(48,48));contact=Image.new('RGBA',(48,48));cap=Image.new('1',(48,48))
    for y in range(48):
        for x in range(48):
            neighbors=[points[p] for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))]
            if points[x,y]:
                core.putpixel((x,y),(255,255,255,255));cap.putpixel((x,y),not all(neighbors))
            elif any(neighbors):contact.putpixel((x,y),(255,255,255,255))
    return core,contact,cap

def stone_tile(texture,core,cap,rec):
    raw=texture.copy();raw.putalpha(core.getchannel('A'));im=Image.new('RGBA',raw.size);im.alpha_composite(raw)
    for y in range(48):
        for x in range(48):
            if cap.getpixel((x,y)):im.putpixel((x,y),rgba(rec['palette']['stone']['joint']))
    return im

def colored_mask(mask,color):
    raw=Image.new('RGBA',mask.size,rgba(color));raw.putalpha(mask.getchannel('A'));im=Image.new('RGBA',raw.size);im.alpha_composite(raw);return im

def compose(ground,body,grass_trim,dirt_trim,dirt_mask):
    """Offline review layering; select trim from the actual substrate per pixel."""
    trim=Image.new('RGBA',(48,48));a=grass_trim.copy();b=dirt_trim.copy()
    ga=bytearray(a.getchannel('A').tobytes());da=bytearray(b.getchannel('A').tobytes());under=dirt_mask.tobytes()
    for i,value in enumerate(under):
        if value:ga[i]=0
        else:da[i]=0
    a.putalpha(Image.frombytes('L',(48,48),bytes(ga)));b.putalpha(Image.frombytes('L',(48,48),bytes(da)))
    trim.alpha_composite(a);trim.alpha_composite(b)
    result=ground.copy();result.alpha_composite(trim);result.alpha_composite(body);return result

def mask_at(cells,x,y):return normalize(sum(bit for name,bit in BITS.items() if (x+OFFSETS[name][0],y+OFFSETS[name][1]) in cells))

def products():
    rec=read_recipe();out={};records=[]
    for r in rec['sources']:
        if sha256((SOURCE/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Paving source changed: '+r['file'])
    def export(path,im):
        raw=encoded(im);out[path]=raw;records.append({'file':path,'artwork_size':list(im.size),'sha256':sha256(raw).hexdigest()})
    def document(path,data):out[path]=(json.dumps(data,indent=2,ensure_ascii=False)+'\n').encode()
    master=source_pattern(rec);export(PACK+'/surface/pattern_96.png',master)
    phases=[master.crop((i%2*48,i//2*48,i%2*48+48,i//2*48+48)) for i in range(4)]
    for i,im in enumerate(phases):export(f'{PACK}/surface/phase_{i}.png',im)
    mortar=Image.new('RGBA',(96,96));joint_colors={rgba(rec['palette']['stone'][n]) for n in ('joint','shadow')}
    for y in range(96):
        for x in range(96):
            if master.getpixel((x,y)) in joint_colors:mortar.putpixel((x,y),(255,255,255,255))
    export(PACK+'/surface/mortar_mask.png',mortar)
    moss_sheet=load(SOURCE/rec['moss']['source']);moss=[]
    moss_ramp={n:rec['palette']['grass'][n] for n in rec['moss']['palette_roles']}
    for i in range(4):
        box=(round(i%2*moss_sheet.width/2),round(i//2*moss_sheet.height/2),round((i%2+1)*moss_sheet.width/2),round((i//2+1)*moss_sheet.height/2))
        cell=moss_sheet.crop(box);cell.putalpha(cell.getchannel('A').point(lambda a:255 if a>=128 else 0));bounds=cell.getbbox()
        if not bounds:raise ValueError('Missing moss source '+str(i))
        crop=cell.crop(bounds);scale=20/max(crop.size);sample=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.NEAREST)
        im=Image.new('RGBA',(24,24));im.alpha_composite(palette_map(sample,moss_ramp),((24-sample.width)//2,(24-sample.height)//2));moss.append(im);export(f'{PACK}/accents/moss_{i}.png',im)
    masks=sorted({normalize(i) for i in range(256)});shapes={m:coverage(m,rec) for m in masks}
    trims={name:{m:colored_mask(shapes[m][1],rec['palette'][name]['moss' if name=='grass' else 'edge']) for m in masks} for name in ('grass','dirt')}
    bodies={(m,p):stone_tile(phases[p],shapes[m][0],shapes[m][2],rec) for m in masks for p in range(4)}
    atlases=[Image.new('RGBA',(384,288)) for _ in range(4)];contacts={n:Image.new('RGBA',(384,288)) for n in trims};alpha=Image.new('RGBA',(384,288));entries=[]
    for i,m in enumerate(masks):
        pos=(i%8*48,i//8*48);files=[]
        for p in range(4):
            name=f'body/phase_{p}/mask_{m:03}.png';export(PACK+'/'+name,bodies[m,p]);files.append(name);atlases[p].alpha_composite(bodies[m,p],pos)
        trim_files={}
        for n in trims:
            name=f'contact/{n}/mask_{m:03}.png';export(PACK+'/'+name,trims[n][m]);contacts[n].alpha_composite(trims[n][m],pos);trim_files[n]=name
        alpha.alpha_composite(shapes[m][0],pos)
        quarters=[]
        for q,(x,y,h,v,d) in QUARTERS.items():quarters.append(f'quarters/coverage/{q}_{state(bool(m&BITS[h]),bool(m&BITS[v]),bool(m&BITS[d]))}.png')
        entries.append({'index':i,'mask':m,'rect':[*pos,48,48],'body_files':files,'contact_files':trim_files,'coverage_quarters':quarters})
    for p,im in enumerate(atlases):export(f'{PACK}/paving_47_phase_{p}.png',im)
    for n,im in contacts.items():export(f'{PACK}/contact_{n}_47.png',im)
    export(PACK+'/coverage_47.png',alpha)
    for q,(x,y,h,v,d) in QUARTERS.items():
        for kind,flags in STATES.items():
            m=sum(BITS[b] for b,on in zip((h,v,d),flags) if on);box=(x,y,x+24,y+24)
            export(f'{PACK}/quarters/coverage/{q}_{kind}.png',shapes[m][0].crop(box))
            for n in trims:export(f'{PACK}/quarters/{n}/{q}_{kind}.png',trims[n][m].crop(box))
    # Labelled shape sheets use phase zero for direct visual comparison. Pattern
    # repetition and phase-crossing examples below use the required world phases.
    ground_meta=json.loads((ROOT/GROUND/'tileset.json').read_text())
    grass=[load(ROOT/GROUND/p) for p in ground_meta['materials']['grass']];dirt=[load(ROOT/GROUND/p) for p in ground_meta['materials']['dirt']]
    for n,background in (('grass',grass[0]),('dirt',dirt[0])):
        board=Image.new('RGB',(8*154,6*174+44),'#e8e9df');draw=ImageDraw.Draw(board);draw.text((12,10),f'Eldenmere / STONE 2x / 47 shapes on {n} / NOT INTEGRATED',fill='#243529')
        for i,m in enumerate(masks):
            im=background.copy();im.alpha_composite(trims[n][m]);im.alpha_composite(bodies[m,0]);x=i%8*154+5;y=i//8*174+35
            board.paste(im.convert('RGB').resize((144,144),Image.Resampling.NEAREST),(x,y));draw.text((x,y+148),f'{i:02} / mask {m:03}',fill='#243529')
        export(f'{REVIEW}/blob_on_{n}.png',board)
    repeated=Image.new('RGBA',(480,384))
    for y in range(8):
        for x in range(10):repeated.alpha_composite(phases[phase_at(x,y)],(x*48,y*48))
    export(REVIEW+'/repeated_surface_native.png',repeated)
    # Two established ground families meet beneath the independent paving layer.
    width,height=20,16;earth=set();paved=set()
    for y in range(6,11):
        for x in range(1,19):earth.add((x,y))
    earth.update((x,y) for y in range(0,16) for x in range(15,18))
    paved.update((x,y) for y in range(3,12) for x in range(9,18));paved.update((x,y) for y in range(2,15) for x in range(4,5))
    paved.update((x,y) for y in range(8,10) for x in range(4,12));paved.difference_update((x,y) for y in range(5,7) for x in range(12,14));paved.update({(1,2),(2,3),(7,13)})
    gt={r['mask']:load(ROOT/GROUND/r['file']) for r in ground_meta['tiles']};scene=Image.new('RGBA',(960,768));underlay=Image.new('RGBA',scene.size);body_layer=Image.new('RGBA',scene.size);contact_layer=Image.new('RGBA',scene.size);cells=[]
    for y in range(height):
        row=[]
        for x in range(width):
            g=(x//3+y//4)%len(grass);dm=mask_at(earth,x,y) if (x,y) in earth else None;fill=(x//3+y//3)%4 if dm==255 else None
            bg=grass[g].copy();dmask=Image.new('L',(48,48))
            if dm is not None:
                if fill is not None:bg=dirt[fill].copy();dmask=Image.new('L',(48,48),255)
                else:bg.alpha_composite(gt[dm]);dmask=gt[dm].getchannel('A')
            underlay.alpha_composite(bg,(x*48,y*48));pm=mask_at(paved,x,y) if (x,y) in paved else None;p=phase_at(x,y)
            if pm is not None:
                body=bodies[pm,p];bg=compose(bg,body,trims['grass'][pm],trims['dirt'][pm],dmask)
                body_layer.alpha_composite(body,(x*48,y*48))
                contact=compose(Image.new('RGBA',(48,48)),Image.new('RGBA',(48,48)),trims['grass'][pm],trims['dirt'][pm],dmask);contact_layer.alpha_composite(contact,(x*48,y*48))
            scene.alpha_composite(bg,(x*48,y*48));row.append({'grass':g,'dirt_mask':dm,'dirt_fill':fill,'paving_mask':pm,'texture_phase':p})
        cells.append(row)
    export(REVIEW+'/underlay_native.png',underlay);export(REVIEW+'/stone_body_native.png',body_layer);export(REVIEW+'/contacts_native.png',contact_layer)
    clean=scene.copy();accent_layer=Image.new('RGBA',scene.size);accent_placements=[]
    for i,(x,y) in enumerate(((9*48+8,3*48+10),(16*48+12,11*48+12),(10*48+12,4*48+8),(4*48+8,3*48+12))):
        patch=moss[i];opaque=[(xx,yy) for yy in range(24) for xx in range(24) if patch.getpixel((xx,yy))[3]]
        candidates=[(x+dx,y+dy) for dy in range(-12,13,2) for dx in range(-12,13,2)]
        count=lambda point:sum(body_layer.getpixel((point[0]+xx,point[1]+yy)) in joint_colors for xx,yy in opaque)
        x,y=max(candidates,key=count);visible=0
        for xx,yy in opaque:
            world=(x+xx,y+yy)
            if body_layer.getpixel(world) in joint_colors:accent_layer.putpixel(world,patch.getpixel((xx,yy)));visible+=1
        accent_placements.append({'variant':i,'position_artwork':[x,y],'visible_pixels':visible})
    scene.alpha_composite(accent_layer);export(REVIEW+'/moss_native.png',accent_layer)
    export(REVIEW+'/layout_clean_native.png',clean);export(REVIEW+'/layout_native.png',scene)
    export(REVIEW+'/three_material_closeup.png',scene.crop((8*48,5*48,13*48,10*48)).resize((720,720),Image.Resampling.NEAREST))
    staged=scene.copy();references=[];path='assets/terrain/eldenmere/cottage/closed.png';building=load(ROOT/path);building=building.resize((building.width*2,building.height*2),Image.Resampling.NEAREST);staged.alpha_composite(building,(11*48,0));references.append({'file':path,'position_artwork':[11*48,0],'density':1})
    for path,foot,anchor in [('assets/characters/caelan/review_hd/idles/idle_front.png',(10*48,9*48),(24,60)),('assets/characters/iselin/idle_front_42x72.png',(12*48,10*48),(21,60))]:
        im=load(ROOT/path);pos=(foot[0]-anchor[0],foot[1]-anchor[1]);staged.alpha_composite(im,pos);references.append({'file':path,'position_artwork':list(pos),'density':2})
    export(REVIEW+'/scale_scene_native.png',staged)
    export(REVIEW+'/walkway_scale_closeup.png',staged.crop((8*48,7*48,14*48,12*48)).resize((864,720),Image.Resampling.NEAREST))
    document(REVIEW+'/layout.json',{'size_tiles':[width,height],'logical_tile_size':[24,24],'artwork_tile_size':[48,48],'cells':cells,'references':references,'moss_placements':accent_placements,'presentation':'Offline illustrative composition; no playable map or runtime activation.'})
    metadata={'version':1,'id':rec['id'],'artwork_state':'rebuilt','integration_status':'not_integrated','visual_approval':rec['visual_approval'],'artwork_pixels_per_world_pixel':2,'logical_tile_size':[24,24],'artwork_tile_size':[48,48],'logical_quarter_size':[12,12],'artwork_quarter_size':[24,24],'rect_space':'artwork','anchor_space':'logical','shape_count':47,'texture_phase_count':4,'surface_atlases':[f'paving_47_phase_{p}.png' for p in range(4)],'surface_pattern':'surface/pattern_96.png','interior_phases':[f'surface/phase_{p}.png' for p in range(4)],'texture_phase_rule':rec['pattern']['phase_rule'],'columns':8,'rows':6,'unused_slot':47,'coverage':'coverage_47.png','neighbor_bits':BITS,'neighbor_offsets':{k:list(v) for k,v in OFFSETS.items()},'diagonal_rule':'Count a diagonal only when both adjoining cardinal neighbors connect.','lookup_256':[masks.index(normalize(i)) for i in range(256)],'tiles':entries,'contact_atlases':{n:f'contact_{n}_47.png' for n in trims},'contact_rule':rec['edge_finish']['mixed_junction_rule'],'moss_accents':[f'accents/moss_{i}.png' for i in range(4)],'moss_mortar_mask':'surface/mortar_mask.png','moss_placement':rec['moss']['placement'],'layer_order':['grass/dirt substrate','substrate-clipped contact trim','phase-correct stone body','optional mortar-clipped moss','sorted objects'],'palette':'palette.json','recipe':'assets/source/terrain/eldenmere/stone_paving_hd/recipe.json','path_conventions':{'assets':'pack_relative','recipe':'repository_relative'},'animation':None}
    document(PACK+'/tileset.json',metadata);document(PACK+'/palette.json',{'materials':rec['palette'],'sources':rec['palette_sources']})
    document(REVIEW+'/exports.json',{'builder':rec['builder'],'sources':rec['sources'],'recipe_sha256':sha256((SOURCE/'recipe.json').read_bytes()).hexdigest(),'integration_status':'not_integrated','outputs':records})
    return out

def build(check=False):
    result=products();stale=[]
    for name,raw in result.items():
        path=ROOT/name
        if not path.exists() or path.read_bytes()!=raw:
            stale.append(name)
            if not check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    if check and stale:raise SystemExit('Stale stone paving exports: '+', '.join(stale))
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args();print(f'{len(build(args.check))} stone paving exports '+('verified' if args.check else 'built'))
