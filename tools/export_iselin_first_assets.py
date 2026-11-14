"""Export Iselin's first two imagegen-authored assets without painting artwork.

Only crop, uniformly register, nearest-neighbor sample, and lay out reviews.
This tool does not register Iselin with the game or replace another character.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PORTRAIT = "assets/source/portraits/eldenmere/iselin_master.png"
SPRITE = "assets/source/characters/iselin/idle_front_master.png"
BASE = "assets/characters/iselin"
REVIEW = "docs/reviews/iselin_first_assets"
MATTE = "#e8edf2"
INK = "#263c35"


def encoded(image):
    stream = BytesIO()
    image.save(stream, format="PNG", optimize=True)
    return stream.getvalue()


def json_bytes(value):
    return (json.dumps(value, indent=2) + "\n").encode()


def digest(data):
    return sha256(data).hexdigest()


def font(size):
    return ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size
    )


def matte(image, scale=1):
    result = Image.new("RGBA", image.size, MATTE)
    result.alpha_composite(image.convert("RGBA"))
    return result.convert("RGB").resize(
        (image.width * scale, image.height * scale), Image.Resampling.NEAREST
    )


def register_sprite(master):
    source = master.convert("RGBA")
    alpha = source.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    source.putalpha(alpha)
    bounds = alpha.getbbox()
    if bounds is None:
        raise ValueError("Iselin's sprite source has no opaque artwork")
    crop = source.crop(bounds)
    scale = 34 / crop.height
    occupied_width = crop.width * scale
    if occupied_width > 22:
        raise ValueError(
            f"Iselin's source is too wide at native height: {occupied_width:.2f}px > 22px"
        )
    # Match the current authored Caelan exporter: one scale for the drawing,
    # with integer output dimensions rounded only at the native pixel boundary.
    # Fractional affine registration changes the sampling phase and can erase a
    # one-pixel eye; resize first, then translate the complete drawing.
    resized = crop.resize((round(occupied_width), 34), Image.Resampling.NEAREST)
    left, top = round(12 - resized.width / 2), 1
    native = Image.new("RGBA", (24, 36))
    native.alpha_composite(resized, (left, top))
    pixels = [native.getpixel((x, y)) for y in range(native.height) for x in range(native.width)]
    # Normalize fully transparent storage without mixing black into the palette.
    native.putdata([pixel if pixel[3] else (0, 0, 0, 0) for pixel in pixels])
    target = native.getchannel("A").getbbox()
    if target is None or target[0] < 1 or target[2] > 23 or target[1] != 1 or target[3] != 35:
        raise ValueError(f"Unexpected native silhouette or clipping: {target}")
    record = {
        "source": SPRITE,
        "source_sha256": digest((ROOT / SPRITE).read_bytes()),
        "source_size": list(master.size),
        "hard_alpha_threshold": 128,
        "source_bounds_xyxy": list(bounds),
        "uniform_scale": scale,
        "rounded_output_size": list(resized.size),
        "destination_origin": [left, top],
        "destination_bounds_xyxy": list(target),
        "canvas": [24, 36],
        "resampling": "nearest",
        "palette_reduction": None,
        "artwork_modifications": "none; hard-alpha extraction and uniform registration only",
    }
    return native, record


def comparison(sprite):
    entries = (
        ("Caelan", Image.open(ROOT / "assets/characters/caelan/idle_front.png").convert("RGBA")),
        ("Mira", Image.open(ROOT / "assets/characters/mira/idle_front.png").convert("RGBA")),
        ("Iselin", sprite),
    )
    # Existing character foot anchors all share row 34; Mira's current canvas
    # is 32px wide, even though an older README still describes 24px.
    width = sum(image.width for _, image in entries) + 24
    strip = Image.new("RGBA", (width, 40))
    x, centers = 4, []
    for name, image in entries:
        strip.alpha_composite(image, (x, 2))
        centers.append((name, x + image.width // 2))
        x += image.width + 8
    return strip, centers


def products():
    master = Image.open(ROOT / PORTRAIT)
    if master.width != master.height:
        raise ValueError("Iselin's dialogue portrait master must be square")
    portrait = master.convert("RGB").resize((72, 72), Image.Resampling.NEAREST)
    sprite, sprite_record = register_sprite(Image.open(ROOT / SPRITE))
    strip, centers = comparison(sprite)
    portrait4 = portrait.resize((288, 288), Image.Resampling.NEAREST)
    sprite16 = matte(sprite, 16)
    comparison4 = matte(strip, 4)
    board = Image.new("RGB", (1280, 850), MATTE)
    draw = ImageDraw.Draw(board)
    draw.text((24, 18), "ISELIN / DESIGN A / FIRST ASSET REVIEW", font=font(25), fill=INK)
    draw.text((24, 57), "Design approved; new artwork awaiting user review. Game integration is pending.", font=font(16), fill=INK)
    draw.text((32, 94), "Dialogue portrait / 72 x 72 export / 4x", font=font(15), fill=INK)
    board.paste(portrait4, (32, 126))
    draw.text((360, 94), "Front idle / 24 x 36 export / 16x", font=font(15), fill=INK)
    board.paste(sprite16, (360, 126))
    draw.text((792, 94), "Same-foot-line comparison / 4x", font=font(15), fill=INK)
    board.paste(comparison4, (792, 126))
    for name, center in centers:
        draw.text((792 + center * 4, 296), name, anchor="mt", font=font(13), fill=INK)
    draw.text((32, 450), "Native portrait / 1x", font=font(15), fill=INK)
    board.paste(portrait, (32, 480))
    draw.text((792, 348), "Native sprite comparison / 1x", font=font(15), fill=INK)
    board.paste(matte(strip), (792, 378))
    draw.text((792, 450), "Caelan and Mira: existing game artwork", font=font(14), fill=INK)
    draw.text((792, 477), "Iselin: new export from generated master", font=font(14), fill=INK)
    draw.text((24, 764), "Enlargements use nearest-neighbor sampling. Source masters are retained separately.", font=font(16), fill=INK)
    draw.text((24, 794), "Preview layout only; no existing actor, portrait registry, or story state has been changed.", font=font(15), fill=INK)
    outputs = {
        "assets/portraits/eldenmere/iselin_neutral.png": encoded(portrait),
        f"{BASE}/idle_front.png": encoded(sprite),
        f"{REVIEW}/portrait_4x.png": encoded(portrait4),
        f"{REVIEW}/idle_front_16x.png": encoded(sprite16),
        f"{REVIEW}/native_comparison.png": encoded(matte(strip)),
        f"{REVIEW}/comparison_4x.png": encoded(comparison4),
        f"{REVIEW}/preview.png": encoded(board),
    }
    outputs[f"{BASE}/idle_front.json"] = json_bytes({
        "character": "iselin", "animation": "idle.front",
        "design_status": "approved", "artwork_status": "awaiting_user_review",
        "status": "awaiting_user_review", "image": "idle_front.png",
        "frame_size": [24, 36], "rect": [0, 0, 24, 36],
        "foot_anchor": [12, 34], "draw_anchor": [12, 30],
        "source": SPRITE,
        "export_recipe": "tools/export_iselin_first_assets.py",
        "runtime_integration": False,
    })
    record = {
        "design": "Iselin / Royal Envoy / approved concept A",
        "design_status": "approved", "artwork_status": "awaiting_user_review",
        "runtime_integration": False,
        "builder": "tools/export_iselin_first_assets.py",
        "portrait": {
            "source": PORTRAIT,
            "source_sha256": digest((ROOT / PORTRAIT).read_bytes()),
            "source_size": list(master.size),
            "source_bounds_xyxy": [0, 0, *master.size],
            "output_size": [72, 72], "output_mode": "RGB",
            "resampling": "nearest",
        },
        "sprite": sprite_record,
        "outputs": {path: {"sha256": digest(data)} for path, data in outputs.items()},
    }
    outputs["assets/source/characters/iselin/first_assets_export.json"] = json_bytes(record)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify existing exports byte-for-byte without writing")
    args = parser.parse_args()
    result = products()
    if args.check:
        stale = [path for path, data in result.items() if not (ROOT / path).is_file() or (ROOT / path).read_bytes() != data]
        if stale:
            raise SystemExit("Missing or stale Iselin exports:\n" + "\n".join(stale))
        print(f"Verified {len(result)} deterministic Iselin exports.")
        return
    for path, data in result.items():
        destination = ROOT / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    print(f"Exported {len(result)} Iselin assets and review records; no runtime integration.")


if __name__ == "__main__":
    main()
