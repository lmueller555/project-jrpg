"""Capture smooth Aether Lattice zoom using real, isolated game-menu input.

The disposable journey starts at rank 1 with no RP, Steps or crystals. Pillow
assembles rendered game frames into a GIF; game artwork is not altered.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'tools'))

import pygame
from PIL import Image
from preview_aether_lattice import LatticePreview


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'work/lattice-zoom')
    args = parser.parse_args(argv)
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    frames, timeline, captures, checks = [], [], [], []
    frame_number = 0

    with LatticePreview(rp=0, crystals=0) as preview:
        game, ui = preview.game, preview.game.lattice_ui
        before = (game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict())
        world_before = {'elapsed_ms': game.elapsed_ms, 'player': list(game.player.position)}

        def event(kind, **fields):
            pygame.event.post(pygame.event.Event(kind, **fields))
            if not game.handle_events():raise RuntimeError('The capture closed during input.')

        def run(seconds, stage):
            nonlocal frame_number
            for _ in range(max(1, math.ceil(seconds*60))):
                if not game.handle_events():raise RuntimeError('The capture closed during animation.')
                game.update(1/60)
                game.draw()
                if frame_number%2 == 0:
                    frame = Image.frombytes('RGB', game.window.get_size(), pygame.image.tobytes(game.window, 'RGB'))
                    frames.append(frame.resize((480, 320), Image.Resampling.NEAREST))
                    timeline.append({'frame': len(frames)-1, 'stage': stage, 'zoom': ui.zoom,
                                     'target_zoom': ui.target_zoom, 'camera': list(ui.pan),
                                     'selected': ui.selected, 'navigating': ui.navigating})
                frame_number += 1

        def record(name):
            game.draw()
            pygame.image.save(game.window, str(output/(name+'.png')))
            captures.append({'file': name+'.png', 'window': list(game.window.get_size()),
                             'text_scale': game.audio.text_scale, 'zoom': ui.zoom,
                             'target_zoom': ui.target_zoom, 'camera': list(ui.pan),
                             'selected': ui.selected})
            assert game.ui_surface.get_clip() == game.ui_surface.get_rect()

        def zoom_transition(stage, trigger):
            old_zoom, old_pan = ui.zoom, ui.pan.copy()
            trigger()
            target = ui.target_zoom
            assert math.isclose(ui.zoom, old_zoom, abs_tol=1e-10), (stage, ui.zoom, old_zoom)
            assert ui.pan == old_pan, stage
            run(1/12, stage+' — easing')
            intermediate = ui.zoom
            if not math.isclose(old_zoom, target):
                assert min(old_zoom, target) < intermediate < max(old_zoom, target), (stage, old_zoom, intermediate, target)
            run(.25, stage+' — settled')
            assert math.isclose(ui.zoom, target, abs_tol=1e-7), (stage, ui.zoom, target)
            checks.append({'stage': stage, 'start_zoom': old_zoom, 'target_zoom': target,
                           'zoom_after_83ms': intermediate, 'settled_zoom': ui.zoom})

        def repeated_key(key, count):
            for _ in range(count):preview.key(key)

        def repeated_click(rect, count):
            for _ in range(count):preview.click(rect.center)

        run(.25, 'selected node at 80%')
        zoom_transition('keyboard zoom out', lambda: repeated_key(pygame.K_MINUS, 3))
        zoom_transition('button zoom in', lambda: repeated_click(ui.zoom_in_rect, 5))
        record('zoomed_in')

        pointer = pygame.Vector2(ui.map_rect.center)+(63, -35)
        preview.hover(pointer)
        world_anchor = ui.pan+(pointer-pygame.Vector2(ui.map_rect.center))/ui.zoom
        old_zoom = ui.zoom
        event(pygame.MOUSEWHEEL, x=0, y=-2)
        assert math.isclose(ui.zoom, old_zoom, abs_tol=1e-10)
        errors = []
        for _ in range(18):
            run(1/60, 'wheel zoom — anchored to pointer')
            projected = pygame.Vector2(ui.map_rect.center)+(world_anchor-ui.pan)*ui.zoom
            errors.append(projected.distance_to(pointer))
        assert max(errors) < 1e-5, max(errors)
        checks.append({'stage': 'pointer anchored wheel zoom', 'logical_pointer': list(pointer),
                       'world_anchor': list(world_anchor), 'max_anchor_error_logical_pixels': max(errors),
                       'settled_zoom': ui.zoom})
        run(.15, 'pointer anchored zoom — settled')
        preview.hover((ui.map_rect.left+8, ui.map_rect.top-8))
        old_zoom, old_target = ui.zoom, ui.target_zoom
        event(pygame.MOUSEWHEEL, x=0, y=-2)
        preview.advance(.25)
        assert math.isclose(ui.zoom, old_zoom) and math.isclose(ui.target_zoom, old_target)
        checks.append({'stage': 'wheel outside the map leaves zoom unchanged', 'zoom': ui.zoom})

        zoom_transition('fit entire board', lambda: preview.click(ui.fit_rect.center))
        for identifier in ui.board.nodes:
            point = ui.node_position(identifier)
            assert ui.map_rect.inflate(-8, -8).collidepoint(point), (identifier, point)
        record('whole_lattice_overview')
        run(.4, 'whole lattice overview')
        zoom_transition('100% reset', lambda: preview.key(pygame.K_0))
        assert math.isclose(ui.zoom, 1.0)
        assert ui.node_position(ui.selected).distance_to(ui.map_rect.center) < 1e-5
        run(.2, 'selected node centered at 100%')

        event(pygame.KEYDOWN, key=pygame.K_RIGHT, repeat=False)
        run(.4, 'gold cursor exploration after zoom')
        cursor = ui.cursor_position.copy()
        nearest = min(ui.board.nodes, key=lambda identifier:
                      pygame.Vector2(ui.board.nodes[identifier]['position']).distance_squared_to(cursor))
        event(pygame.KEYUP, key=pygame.K_RIGHT)
        assert ui.selected == nearest
        run(.45, 'nearest selected node — centered and pulsing')
        assert ui.node_position(nearest).distance_to(ui.map_rect.center) < 1e-5
        checks.append({'stage': 'navigation after zoom', 'nearest_node': nearest,
                       'cursor_at_release': list(cursor), 'selected': ui.selected})

        preview.resize((480, 320), 1.5)
        preview.advance(.25)
        record('minimum_window_large_text')
        toolbar = (ui.zoom_out_rect, ui.zoom_in_rect, ui.fit_rect, ui.reset_zoom_rect)
        assert all(ui.map_rect.contains(rect) for rect in toolbar)
        assert all(not a.colliderect(b) for index, a in enumerate(toolbar) for b in toolbar[index+1:])
        assert before == (game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict())
        assert game.lattice.state()['position'] == 'origin'
        assert world_before == {'elapsed_ms': game.elapsed_ms, 'player': list(game.player.position)}

    durations = [40 if index%3 == 2 else 30 for index in range(len(frames))]
    frames[0].save(output/'zoom.gif', save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=True, disposal=1)
    with Image.open(output/'zoom.gif') as animation:encoded_frames = animation.n_frames
    sheet = Image.new('RGB', (480*3, 320*2))
    indices = (0, 14, 25, 45, 65, len(frames)-1)
    for cell, index in enumerate(indices):sheet.paste(frames[min(index, len(frames)-1)], ((cell%3)*480, (cell//3)*320))
    sheet.save(output/'contact_sheet.png')
    metadata = {'isolated_temporary_journey': True, 'normal_journey_untouched': True,
                'fixture': {'rank': 1, 'rp': 0, 'steps': 0, 'crystals': 0},
                'progression_unchanged': True, 'world_unchanged': True,
                'checks': checks, 'captures': captures,
                'animation': {'file': 'zoom.gif', 'rendered_frames': len(frames),
                              'encoded_frames': encoded_frames, 'fps': 30,
                              'logical_size': [480, 320], 'timeline': timeline}}
    (output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps({'output': str(output), 'rendered_frames': len(frames),
                      'encoded_frames': encoded_frames, 'gif_bytes': (output/'zoom.gif').stat().st_size}))
    return 0


if __name__ == '__main__':raise SystemExit(main())
