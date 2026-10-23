"""Export Serene's retained front-idle concept at the shared 24×36 scale."""
import json
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/characters/serene'
OUT = ROOT / 'assets/characters/serene'
BACKGROUND = '#e8edf2'


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def rgb(value):
    return ImageColor.getrgb(value)


def font(size):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', size)


def build():
    recipe = json.loads((SOURCE / 'export.json').read_text())
    palette = json.loads((OUT / 'palette.json').read_text())
    source = Image.open(SOURCE / recipe['source']).convert('RGBA')
    native = Image.new('RGBA', tuple(recipe['frame_size']))
    left, _, right, _ = recipe['source_bounds']
    x, _, width, _ = recipe['occupied_rect']
    for band in recipe['bands']:
        top, bottom = band['source_y']
        first, last = band['native_y']
        sampled = source.crop((left, top, right, bottom)).resize(
            (width, last - first), Image.Resampling.NEAREST)
        for sy in range(sampled.height):
            for sx in range(sampled.width):
                pixel = sampled.getpixel((sx, sy))
                if pixel[3] < recipe['alpha_threshold']:
                    continue
                source_x = left + int((sx + .5) * (right - left) / width)
                source_y = top + int((sy + .5) * (bottom - top) / sampled.height)
                materials = band['materials']
                for window in recipe['material_windows']:
                    x0, y0, x1, y1 = window['rect']
                    if x0 <= source_x < x1 and y0 <= source_y < y1:
                        materials = window['materials']
                colors = [rgb(c) for material in materials for c in palette['materials'][material]]
                color = min(colors, key=lambda c: sum((a - b) ** 2 for a, b in zip(c, pixel[:3])))
                native.putpixel((x + sx, first + sy), (*color, 255))
    # Explicit eye landmarks keep both eyes readable after the very small export.
    for ex, ey in recipe['eyes']['top_pixels']:
        native.putpixel((ex, ey), (*rgb(palette['eyes']['pupil']), 255))
        native.putpixel((ex, ey + 1), (*rgb(palette['eyes']['iris']), 255))

    native.save(OUT / 'idle_front.png')
    layers = []
    combined = Image.new('RGBA', native.size)
    for name, rows in recipe['layers'].items():
        layer = Image.new('RGBA', native.size)
        layer.paste(native.crop((0, rows[0], 24, rows[1])), (0, rows[0]))
        layer.save(SOURCE / 'layers' / f'{name}.png')
        combined.alpha_composite(layer)
        layers.append(f'../../source/characters/serene/layers/{name}.png')
    assert combined.tobytes() == native.tobytes(), 'Layer reconstruction differs'
    assert native.getbbox()[1::2] == (1, 35), 'Shared height and foot baseline'
    assert set(native.getchannel('A').getdata()) == {0, 255}
    allowed = {(*rgb(c), 255) for colors in palette['materials'].values() for c in colors}
    allowed.update((*rgb(c), 255) for c in palette['eyes'].values())
    assert all(p[3] == 0 or p in allowed for p in native.getdata())
    for ex, ey in recipe['eyes']['top_pixels']:
        assert native.getpixel((ex, ey + 1))[:3] == rgb(palette['eyes']['iris'])

    review = Image.new('RGB', (720, 1040), BACKGROUND)
    draw = ImageDraw.Draw(review)
    draw.text((32, 16), 'Mother Serene — front idle', font=font(28), fill='#26343e')
    draw.text((32, 54), '24×36 pixels · 24× nearest-neighbor · review', font=font(20), fill='#52616c')
    enlarged = native.resize((576, 864), Image.Resampling.NEAREST)
    review.paste(enlarged, (72, 96), enlarged)
    draw.text((32, 984), 'Silver temples · sage dress · linen apron', font=font(23), fill='#26343e')
    review.save(OUT / 'idle_front_review.png')

    board = Image.new('RGB', (1280, 720), BACKGROUND)
    draw = ImageDraw.Draw(board)
    draw.text((32, 16), 'Shared character scale — 24×36 frames at 16×', font=font(26), fill='#26343e')
    for index, (name, character) in enumerate([('Caelan', 'caelan'), ('Serene (review)', 'serene'), ('Mira', 'mira')]):
        sprite = Image.open(ROOT / 'assets/characters' / character / 'idle_front.png').convert('RGBA')
        enlarged = sprite.resize((384, 576), Image.Resampling.NEAREST)
        bx = 32 + index * 416
        board.paste(enlarged, (bx, 96), enlarged)
        draw.text((bx + 40, 682), name, font=font(23), fill='#26343e')
    board.save(OUT / 'scale_comparison.png')
    metadata_path = OUT / 'idle_front.json'
    status = json.loads(metadata_path.read_text()).get('status', 'review') if metadata_path.exists() else 'review'
    write_json(metadata_path, {
        'character': 'serene', 'display_name': 'Mother Serene', 'animation': 'idle.front',
        'design_status': 'approved', 'status': status, 'image': 'idle_front.png',
        'frame_size': [24, 36], 'rect': [0, 0, 24, 36], 'foot_anchor': [12, 34],
        'palette': 'palette.json', 'source': '../../source/characters/serene/idle_front_concept.png',
        'export_recipe': '../../source/characters/serene/export.json', 'layers': layers,
        'eyes': recipe['eyes'], 'dress': {'hem_row': 28},
        'review': {'image': 'idle_front_review.png', 'scale': 24, 'background': BACKGROUND},
        'comparison': 'scale_comparison.png',
    })
    print('Exported Serene front idle, four layers and two opaque review images.')


if __name__ == '__main__':
    build()
