"""Capture production Aether Lattice input using disposable review journeys."""
import json
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
from main import Game
from preview_aether_lattice import LatticePreview


def main():
    output = ROOT/'work/aether-lattice'
    output.mkdir(parents=True, exist_ok=True)
    captures, operations = [], []

    def record(preview, name):
        preview.advance(.25)
        game = preview.game
        game.draw()
        if game.lattice_ui.is_open:
            ui = game.lattice_ui
            for rect in (ui.map_rect, ui.detail_view, ui.move_rect, ui.activate_rect, ui.close_rect):
                assert pygame.Rect(0, 0, 480, 320).contains(rect), (name, rect)
            assert game.ui_surface.get_clip() == game.ui_surface.get_rect()
        pygame.image.save(game.window, str(output/(name+'.png')))
        captures.append({'capture': name, 'window': list(game.window.get_size()),
                         'text_scale': game.audio.text_scale,
                         'selected': game.lattice_ui.selected,
                         'pending': game.lattice_ui.pending,
                         'rank': game.lattice.rank(), 'steps': game.lattice.steps(),
                         'rp_progress': game.lattice.rp_progress(),
                         'lattice': game.lattice.state(),
                         'base_attributes': game.attributes.to_dict()['attributes'],
                         'effective_attributes': {key: game.attributes.value(key)
                                                  for key in game.attributes.definitions},
                         'current_hp': game.attributes.current_hp,
                         'current_mp': game.attributes.current_mp,
                         'crystals': {key: game.inventory.quantity(key)
                                      for key in game.lattice.board.crystals},
                         'known_abilities': game.lattice.learned_abilities(),
                         'zoom': game.lattice_ui.zoom,
                         'confirmation_text': game.lattice_ui.confirmation_text(),
                         'confirmation_scroll': game.lattice_ui.confirm_scroll,
                         'confirmation_max_scroll': game.lattice_ui.confirm_max_scroll,
                         'detail_scroll': game.lattice_ui.detail_scroll,
                         'detail_text': game.lattice_ui.detail_text()})

    def prepare(preview, action, target):
        game = preview.game;preview.select_node(target);game.draw()
        before = game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict()
        rect = game.lattice_ui.move_rect if action == 'move' else game.lattice_ui.activate_rect
        preview.click(rect.center)
        assert game.lattice_ui.pending == (action, target), (action, target, game.lattice_ui.message)
        assert before == (game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict())

    def confirm(preview, action, target):
        preview.key(pygame.K_RETURN)
        game = preview.game
        assert game.lattice_ui.pending is None
        if action == 'move':assert game.lattice.state()['position'] == target
        else:assert target in game.lattice.state()['activated']
        operations.append({'action': action, 'target': target, 'rank': game.lattice.rank(),
                           'steps': game.lattice.steps(), 'position': game.lattice.state()['position']})

    with LatticePreview(rp=0, crystals=0) as preview:
        record(preview, 'lattice_start_closeup')
        preview.key(pygame.K_f)
        record(preview, 'lattice_initial')
        preview.select_node('blank_05')
        preview.key(pygame.K_m)
        assert 'Attunement 5' in preview.game.lattice_ui.message
        record(preview, 'lattice_rank_gate')
        assert preview.game.lattice.rank() == 1
        assert preview.game.lattice.steps() == 0

    with LatticePreview() as preview:
        game = preview.game
        prepare(preview, 'move', 'hp_01')
        record(preview, 'lattice_move_confirmation')
        confirm(preview, 'move', 'hp_01')
        prepare(preview, 'activate', 'hp_01')
        record(preview, 'lattice_activation_confirmation')
        preview.resize((480, 320), 1.5)
        record(preview, 'lattice_activation_confirmation_small_large')
        confirmation = preview.game.lattice_ui.confirmation_text()
        assert any('140' in line and '160' in line for line in confirmation)
        assert any('Emerald' in line and '1 owned' in line for line in confirmation)
        assert preview.game.lattice_ui.confirm_max_scroll == 0
        preview.resize((960, 640), 1.0)
        confirm(preview, 'activate', 'hp_01')
        assert game.attributes.value('hp') == 160
        assert game.attributes.current_hp == 140
        assert game.attributes.base_value('hp') == 140
        assert game.inventory.quantity('aether_emerald') == 0
        record(preview, 'lattice_hp_activated')
        preview.open_menu('Characters')
        record(preview, 'characters_lattice_bonus')
        preview.resize((960, 640), 1.5)
        record(preview, 'characters_lattice_bonus_large')
        game.save_progress()
        checkpoint = game.lattice.to_dict(), game.inventory.to_dict(), game.attributes.to_dict()
        for _ in range(2):
            restored = Game(fullscreen=False, start_on_title=True, save_path=preview.path/'journey.json',
                            settings_path=preview.path/'settings.json')
            restored.audio.set_music(0);restored.audio.set_effects(0)
            assert restored.has_saved_journey and restored.begin_journey(True)
            assert checkpoint == (restored.lattice.to_dict(), restored.inventory.to_dict(), restored.attributes.to_dict())
            assert restored.attributes.value('hp') == 160
            preview.game = restored
        preview.open_menu('Aether Lattice')
        record(preview, 'lattice_after_continue')

    with LatticePreview(rp=2000, crystals=3) as preview:
        game = preview.game
        prepare(preview, 'move', 'blank_01');confirm(preview, 'move', 'blank_01')
        assert game.lattice.state()['activated'] == []
        record(preview, 'lattice_blank_travel')
        prepare(preview, 'move', 'mend_01');confirm(preview, 'move', 'mend_01')
        prepare(preview, 'activate', 'mend_01');confirm(preview, 'activate', 'mend_01')
        assert 'mend' in game.lattice.learned_abilities()
        record(preview, 'lattice_mend_learned')
        prepare(preview, 'move', 'brace_01');confirm(preview, 'move', 'brace_01')
        prepare(preview, 'activate', 'brace_01');confirm(preview, 'activate', 'brace_01')
        assert 'brace' in game.lattice.learned_abilities()
        preview.key(pygame.K_END)
        record(preview, 'lattice_known_abilities_and_crystals')
        preview.key(pygame.K_HOME);preview.key(pygame.K_f)
        record(preview, 'lattice_explored_overview')
        preview.resize((960, 640), 1.5)
        preview.select_node('hp_03')
        record(preview, 'lattice_large_text')
        preview.resize((480, 320), 1.5)
        record(preview, 'lattice_small_large_text')
        preview.key(pygame.K_F1)
        record(preview, 'lattice_controls_small_large')

    (output/'verification.json').write_text(json.dumps({
        'isolated_temporary_journeys': True,
        'continue_round_trips': 2,
        'normal_new_game': {'rank': 1, 'rp': 0, 'steps': 0, 'crystals': 0},
        'review_fixtures': [{'rp': 0, 'crystals': 0}, {'rp': 20, 'aether_emerald': 1},
                            {'rp': 2000, 'each_crystal': 3}],
        'operations': operations, 'captures': captures,
    }, indent=2)+'\n')
    print(output)
    return 0


if __name__ == '__main__':raise SystemExit(main())
