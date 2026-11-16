"""Export staged 2× Eldenmere grass/dirt art; never modify playable terrain.

Fresh retained drawings supply material pixels and the edge profile study.
Technical processing samples named palette ramps, registers common seams,
assembles oriented quarter pieces and writes the 47 canonical neighborhoods.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
from io import BytesIO
import json
import statistics
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/grass_dirt_hd'
OUTPUT='assets/terrain/eldenmere/grass_dirt_hd'
REVIEW='docs/reviews/eldenmere_hd_blob'
SIZE=48;HALF=24
BITS={'N':1,'NE':2,'E':4,'SE':8,'S':16,'SW':32,'W':64,'NW':128}
OFFSETS={'N':(0,-1),'NE':(1,-1),'E':(1,0),'SE':(1,1),'S':(0,1),'SW':(-1,1),'W':(-1,0),'NW':(-1,-1)}
QUARTERS={'nw':(0,0,'W','N','NW'),'ne':(24,0,'E','N','NE'),'sw':(0,24,'W','S','SW'),'se':(24,24,'E','S','SE')}
STATES={'outer':(False,False,False),'edge_x':(False,True,False),'edge_y':(True,False,False),'inner':(True,True,False),'full':(True,True,True)}
def normalize(mask):
    for diagonal,a,b in (('NE','N','E'),('SE','E','S'),('SW','S','W'),('NW','W','N')):
        if not (mask&BITS[a] and mask&BITS[b]):mask &= ~BITS[diagonal]
    return mask

def state(h,v,d):return ('full' if d else 'inner') if h and v else 'edge_y' if h else 'edge_x' if v else 'outer'
def rgba(color):return (*bytes.fromhex(color.lstrip('#')),255)
def encoded(image):
    stream=BytesIO();image.save(stream,format='PNG',optimize=True);return stream.getvalue()
def tree_digest(folder):
    digest=sha256();files=sorted(p for p in folder.rglob('*') if p.is_file())
    for path in files:
        digest.update(path.relative_to(folder).as_posix().encode()+b'\0');digest.update(sha256(path.read_bytes()).digest())
    return {'file_count':len(files),'tree_sha256':digest.hexdigest()}
def recipe():return json.loads((SOURCE/'recipe.json').read_text())
def verify_inputs(rec):
    for source in rec['sources']:
        if sha256((SOURCE/source['file']).read_bytes()).hexdigest()!=source['sha256']:raise ValueError('Source changed: '+source['file'])

def material(cell,palette,base,border,contrast):
    """Uniform source sampling and exact color assignment; common 2px seam ports."""
    colors=[rgba(c) for c in palette.values()];cache={}
    im=cell.convert('RGB').resize((SIZE,SIZE),Image.Resampling.NEAREST);out=Image.new('RGBA',im.size)
    medians=[statistics.median(im.getchannel(c).tobytes()) for c in ('R','G','B')]
    target=rgba(base)
    for y in range(SIZE):
        for x in range(SIZE):
            pixel=im.getpixel((x,y))
            if pixel not in cache:
                corrected=tuple(target[i]+(pixel[i]-medians[i])*contrast for i in range(3))
                cache[pixel]=min(colors,key=lambda c:sum((c[i]-corrected[i])**2 for i in range(3)))
            out.putpixel((x,y),rgba(base) if min(x,y,SIZE-1-x,SIZE-1-y)<border else cache[pixel])
    return out

def inside(mask,x,y,rec):
    cells={(0,0):True};cells.update({offset:bool(mask&BITS[name]) for name,offset in OFFSETS.items()})
    cx,cy=x//SIZE,y//SIZE
    if not cells.get((cx,cy),False):return False
    xx,yy=x%SIZE,y%SIZE;qx=-1 if xx<HALF else 1;qy=-1 if yy<HALF else 1
    u=xx if qx==-1 else SIZE-1-xx;v=yy if qy==-1 else SIZE-1-yy
    kind=state(cells.get((cx+qx,cy),False),cells.get((cx,cy+qy),False),cells.get((cx+qx,cy+qy),False))
    profile=rec['edge_profile']
    if kind=='full':return True
    if kind=='inner':return u*u+v*v>=rec['inner_corner_radius']**2
    if kind=='edge_y':return v>=profile[u]
    if kind=='edge_x':return u>=profile[v]
    r=rec['outer_corner_radius'];center=profile[0]+r
    return u>=profile[v] and v>=profile[u] and (u>=center or v>=center or (u-center)**2+(v-center)**2<=r*r)

def quarter_images(texture,rec):
    result={}
    for orientation,(x0,y0,h,v,d) in QUARTERS.items():
        for kind,flags in STATES.items():
            mask=sum(BITS[name] for name,connected in zip((h,v,d),flags) if connected)
            image=Image.new('RGBA',(HALF,HALF))
            for yy in range(HALF):
                for xx in range(HALF):
                    x,y=x0+xx,y0+yy
                    if not inside(mask,x,y,rec):continue
                    pixel=texture.getpixel((x,y))
                    # A narrow soil lip registers the drawn material to the
                    # shared contour; no black tile border or random pixel noise.
                    if any(not inside(mask,x+dx,y+dy,rec) for dx,dy in ((-1,0),(1,0),(0,-1),(0,1))):pixel=rgba(rec['palette']['dirt']['edge'])
                    image.putpixel((xx,yy),pixel)
            result[orientation,kind]=image
    return result

def assemble(mask,parts):
    image=Image.new('RGBA',(SIZE,SIZE));names=[]
    for name,(x,y,h,v,d) in QUARTERS.items():
        kind=state(bool(mask&BITS[h]),bool(mask&BITS[v]),bool(mask&BITS[d]));image.alpha_composite(parts[name,kind],(x,y));names.append(name+'_'+kind)
    return image,names

def composition(grass,dirt):return Image.alpha_composite(grass,dirt).convert('RGB')

def products():
    rec=recipe();verify_inputs(rec);result={};records=[]
    def export(path,image):
        raw=encoded(image);result[path]=raw;records.append({'file':path,'artwork_size':list(image.size),'sha256':sha256(raw).hexdigest()})
    def document(path,value):result[path]=(json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode()
    source=Image.open(SOURCE/rec['material_source']).convert('RGB');materials=[]
    for i,(name,box) in enumerate(zip(rec['material_names'],rec['source_cells'])):
        ramp=rec['palette']['grass' if i<4 else 'dirt']
        materials.append(material(source.crop(box),ramp,ramp['base'],rec['seam_border_artwork_pixels'],rec['material_color_registration']['contrast']))
        export(OUTPUT+'/materials/'+name+'.png',materials[-1])
    grass=materials[:4];fills=materials[4:];parts=quarter_images(fills[0],rec)
    for (orientation,kind),image in parts.items():export(f'{OUTPUT}/quarters/{orientation}_{kind}.png',image)
    masks=sorted({normalize(m) for m in range(256)});tiles={};tile_records=[];atlas=Image.new('RGBA',(SIZE*8,SIZE*6));coverage=Image.new('RGBA',atlas.size)
    composite_atlas=Image.new('RGB',atlas.size,rec['palette']['grass']['base'])
    for i,mask in enumerate(masks):
        tile,names=assemble(mask,parts);tiles[mask]=tile;x=i%8*SIZE;y=i//8*SIZE;path=f'{OUTPUT}/dirt/mask_{mask:03}.png'
        export(path,tile);atlas.alpha_composite(tile,(x,y));composite_atlas.paste(composition(grass[0],tile),(x,y))
        alpha=Image.new('RGBA',tile.size,'white');alpha.putalpha(tile.getchannel('A'));coverage.alpha_composite(alpha,(x,y))
        tile_records.append({'index':i,'mask':mask,'file':path[len(OUTPUT)+1:],'rect':[x,y,SIZE,SIZE],'quarters':[f'quarters/{n}.png' for n in names]})
    export(OUTPUT+'/dirt_blob_47.png',atlas);export(OUTPUT+'/coverage_47.png',coverage)
    export(REVIEW+'/blob_on_grass_native.png',composite_atlas)
    board=Image.new('RGB',(8*154,6*174+44),'#e8e9df');draw=ImageDraw.Draw(board)
    draw.text((12,10),'Eldenmere / NEW 2x grass-dirt / 47 shapes / NOT INTEGRATED',fill='#243529')
    for i,mask in enumerate(masks):
        x=i%8*154+5;y=i//8*174+35;im=composition(grass[0],tiles[mask]).resize((144,144),Image.Resampling.NEAREST);board.paste(im,(x,y));draw.text((x,y+148),f'{i:02} / mask {mask:03}',fill='#243529')
    export(REVIEW+'/blob_47_review.png',board)
    materials_board=Image.new('RGB',(8*154,194),'#e8e9df');draw=ImageDraw.Draw(materials_board)
    for i,(name,im) in enumerate(zip(rec['material_names'],materials)):
        materials_board.paste(im.convert('RGB').resize((144,144),Image.Resampling.NEAREST),(i*154+5,8));draw.text((i*154+5,162),name,fill='#243529')
    export(REVIEW+'/materials_review.png',materials_board)
    # Deterministic stress layout: one/two-tile paths, bends, junction, enclosed
    # grass island, isolated dirt, diagonally touching patches, and broad fill.
    width,height=20,16;dirt=set()
    def rect(a,b,c,d):dirt.update((x,y) for y in range(b,d) for x in range(a,c))
    rect(0,7,20,9);rect(3,1,5,15);rect(9,2,17,6);rect(9,2,11,9);rect(15,4,17,12);rect(9,10,17,14)
    rect(12,5,14,9)
    dirt.difference_update((x,y) for x in range(11,15) for y in range(11,13));dirt.update({(1,2),(7,12),(8,13),(18,2)})
    cells=[];scene=Image.new('RGB',(width*SIZE,height*SIZE));lawn=Image.new('RGB',scene.size)
    for y in range(height):
        row=[]
        for x in range(width):
            family=2 if x>12 and y>9 else 3 if x<3 and y<5 else (x//3+y//4)%2
            im=grass[family].copy();lawn.paste(im,(x*SIZE,y*SIZE));mask=None;fill=None
            if (x,y) in dirt:
                mask=normalize(sum(bit for name,bit in BITS.items() if (x+OFFSETS[name][0],y+OFFSETS[name][1]) in dirt))
                if mask==255:fill=(x//3+y//3)%len(fills);im=fills[fill].copy()
                else:im.alpha_composite(tiles[mask])
            scene.paste(im,(x*SIZE,y*SIZE));row.append({'grass':family,'mask':mask,'fill':fill})
        cells.append(row)
    export(REVIEW+'/layout_native.png',scene);export(REVIEW+'/repeated_grass_native.png',lawn)
    # Offline reference composition: existing cottage remains legacy art shown
    # at 2× sampling. Characters retain their native HD pixels and physical size.
    staged=scene.copy();refs=[]
    cottage_path='assets/terrain/eldenmere/cottage/closed.png';cottage=Image.open(ROOT/cottage_path).convert('RGBA');cottage=cottage.resize((cottage.width*2,cottage.height*2),Image.Resampling.NEAREST)
    staged.paste(cottage,(11*SIZE,0),cottage);refs.append({'file':cottage_path,'position_artwork':[11*SIZE,0],'density':1,'role':'unchanged existing building reference'})
    for path,ground,anchor in [('assets/characters/caelan/review_hd/idles/idle_front.png',(6*SIZE,8*SIZE),(24,60)),('assets/characters/iselin/idle_front_42x72.png',(8*SIZE,8*SIZE),(21,60))]:
        image=Image.open(ROOT/path).convert('RGBA');pos=(ground[0]-anchor[0],ground[1]-anchor[1]);staged.paste(image,pos,image);refs.append({'file':path,'position_artwork':list(pos),'density':2,'role':'unchanged approved scale reference'})
    export(REVIEW+'/scale_scene_native.png',staged)
    close=staged.crop((4*SIZE,5*SIZE,11*SIZE,10*SIZE)).resize((672,480),Image.Resampling.NEAREST);export(REVIEW+'/scale_closeup.png',close)
    document(REVIEW+'/layout.json',{'artwork_tile_size':[48,48],'logical_tile_size':[24,24],'size_tiles':[width,height],'cells':cells,'references':refs,'presentation':'Offline illustrative asset composition, not a playable map or runtime integration.'})
    metadata={'version':1,'id':rec['id'],'artwork_state':'rebuilt','integration_status':'not_integrated','visual_approval':rec['visual_approval'],'artwork_pixels_per_world_pixel':2,'logical_tile_size':[24,24],'artwork_tile_size':[48,48],'logical_quarter_size':[12,12],'artwork_quarter_size':[24,24],'rect_space':'artwork','anchor_space':'logical','image':'dirt_blob_47.png','count':47,'columns':8,'rows':6,'unused_slot':47,'spacing':0,'margin':0,'neighbor_bits':BITS,'neighbor_offsets':{k:list(v) for k,v in OFFSETS.items()},'diagonal_rule':'Diagonal counts only when both adjoining cardinal neighbors connect.','lookup_256':[masks.index(normalize(m)) for m in range(256)],'tiles':tile_records,'materials':{'grass':[f'materials/{n}.png' for n in rec['material_names'][:4]],'dirt':[f'materials/{n}.png' for n in rec['material_names'][4:]]},'layer_order':['opaque grass','dirt overlay or fully connected dirt fill','independent sorted objects'],'recipe':'assets/source/terrain/eldenmere/grass_dirt_hd/recipe.json','palette':'palette.json','path_conventions':{'image':'pack_relative','tile_files':'pack_relative','quarter_files':'pack_relative','material_files':'pack_relative','palette':'pack_relative','recipe':'repository_relative'},'animation':None}
    document(OUTPUT+'/tileset.json',metadata);document(OUTPUT+'/palette.json',{'artwork_state':'rebuilt','materials':rec['palette'],'sources':rec['palette_sources']})
    document(REVIEW+'/exports.json',{'builder':rec['builder'],'sources':rec['sources'],'recipe_sha256':sha256((SOURCE/'recipe.json').read_bytes()).hexdigest(),'integration_status':'not_integrated','outputs':records})
    return result

def build(check=False):
    output=products();stale=[]
    for name,raw in output.items():
        path=ROOT/name
        if not path.exists() or path.read_bytes()!=raw:
            stale.append(name)
            if not check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    if check and stale:raise SystemExit('Stale HD blob exports: '+', '.join(stale))
    return output
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args();print(f'{len(build(args.check))} HD blob exports '+('verified' if args.check else 'built'))
