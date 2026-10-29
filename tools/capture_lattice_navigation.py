"""Capture free Aether Lattice exploration using real paused-menu input.

The disposable journey starts at rank 1 with no Steps or crystals. No normal
journey/settings file is read or written. Pillow assembles rendered game frames
into a GIF; it does not generate or alter the game's artwork.
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
    parser.add_argument('--output', type=Path, default=ROOT/'work/lattice-navigation')
    args = parser.parse_args(argv)
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    frames, timeline, selections, captures = [], [], [], []
    frame_number = 0

    with LatticePreview(rp=0, crystals=0) as preview:
        game, ui = preview.game, preview.game.lattice_ui
        before = (game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict())
        world_before = {'elapsed_ms': game.elapsed_ms, 'player': list(game.player.position)}

        def event(kind, **fields):
            pygame.event.post(pygame.event.Event(kind, **fields))
            if not game.handle_events():raise RuntimeError('The capture was closed during input.')

        def run(seconds, stage):
            nonlocal frame_number
            for _ in range(max(1, math.ceil(seconds*60))):
                if not game.handle_events():raise RuntimeError('The capture was closed during animation.')
                game.update(1/60)
                game.draw()
                if frame_number % 2 == 0:
                    frame = Image.frombytes('RGB', game.window.get_size(),
                                            pygame.image.tobytes(game.window, 'RGB'))
                    frames.append(frame.resize((480, 320), Image.Resampling.NEAREST))
                    timeline.append({'frame': len(frames)-1, 'stage': stage,
                                     'selected': ui.selected, 'navigating': ui.navigating,
                                     'cursor': list(ui.cursor_position), 'camera': list(ui.pan),
                                     'pulse': round(ui.pulse_strength, 4)})
                frame_number += 1

        def record(name):
            game.draw()
            pygame.image.save(game.window, str(output/(name+'.png')))
            captures.append({'file': name+'.png', 'window': list(game.window.get_size()),
                             'text_scale': game.audio.text_scale, 'selected': ui.selected,
                             'navigating': ui.navigating, 'cursor': list(ui.cursor_position),
                             'camera': list(ui.pan), 'pulse': round(ui.pulse_strength, 4)})
            assert game.ui_surface.get_clip() == game.ui_surface.get_rect()

        def explore(key, seconds, label):
            event(pygame.KEYDOWN, key=key, repeat=False)
            run(seconds, label+' — explore')
            assert ui.navigating
            if not captures:record('gold_cursor_exploring')
            cursor = ui.cursor_position.copy()
            nearest = min(ui.board.nodes, key=lambda identifier:
                          pygame.Vector2(ui.board.nodes[identifier]['position']).distance_squared_to(cursor))
            event(pygame.KEYUP, key=key)
            assert not ui.navigating
            assert ui.selected == nearest, (ui.selected, nearest)
            release_camera = ui.pan.copy()
            run(.1, label+' — center')
            intermediate_camera = ui.pan.copy()
            run(.5, label+' — selected pulse')
            target = pygame.Vector2(ui.board.nodes[nearest]['position'])
            assert ui.pan.distance_to(target) < .001
            assert ui.node_position(nearest).distance_to(ui.map_rect.center) < .001
            if release_camera.distance_to(target) > .01:
                assert intermediate_camera != release_camera
                assert intermediate_camera.distance_to(target) < release_camera.distance_to(target)
            selections.append({'stage': label, 'free_cursor_at_release': list(cursor),
                               'nearest_node': nearest, 'camera_at_release': list(release_camera),
                               'camera_after_100ms': list(intermediate_camera),
                               'centered_camera': list(ui.pan)})

        run(.35, 'opening pulse')
        explore(pygame.K_RIGHT, .55, 'free exploration right')
        explore(pygame.K_DOWN, 1.1, 'free exploration down')
        record('selected_node_pulsing')
        # Start from Mend's authored neighbor so this input exercise remains
        # meaningful when the lattice layout changes. The locked ability is
        # inspectable at rank 1 with zero Steps.
        preview.select_node('spr_02')
        # Establish a readable fixture without reintroducing a player shortcut.
        ui.reset_zoom();preview.advance(.25)
        displacement = pygame.Vector2(ui.board.nodes['mend_01']['position'])-ui.pan
        while displacement.length()*ui.zoom > min(ui.map_rect.size)*.3:
            preview.wheel(ui.map_rect.center, -1);preview.advance(.25)
        drag_start = pygame.Vector2(ui.map_rect.center)
        event(pygame.MOUSEBUTTONDOWN, button=1, pos=preview.point(drag_start))
        for index in range(1, 19):
            point = drag_start-displacement*ui.zoom*index/18
            event(pygame.MOUSEMOTION, pos=preview.point(point), rel=(0, -3), buttons=(1, 0, 0))
            run(1/60, 'mouse drag — explore')
        mouse_cursor = ui.cursor_position.copy()
        mouse_nearest = min(ui.board.nodes, key=lambda identifier:
                            pygame.Vector2(ui.board.nodes[identifier]['position']).distance_squared_to(mouse_cursor))
        event(pygame.MOUSEBUTTONUP, button=1, pos=preview.point(point))
        assert ui.selected == mouse_nearest == 'mend_01'
        run(.6, 'mouse release — selected pulse')
        assert ui.node_position('mend_01').distance_to(ui.map_rect.center) < .001
        preview.resize((480, 320), 1.5)
        preview.advance(.25)
        record('minimum_window_large_text')
        assert before == (game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict())
        assert game.lattice.state()['position'] == 'origin'
        assert world_before == {'elapsed_ms': game.elapsed_ms, 'player': list(game.player.position)}

    # GIF timing is in hundredths of a second; distribute 30/30/40ms to keep
    # the rendered 30 Hz motion at the same average playback speed.
    durations = [40 if index%3 == 2 else 30 for index in range(len(frames))]
    frames[0].save(output/'navigation.gif', save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=1)
    indices = (0, 15, 24, 39, 65, len(frames)-1)
    sheet = Image.new('RGB', (480*3, 320*2))
    for cell, index in enumerate(indices):sheet.paste(frames[min(index, len(frames)-1)], ((cell%3)*480, (cell//3)*320))
    sheet.save(output/'contact_sheet.png')
    metadata = {'isolated_temporary_journey': True, 'normal_journey_untouched': True,
                'fixture': {'rank': 1, 'rp': 0, 'steps': 0, 'crystals': 0},
                'progression_unchanged': True, 'world_unchanged': True,
                'keyboard_selection_checks': selections, 'captures': captures,
                'mouse_selection_check': {'free_cursor_at_release': list(mouse_cursor),
                                          'nearest_node': mouse_nearest},
                'animation': {'file': 'navigation.gif', 'frames': len(frames), 'fps': 30,
                              'logical_size': [480, 320], 'timeline': timeline}}
    (output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps({'output': str(output), 'frames': len(frames),
                      'selected_nodes': [item['nearest_node'] for item in selections]}))
    return 0


if __name__ == '__main__':raise SystemExit(main())
