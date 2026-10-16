"""Seam-constrained 47-mask terrain using the approved meadow sheet textures."""
from pathlib import Path
import json
from PIL import Image
from engine.grassland_autotile import CANONICAL_MASKS, OFFSETS, BITS

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"assets/source/terrain/grassland/blob47_source.png"
ATLAS=ROOT/"assets/atlases/terrain/grassland_blob47.png"
MANIFEST=ROOT/"assets/manifests/assets.json"
EDGES=(0,156,313,470,627,784,941,1098,1254)
DIRECTIONS=tuple((BITS[k],*delta) for k,delta in OFFSETS.items())

def source_tile(image,index):
    row,col=divmod(index,8)
    return image.crop((EDGES[col]+5,EDGES[row]+5,EDGES[col+1]-5,EDGES[row+1]-5)).resize((32,32),Image.Resampling.NEAREST)

def hash_pixel(x,y,salt=0):
    n=(x*374761393+y*668265263+salt*1442695041)&0xffffffff
    n=((n^(n>>13))*1274126177)&0xffffffff
    return n^(n>>16)

def coverage(mask,x,y):
    occupied={(0,0):1.0}
    for bit,dx,dy in DIRECTIONS:
        occupied[(dx,dy)]=float(bool(mask&bit))
    # Edges are symmetric between adjacent cells, including four-way joints.
    if x in (0,31) and y in (0,31):
        dx=-1 if x==0 else 1
        dy=-1 if y==0 else 1
        return float(all(occupied[(ax,ay)] for ax,ay in
                         ((0,0),(dx,0),(0,dy),(dx,dy))))
    if x==0:return occupied[(-1,0)]
    if x==31:return occupied[(1,0)]
    if y==0:return occupied[(0,-1)]
    if y==31:return occupied[(0,1)]
    x=(x-15.5)/31
    y=(y-15.5)/31
    ix=-1 if x<0 else 0
    iy=-1 if y<0 else 0
    ax=x-ix
    ay=y-iy
    value=sum(occupied[(ix+dx,iy+dy)]*(ax if dx else 1-ax)*(ay if dy else 1-ay)
              for dy in (0,1) for dx in (0,1))
    jitter=((hash_pixel(int(x*31+15.5),int(y*31+15.5),271)&255)/255-0.5)*0.12
    return float(value+jitter>=0.64)

def texel(texture,x,y):
    return texture.getpixel((0 if x==31 else x,0 if y==31 else y))

def paint(grass,dirt,mask=None,variant=0):
    out=Image.new("RGBA",(32,32))
    for y in range(32):
        for x in range(32):
            dirt_here=coverage(mask,x,y) if mask is not None else bool(variant<0)
            pixel=texel(dirt if dirt_here else grass,x,y)
            if mask is None and 4<x<27 and 4<y<27 and abs(variant)>1 and hash_pixel(x,y,abs(variant)+503)%107==0:
                pixel=(min(pixel[0]+12,255),min(pixel[1]+12,255),min(pixel[2]+7,255),255)
            out.putpixel((x,y),pixel)
    return out

def build():
    image=Image.open(SOURCE).convert("RGBA")
    if image.size!=(1254,1254):
        raise ValueError(f"Expected 1254x1254 source, got {image.size}")
    grass,dirt=source_tile(image,0),source_tile(image,8)
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
        place(16+i,f"terrain.grassland.blob.mask_{mask:03d}",paint(grass,dirt,mask=mask))
    return atlas,specs

def save():
    atlas,specs=build()
    ATLAS.parent.mkdir(parents=True,exist_ok=True)
    atlas.save(ATLAS,optimize=False)
    doc=json.loads(MANIFEST.read_text())
    doc["assets"].update(specs)
    MANIFEST.write_text(json.dumps(doc,indent=2)+"\n")
    return atlas,specs

if __name__=="__main__":
    image,entries=save()
    print(f"Produced {len(entries)} native sprites including 47 canonical masks")
