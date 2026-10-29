"""Capture the full-width Aether Lattice using disposable production-game input.

Pillow assembles rendered frames into an animation. Game artwork is unchanged;
normal journey and settings files are never opened by this review tool.
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
    parser.add_argument('--output', type=Path, default=ROOT/'work/lattice-fullwidth')
    args = parser.parse_args(argv)
    output = args.output;output.mkdir(parents=True, exist_ok=True)
    frames, timeline, captures, checks = [], [], [], []
    frame_number = 0

    with LatticePreview(rp=0, crystals=0) as preview:
        game, ui = preview.game, preview.game.lattice_ui
        before = game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict()
        world = game.elapsed_ms, list(game.player.position)

        def event(kind, **fields):
            pygame.event.post(pygame.event.Event(kind, **fields))
            if not game.handle_events():raise RuntimeError('The capture closed during input.')

        def run(seconds, stage):
            nonlocal frame_number
            for _ in range(max(1, math.ceil(seconds*60))):
                if not game.handle_events():raise RuntimeError('The capture closed during animation.')
                game.update(1/60);game.draw()
                if frame_number%4 == 0:
                    frame = Image.frombytes('RGB', game.window.get_size(), pygame.image.tobytes(game.window, 'RGB'))
                    frames.append(frame.resize((480, 320), Image.Resampling.NEAREST))
                    timeline.append({'frame': len(frames)-1, 'stage': stage, 'zoom': ui.zoom,
                                     'selected': ui.selected, 'navigating': ui.navigating,
                                     'camera': list(ui.pan), 'map_rect': list(ui.map_rect)})
                frame_number += 1

        def record(name):
            game.draw();pygame.image.save(game.window, str(output/(name+'.png')))
            assert game.ui_surface.get_clip() == game.ui_surface.get_rect()
            captures.append({'file': name+'.png', 'window': list(game.window.get_size()),
                             'text_scale': game.audio.text_scale, 'map_rect': list(ui.map_rect),
                             'zoom': ui.zoom, 'selected': ui.selected, 'camera': list(ui.pan)})

        def assert_map_uses_previous_sidebar():
            assert ui.map_rect.left <= 20 and ui.map_rect.right >= 460
            assert ui.map_rect.width >= 440
            assert not hasattr(ui, 'move_rect') and not hasattr(ui, 'activate_rect')
            assert not hasattr(ui, 'detail_view')
            assert ui.map_rect.collidepoint((382, 264))
            assert ui.map_rect.collidepoint((382, 292))

        run(.1, 'full-width lattice')
        assert_map_uses_previous_sidebar()
        ui.fit_board();run(.35, 'whole section fixture across full content width')
        assert all(ui.map_rect.inflate(-8, -8).collidepoint(ui.node_position(key)) for key in ui.board.nodes)
        record('fullwidth_overview')
        preview.select_node('brace_01')
        ui.reset_zoom();preview.advance(.25)
        preview.wheel(ui.map_rect.center, -4)
        run(.35, 'selected center with no information sidebar')
        preview.hover((382, 180));run(.15, 'former sidebar is clear map space')
        record('fullwidth_closeup')

        start = pygame.Vector2(410, 200)
        event(pygame.MOUSEBUTTONDOWN, button=1, pos=preview.point(start))
        for shift in (15, 30, 45, 60):
            end = start-pygame.Vector2(shift, 0)
            event(pygame.MOUSEMOTION, pos=preview.point(end), rel=(-30, 0), buttons=(1, 0, 0))
            run(.05, 'drag through former sidebar')
        cursor = ui.cursor_position.copy()
        nearest = min(ui.board.nodes, key=lambda key:
                      pygame.Vector2(ui.board.nodes[key]['position']).distance_squared_to(cursor))
        event(pygame.MOUSEBUTTONUP, button=1, pos=preview.point(end))
        run(.25, 'nearest node centered after right-side drag')
        assert ui.selected == nearest and ui.action_preview() is None
        checks.append({'stage': 'former sidebar supports dragging', 'nearest_node': nearest,
                       'selected': ui.selected, 'cursor_at_release': list(cursor)})

        for point in ((382, 264), (382, 292)):
            preview.click(point);run(.2, 'former action-button space is navigable map')
            assert ui.action_preview() is None
            assert before == (game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict())
            checks.append({'stage': 'former action-button space selects only', 'logical_point': point,
                           'selected': ui.selected})

        event(pygame.KEYDOWN, key=pygame.K_RIGHT, repeat=False)
        run(.25, 'gold cursor exploring the wider map')
        event(pygame.KEYUP, key=pygame.K_RIGHT)
        run(.35, 'selected node centered and pulsing')
        assert ui.node_position(ui.selected).distance_to(ui.map_rect.center) < .001
        preview.resize((480, 320), 1.5)
        ui.fit_board();preview.advance(.3)
        assert_map_uses_previous_sidebar()
        record('minimum_window_large_text')
        assert before == (game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict())
        assert world == (game.elapsed_ms, list(game.player.position))
        assert game.lattice.state()['position'] == 'origin'

    durations = [60 if index%3 == 1 else 70 for index in range(len(frames))]
    frames[0].save(output/'fullwidth.gif', save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=1)
    with Image.open(output/'fullwidth.gif') as animation:encoded_frames = animation.n_frames
    sheet = Image.new('RGB', (480*3, 320*2))
    for cell, index in enumerate((0, 5, 10, 15, len(frames)//2, len(frames)-1)):
        sheet.paste(frames[min(index, len(frames)-1)], ((cell%3)*480, (cell//3)*320))
    sheet.save(output/'contact_sheet.png')
    metadata = {'isolated_temporary_journey': True, 'normal_journey_untouched': True,
                'fixture': {'rp': 0, 'rank': 1, 'steps': 0, 'crystals': 0},
                'progression_unchanged': True, 'world_unchanged': True,
                'permanent_node_details_panel': False, 'permanent_move_activate_controls': False,
                'new_guidance_cues_added': False, 'checks': checks, 'captures': captures,
                'animation': {'file': 'fullwidth.gif', 'rendered_frames': len(frames),
                              'encoded_frames': encoded_frames, 'fps': 15,
                              'logical_size': [480, 320], 'timeline': timeline}}
    (output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps({'output': str(output), 'rendered_frames': len(frames),
                      'encoded_frames': encoded_frames, 'gif_bytes': (output/'fullwidth.gif').stat().st_size}))
    return 0


if __name__ == '__main__':raise SystemExit(main())
