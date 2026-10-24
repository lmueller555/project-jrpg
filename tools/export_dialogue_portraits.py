"""Split the generated portrait masters and export review-sized PNG assets.

This tool only crops, resizes and lays out artwork; image generation owns the
portrait designs. It does not modify approved world sprites or game behavior.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/portraits/eldenmere'
OUTPUT = ROOT / 'assets/portraits/eldenmere'
REVIEW = ROOT / 'docs/reviews/dialogue_portraits'
SIZE = 72
GROUPS = (
    ('main_cast_atlas.png', 2, 2, 'main_cast.png', (
        ('caelan', 'Caelan', 'caelan'),
        ('mira', 'Mira', 'mira'),
        ('serene', 'Mother Serene', 'serene'),
        ('tomas', 'Tomas', 'tomas'),
    )),
    ('villagers_atlas.png', 3, 2, 'villagers.png', (
        ('male_01', 'Male NPC / moss', 'npcs/male_01'),
        ('male_02', 'Male NPC / rust', 'npcs/male_02'),
        ('male_03', 'Male NPC / slate', 'npcs/male_03'),
        ('female_01', 'Female NPC / blue', 'npcs/female_01'),
        ('female_02', 'Gardener / sage', 'npcs/female_02'),
        ('female_03', 'Female NPC / plum', 'npcs/female_03'),
    )),
)


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    records = {}
    # Font is used only to label review boards, never loaded by the game.
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
    for source, columns, rows, preview, characters in GROUPS:
        atlas = Image.open(SOURCE / source).convert('RGB')
        if atlas.width % columns or atlas.height % rows:
            raise ValueError(f'{source}: atlas is not evenly divisible')
        width, height = atlas.width // columns, atlas.height // rows
        if width != height:
            raise ValueError(f'{source}: portrait cells must be square')
        board = Image.new('RGB', (columns * 320, rows * 360 + 48), '#e8edf2')
        draw = ImageDraw.Draw(board)
        draw.text((16, 12), 'ELDENMERE / dialogue portraits / awaiting review',
                  font=font, fill='#263c35')
        for index, (key, label, sprite) in enumerate(characters):
            x, y = index % columns, index // columns
            box = (x * width, y * height, (x + 1) * width, (y + 1) * height)
            portrait = atlas.crop(box).resize((SIZE, SIZE), Image.Resampling.NEAREST)
            portrait.save(OUTPUT / f'{key}_neutral.png')
            enlarged = portrait.resize((288, 288), Image.Resampling.NEAREST)
            enlarged.save(REVIEW / f'{key}_4x.png')
            origin = (x * 320 + 16, y * 360 + 48)
            board.paste(enlarged, origin)
            draw.text((origin[0], origin[1] + 296), label, font=font, fill='#263c35')
            draw.text((origin[0], origin[1] + 324), '72 x 72 native / enlarged 4x',
                      font=small, fill='#526761')
            records[key] = {
                'name': label, 'expression': 'neutral', 'file': f'{key}_neutral.png',
                'sprite_root': f'assets/characters/{sprite}',
                'source': f'assets/source/portraits/eldenmere/{source}',
                'source_rect': list(box),
            }
        board.save(REVIEW / preview)
    manifest = {
        'status': 'awaiting_user_review', 'frame_size': [SIZE, SIZE],
        'format': 'RGB PNG', 'background': 'opaque dark green',
        'portraits': records,
        'aliases': {'mother_serene': 'serene', 'sanctuary_gardener': 'female_02'},
        'runtime_integration': False,
    }
    (OUTPUT / 'portraits.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Exported {len(records)} portraits at {SIZE}x{SIZE} and labeled 4x review boards.')


if __name__ == '__main__':
    build()
