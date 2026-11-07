"""Render isolated Cave Bat encounters with real Game/BattleScene and ATB.

The existing Eldenmere battlefield and Bat drawings are a review stage. This
tool does not place Cave Bats in the world, unlock the cave or settle rewards.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
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
DEFAULT_OUTPUT = ROOT/'docs/reviews/cave_bat'
SOURCE_PATHS = (
    'main.py', 'bestiary.py', 'enemy_growth.py', 'leveling.py',
    'battle_model.py', 'battle_scene.py', 'battle_action_fx.py',
    'battle_action_audio.py', 'battle_choreography.py', 'combat_damage.py',
    'combat_motion_art.py', 'character_attributes.py', 'ui_style.py',
    'assets/combat/bestiary.json', 'assets/combat/actions.json',
    'assets/combat/enemy_archetypes.json', 'assets/characters/level_growth.json',
    'assets/characters/attributes.json', 'assets/combat/caelan_choreography.json',
    'tools/capture_cave_bat.py',
)
ART_FOLDERS = ('assets/combat/bat', 'assets/combat/caelan',
               'assets/combat/caelan_motion', 'assets/combat/eldenmere')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    paths = set(SOURCE_PATHS)
    for folder in ART_FOLDERS:
        paths.update(str(path.relative_to(ROOT)) for path in (ROOT/folder).rglob('*')
                     if path.is_file())
    return {name: digest(ROOT/name) for name in sorted(paths)}


def check(output):
    report = json.loads((output/'verification.json').read_text())
    assert report['source_sha256'] == source_hashes(), 'Production sources changed; recapture.'
    for name, expected in report['artifact_sha256'].items():
        assert digest(output/name) == expected, name
    assert {(shot['level'], shot['state']) for shot in report['captures']} == {
        (2, 'ready'), (3, 'ready'), (3, 'bite'), (3, 'wing_gust')}
    actions = report['enemy_actions']
    assert actions[:8] == [
        {'action': 'cave_bat_bite', 'mp': 5},
        {'action': 'cave_bat_wing_gust', 'mp': 3},
        {'action': 'cave_bat_bite', 'mp': 3},
        {'action': 'cave_bat_wing_gust', 'mp': 1},
        *[{'action': 'cave_bat_bite', 'mp': 1} for _ in range(4)]]
    assert sum(action['action'] == 'cave_bat_wing_gust' for action in actions) == 2
    assert report['outcome'] == 'victory'
    assert {'idle', 'attack', 'cast', 'hurt', 'defeat'} <= set(report['bat_states'])
    assert report['persistent_attributes_unchanged']
    for shot in report['captures']:
        assert 'Cave Bat' in shot['text']
    print('Cave Bat real-render captures, ATB/MP behavior and source hashes verified.')


def capture(output):
    import pygame
    from PIL import Image, ImageDraw
    from battle_model import BattleModel
    from battle_scene import BattleScene
    from character_attributes import CharacterAttributes
    from leveling import character_stats
    from main import Game
    from ui_style import Painter

    output.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    shots, enemy_actions, events, bat_states = [], [], [], set()

    def render(game, scene):
        _, _, origin = game._ensure_ui_surface()
        scene.draw(game.canvas, game.ui_surface)
        game.window.fill('#101b19')
        game.window.blit(game.ui_surface, origin)
        pygame.display.flip()

    def command(game, scene, identifier):
        render(game, scene)
        point = scene.command_rects[identifier].center
        width, height = game.window.get_size()
        scale = max(1, min(width//480, height//320))
        position = (round((width-480*scale)//2+point[0]*scale),
                    round((height-320*scale)//2+point[1]*scale))
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            scene.handle_event(pygame.event.Event(kind, button=1, pos=position))

    def shot(game, scene, level, state):
        labels = []
        original_text = Painter.text
        def text(painter, value, *args, **kwargs):
            labels.append(str(value))
            return original_text(painter, value, *args, **kwargs)
        with patch.object(Painter, 'text', text):
            render(game, scene)
        filename = f'level_{level}_{state}.png'
        pygame.image.save(game.window, str(output/filename))
        model = scene.model
        action = model.current_action
        shots.append({'file': filename, 'level': level, 'state': state,
                      'text': labels, 'player_hp': model.player.hp,
                      'enemy_hp': model.enemy.hp, 'enemy_mp': model.enemy.mp,
                      'action': action.action if action else None,
                      'action_elapsed': action.elapsed if action else None})

    with tempfile.TemporaryDirectory(prefix='cave-bat-review-') as directory:
        work = Path(directory)
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                    save_path=work/'journey.json', settings_path=work/'settings.json')
        game.audio.set_music(0)
        game.audio.set_effects(0)
        game.opening.restore({'version': 1, 'stage': 'disabled'})
        pygame.event.clear()
        persistent = deepcopy(game.attributes.to_dict())
        for level in (2, 3):
            catalog = deepcopy(CharacterAttributes().catalog)
            catalog['characters']['caelan']['attributes'] = character_stats('caelan', level)
            source = CharacterAttributes('caelan', catalog)
            model = BattleModel.from_bestiary(source, 'cave_bat', level, rng=random.Random(7))
            scene = BattleScene(game, model, battlefield='eldenmere')
            source_before = deepcopy(source.to_dict())
            recorded, action_object, captured = [], None, set()
            original_drain = model.drain_events
            def drain():
                batch = original_drain()
                if level == 3:events.extend(deepcopy(batch))
                return batch
            original_frame = scene.sprites.frame
            def frame(actor, state, elapsed):
                assert actor != 'cave_bat', 'Cave Bat ID escaped the sprite alias'
                if level == 3 and actor == 'bat':bat_states.add(state)
                return original_frame(actor, state, elapsed)
            with patch.object(model, 'drain_events', drain), \
                    patch.object(scene.sprites, 'frame', frame):
                for _ in range(16000):
                    if model.waiting_for_player:
                        if 'ready' not in captured:
                            # Waiting pauses ATB; let the first-hit popup settle.
                            scene.update(1.2)
                            shot(game, scene, level, 'ready')
                            captured.add('ready')
                        if level == 2:break
                        command(game, scene, 'guard' if len(recorded) < 8 else 'attack')
                    scene.update(.04)
                    action = model.current_action
                    if action is not None and action is not action_object:
                        action_object = action
                        if action.actor == 'enemy':
                            recorded.append({'action': action.action, 'mp': model.enemy.mp})
                    render(game, scene)
                    if level == 3 and action is not None and action.actor == 'enemy':
                        state = 'bite' if action.action == 'cave_bat_bite' else 'wing_gust'
                        if state not in captured and action.impact_at <= action.elapsed:
                            shot(game, scene, level, state)
                            captured.add(state)
                    if model.ended:
                        for _ in range(15):
                            scene.update(.04)
                            render(game, scene)
                        break
                else:raise AssertionError('Cave Bat fixture did not complete')
            assert source.to_dict() == source_before
            if level == 3:
                enemy_actions = recorded
                assert model.phase == 'victory'
        assert game.attributes.to_dict() == persistent
        pygame.quit()

    assert before == source_hashes(), 'Production sources changed during capture.'
    sheet = Image.new('RGB', (960, 680), '#142d25')
    draw = ImageDraw.Draw(sheet)
    ordered = sorted(shots, key=lambda entry: (entry['state'] != 'ready', entry['level'],
                                               entry['state']))
    for index, entry in enumerate(ordered):
        x, y = index % 2*480, index//2*340
        image = Image.open(output/entry['file']).convert('RGB')
        image.thumbnail((480, 320), Image.Resampling.NEAREST)
        sheet.paste(image, (x, y+20))
        draw.text((x+8, y+4), f"Level {entry['level']} · {entry['state'].replace('_', ' ')}", fill='#e7c779')
    sheet.save(output/'contact_sheet.png')
    artifacts = {entry['file']: digest(output/entry['file']) for entry in shots}
    artifacts['contact_sheet.png'] = digest(output/'contact_sheet.png')
    report = {'version': 1, 'source_sha256': before, 'artifact_sha256': artifacts,
              'captures': shots, 'enemy_actions': enemy_actions,
              'events': events, 'bat_states': sorted(bat_states),
              'outcome': 'victory', 'persistent_attributes_unchanged': True,
              'fixtures': [
                  'Real Game with temporary journey/settings; existing Eldenmere review stage.',
                  'Existing Bat art alias; no new Cave Bat sprite or cave background.',
                  'Caelan uses approved same-level growth stats via a copied attribute catalog.',
                  'Real ATB, seed 7, mouse Guard/Attack input; no HP/MP or pose injection.',
                  'Level 3 encounter completes; no world spawn, cave unlock, loot or XP settlement.',
                  'Planned Fire weakness and Stagger resistance remain inert metadata.']}
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
