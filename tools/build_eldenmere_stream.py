"""Build six-frame 24px water, stationary 47-state banks and review scenes."""

import json
from pathlib import Path

from PIL import Image, ImageDraw

from build_eldenmere_terrain import BITS, OFFSETS, QUARTERS, inside, normalize_mask, state


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/source/terrain/eldenmere/stream"
OUTPUT = ROOT / "assets/terrain/eldenmere/stream"


def read_json(path):
    return json.loads(path.read_text())


def write_json(path,data):
    path.write_text(json.dumps(data,indent=2)+"\n")


def rgba(color):
    return (*bytes.fromhex(color[1:]),255)


def enlarged(image,scale):
    return image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST)


def save_loop(path,images,recipe):
    images[0].save(path,save_all=True,append_images=images[1:],duration=recipe["duration_ms"],
                   loop=0,disposal=2,optimize=False)


def export_surface(recipe):
    source = Image.open(SOURCE / recipe["source"]).convert("RGB")
    part_dir = SOURCE / "parts"
    part_dir.mkdir(parents=True,exist_ok=True)
    native = source.crop(recipe["base_crop"]).resize((24,24),Image.Resampling.NEAREST)
    brightness = sorted(sum(p)/3 for p in native.get_flattened_data())[288]
    water = recipe["palette"]["water"]
    base = Image.new("RGBA",(24,24),rgba(water["base"]))
    for y in range(2,22):
        for x in range(2,22):
            in_window = any(a<=x<a+w and b<=y<b+h for a,b,w,h in recipe["depth_windows"])
            if in_window and sum(native.getpixel((x,y)))/3 < brightness-15:
                base.putpixel((x,y),rgba(water["deep"]))
    base.save(part_dir / "surface_base.png")
    glyphs = []
    for index,crop in enumerate(recipe["glyph_crops"]):
        sample = source.crop(crop["rect"]).resize(tuple(crop["size"]),Image.Resampling.NEAREST)
        glyph = Image.new("RGBA",sample.size)
        for y in range(sample.height):
            for x in range(sample.width):
                if sum(sample.getpixel((x,y)))/3 >= recipe["glyph_luminance_threshold"]:
                    glyph.putpixel((x,y),(255,255,255,255))
        if glyph.getbbox() is None:
            raise ValueError(f"Source ripple {index} exported empty")
        glyph.save(part_dir / f"ripple_{index:02}.png")
        glyphs.append(glyph)
    variants = []
    (OUTPUT / "surface").mkdir(parents=True,exist_ok=True)
    strip = Image.new("RGBA",(144,48))
    for variant,instances in enumerate((recipe["ripple_instances"],recipe["alternate_ripple_instances"])):
        frames = []
        for phase in range(recipe["frame_count"]):
            frame = base.copy()
            for instance in instances:
                pose = recipe["ripple_phases"][(phase+instance["phase_offset"])%6]
                if pose["shade"] is None:
                    continue
                glyph = glyphs[instance["glyph"]]
                left,top = [a+b for a,b in zip(instance["position"],pose["offset"])]
                for y in range(glyph.height):
                    for x in range(glyph.width):
                        if glyph.getpixel((x,y))[3] and 2<=left+x<22 and 2<=top+y<22:
                            frame.putpixel((left+x,top+y),rgba(water[pose["shade"]]))
            frame.save(OUTPUT / "surface" / f"variant_{variant:02}_frame_{phase+1:02}.png")
            strip.paste(frame,(phase*24,variant*24))
            frames.append(frame)
        variants.append(frames)
    strip.save(OUTPUT / "water_surface.png")
    return variants


