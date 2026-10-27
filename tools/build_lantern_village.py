"""Build the small festival preparations used by MQ04's village visits.

Existing residents, beds, the working mill, the returned cart and Elira's
memorial lantern remain owned by their original scenes/controllers. This pack
adds only flour set aside for baking and a light paper-decoration tray.
"""
from pathlib import Path
import hashlib
import json

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/story/lantern'
PREFIX = 'assets/story/lantern/'
PAPER_BLUE = '#7195a8'
PAPER_YELLOW = '#d8ba67'
WOOD_DARK = '#54452f'
WOOD = '#9b774a'
WOOD_LIGHT = '#c3a16b'


def png(name, image):
    assert image.mode == 'RGBA'
    assert set(image.getchannel('A').tobytes()) <= {0, 255}
    path = OUT/'village_props'/name
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    image.save(temporary, format='PNG')
    temporary.replace(path)
    return path.relative_to(ROOT).as_posix()


def metadata(name, record):
    path = OUT/name
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(record, indent=2)+'\n')
    temporary.replace(path)


def flour_stack():
    """Three exact approved sacks; no new food or inventory asset identity."""
    sack = Image.open(ROOT/'assets/story/halden/sack.png').convert('RGBA')
    image = Image.new('RGBA', (31, 29))
    image.alpha_composite(sack, (0, 11))
    image.alpha_composite(sack, (15, 10))
    image.alpha_composite(sack, (7, 0))
    return image


def paper_tray(selected=False):
    """A low tray at the bedside; the child chooses while remaining in bed."""
    image = Image.new('RGBA', (38, 18))
    d = ImageDraw.Draw(image)
    d.polygon([(2, 2), (33, 2), (37, 12), (0, 12)], fill=WOOD_DARK)
    d.polygon([(3, 3), (32, 3), (35, 10), (2, 10)], fill=WOOD)
    d.line((4, 3, 31, 3), fill=WOOD_LIGHT)
    d.line((0, 12, 37, 12), fill=WOOD_LIGHT)
    d.rectangle((1, 13, 36, 15), fill=WOOD_DARK)
    # The two piles remain visible after choosing. The short alternating strip
    # is their modest contribution, not an instantaneous finished festival.
    for x, y, color in ((5, 4, PAPER_BLUE), (14, 4, PAPER_YELLOW)):
        d.polygon([(x, y), (x+5, y), (x+6, y+4), (x+1, y+4)], fill=color)
        d.line((x+1, y, x+4, y), fill='#e4d5ad')
    if selected:
        for x, color in ((23, PAPER_YELLOW), (27, PAPER_BLUE), (31, PAPER_YELLOW)):
            d.rectangle((x, 7, x+2, 10), fill=WOOD_DARK)
            d.rectangle((x, 7, x+2, 8), fill=color)
        d.line((23, 6, 33, 6), fill='#d6c39a')
    else:
        d.line((23, 6, 33, 6), fill='#d6c39a')
        d.line((24, 8, 32, 8), fill=PAPER_BLUE)
        d.line((25, 10, 33, 10), fill=PAPER_YELLOW)
    return image


def build():
    flour = png('festival_flour.png', flour_stack())
    before = png('venn_papers_unselected.png', paper_tray(False))
    after = png('venn_papers_selected.png', paper_tray(True))
    metadata('village_art.json', {
        'props': [
            {'id': 'festival_flour', 'scene': 'eldenmere.playable',
             'position': [1066, 380], 'sort_y': 410,
             'states': {'ready': flour}, 'footprint': [1067, 400, 27, 8]},
            {'id': 'venn_festival_papers', 'scene': 'venn',
             'position': [54, 164], 'sort_y': 183,
             'states': {'unselected': before, 'selected': after}},
        ],
        'source_sack': 'assets/story/halden/sack.png',
        'source_sack_sha256': hashlib.sha256((ROOT/'assets/story/halden/sack.png').read_bytes()).hexdigest(),
        'scope': 'Two small preparation props; no new residents, bodily poses or memorial lantern.',
        'paper_colors': {'yellow': PAPER_YELLOW, 'blue': PAPER_BLUE},
        'paper_selected_after': 'neighbours_visited',
    })
    metadata('village_layout.json', {
        'mill': [1006, 432], 'mill_liam': [1024, 430], 'mill_tomas': [1050, 430],
        'mill_halden': [1032, 408],
        'venn': [136, 212], 'venn_liam': [126, 156], 'venn_tomas': [158, 178],
        'venn_mother': [104, 178], 'venn_father': [300, 202], 'venn_child': [88, 138],
        'elira': [170, 196], 'elira_liam': [190, 184], 'elira_tomas': [230, 224],
        'elira_resident': [210, 202],
        'reflection': [672, 1000], 'reflection_liam': [696, 1000], 'reflection_tomas': [718, 1014],
        'venn_approach': [1248, 750], 'venn_door': [1247.5, 726],
        'venn_entry': [252, 294], 'venn_exit': [252, 306],
        'elira_approach': [672, 990], 'elira_door': [671.5, 966],
        'elira_entry': [102, 294], 'elira_exit': [102, 306],
        'route': ['workshop', 'mill', 'venn', 'elira', 'reflection'],
        'scene_ids': {'mill': 'eldenmere.playable', 'venn': 'venn', 'elira': 'elira', 'reflection': 'eldenmere.playable'},
        'registration': 'Player stations use the ordinary 24x12 probe; companion stations use each existing actor probe.',
    })
    print('Built MQ04 village layout and two grounded preparation props.')


if __name__ == '__main__':build()
