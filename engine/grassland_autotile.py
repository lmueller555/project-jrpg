"""Canonical 47-mask neighborhood logic for grass/dirt autotiling.

The illustrated atlas uses source-slot IDs, not semantic mask IDs. A verified
art mapping must be supplied before rendering with this resolver.
"""
from __future__ import annotations

N,E,S,W,NE,SE,SW,NW=(1,2,4,8,16,32,64,128)
BITS={"N":N,"E":E,"S":S,"W":W,"NE":NE,"SE":SE,"SW":SW,"NW":NW}
OFFSETS={"N":(0,-1),"E":(1,0),"S":(0,1),"W":(-1,0),
         "NE":(1,-1),"SE":(1,1),"SW":(-1,1),"NW":(-1,-1)}
DIAGONALS={NE:(N,E),SE:(S,E),SW:(S,W),NW:(N,W)}

def canonical(mask:int)->int:
    if type(mask) is not int or not 0<=mask<=255:
        raise ValueError("mask must be an integer from 0 to 255")
    for bit,(a,b) in DIAGONALS.items():
        if not (mask&a and mask&b):
            mask &= ~bit
    return mask

CANONICAL_MASKS=tuple(sorted({canonical(x) for x in range(256)}))
assert len(CANONICAL_MASKS)==47

def dirt_mask(rows, x:int, y:int, dirt="p")->int:
    """8-neighbor mask around a dirt tile; off-map cells are not dirt."""
    if rows[y][x] != dirt:
        raise ValueError("mask is only defined for a dirt cell")
    height=len(rows)
    width=len(rows[0])
    mask=0
    for key,(dx,dy) in OFFSETS.items():
        nx,ny=x+dx,y+dy
        if 0<=ny<height and 0<=nx<width and rows[ny][nx]==dirt:
            mask|=BITS[key]
    return canonical(mask)

def mapped_asset_id(mask:int, mapping:dict[int,str]|None=None)->str:
    """Fail closed until all canonical masks have an art-verified assignment."""
    if mapping is None or set(mapping)!=set(CANONICAL_MASKS):
        raise ValueError("Unverified/incomplete canonical transition artwork mapping")
    mask=canonical(mask)
    return mapping[mask]