def render_bank_quarters(recipe,geometry,ground_palette):
    directory = SOURCE / "quarters"
    directory.mkdir(exist_ok=True)
    parts = {}
    states = {"outer":(False,False,False),"edge_x":(False,True,False),
              "edge_y":(True,False,False),"inner":(True,True,False),"full":(True,True,True)}
    for name,(x0,y0,h,v,d) in QUARTERS.items():
        for kind,flags in states.items():
            representative = sum(BITS[bit] for bit,connected in zip((h,v,d),flags) if connected)
            bank,water = Image.new("RGBA",(12,12)),Image.new("RGBA",(12,12))
            for yy in range(12):
                for xx in range(12):
                    x,y = x0+xx,y0+yy
                    if not inside(representative,x,y,geometry):
                        continue
                    distance = 4
                    for radius in range(1,4):
                        if any(not inside(representative,x+dx,y+dy,geometry)
                               for dx in range(-radius,radius+1) for dy in range(-radius,radius+1)):
                            distance = radius
                            break
                    if distance<=recipe["earth_width"]:
                        color = ground_palette["dirt"]["shadow"]
                        if distance==1:
                            color = ground_palette["dirt"]["edge"]
                            if (min(x,23-x)+min(y,23-y))%7==2:
                                color = ground_palette["grass"]["base"]
                        bank.putpixel((xx,yy),rgba(color))
                    else:
                        water.putpixel((xx,yy),(255,255,255,255))
                        if distance<=recipe["earth_width"]+recipe["shallow_width"]:
                            bank.putpixel((xx,yy),rgba(recipe["palette"]["water"]["shallow"]))
            bank.save(directory / f"{name}_{kind}_bank.png")
            water.save(directory / f"{name}_{kind}_water.png")
            parts[name,kind] = bank,water
    return parts


def assemble(mask,parts):
    bank,water = Image.new("RGBA",(24,24)),Image.new("RGBA",(24,24))
    files = []
    for name,(x,y,h,v,d) in QUARTERS.items():
        kind = state(bool(mask&BITS[h]),bool(mask&BITS[v]),bool(mask&BITS[d]))
        b,w = parts[name,kind]
        bank.paste(b,(x,y))
        water.paste(w,(x,y))
        files.append({"position":[x,y],"bank":f"../../../source/terrain/eldenmere/stream/quarters/{name}_{kind}_bank.png",
                      "water":f"../../../source/terrain/eldenmere/stream/quarters/{name}_{kind}_water.png"})
    return bank,water,files


def composite_tile(surface,bank,mask):
    tile = Image.new("RGBA",surface.size)
    tile.paste(surface,(0,0),mask.getchannel("A"))
    return Image.alpha_composite(tile,bank)


def scene_cells():
    water = set()
    rows = {0:range(14,16),1:range(14,16),2:range(13,17),3:range(12,18),
            4:range(12,18),5:range(13,18),6:range(16,19),7:range(17,19),
            8:range(17,19),9:range(17,19),10:range(16,19),11:range(14,18),
            12:range(14,18),13:range(14,16),14:range(13,17),15:range(13,17)}
    for y,xs in rows.items():
        water.update((x,y) for x in xs)
    water.update(((18,3),(18,2),(19,2)))
    return water


def surface_variant(x,y):
    return int((x*7+y*11+x*y%5)%3==0)


