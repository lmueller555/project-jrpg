"""Export 24px grass/dirt materials, 47 blob tiles and a character-scale review."""

import json
import math
from pathlib import Path
from random import Random

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/source/terrain/eldenmere/grass_dirt"
OUTPUT = ROOT / "assets/terrain/eldenmere/grass_dirt"
SIZE = 24
BITS = {"N": 1, "NE": 2, "E": 4, "SE": 8, "S": 16, "SW": 32, "W": 64, "NW": 128}
OFFSETS = {"N": (0,-1), "NE": (1,-1), "E": (1,0), "SE": (1,1),
           "S": (0,1), "SW": (-1,1), "W": (-1,0), "NW": (-1,-1)}
QUARTERS = {"nw": (0,0,"W","N","NW"), "ne": (12,0,"E","N","NE"),
            "sw": (0,12,"W","S","SW"), "se": (12,12,"E","S","SE")}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2)+"\n")


def rgba(hex_color):
    return (*bytes.fromhex(hex_color[1:]), 255)


def normalize_mask(mask):
    for diagonal, a, b in (("NE","N","E"), ("SE","E","S"),
                           ("SW","S","W"), ("NW","W","N")):
        if not (mask & BITS[a] and mask & BITS[b]):
            mask &= ~BITS[diagonal]
    return mask


def state(horizontal, vertical, diagonal):
    if horizontal and vertical:
        return "full" if diagonal else "inner"
    if horizontal:
        return "edge_y"
    if vertical:
        return "edge_x"
    return "outer"


def inside(mask, x, y, recipe):
    """Evaluate a pixel, including a one-pixel halo for seamless edge shading."""
    cells = {(0,0): True}
    cells.update({offset: bool(mask & BITS[name]) for name, offset in OFFSETS.items()})
    cx, cy = x//SIZE, y//SIZE
    if not cells.get((cx,cy), False):
        return False
    local_x, local_y = x % SIZE, y % SIZE
    qx, qy = (-1 if local_x < 12 else 1), (-1 if local_y < 12 else 1)
    u = local_x if qx == -1 else 23-local_x
    v = local_y if qy == -1 else 23-local_y
    kind = state(cells.get((cx+qx,cy), False), cells.get((cx,cy+qy), False),
                 cells.get((cx+qx,cy+qy), False))
    profile = recipe["edge_profile"]
    if kind == "full":
        return True
    if kind == "inner":
        return u*u+v*v >= recipe["inner_corner_radius"]**2
    if kind == "edge_y":
        return v >= profile[u]
    if kind == "edge_x":
        return u >= profile[v]
    margin, radius = profile[0], recipe["outer_corner_radius"]
    center = margin+radius
    return (u >= margin and v >= margin and
            (u >= center or v >= center or (u-center)**2+(v-center)**2 <= radius*radius))


def export_material(source, crop, ramp, border, windows):
    native = source.crop(crop).convert("RGB").resize((SIZE,SIZE), Image.Resampling.NEAREST)
    colors = [rgba(c) for c in ramp.values()]
    pixels = []
    for y in range(SIZE):
        for x in range(SIZE):
            pixel = native.getpixel((x,y))
            color = min(colors, key=lambda c: sum((a-b)**2 for a,b in zip(c[:3],pixel)))
            keep_texture = any(x0 <= x < x0+w and y0 <= y < y0+h for x0,y0,w,h in windows)
            if min(x,y,23-x,23-y) < border or not keep_texture:
                color = rgba(ramp["base"])
            pixels.append(color)
    result = Image.new("RGBA", (SIZE,SIZE))
    result.putdata(pixels)
    return result


def render_quarters(texture, recipe):
    parts = {}
    directory = SOURCE / "quarters"
    directory.mkdir(parents=True, exist_ok=True)
    representatives = {"outer": (False,False,False), "edge_x": (False,True,False),
                       "edge_y": (True,False,False), "inner": (True,True,False),
                       "full": (True,True,True)}
    for name, (x0,y0,h,v,d) in QUARTERS.items():
        for kind, flags in representatives.items():
            mask = sum(BITS[bit] for bit, connected in zip((h,v,d),flags) if connected)
            part = Image.new("RGBA", (12,12))
            for yy in range(12):
                for xx in range(12):
                    x,y = x0+xx,y0+yy
                    if not inside(mask,x,y,recipe):
                        continue
                    color = texture.getpixel((x,y))
                    if any(not inside(mask,x+dx,y+dy,recipe) for dx,dy in ((-1,0),(1,0),(0,-1),(0,1))):
                        color = rgba(recipe["palette"]["dirt"]["edge"])
                        # A few grass-colored tips overlap the earthy lip.
                        if (min(x,23-x)+min(y,23-y)) % 7 == 2:
                            color = rgba(recipe["palette"]["grass"]["base"])
                    part.putpixel((xx,yy), color)
            part.save(directory / f"{name}_{kind}.png")
            parts[name,kind] = part
    return parts


