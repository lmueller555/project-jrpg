"""Capture the authored circular Aether Lattice through the production menu.

All journeys and reward fixtures are temporary. Pillow only assembles rendered
game frames into a review animation; no game artwork is generated or altered.
"""
from __future__ import annotations

import argparse
from collections import Counter
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
from aether_lattice import AetherLattice
from main import Game
from preview_aether_lattice import LatticePreview


def through_route(board, formation, rp):
    """Check the actual default Move routes, not a manually chosen detour."""
    probe = AetherLattice(board)
    assert probe.award_rewards('review_route', {'caelan': rp})
    entry, center, exit_node = (formation[key] for key in ('entry', 'center_node', 'exit'))
    if probe.state()['position'] != entry:assert probe.move(entry)
    inward = probe.route(center)
    assert inward and probe.move(center)
    outward = probe.route(exit_node)
    assert outward
    path = inward+outward[1:]
    assert set(path) <= set(formation['nodes']), formation['name']
    assert len(path) == len(set(path)), ('Default Move retraces its approach', formation['name'], path)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'work/lattice-formations')
    args = parser.parse_args(argv)
    output = args.output;output.mkdir(parents=True, exist_ok=True)
    frames, timeline, captures, operations = [], [], [], []
    frame_number = 0

    with LatticePreview(rp=0, crystals=0) as zero:
        zero.key(pygame.K_f);zero.advance(.3)
        pygame.image.save(zero.game.window, str(output/'new_game_overview.png'))
        assert zero.game.lattice.state()['position'] == 'origin'
        assert zero.game.lattice.rank() == 1 and zero.game.lattice.steps() == 0
        assert not any(zero.game.inventory.quantity(key) for key in zero.game.lattice.board.crystals)
        review_rp = zero.game.lattice.board.rp_for_rank(150)

    with LatticePreview(rp=review_rp, crystals=0) as preview:
        game, ui = preview.game, preview.game.lattice_ui
        board = game.lattice.board
        assert game.lattice.rank() >= max(edge['min_rank'] for edge in board.edges)
        assert len(board.nodes) == 200
        counts = Counter(node['kind'] for node in board.nodes.values())
        assert counts == {'stat': 130, 'ability': 20, 'blank': 50}
        large_id, large = next((key, value) for key, value in board.formations.items() if value['size'] == 'large')
        small_id, small = next((key, value) for key, value in board.formations.items() if value['size'] == 'small')
        routes = {key: through_route(board, formation, review_rp)
                  for key, formation in board.formations.items()}
        path = routes[large_id]
        assert len(path) == len(set(path)) and large['center_node'] in path[1:-1]
        model_before = game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict()
        world_before = game.elapsed_ms, list(game.player.position)

        def run(seconds, stage):
            nonlocal frame_number
            for _ in range(max(1, math.ceil(seconds*60))):
                if not game.handle_events():raise RuntimeError('The review capture closed during input.')
                game.update(1/60);game.draw()
                if frame_number%4 == 0:
                    frame = Image.frombytes('RGB', game.window.get_size(), pygame.image.tobytes(game.window, 'RGB'))
                    frames.append(frame.resize((480, 320), Image.Resampling.NEAREST))
                    timeline.append({'frame': len(frames)-1, 'stage': stage, 'zoom': ui.zoom,
                                     'selected': ui.selected, 'position': game.lattice.state()['position'],
                                     'camera': list(ui.pan)})
                frame_number += 1

        def select(identifier):
            for _ in range(len(board.nodes)+1):
                if ui.selected == identifier:return
                preview.key(pygame.K_TAB)
            raise AssertionError('The production cursor could not reach '+identifier)

        def scale(desired):
            difference = round(math.log(desired/ui.target_zoom)/math.log(1.2))
            for _ in range(abs(difference)):
                preview.key(pygame.K_PLUS if difference > 0 else pygame.K_MINUS)

        def record(name):
            game.draw();pygame.image.save(game.window, str(output/(name+'.png')))
            captures.append({'file': name+'.png', 'window': list(game.window.get_size()),
                             'text_scale': game.audio.text_scale, 'zoom': ui.zoom,
                             'selected': ui.selected, 'position': game.lattice.state()['position'],
                             'camera': list(ui.pan)})
            assert game.ui_surface.get_clip() == game.ui_surface.get_rect()

        def move(identifier):
            if game.lattice.state()['position'] == identifier:return
            select(identifier)
            run(.18, 'preview onward route — '+identifier)
            cost = len(game.lattice.route(identifier))-1
            old_steps = game.lattice.steps()
            inventory, attributes = game.inventory.to_dict(), game.attributes.to_dict()
            preview.key(pygame.K_m)
            assert ui.pending == ('move', identifier), ui.message
            preview.key(pygame.K_RETURN)
            assert game.lattice.state()['position'] == identifier
            assert game.lattice.steps() == old_steps-cost
            assert game.inventory.to_dict() == inventory and game.attributes.to_dict() == attributes
            assert game.lattice.state()['activated'] == []
            operations.append({'to': identifier, 'steps': cost, 'remaining_steps': game.lattice.steps()})
            run(.3, 'travel through center — '+identifier)

        preview.key(pygame.K_f);run(.35, 'whole section — large and small formations')
        assert all(ui.map_rect.inflate(-6, -6).collidepoint(ui.node_position(key)) for key in board.nodes)
        record('whole_lattice_overview')
        run(.4, 'whole section — settled overview')
        select(large['center_node']);scale(.46);run(.35, 'large formation — curved internal paths')
        record('large_formation')
        run(.4, 'large formation — selected center pulse')
        select(small['center_node']);preview.key(pygame.K_0);preview.key(pygame.K_MINUS)
        run(.35, 'small formation — through-center route')
        record('small_formation')
        run(.4, 'small formation — selected center pulse')
        outside = [key for key in board.nodes if key not in board.node_formations]
        assert outside
        bridge = min(outside, key=lambda key: pygame.Vector2(board.nodes[key]['position']).distance_squared_to(large['center']))
        select(bridge);scale(.45);run(.3, 'straight bridge between circular formations')
        record('straight_bridge')
        run(.4, 'straight connector between formations')
        assert model_before == (game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict())

        select(large['entry']);scale(.45);run(.25, 'enter large formation')
        move(large['entry'])
        route_start_steps = game.lattice.steps()
        move(large['center_node'])
        move(large['exit'])
        run(.3, 'center reached and onward exit — no retraced edge')
        assert game.lattice.steps() == route_start_steps-(len(path)-1)
        assert game.lattice.state()['position'] == large['exit']
        assert len({frozenset(pair) for pair in zip(path, path[1:])}) == len(path)-1
        assert world_before == (game.elapsed_ms, list(game.player.position))

        select(small['center_node']);scale(.6);run(.25, 'small formation after travel')
        preview.resize((480, 320), 1.5);preview.advance(.25)
        record('minimum_window_large_text')
        checkpoint = game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict()
        game.save_progress()
        for _ in range(2):
            restored = Game(fullscreen=False, start_on_title=True,
                            save_path=preview.path/'journey.json', settings_path=preview.path/'settings.json')
            restored.audio.set_music(0);restored.audio.set_effects(0)
            assert restored.has_saved_journey and restored.begin_journey(True)
            assert checkpoint == (restored.lattice.to_dict(), restored.inventory.to_dict(), restored.attributes.to_dict())
            preview.game = restored

        internal, external = [], []
        for edge in board.edges:
            same = board.node_formations.get(edge['from']) is not None and board.node_formations.get(edge['from']) == board.node_formations.get(edge['to'])
            if same:
                assert 'curve' in edge and len(ui.edge_points(edge)) > 2
                internal.append(edge)
            else:
                assert 'curve' not in edge and len(ui.edge_points(edge)) == 2
                external.append(edge)

    durations = [60 if index%3 == 1 else 70 for index in range(len(frames))]
    frames[0].save(output/'formations.gif', save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=True, disposal=1)
    with Image.open(output/'formations.gif') as animation:encoded_frames = animation.n_frames
    sheet = Image.new('RGB', (480*3, 320*2))
    for cell, index in enumerate((0, 8, 15, 24, len(frames)//2, len(frames)-1)):
        sheet.paste(frames[min(index, len(frames)-1)], ((cell%3)*480, (cell//3)*320))
    sheet.save(output/'contact_sheet.png')
    metadata = {'isolated_temporary_journeys': True, 'normal_journey_untouched': True,
                'normal_new_game': {'rp': 0, 'rank': 1, 'steps': 0, 'crystals': 0},
                'travel_fixture': {'rp': review_rp, 'rank': 150, 'crystals': 0}, 'board_version': board.version,
                'node_counts': dict(counts), 'formation_sizes': dict(Counter(f['size'] for f in board.formations.values())),
                'curved_internal_edges': len(internal), 'straight_external_edges': len(external),
                'large_formation': large_id, 'small_formation': small_id, 'straight_bridge_node': bridge,
                'entry_center_exit_route': path, 'center': large['center_node'], 'no_retraced_edges': True,
                'all_formation_default_routes': routes,
                'movement_operations': operations, 'movement_never_activated_nodes': True,
                'world_unchanged': True, 'continue_round_trips': 2, 'captures': captures,
                'animation': {'file': 'formations.gif', 'rendered_frames': len(frames),
                              'encoded_frames': encoded_frames, 'fps': 15, 'logical_size': [480, 320],
                              'timeline': timeline}}
    (output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps({'output': str(output), 'frames': len(frames),
                      'gif_bytes': (output/'formations.gif').stat().st_size, 'route_nodes': len(path)}))
    return 0


if __name__ == '__main__':raise SystemExit(main())
