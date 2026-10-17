"""Pure semantic resolution of native 32px Eldenmere ground sprites.

Only g/p receive the new artwork; all other logical map tiles use the
existing rendering path. No changes to physical map, movement, or collision.
"""
from engine.grassland_autotile import dirt_mask

def ground_sprite_id(rows, x, y):
    if y<0 or y>=len(rows) or x<0 or x>=len(rows[y]):
        return None
    char=rows[y][x]
    variant=1+((x*17+y*31)&7)
    if char=="g":
        return f"terrain.grassland.blob.grass_{variant:02d}"
    if char=="p":
        mask=dirt_mask(rows,x,y)
        if mask==255:
            return f"terrain.grassland.blob.dirt_{variant:02d}"
        return f"terrain.grassland.blob.mask_{mask:03d}"
    return None