def assemble_tile(mask, parts):
    tile = Image.new("RGBA", (SIZE,SIZE))
    files = []
    for name, (x,y,h,v,d) in QUARTERS.items():
        kind = state(bool(mask & BITS[h]), bool(mask & BITS[v]), bool(mask & BITS[d]))
        tile.paste(parts[name,kind], (x,y))
        files.append(f"../../../source/terrain/eldenmere/grass_dirt/quarters/{name}_{kind}.png")
    return tile, files


def enlarged(image, scale):
    return image.resize((image.width*scale,image.height*scale), Image.Resampling.NEAREST)


def composite(grass, overlay):
    return Image.alpha_composite(grass, overlay).convert("RGB")


def draw_reviews(grass, fills, tiles, masks, recipe):
    board = Image.new("RGB", (1344,1224), "#e8edf2")
    draw = ImageDraw.Draw(board)
    draw.text((16,12), f"Eldenmere - 24px dirt-on-grass / 47 blob tiles / {recipe['status']}", fill="#243529", font_size=24)
    for index, mask in enumerate(masks):
        col,row = index%8,index//8
        board.paste(enlarged(composite(grass[0],tiles[mask]),6), (col*168+12,row*196+48))
        draw.text((col*168+12,row*196+198), f"{index:02} / mask {mask:03}", fill="#243529", font_size=16)
    board.save(OUTPUT / "blob_47_review.png")
    materials = Image.new("RGB", (1152,400), "#e8edf2")
    draw = ImageDraw.Draw(materials)
    draw.text((16,12), f"Eldenmere / grass variations and dirt interiors / 24px / {recipe['status']}", fill="#243529", font_size=22)
    for col, image in enumerate(grass+fills):
        materials.paste(enlarged(image.convert("RGB"),6),(col*164+10,64))
        label = f"Grass {col+1}" if col<4 else f"Dirt fill {col-3}"
        draw.text((col*164+10,218),label,fill="#243529",font_size=18)
    draw.text((16,276), "Fresh greens / cool shadows / compacted stony earth",fill="#243529",font_size=20)
    draw.text((16,314), "47 shapes assemble from reusable 12x12 quarter pieces.",fill="#243529",font_size=20)
    draw.text((16,350), "Dirt overlays grass; transparent outside each shape.",fill="#243529",font_size=20)
    materials.save(OUTPUT / "materials_review.png")


def build_scene(grass, fills, tiles, recipe):
    width,height = 20,16
    dirt = set()
    def rect(x0,y0,x1,y1):
        dirt.update((x,y) for y in range(y0,y1) for x in range(x0,x1))
    rect(0,8,20,10)
    rect(8,0,10,15)
    rect(0,4,5,6)
    rect(3,4,5,10)
    rect(12,3,18,10)
    dirt.remove((14,5))
    dirt.update((15,y) for y in range(10,15))
    dirt.update((x,14) for x in range(15,18))
    dirt.update(((3,12),(4,13),(5,13),(18,1),(18,2)))
    rng = Random(47)
    grass_ids = [[rng.choices(range(4),weights=(5,3,2,1))[0] for x in range(width)] for y in range(height)]
    masks, interiors = [], []
    ground = Image.new("RGBA", (width*SIZE,height*SIZE))
    for y in range(height):
        mask_row,fill_row = [],[]
        for x in range(width):
            ground.paste(grass[grass_ids[y][x]],(x*SIZE,y*SIZE))
            mask,fill = None,None
            if (x,y) in dirt:
                raw = sum(BITS[name] for name,(dx,dy) in OFFSETS.items() if (x+dx,y+dy) in dirt)
                mask = normalize_mask(raw)
                fill = rng.randrange(len(fills)) if mask==255 else None
                overlay = fills[fill] if fill is not None else tiles[mask]
                ground.alpha_composite(overlay,(x*SIZE,y*SIZE))
            mask_row.append(mask)
            fill_row.append(fill)
        masks.append(mask_row)
        interiors.append(fill_row)
    ground.convert("RGB").save(OUTPUT / "review_scene_ground_native.png")
    scene = ground.copy()
    placements = [
        ("caelan", "assets/characters/caelan/idle_front.png",9,8),
        ("mira", "assets/characters/mira/idle_front.png",10,10),
        ("male_01", "assets/characters/npcs/male_01/idle_front.png",4,3),
        ("male_02", "assets/characters/npcs/male_02/idle_front.png",4,8),
        ("male_03", "assets/characters/npcs/male_03/idle_front.png",15,4),
        ("female_01", "assets/characters/npcs/female_01/idle_front.png",13,8),
        ("female_02", "assets/characters/npcs/female_02/idle_front.png",6,12),
        ("female_03", "assets/characters/npcs/female_03/idle_front.png",15,13),
    ]
    characters = []
    for name,path,x,y in sorted(placements,key=lambda p:p[3]):
        image = Image.open(ROOT/path).convert("RGBA")
        foot = [x*SIZE+12,y*SIZE+20]
        position = [foot[0]-12,foot[1]-34]
        scene.alpha_composite(image,tuple(position))
        characters.append({"name":name,"image_from_repo_root":path,"position":position,"foot":foot})
    scene = scene.convert("RGB")
    scene.save(OUTPUT / "review_scene_native.png")
    enlarged(scene,recipe["scene_scale"]).save(OUTPUT / "review_scene.png")
    write_json(OUTPUT / "review_scene.json", {
        "status":recipe["status"],"purpose":"Art review and scale/seam test; not a canonical Eldenmere map or playable scene",
        "tile_size":[24,24],"grid_size":[width,height],"grass_variants":grass_ids,
        "dirt_masks":masks,"dirt_fill_variants":interiors,"characters":characters,
        "native":"review_scene_native.png","ground":"review_scene_ground_native.png",
        "review":{"image":"review_scene.png","scale":recipe["scene_scale"]},
    })


