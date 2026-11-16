"""Export staged 2× retaining walls, south stairs and terrace material variants.

Fresh source drawings supply visible pixels. Retained logical alpha envelopes
preserve the existing wall modules' coverage; old color artwork is never reused.
Only new pack/review paths are written, without active-map or collision changes.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import statistics
import sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.build_eldenmere_grass_dirt_hd import rgba,tree_digest
SOURCE=ROOT/'assets/source/terrain/eldenmere/terraces_hd'
PACK='assets/terrain/eldenmere/terraces_hd';REVIEW='docs/reviews/eldenmere_hd_terraces'
GROUND=ROOT/'assets/terrain/eldenmere/grass_dirt_hd';PAVING=ROOT/'assets/terrain/eldenmere/stone_paving_hd'
STYLES=('maintained','weathered','mossy');SIZE=48

def load(path):
    with Image.open(path) as im:return im.convert('RGBA')
def read_recipe():return json.loads((SOURCE/'recipe.json').read_text())
def encoded(im):
    stream=BytesIO();im.save(stream,format='PNG',optimize=True);return stream.getvalue()
def quantize(im,rec):
    stone=[rgba(c) for c in rec['palette']['stone'].values()];green=[rgba(c) for c in rec['palette']['grass'].values()]
    medians=[statistics.median(im.getchannel(c).tobytes()) for c in ('R','G','B')];base=rgba(rec['palette']['stone']['base']);out=Image.new('RGBA',im.size);cache={}
    for y in range(im.height):
        for x in range(im.width):
            c=im.getpixel((x,y))
            if c[3]<128:continue
            if c not in cache:
                moss=c[1]>c[0]+4 and c[1]>c[2]+8
                calibrated=c[:3] if moss else [base[i]+(c[i]-medians[i])*rec['color_registration']['contrast'] for i in range(3)]
                cache[c]=min(green if moss else stone,key=lambda v:sum((v[i]-calibrated[i])**2 for i in range(3)))
            out.putpixel((x,y),cache[c])
    return out

def shade(im,rec):
    ramp=list(rec['palette']['stone'].values());mapping={rgba(c):rgba(ramp[max(0,i-1)]) for i,c in enumerate(ramp)};out=im.copy()
    for y in range(im.height):
        for x in range(im.width):
            c=im.getpixel((x,y));out.putpixel((x,y),mapping.get(c,c))
    return out

def material_faces(rec):
    raw=load(SOURCE/'walls_authored.png');faces={}
    for record in rec['wall_variants']:
        strip=quantize(raw.crop(record['source_rect']).resize((144,48),Image.Resampling.NEAREST),rec)
        for i in range(3):
            cell=strip.crop((i*48,0,(i+1)*48,48));im=Image.new('RGBA',(48,48))
            im.alpha_composite(cell.crop((0,0,48,7)).resize((48,10),Image.Resampling.NEAREST))
            im.alpha_composite(cell.crop((0,7,48,48)).resize((48,38),Image.Resampling.NEAREST),(0,10));faces[record['id'],i]=im
    return faces

def modules(rec,faces):
    masks={r['id']:Image.open(SOURCE/r['file']).convert('L').resize((48,48),Image.Resampling.NEAREST) for r in rec['logical_envelopes']}
    reference=faces['maintained',0];cap=reference.crop((0,0,48,10));front_port=reference.crop((0,0,1,48));result={}
    for style in STYLES:
        tiles={}
        for i in range(3):
            im=faces[style,i].copy();im.paste(cap,(0,0));im.paste(front_port,(0,0));im.paste(front_port,(47,0));tiles[f'wall_front_{i:02}']=im
        for side in ('left','right'):
            left=side=='left';x=0 if left else 40;column=tiles['wall_front_01'].crop((0 if left else 40,0,8 if left else 48,48))
            for kind in ('outer','inner','end'):
                im=tiles['wall_front_01' if kind!='end' else 'wall_front_02'].copy()
                if kind=='outer':im.paste(shade(column,rec),(x,0))
                elif kind=='inner':
                    turned=cap.transpose(Image.Transpose.ROTATE_90 if left else Image.Transpose.ROTATE_270)
                    im.paste(turned,(0 if left else 38,0))
                else:
                    edge=reference.crop((0 if left else 46,0,2 if left else 48,48));im.paste(edge,(0 if left else 46,0))
                # The continuing front port is distinct from the decorative return.
                im.paste(front_port,(47 if left else 0,0));tiles[f'wall_{kind}_{side}']=im
            side_im=Image.new('RGBA',(48,48));turned=cap.transpose(Image.Transpose.ROTATE_90 if left else Image.Transpose.ROTATE_270)
            side_im.alpha_composite(turned,(0 if left else 38,0))
            return_strip=tiles['wall_front_02'].crop((0,0,2,48));side_im.alpha_composite(shade(return_strip,rec),(10 if left else 36,0))
            tiles[f'wall_side_{side}']=side_im
        back=Image.new('RGBA',(48,48));back.alpha_composite(cap);tiles['wall_back']=back
        for side in ('left','right'):
            im=tiles[f'wall_side_{side}'].copy();im.alpha_composite(back);tiles[f'wall_back_{side}']=im
        result[style]=tiles
    # Common ports across styles: no one-pixel slits when changing wear treatment.
    side_ports={s:result['maintained'][f'wall_side_{s}'].crop((0,16,48,17)) for s in ('left','right')}
    back_port=result['maintained']['wall_back'].crop((0,0,1,48))
    for style,tiles in result.items():
        for side in ('left','right'):
            im=tiles[f'wall_side_{side}'];im.paste(side_ports[side],(0,0));im.paste(side_ports[side],(0,47))
        im=tiles['wall_back'];im.paste(back_port,(0,0));im.paste(back_port,(47,0))
        for side in ('left','right'):
            im=tiles[f'wall_side_{side}'].copy();im.alpha_composite(tiles['wall_back']);im.paste(side_ports[side],(0,47))
            im.paste(back_port,(47 if side=='left' else 0,0));tiles[f'wall_back_{side}']=im
        for name,im in list(tiles.items()):
            im.putalpha(masks[name]);clean=Image.new('RGBA',(48,48));clean.alpha_composite(im);tiles[name]=clean
    return result,masks

def stairs(rec):
    source=load(SOURCE/'stairs_authored.png');out={};records=[]
    for r in rec['stair_variants']:
        im=quantize(source.crop(r['source_rect']).resize((96,96),Image.Resampling.NEAREST),rec);source_rows=[]
        for target in rec['stair_nosing_rows_artwork']:
            row=max(range(target-3,target+4),key=lambda y:sum(sum(im.getpixel((x,y))[:3]) for x in range(14,82)))
            source_rows.append(row);strip=im.crop((14,row,82,row+1));im.paste(strip,(14,target))
        out[r['id']]=im;records.append({'id':r['id'],'source_nosing_rows_artwork':source_rows,'nosing_rows_artwork':rec['stair_nosing_rows_artwork']})
    return out,records

def phase_at(x,y):return x%2+2*(y%2)
def floor_tile(surface,x,y,ground,paving):return (paving[phase_at(x,y)] if surface=='paving' else ground[surface][(x//3+y//3)%4]).copy()
def landing(im,surface,phase,upper,ground,paving):
    result=Image.new('RGBA',(96,48));x,y=phase%2,phase//2
    for col in range(2):result.alpha_composite(floor_tile(surface,x+col,y,ground,paving),(col*48,0))
    band=im.crop((0,0,96,6) if upper else (0,90,96,96)).transpose(Image.Transpose.FLIP_TOP_BOTTOM);result.paste(band,(0,42 if upper else 0));return result

def products():
    rec=read_recipe();out={};exports=[]
    for r in rec['sources']+rec['logical_envelopes']:
        if sha256((SOURCE/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Terrace source changed: '+r['file'])
    def export(name,im):
        raw=encoded(im);out[name]=raw;exports.append({'file':name,'artwork_size':list(im.size),'sha256':sha256(raw).hexdigest()})
    def document(name,data):out[name]=(json.dumps(data,indent=2,ensure_ascii=False)+'\n').encode()
    faces=material_faces(rec);walls,masks=modules(rec,faces);steps,step_records=stairs(rec)
    wall_records=[]
    for style in STYLES:
        atlas=Image.new('RGBA',(48*7,48*2))
        for i,(name,im) in enumerate(walls[style].items()):
            path=f'modules/{style}/{name}.png';export(PACK+'/'+path,im);atlas.alpha_composite(im,(i%7*48,i//7*48))
            ports={}
            if name.startswith('wall_front_'):ports={'W':'front','E':'front'}
            elif any(name.startswith('wall_'+k+'_') for k in ('outer','inner','end')):ports={'E' if name.endswith('left') else 'W':'front'}
            elif name.startswith('wall_side_'):ports={'N':'side_'+name.rsplit('_',1)[1],'S':'side_'+name.rsplit('_',1)[1]}
            elif name=='wall_back':ports={'W':'back','E':'back'}
            else:ports={'E' if name.endswith('left') else 'W':'back','S':'side_'+name.rsplit('_',1)[1]}
            wall_records.append({'id':style+'.'+name,'style':style,'module':name,'file':path,'atlas':'atlases/'+style+'.png','rect':[i%7*48,i//7*48,48,48],'logical_size':[24,24],'draw_anchor_logical':[12,24],'height_logical':24,'ports':ports,'logical_coverage_source':next(r['file'] for r in rec['logical_envelopes'] if r['id']==name)})
        export(PACK+'/atlases/'+style+'.png',atlas)
    for s in step_records:
        name=s['id'];im=steps[name];export(PACK+'/stairs/'+name+'.png',im);s.update(file='stairs/'+name+'.png',logical_size=[48,48],artwork_size=[96,96],elevation_change_logical=24,walkable_rect_logical=[7,0,34,48],tread_count=4,upper_landing='N',lower_landing='S',draw_anchor_logical=[24,48])
        s['quarters']=[]
        for row in range(2):
            for col in range(2):
                path=f'stairs/{name}/quarter_{col}_{row}.png';export(PACK+'/'+path,im.crop((col*48,row*48,(col+1)*48,(row+1)*48)));s['quarters'].append(path)
    gm=json.loads((GROUND/'tileset.json').read_text());ground={n:[load(GROUND/p) for p in gm['materials'][n]] for n in ('grass','dirt')};pm=json.loads((PAVING/'tileset.json').read_text());paving=[load(PAVING/p) for p in pm['interior_phases']]
    landings={};landing_records=[]
    for name,im in steps.items():
        for surface in ('grass','dirt','paving'):
            for phase in (range(4) if surface=='paving' else (0,)):
                for end in ('upper','lower'):
                    result=landing(im,surface,phase,end=='upper',ground,paving);path=f'landings/{name}/{surface}_{end}_phase_{phase}.png';export(PACK+'/'+path,result);landings[name,surface,phase,end]=result
                    landing_records.append({'file':path,'stair_variant':name,'surface':surface,'end':end,'texture_phase':phase,'logical_size':[48,24],'floor_phase_rule':'Paving uses a common world origin; phase is x%2+2*(y%2). Regenerate floor portion for other origins.','connection_edge':'S' if end=='upper' else 'N'})
    prefab_records=[];prefabs={}
    for style in STYLES:
        for surface in ('grass','dirt','paving'):
            im=Image.new('RGBA',(288,288));tiles=[]
            for y in range(3):
                for x in range(6):im.alpha_composite(floor_tile(surface,x,y,ground,paving),(x*48,y*48))
            def place(name,x,y):im.alpha_composite(walls[style][name],(x*48,y*48));tiles.append({'module':name,'position_artwork':[x*48,y*48]})
            for x in range(1,5):place('wall_back',x,0)
            place('wall_back_left',0,0);place('wall_back_right',5,0)
            for y in (1,2):place('wall_side_left',0,y);place('wall_side_right',5,y)
            for x in (0,1,4,5):place('wall_outer_left' if x==0 else 'wall_outer_right' if x==5 else 'wall_front_'+str(x%3).zfill(2),x,3)
            im.alpha_composite(steps[style],(96,144));im.alpha_composite(landings[style,surface,0,'upper'],(96,96));lower_phase=2 if surface=='paving' else 0;im.alpha_composite(landings[style,surface,lower_phase,'lower'],(96,240))
            path=f'prefabs/{style}_{surface}.png';export(PACK+'/'+path,im);prefabs[style,surface]=im
            prefab_records.append({'id':style+'_'+surface,'file':path,'wall_style':style,'top_surface':surface,'logical_size':[144,144],'artwork_size':[288,288],'upper_elevation_logical':24,'lower_elevation_logical':0,'top_rect_logical':[0,0,144,72],'stair_variant':style,'stair_rect_logical':[48,72,48,48],'upper_landing_rect_logical':[48,48,48,24],'lower_landing_rect_logical':[48,120,48,24],'floor_origin_tiles':[0,0],'wall_instances':tiles,'draw_anchor_logical':[72,144],'collision':'Not inferred from alpha; use declared landings and stair clearance during future integration.'})
    # Labelled, offline asset reviews; not actual playable-map captures.
    from PIL import ImageDraw
    board=Image.new('RGB',(7*150,3*2*175+35),'#e8e9df');draw=ImageDraw.Draw(board);draw.text((10,8),'Eldenmere / NEW 2x walls / 3 styles / NOT INTEGRATED',fill='#243529')
    for row,style in enumerate(STYLES):
        for i,(name,im) in enumerate(walls[style].items()):
            x=i%7*150+3;y=(row*2+i//7)*175+30;background=ground['grass'][0].copy();background.alpha_composite(im);board.paste(background.convert('RGB').resize((144,144),Image.Resampling.NEAREST),(x,y));draw.text((x,y+146),style+' / '+name.removeprefix('wall_'),fill='#243529')
    export(REVIEW+'/wall_variants.png',board)
    board=Image.new('RGB',(4*218,242),'#e8e9df');draw=ImageDraw.Draw(board)
    for i,(name,im) in enumerate(steps.items()):board.paste(im.convert('RGB').resize((192,192),Image.Resampling.NEAREST),(i*218+10,10));draw.text((i*218+10,208),name+' / 4 treads',fill='#243529')
    export(REVIEW+'/stair_variants.png',board)
    board=Image.new('RGB',(3*312,3*318),'#2c7c50');draw=ImageDraw.Draw(board)
    for row,style in enumerate(STYLES):
        for col,surface in enumerate(('grass','dirt','paving')):x=col*312+12;y=row*318+24;im=prefabs[style,surface];board.paste(im,(x,y),im);draw.text((x,y-16),style+' / '+surface,fill='white')
    export(REVIEW+'/terrace_variants.png',board)
    scene=Image.new('RGBA',(960,768));placements=[];refs=[]
    for y in range(16):
        for x in range(20):scene.alpha_composite(floor_tile('grass',x,y,ground,paving),(x*48,y*48))
    for i,(style,surface) in enumerate(zip(STYLES,('grass','dirt','paving'))):
        x=16+i*320;y=180;im=prefabs[style,surface];scene.alpha_composite(im,(x,y));placements.append({'prefab':style+'_'+surface,'position_artwork':[x,y]})
        for path,foot,anchor in [('assets/characters/caelan/review_hd/idles/idle_front.png',(x+160,y+90),(24,60)),('assets/characters/iselin/idle_front_42x72.png',(x+144,y+272),(21,60))]:
            actor=load(ROOT/path);point=(foot[0]-anchor[0],foot[1]-anchor[1]);scene.alpha_composite(actor,point);refs.append({'file':path,'position_artwork':list(point),'artwork_pixels_per_world_pixel':2,'role':'Unchanged approved character scale reference, repeated across independent examples.'})
    export(REVIEW+'/scale_scene_native.png',scene)
    export(REVIEW+'/scale_closeup.png',scene.crop((320,150,640,510)).resize((640,720),Image.Resampling.NEAREST))
    document(REVIEW+'/layout.json',{'presentation':'Offline illustrative asset composition, not a gameplay capture or live map integration.','artwork_size':[960,768],'prefabs':placements,'references':refs})
    meta={'version':1,'id':rec['id'],'artwork_state':'rebuilt','integration_status':'not_integrated','visual_approval':rec['visual_approval'],'artwork_pixels_per_world_pixel':2,'logical_tile_size':[24,24],'artwork_tile_size':[48,48],'rect_space':'artwork','anchor_space':'logical','height_space':'logical','wall_height_logical':24,'wall_styles':list(STYLES),'wall_modules':wall_records,'stair_variants':step_records,'landings':landing_records,'terrace_prefabs':prefab_records,'path_conventions':{'asset_files':'pack_relative','recipe':'repository_relative'},'palette':'palette.json','recipe':'assets/source/terrain/eldenmere/terraces_hd/recipe.json','activation':'No runtime selector/map registration. Integrate separately with existing geometry and actual-game checks.','animation':None}
    document(PACK+'/tileset.json',meta);document(PACK+'/palette.json',{'materials':rec['palette'],'sources':['assets/terrain/eldenmere/terraces/palette.json','assets/terrain/eldenmere/grass_dirt_hd/palette.json']})
    document(REVIEW+'/exports.json',{'builder':rec['builder'],'sources':rec['sources'],'recipe_sha256':sha256((SOURCE/'recipe.json').read_bytes()).hexdigest(),'integration_status':'not_integrated','outputs':exports})
    return out

def build(check=False):
    result=products();stale=[]
    for name,raw in result.items():
        path=ROOT/name
        if not path.exists() or path.read_bytes()!=raw:
            stale.append(name)
            if not check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    if check and stale:raise SystemExit('Stale HD terrace exports: '+', '.join(stale))
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args();print(f'{len(build(args.check))} HD terrace exports '+('verified' if args.check else 'built'))
