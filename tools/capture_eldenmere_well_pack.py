"""Review the staged well pack without activating it in a live map.

The proposed town images are OFFLINE STATIC ASSET COMPOSITES. A disposable Game
renders its ordinary town, residents and Caelan; only the in-memory well drawing
and its draw origin are replaced. No mechanism, actor animation, collision,
interaction or runtime integration is established by these pictures.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageChops, ImageDraw, ImageFont, PngImagePlugin
import pygame

from tools.capture_eldenmere_settlement_framework import (
    Game, canonical, meaningful_state, production_snapshot,
)

PACK = ROOT/'assets/terrain/eldenmere/well_hd'
DEFAULT_OUTPUT = ROOT/'docs/reviews/eldenmere_well_pack'
PLAYER = (576, 914)
FOCUS = (528, 850)


def read(path):
    return json.loads(Path(path).read_text())


def digest(raw):
    return sha256(raw).hexdigest()


def font(size=16):
    try:
        return ImageFont.truetype('DejaVuSans.ttf', size)
    except OSError:
        return ImageFont.load_default()


def normalized_baseline(raw):
    return {
        'revision': raw.get('revision', raw.get('git_commit')),
        'production': raw['production'],
        'protected_files': {
            **raw.get('protected_files', {}),
            **raw.get('preserved_implementation_sha256', {}),
        },
    }


def check_preserved(baseline):
    if production_snapshot() != baseline['production']:
        raise AssertionError('Active town files or map metadata differ from the pre-pack baseline')
    changed = [name for name, expected in baseline['protected_files'].items()
               if not (ROOT/name).is_file() or digest((ROOT/name).read_bytes()) != expected]
    if changed:
        raise AssertionError(('Legacy well/gardener/runtime source changed', changed))


def checker(size, cell=8):
    picture = Image.new('RGB', size, '#d8d9d0')
    painter = ImageDraw.Draw(picture)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x//cell+y//cell) % 2:
                painter.rectangle((x, y, x+cell-1, y+cell-1), fill='#bec2b8')
    return picture


def asset(record):
    path = record['file'] if isinstance(record, dict) else record
    with Image.open(PACK/path) as raw:
        return raw.convert('RGBA')


def save_raw(picture, path, description):
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text('Description', description)
    picture.save(path, pnginfo=metadata)


def review_board(picture, title, subtitle):
    board = Image.new('RGB', (picture.width, picture.height+70), '#172b27')
    painter = ImageDraw.Draw(board)
    painter.text((14, 8), title, font=font(18), fill='#f2e8c9')
    painter.text((14, 36), subtitle, font=font(13), fill='#cad6c5')
    board.paste(picture, (0, 70))
    return board


def component_sheet(records, filename, folder, title, *, masks=False):
    columns = min(3, max(1, len(records)))
    card_width, card_height = 330, 430
    rows = math.ceil(len(records)/columns)
    board = Image.new('RGB', (columns*card_width, 74+rows*card_height), '#172b27')
    painter = ImageDraw.Draw(board)
    painter.text((14, 10), title, font=font(20), fill='#f2e8c9')
    painter.text((14, 40), 'STAGED / diagnostic sheet; artwork shown at 2x native export pixels',
                 font=font(13), fill='#cad6c5')
    for index, record in enumerate(records):
        x, y = (index % columns)*card_width, 74+(index//columns)*card_height
        picture = asset(record)
        if masks:
            # Exported masks are data. White means covered; black means clear.
            with Image.open(PACK/record['file']) as raw:
                coverage = raw.getchannel('A') if raw.mode == 'RGBA' else raw.convert('L')
            picture = Image.merge('RGBA', (coverage, coverage, coverage, Image.new('L', coverage.size, 255)))
        enlarged = picture.resize((picture.width*2, picture.height*2), Image.Resampling.NEAREST)
        surface = checker(enlarged.size)
        surface.paste(enlarged, mask=enlarged.getchannel('A'))
        board.paste(surface, (x+(card_width-surface.width)//2, y+38))
        painter.text((x+12, y+8), record['id'], font=font(16), fill='#f2e8c9')
        painter.text((x+12, y+card_height-20), f"{picture.width}x{picture.height} artwork pixels", font=font(12), fill='#cad6c5')
    board.save(folder/filename)


def pail_sheet(manifest, folder):
    variants = manifest['pail']['variants']
    if [item['units'] for item in variants] != list(range(7)):
        raise AssertionError('Review requires canonical pail levels zero through six')
    width, height = 112, 260
    board = Image.new('RGB', (max(784, width*len(variants)), 70+height), '#172b27')
    painter = ImageDraw.Draw(board)
    painter.text((14, 10), 'STAGED PAIL / seven static fill variants', font=font(20), fill='#f2e8c9')
    painter.text((14, 40), 'Upper: 4x native inspection. Lower: native 24x36 artwork pixels. Not an animation.',
                 font=font(12), fill='#cad6c5')
    for index, item in enumerate(variants):
        picture = asset(item)
        if picture.size != tuple(manifest['pail']['artwork_size']):
            raise AssertionError(('Pail canvas changed', item))
        enlarged = picture.resize((picture.width*4, picture.height*4), Image.Resampling.NEAREST)
        surface = checker(enlarged.size)
        surface.paste(enlarged, mask=enlarged.getchannel('A'))
        x = index*width
        board.paste(surface, (x+(width-surface.width)//2, 110))
        painter.text((x+width//2-14, 82), f"{item['units']}/6", font=font(16), fill='#f2e8c9')
        native = checker(picture.size, 4)
        native.paste(picture, mask=picture.getchannel('A'))
        board.paste(native, (x+(width-picture.width)//2, 276))
    board.save(folder/'pail_fill_variants.png')
    return {'variant_units': [item['units'] for item in variants],
            'logical_size': manifest['pail']['logical_size'],
            'artwork_size': manifest['pail']['artwork_size'],
            'grip_logical': manifest['pail']['grip_logical']}


def geometry_sheet(manifest, folder):
    assembly = manifest['assembly'];picture = asset(assembly)
    scale = 3
    enlarged = picture.resize((picture.width*scale, picture.height*scale), Image.Resampling.NEAREST)
    board = Image.new('RGB', (1040, 760), '#172b27')
    board.paste(checker(enlarged.size, 12), (18, 82))
    board.paste(enlarged, (18, 82), enlarged.getchannel('A'))
    painter = ImageDraw.Draw(board)
    painter.text((14, 10), 'STAGED GEOMETRY / source registration targets', font=font(21), fill='#f2e8c9')
    painter.text((14, 42), '3x native inspection; coloured lines are diagnostics, not new ground or collision.',
                 font=font(14), fill='#cad6c5')
    origin = assembly['world_position']
    support = read(ROOT/'assets/maps/eldenmere/well_square/layout.json')['well_ground_rect']
    local = [support[0]-origin[0], support[1]-origin[1], support[2], support[3]]
    factor = scale*2
    x, y, w, h = local
    painter.rectangle((18+x*factor, 82+y*factor, 18+(x+w)*factor-1, 82+(y+h)*factor-1),
                      outline='#f6c85f', width=2)
    ground_anchor = assembly['ground_anchor_logical']
    ax, ay = ground_anchor;px, py = 18+ax*factor, 82+ay*factor
    painter.line((px-8, py, px+8, py), fill='#74e4e3', width=2)
    painter.line((px, py-8, px, py+8), fill='#74e4e3', width=2)
    lines = (
        'Native artwork: '+str(assembly['artwork_size']),
        'Logical canvas: '+str(assembly['logical_size']),
        'Proposed draw origin: '+str(origin),
        'Draw anchor, logical: '+str(assembly['draw_anchor_logical']),
        'Ground anchor, logical: '+str(ground_anchor),
        'Canonical support, world: '+str(support),
        'Support in new canvas: '+str(local),
        '',
        'Gold: retained physical support target',
        'Cyan: declared ground registration anchor',
        '',
        'The live map, support and navigation are unchanged.',
        'Operator poses and per-layer runtime depth follow in later PRs.',
    )
    for index, line in enumerate(lines):
        painter.text((520, 110+index*31), line, font=font(14), fill='#f2e8c9' if index < 7 else '#cad6c5')
    geometry = manifest['geometry']
    anchors = geometry.get('anchors_logical', {})
    for name, point in anchors.items():
        px, py = 18+point[0]*factor, 82+point[1]*factor
        painter.ellipse((px-3, py-3, px+3, py+3), fill='#ffb080', outline='#172b27')
    for item in geometry.get('stations', []):
        point = item['feet_local_logical']
        px, py = 18+point[0]*factor, 82+point[1]*factor
        painter.line((px-7, py, px+7, py), fill='#b8b2ff', width=2)
        painter.line((px, py-7, px, py+7), fill='#b8b2ff', width=2)
        painter.text((px+10, py-8), item['id']+' feet target', font=font(12), fill='#d5d1ff')
    painter.text((520, 610), 'Orange: mechanism anchor targets', font=font(14), fill='#ffb080')
    painter.text((520, 640), 'Violet: future operator feet targets', font=font(14), fill='#d5d1ff')
    board.save(folder/'geometry_diagnostic.png')
    return {'canonical_support_world': support, 'proposed_support_local': local,
            'source_assembly': assembly, 'mechanism_anchors_logical': anchors,
            'future_stations': geometry.get('stations', [])}


def town_composite(manifest, folder):
    assembly = manifest['assembly']
    with tempfile.TemporaryDirectory(prefix='well-pack-review-') as directory:
        temporary = Path(directory)
        game = Game(fullscreen=False, window_size=(960, 640), start_on_title=True,
                    save_path=temporary/'journey.json', settings_path=temporary/'settings.json')
        try:
            game.on_title = False
            game.opening.restore({'version': 1, 'stage': 'disabled'})
            game.opening_fade = game.transfer_cooldown = 0
            game.audio.set_music(0);game.audio.set_effects(0)
            game.world = game.town
            if not game.town.can_stand(PLAYER):
                raise AssertionError(('Player scale fixture is blocked', PLAYER))
            game.player.position.update(PLAYER);game.player.facing = 'front'
            game.player.moving = game.player.running = False;game.player.walk_ms = 0
            game.location_label = None;game.location_seconds = 0;game.saves.notice_seconds = 0
            game.elapsed_ms = 0;game.camera.reset();game.camera.focus(FOCUS, duration=0)
            state = canonical(meaningful_state(game))
            original_data = deepcopy(game.town.data)
            record = next(item for item in game.town.entities if item['id'] == 'well')
            old_position = list(record['position'])
            old_size = list(game.town.well.sprite(0).get_size())

            def shot():
                game.draw()
                if game.window.get_size() != (960, 640):
                    raise AssertionError('Town review must retain the complete native scene')
                return Image.frombytes('RGB', game.window.get_size(), pygame.image.tobytes(game.window, 'RGB'))

            before = shot()
            save_raw(before, folder/'town_live_baseline_native.png',
                     'Unmodified production town, initialized Game fixture at native 960x640.')
            proposed = game.town.art_image((PACK/assembly['file']).relative_to(ROOT).as_posix(),
                                           {'artwork_pixels_per_world_pixel': 2,
                                            'logical_size': assembly['logical_size']})
            game.town.well.sprite = lambda elapsed_ms: proposed
            record['position'] = list(assembly['world_position'])
            record['rect'] = proposed.get_rect(topleft=record['position'])
            # Keep the established overall sort baseline for this scale study.
            # Future runtime integration must separately establish each layer's depth.
            after = shot()
            save_raw(after, folder/'town_proposed_native.png',
                     'OFFLINE STATIC ASSET COMPOSITE. In-memory staged drawing replacement; not integrated gameplay.')
            camera = list(game.camera.position())
            allowed = Image.new('L', before.size)
            painter = ImageDraw.Draw(allowed)
            for position, size in ((old_position, old_size), (assembly['world_position'], assembly['logical_size'])):
                x, y = (position[i]-camera[i] for i in range(2));w, h = size
                painter.rectangle((round(x*2), round(y*2), round((x+w)*2)-1, round((y+h)*2)-1), fill=255)
            difference = ImageChops.difference(before, after)
            channels = difference.split()
            changed_mask = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2]).point(
                lambda value: 255 if value else 0)
            changed = changed_mask.histogram()[255]
            outside = ImageChops.multiply(changed_mask, ImageChops.invert(allowed)).histogram()[255]
            if not changed or outside:
                raise AssertionError(('Proposed composite changed outside well drawing bounds', changed, outside))
            if game.town.data != original_data or canonical(meaningful_state(game)) != state:
                raise AssertionError('Offline preview mutated world data or gameplay progress')
            board = review_board(after, 'OFFLINE ASSET COMPOSITE / proposed Eldenmere well',
                                 'Staged artwork in the native town view. Live collision, actors and game selection remain unchanged.')
            board.save(folder/'town_proposed_review.png')
            comparison = Image.new('RGB', (1920, 710), '#172b27')
            comparison.paste(review_board(before, 'CURRENT LIVE WELL / production baseline',
                                         'Native 960x640 initialized-Game view; unchanged town and Caelan.'), (0, 0))
            comparison.paste(review_board(after, 'PROPOSED WELL / offline static composite',
                                         'Native 960x640; only the disposable in-memory well drawing is replaced.'), (960, 0))
            comparison.save(folder/'town_before_after.png')
            return {'fixture': 'Initialized production Game; disposable saves/settings; opening disabled; no updates or seeded quests.',
                    'review_kind': 'offline_static_asset_composite', 'runtime_integration': False,
                    'native_scene_size': list(before.size), 'player_logical': list(PLAYER),
                    'camera_focus_logical': list(FOCUS), 'camera_logical': camera,
                    'old_draw_position': old_position, 'old_canvas_logical': old_size,
                    'new_draw_position': assembly['world_position'], 'new_canvas_logical': assembly['logical_size'],
                    'changed_native_pixels': changed, 'changed_outside_well_canvas_union': outside,
                    'same_town_actors_ground_buildings_and_player': True,
                    'in_memory_map_metadata_and_progress_unchanged': True,
                    'limits': 'Static scale/projection review only. Mechanism timing, operator poses, per-layer actor depth and gameplay integration are not demonstrated.'}
        finally:
            game.music.stop();pygame.quit()


def capture(folder, baseline_file=None):
    baseline_path = baseline_file or folder/'production_before.json'
    if not baseline_path.is_file():
        raise ValueError('Provide --baseline-file from the clean pre-pack source snapshot for the first capture')
    baseline = normalized_baseline(read(baseline_path))
    check_preserved(baseline)
    manifest = read(PACK/'manifest.json')
    folder.mkdir(parents=True, exist_ok=True)
    report = {
        'purpose': 'Staged well/pail art review, with offline town compositing and exact live-source preservation proof.',
        'baseline_revision': baseline['revision'],
        'capture_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'working_tree_dirty_at_capture': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)),
        'revision_note': 'HEAD identifies the checkout base. The staged manifest, helper and PNG hashes identify the actual reviewed bytes, including uncommitted pack work.',
        'staged_manifest': (PACK/'manifest.json').relative_to(ROOT).as_posix(),
        'staged_manifest_sha256': digest((PACK/'manifest.json').read_bytes()),
        'capture_helper_sha256': digest(Path(__file__).read_bytes()),
        'runtime_integration': False,
    }
    report['town_composite'] = town_composite(manifest, folder)
    component_sheet(manifest['layers'], 'layer_breakdown.png', folder, 'STAGED WELL / authored layer breakdown')
    component_sheet(manifest['masks'], 'mask_breakdown.png', folder, 'STAGED WELL / authored coverage masks', masks=True)
    report['pail'] = pail_sheet(manifest, folder)
    report['geometry'] = geometry_sheet(manifest, folder)
    check_preserved(baseline)
    report['preservation'] = {
        'active_file_count': baseline['production']['active_file_count'],
        'protected_implementation_files': len(baseline['protected_files']),
        'all_active_files_and_map_fields_identical': True,
        'all_protected_source_files_identical': True,
        'collision_navigation_and_runtime_well_unchanged': True,
    }
    report['capture_png_sha256'] = {path.name: digest(path.read_bytes()) for path in sorted(folder.glob('*.png'))}
    (folder/'production_before.json').write_text(json.dumps(baseline, indent=2)+'\n')
    (folder/'observations.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Staged well pack review:', len(report['capture_png_sha256']), 'PNG witnesses;',
          report['preservation']['active_file_count'], 'active files preserved.')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--baseline-file', type=Path)
    arguments = parser.parse_args()
    capture(arguments.output.resolve(), arguments.baseline_file.resolve() if arguments.baseline_file else None)