def scene_reviews(recipe,ground_pack,ground_meta,tiles):
    old = read_json(ground_pack / "review_scene.json")
    width,height = old["grid_size"]
    wet = scene_cells()
    dry = {(x,y) for y,row in enumerate(old["dirt_masks"]) for x,mask in enumerate(row) if mask is not None}-wet
    grass = [Image.open(ground_pack / p).convert("RGBA") for p in ground_meta["grass"]["images"]]
    dirt = {t["mask"]:Image.open(ground_pack/t["image"]).convert("RGBA") for t in ground_meta["tiles"]}
    fills = [Image.open(ground_pack / p).convert("RGBA") for p in ground_meta["dirt_interiors"]["images"]]
    ground = Image.new("RGBA",(width*24,height*24))
    water_rows,dirt_rows,fill_rows = [],[],[]
    for y in range(height):
        water_row,dirt_row,fill_row = [],[],[]
        for x in range(width):
            ground.paste(grass[old["grass_variants"][y][x]],(x*24,y*24))
            water_mask,dirt_mask,fill = None,None,None
            if (x,y) in dry:
                raw = sum(BITS[n] for n,(dx,dy) in OFFSETS.items() if (x+dx,y+dy) in dry)
                dirt_mask = normalize_mask(raw)
                if dirt_mask==255:
                    fill = old["dirt_fill_variants"][y][x]
                    if fill is None:
                        fill = (x+y)%3
                overlay = fills[fill] if fill is not None else dirt[dirt_mask]
                ground.alpha_composite(overlay,(x*24,y*24))
            if (x,y) in wet:
                raw = sum(BITS[n] for n,(dx,dy) in OFFSETS.items() if (x+dx,y+dy) in wet)
                water_mask = normalize_mask(raw)
            water_row.append(water_mask)
            dirt_row.append(dirt_mask)
            fill_row.append(fill)
        water_rows.append(water_row)
        dirt_rows.append(dirt_row)
        fill_rows.append(fill_row)
    characters = old["characters"]
    moves = {"male_03":(11,4),"female_03":(12,12)}
    for character in characters:
        if character["name"] in moves:
            x,y = moves[character["name"]]
            character["foot"] = [x*24+12,y*24+20]
            character["position"] = [x*24,y*24-14]
    characters.sort(key=lambda c:c["foot"][1])
    native_frames,previews = [],[]
    for phase in range(6):
        image = ground.copy()
        for y,row in enumerate(water_rows):
            for x,mask in enumerate(row):
                if mask is not None:
                    image.alpha_composite(tiles[surface_variant(x,y)][phase][mask],(x*24,y*24))
        for character in characters:
            sprite = Image.open(ROOT / character["image_from_repo_root"]).convert("RGBA")
            image.alpha_composite(sprite,tuple(character["position"]))
        native = image.convert("RGB")
        native.save(OUTPUT / f"review_scene_frame_{phase+1:02}.png")
        native_frames.append(native)
        previews.append(enlarged(native,recipe["scene_scale"]))
    previews[0].save(OUTPUT / "review_scene.png")
    save_loop(OUTPUT / "review_scene.gif",previews,recipe)
    write_json(OUTPUT / "review_scene.json",{
        "status":recipe["status"],"purpose":"Animated art review; not a canonical Eldenmere map or playable scene",
        "grid_size":[width,height],"tile_size":[24,24],"ground_pack":"../grass_dirt/tileset.json",
        "grass_variants":old["grass_variants"],"dirt_masks":dirt_rows,"dirt_fill_variants":fill_rows,
        "water_masks":water_rows,"characters":characters,"shared_water_phase":True,
        "water_surface_variants":[[surface_variant(x,y) if (x,y) in wet else None for x in range(width)] for y in range(height)],
        "loop":True,"frames":[{"image":f"review_scene_frame_{i+1:02}.png","duration_ms":recipe["duration_ms"]} for i in range(6)],
        "review":{"image":"review_scene.png","gif":"review_scene.gif","scale":recipe["scene_scale"]},
    })
    # A three-by-three pool at 6x scale makes the fixed bank easy to inspect.
    pool = {(x,y) for y in range(1,4) for x in range(1,4)}
    closeups = []
    for phase in range(6):
        image = Image.new("RGBA",(120,120))
        for y in range(5):
            for x in range(5):
                image.paste(grass[0],(x*24,y*24))
                if (x,y) in pool:
                    mask = normalize_mask(sum(BITS[n] for n,(dx,dy) in OFFSETS.items() if (x+dx,y+dy) in pool))
                    image.alpha_composite(tiles[surface_variant(x,y)][phase][mask],(x*24,y*24))
        closeups.append(enlarged(image.convert("RGB"),recipe["closeup_scale"]))
    closeups[0].save(OUTPUT / "water_cycle_review.png")
    save_loop(OUTPUT / "water_cycle_review.gif",closeups,recipe)


