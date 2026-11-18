"""Review the staged mechanism using its actual deterministic controller.

Operation GIFs are offline previews, not live gameplay. Native town stills use
a disposable initialized Game and substitute only the well's in-memory drawing.
No operator/actor performance or new live interaction is claimed here.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from hashlib import sha256
import json
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

from PIL import Image, ImageChops, ImageDraw, ImageSequence
import pygame

from well_mechanism import WellMechanism
from well_mechanism_presentation import WellMechanismPresentation
from tools.capture_eldenmere_well_pack import (
    check_preserved, font, read, review_board, checker,
)
from tools.capture_eldenmere_settlement_framework import (
    Game, canonical, meaningful_state, production_snapshot,
)

OUTPUT = ROOT/'docs/reviews/eldenmere_well_mechanism'
BASELINE = ROOT/'docs/reviews/eldenmere_well_pack/production_before.json'
MANIFEST = ROOT/'assets/terrain/eldenmere/well_hd/mechanism/manifest.json'
GATES = {'await_loading': 'loading', 'await_operator': 'operator', 'await_retrieval': 'loading'}


def digest(raw):
    return sha256(raw).hexdigest()


def plain(value):
    return value.to_dict() if hasattr(value, 'to_dict') else asdict(value) if is_dataclass(value) else value


def operation_trace(step_seconds=.05):
    """Drive real controller time; disclose synthetic readiness at walk gates."""
    model = WellMechanism(); token = model.reserve('offline.operator', 'canonical.gardener.pail')
    if token is None: raise AssertionError('The available well rejected its preview operator')
    trace = []; gate_phase = None; gate_ms = 0; preview_ms = 0
    for _ in range(2000):
        snapshot = model.snapshot()
        events = model.drain_events()
        trace.append({'preview_ms': round(preview_ms, 6), 'state': plain(snapshot),
                      'events': [plain(event) for event in events]})
        if snapshot.completed: break
        if snapshot.phase_id in GATES:
            if gate_phase != snapshot.phase_id:
                gate_phase = snapshot.phase_id; gate_ms = 0
            if gate_ms >= 500:
                if not model.signal_ready(token, GATES[snapshot.phase_id]):
                    raise AssertionError('The agreed station readiness was rejected')
                gate_phase = None; gate_ms = 0
            else:
                model.update(step_seconds); gate_ms += step_seconds*1000
        else:
            model.update(step_seconds)
        preview_ms += step_seconds*1000
    else:
        raise AssertionError('The staged controller did not complete the preview operation')
    return trace


def preview_frame(picture, state, preview_ms, *, reduced=False):
    board = Image.new('RGB', (318, 488), '#172b27'); draw = ImageDraw.Draw(board)
    draw.text((12, 10), 'STAGED WELL / OFFLINE', font=font(18), fill='#f2e8c9')
    draw.text((12, 36), 'Actor-held pail omitted. Not gameplay.', font=font(11), fill='#cad6c5')
    enlarged = picture.resize((288, 352), Image.Resampling.NEAREST)
    background = checker(enlarged.size); background.paste(enlarged, (0, 0), enlarged)
    board.paste(background, (15, 62))
    rows = (f"{state['phase_id']}  {state['phase_progress']:.2f}",
            f"Pail: {state['pail_owner']} | water {state['water_units']}/6 | crank {state['crank_sample']:02}",
            f"{preview_ms/1000:.2f}s | "+('reduced ambient' if reduced else 'normal ambient'))
    for index, text in enumerate(rows):
        draw.text((12, 426+index*19), text, font=font(12), fill='#f2e8c9')
    return board


def animated_previews(folder, trace, renderer):
    normal = []; reduced = []; phase_samples = {}
    for record in trace:
        state = record['state']; time = record['preview_ms']
        image = renderer.render(state, time, False)
        normal.append(preview_frame(image, state, time))
        reduced.append(preview_frame(renderer.render(state, time, True), state, time, reduced=True))
        phase = state['phase_id']
        if phase not in phase_samples or (phase not in GATES and state['phase_progress'] <= .55):
            phase_samples[phase] = record
    # Repeat the stable completion arrangement briefly, preserving real time.
    normal.extend([normal[-1]]*8); reduced.extend([reduced[-1]]*8)
    # A shared GIF palette permits true delta frames and bounded review files.
    # Native PNGs remain the color/alpha reference, as for other sprite reviews.
    palette = normal[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    normal_indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in normal]
    reduced_indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in reduced]
    for name, frames, delay in (('operation_normal.gif', normal_indexed, 50),
                                ('operation_half_speed.gif', normal_indexed, 100),
                                ('operation_reduced_motion.gif', reduced_indexed, 50)):
        frames[0].save(folder/name, save_all=True, append_images=frames[1:], duration=delay,
                       loop=0, disposal=1, optimize=True)
        with Image.open(folder/name) as saved:
            actual = sum(frame.info.get('duration', 0) for frame in ImageSequence.Iterator(saved))
        if actual != len(frames)*delay:
            raise AssertionError(('Saved GIF timing differs from its controller preview', name, actual))
    columns = 4; card = (300, 420); phases = list(phase_samples)
    sheet = Image.new('RGB', (columns*card[0], 70+((len(phases)+columns-1)//columns)*card[1]), '#172b27')
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 10), 'STAGED / numbered controller phases', font=font(23), fill='#f2e8c9')
    draw.text((12, 42), 'Actual operation samples; no moving gardener or live town integration is claimed.', font=font(13), fill='#cad6c5')
    for index, name in enumerate(phases):
        record = phase_samples[name]; x = (index % columns)*card[0]; y = 70+(index//columns)*card[1]
        image = renderer.render(record['state'], record['preview_ms']).resize((288, 352), Image.Resampling.NEAREST)
        background = checker(image.size); background.paste(image, (0, 0), image)
        sheet.paste(background, (x+6, y+35))
        draw.text((x+8, y+6), f'{index+1:02}. {name}', font=font(14), fill='#f2e8c9')
        draw.text((x+8, y+393), f"{record['preview_ms']/1000:.2f}s | {record['state']['pail_owner']}", font=font(12), fill='#cad6c5')
    sheet.save(folder/'numbered_phases.png')
    return phase_samples


def town_stills(folder, renderer, samples):
    with tempfile.TemporaryDirectory(prefix='well-mechanism-offline-') as directory:
        temporary = Path(directory)
        game = Game(fullscreen=False, window_size=(960, 640), start_on_title=True,
                    save_path=temporary/'journey.json', settings_path=temporary/'settings.json')
        try:
            game.on_title = False; game.opening.restore({'version': 1, 'stage': 'disabled'})
            game.opening_fade = game.transfer_cooldown = 0; game.world = game.town
            game.audio.set_music(0); game.audio.set_effects(0)
            game.player.position.update((576, 914)); game.player.facing = 'front'
            game.player.moving = game.player.running = False; game.player.walk_ms = 0
            game.location_label = None; game.location_seconds = 0; game.saves.notice_seconds = 0
            game.camera.reset(); game.camera.focus((528, 850), duration=0); game.elapsed_ms = 0
            original_data = deepcopy(game.town.data); initial = canonical(meaningful_state(game))
            record = next(item for item in game.town.entities if item['id'] == 'well')
            record['position'] = [492, 800]
            files = []
            for phase in ('attach', 'guide_into_shaft', 'lower', 'fill', 'raise', 'secure'):
                sample = samples[phase]; image = renderer.render(sample['state'], sample['preview_ms'])
                raw = pygame.image.frombytes(image.tobytes(), image.size, 'RGBA')
                from rendering import record_art
                artwork = record_art(raw, {'artwork_pixels_per_world_pixel': 2, 'logical_size': [72, 88]})
                game.town.well.sprite = lambda elapsed_ms, artwork=artwork: artwork
                record['rect'] = artwork.get_rect(topleft=record['position'])
                game.draw()
                picture = Image.frombytes('RGB', game.window.get_size(), pygame.image.tobytes(game.window, 'RGB'))
                filename = 'town_'+phase+'.png'
                review_board(picture, 'OFFLINE CONTROLLER COMPOSITE / '+phase,
                             'Native town backdrop; stationary fixture. No live operator, gameplay activation or actor-depth claim.').save(folder/filename)
                files.append(filename)
            if game.town.data != original_data or canonical(meaningful_state(game)) != initial:
                raise AssertionError('Offline composition mutated map data or gameplay progress')
            return {'files': files, 'native_scene_size': [960, 640], 'no_game_updates': True,
                    'no_live_operator_performance_claim': True, 'in_memory_data_and_progress_preserved': True}
        finally:
            game.music.stop(); pygame.quit()


def capture(folder=OUTPUT):
    folder.mkdir(parents=True, exist_ok=True)
    baseline = read(BASELINE); check_preserved(baseline)
    production = production_snapshot(); manifest_raw = MANIFEST.read_bytes()
    implementation_paths = ('well_mechanism.py', 'well_mechanism_presentation.py',
                            'tools/build_eldenmere_well_mechanism.py',
                            'tools/capture_eldenmere_well_mechanism.py',
                            'assets/source/terrain/eldenmere/well_hd/mechanism/contract.json')
    implementation_hashes = {path: digest((ROOT/path).read_bytes()) for path in implementation_paths}
    renderer = WellMechanismPresentation(); trace = operation_trace()
    samples = animated_previews(folder, trace, renderer)
    context = town_stills(folder, renderer, samples)
    check_preserved(baseline)
    if production_snapshot() != production:
        raise AssertionError('Live production files changed during mechanism preview')
    if implementation_hashes != {path: digest((ROOT/path).read_bytes()) for path in implementation_paths}:
        raise AssertionError('A controller, renderer or review source changed during capture')
    (folder/'trace.json').write_text(json.dumps({'schema_version': 1,
        'fixture': 'Actual controller at50ms,500msreadinessholds,syntheticoperatorready; no actor/Game operation.',
        'step_ms': 50, 'samples': trace}, indent=2)+'\n')
    report = {'scope': 'Staged controller-driven offline mechanism preview, not live gameplay.',
              'runtime_integration': False,
              'capture_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'working_tree_dirty_at_capture': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)),
              'mechanism_manifest_sha256': digest(manifest_raw),
              'helper_sha256': digest(Path(__file__).read_bytes()),
              'implementation_sha256': implementation_hashes,
              'baseline_revision': baseline['revision'], 'active_files_preserved': production['active_file_count'],
              'protected_files_preserved': len(baseline['protected_files']),
              'trace_samples': len(trace), 'trace_duration_ms': trace[-1]['preview_ms'],
              'phases': list(samples), 'events': [event for item in trace for event in item['events']],
              'town_composites': context, 'cache': renderer.cache_info(),
              'output_sha256': {path.name: digest(path.read_bytes()) for path in sorted(folder.iterdir())
                                if path.suffix in ('.png', '.gif', '.json') and path.name != 'observations.json'}}
    (folder/'observations.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f"Staged mechanism review: {len(trace)} actual controller samples; {production['active_file_count']} active files preserved.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('output', nargs='?', type=Path, default=OUTPUT)
    capture(parser.parse_args().output.resolve())
