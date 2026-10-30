"""Capture the real Eldenmere Bat encounter using disposable journeys.

The production game owns every input, animation, ATB update and reward. Pillow
only assembles already-rendered game frames into the review GIF/contact sheet.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import json
import math
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

import pygame
from PIL import Image
from main import Game
from ui_style import Painter
from quests import OPENING_QUEST, MILL_QUEST, REGENT_QUEST


def seed_completed_mill(game):
    """Review fixture: a legacy completed mill journey, with no battle rewards."""
    assert game.accept_quest(OPENING_QUEST)
    for objective in ('halden', 'elira', 'venn'):
        assert game.quests.complete_objective(OPENING_QUEST, objective)
    game._sync_inventory()
    game.halden_visit.restore();game.elira_visit.restore();game.venn_visit.restore()
    assert game.quests.turn_in(OPENING_QUEST, 'mother_serene')
    assert game.quests.unlock(MILL_QUEST) and game.accept_quest(MILL_QUEST)
    for objective in game.quests.definitions[MILL_QUEST]['objectives']:
        assert game.quests.complete_objective(MILL_QUEST, objective['id'])
    assert game.quests.turn_in(MILL_QUEST, 'mira_worker')
    assert game.mill_quest.restore({'version': 1,
        'inspected': ['mechanism', 'race', 'intake'], 'prepared': True,
        'spell_done': True, 'encouraged': True, 'restored': True,
        'verified': True, 'resolved': True})
    game.opening_conclusion.restore({'version': 1, 'stage': 'done'})
    game.opening.restore({'version': 1, 'stage': 'disabled'})
    assert game.quests.unlock(REGENT_QUEST)
    game.regent_quest.restore(None)
    game.social.blocked.clear();game.quests.drain_events();game.quest_ui.reset()


@contextmanager
def fixture(*, unlocked_bat=True):
    with tempfile.TemporaryDirectory(prefix='atb-combat-capture-') as directory:
        path = Path(directory)
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                    save_path=path/'journey.json', settings_path=path/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        pygame.event.clear()
        if unlocked_bat:seed_completed_mill(game)
        try:yield game
        finally:
            game.opening_audio.reset()
            pygame.quit()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'work/atb-combat')
    output = parser.parse_args(argv).output
    output.mkdir(parents=True, exist_ok=True)
    frames, timeline, captures, checks, actions = [], [], [], [], []
    frame_number = 0
    action_objects = []

    def key(game, value):
        for kind in (pygame.KEYDOWN, pygame.KEYUP):
            pygame.event.post(pygame.event.Event(kind, key=value, repeat=False))
        if not game.handle_events():raise RuntimeError('The combat capture was closed during input.')

    def point(game, logical):
        width, height = game.window.get_size()
        scale = max(1, min(width//480, height//320))
        return (round((width-480*scale)//2+logical[0]*scale),
                round((height-320*scale)//2+logical[1]*scale))

    def click(game, logical):
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=point(game, logical)))
        if not game.handle_events():raise RuntimeError('The combat capture was closed during click.')

    def observe_action(game):
        action = game.combat.model.current_action if game.combat.active else None
        if action is not None and not any(action is seen for seen in action_objects):
            action_objects.append(action)

    def run(game, seconds, stage, animate=True):
        nonlocal frame_number
        count = max(1, math.ceil(seconds*60))
        for _ in range(count):
            if not game.handle_events():raise RuntimeError('The combat capture was closed during animation.')
            game.update(seconds/count, (0, 0), False)
            observe_action(game)
            game.draw()
            if animate and frame_number%6 == 0:
                frame = Image.frombytes('RGB', game.ui_surface.get_size(),
                                        pygame.image.tobytes(game.ui_surface, 'RGB'))
                frames.append(frame.resize((480, 320), Image.Resampling.NEAREST))
                model = game.combat.model
                timeline.append({'frame': len(frames)-1, 'stage': stage,
                                 'phase': model.phase if model else 'exploration',
                                 'player_atb': model.player.atb if model else None,
                                 'enemy_atb': model.enemy.atb if model else None,
                                 'action': model.current_action.action
                                 if model and model.current_action else None})
            frame_number += 1

    def until(game, predicate, label, limit=6000):
        for _ in range(limit):
            if predicate():return
            run(game, 1/60, label, animate=False)
        raise AssertionError('The encounter did not reach '+label)

    def record(game, name):
        game.draw()
        pygame.image.save(game.window, str(output/(name+'.png')))
        model = game.combat.model
        captures.append({'file': name+'.png', 'window': list(game.window.get_size()),
                         'text_scale': game.audio.text_scale,
                         'phase': model.phase if model else 'exploration',
                         'player_hp': model.player.hp if model else game.attributes.current_hp,
                         'player_mp': model.player.mp if model else game.attributes.current_mp,
                         'player_atb': model.player.atb if model else None,
                         'enemy_atb_for_verification_only': model.enemy.atb if model else None})
        assert game.ui_surface.get_clip() == game.ui_surface.get_rect()

    def place(game):
        # Camera/player placement is a review fixture. Starting the encounter
        # still requires the actual E input at its real world interaction point.
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 24))
        game.player.facing = 'back'
        game.camera.reset()
        assert game.world.can_stand(game.player.position)
        assert game.combat.interaction_hint() == 'E: Engage Bat'

    def start(game):
        place(game)
        key(game, pygame.K_e)
        assert game.combat.active
        game.combat.model.rng = random.Random(7)
        game.draw()
        return game.combat.scene

    def choose(game, scene, action):
        assert scene.model.waiting_for_player
        game.draw()
        assert action in scene.command_rects
        click(game, scene.command_rects[action].center)
        observe_action(game)
        assert scene.model.current_action.action == action
        assert scene.model.phase == 'acting'

    with fixture() as game:
        place(game)
        assert game.save_progress()
        run(game, .3, 'visible Bat west of the well')
        record(game, 'eldenmere_bat')
        scene = start(game)
        model = scene.model
        world = game.elapsed_ms, list(game.player.position)
        npcs = [list(actor.position) for actor in game.persistent_npcs]
        pre_battle = game.attributes.to_dict(), game.lattice.to_dict(), game.inventory.to_dict()
        run(game, .5, 'battle scene and charging ATB')
        record(game, 'battle_charging')
        until(game, lambda: model.waiting_for_player, 'first ready command')
        before = model.player.atb, model.enemy.atb
        assert before[0] == 1 and before[1] > 0
        run(game, .8, 'player chooses while every gauge waits')
        run(game, 2.2, 'remaining decision time', animate=False)
        assert before == (model.player.atb, model.enemy.atb)
        assert model.phase == 'ready'
        assert pre_battle == (game.attributes.to_dict(), game.lattice.to_dict(), game.inventory.to_dict())
        texts = []
        original_text = Painter.text

        def visible_text(painter, text, *args, **kwargs):
            texts.append(str(text))
            return original_text(painter, text, *args, **kwargs)

        with patch.object(Painter, 'text', visible_text):game.draw()
        assert texts.count('ATB') == 1
        assert not any('Enemy ATB' in text or 'Bat ATB' in text for text in texts)
        record(game, 'battle_ready')
        checks.append({'stage': 'ready decision pauses all gauges', 'wait_seconds': 3,
                       'before': list(before), 'after': [model.player.atb, model.enemy.atb],
                       'live_journey_unchanged': True, 'visible_atb_labels': texts.count('ATB')})

        choose(game, scene, 'guard')
        run(game, .3, 'Caelan guards')
        record(game, 'caelan_guard')
        until(game, lambda: model.current_action is not None and model.current_action.actor == 'enemy',
              'Bat Bite')
        run(game, .38, 'Bat Bite and guarded hit')
        record(game, 'bat_bite')
        run(game, .3, 'Bite recovery')

        first_attack, gust_captured = True, False
        while not model.ended:
            if model.waiting_for_player:
                choose(game, scene, 'attack')
                if first_attack:
                    run(game, .24, 'Caelan attacks')
                    record(game, 'caelan_attack')
                    run(game, .5, 'Attack impact and recovery')
                    first_attack = False
                else:run(game, .75, 'Caelan attacks', animate=True)
            elif (not gust_captured and model.current_action is not None
                  and model.current_action.action == 'wing_gust'):
                run(game, .28, 'Bat Wing Gust')
                record(game, 'bat_wing_gust')
                run(game, .58, 'Wing Gust impact')
                gust_captured = True
            else:run(game, 1/60, 'charging and enemy turns', animate=False)
        assert model.phase == 'victory' and gust_captured
        assert world == (game.elapsed_ms, list(game.player.position))
        assert npcs == [list(actor.position) for actor in game.persistent_npcs]
        assert pre_battle == (game.attributes.to_dict(), game.lattice.to_dict(), game.inventory.to_dict())
        run(game, .6, 'victory and battle rewards')
        record(game, 'battle_victory')
        outcome_hp, outcome_mp = model.player.hp, model.player.mp
        until(game, lambda: game.combat.post_phase == 'spoils' and
              game.combat.spoils.awarded, 'Spoils award checkpoint')
        record(game, 'battle_spoils')
        click(game, game.combat.spoils.continue_rect.center)
        assert not game.combat.active
        assert game.lattice.state()['rp'] == 20 and game.lattice.rank() == 2
        assert game.lattice.steps() == 1 and game.inventory.quantity('aether_emerald') == 1
        assert (game.attributes.current_hp, game.attributes.current_mp) == (outcome_hp, outcome_mp)
        assert world == (game.elapsed_ms, list(game.player.position))
        snapshot = game.attributes.to_dict(), game.lattice.to_dict(), game.inventory.to_dict()
        game.combat.update(0);game.combat.update(0)
        assert snapshot == (game.attributes.to_dict(), game.lattice.to_dict(), game.inventory.to_dict())
        saved = json.loads(game.save_store.path.read_text())
        assert saved['character_attributes'] == game.attributes.to_dict()
        assert saved['aether_lattice'] == game.lattice.to_dict()
        assert saved['inventory'] == game.inventory.to_dict()
        record(game, 'return_to_eldenmere')
        run(game, .3, 'back in Eldenmere')
        checks.append({'stage': 'victory settles once', 'rp': 20, 'rank': 2, 'steps': 1,
                       'aether_emerald': 1, 'current_hp': outcome_hp, 'current_mp': outcome_mp,
                       'world_unchanged_during_battle': True, 'durable_checkpoint': True,
                       'duplicate_settlement_unchanged': True})

    # A separate, explicitly rewarded review journey learns Dart through the
    # actual lattice. It has unchanged starting attributes and ordinary MP.
    with fixture() as game:
        rp = game.lattice.board.rp_for_rank(50)
        assert game.award_battle_rewards('capture:learn-dart', {'caelan': rp}, {'aether_diamond': 1})
        assert game.move_lattice('aether_dart_01')
        assert game.activate_lattice('aether_dart_01')
        assert game.attributes.value('str') == game.attributes.value('mag') == 10
        scene = start(game);model = scene.model
        until(game, lambda: model.waiting_for_player, 'learned Dart command')
        game.windowed_size = (480, 320)
        game.window = pygame.display.set_mode((480, 320), pygame.RESIZABLE)
        game.audio.set_text_scale(1.5)
        game.draw()
        for rect in scene.command_rects.values():assert scene.panel_rect.contains(rect)
        record(game, 'minimum_window_large_text')
        choose(game, scene, 'guard')
        run(game, .55, 'minimum-window command input', animate=False)
        until(game, lambda: model.waiting_for_player, 'ready after minimum-window Guard')
        game.windowed_size = (1440, 810)
        game.window = pygame.display.set_mode((1440, 810), pygame.RESIZABLE)
        game.audio.set_text_scale(1.0)
        game.draw()
        record(game, 'letterboxed_ready')
        choose(game, scene, 'aether_dart')
        assert model.player.mp == 26 and game.attributes.current_mp == 30
        game.windowed_size = (960, 640)
        game.window = pygame.display.set_mode((960, 640), pygame.RESIZABLE)
        game.draw()
        run(game, .34, 'Caelan casts learned Aether Dart')
        record(game, 'caelan_cast')
        run(game, .6, 'Dart impact and recovery')
        until(game, lambda: model.waiting_for_player or model.ended, 'next command after Dart')
        assert not model.ended
        choose(game, scene, 'flee')
        run(game, .8, 'Flee returns safely')
        assert model.phase == 'fled'
        before_rp, before_gems = game.lattice.state()['rp'], game.inventory.quantity('aether_emerald')
        click(game, scene.continue_rect.center)
        assert not game.combat.active
        assert game.attributes.current_mp == 26
        assert (game.lattice.state()['rp'], game.inventory.quantity('aether_emerald')) == (before_rp, before_gems)
        checks.append({'stage': 'learned Dart and flee', 'training_fixture_rp': rp,
                       'learned_via_real_lattice': True, 'dart_mp_cost': 4,
                       'flee_awarded_no_rewards': True, 'minimum_window': [480, 320],
                       'large_text_scale': 1.5, 'minimum_window_guard_click': True,
                       'letterboxed_window': [1440, 810], 'letterboxed_dart_click': True})

    for action in action_objects:actions.append(asdict(action))
    # One palette keeps static scenery identical across GIF frames. Independent
    # frame palettes turn a detailed backdrop into flickering full-frame deltas.
    samples = Image.new('RGB', (120*len(frames), 80))
    for index, frame in enumerate(frames):
        samples.paste(frame.resize((120, 80), Image.Resampling.NEAREST), (index*120, 0))
    palette = samples.quantize(colors=256, dither=Image.Dither.NONE)
    gif_frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    gif_frames[0].save(output/'combat.gif', save_all=True, append_images=gif_frames[1:],
                       duration=100, loop=0, optimize=False, disposal=1)
    with Image.open(output/'combat.gif') as animation:encoded_frames = animation.n_frames
    sheet = Image.new('RGB', (480*3, 320*2))
    labels = ('battle_ready', 'caelan_guard', 'caelan_attack', 'bat_bite', 'bat_wing_gust', 'caelan_cast')
    for index, name in enumerate(labels):
        with Image.open(output/(name+'.png')) as shot:
            sheet.paste(shot.resize((480, 320), Image.Resampling.NEAREST), ((index%3)*480, (index//3)*320))
    sheet.save(output/'action_contact_sheet.png')
    metadata = {'isolated_temporary_journeys': True, 'normal_journey_and_settings_untouched': True,
                'world_bat_position': [336, 900], 'trigger': 'E within 32 world pixels',
                'fixtures': [{'name': 'starter', 'starting_hp': 140, 'starting_mp': 30,
                              'rp': 0, 'crystals': 0},
                             {'name': 'learned Dart', 'training_rp': rp,
                              'training_crystal': {'aether_diamond': 1},
                              'ability_activated_through_lattice': 'aether_dart_01'}],
                'enemy_atb_visible': False, 'checks': checks, 'actions': actions,
                'captures': captures, 'animation': {'file': 'combat.gif', 'fps': 10,
                    'rendered_frames': len(frames), 'encoded_frames': encoded_frames,
                    'logical_size': [480, 320], 'timeline': timeline}}
    (output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps({'output': str(output), 'captures': len(captures), 'checks': len(checks),
                      'rendered_frames': len(frames), 'encoded_frames': encoded_frames,
                      'gif_bytes': (output/'combat.gif').stat().st_size}))
    return 0


if __name__ == '__main__':raise SystemExit(main())
