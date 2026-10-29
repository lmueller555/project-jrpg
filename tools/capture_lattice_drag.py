"""Capture direct camera dragging through disposable production-game input.

Pillow assembles the rendered frames. Normal journey and settings files are
never opened, and game artwork is unchanged.
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
    parser.add_argument('--output', type=Path, default=ROOT/'work/lattice-drag')
    output = parser.parse_args(argv).output
    output.mkdir(parents=True, exist_ok=True)
    frames, captures, checks, timeline = [], [], [], []
    frame_number = 0

    with LatticePreview(rp=0, crystals=0) as preview:
        game, ui = preview.game, preview.game.lattice_ui
        before = game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict()
        world = game.elapsed_ms, list(game.player.position)

        def event(kind, **fields):
            pygame.event.post(pygame.event.Event(kind, **fields))
            if not game.handle_events():raise RuntimeError('Capture closed during input.')

        def run(seconds, stage, animate=True):
            nonlocal frame_number
            for _ in range(max(1, math.ceil(seconds*60))):
                if not game.handle_events():raise RuntimeError('Capture closed during animation.')
                game.update(1/60);game.draw()
                if animate and frame_number%5 == 0:
                    frame = Image.frombytes('RGB', game.ui_surface.get_size(),
                                            pygame.image.tobytes(game.ui_surface, 'RGB'))
                    frames.append(frame.resize((480, 320), Image.Resampling.NEAREST))
                    timeline.append({'frame': len(frames)-1, 'stage': stage,
                                     'camera': list(ui.pan), 'zoom': ui.zoom,
                                     'selected': ui.selected, 'dragging': ui.dragging})
                frame_number += 1

        def record(name):
            game.draw();pygame.image.save(game.window, str(output/(name+'.png')))
            assert game.ui_surface.get_clip() == game.ui_surface.get_rect()
            captures.append({'file': name+'.png', 'window': list(game.window.get_size()),
                             'text_scale': game.audio.text_scale, 'map_rect': list(ui.map_rect),
                             'camera': list(ui.pan), 'zoom': ui.zoom, 'selected': ui.selected})

        def drag(displacement, label, save=False, animate=True):
            start = pygame.Vector2(ui.map_rect.center)+(48, -8)
            displacement = pygame.Vector2(displacement)
            camera = ui.pan.copy()
            grabbed = camera+(start-pygame.Vector2(ui.map_rect.center))/ui.zoom
            event(pygame.MOUSEBUTTONDOWN, button=1, pos=preview.point(start))
            errors = []
            for index in range(1, 13):
                point = start+displacement*index/12
                event(pygame.MOUSEMOTION, pos=preview.point(point), rel=(0, 0), buttons=(1, 0, 0))
                logical = pygame.Vector2(game.to_canvas(preview.point(point)))
                under_pointer = ui.pan+(logical-pygame.Vector2(ui.map_rect.center))/ui.zoom
                if logical.distance_to(start) >= 3:
                    errors.append(under_pointer.distance_to(grabbed))
                    assert errors[-1] < .001, (label, errors[-1])
                run(1/30, label+' — direct drag', animate)
            stationary = ui.pan.copy()
            run(.15, label+' — stationary hold', animate)
            assert ui.pan == stationary
            assert ui.cursor_position == ui.pan
            if save:record('during_drag')
            nearest = ui._nearest_node(ui.cursor_position)
            event(pygame.MOUSEBUTTONUP, button=1, pos=preview.point(point))
            assert ui.selected == nearest and not ui.navigating
            assert ui.pan == stationary
            target = pygame.Vector2(ui.board.nodes[nearest]['position'])
            run(.1, label+' — smooth release centering', animate)
            intermediate = ui.pan.copy()
            run(.45, label+' — selected pulse', animate)
            assert ui.node_position(nearest).distance_to(ui.map_rect.center) < .001
            if stationary.distance_to(target) > .001:
                assert intermediate != stationary
                assert intermediate.distance_to(target) < stationary.distance_to(target)
            checks.append({'stage': label, 'window': list(game.window.get_size()),
                           'zoom': ui.zoom, 'logical_displacement': list(displacement),
                           'grabbed_world': list(grabbed), 'maximum_anchor_error': max(errors),
                           'stationary_hold_camera_unchanged': True,
                           'camera_at_release': list(stationary),
                           'camera_after_100ms': list(intermediate),
                           'centered_node': nearest, 'centered_camera': list(ui.pan)})

        preview.select_node('brace_01')
        ui.reset_zoom();preview.advance(.25)
        preview.wheel(ui.map_rect.center, -3)
        run(.3, 'before dragging')
        record('before_drag')
        drag((-72, 24), 'normal window left and down', save=True)
        record('after_release')
        drag((60, -24), 'normal window right and up')

        preview.resize((1440, 810))
        ui.reset_zoom();preview.advance(.25)
        drag((-48, -12), 'letterboxed window at 100 percent', animate=False)
        preview.resize((480, 320), 1.5)
        ui.fit_board();preview.advance(.25)
        drag((24, 12), 'minimum window with large text', animate=False)
        record('minimum_window_large_text')
        assert before == (game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict())
        assert world == (game.elapsed_ms, list(game.player.position))
        assert game.lattice.state()['position'] == 'origin'

    durations = [80 if index%3 else 90 for index in range(len(frames))]
    frames[0].save(output/'camera_drag.gif', save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=1)
    with Image.open(output/'camera_drag.gif') as animation:encoded_frames = animation.n_frames
    metadata = {'isolated_temporary_journey': True, 'normal_journey_untouched': True,
                'fixture': {'rank': 1, 'rp': 0, 'steps': 0, 'crystals': 0},
                'progression_unchanged': True, 'world_unchanged': True,
                'checks': checks, 'captures': captures,
                'animation': {'file': 'camera_drag.gif', 'fps': 12,
                              'logical_size': [480, 320], 'rendered_frames': len(frames),
                              'encoded_frames': encoded_frames, 'timeline': timeline}}
    (output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps({'output': str(output), 'checks': len(checks),
                      'rendered_frames': len(frames), 'encoded_frames': encoded_frames,
                      'gif_bytes': (output/'camera_drag.gif').stat().st_size}))
    return 0


if __name__ == '__main__':raise SystemExit(main())
