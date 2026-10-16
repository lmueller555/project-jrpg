"""Quantify source-slot edge mismatches; no automatic mask mapping is inferred.

Run: python -m tools.terrain.audit_grassland_seams
"""
from pathlib import Path
from PIL import Image
import json

ROOT=Path(__file__).resolve().parents[2]
ATLAS=ROOT/"assets/atlases/terrain/grassland_v1.png"
SIZE=32

def tile(atlas,slot):
    col,row=slot%8,slot//8
    return atlas.crop((col*SIZE,row*SIZE,(col+1)*SIZE,(row+1)*SIZE)).convert("RGB")

def edge_error(a,b,axis="horizontal"):
    if a.size!=(SIZE,SIZE) or b.size!=(SIZE,SIZE):
        raise ValueError("Only native 32x32 tile comparisons supported")
    if axis=="horizontal":
        aa=[a.getpixel((31,y)) for y in range(32)]
        bb=[b.getpixel((0,y)) for y in range(32)]
    elif axis=="vertical":
        aa=[a.getpixel((x,31)) for x in range(32)]
        bb=[b.getpixel((x,0)) for x in range(32)]
    else:
        raise ValueError("axis must be horizontal or vertical")
    return sum(abs(c-d) for p,q in zip(aa,bb) for c,d in zip(p,q))/(32*3)

def report():
    atlas=Image.open(ATLAS).convert("RGBA")
    if atlas.size != (256,256):
        raise ValueError(f"Expected 256x256 atlas, got {atlas.size}")
    cases=[("grass_variation_1_2",0,1,"horizontal"),
           ("grass_variation_1_5",0,4,"horizontal"),
           ("dirt_variation_1_2",8,9,"horizontal"),
           ("transition_slot_1_2",16,17,"horizontal"),
           ("transition_slot_9_10",24,25,"horizontal")]
    return {name:round(edge_error(tile(atlas,i),tile(atlas,j),axis),3)
            for name,i,j,axis in cases}

if __name__=="__main__":
    print(json.dumps(report(),indent=2))
    print("Numbers are RGB differences, not an artistic pass/fail; all mask adjacency permutations still need verification.")
