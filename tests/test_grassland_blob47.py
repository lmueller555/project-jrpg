from tools.terrain.build_blob47 import build
from engine.grassland_autotile import CANONICAL_MASKS,canonical,OFFSETS,BITS
import random

def test_mask_atlas_count_and_coordinates():
    atlas,specs=build()
    assert atlas.size==(256,256)
    assert len(specs)==63 and len(CANONICAL_MASKS)==47
    for mask in CANONICAL_MASKS:
        assert f"terrain.grassland.blob.mask_{mask:03d}" in specs
    assert len({tuple(s["rect"]) for s in specs.values()})==63

def test_exhaustive_local_patterns_share_identical_edges():
    atlas,specs=build()
    def sprite(name):
        x,y,w,h=specs[name]["rect"]
        return atlas.crop((x,y,x+w,y+h))
    for repeat_seed in range(12):
        rng=random.Random(repeat_seed)
        tiles=[[rng.random()<0.52 for _ in range(12)] for _ in range(9)]
        result={}
        for y in range(9):
            for x in range(12):
                if not tiles[y][x]:
                    name="terrain.grassland.blob.grass_01"
                else:
                    mask=0
                    for direction,(dx,dy) in OFFSETS.items():
                        if 0<=x+dx<12 and 0<=y+dy<9 and tiles[y+dy][x+dx]:
                            mask|=BITS[direction]
                    name=f"terrain.grassland.blob.mask_{canonical(mask):03d}"
                result[x,y]=sprite(name)
        for y in range(9):
            for x in range(12):
                a=result[x,y]
                if x<11:
                    b=result[x+1,y]
                    assert all(a.getpixel((31,k))==b.getpixel((0,k)) for k in range(32)),(repeat_seed,x,y,'E')
                if y<8:
                    b=result[x,y+1]
                    assert all(a.getpixel((k,31))==b.getpixel((k,0)) for k in range(32)),(repeat_seed,x,y,'S')
