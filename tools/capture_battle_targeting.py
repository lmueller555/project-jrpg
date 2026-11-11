"""Capture disposable battle-targeting fixtures with production rendering.

The party composition, enemy formation and full ATB are explicit review
fixtures. This tool does not read or change a player's journey. The sprites,
UI rendering, target selection and enemy-click input use the game itself.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFont

from battle_model import BattleModel
from battle_scene import BattleScene
from main import Game


MIXED = [
    {'enemy_id': 'cave_bat', 'level': 3},
    {'enemy_id': 'cave_bat', 'level': 3},
    {'enemy_id': 'lithrusk', 'level': 3},
    {'enemy_id': 'veylume', 'level': 4},
]


class Review:
    def __init__(self, output):
        self.output = output
        self.output.mkdir(parents=True, exist_ok=True)
        self.captures = []
        self.checks = []

    def size(self, dimensions=(960, 640), text_scale=1):
        game = self.game
        game.window = pygame.display.set_mode(dimensions, pygame.RESIZABLE)
        game.windowed_size = dimensions
        game.audio.set_text_scale(text_scale)
        game._ensure_ui_surface()

    def scene(self, *, enemy=None, members=None):
        game = self.game
        options = dict(party_members=game.party.battle_members(),
                       learned_abilities=['aether_edge'], weapon_equipped=True,
                       initial_atb=False, rng=random.Random(37))
        if members is not None:
            model = BattleModel.from_bestiary_group(game.attributes, members, **options)
            battlefield = 'cave_hollow'
        else:
            model = BattleModel(game.attributes, enemy_id=enemy or 'bat', **options)
            battlefield = 'millrace' if enemy == 'ridgeback_tusker' else 'eldenmere'
        for actor in (*model.party, *model.enemies):
            actor.atb = 0
        model.player.atb = 1
        scene = BattleScene(game, model, battlefield=battlefield)
        scene.update(0)
        assert model.waiting_for_player
        return scene

    def capture(self, scene, filename, label):
        game = self.game
        scene.draw(game.canvas, game.ui_surface)
        _, _, origin = game._ensure_ui_surface()
        game.window.fill('#101b19')
        game.window.blit(game.ui_surface, origin)
        pygame.image.save(game.window, str(self.output/filename))
        record = {'file': filename, 'label': label,
                  'window': list(game.window.get_size()),
                  'text_scale': game.audio.text_scale,
                  'selected_enemy': scene.model.selected_target,
                  'phase': scene.model.phase,
                  'enemy_bodies': {key: list(rect) for key, rect in scene.enemy_rects.items()},
                  'enemy_headers': {key: list(row['row']) for key, row in scene.enemy_rows.items()},
                  'hud': list(scene.panel_rect)}
        marker = getattr(scene, 'target_marker_rects', None)
        if marker is not None:
            record['marker'] = {key: list(rect) if isinstance(rect, pygame.Rect) else rect
                                for key, rect in marker.items()}
        self.captures.append(record)
        return record

    def window_point(self, logical):
        _, size, origin = self.game._ensure_ui_surface()
        return (round(origin[0]+logical[0]*size[0]/480),
                round(origin[1]+logical[1]*size[1]/320))

    def click(self, scene, logical):
        point = self.window_point(logical)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            scene.handle_event(pygame.event.Event(kind, button=1, pos=point))

    def verify_marker(self, scene):
        marker = getattr(scene, 'target_marker_rects', None)
        if marker is None:
            return
        if not marker:
            assert scene.model.phase != 'ready' or scene.paused or not scene.focused
            return
        body = scene.enemy_rects[scene.model.selected_target]
        ring, finger = marker['ring'], marker['finger']
        field = pygame.Rect(0, 0, 480, scene.panel_rect.top)
        assert field.contains(finger), ('finger outside field', finger)
        assert field.contains(ring), ('ring outside field', ring)
        assert finger.bottom <= body.top, ('finger covers sprite', finger, body)
        assert not any(finger.colliderect(row[key])
                       for row in scene.enemy_rows.values() for key in ('name', 'hp', 'atb')), \
            ('finger covers enemy status', finger)
        self.checks.append({'target': scene.model.selected_target,
                            'finger_above_body': True, 'markers_inside_field': True,
                            'finger_clear_of_headers': True})

    def run(self):
        with tempfile.TemporaryDirectory(prefix='battle-target-review-') as directory:
            folder = Path(directory)
            game = self.game = Game(window_size=(960, 640), fullscreen=False,
                start_on_title=False, save_path=folder/'journey.json',
                settings_path=folder/'settings.json')
            game.audio.set_music(0)
            game.audio.set_effects(0)
            for identifier in ('mira', 'lucan'):
                assert game.party.recruit(identifier)
            assert game.party.select(('caelan', 'mira', 'lucan'))

            for enemy, filename, label in (
                    ('bat', 'single_bat.png', 'Bat · finger above, ring on the ground'),
                    ('ridgeback_tusker', 'single_tusker.png', 'Tusker · large silhouette')):
                scene = self.scene(enemy=enemy)
                self.capture(scene, filename, label)
                self.verify_marker(scene)

            scene = self.scene(members=MIXED)
            for target, filename, label in (
                    ('enemy', 'mixed_bat.png', 'Mixed formation · Cave Bat selected'),
                    ('enemy_3', 'mixed_lithrusk.png', 'Mixed formation · Lithrusk selected'),
                    ('enemy_4', 'mixed_veylume.png', 'Mixed formation · Veylume selected')):
                assert scene.model.select_target(target)
                self.capture(scene, filename, label)
                self.verify_marker(scene)

            self.click(scene, scene.command_rects['skills'].center)
            skill = scene.command_rects['aether_edge'].center
            scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION,
                pos=self.window_point(skill), rel=(0, 0), buttons=(0, 0, 0)))
            assert scene._target_command is None
            before_mp = scene.model.player.mp
            scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION,
                pos=self.window_point(scene.enemy_rects['enemy_4'].center),
                rel=(0, 0), buttons=(0, 0, 0)))
            assert scene.model.current_action is None and scene.model.player.mp == before_mp
            self.capture(scene, 'selected_skill.png', 'Highlighted skill · click a foe to cast')
            self.verify_marker(scene)
            self.click(scene, scene.enemy_rects['enemy_4'].center)
            action = scene.model.current_action
            assert action is not None and action.action == 'aether_edge'
            assert action.target == 'enemy_4'
            assert scene.model.player.mp == before_mp-4
            self.capture(scene, 'clicked_skill.png', 'Enemy click · Aether Edge executes once')
            assert not scene.target_marker_rects, 'The selector must hide while an action executes'
            self.checks.append({'clicked_skill': action.action, 'clicked_enemy': action.target,
                                'mp_spent': before_mp-scene.model.player.mp})

            scene = self.scene(members=[{'enemy_id': 'cave_bat', 'level': 3}]*4)
            assert scene.model.select_target('enemy_3')
            self.capture(scene, 'four_bats.png', 'Four Bats · distinct selected enemy')
            self.verify_marker(scene)

            self.size((480, 320), 1.5)
            scene = self.scene(members=MIXED)
            assert scene.model.select_target('enemy_4')
            self.capture(scene, 'mixed_large_text.png', 'Mixed formation · 480 × 320 · text 150%')
            self.verify_marker(scene)
            scene = self.scene(enemy='ridgeback_tusker')
            self.capture(scene, 'tusker_large_text.png', 'Tusker · 480 × 320 · text 150%')
            self.verify_marker(scene)

            metadata = {'fixture': 'Disposable ready-party and enemy-formation review fixtures',
                        'captures': self.captures, 'checks': self.checks}
            (self.output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
            self.contact_sheet()
            game.music.stop()
            game.combat.stop_audio()
            pygame.quit()

    def contact_sheet(self):
        columns, cell_width, cell_height = 2, 490, 350
        sheet = Image.new('RGB', (columns*cell_width,
            ((len(self.captures)+columns-1)//columns)*cell_height), '#142b25')
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'), 14)
        for index, record in enumerate(self.captures):
            x, y = index % columns*cell_width, index // columns*cell_height
            picture = Image.open(self.output/record['file']).convert('RGB')
            picture.thumbnail((480, 320), Image.Resampling.NEAREST)
            sheet.paste(picture, (x+(cell_width-picture.width)//2, y+22))
            draw.text((x+8, y+3), record['label'], fill='#e8cc7a', font=font)
        sheet.save(self.output/'contact_sheet.png')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/reviews/battle_targeting')
    args = parser.parse_args(argv)
    Review(args.output).run()
    print(f'Captured battle targeting review in {args.output}')


if __name__ == '__main__':
    main()
