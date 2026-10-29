"""Capture mouse-led Aether Lattice selection and contextual commands.

The production game runs with disposable journey/settings files. Pillow only
assembles rendered frames; no game artwork or ordinary saves are changed.
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
    parser.add_argument('--output', type=Path, default=ROOT/'work/lattice-simple')
    output = parser.parse_args(argv).output
    output.mkdir(parents=True, exist_ok=True)
    frames, timeline, captures, checks = [], [], [], []
    frame_number = 0

    with LatticePreview(rp=0, crystals=0) as preview:
        game, ui = preview.game, preview.game.lattice_ui
        world = game.elapsed_ms, list(game.player.position)

        def model():
            return game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict()

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
                                     'selected': ui.selected, 'camera': list(ui.pan),
                                     'zoom': ui.zoom, 'offer': ui.action_preview()})
                frame_number += 1

        def record(name):
            game.draw()
            pygame.image.save(game.window, str(output/(name+'.png')))
            assert game.ui_surface.get_clip() == game.ui_surface.get_rect()
            if ui.context_rect is not None:
                assert ui.map_rect.contains(ui.context_rect)
                assert ui.context_rect.contains(ui.action_rect)
            captures.append({'file': name+'.png', 'window': list(game.window.get_size()),
                             'text_scale': game.audio.text_scale, 'selected': ui.selected,
                             'offer': ui.action_preview(),
                             'context_rect': list(ui.context_rect) if ui.context_rect else None})

        browsing = model()
        preview.select_node('hp_01')
        assert ui.selected == 'hp_01' and ui.action_preview() is None
        record('unaffordable_selection')
        run(.3, 'selected node without an affordable command')
        preview.select_node('mend_01')
        assert ui.selected == 'mend_01' and ui.action_preview() is None
        checks.append({'stage': 'unaffordable and rank-locked nodes remain inspectable',
                       'travel_offer': False, 'progression_unchanged': model() == browsing})

        pointer = pygame.Vector2(ui.map_rect.center)+(40, -12)
        grabbed = ui.pan+(pointer-pygame.Vector2(ui.map_rect.center))/ui.zoom
        preview.wheel(pointer, -2)
        anchor_errors = []
        for _ in range(12):
            run(1/60, 'mouse-wheel zoom around the pointer')
            projected = pygame.Vector2(ui.map_rect.center)+(grabbed-ui.pan)*ui.zoom
            anchor_errors.append(projected.distance_to(pointer))
        assert max(anchor_errors) < .001
        start = pygame.Vector2(ui.map_rect.center)+(28, -8)
        event(pygame.MOUSEBUTTONDOWN, button=1, pos=preview.point(start))
        assert ui.action_preview() is None
        for index in range(1, 9):
            point = start+pygame.Vector2(-32, 12)*index/8
            event(pygame.MOUSEMOTION, pos=preview.point(point), rel=(0, 0), buttons=(1, 0, 0))
            run(1/30, 'direct camera drag')
        nearest = ui._nearest_node(ui.cursor_position)
        event(pygame.MOUSEBUTTONUP, button=1, pos=preview.point(point))
        run(.25, 'release selects and centers nearest node')
        assert ui.selected == nearest and model() == browsing
        checks.append({'stage': 'mouse-wheel zoom and direct camera dragging',
                       'maximum_wheel_anchor_error': max(anchor_errors),
                       'release_selected': nearest, 'progression_unchanged': True})

        assert game.award_battle_rewards('context_review', {'caelan': 20}, {'aether_emerald': 1})
        preview.select_node('hp_01')
        preview.zoom_to(.8)
        game.draw()
        offer = ui.action_preview()
        assert offer and (offer['action'], offer['node']) == ('move', 'hp_01')
        assert any('1 Step' in line for line in offer['lines'])
        before_shortcuts = model(), ui.selected, ui.zoom, ui.target_zoom
        for key in (pygame.K_PLUS, pygame.K_MINUS, pygame.K_f, pygame.K_0,
                    pygame.K_TAB, pygame.K_m, pygame.K_a, pygame.K_RETURN):
            preview.key(key)
        run(.2, 'affordable travel preview and Move button')
        assert (model(), ui.selected, ui.zoom, ui.target_zoom) == before_shortcuts
        record('travel_preview')
        preview.resize((480, 320), 1.5)
        run(.1, 'minimum window preview', animate=False)
        record('minimum_window_large_text')
        preview.resize((960, 640), 1.0)
        run(.3, 'ready to move with one Step')
        preview.perform_action('move', 'hp_01')
        run(.3, 'movement executed through contextual Move command')
        assert game.lattice.state()['position'] == 'hp_01'
        assert game.lattice.steps() == 0 and game.lattice.rank() == 2
        assert game.inventory.quantity('aether_emerald') == 1
        offer = ui.action_preview()
        assert offer and offer['action'] == 'activate'
        assert any('Emerald' in line for line in offer['lines'])
        assert any('140' in line and '160' in line for line in offer['lines'])
        record('activation_preview')
        run(.5, 'eligible current node shows effect, crystal cost and Activate')
        old_action = ui.action_rect.copy()
        preview.perform_action('activate', 'hp_01')
        run(.3, 'node activated once and contextual command disappears')
        assert game.attributes.value('hp') == 160 and game.attributes.current_hp == 140
        assert game.attributes.base_value('hp') == 140
        assert game.inventory.quantity('aether_emerald') == 0
        assert ui.action_preview() is None and ui.action_rect is None
        activated = model()
        preview.click(old_action.center)
        assert model() == activated
        record('activated_node')
        checks.append({'stage': 'contextual commands execute directly',
                       'travel_steps_spent': 1, 'rank_after_travel': game.lattice.rank(),
                       'activation_emeralds_spent': 1, 'effective_hp': game.attributes.value('hp'),
                       'current_hp': game.attributes.current_hp,
                       'repeat_activation_prevented': True, 'removed_shortcuts_inert': True})
        assert world == (game.elapsed_ms, list(game.player.position))

    durations = [80 if index%3 else 90 for index in range(len(frames))]
    frames[0].save(output/'contextual_controls.gif', save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=1)
    with Image.open(output/'contextual_controls.gif') as animation:encoded_frames = animation.n_frames
    metadata = {'isolated_temporary_journey': True, 'normal_journey_untouched': True,
                'initial_fixture': {'rank': 1, 'rp': 0, 'steps': 0, 'crystals': 0},
                'review_reward': {'rp': 20, 'aether_emerald': 1},
                'world_unchanged': True, 'checks': checks, 'captures': captures,
                'animation': {'file': 'contextual_controls.gif', 'fps': 12,
                              'rendered_frames': len(frames), 'encoded_frames': encoded_frames,
                              'logical_size': [480, 320], 'timeline': timeline}}
    (output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps({'output': str(output), 'checks': len(checks),
                      'rendered_frames': len(frames), 'encoded_frames': encoded_frames,
                      'gif_bytes': (output/'contextual_controls.gif').stat().st_size}))
    return 0


if __name__ == '__main__':raise SystemExit(main())
