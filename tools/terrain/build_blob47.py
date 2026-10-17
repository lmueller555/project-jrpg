"""Polished, deterministic, seam-constrained 47-mask grassland atlas.

Source colors and forms come from the approved meadow illustration. Every
sprite shares fixed boundary texels; texture variety is restricted to interiors.
Requires Pillow only.
"""
from pathlib import Path
import json
import math
from PIL import Image
from engine.grassland_autotile import CANONICAL_MASKS, OFFSETS, BITS

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"assets/source/terrain/grassland/blob47_source.png"
ATLAS=ROOT/"assets/atlases/terrain/grassland_blob47.png"
MANIFEST=ROOT/"assets/manifests/assets.json"
EDGES=(0,156,313,470,627,784,941,1098,1254)
DIRECTIONS=tuple((BITS[key],*delta) for key,delta in OFFSETS.items())

def source_tile(image,index):
    row,col=divmod(index,8)
    return image.crop((EDGES[col]+5,EDGES[row]+5,EDGES[col+1]-5,EDGES[row+1]-5)).resize((32,32),Image.Resampling.NEAREST)

def hash_pixel(*args):
    n=2166136261
    for value in args:
        n=((n ^ (int(value)&0xffffffff))*16777619)&0xffffffff
    n ^= n>>13
    n=(n*1274126177)&0xffffffff
    return n^(n>>16)

def smoothstep(a,b,v):
    t=max(0.0,min(1.0,(v-a)/(b-a)))
    return t*t*(3-2*t)

def material_pixel(sources,x,y,variant):
    # Identical texture at all four possible shared tile borders.
    wx=0 if x==31 else x
    wy=0 if y==31 else y
    a=sources[0].getpixel((wx,wy))
    b=sources[4 if len(sources)>4 else 0].getpixel((wx,wy))
    use_b=((wx//4+wy//4)%3==0)
    portion=0.5 if use_b else 0.28
    edge=tuple(round(a[k]*(1-portion)+b[k]*portion) for k in range(3))
    distance=min(x,y,31-x,31-y)
    fade=smoothstep(2.5,8.0,distance)
    gx=(wx+variant*7)%32
    gy=(wy+variant*11)%32
    first=sources[hash_pixel(gx//6,gy//6,variant)%len(sources)].getpixel((wx,wy))
    second=sources[hash_pixel(gx//3,gy//3,variant,19)%len(sources)].getpixel((wx,wy))
    blend=max(0.15,min(0.85,0.35+0.3*math.sin((gx+gy+variant*3)/9)+0.15*math.cos((gx-gy)/5)))
    interior=[first[k]*(1-blend)+second[k]*blend for k in range(3)]
    if distance>4 and hash_pixel(x,y,variant,55)%47==0:
        interior=[min(255,v+10) for v in interior]
    if distance>5 and hash_pixel(x,y,variant,83)%59==0:
        interior=[max(0,v-9) for v in interior]
    return tuple(max(0,min(255,round(edge[k]*(1-fade)+interior[k]*fade))) for k in range(3))+(255,)

def coverage(mask,x,y,variant=0):
    occupied={(0,0):1.0}
    for bit,dx,dy in DIRECTIONS:
        occupied[(dx,dy)]=float(bool(mask&bit))
    # Identical four-cell corner condition no matter which neighbor renders it.
    if x in (0,31) and y in (0,31):
        dx=-1 if x==0 else 1
        dy=-1 if y==0 else 1
        return float(all(occupied[(ax,ay)] for ax,ay in
                         ((0,0),(dx,0),(0,dy),(dx,dy))))
    if x==0:return occupied[(-1,0)]
    if x==31:return occupied[(1,0)]
    if y==0:return occupied[(0,-1)]
    if y==31:return occupied[(0,1)]
    fx=(x-15.5)/31
    fy=(y-15.5)/31
    ix=-1 if fx<0 else 0
    iy=-1 if fy<0 else 0
    ax=fx-ix
    ay=fy-iy
    value=sum(occupied[(ix+dx,iy+dy)]*(ax if dx else 1-ax)*(ay if dy else 1-ay)
              for dy in (0,1) for dx in (0,1))
    # Frayed organic edges, controlled and deterministic per mask.
    noise=((hash_pixel(x//3,y//3,mask,variant)&255)/255-0.5)*0.12
    noise+=((hash_pixel(x//5,y//5,mask,variant,17)&255)/255-0.5)*0.08
    band=max(0.0,1.0-abs(value-0.5)*2.0)
    return float(value+noise*band>=0.52)

def paint(grass_sources,dirt_sources,mask=None,variant=0):
    out=Image.new("RGBA",(32,32))
    for y in range(32):
        for x in range(32):
            dirt_here=coverage(mask,x,y,variant) if mask is not None else variant<0
            sources=dirt_sources if dirt_here else grass_sources
            c=material_pixel(sources,x,y,abs(variant))
            if mask is not None and 0<x<31 and 0<y<31:
                # Dark soil lip / slightly lifted grass at transitions.
                neighbors=[coverage(mask,x+dx,y+dy,variant) for dx,dy in ((-1,0),(1,0),(0,-1),(0,1))]
                if min(neighbors)!=max(neighbors):
                    adjustment=-7 if dirt_here else 5
                    c=tuple(max(0,min(255,v+adjustment)) for v in c[:3])+(255,)
            out.putpixel((x,y),c)
    return out

def build():
    image=Image.open(SOURCE).convert("RGBA")
    if image.size!=(1254,1254):
        raise ValueError(f"Expected 1254x1254 source, got {image.size}")
    grass=[source_tile(image,i) for i in range(8)]
    dirt=[source_tile(image,8+i) for i in range(8)]
    atlas=Image.new("RGBA",(256,256),(0,0,0,0))
    specs={}
    def place(index,key,tile):
        x,y=(index%8)*32,(index//8)*32
        atlas.paste(tile,(x,y))
        specs[key]={"atlas":"atlases/terrain/grassland_blob47.png",
                    "rect":[x,y,32,32],"anchor":[0,0],"layer":"ground"}
    for i in range(8):
        place(i,f"terrain.grassland.blob.grass_{i+1:02d}",paint(grass,dirt,variant=i+1))
        place(8+i,f"terrain.grassland.blob.dirt_{i+1:02d}",paint(grass,dirt,variant=-(i+1)))
    for i,mask in enumerate(CANONICAL_MASKS):
        place(16+i,f"terrain.grassland.blob.mask_{mask:03d}",paint(grass,dirt,mask=mask,variant=i%4))
    return atlas,specs

def save():
    atlas,specs=build()
    ATLAS.parent.mkdir(parents=True,exist_ok=True)
    atlas.save(ATLAS,optimize=False)
    doc=json.loads(MANIFEST.read_text())
    # IDs and semantic rectangles remain unchanged.
    for key,spec in specs.items():
        if key in doc["assets"] and doc["assets"][key] != spec:
            raise ValueError(f"Unexpected changed semantic registration: {key}")
    doc["assets"].update(specs)
    MANIFEST.write_text(json.dumps(doc,indent=2)+"\n")
    return atlas,specs

if __name__=="__main__":
    atlas,specs=save()
    print(f"Polished atlas: {len(specs)} sprites including 47 canonical masks")
