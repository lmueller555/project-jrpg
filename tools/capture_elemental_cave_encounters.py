"""Capture optional cave guardians with production menus, timing and rendering.

Earlier MQ01/MQ02 and Aqua progression, a rested level-four party, zero Caelan
MP and near-room placement are labelled fixtures. Neither enemy HP nor combat
outcomes are edited. Every photographed attack, warning and focus installation
comes from the live Game. Pillow only arranges the resulting screenshots.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import pygame
from PIL import Image, ImageDraw, ImageFont

from elemental_bosses import REGISTRY, definition
from test_elemental_cave_gameplay import ElementalCaveGameplayTests
from test_mill_battle_gameplay import click, finish_spoils_presentation, key

OUTPUT = ROOT/'docs/reviews/elemental_cave_encounters'
SOURCE_FILES = (
    'main.py', 'world_encounters.py', 'post_battle.py', 'elemental_bosses.py',
    'elemental_boss_entry.py', 'elemental_room_fx.py', 'sanctuary_boss.py', 'battle_model.py',
    'battle_scene.py', 'battle_announcements.py', 'combat_damage.py',
    'character_abilities.py', 'gear_widget.py', 'gearblade_fx.py',
    'assets/combat/actions.json', 'assets/combat/bestiary.json',
    'assets/combat/cave_encounters.json', 'assets/maps/sanctuary_cave/map.json',
    'assets/source/maps/sanctuary_cave/recipe.json',
    'assets/source/combat/cave_battlefields/recipe.json',
    'tools/capture_elemental_cave_encounters.py', 'tools/capture_mq03_emergency.py',
    'tests/test_elemental_cave_gameplay.py', 'tests/test_mill_battle_gameplay.py',
)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    names = set(SOURCE_FILES)
    for folder in ('assets/combat/embravyr', 'assets/combat/nivareth',
                   'assets/combat/cave_embervein', 'assets/combat/cave_stillfrost',
                   'assets/source/combat/embravyr', 'assets/source/combat/nivareth',
                   'assets/maps/sanctuary_cave'):
        names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/folder).rglob('*') if path.is_file())
    return {name: digest(ROOT/name) for name in sorted(names)}


def check_review(output):
    record = json.loads((output/'verification.json').read_text())
    for name, expected in record['source_sha256'].items():
        if digest(ROOT/name) != expected:raise ValueError('Review source changed: '+name)
    for name, expected in record['artifact_sha256'].items():
        if digest(output/name) != expected:raise ValueError('Review artifact changed: '+name)
    if set(record['victories']) != set(REGISTRY):raise ValueError('The review needs both real victories')
    for enemy_id, result in record['victories'].items():
        if not result['all_five_actions_observed'] or result['outcome'] != 'victory':
            raise ValueError('The actual full combat cycle was not captured: '+enemy_id)
        if result['caelan_mp_after'] != 0:raise ValueError('The zero-MP teaching fixture changed')
        if result['exhaustion_multipliers'] != [1.5]:raise ValueError('Exhaustion evidence is incomplete')
    return len(record['captures'])


class Review:
    def __init__(self, output):
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.captures = []
        self.victories = {}
        self.seen = set()
        self.events = []

    @property
    def game(self):return self.case.game

    def photograph(self, name, label):
        if name in self.seen:return
        self.seen.add(name)
        game = self.game
        game.location_seconds = 0
        game.quest_ui.current_notice = None
        game.quest_ui.notices.clear()
        game.draw()
        pygame.image.save(game.ui_surface, self.output/name)
        model = game.combat.model
        action = model.current_action if model else None
        message = game.combat.scene.announcements.current if game.combat.scene else None
        self.captures.append({'file': name, 'label': label,
            'scene': game.world.data['id'], 'position': list(game.player.position),
            'script': game.social.script_identifier,
            'battle_phase': model.phase if model else None,
            'action': action.action if action else None,
            'action_seconds': round(action.elapsed, 3) if action else None,
            'announcement': deepcopy(message),
            'owned_gems': list(game.character_abilities.owned_gems()),
            'learned': sorted(game.character_abilities.known_abilities()),
            'selected_gem': game.character_abilities.active_gem(),
            'caelan_mp': model.player.mp if model else game.attributes.current_mp,
            'elemental_state': game.elemental_bosses.to_dict(),
            'text_scale': game.audio.text_scale})

    def tick(self, seconds=.05):self.game.update(seconds, (0, 0), False)

    def enter(self, enemy_id):
        game = self.game
        self.case.position(enemy_id)
        self.photograph(enemy_id+'_room.png', definition(enemy_id)['location']+' · live cave rendering')
        if enemy_id == 'embravyr':
            key(game, pygame.K_m)
            self.photograph('continuous_cave_map.png', 'Continuous cave · two optional branches')
            key(game, pygame.K_ESCAPE)
        self.case.offer(enemy_id)
        self.photograph(enemy_id+'_offer.png', definition(enemy_id)['name']+' · deliberate approach')
        with patch('elemental_bosses.random.SystemRandom') as source:
            source.return_value.randrange.return_value = 0
            self.case.choose('enter')
        ticket = deepcopy(game.elemental_bosses.pending)
        for _ in range(10):
            game.draw();self.tick(.05)
        self.photograph(enemy_id+'_introduction.png', definition(enemy_id)['name']+' · live chamber introduction')
        for _ in range(160):
            if game.combat.entry_phase == 'loading':break
            self.tick(.05)
        assert game.combat.entry_phase == 'loading'
        self.photograph(enemy_id+'_loading.png', definition(enemy_id)['name']+' · presented loading screen')
        game.draw();self.tick(.01)
        for _ in range(60):
            if game.combat.model is not None and not game.combat.transitioning:break
            game.draw();self.tick(.05)
        assert game.combat.model is not None and not game.combat.transitioning, getattr(game.combat.entry, 'error', None)
        self.photograph(enemy_id+'_opening.png', definition(enemy_id)['name']+' · level-four solo battle')
        return ticket

    def switch_focus(self, gem):
        game, scene = self.game, self.game.combat.scene
        if scene.model.active_gem == gem:return
        key(game, pygame.K_g)
        for _ in range(4):
            if scene.gear.preview_gem == gem:break
            key(game, pygame.K_RIGHT)
        assert scene.gear.preview_gem == gem
        key(game, pygame.K_RETURN);self.tick(.1);key(game, pygame.K_TAB)
        assert scene.model.active_gem == gem and not scene.model.gear_settling

    def choose_command(self, command, *, capture_menu=None):
        game, scene = self.game, self.game.combat.scene
        game.draw()
        if command in ('aqua_edge', 'flame_edge', 'ice_edge', 'aether_edge'):
            click(game, scene.command_rects['skills'].center);game.draw()
            if capture_menu:self.photograph(*capture_menu)
        assert not scene.model.action_reason(command), scene.model.action_reason(command)
        click(game, scene.command_rects[command].center)
        if scene._target_command is not None:key(game, pygame.K_RETURN)

    def play(self, enemy_id, ticket):
        game, owner = self.game, self.game.combat
        model, scene = owner.model, owner.scene
        actions = set(model.enemy_definition['abilities'])
        observed = set()
        recoveries = set()
        edge_used = False
        trace = []
        original = model.drain_events

        def observe():
            batch = original()
            for event in batch:
                if event['type'] in ('impact', 'action_started', 'recovery_started', 'recovery_ended', 'telegraph'):
                    trace.append(deepcopy(event))
            return batch

        with patch.object(model, 'drain_events', side_effect=observe):
            for _ in range(16000):
                action = model.current_action
                if action is not None and action.actor == 'enemy':
                    if action.action in actions and action.elapsed >= action.impact_at:
                        observed.add(action.action)
                        suffix = action.action.removeprefix(enemy_id+'_')
                        self.photograph(enemy_id+'_'+suffix+'.png', definition(enemy_id)['name']+' · '+model.actions[action.action]['name'])
                    if model.enemy_telegraphs:
                        self.photograph(enemy_id+'_charge_warning.png', 'Marked heavy hit · red charge aura')
                if model.enemy_recovery_states:
                    recoveries.update(model.enemy_recovery_states.values())
                    notice = scene.announcements.current
                    if notice is not None and '50%' in notice.get('text', ''):
                        self.photograph(enemy_id+'_exhaustion_50.png', 'Exhausted · takes 50% more damage')
                if action is not None and action.actor == 'player' and action.action in ('aqua_edge', 'flame_edge', 'ice_edge'):
                    if action.elapsed >= action.impact_at and action.resolved:
                        self.photograph(enemy_id+'_elemental_strike.png', model.actions[action.action]['name']+' · actual elemental strike')
                if model.ended:
                    assert model.phase == 'victory', {'enemy': enemy_id, 'phase': model.phase,
                        'party': [(member.identifier, member.hp) for member in model.party]}
                    break
                if scene.tutorial_active:key(game, pygame.K_SPACE)
                elif model.waiting_for_player:
                    marked = model.telegraphed_target
                    if marked in model.ready_members and model.ready_actor != marked:
                        game.draw();click(game, scene.party_rows[marked]['row'].center)
                    actor = model.ready_actor
                    command = 'guard'
                    if actor == marked:command = 'guard'
                    elif actor == 'mira':
                        command = 'guard' if observed != actions else 'attack'
                    elif actor == 'player' and (observed == actions or not edge_used):
                        command = 'aqua_edge' if enemy_id == 'embravyr' else 'flame_edge'
                        self.switch_focus('water' if command == 'aqua_edge' else 'fire')
                        if not edge_used:
                            self.choose_command(command, capture_menu=(enemy_id+'_edge_0mp.png', 'Teaching encounter · elemental Edges cost 0 MP'))
                            edge_used = True
                            continue
                    self.choose_command(command)
                else:self.tick(.05)
            else:raise AssertionError('The actual guardian encounter did not finish: '+enemy_id)
        self.case.award()
        self.photograph(enemy_id+'_spoils.png', 'Guaranteed focus · survivor EXP · actual Spoils')
        self.victories[enemy_id] = {'ticket': ticket, 'outcome': model.phase,
            'all_five_actions_observed': observed == actions, 'observed_actions': sorted(observed),
            'exhaustion_multipliers': sorted(recoveries), 'caelan_mp_after': model.player.mp,
            'party_after': self.case.resources(), 'event_trace': trace}
        assert observed == actions, {'missing_actions': sorted(actions-observed)}
        assert recoveries == {1.5} and model.player.mp == 0
        self.case.finish_spoils()
        self.acquire(enemy_id)

    def acquire(self, enemy_id):
        game = self.game
        for _ in range(200):
            if game.social.active:
                assert game.social.script_identifier == 'elemental_focus_acquisition_'+enemy_id
                line = game.social.page['source_line']
                self.tick(.1)
                if line >= (2 if enemy_id == 'embravyr' else 1):
                    self.photograph(enemy_id+'_focus_installation.png', definition(enemy_id)['gem_name']+' · actual gem seating')
                    game.audio.set_text_scale(1.5);game._ensure_ui_surface()
                    self.photograph(enemy_id+'_focus_installation_150.png', '150% text · focus installation and dialogue')
                    game.audio.set_text_scale(1);game._ensure_ui_surface()
                key(game, pygame.K_SPACE)
            else:self.tick(.05)
            if not game.elemental_bosses.bosses[enemy_id]['pending_acquisition']:break
        else:raise AssertionError('Focus presentation did not settle')
        assert definition(enemy_id)['gem'] in game.character_abilities.owned_gems()
        assert definition(enemy_id)['skill'] in game.character_abilities.known_abilities()
        self.photograph(enemy_id+'_cleared_room.png', 'Cleared chamber · permanent focus recorded once')

    def contact_sheet(self):
        thumb = (480, 320)
        row = 352
        image = Image.new('RGB', (960, ((len(self.captures)+1)//2)*row), '#132c25')
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
        for index, record in enumerate(self.captures):
            x, y = index%2*480, index//2*row
            label = record['label']
            while draw.textlength(label, font=font) > 464:label = label[:-2]+'…'
            draw.text((x+8, y+5), label, fill='#efd38c', font=font)
            frame = Image.open(self.output/record['file']).convert('RGB')
            frame.thumbnail(thumb, Image.Resampling.NEAREST)
            image.paste(frame, (x, y+30))
        image.save(self.output/'contact_sheet.png', optimize=True)

    def run(self):
        ElementalCaveGameplayTests.setUpClass()
        self.case = ElementalCaveGameplayTests()
        try:
            self.case.setUp()
            self.game.attributes.set_current(mp=0)
            assert self.game.save_progress()
            story_before = self.case.story()
            for enemy_id in ('embravyr', 'nivareth'):
                ticket = self.enter(enemy_id)
                self.play(enemy_id, ticket)
            assert self.case.story() == story_before
            assert set(self.game.character_abilities.owned_gems()) == {'water', 'fire', 'ice'}
            assert self.game.elemental_bosses.victory_order == ['embravyr', 'nivareth']
            final = self.case.durable()
            assert self.game.save_progress()
            self.case.game = self.case.load()
            assert self.case.durable() == final
            self.contact_sheet()
            banks = {}
            for enemy_id in REGISTRY:
                manifest = json.loads((ROOT/'assets/combat'/enemy_id/'animation.json').read_text())
                banks[enemy_id] = {'manifest': 'assets/combat/'+enemy_id+'/animation.json',
                    'authored_frames': manifest.get('authored_frames'),
                    'states': {key: len(value['frames']) for key, value in manifest['animations'].items()},
                    'full_runtime_sheet': 'assets/combat/'+enemy_id+'/'+manifest['sheet'],
                    'source_sheets': manifest.get('source_sha256', {})}
            record = {'fixtures': [
                'Earlier MQ01/MQ02 completion and Aqua discovery are explicitly initialized; MQ03 departure and Sanctuary arrival use production dialogue/travel.',
                'The actual Caelan/Mira story pair receives EXP through public progression APIs to start rested at level four; Caelan MP is explicitly set to zero.',
                'Near-room placement and fixed entry seed 0 shorten setup only. All combat commands use actual menu/mouse/keyboard input; no enemy HP or outcomes are edited.',
                'Both fights carry actual remaining HP/MP and earned EXP forward; post-Spoils focus presentations are acknowledged normally.',
                'Text size changes to 150% only for labelled installation screenshots, then returns to 100%.'],
                'synthetic_attack_poses': False, 'disposable_saves_and_settings': True,
                'captures': self.captures, 'victories': self.victories,
                'animation_banks': banks, 'final': final,
                'source_sha256': source_hashes(),
                'artifact_sha256': {entry['file']: digest(self.output/entry['file']) for entry in self.captures}}
            record['artifact_sha256']['contact_sheet.png'] = digest(self.output/'contact_sheet.png')
            (self.output/'verification.json').write_text(json.dumps(record, indent=2)+'\n')
        finally:self.case.doCleanups()
        return len(self.captures)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    count = check_review(args.output) if args.check else Review(args.output).run()
    print(('Verified ' if args.check else 'Captured ')+str(count)+' actual elemental encounter images')


if __name__ == '__main__':main()