def build():
    recipe = read_json(SOURCE / "recipe.json")
    geometry = read_json(SOURCE / recipe["geometry_recipe"])
    ground_pack = (SOURCE / recipe["ground_pack"]).resolve()
    ground_meta = read_json(ground_pack / "tileset.json")
    ground_palette = read_json(ground_pack / "palette.json")["materials"]
    OUTPUT.mkdir(parents=True,exist_ok=True)
    surfaces = export_surface(recipe)
    parts = render_bank_quarters(recipe,geometry,ground_palette)
    masks = sorted({normalize_mask(raw) for raw in range(256)})
    banks,water_masks,records = {},{},[]
    bank_atlas,mask_atlas = Image.new("RGBA",(192,144)),Image.new("RGBA",(192,144))
    for index,mask in enumerate(masks):
        bank,water,files = assemble(mask,parts)
        banks[mask],water_masks[mask] = bank,water
        position = (index%8*24,index//8*24)
        bank_atlas.paste(bank,position)
        mask_atlas.paste(water,position)
        records.append({"index":index,"mask":mask,"rect":[*position,24,24],"quarters":files})
    bank_atlas.save(OUTPUT / "banks_47.png")
    mask_atlas.save(OUTPUT / "water_masks_47.png")
    (OUTPUT / "water_47").mkdir(exist_ok=True)
    sheet = Image.new("RGBA",(192,864))
    tiles,frames = [[],[]],[]
    for phase,surface in enumerate(surfaces[0]):
        atlas = Image.new("RGBA",(192,144))
        phase_tiles = {}
        for record in records:
            mask = record["mask"]
            tile = composite_tile(surface,banks[mask],water_masks[mask])
            phase_tiles[mask] = tile
            atlas.paste(tile,tuple(record["rect"][:2]))
        filename = f"water_47/frame_{phase+1:02}.png"
        atlas.save(OUTPUT / filename)
        sheet.paste(atlas,(0,phase*144))
        tiles[0].append(phase_tiles)
        tiles[1].append({mask:composite_tile(surfaces[1][phase],banks[mask],water_masks[mask]) for mask in masks})
        frames.append({"image":filename,"sheet_rect":[0,phase*144,192,144],"duration_ms":recipe["duration_ms"]})
    sheet.save(OUTPUT / "water_blob_47.png")
    write_json(OUTPUT / "palette.json",{"status":recipe["status"],"materials":{**ground_palette,**recipe["palette"]}})
    write_json(OUTPUT / "tileset.json",{
        "id":recipe["id"],"status":recipe["status"],"design_plan":recipe["design_plan"],
        "tile_size":[24,24],"quarter_size":[12,12],"count":47,"columns":8,"spacing":0,"margin":0,
        "neighbor_bits":BITS,"neighbor_offsets":OFFSETS,"lookup_256":[masks.index(normalize_mask(raw)) for raw in range(256)],
        "diagonal_rule":ground_meta["diagonal_rule"],"tiles":records,"loop":True,"cycle_duration_ms":1200,
        "frames":frames,"image":"water_blob_47.png","banks":"banks_47.png","water_masks":"water_masks_47.png",
        "surface":{"image":"water_surface.png","variants":[
            {"index":v,"frames":[{"image":f"surface/variant_{v:02}_frame_{i+1:02}.png","duration_ms":recipe["duration_ms"]} for i in range(6)]}
            for v in range(2)],"composited_atlas_variant":0},
        "layer_order":["ground","masked_animated_water","stationary_bank_and_shallows","characters_or_props"],
        "synchronization":"One shared phase for all connected water tiles; offsets are baked into pixels",
        "palette":"palette.json","recipe":"../../../source/terrain/eldenmere/stream/recipe.json",
        "review":{"scene":"review_scene.gif","atlas":"bank_47_review.png","cycle":"water_cycle_review.gif"},
    })
    board = Image.new("RGB",(1344,1224),"#e8edf2")
    draw = ImageDraw.Draw(board)
    draw.text((16,12),f"Eldenmere stream / 47 stationary banks / six water phases / {recipe['status']}",fill="#243529",font_size=22)
    grass = Image.open(ground_pack / "grass_00.png").convert("RGBA")
    for index,mask in enumerate(masks):
        tile = Image.alpha_composite(grass,tiles[0][0][mask]).convert("RGB")
        x,y = index%8*168+12,index//8*196+48
        board.paste(enlarged(tile,6),(x,y))
        draw.text((x,y+150),f"{index:02} / mask {mask:03}",fill="#243529",font_size=16)
    board.save(OUTPUT / "bank_47_review.png")
    scene_reviews(recipe,ground_pack,ground_meta,tiles)
    print("Built Eldenmere stream: 47 stationary banks, six water phases, 282 composited tiles and animated scene")


if __name__ == "__main__":
    build()
