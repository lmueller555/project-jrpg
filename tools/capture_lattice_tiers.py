"""Capture authored Aether Lattice tier rewards through the production menu.

The review uses disposable journeys and explicit sample battle rewards. Pillow
only assembles rendered frames; no ordinary journey or game artwork is changed.
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
from preview_aether_lattice import LatticePreview


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'work/lattice-tiers')
    output = parser.parse_args(argv).output
    output.mkdir(parents=True, exist_ok=True)
    frames, timeline, captures, operations, checks = [], [], [], [], []
    frame_number = 0

    def run(preview, seconds, stage, animate=True):
        nonlocal frame_number
        game, ui = preview.game, preview.game.lattice_ui
        for _ in range(max(1, math.ceil(seconds*60))):
            if not game.handle_events():raise RuntimeError('Tier capture closed during input.')
            game.update(1/60);game.draw()
            if animate and frame_number%6 == 0:
                frame = Image.frombytes('RGB', game.ui_surface.get_size(),
                                        pygame.image.tobytes(game.ui_surface, 'RGB'))
                frames.append(frame.resize((480, 320), Image.Resampling.NEAREST))
                timeline.append({'frame': len(frames)-1, 'stage': stage,
                                 'selected': ui.selected, 'offer': ui.action_preview(),
                                 'rank': game.lattice.rank(), 'steps': game.lattice.steps()})
            frame_number += 1

    def record(preview, name):
        game, ui = preview.game, preview.game.lattice_ui
        game.draw();pygame.image.save(game.window, str(output/(name+'.png')))
        assert game.ui_surface.get_clip() == game.ui_surface.get_rect()
        if ui.context_rect is not None:
            assert ui.map_rect.contains(ui.context_rect)
            assert ui.context_rect.contains(ui.action_rect)
            assert not ui.context_rect.collidepoint(ui.node_position(ui.selected))
        captures.append({'file': name+'.png', 'window': list(game.window.get_size()),
                         'text_scale': game.audio.text_scale, 'selected': ui.selected,
                         'node': game.lattice.board.nodes[ui.selected],
                         'offer': ui.action_preview(), 'zoom': ui.zoom,
                         'context_rect': list(ui.context_rect) if ui.context_rect else None})

    def activation_offer(preview, identifier, stage):
        game, ui = preview.game, preview.game.lattice_ui
        node = game.lattice.board.nodes[identifier]
        preview.select_node(identifier)
        route = game.lattice.route(identifier)
        cost, steps = len(route)-1, game.lattice.steps()
        preview.perform_action('move', identifier)
        run(preview, .25, stage+' — travel', animate=False)
        assert game.lattice.state()['position'] == identifier
        assert game.lattice.steps() == steps-cost
        offer = ui.action_preview()
        assert offer and (offer['action'], offer['node']) == ('activate', identifier)
        current_value = game.attributes.value(node['stat'])
        assert any(str(current_value)+' → '+str(current_value+node['amount']) in line
                   for line in offer['lines'])
        for crystal, amount in node['cost'].items():
            assert any(game.lattice.board.crystals[crystal]['name'] in line
                       and str(amount) in line for line in offer['lines'])
        operations.append({'action': 'move', 'node': identifier, 'steps': cost,
                           'remaining_steps': game.lattice.steps()})
        return node

    def activate(preview, identifier):
        game, ui = preview.game, preview.game.lattice_ui
        node = game.lattice.board.nodes[identifier]
        before = game.attributes.value(node['stat'])
        current = game.attributes.current_hp, game.attributes.current_mp
        quantities = {crystal: game.inventory.quantity(crystal) for crystal in node['cost']}
        preview.perform_action('activate', identifier)
        assert game.attributes.value(node['stat']) == before+node['amount']
        assert current == (game.attributes.current_hp, game.attributes.current_mp)
        assert all(game.inventory.quantity(crystal) == quantities[crystal]-amount
                   for crystal, amount in node['cost'].items())
        assert identifier in game.lattice.state()['activated']
        assert identifier not in game.lattice.state().get('legacy_activated', [])
        assert ui.action_preview() is None
        operations.append({'action': 'activate', 'node': identifier, 'stat': node['stat'],
                           'amount': node['amount'], 'cost': node['cost'],
                           'effective_value': game.attributes.value(node['stat']),
                           'current_hp': current[0], 'current_mp': current[1]})

    with LatticePreview(rp=20, crystals=None) as preview:
        game, ui = preview.game, preview.game.lattice_ui
        assert game.lattice.board.version == 3
        assert game.lattice.board.nodes['hp_01']['amount'] == 100
        assert game.lattice.board.nodes['mp_01']['amount'] == 5
        world = game.elapsed_ms, list(game.player.position)
        activation_offer(preview, 'hp_01', 'first HP reward')
        run(preview, .4, 'first HP reward — +100 HP costs one Emerald')
        record(preview, 'early_hp_activation')
        activate(preview, 'hp_01')
        assert game.attributes.value('hp') == 240 and game.attributes.current_hp == 140
        run(preview, .2, 'HP maximum increased without refilling current HP')
        assert world == (game.elapsed_ms, list(game.player.position))
        checks.append({'stage': 'early HP activation', 'effective_hp': 240, 'current_hp': 140,
                       'rank': game.lattice.rank(), 'world_unchanged': True})
        rank_rp = game.lattice.board.rp_for_rank(350)
        center = game.lattice.board.formations['quiet_reserve']['center_node']
        center_rank = next(rank for rank in range(2, 50)
                           if _can_travel(game.lattice.board, center, rank))
        center_rp = game.lattice.board.rp_for_rank(center_rank)

    with LatticePreview(rp=center_rp, crystals=1) as preview:
        game = preview.game
        world = game.elapsed_ms, list(game.player.position)
        assert game.lattice.board.nodes[center]['stat'] == 'hp'
        assert game.lattice.board.nodes[center]['amount'] == 400
        activation_offer(preview, center, 'rare early center reward')
        run(preview, .4, 'rare early circular center — +400 HP')
        record(preview, 'rare_center_activation')
        activate(preview, center)
        assert game.attributes.value('hp') == 540
        assert world == (game.elapsed_ms, list(game.player.position))
        checks.append({'stage': 'rare early center reward', 'node': center,
                       'earliest_travel_rank': center_rank, 'effective_hp': 540,
                       'current_hp': game.attributes.current_hp, 'world_unchanged': True})

    with LatticePreview(rp=rank_rp, crystals=3) as preview:
        game, ui = preview.game, preview.game.lattice_ui
        board = game.lattice.board
        world = game.elapsed_ms, list(game.player.position)
        before_browsing = game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict()
        ui.fit_board();run(preview, .3, 'whole section', animate=False)
        record(preview, 'whole_lattice_overview')
        assert before_browsing == (game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict())
        preview.zoom_to(.8)

        activation_offer(preview, 'mp_01', 'first MP reward')
        run(preview, .35, 'first MP reward — +5 MP costs one Sapphire')
        record(preview, 'early_mp_activation')
        activate(preview, 'mp_01')
        assert game.attributes.value('mp') == 35 and game.attributes.current_mp == 30

        for identifier, expected_stat, name in (
                ('hp_05', 'mp', 'converted_mp_activation'),
                ('hp_07', 'mag', 'converted_mag_activation')):
            assert board.nodes[identifier]['stat'] == expected_stat
            activation_offer(preview, identifier, name)
            run(preview, .4, name)
            record(preview, name)
            activate(preview, identifier)

        late = next(identifier for identifier, node in board.nodes.items()
                    if node['kind'] == 'stat' and node['stat'] not in ('hp', 'mp')
                    and node['amount'] == 4
                    and game.lattice.required_rank(identifier) >= 85)
        activation_offer(preview, late, 'late maximum-tier reward')
        run(preview, .4, 'late progression — rare +4 attribute node')
        record(preview, 'late_maximum_activation')
        preview.resize((480, 320), 1.5)
        run(preview, .1, 'minimum window and large text', animate=False)
        record(preview, 'minimum_window_large_text')
        activate(preview, late)
        assert world == (game.elapsed_ms, list(game.player.position))
        checks.append({'stage': 'MP, converted nodes and maximum tiers',
                       'converted_mp': 'hp_05', 'converted_mag': 'hp_07',
                       'late_maximum': late,
                       'world_unchanged': True})
        stat_counts = Counter(node['stat'] for node in board.nodes.values() if node['kind'] == 'stat')
        tier_counts = {stat: dict(sorted(Counter(node['amount'] for node in board.nodes.values()
                                               if node['kind'] == 'stat' and node['stat'] == stat).items()))
                       for stat in stat_counts}

    durations = [100]*len(frames)
    frames[0].save(output/'tier_rewards.gif', save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=1)
    with Image.open(output/'tier_rewards.gif') as animation:encoded_frames = animation.n_frames
    metadata = {'isolated_temporary_journeys': True, 'normal_journey_untouched': True,
                'board_version': board.version, 'node_counts': dict(stat_counts),
                'attribute_bonus_tiers': tier_counts,
                'fixtures': [{'rp': 20, 'aether_emerald': 1},
                             {'rp': center_rp, 'rank': center_rank, 'each_crystal': 1},
                             {'rp': rank_rp, 'rank': 350, 'each_crystal': 3}],
                'checks': checks, 'operations': operations, 'captures': captures,
                'animation': {'file': 'tier_rewards.gif', 'fps': 10,
                              'rendered_frames': len(frames), 'encoded_frames': encoded_frames,
                              'logical_size': [480, 320], 'timeline': timeline}}
    (output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps({'output': str(output), 'checks': len(checks), 'operations': len(operations),
                      'rendered_frames': len(frames), 'encoded_frames': encoded_frames,
                      'gif_bytes': (output/'tier_rewards.gif').stat().st_size}))
    return 0


def _can_travel(board, target, rank):
    """Find a review milestone using both its gates and its paid Step distance."""
    probe = AetherLattice(board)
    assert probe.award_rewards('tier_review_access', {'caelan': board.rp_for_rank(rank)})
    return not probe.move_reason(target)


if __name__ == '__main__':raise SystemExit(main())
