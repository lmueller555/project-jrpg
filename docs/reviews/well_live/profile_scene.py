"""Reproduce this review's draw comparison against either repository checkout.

Usage: python profile_scene.py CHECKOUT OUTPUT.json
This temporary-save fixture times production World.draw, not updates or PNG
conversion. It imports Game from the explicitly supplied checkout.
"""
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
import tempfile
import time
from hashlib import sha256

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT))
import pygame
from main import Game


def describe(values):
    ordered = sorted(values)
    return {'samples':len(values), 'min_ms':min(values), 'mean_ms':statistics.mean(values),
            'median_ms':statistics.median(values), 'p95_ms':ordered[min(len(ordered)-1, int(.95*len(ordered)))],
            'max_ms':max(values)}


def draw(game):
    start = time.perf_counter()
    game.canvas.reset_detail()
    game.world.draw(game.canvas, (288, 660), game.player, game.elapsed_ms, include_ui=False)
    return (time.perf_counter()-start)*1000


def profile(game, actor):
    first = draw(game)
    stable = describe([draw(game) for _ in range(30)])
    moving = []
    phase = actor.state
    for _ in range(30):
        game.update(1/60, (0, 0), False)
        moving.append(draw(game))
    result = {'actor_state_start':phase, 'actor_state_end':actor.state,
              'first_draw_ms':first, 'warm_static':stable, 'moving_draw':describe(moving)}
    if hasattr(game.town.well, 'cache_info'):
        result['well_cache'] = game.town.well.cache_info()
    return result


sources = ['main.py', 'npc_routines.py', 'well_routine.py', 'rendering.py',
           'well_live_presentation.py', 'gardener_well_runtime.py']
before = {p:sha256((ROOT/p).read_bytes()).hexdigest() for p in sources if (ROOT/p).is_file()}
with tempfile.TemporaryDirectory(prefix='well-profile-') as temporary:
    temporary = Path(temporary)
    game = Game(fullscreen=False, start_on_title=False,
                save_path=temporary/'save.json', settings_path=temporary/'settings.json')
    game.opening.stage = 'disabled'
    game.player.position.update(520, 520)
    actor = next(a for a in game.town.npcs if a.data['id']=='sanctuary_gardener')
    actor._rng = random.Random(2026)
    actor.rest_duration_ms = actor._new_rest_duration()
    report = {'root':str(ROOT),
              'revision':subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'native_size':list(game.canvas.native.get_size()), 'camera_logical':[288, 660],
              'iterations':30,
              'initial_rest_rng_seed':2026,
              'timing_scope':'Production World.draw including native buffer reset; updates, image conversion, UI and display presentation excluded; hardware specific.',
              'source_sha256':before,
              'driver_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
    report['idle'] = profile(game, actor)
    game.update(actor.rest_remaining_ms/1000+1/60, (0, 0), False)
    for _ in range(6000):
        if actor.state == 'well_lower':break
        game.update(1/60, (0, 0), False)
    else:raise AssertionError('Could not reach actual well_lower: '+actor.state)
    report['lower'] = profile(game, actor)
    game.music.stop()
    pygame.quit()
for relative, expected in before.items():
    if sha256((ROOT/relative).read_bytes()).hexdigest() != expected:
        raise AssertionError('Source changed during profiling: '+relative)
Path(sys.argv[2]).write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({key:report[key] for key in ('revision', 'idle', 'lower')}, indent=2))
