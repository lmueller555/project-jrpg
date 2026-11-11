"""Render disposable combat-information fixtures through the production scene.

NPC action scheduling and ATB are explicit review fixtures. Preparation,
resolution, announcement delivery, aura drawing, and release use the real
BattleModel/BattleScene. No player journey or settings are read or changed.
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
from PIL import Image, ImageDraw

from battle_model import BattleModel
from battle_scene import BattleScene
from main import Game
from ui_style import Painter


MIXED = [
    {'enemy_id': 'cave_bat', 'level': 3},
    {'enemy_id': 'lithrusk', 'level': 3},
    {'enemy_id': 'veylume', 'level': 4},
    {'enemy_id': 'veylume', 'level': 4},
]


class Review:
    def __init__(self, output):
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.captures = []
        self.checks = []

    def size(self, dimensions=(960, 640), text_scale=1):
        game = self.game
        game.window = pygame.display.set_mode(dimensions, pygame.RESIZABLE)
        game.windowed_size = dimensions
        game.audio.set_text_scale(text_scale)
        game._ensure_ui_surface()

    @staticmethod
    def clear_gauges(scene):
        for actor in (*scene.model.party, *scene.model.enemies):
            actor.atb = 0

    def scene(self, *, tusker=False, mixed=False):
        game = self.game
        options = dict(party_members=game.party.battle_members(),
                       learned_abilities=['aether_edge'], weapon_equipped=True,
                       initial_atb=False, rng=random.Random(47))
        if mixed:
            model = BattleModel.from_bestiary_group(game.attributes, MIXED, **options)
            battlefield = 'cave_hollow'
        else:
            model = BattleModel(game.attributes,
                                enemy_id='ridgeback_tusker' if tusker else 'bat',
                                **options)
            battlefield = 'millrace' if tusker else 'eldenmere'
        scene = BattleScene(game, model, battlefield=battlefield)
        self.clear_gauges(scene)
        scene.update(0)
        scene.announcements.clear()
        return scene

    def start(self, scene, actor, action, target=None):
        self.clear_gauges(scene)
        scene.model._start_action(actor, action, target_id=target)
        scene.update(0)
        assert scene.model.current_action.action == action
        return scene.model.current_action

    def prepare(self, scene, actor, action):
        current = self.start(scene, actor, action)
        scene.update(current.duration)
        self.clear_gauges(scene)
        assert actor in scene.model.enemy_telegraphs

    def ready(self, scene, seconds=3):
        self.clear_gauges(scene)
        scene.model.player.atb = 1
        scene.update(0)
        assert scene.model.waiting_for_player
        scene.update(seconds)

    def render(self, scene):
        game = self.game
        scene.draw(game.canvas, game.ui_surface)
        _, _, origin = game._ensure_ui_surface()
        game.window.fill('#101b19')
        game.window.blit(game.ui_surface, origin)
        return Image.frombytes('RGB', game.window.get_size(),
                               pygame.image.tobytes(game.window, 'RGB'))

    def capture(self, scene, filename, label, *, expected_charges=()):
        frame = self.render(scene)
        frame.save(self.output / filename)
        box = pygame.Rect(scene.announcement_rect)
        field = pygame.Rect(0, 0, 480, scene.panel_rect.top)
        assert field.contains(box), ('Announcement outside field', box, field)
        assert all(box.contains(rect) for rect in scene.announcement_text_rects), \
            ('Announcement text escapes panel', scene.announcement_text_rects)
        assert not any(box.colliderect(row[key]) for row in scene.enemy_rows.values()
                       for key in ('name', 'hp', 'atb')), 'Announcement obscures enemy status'
        actual = tuple(scene.charging_enemies)
        assert set(actual) == set(expected_charges), (filename, actual, expected_charges)
        aura = scene.charge_aura_rects
        assert set(aura) == set(expected_charges), (filename, aura, expected_charges)
        assert all(field.contains(rect) for rect in aura.values()), 'Aura reaches HUD'
        current = scene.announcements.current
        record = {
            'file': filename, 'label': label,
            'window': list(self.game.window.get_size()), 'text_scale': self.game.audio.text_scale,
            'phase': scene.model.phase,
            'current_announcement': current,
            'warnings': list(scene.announcements.warnings),
            'charging_enemies': list(actual), 'announcement_rect': list(box),
            'announcement_text_rects': [list(rect) for rect in scene.announcement_text_rects],
            'aura_rects': {identifier: list(rect) for identifier, rect in aura.items()},
            'enemy_bodies': {identifier: list(rect) for identifier, rect in scene.enemy_rects.items()},
            'hud': list(scene.panel_rect),
        }
        self.captures.append(record)
        self.checks.append({'file': filename, 'announcement_clear_of_status': True,
                            'aura_inside_field': True, 'charge_ids_match_model': True})
        return frame

    def check_large_warning(self):
        """Show every page of a long warning at the actual accessibility size."""
        self.size((480, 320), 1.5)
        scene = self.scene(tusker=True)
        self.prepare(scene, 'enemy', 'prepare_charge')
        self.ready(scene)
        message = scene.announcements.current
        assert message['kind'] == 'warning'
        painter = self.game.ui.painter(self.game.ui_surface)
        height = painter.font(bold=True).get_linesize()
        capacity = max(1, (scene.announcement_rect.height-6)//height)
        lines = painter.wrap(message['text'], scene.announcement_rect.width-18, bold=True)
        pages = (len(lines)+capacity-1)//capacity
        crops = []
        page_text = []
        for page in range(pages):
            current = scene.announcements.current
            target_age = (page+.25)*current['duration']/pages
            # The single held warning recurs; advance to a stable interior
            # point of each page using the presentation clock itself.
            delta = (target_age-current['age']) % current['duration']
            if delta:scene.update(delta)
            drawn = []
            original = Painter.text

            def record(painter, text, *args, **kwargs):
                rect = original(painter, text, *args, **kwargs)
                if scene.announcement_rect.contains(rect):drawn.append(str(text))
                return rect

            with patch.object(Painter, 'text', record):
                image = self.render(scene)
            box = scene.announcement_rect
            assert all(box.contains(rect) for rect in scene.announcement_text_rects)
            assert not any(line.rstrip().endswith('→') for line in drawn), 'Orphan target arrow'
            page_text.append(drawn)
            crops.append(image.crop((box.left, box.top, box.right, box.bottom)))
        assert ' '.join(line for page in page_text for line in page) == message['text']
        sheet = Image.new('RGB', (480, pages*49+8), '#142d26')
        draw = ImageDraw.Draw(sheet)
        for index, crop in enumerate(crops):
            y = 8+index*49
            draw.text((8, y), 'Native 150% warning · page '+str(index+1)+'/'+str(pages),
                      fill='#f1cd77')
            sheet.paste(crop, (8, y+14))
        sheet.save(self.output/'warning_pages_large_text.png')
        self.checks.append({'long_warning_text': message['text'], 'native_text_scale': 1.5,
                            'pages_rendered': pages, 'rendered_page_text': page_text,
                            'all_text_inside_panel': True, 'target_arrow_stays_with_name': True})
        self.size()

    def run(self):
        with tempfile.TemporaryDirectory(prefix='battle-feedback-review-') as directory:
            folder = Path(directory)
            game = self.game = Game(window_size=(960, 640), fullscreen=False,
                start_on_title=False, save_path=folder/'journey.json',
                settings_path=folder/'settings.json')
            game.audio.set_music(0)
            game.audio.set_effects(0)
            for identifier in ('mira', 'lucan'):
                assert game.party.recruit(identifier)
            assert game.party.select(('caelan', 'mira', 'lucan'))

            basic = self.scene()
            self.start(basic, 'player', 'attack', 'enemy')
            assert basic.announcements.current is None, 'Basic Attack must not become a named-ability notice'
            self.checks.append({'basic_attack_omitted': True})

            skill = self.scene()
            self.start(skill, 'player', 'aether_edge', 'enemy')
            self.capture(skill, 'named_ability.png', 'Aether Edge · named ability announcement')

            tusker = self.scene(tusker=True)
            action = self.start(tusker, 'enemy', 'prepare_charge')
            self.capture(tusker, 'tusker_preparing.png', 'Tusker begins its heavy-attack windup',
                         expected_charges=('enemy',))
            tusker.update(action.duration)
            self.ready(tusker)
            self.capture(tusker, 'tusker_held.png', 'Charge persists through the player decision',
                         expected_charges=('enemy',))

            frames = []
            for _ in range(16):
                tusker.update(.09)
                frames.append(self.render(tusker).resize((480, 320), Image.Resampling.NEAREST))
            assert any(frame.tobytes() != frames[0].tobytes() for frame in frames[1:])
            frames[0].save(self.output/'charging_aura.gif', save_all=True,
                           append_images=frames[1:], duration=90, loop=0,
                           optimize=False, disposal=2)
            self.checks.append({'animated_aura_frames': len(frames), 'distinct_frames': True,
                                'gif_uses_actual_scene_updates': True})

            action = self.start(tusker, 'enemy', 'tusker_charge')
            tusker.update(action.impact_at * .5)
            self.capture(tusker, 'tusker_releasing.png', 'Bankbreaker Charge · aura stays until impact',
                         expected_charges=('enemy',))
            tusker.update(action.impact_at - action.elapsed + .001)
            self.capture(tusker, 'tusker_released.png', 'The power aura clears when the heavy hit lands')

            mixed = self.scene(mixed=True)
            for actor in ('enemy_3', 'enemy_4'):
                self.prepare(mixed, actor, 'veylume_gather_charge')
            self.ready(mixed)
            self.capture(mixed, 'multiple_charges.png', 'Two independent Veylume windups',
                         expected_charges=('enemy_3', 'enemy_4'))

            self.size((480, 320), 1.5)
            self.capture(mixed, 'multiple_charges_large_text.png', 'Native 480 × 320 · text 150%',
                         expected_charges=('enemy_3', 'enemy_4'))
            self.size()

            emote = self.scene(tusker=True)
            emote.announce('The Tusker paws the earth!', actor='enemy')
            assert emote.announcements.current['text'] == 'The Tusker paws the earth!'
            self.capture(emote, 'battle_emote.png', 'Authored battle-emote presentation hook')
            self.check_large_warning()

            metadata = {'fixture': 'Disposable battle-information review; explicit NPC scheduling and ATB',
                        'captures': self.captures, 'checks': self.checks}
            (self.output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
        pygame.quit()
        self.contact_sheet()

    def contact_sheet(self):
        width, height, gap = 480, 320, 10
        sheet = Image.new('RGB', (width*2+gap*3, (height+26)*4+gap*5), '#142d26')
        draw = ImageDraw.Draw(sheet)
        for index, record in enumerate(self.captures):
            x = gap+(index % 2)*(width+gap)
            y = gap+(index // 2)*(height+26+gap)
            image = Image.open(self.output/record['file']).convert('RGB')
            image = image.resize((width, height), Image.Resampling.NEAREST)
            draw.text((x, y), record['label'], fill='#f1cd77')
            sheet.paste(image, (x, y+22))
        sheet.save(self.output/'contact_sheet.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/reviews/battle_feedback')
    args = parser.parse_args()
    Review(args.output).run()
    print('Verified battle-feedback captures:', args.output)


if __name__ == '__main__':
    main()
