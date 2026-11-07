"""Capture the production menus and item-only victory after progression cleanup.

Uses an isolated real Game, real input and an ordinary Bat battle. No persistent
journey or settings outside a temporary directory is accessed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import tempfile
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_OUTPUT = ROOT/'docs/reviews/progression_cleanup'
SOURCE_PATHS = (
    'main.py', 'pause_menu.py', 'status_ui.py', 'spoils_scene.py',
    'world_encounters.py', 'post_battle.py', 'battle_rewards.py',
    'character_abilities.py', 'character_attributes.py', 'party_state.py',
    'legacy_save.py', 'assets/combat/bestiary.json',
    'assets/abilities/characters.json',
    'assets/compatibility/retired_progression_rewards.json',
    'assets/items/catalog.json', 'tools/capture_progression_cleanup.py',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    return {name: digest(ROOT/name) for name in SOURCE_PATHS}


def check(output):
    report = json.loads((output/'verification.json').read_text())
    assert report['source_sha256'] == source_hashes(), 'Production sources changed; recapture.'
    for name, expected in report['artifact_sha256'].items():
        assert digest(output/name) == expected, name
    assert len(report['captures']) == 6
    assert report['completed_real_bat_battle']
    assert report['item_reward_delta'] == 1
    assert report['receipt_survived_continue']
    assert report['reward_not_repeated']
    for shot in report['captures']:
        labels = ' '.join(shot['text']).lower()
        assert 'lattice' not in labels and 'attunement' not in labels
        assert 'resonance points' not in labels
        assert not any(word == 'rp' for word in labels.replace('+', ' ').split())
    print('Production menu/Spoils captures, source hashes and once-only item receipt verified.')


def capture(output):
    import pygame
    from main import Game
    from ui_style import Painter

    output.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    shots = []

    def key(game, value):
        for kind in (pygame.KEYDOWN, pygame.KEYUP):
            pygame.event.post(pygame.event.Event(kind, key=value, repeat=False))
        assert game.handle_events()

    def click(game, logical):
        width, height = game.window.get_size()
        scale = max(1, min(width//480, height//320))
        point = (round((width-480*scale)//2+logical[0]*scale),
                 round((height-320*scale)//2+logical[1]*scale))
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        assert game.handle_events()

    def resize(game, size, text_scale):
        game.audio.set_text_scale(text_scale)
        pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE,
                                           w=size[0], h=size[1], size=size))
        assert game.handle_events()
        game.draw()
        assert game.window.get_size() == size

    def shot(game, name):
        labels = []
        original = Painter.text
        def text(painter, value, *args, **kwargs):
            labels.append(str(value))
            return original(painter, value, *args, **kwargs)
        with patch.object(Painter, 'text', text):
            game.draw()
        content = ' '.join(labels).lower()
        assert not any(term in content for term in
                       ('lattice', 'attunement', 'resonance points'))
        assert not any(word == 'rp' for word in content.replace('+', ' ').split())
        pygame.image.save(game.window, str(output/name))
        shots.append({'file': name, 'window': list(game.window.get_size()),
                      'text_scale': game.audio.text_scale, 'text': labels})
        return labels

    def menus(game, suffix):
        key(game, pygame.K_ESCAPE)
        assert game.pause.is_open
        labels = shot(game, 'pause_'+suffix+'.png')
        assert 'Characters' in labels and 'Inventory' in labels
        assert 'Aether Lattice' not in game.pause.options
        key(game, pygame.K_DOWN)
        key(game, pygame.K_RETURN)
        assert game.status_ui.is_open and game.pause.overlay == 'status'
        labels = shot(game, 'characters_'+suffix+'.png')
        assert 'Characters' in labels and 'Caelan' in labels
        key(game, pygame.K_ESCAPE)
        assert not game.status_ui.is_open
        key(game, pygame.K_ESCAPE)
        assert not game.pause.is_open

    with tempfile.TemporaryDirectory(prefix='progression-cleanup-review-') as directory:
        work = Path(directory)
        journey, settings = work/'journey.json', work/'settings.json'
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                    save_path=journey, settings_path=settings)
        game.audio.set_music(0)
        game.audio.set_effects(0)
        game.opening.restore({'version': 1, 'stage': 'disabled'})
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 40))
        game.player.facing = 'back'
        game.camera.reset()
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        assert not any(hasattr(game, field) for field in
                       ('lattice', 'lattice_progression', 'lattice_ui'))
        menus(game, '960')
        resize(game, (480, 320), 1.5)
        menus(game, '480_text_150')
        resize(game, (960, 640), 1.0)

        original_stats = game.attributes.to_dict()['attributes']
        original_items = game.inventory.quantity('aether_emerald')
        game.player.position.update(game.combat.position+(0, 24))
        game.camera.reset()
        assert game.combat.interact(rng=random.Random(7))
        model, scene = game.combat.model, game.combat.scene
        for _ in range(5000):
            if model.ended:break
            if model.waiting_for_player:
                game.draw()
                click(game, scene.command_rects['attack'].center)
            else:
                game.update(.1, (0, 0), False)
        else:raise AssertionError('Ordinary Bat battle did not complete')
        assert model.phase == 'victory'
        for _ in range(200):
            if game.combat.post_phase == 'spoils' and game.combat.spoils.awarded:break
            game.update(.1, (0, 0), False)
        else:raise AssertionError('Victory did not reach awarded item Spoils')
        labels = shot(game, 'spoils_960.png')
        assert 'Spoils of Battle' in labels and any('Emerald' in label for label in labels)
        assert game.inventory.quantity('aether_emerald') == original_items+1
        assert game.attributes.to_dict()['attributes'] == original_stats
        receipt = game.combat.receipt_id
        assert game.battle_rewards.has_receipt(receipt)
        committed = (game.inventory.to_dict(), game.battle_rewards.to_dict())
        for _ in range(10):game.update(.5, (0, 0), False)
        assert committed == (game.inventory.to_dict(), game.battle_rewards.to_dict())
        resize(game, (480, 320), 1.5)
        shot(game, 'spoils_480_text_150.png')
        assert game.save_progress()
        saved = json.loads(journey.read_text())
        assert 'aether_lattice' not in saved and 'battle_rewards' in saved
        assert set(saved['post_battle']['rewards']) == {'drops'}
        bytes_before_title = journey.read_bytes()
        restored = Game(window_size=(960, 640), fullscreen=False, start_on_title=True,
                        save_path=journey, settings_path=settings)
        restored.audio.set_music(0)
        restored.audio.set_effects(0)
        assert restored.has_saved_journey
        assert journey.read_bytes() == bytes_before_title
        assert restored.begin_journey(True)
        assert restored.battle_rewards.has_receipt(receipt)
        assert committed == (restored.inventory.to_dict(), restored.battle_rewards.to_dict())
        assert restored.combat.post_phase == 'spoils' and restored.combat.spoils.awarded
        restored.draw()
        click(restored, restored.combat.spoils.continue_rect.center)
        assert not restored.combat.active
        assert committed == (restored.inventory.to_dict(), restored.battle_rewards.to_dict())
        assert restored.attributes.to_dict()['attributes'] == original_stats
        pygame.quit()

    assert before == source_hashes(), 'Production files changed during capture.'
    artifacts = {shot['file']: digest(output/shot['file']) for shot in shots}
    report = {'version': 1, 'source_sha256': before, 'artifact_sha256': artifacts,
              'captures': shots, 'completed_real_bat_battle': True,
              'item_reward_delta': 1, 'receipt_survived_continue': True,
              'reward_not_repeated': True,
              'fixtures': ['Temporary journey/settings only; opening guidance disabled for review.',
                           'Player placed near the real test Bat; normal stats, abilities, RNG seed 7.',
                           'Actual keyboard menu input and mouse combat/Continue input.',
                           'No enemy/player HP, damage, rewards, poses or draw calls replaced.']}
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    check(output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    if args.check:check(args.output)
    else:capture(args.output)


if __name__ == '__main__':
    main()
