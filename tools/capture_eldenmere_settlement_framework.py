"""Capture unchanged production town views before/after settlement-framework work.

These are initialized-Game review fixtures with disposable saves/settings. They
position the player on clear ground and hold the normal exploration camera at
explicit points; no replacement scene art is painted and no quests are seeded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageChops, ImageDraw

from main import Game

DEFAULT_OUTPUT = ROOT/'docs/reviews/eldenmere_settlement_framework'
TOWN = ROOT/'assets/maps/eldenmere/playable/map.json'
VIEWS = (
    ('serene_terrace', (384, 320), (384, 270)),
    ('workshop_yard', (670, 470), (636, 420)),
    ('mill_yard', (984, 396), (1008, 330)),
    ('commons', (576, 914), (528, 864)),
    ('school_frontage', (672, 756), (672, 680)),
    ('eastern_growing_area', (1260, 744), (1272, 744)),
    ('southern_arrival', (528, 1512), (528, 1450)),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def image_paths(value):
    """Follow active image values; alias-map keys are historical lookup names."""
    if isinstance(value, dict):
        for child in value.values():
            yield from image_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from image_paths(child)
    elif isinstance(value, str) and value.startswith('assets/') and value.endswith('.png'):
        yield value


def production_snapshot():
    town = json.loads(TOWN.read_text())
    paths = {TOWN.relative_to(ROOT).as_posix(), town['collision'], town['navigation_allowed']}
    for key in ('ground_frames', 'ground_overlays', 'entities', 'foreground',
                'doors', 'landmark_layers', 'art_replacements', 'well_art'):
        paths.update(image_paths(town.get(key)))
    grass = town.get('grass', {}).get('manifest')
    if grass:
        paths.add(grass)
        variants = json.loads((ROOT/grass).read_text())['tall_grass']['variants']
        for variant in {record['variant'] for record in town['grass']['instances']}:
            paths.update(image_paths(variants[variant]))
    files = {}
    for path in sorted(paths):
        source = ROOT/path
        if not source.is_file():
            raise AssertionError(f'Active production file missing: {path}')
        raw = source.read_bytes()
        files[path] = {'sha256': digest(raw), 'bytes': len(raw)}
    return {
        'town_map': TOWN.relative_to(ROOT).as_posix(),
        'map_field_sha256': {key: digest(canonical(value)) for key, value in sorted(town.items())},
        'active_file_count': len(files),
        'active_files': files,
        'town_size_logical': town['size_pixels'],
        'building_portals': len(town['doors']),
        'npc_ids': [record['id'] for record in town['npcs']],
        'persistent_npc_ids': [record['id'] for record in town.get('persistent_npcs', [])],
    }


def meaningful_state(game):
    return {
        'quests': game.quests.to_dict(), 'party': game.party.to_dict(),
        'inventory': game.inventory.to_dict(), 'flags': sorted(game.social.flags),
    }


def changed_pixels(first, second):
    difference = ImageChops.difference(first.convert('RGB'), second.convert('RGB')).tobytes()
    return sum(any(difference[index:index+3]) for index in range(0, len(difference), 3))


def protection_diagnostic(folder, manifest):
    """Separate illustrative reservation overlay; never a gameplay capture."""
    raw = manifest.read_bytes()
    contract = json.loads(raw)
    town = json.loads(TOWN.read_text())
    base = Image.open(ROOT/town['overview']).convert('RGBA')
    overlay = Image.new('RGBA', base.size)
    painter = ImageDraw.Draw(overlay)

    def hull(points):
        points = sorted(set(points))
        def cross(a, b, c):
            return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        lower, upper = [], []
        for point in points:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
                lower.pop()
            lower.append(point)
        for point in reversed(points):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
                upper.pop()
            upper.append(point)
        return lower[:-1]+upper[:-1]

    for record in contract['protected_spaces']:
        color = (255, 198, 80, 80) if 'sightline' in record['roles'] else (70, 215, 245, 80)
        edge = (*color[:3], 190)
        px, py = record['padding'];geometry = record['geometry']
        if record['shape'] == 'point':
            x, y = geometry
            painter.rectangle((x-px, y-py, x+px, y+py), fill=color, outline=edge)
        elif record['shape'] == 'rect':
            x, y, width, height = geometry
            painter.rectangle((x-px, y-py, x+width+px, y+height+py), fill=color, outline=edge)
        else:
            # Minkowski sum with the rectangular logical clearance. This avoids
            # presenting every actor's 24x12 footprint as a circular brush.
            for first, second in zip(geometry, geometry[1:]):
                polygon = hull([(x+dx, y+dy) for x, y in (first, second)
                                for dx, dy in ((-px,-py),(-px,py),(px,-py),(px,py))])
                if len(polygon) >= 3:
                    painter.polygon(polygon, fill=color, outline=edge)
                else:
                    painter.line([first, second], fill=edge, width=1)
    base.alpha_composite(overlay)
    result = Image.new('RGB', (base.width, base.height+64), '#172b27')
    result.paste(base.convert('RGB'), (0, 64))
    title = ImageDraw.Draw(result)
    title.text((12, 8), 'DIAGNOSTIC: current town source reservations, not proposed artwork or a gameplay screenshot.', fill='white')
    title.text((12, 26), 'Cyan: movement clearance. Amber: records also protecting actor / interaction sightlines.', fill='#ffda91')
    title.text((12, 44), 'Logical source padding shown; final placement validation also considers actual footprints and visibility.', fill='white')
    result.save(folder/'protection_plan_diagnostic.png')
    return {'manifest_sha256': digest(raw), 'records': len(contract['protected_spaces']),
            'image': 'protection_plan_diagnostic.png'}


def capture(folder, baseline=None, protection_manifest=None):
    folder.mkdir(parents=True, exist_ok=True)
    production = production_snapshot()
    report = {
        'scope': 'Production initialized Game, fixed clear-ground camera fixtures; no quest playthrough or new scenery.',
        'display_pixels': [960, 640], 'production': production,
        'views': {}, 'pixel_sha256': {},
    }
    with tempfile.TemporaryDirectory(prefix='eldenmere-settlement-review-') as directory:
        temporary = Path(directory)
        game = Game(fullscreen=False, window_size=(960, 640), start_on_title=True,
                    save_path=temporary/'journey.json', settings_path=temporary/'settings.json')
        try:
            game.on_title = False
            game.opening.restore({'version': 1, 'stage': 'disabled'})
            game.opening_fade = game.transfer_cooldown = 0
            game.audio.set_music(0);game.audio.set_effects(0)
            game.world = game.town
            before = canonical(meaningful_state(game))

            def place(point, focus):
                if not game.town.can_stand(point):
                    raise AssertionError(('Fixture is not clear', point))
                game.player.position.update(point)
                game.player.facing = 'front'
                game.player.moving = game.player.running = False
                game.player.walk_ms = 0
                game.location_label = None;game.location_seconds = 0
                game.saves.notice_seconds = 0
                game.camera.reset();game.camera.focus(focus, duration=0)

            def shot(name, time=0):
                game.elapsed_ms = time
                game.draw()
                if game.window.get_size() != (960, 640):
                    raise AssertionError('Capture must preserve the native display size')
                pygame.image.save(game.window, str(folder/(name+'.png')))
                raw = pygame.image.tobytes(game.window, 'RGB')
                report['pixel_sha256'][name] = digest(raw)
                report['views'][name] = {
                    'scene': game.world.data['id'], 'player_logical': list(game.player.position),
                    'camera_logical': list(game.camera.position()), 'elapsed_ms': time,
                    'reduced_motion': game.audio.reduced_motion,
                }
                return Image.frombytes('RGB', game.window.get_size(), raw)

            for name, player, focus in VIEWS:
                place(player, focus);shot(name)

            # The crop lies below the main bridge, inside the brook's water-only
            # center. It excludes UI, banks, actors and changing mill machinery.
            place((816, 1032), (840, 1080))
            camera = game.camera.position()
            water_rect = (828, 1128, 24, 48)
            crop = (round((water_rect[0]-camera[0])*2), round((water_rect[1]-camera[1])*2),
                    round((water_rect[0]+water_rect[2]-camera[0])*2),
                    round((water_rect[1]+water_rect[3]-camera[1])*2))
            report['water'] = {'logical_crop': water_rect, 'native_crop': crop}
            for reduced in (False, True):
                game.audio.set_reduced_motion(reduced)
                game._update_grass(0)
                prefix = 'water_still' if reduced else 'water_normal'
                images = [shot(f'{prefix}_{time}', time).crop(crop) for time in (0, 200, 400)]
                changes = [changed_pixels(images[0], image) for image in images[1:]]
                report['water'][prefix+'_changed_pixels'] = changes
                if reduced and any(changes):
                    raise AssertionError(('Reduced-motion water moved', changes))
                if not reduced and not any(changes):
                    raise AssertionError('Normal water fixture did not animate')
            report['quest_party_inventory_flags_unchanged'] = before == canonical(meaningful_state(game))
            if not report['quest_party_inventory_flags_unchanged']:
                raise AssertionError('Visual fixtures changed gameplay progress')
        finally:
            game.music.stop();pygame.quit()

    if production_snapshot() != production:
        raise AssertionError('Production inputs changed during capture; rerun after writers finish')
    if baseline is not None:
        previous = json.loads(baseline.read_text())
        checks = {
            'production_files_and_map_fields_identical': report['production'] == previous['production'],
            'all_native_view_pixels_identical': report['pixel_sha256'] == previous['pixel_sha256'],
            'fixtures_identical': report['views'] == previous['views'],
        }
        report['baseline_comparison'] = checks
        if not all(checks.values()):
            raise AssertionError(('Settlement framework changed production presentation', checks))
    if protection_manifest is not None:
        report['protection_diagnostic'] = protection_diagnostic(folder, protection_manifest)
    report['capture_png_sha256'] = {
        path.name: digest(path.read_bytes()) for path in sorted(folder.glob('*.png'))
    }
    (folder/'observations.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f"Captured {len(report['views'])} production views; "
          f"{production['active_file_count']} active input files; baseline "
          f"{'identical' if baseline is not None else 'recorded'}.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--baseline', type=Path,
                        help='Compare map/art and native pixels to a prior observations.json.')
    parser.add_argument('--protection-manifest', type=Path,
                        help='Add a separately labelled source-reservation diagnostic overlay.')
    args = parser.parse_args()
    capture(args.output, args.baseline, args.protection_manifest)
