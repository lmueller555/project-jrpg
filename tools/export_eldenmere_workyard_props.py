"""Export independent native workyard storage from retained detailed masters.

This bank registers the genuine burlap sack, empty wooden crate and toolbox
drawings. It never enlarges a regional miniature or reuses a live quest ID.
Collision and runtime activation belong to the maintained settlement composer.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_eldenmere_hd import fit, source_cell

RECIPE = 'assets/source/maps/eldenmere/workyard_props/recipe.json'
PACK = 'assets/terrain/eldenmere/workyard_props'


def document(value):
    return (json.dumps(value, indent=2)+'\n').encode()


def products():
    """Return reproducible bytes without writing files, including for --check."""
    recipe_path = ROOT/RECIPE
    recipe_raw = recipe_path.read_bytes()
    recipe = json.loads(recipe_raw)
    if recipe.get('version') != 1 or recipe.get('artwork_pixels_per_world_pixel') != 2:
        raise ValueError('Unsupported workyard prop recipe version/density')
    source = recipe['source']
    source_path = ROOT/source['file']
    if sha256(source_path.read_bytes()).hexdigest() != source['sha256']:
        raise ValueError('Changed retained workyard source; inspect its silhouettes before exporting')
    with Image.open(source_path) as raw:
        sheet = raw.convert('RGBA')
    out, exports, props, seen = {}, [], [], set()
    for record in recipe['props']:
        name = record['id']
        if name in seen:
            raise ValueError('Duplicate workyard prop '+name)
        seen.add(name)
        raw = source_cell(sheet, record['cell'], source['columns'], source['rows'])
        if list(raw.size) != record['source_silhouette_size']:
            raise ValueError('Retained workyard source cell changed: '+name)
        size = record['logical_size']
        if (len(size) != 2 or any(type(value) is not int or value <= 0 for value in size)):
            raise ValueError('Workyard canvas must use positive logical dimensions: '+name)
        left, top, right, bottom = record['register_bounds_logical']
        if not (0 <= left < right <= size[0] and 0 <= top < bottom <= size[1]):
            raise ValueError('Workyard registration leaves the canvas: '+name)
        if bottom != record['depth_baseline_logical']:
            raise ValueError('Workyard depth must agree with its registered support: '+name)
        native = fit(raw, size, record['register_bounds_logical'])
        if native.size != tuple(value*2 for value in size):
            raise ValueError('Workyard export lost native density: '+name)
        alpha = native.getchannel('A')
        if set(alpha.tobytes()) - {0, 255}:
            raise ValueError('Workyard export must retain hard alpha: '+name)
        bounds = native.getbbox()
        if bounds is None or bounds[3] != bottom*2:
            raise ValueError('Workyard occupied support lost registration: '+name)
        # Reject neighboring source fragments, preserving a single real object.
        import pygame
        mask = pygame.mask.from_surface(pygame.image.frombytes(native.tobytes(), native.size, 'RGBA'))
        components = mask.connected_components()
        if not components or max(piece.count() for piece in components) != mask.count():
            raise ValueError('Workyard export contains disconnected object fragments: '+name)
        relative = 'props/'+name+'/idle.png'
        path = PACK+'/'+relative
        stream = BytesIO();native.save(stream, format='PNG')
        encoded = stream.getvalue()
        digest = sha256(encoded).hexdigest()
        out[path] = encoded
        exports.append(dict(file=path, artwork_size=list(native.size), sha256=digest))
        props.append(dict(id=name, family='workyard_storage', mount='ground',
                          logical_size=list(size), artwork_size=list(native.size),
                          artwork_pixels_per_world_pixel=2,
                          idle=relative, frames=[dict(file=relative, duration_ms=600)],
                          animation='static', frame_duration_ms=600,
                          depth_baseline_logical=bottom,
                          draw_anchor_logical=[size[0]/2, bottom],
                          anchor_artwork=[size[0], bottom*2], anchor_space='artwork',
                          occupied_rect_logical=[bounds[0]/2, bounds[1]/2,
                                                 (bounds[2]-bounds[0])/2, (bounds[3]-bounds[1])/2],
                          footprint_root=list(record['footprint_root']),
                          collision='not_registered; each placement needs an explicit reviewed support',
                          interaction_cues=False, semantic_use=record['semantic_use'],
                          source=dict(file=source['file'], sha256=source['sha256'],
                                      cell=record['cell'], columns=source['columns'], rows=source['rows'],
                                      silhouette_size=list(raw.size)), output_sha256=digest))
    manifest = dict(version=1, id=recipe['id'], artwork_state='retained_native_source_export',
                    integration_status='available_for_explicit_placement',
                    visual_approval='registration_requires_scene_review',
                    artwork_pixels_per_world_pixel=2,
                    recipe=RECIPE, recipe_sha256=sha256(recipe_raw).hexdigest(),
                    exporter='tools/export_eldenmere_workyard_props.py',
                    exporter_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                    sources=[source], props=props, exports=exports)
    out[PACK+'/manifest.json'] = document(manifest)
    return out


def build(check=False):
    result = products()
    stale = []
    for path, raw in result.items():
        target = ROOT/path
        if not target.is_file() or target.read_bytes() != raw:
            stale.append(path)
            if not check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
    if check and stale:
        raise SystemExit('Stale workyard prop exports: '+', '.join(stale))
    print(f'{len(result)} workyard prop exports '+('verified' if check else 'built'))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
