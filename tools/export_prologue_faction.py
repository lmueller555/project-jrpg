"""Export image-authored Carcovian heraldry while protecting scene pixels.

Image generation owns the new cloth, badge and armor drawings. This technical
export restores the approved source outside explicit repair windows; it never
recolors painted pixels or constructs character anatomy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ENV = ROOT/'assets/source/cinematics/fire_veinhold/shot01/environment'
MATERIALS = ROOT/'assets/source/cinematics/fire_veinhold/continuation/materials'
# Native-source repair windows include the original cloth and its old badge.
# Architectural stone, emissive warning glass and amber machinery stay outside.
BANNER_WINDOWS = {
    'panorama': [(235,317,251,365),(287,317,304,365),(523,349,546,401),
                 (465,412,481,449),(581,411,600,449),
                 (432,477,454,527),(505,477,531,537),
                 (781,475,810,526),(911,474,933,526)],
    '090': [(478,733,501,780),(651,627,679,705),(805,665,829,711),
            (746,730,770,780),(580,786,603,830),(705,775,731,818),
            (542,908,566,959),(566,919,589,983),(926,896,956,974),
            (769,926,797,974),(1177,917,1209,985)],
    '180': [(309,795,346,866),(384,877,424,962),
            (1017,732,1056,807),(976,863,1026,941)],
}


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _protected(original, generated, mask):
    original = Image.open(original).convert('RGB')
    generated = Image.open(generated).convert('RGB')
    if generated.size != original.size:
        raise ValueError('Faction edits must retain the approved source canvas')
    result = Image.composite(generated, original, mask)
    outside = ImageChops.invert(mask)
    difference = ImageChops.difference(result, original)
    if ImageChops.multiply(difference, outside.convert('RGB')).getbbox():
        raise ValueError('Faction export changed pixels outside its repair mask')
    return result


def products():
    output = {}
    records = {}
    for label, windows in BANNER_WINDOWS.items():
        folder = ENV if label == 'panorama' else MATERIALS
        original = folder/('veinhold_generated.png' if label == 'panorama'
                           else f'orbit_{label}_pre_faction_reference.png')
        generated = folder/('veinhold_faction_generated.png' if label == 'panorama'
                            else f'orbit_{label}_faction_generated.png')
        dest = folder/('veinhold_faction_final.png' if label == 'panorama'
                       else f'orbit_{label}_final.png')
        with Image.open(original) as image:
            mask = Image.new('L', image.size)
        draw = ImageDraw.Draw(mask)
        for window in windows:
            draw.rectangle(window, fill=255)
        output[dest] = _protected(original, generated, mask)
        records[label] = {'original':str(original.relative_to(ROOT)),
                          'original_sha256':_hash(original),
                          'generated':str(generated.relative_to(ROOT)),
                          'generated_sha256':_hash(generated),
                          'output':str(dest.relative_to(ROOT)),
                          'repair_rectangles':windows,
                          'protected_pixels':'All pixels outside the authored banner repair windows.'}
    from tools.export_frozen_guard_layers import POLYGONS
    original = MATERIALS/'frozen_bridge_pre_faction_reference.png'
    generated = MATERIALS/'frozen_bridge_faction_generated.png'
    with Image.open(original) as image:
        mask = Image.new('L', image.size)
    draw = ImageDraw.Draw(mask)
    for polygon in POLYGONS.values():
        draw.polygon([(round(x*1.6), round(y*1.6)) for x,y in polygon], fill=255)
    mask = mask.filter(ImageFilter.MaxFilter(7))
    output[MATERIALS/'frozen_bridge_final.png'] = _protected(original, generated, mask)
    records['frozen_guards'] = {'original':str(original.relative_to(ROOT)),
        'original_sha256':_hash(original),'generated':str(generated.relative_to(ROOT)),
        'generated_sha256':_hash(generated),'output':str((MATERIALS/'frozen_bridge_final.png').relative_to(ROOT)),
        'repair_polygons_at_960x640':POLYGONS,'safety_dilation_source_pixels':3,
        'protected_pixels':'All bridge, mountains, sky, torches and deck outside the existing four ice/guard silhouettes.'}
    # Use native nearest sampling and the production quiet-lens pass for the
    # derived terrain plate. Fixed crop rounding differs from the production
    # layout's fractional size/offset arithmetic by one vertical pixel; this
    # first visual handoff is not claimed to be a pixel-identical shot join.
    import pygame
    from cinematic_facility import CinematicFacility
    source = output[ENV/'veinhold_faction_final.png']
    scene = json.loads((ENV/'recipe.json').read_text())
    software = pygame.image.frombytes(source.tobytes(), source.size, 'RGB')
    software = CinematicFacility(scene['facility'], source.size).inactive_background(software)
    factor = max(960/source.width, 640/source.height)*1.035
    size = (round(source.width*factor), round(source.height*factor))
    origin = (round((960-size[0])/2), round(-scene['framing']['vista_y']*factor))
    target = pygame.Surface((960,640), depth=32)
    target.blit(pygame.transform.scale(software, size), origin)
    projection = Image.frombytes('RGB', (960,640), pygame.image.tobytes(target, 'RGB'))
    output[MATERIALS/'approved_projection.png'] = projection
    output[MATERIALS/'orbit_000_final.png'] = projection.copy()
    records['initial_projection'] = {'source':'veinhold_faction_final.png',
        'sampler':'pygame.transform.scale; production quiet red-lens pass; fixed source-crop rounding',
        'source_scale':factor,'sample_size':size,'blit_origin':origin,
        'output_canvas':[960,640],'global_time_seconds':25,
        'registration_note':'One vertical pixel of crop-rounding difference from the first-shot fractional layout; not a pixel-identical eagle-to-orbit join.',
        'scope':'Terrain-only first handoff; vent-anchored plumes remain separate.'}
    return output, records


def build(check=False):
    output, records = products()
    for path, image in output.items():
        if check:
            if not path.exists() or ImageChops.difference(Image.open(path).convert('RGB'), image).getbbox():
                raise ValueError('Stale faction artwork export: '+path.name)
        else:
            image.save(path, compress_level=6)
    if not check:
        # Register the new source without changing preserved historical masters.
        recipe_path = ENV/'recipe.json'
        recipe = json.loads(recipe_path.read_text())
        recipe['source_records'] = [r for r in recipe['source_records']
                                    if r['file'] not in ('veinhold_faction_generated.png','veinhold_faction_final.png')]
        for name in ('veinhold_faction_generated.png','veinhold_faction_final.png'):
            recipe['source_records'].append({'file':name,'sha256':_hash(ENV/name),
                'generation_id':'exec-5776255e-298d-47c7-9c00-d59ae7e2e472',
                'prompt_file':'veinhold_faction_prompt.txt',
                'export_tool':'tools/export_prologue_faction.py',
                'purpose':'Charcoal cloth and copper split-ring/bar heraldry; preserve all non-banner pixels.'})
        recipe['layers']['panorama']['source'] = 'veinhold_faction_final.png'
        recipe_path.write_text(json.dumps(recipe, indent=2)+'\n')
        manifest = {'version':1,'exporter':'tools/export_prologue_faction.py',
                    'method':'Image-authored redraws inside explicit protected repair windows; no hue remapping.',
                    'records':records,
                    'output_sha256':{str(path.relative_to(ROOT)):_hash(path) for path in output}}
        (MATERIALS/'faction_export_recipe.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Faction artwork matches image-authored repairs with exact outside-pixel preservation.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
