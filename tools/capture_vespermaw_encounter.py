"""Review the live Echo Chamber encounter with a disposable production Game.

Earlier quests and level-seven starting resources are labelled review fixtures.
The MQ03 departure, cave entry, boss offer, combat commands and spoils use the
game. No save or settings outside a temporary directory is read or changed.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFont

from leveling import CharacterLevel, character_stats, total_xp_for_level
from sanctuary_cave import RESERVE_ENTRY_APPROACH
from tools.capture_mq03_emergency import Driver


OUTPUT = ROOT/'docs/reviews/vespermaw_encounter'
SOURCE_FILES = (
    'main.py', 'sanctuary_boss.py', 'world_encounters.py', 'post_battle.py',
    'sanctuary_boss_entry.py',
    'battle_model.py', 'battle_scene.py', 'combat_damage.py',
    'cave_battlefield.py', 'cave_battle_entry.py', 'game_music.py',
    'assets/combat/bestiary.json', 'assets/combat/actions.json',
    'assets/combat/vespermaw/animation.json', 'assets/combat/cave_echo_chamber/battlefield.json',
    'tools/capture_vespermaw_encounter.py')


def digest(path):return sha256(path.read_bytes()).hexdigest()


def sources():
    names = set(SOURCE_FILES)
    for folder in ('assets/combat/cave_echo_chamber', 'assets/story/sanctuary_boss'):
        names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/folder).rglob('*') if path.is_file())
    return {name: digest(ROOT/name) for name in sorted(names) if (ROOT/name).is_file()}


def durable_story(game):
    return deepcopy({'regent': game.regent_quest.to_dict(), 'quests': game.quests.to_dict(),
                     'event': game.party.current_event_id, 'members': game.party.members,
                     'active': list(game.party.active_ids), 'music': game.music.desired_track,
                     'treasure': game.sanctuary_cave.to_dict(),
                     'random_encounters': game.cave_random_encounters.to_dict()})


class Review:
    def __init__(self, output):
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.captures = []
        self.capture_prefix = ''

    def key(self, key):
        assert self.game.handle_events([
            pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False),
            pygame.event.Event(pygame.KEYUP, key=key)])

    def tick(self, seconds=.05):self.game.update(seconds, (0, 0), False)

    def photograph(self, name, label):
        game = self.game
        name = self.capture_prefix+name
        if self.capture_prefix:label = 'Low-HP retry fixture · '+label
        game.location_seconds = 0
        game.quest_ui.current_notice = None
        game.quest_ui.notices.clear()
        game.draw()
        pygame.image.save(game.window, self.output/name)
        model = game.combat.model
        self.captures.append({'file': name, 'label': label,
            'scene': game.world.data['id'], 'position': list(game.player.position),
            'script': game.social.script_identifier,
            'battle_phase': model.phase if model is not None else None,
            'boss': game.sanctuary_boss.to_dict()})

    def choices(self):
        game = self.game
        for _ in range(40):
            if game.social.choosing:break
            assert game.social.active, 'The expected boss choice is unavailable'
            self.key(pygame.K_SPACE)
        assert game.social.choosing
        game.draw()

    def choose(self, action):
        game = self.game
        self.choices()
        options = game.social.choice_options
        index = next(index for index, option in enumerate(options) if option['action'] == action)
        rect = game.social.choice_rects[index]
        _, size, origin = game._ensure_ui_surface()
        point = (round(origin[0]+rect.centerx*size[0]/480),
                 round(origin[1]+rect.centery*size[1]/320))
        assert game.handle_events([
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point),
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point)])

    def seed(self, directory):
        driver = Driver(directory)
        driver.meal();driver.attack_report();driver.departure();driver.rejoin_mira();driver.arrive()
        game = self.game = driver.game
        game.window = pygame.display.set_mode((960, 640), pygame.RESIZABLE)
        game.windowed_size = (960, 640)
        game.audio.set_text_scale(1)
        game._ensure_ui_surface()
        # Fixture levels/resources are explicit; no additional companion joins.
        for identifier in game.party.active_ids:
            attributes = game.party.characters[identifier]
            attributes._attributes = character_stats(identifier, 7)
            attributes.recover()
            game.character_progression.records[identifier] = CharacterLevel(
                identifier, total_xp_for_level(7))
        driver.walk(RESERVE_ENTRY_APPROACH)
        self.key(pygame.K_e)
        assert game.world.data['id'] == 'sanctuary_cave'
        for _ in range(30):self.tick()
        game.social.cancel()
        game.opening_fade = game.transfer_cooldown = 0
        game.party_travel.reset();game.camera.reset()
        return driver

    def enter(self):
        from sanctuary_boss import APPROACH
        game = self.game
        assert game.world.can_stand(APPROACH)
        # A labelled near-arena placement avoids a second full dungeon walk;
        # the offer and all subsequent entry/combat input remain production.
        game.player.position.update(APPROACH)
        game.player.facing = 'back'
        game.player.moving = game.player.running = False
        game.party_travel.reset();game.camera.reset()
        self.key(pygame.K_e)
        for _ in range(30):
            if game.social.choosing:break
            self.key(pygame.K_SPACE)
        self.photograph('approach_offer.png', 'Echo Chamber approach · deliberate entry')
        # Preserve the real entry path while making the opening review repeatable.
        with patch('sanctuary_boss.random.SystemRandom') as generator:
            generator.return_value.randrange.return_value = 7
            self.choose('enter')
        assert game.combat.kind == 'cave_boss'
        for _ in range(12):self.tick()
        if game.combat.entry is not None:
            self.photograph('introduction.png', 'Crystal-and-growl introduction · production entry')
        for _ in range(300):
            if game.combat.model is not None and not game.combat.transitioning:break
            if game.social.active and not game.social.choosing:self.key(pygame.K_SPACE)
            game.draw()  # Loading must be presented before its owner installs combat.
            self.tick()
        assert game.combat.model is not None and not game.combat.transitioning, {
            'entry_phase': game.combat.entry_phase,
            'entry_error': getattr(game.combat.entry, 'error', None),
            'save_error': game.save_error, 'boss': game.sanctuary_boss.to_dict()}
        assert game.combat.model.enemy.hp == 1877
        self.photograph('battle_opening.png', 'Live level-seven boss · authentic two-member outing')

    def play(self):
        game = self.game
        observed = set()
        for _ in range(18000):
            model = game.combat.model
            if model is None:
                self.tick()
                continue
            if game.combat.post_phase == 'spoils':
                self.photograph('spoils.png', 'Victory rewards · actual surviving active party')
                return observed
            action = model.current_action
            if action is not None and action.actor == 'enemy':
                name = action.action.removeprefix('vespermaw_')
                if name not in observed and action.resolved:
                    observed.add(name)
                    self.photograph(name+'.png', 'Live combat · '+name.replace('_', ' '))
            if model.waiting_for_player:
                target = model.telegraphed_target
                if target in model.ready_members:model.select_ready(target)
                actor = model.ready_actor
                if actor == model.telegraphed_target:
                    command = 'guard'
                elif actor == 'mira' and 'overclock' in model.available_actions():
                    bot = model.active_bot()
                    command = ('overclock' if bot is not None and not bot.haste_turns
                               and not model.action_reason('overclock') else 'attack')
                elif actor == 'player' and 'aether_edge' in model.available_actions():
                    command = 'aether_edge' if not model.action_reason('aether_edge') else 'attack'
                else:command = 'attack'
                assert model.choose_action(command)
            self.tick()
        raise AssertionError('The live boss fight did not finish')

    def finish_spoils(self):
        game = self.game
        for _ in range(240):
            if game.combat.spoils is None:return
            self.key(pygame.K_RETURN)
            self.tick(.1)
        raise AssertionError('Spoils did not return to the cleared chamber')

    def defeat_and_return(self, journey, directory):
        from main import Game
        from sanctuary_boss import RETREAT
        path = Path(directory)/'low-hp-journey.json'
        path.write_text(json.dumps(journey))
        self.game = game = Game(window_size=(960, 640), fullscreen=False,
            start_on_title=True, save_path=path,
            settings_path=Path(directory)/'low-hp-settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        assert game.begin_journey(True), game.save_error
        game.opening_fade = game.transfer_cooldown = 0
        for identifier in game.party.active_ids:
            game.party.characters[identifier].set_current(hp=1, mp=0)
        before_xp = game.character_progression.to_dict()
        before_items = game.inventory.to_dict()
        self.capture_prefix = 'defeat_'
        self.enter()

        def lose():
            for _ in range(6000):
                if not game.combat.active and game.social.script_identifier == 'sanctuary_boss_defeat':return
                model = game.combat.model
                if model is not None:
                    if model.waiting_for_player:assert model.choose_action('attack')
                    elif model.phase == 'defeat':self.key(pygame.K_RETURN)
                game.draw();self.tick()
            raise AssertionError('The low-HP fixture did not reach the production defeat choice')

        lose()
        self.choices()
        self.photograph('choice.png', 'Retry or return after actual defeat')
        self.choose('retry')
        for _ in range(240):
            if game.combat.model is not None and not game.combat.transitioning:break
            game.draw();self.tick()
        assert game.combat.model is not None
        assert all((member.hp, member.mp) == (1, 0) for member in game.combat.model.party)
        self.photograph('retry.png', 'Retry preserves captured entry HP/MP')
        lose()
        self.choose('return')
        self.tick()
        self.photograph('quiet_shelf.png', 'Safe return with boss unbeaten and no reward')
        assert tuple(game.player.position) == RETREAT
        assert not game.sanctuary_boss.defeated and game.sanctuary_boss.pending is None
        assert all((game.party.characters[key].current_hp, game.party.characters[key].current_mp)
                   == (1, 0) for key in game.party.active_ids)
        assert game.character_progression.to_dict() == before_xp
        assert game.inventory.to_dict() == before_items
        return {'retry_entry_resources': {'hp': 1, 'mp': 0},
                'returned_to_quiet_shelf': True, 'defeated': False,
                'pending': None, 'xp_and_inventory_unchanged': True}

    def contact_sheet(self):
        count = len(self.captures)
        sheet = Image.new('RGB', (960, ((count+1)//2)*348), '#10271f')
        draw = ImageDraw.Draw(sheet)
        try:font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
        except OSError:font = ImageFont.load_default()
        for index, capture in enumerate(self.captures):
            x, y = (index%2)*480, (index//2)*348
            caption = capture['label']
            while draw.textlength(caption, font=font) > 468:
                caption = caption[:-2].rstrip()+'…'
            draw.text((x+6, y+4), caption, fill='#efd38c', font=font)
            image = Image.open(self.output/capture['file']).convert('RGB')
            image.thumbnail((480, 320), Image.Resampling.NEAREST)
            sheet.paste(image, (x, y+28))
        sheet.save(self.output/'contact_sheet.png')

    def run(self):
        with tempfile.TemporaryDirectory(prefix='vespermaw-live-review-') as directory:
            driver = self.seed(directory)
            game = self.game
            assert game.save_progress()
            entry_journey = json.loads(driver.save.read_text())
            before_story = durable_story(game)
            before_xp = {key: game.character_progression[key].total_xp for key in game.party.active_ids}
            before_items = {key: game.inventory.quantity(key) for key in ('aether_amethyst', 'aether_sapphire')}
            self.enter()
            observed = self.play()
            self.finish_spoils()
            self.photograph('cleared_chamber.png', 'One-time victory · chamber cleared')
            assert game.sanctuary_boss.to_dict()['defeated']
            assert game.sanctuary_boss.pending is None
            assert durable_story(game) == before_story
            assert all(game.inventory.quantity(key) == value+1 for key, value in before_items.items())
            rewards = {key: game.character_progression[key].total_xp-before_xp[key] for key in before_xp}
            assert game.save_progress()
            assert game._read_saved_journey() is not None, game.save_error
            defeat_check = self.defeat_and_return(entry_journey, directory)
            metadata = {'fixture': 'Earlier quest fixture followed by real MQ03 travel; level7 resources and near-arena location are review fixtures. No additional companion is recruited.',
                'captures': self.captures, 'observed_enemy_actions': sorted(observed),
                'xp_gained': rewards, 'story_unchanged': True,
                'low_hp_defeat_fixture': defeat_check, 'source_sha256': sources()}
            self.contact_sheet()
            metadata['artifact_sha256'] = {path.name: digest(path) for path in sorted(self.output.iterdir())
                                           if path.is_file() and path.name != 'verification.json'}
            (self.output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
        pygame.quit()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    if args.check:
        record = json.loads((args.output/'verification.json').read_text())
        assert record['source_sha256'] == sources(), 'Live review production sources changed'
        for name, expected in record['artifact_sha256'].items():
            assert digest(args.output/name) == expected, 'Live review artifact changed: '+name
        print('Vespermaw live encounter review verified.')
    else:
        Review(args.output).run()
        print('Captured the live Vespermaw encounter in '+str(args.output))
    return 0


if __name__ == '__main__':raise SystemExit(main())
