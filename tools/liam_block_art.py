"""Source-owned 2x orthogonal toy box, conserved contents and literal front lip.

All geometry here is ARTWORK pixels. Runtime positions, anchors, occupied ground
and contact remain logical. No generated furniture-sheet extraction participates.
"""
from __future__ import annotations

from PIL import Image, ImageChops, ImageDraw

SIZE = (32, 24)
DENSITY = 2
PREFIX = 'rooms/liam_house/blocks'
OUTLINE = '#211a17'
WOOD = '#98653b'
LIGHT = '#c39358'
WORN = '#d9b478'
DARK = '#61452e'
# Canonical blocks retain their established logical canvases and draw anchors.
COLORS = ('#ad5643', '#507d99', '#c5a24f', '#6d8c57', '#b78a51')
# All stored pieces sit within the reachable right half; the beam's right end
# is also near the east access. Upper faces follow the horizontal/vertical map.
INSIDE = ((25, 12), (19.5, 12), (25, 7), (19.5, 7), (20.5, 13))


def blank(size=SIZE):
    return Image.new('RGBA', tuple(v*DENSITY for v in size))


def block(index):
    """Four painted wooden cuboids and a broad oak crosspiece, not toy icons."""
    im = blank((5, 5) if index < 4 else (16, 4))
    d = ImageDraw.Draw(im); w, h = im.size
    d.rectangle((0, 0, w-1, h-1), fill=OUTLINE)
    d.rectangle((1, 1, w-2, h-2), fill=COLORS[index])
    d.line((1, 1, w-2, 1), fill=WORN)
    d.line((1, h-4, w-2, h-4), fill=DARK)
    d.line((1, h-3, w-2, h-3), fill=WOOD)
    d.point((w-3, 2), fill=LIGHT)
    if index == 4:
        d.line((5, 3, 19, 3), fill=LIGHT)
        d.line((22, 4, 27, 4), fill=DARK)
    return im


def structure():
    """Parallel rims and vertical front, with fixed depth and no convergence."""
    shell = blank(); d = ImageDraw.Draw(shell)
    d.rectangle((4, 10, 59, 44), fill=OUTLINE)
    # Recessed interior; top footprint is a rectangle, never a trapezoid.
    d.rectangle((8, 13, 55, 32), fill='#503c2b')
    d.rectangle((10, 17, 53, 30), fill='#735134')
    d.line((11, 21, 52, 21), fill='#65472f')
    d.line((11, 27, 52, 27), fill='#815d3c')
    # Rear and side timber rims are a single connected stationary support.
    d.rectangle((5, 11, 58, 13), fill=LIGHT)
    d.line((6, 11, 57, 11), fill=WORN)
    d.rectangle((5, 14, 8, 33), fill=WOOD)
    d.rectangle((55, 14, 58, 33), fill=LIGHT)
    d.line((5, 14, 5, 32), fill=WORN)
    d.line((58, 14, 58, 32), fill=DARK)
    front = blank(); d = ImageDraw.Draw(front)
    d.rectangle((4, 31, 59, 44), fill=OUTLINE)
    d.rectangle((5, 32, 58, 43), fill=WOOD)
    d.line((6, 32, 57, 32), fill=WORN)
    d.line((6, 33, 57, 33), fill=LIGHT)
    d.line((6, 37, 57, 37), fill=DARK)
    d.line((7, 38, 56, 38), fill=LIGHT)
    # Fine grain and pinned corners: one native artwork pixel, not noise.
    for a,b,y in ((12,23,35),(35,48,35),(16,31,41),(40,52,41)):
        d.line((a,y,b,y), fill=DARK)
    for x in (7,56):
        d.line((x,34,x,42), fill=DARK)
        d.point((x,35), fill=OUTLINE); d.point((x,41), fill=OUTLINE)
    return shell, front


def layers(mask):
    shell, front = structure(); contents = blank()
    for index, (x,y) in enumerate(INSIDE):
        if mask & (1 << index):
            anchor = (2,2) if index < 4 else (8,2)
            contents.alpha_composite(block(index), (round((x-anchor[0])*2), round((y-anchor[1])*2)))
    # Interior owns contents; walls and their exact front layer obscure them.
    opening = Image.new('L', contents.size)
    ImageDraw.Draw(opening).rectangle((9,14,54,31), fill=255)
    contents.putalpha(ImageChops.multiply(contents.getchannel('A'), opening))
    merged = shell.copy(); merged.alpha_composite(contents); merged.alpha_composite(front)
    return merged, {'back':shell, 'contents':contents, 'front':front}


def integrate(data, entity, before, export):
    """Replace the entire state family together, preserving all gameplay data."""
    aliases = data.setdefault('art_replacements', {})
    states = {}
    for mask in range(32):
        im, _ = layers(mask)
        states[f'contents_{mask:02d}'] = export.png(f'{PREFIX}/contents_{mask:02d}', im)
    for count, legacy in before.get('state_images', {}).items():
        path = states[f'contents_{(1 << int(count))-1:02d}']
        states[count] = path
        aliases[legacy] = export.art(path, SIZE)
    full = states['contents_31']
    for legacy in before['frames']:
        aliases[legacy] = export.art(full, SIZE)
    entity.update(frames=[full], state_images=states, logical_size=list(SIZE),
                  artwork_pixels_per_world_pixel=2, reduced_motion_frame=0,
                  content_state_prefix='contents_',
                  construction_source='tools/liam_block_art.py',
                  artwork_registration={
                      'coordinate_space':'logical_world_units',
                      'canvas':[32,24], 'occupied_ground_rect':[2,15,28,8],
                      'depth_baseline':23, 'near_face_rect':[2,15.5,28,7],
                      'east_access':[36,20], 'east_contact':[26,11],
                      'projection':'orthogonal_parallel_rims'})


def props(export, pack):
    """The same block image moves from storage to hand to the floor."""
    aliases = {}
    for i, spec in enumerate(pack['blocks']):
        path = export.png(f'{PREFIX}/{spec["id"]}', block(i))
        aliases[spec['image']] = export.art(path, tuple(spec['frame_size']))
    _, front = structure()
    path = export.png(f'{PREFIX}/front_overlay', front)
    aliases[pack['front_overlay']] = export.art(path, SIZE)
    # Keep inspectable source layers next to the existing provenance.
    for mask in (0,31):
        _, source_layers = layers(mask)
        for name, im in source_layers.items():
            # Export collector keeps determinism/hash accounting; the source
            # recipe is this module, and these are its separated layer proofs.
            export.png(f'{PREFIX}/source/contents_{mask:02d}_{name}', im)
    return aliases
