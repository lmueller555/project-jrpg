"""Build the three female NPC front-idle palettes and eye-color comparisons."""

from copy import deepcopy
from pathlib import Path
import json

from PIL import Image, ImageDraw

from build_npc_palette_variants import recolor, preview, write_json, rgba


ROOT = Path(__file__).resolve().parents[1]
NPCS = ROOT / "assets/characters/npcs"
SOURCE = ROOT / "assets/source/characters/npcs/female_01"


def read_json(path):
    return json.loads(path.read_text())


def main():
    config = read_json(SOURCE / "palette_variants.json")
    base = Image.open(SOURCE / config["source"]).convert("RGBA")
    palette = read_json(SOURCE / config["source_palette"])["materials"]
    base_meta = read_json(SOURCE / config["source_metadata"])
    layers = read_json(SOURCE / "export.json")["layers"]
    entries = [(config["base_label"], base_meta, base)]
    for variant in config["variants"]:
        number = variant["variant"]
        folder = NPCS / f"female_{number:02}"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "idle_front.json"
        status = read_json(path)["status"] if path.exists() else "draft"
        sprite = recolor(base, palette, variant, config)
        eyes = deepcopy(base_meta["eyes"])
        eyes.update({"iris_color": variant["iris_color"], "iris_name": variant["eye_name"]})
        for x, y in eyes["top_pixels"]:
            sprite.putpixel((x, y), rgba(eyes["pupil_color"]))
            sprite.putpixel((x, y+eyes["iris_offset_y"]), rgba(eyes["iris_color"]))
        sprite.save(folder / "idle_front.png")
        preview(sprite).save(folder / "idle_front_review.png")
        materials = deepcopy(palette)
        materials.update(variant["materials"])
        materials["eyes"]["iris"] = eyes["iris_color"]
        write_json(folder / "palette.json", {
            "status": status, "materials": materials, "source_palette": "../female_01/palette.json",
            "regions": config["material_regions"], "eye_feature": eyes,
        })
        metadata = deepcopy(base_meta)
        metadata.update({
            "character": variant["character"], "variant": number,
            "design_status": status, "status": status, "eyes": eyes,
            "source": "../female_01/idle_front.png",
            "recipe": "../../../source/characters/npcs/female_01/palette_variants.json",
        })
        metadata.pop("export_recipe", None)
        metadata["layers"] = []
        part_dir = ROOT / "assets/source/characters/npcs" / f"female_{number:02}" / "layers"
        part_dir.mkdir(parents=True, exist_ok=True)
        for name, definition in layers.items():
            y0, y1 = definition["rows"]
            layer = Image.new("RGBA", (24, 36))
            layer.paste(sprite.crop((0, y0, 24, y1)), (0, y0))
            layer.save(part_dir / f"{name}.png")
            metadata["layers"].append(f"../../../source/characters/npcs/female_{number:02}/layers/{name}.png")
        write_json(path, metadata)
        entries.append((variant["label"], metadata, sprite))

    sheet = Image.new("RGBA", (72, 36))
    board = Image.new("RGB", (1152, 708), "#e8edf2")
    eye_board = Image.new("RGB", (768, 240), "#e8edf2")
    draw, eye_draw = ImageDraw.Draw(board), ImageDraw.Draw(eye_board)
    records = []
    for col, (label, metadata, sprite) in enumerate(entries):
        sheet.paste(sprite, (col*24, 0))
        background = Image.new("RGB", (24, 36), "#e8edf2")
        background.paste(sprite, mask=sprite.getchannel("A"))
        board.paste(background.resize((384, 576), Image.Resampling.NEAREST), (col*384, 8))
        draw.text((col*384+16, 600), label, fill="#1a0e16", font_size=18)
        eye_label = metadata["eyes"]["iris_name"] + " eyes"
        draw.text((col*384+16, 630), eye_label, fill="#1a0e16", font_size=18)
        draw.text((col*384+16, 660), metadata["status"].capitalize(), fill="#455531", font_size=18)
        face = background.crop((8, 7, 16, 13)).resize((256, 192), Image.Resampling.NEAREST)
        eye_board.paste(face, (col*256, 8))
        eye_draw.text((col*256+24, 208), eye_label, fill="#1a0e16", font_size=20)
        records.append({"variant": col+1, "status": metadata["status"],
                        "rect": [col*24, 0, 24, 36], "metadata": f"female_{col+1:02}/idle_front.json",
                        "eyes": metadata["eyes"]})
    sheet.save(NPCS / "female_variants.png")
    board.save(NPCS / "female_variants_review.png")
    eye_board.save(NPCS / "female_eyes_review.png")
    write_json(NPCS / "female_variants.json", {
        "image": "female_variants.png", "frame_size": [24, 36], "foot_anchor": [12, 34],
        "variants": records, "review": {"image": "female_variants_review.png", "scale": 16,
                                           "eyes": "female_eyes_review.png", "eye_scale": 32},
    })


if __name__ == "__main__":
    main()
