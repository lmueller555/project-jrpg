"""Export Caelan's authored native bench pose without warping his body.

The imagegen concept establishes a relaxed, two-knee seated silhouette. The
production sprite registers the approved head and upper tunic unchanged and
authors the bent elbows, lap, knees and boots explicitly on the native grid.
No flattened character is stretched, sheared, rotated or folded.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/characters/caelan/participation_sit'
OUTPUT = ROOT/'assets/characters/caelan/participation_sit_front.png'
IDLE = ROOT/'assets/characters/caelan/idle_front.png'
PALETTE = {
    '.': (0, 0, 0, 0),
    'o': '#1a0e16', 'd': '#2b1715', 'b': '#573422',
    'n': '#645450', 'l': '#8b5531', 'p': '#b67644',
    'a': '#e8c49d', 't': '#e99f55', 'c': '#fbeed0',
    'f': '#1f5d72', 'g': '#d3963f',
}


def build():
    SOURCE.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    idle = Image.open(IDLE).convert('RGBA')
    image = Image.new('RGBA', (24, 36))
    # Approved appearance pixels remain registered, including the asymmetric
    # fringe, face, golden tunic, blue vest and upper cream sleeves.
    image.alpha_composite(idle.crop((0, 0, 24, 19)), (0, 0))
    image.alpha_composite(idle.crop((8, 19, 17, 25)), (8, 19))
    draw = ImageDraw.Draw(image)

    def pixels(y, x, row):
        for offset, symbol in enumerate(row):
            if symbol != '.':
                draw.point((x+offset, y), fill=PALETTE[symbol])

    # Lap projects forward from the hips. Separate broad thighs and knees
    # lead into two hanging shins; boots remain clear of the bench artwork.
    for y, x, row in (
        (24, 6, 'oobbggggbboo'),
        (25, 5, 'obnnngggnnnbo'),
        (26, 4, 'onnnnnboobnnnnno'),
        (27, 4, 'onnnnno..onnnnno'),
        (28, 5, 'onnno....onnno'),
        (29, 6, 'obbo....obbo'),
        (30, 6, 'olpo....oplo'),
        (31, 5, 'olppo....opplo'),
        (32, 5, 'ooooo....ooooo'),
    ):
        pixels(y, x, row)

    # Explicit bent cream-sleeved elbows, brown wristbands and warm hands
    # resting on each thigh. Segment lengths are authored, not raster warps.
    for y, x, row in (
        (19, 5, 'ocao......oaco'),
        (20, 5, 'ocao......oaco'),
        (21, 5, 'occo......occo'),
        (22, 5, '.obao....oabo.'),
        (23, 6, 'otaa....aato'),
        (24, 7, 'oaat..taao'),
        (25, 8, 'oa....ao'),
    ):
        pixels(y, x, row)

    image.save(OUTPUT)
    recipe = {
        'output': OUTPUT.relative_to(ROOT).as_posix(),
        'size': [24, 36], 'draw_anchor': [12, 34],
        'seat_contact': [12, 25], 'boots_baseline': 33,
        'appearance_source': IDLE.relative_to(ROOT).as_posix(),
        'appearance_sha256': hashlib.sha256(IDLE.read_bytes()).hexdigest(),
        'concept': 'imagegen_concept.png',
        'method': 'Approved head/upper tunic pixels plus explicit native articulated seated limbs; no anatomical raster warps.',
    }
    (SOURCE/'recipe.json').write_text(json.dumps(recipe, indent=2)+'\n')
    image.resize((240, 360), Image.Resampling.NEAREST).save(SOURCE/'native_review.png')


if __name__ == '__main__':
    build()
