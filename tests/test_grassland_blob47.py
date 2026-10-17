from tools.terrain.build_blob47 import build
from engine.grassland_autotile import CANONICAL_MASKS,canonical,OFFSETS,BITS
import random

def test_atlas_semantic_ids_and_size():
    atlas,specs=build()
    assert atlas.size==(256,256)
    assert atlas.mode=="RGBA"
    assert len(specs)==63 and len(CANONICAL_MASKS)==47
    assert len({tuple(v["rect"]) for v in specs.values()})==63
    assert all(f"terrain.grassland.blob.mask_{m:03d}" in specs for m in CANONICAL_MASKS)
    assert all(spec["rect"][2:]==[32,32] for spec in specs.values())

def test_24_randomized_compositions_have_identical_boundary_pixels():
    atlas,specs=build()
    sprites={}
    for key,spec in specs.items():
        x,y,w,h=spec["rect"]
        sprites[key]=atlas.crop((x,y,x+w,y+h))
    for trial in range(24):
        rng=random.Random(trial)
        terrain=[[rng.random()<0.52 for _ in range(12)] for _ in range(9)]
        selected={}
        for y in range(9):
            for x in range(12):
                if not terrain[y][x]:
                    key=f"terrain.grassland.blob.grass_{1+((x*17+y*31)&7):02d}"
                else:
                    mask=0
                    for direction,(dx,dy) in OFFSETS.items():
                        if 0<=x+dx<12 and 0<=y+dy<9 and terrain[y+dy][x+dx]:
                            mask |= BITS[direction]
                    mask=canonical(mask)
                    key=(f"terrain.grassland.blob.dirt_{1+((x*17+y*31)&7):02d}" if mask==255
                         else f"terrain.grassland.blob.mask_{mask:03d}")
                selected[x,y]=sprites[key]
        for y in range(9):
            for x in range(12):
                a=selected[x,y]
                if x<11:
                    b=selected[x+1,y]
                    assert all(a.getpixel((31,k))==b.getpixel((0,k)) for k in range(32)),(trial,x,y,"E")
                if y<8:
                    b=selected[x,y+1]
                    assert all(a.getpixel((k,31))==b.getpixel((k,0)) for k in range(32)),(trial,x,y,"S")
