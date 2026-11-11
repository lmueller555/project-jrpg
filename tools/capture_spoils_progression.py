"""Render disposable progression fixtures with the production Spoils and menus.

These screenshots exercise presentation, not a claim that the depicted XP was
earned through gameplay. All party levels, rewards and damage are explicit
review fixtures; no player journey or settings outside a temporary folder is
read or written. Runtime rendering and input handlers are otherwise unchanged.
"""
from __future__ import annotations

import argparse
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

import pygame
from PIL import Image, ImageDraw, ImageFont

from battle_model import BattleModel
from battle_scene import BattleScene
from character_attributes import ATTRIBUTE_IDS
from leveling import CharacterLevel, character_stats, total_xp_for_level
from main import Game
from spoils_scene import SpoilsScene
from ui_style import Painter


class Review:
    def __init__(self, output):
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.captures = []

    def size(self, size=(960, 640), text_scale=1.0):
        self.game.window = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.game.windowed_size = size
        self.game.audio.set_text_scale(text_scale)
        self.game._ensure_ui_surface()

    def capture(self, name, draw, *, label):
        game = self.game
        _, _, origin = game._ensure_ui_surface()
        texts = []
        original = Painter.text

        def record(painter, content, *args, **kwargs):
            texts.append({'text': str(content), 'color': str(kwargs.get('color', 'default'))})
            return original(painter, content, *args, **kwargs)

        game.ui_surface.fill('#10271f')
        with patch.object(Painter, 'text', record):
            draw()
        game.window.fill('#101b19')
        game.window.blit(game.ui_surface, origin)
        target = self.output/name
        pygame.image.save(game.window, str(target))
        record = {'file': name, 'label': label, 'window': list(game.window.get_size()),
                  'text_scale': game.audio.text_scale, 'drawn_text': texts}
        self.captures.append(record)
        return record

    @staticmethod
    def confirm(scene):
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, repeat=False))
        scene.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_RETURN))

    def set_level(self, identifier, level, into=0):
        game = self.game
        old = game.character_progression.records[identifier]
        before = character_stats(identifier, old.level)
        after = character_stats(identifier, level)
        gains = {key: after[key]-before[key] for key in ATTRIBUTE_IDS}
        assert game.party.characters[identifier].apply_growth(gains)
        game.character_progression.records[identifier] = CharacterLevel(
            identifier, total_xp_for_level(level)+into)

    def battle(self):
        game = self.game
        model = BattleModel.from_bestiary_group(
            game.attributes,
            [{'enemy_id': 'cave_bat', 'level': 3},
             {'enemy_id': 'lithrusk', 'level': 3}],
            party_members=game.party.battle_members(),
            learned_abilities=game.character_abilities.known_abilities(),

            rng=random.Random(73))
        scene = BattleScene(game, model, battlefield='cave_grotto')
        for enemy in model.enemies:
            enemy.hp = 0
        model._result('victory')
        scene.draw(game.canvas, game.ui_surface)
        return model, scene

    def spoils(self, amount, *, end_hp=None, items=True):
        game = self.game
        model, background = self.battle()
        if end_hp is None:
            end_hp = {identifier: game.party.characters[identifier].current_hp
                      for identifier in game.party.active_ids}
        plan = game.character_progression.preview(amount, game.party.active_ids, end_hp)
        drops = {'aether_emerald': 2, 'aether_sapphire': 1} if items else {}
        loot = ({'offered': {'aether_emerald': 3, 'aether_sapphire': 1},
                 'received': drops, 'lost': {'aether_emerald': 1}} if items else
                {'offered': {}, 'received': {}, 'lost': {}})
        scene = SpoilsScene(game, {'drops': drops}, party=model.party, model=model,
                            progression=plan, background=background, loot=loot)
        scene.set_awarded()
        return scene, plan

    def run(self):
        with tempfile.TemporaryDirectory(prefix='spoils-progression-review-') as directory:
            folder = Path(directory)
            game = self.game = Game(window_size=(960, 640), fullscreen=False,
                start_on_title=False, save_path=folder/'journey.json',
                settings_path=folder/'settings.json')
            game.audio.set_music(0)
            game.audio.set_effects(0)
            game.opening_fade = game.transfer_cooldown = 0
            for identifier in ('mira', 'lucan'):
                assert game.party.recruit(identifier)
            assert game.party.select(('caelan', 'mira', 'lucan'))
            self.set_level('caelan', 3, 440)
            self.set_level('mira', 4, 50)
            self.set_level('lucan', 6, 35)
            game.party.characters['caelan'].set_current(hp=94, mp=11)
            game.party.characters['mira'].set_current(hp=107, mp=9)
            game.party.characters['lucan'].set_current(hp=96, mp=6)

            spoils, plan = self.spoils(840)
            spoils.update(.7)
            self.capture('spoils_progress.png', lambda:spoils.draw(game.canvas, game.ui_surface),
                         label='EXP animation · 960 × 640')
            spoils.update(3)
            assert spoils.level_up is not None
            first_levelup = dict(spoils.level_up)
            assert first_levelup['new_level']-first_levelup['old_level'] >= 2
            self.capture('level_up_caelan.png', lambda:spoils.draw(game.canvas, game.ui_surface),
                         label='Multiple levels · aggregate stat gains')
            self.size((480, 320), 1.5)
            level_top = self.capture('level_up_large_text.png',
                lambda:spoils.draw(game.canvas, game.ui_surface),
                label='Level-up sheet · 480 × 320 · text 150%')
            spoils.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEDOWN, repeat=False))
            spoils.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_PAGEDOWN))
            level_middle = self.capture('level_up_stats_middle_large.png',
                lambda:spoils.draw(game.canvas, game.ui_surface),
                label='Stat rows · large text · Page Down')
            spoils.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END, repeat=False))
            spoils.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_END))
            level_bottom = self.capture('level_up_stats_bottom_large.png',
                lambda:spoils.draw(game.canvas, game.ui_surface),
                label='All stat rows accessible · large text · End')
            shown = {entry['text'] for record in (level_top, level_middle, level_bottom)
                     for entry in record['drawn_text']}
            labels = {game.attributes.definitions[key]['label'] for key in ATTRIBUTE_IDS}
            assert labels <= shown, 'Level-up scrolling must expose every stat'
            assert any(entry['color'] == '#000000'
                       for entry in level_top['drawn_text']), 'Old values must be black'
            self.size()
            while spoils.level_up is not None:
                self.confirm(spoils)
            assert spoils.presentation_complete
            self.capture('spoils_complete.png', lambda:spoils.draw(game.canvas, game.ui_surface),
                         label='Final EXP totals and items')

            # Apply once so the real menus display the same reviewed gains.
            assert game.character_progression.apply(plan)
            game.party_ui.open()
            self.capture('party_levels.png', lambda:game.party_ui.draw(game.ui_surface),
                         label='Party formation and roster levels')
            self.size((480, 320), 1.5)
            self.capture('party_levels_large_text.png', lambda:game.party_ui.draw(game.ui_surface),
                         label='Party levels · 480 × 320 · text 150%')
            self.size()
            game.party_ui.reset()
            game.status_ui.open()
            assert game.status_ui.select_character('mira')
            self.capture('characters_mira.png', lambda:game.status_ui.draw(game.ui_surface),
                         label='Characters · Mira · EXP and level')
            self.size((480, 320), 1.5)
            self.capture('characters_large_text.png', lambda:game.status_ui.draw(game.ui_surface),
                         label='Characters · 480 × 320 · text 150%')
            game.status_ui.reset()
            self.size()

            # Separate explicit fixture for a capped character and a KO member.
            self.set_level('caelan', 100)
            game.party.characters['mira'].set_current(hp=0)
            state, cap_plan = self.spoils(84, items=False)
            state.update(3)
            while state.level_up is not None:
                self.confirm(state)
            self.capture('spoils_ko_max.png', lambda:state.draw(game.canvas, game.ui_surface),
                         label='MAX level · KO · no item drops')
            self.size((480, 320), 1.5)
            self.capture('spoils_ko_max_large_text.png', lambda:state.draw(game.canvas, game.ui_surface),
                         label='MAX and KO · 480 × 320 · text 150%')

            metadata = {'fixture': 'Explicit disposable review levels, XP and rewards; not gameplay-earned',
                        'progression': plan, 'cap_progression': cap_plan,
                        'first_levelup': first_levelup, 'captures': self.captures}
            (self.output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
            self.contact_sheet()
            game.music.stop()
            game.opening_audio.reset()
            pygame.quit()

    def contact_sheet(self):
        selected = self.captures
        width, cell_width, cell_height = 980, 490, 350
        rows = (len(selected)+1)//2
        sheet = Image.new('RGB', (width, rows*cell_height), '#142b25')
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'), 14)
        for index, record in enumerate(selected):
            x, y = (index % 2)*cell_width, (index//2)*cell_height
            picture = Image.open(self.output/record['file']).convert('RGB')
            picture.thumbnail((480, 320), Image.Resampling.NEAREST)
            sheet.paste(picture, (x+(cell_width-picture.width)//2, y+22))
            draw.text((x+8, y+3), record['label'], fill='#e8cc7a', font=font)
        sheet.save(self.output/'contact_sheet.png')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=ROOT/'docs/reviews/spoils_progression')
    args = parser.parse_args(argv)
    Review(args.output).run()
    print(f'Captured Spoils and progression menus in {args.output}')


if __name__ == '__main__':main()