def build():
    recipe = json.loads((SOURCE / "recipe.json").read_text())
    OUTPUT.mkdir(parents=True,exist_ok=True)
    (OUTPUT / "dirt").mkdir(exist_ok=True)
    source = Image.open(SOURCE / recipe["source"])
    grass = [export_material(source,crop,recipe["palette"]["grass"],recipe["texture_border"],windows)
             for crop,windows in zip(recipe["grass_crops"],recipe["grass_texture_windows"],strict=True)]
    dirt_ramp = {name:color for name,color in recipe["palette"]["dirt"].items() if name!="edge"}
    fills = [export_material(source,crop,dirt_ramp,recipe["texture_border"],windows)
             for crop,windows in zip(recipe["dirt_crops"],recipe["dirt_texture_windows"],strict=True)]
    for name,images in (("grass",grass),("dirt_fill",fills)):
        strip = Image.new("RGBA", (len(images)*SIZE,SIZE))
        for index,image in enumerate(images):
            image.save(OUTPUT / f"{name}_{index:02}.png")
            strip.paste(image,(index*SIZE,0))
        strip.save(OUTPUT / f"{name}.png")
    parts = render_quarters(fills[0],recipe)
    masks = sorted({normalize_mask(raw) for raw in range(256)})
    if len(masks) != 47:
        raise ValueError("Blob mask normalization must produce exactly 47 states")
    columns = recipe["atlas_columns"]
    atlas = Image.new("RGBA", (columns*SIZE,math.ceil(len(masks)/columns)*SIZE))
    tiles,records = {},[]
    for index,mask in enumerate(masks):
        tile,files = assemble_tile(mask,parts)
        tiles[mask] = tile
        filename = f"dirt/mask_{mask:03}.png"
        tile.save(OUTPUT / filename)
        x,y = index%columns*SIZE,index//columns*SIZE
        atlas.paste(tile,(x,y))
        records.append({"index":index,"mask":mask,"rect":[x,y,SIZE,SIZE],"image":filename,
                        "neighbors":[name for name,bit in BITS.items() if mask & bit],"quarters":files})
    atlas.save(OUTPUT / "dirt_blob_47.png")
    write_json(OUTPUT / "tileset.json", {
        "id":recipe["id"],"status":recipe["status"],"tile_size":[24,24],"quarter_size":[12,12],
        "image":"dirt_blob_47.png","columns":columns,"count":47,"spacing":0,"margin":0,
        "neighbor_bits":BITS,"neighbor_offsets":OFFSETS,
        "diagonal_rule":"Count a diagonal only when both adjoining cardinal neighbors connect",
        "lookup_256":[masks.index(normalize_mask(raw)) for raw in range(256)],"tiles":records,
        "grass":{"image":"grass.png","count":4,"images":[f"grass_{i:02}.png" for i in range(4)]},
        "dirt_interiors":{"image":"dirt_fill.png","count":3,"mask":255,
                          "images":[f"dirt_fill_{i:02}.png" for i in range(3)]},
        "layer_order":["grass","dirt_overlay","characters_or_props"],
        "palette":"palette.json","recipe":"../../../source/terrain/eldenmere/grass_dirt/recipe.json",
        "review":{"atlas":"blob_47_review.png","materials":"materials_review.png","scene":"review_scene.png"},
    })
    write_json(OUTPUT / "palette.json", {"status":recipe["status"],"materials":recipe["palette"]})
    draw_reviews(grass,fills,tiles,masks,recipe)
    build_scene(grass,fills,tiles,recipe)
    print("Built Eldenmere: 4 grass variations, 47 dirt blobs, 3 dirt interiors and native-scale character review")


if __name__ == "__main__":
    build()
