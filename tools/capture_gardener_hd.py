"""Capture native in-game poses from the uninterrupted sanctuary gardener routine."""
import argparse
import os
from pathlib import Path
import random
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from main import Game
from npc_routines import Gardener

CAPTURES = (
    ('rest', 0, 'At rest'), ('pickup', 230, 'Picking up the pail'),
    ('to_well', 200, 'Carrying the empty pail'),
    ('well_attach', 420, 'Hooking on the pail'),
    ('well_lower', 190, 'Lowering the pail'),
    ('well_raise', 580, 'Raising the full pail'),
    ('well_take', 500, 'Taking back the pail'),
    ('return_to_sanctuary', 350, 'Carrying the full pail'),
    ('water_west_flowers', 650, 'Pouring at the flowers'),
)


def capture(path):
    game = Game(fullscreen=False, start_on_title=False)
    world = game.town
    index = next(i for i, n in enumerate(world.npcs) if n.data['id'] == 'sanctuary_gardener')
    gardener = world.npcs[index] = Gardener(world.npcs[index].data, world, random.Random(834))
    game.player.position.update(520, 520)
    shots = {}
    times = {}
    for _ in range(100 * 60):
        state = gardener.state
        times[state] = times.get(state, 0) + 1000 / 60
        for capture_state, elapsed, label in CAPTURES:
            if state != capture_state or label in shots or times[state] < elapsed:
                continue
            camera = (max(0, min(world.size[0]-480, int(gardener.position.x)-100)),
                      max(0, min(world.size[1]-320, int(gardener.position.y)-120)))
            rel = gardener.position - pygame.Vector2(camera)
            world.draw(game.canvas, camera, game.player, game.elapsed_ms, include_ui=False)
            surface = game.canvas.native.subsurface(
                (int(rel.x-55)*2, int(rel.y-90)*2, 220, 206))
            shots[label] = Image.frombytes('RGB', surface.get_size(),
                                          pygame.image.tobytes(surface, 'RGB'))
        if len(shots) == len(CAPTURES):
            break
        step = gardener.rest_remaining_ms / 1000 + 1/60 if state == "rest" else 1/60
        game.update(step, (0, 0), False)
    assert len(shots) == len(CAPTURES), list(shots)
    sheet = Image.new('RGB', (660, 684), '#26372e')
    draw = ImageDraw.Draw(sheet)
    for i, (_, _, label) in enumerate(CAPTURES):
        x, y = i % 3 * 220, i // 3 * 228
        sheet.paste(shots[label], (x, y))
        draw.text((x + 5, y + 208), label, fill='#e8eadc')
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    pygame.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=ROOT/'docs/reviews/gardener_roster_hd/live_sequence.png')
    capture(parser.parse_args().output)
