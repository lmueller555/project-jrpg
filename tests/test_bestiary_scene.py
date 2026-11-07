"""Real Cave Bat presentation through ATB, impacts, depletion and victory."""
from copy import deepcopy
import os
import random
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from audio_settings import AudioSettings
from battle_model import BattleModel
from battle_scene import BattleScene, CombatSprites
from bestiary import load_bestiary
from character_attributes import CharacterAttributes
from inventory import Inventory
from leveling import character_stats
from ui_style import Painter, UIStyle


def leveled_caelan(level):
    catalog = deepcopy(CharacterAttributes().catalog)
    catalog['characters']['caelan']['attributes'] = character_stats('caelan', level)
    return CharacterAttributes('caelan', catalog)


class BestiarySceneTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        self.game = SimpleNamespace(
            window=pygame.display.set_mode((960, 640)),
            ui_surface=pygame.Surface((960, 640)),
            audio=AudioSettings(), inventory=Inventory())
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = lambda point: (point[0]/2, point[1]/2)
        self.canvas = pygame.Surface((480, 320))

    def tearDown(self):
        pygame.quit()

    def encounter(self, level):
        self.game.attributes = leveled_caelan(level)
        model = BattleModel.from_bestiary(self.game.attributes, 'cave_bat', level,
                                          rng=random.Random(7))
        return model, BattleScene(self.game, model, battlefield='eldenmere')

    def draw(self, scene):
        scene.draw(self.canvas, self.game.ui_surface)

    def command(self, scene, identifier):
        self.draw(scene)
        x, y = scene.command_rects[identifier].center
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            scene.handle_event(pygame.event.Event(kind, button=1, pos=(x*2, y*2)))

    def test_level_specific_names_and_real_bat_idle_render_at_both_levels(self):
        for level, hp, reward in ((2, 73, 84), (3, 85, 104)):
            with self.subTest(level=level):
                model, scene = self.encounter(level)
                labels = []
                original = Painter.text
                def record(painter, value, *args, **kwargs):
                    labels.append(str(value))
                    return original(painter, value, *args, **kwargs)
                with patch.object(Painter, 'text', record):
                    self.draw(scene)
                self.assertIsInstance(scene.sprites, CombatSprites)
                self.assertEqual(model.enemy_sprite_id, 'bat')
                self.assertEqual(model.enemy_id, 'cave_bat')
                self.assertEqual((model.enemy_level, model.enemy.hp,
                                  model.enemy_xp_reward), (level, hp, reward))
                self.assertIn('Cave Bat', labels)
                self.assertEqual(scene.location_name, 'Eldenmere')

    def test_elemental_design_data_is_hidden_in_ordinary_battle_presentation(self):
        catalog = load_bestiary()
        alternate = deepcopy(catalog)
        profile = alternate['enemies']['cave_bat']['elemental_profile']
        profile['element'] = 'fire'
        profile['damage_percentages'] = dict.fromkeys(profile['damage_percentages'], 75)
        profile['damage_percentages']['fire'] = 200
        profile['absorption']['elements'] = ['fire']
        presentations = []
        for data in (catalog, alternate):
            self.game.attributes = leveled_caelan(2)
            model = BattleModel.from_bestiary(self.game.attributes, 'cave_bat', 2,
                                              bestiary_data=data, rng=random.Random(7))
            scene = BattleScene(self.game, model, battlefield='eldenmere')
            labels = []
            original = Painter.text
            def record(painter, value, *args, **kwargs):
                labels.append(str(value))
                return original(painter, value, *args, **kwargs)
            self.canvas.fill('black')
            self.game.ui_surface.fill('black')
            with patch.object(Painter, 'text', record):
                self.draw(scene)
            presentations.append((labels, pygame.image.tobytes(self.canvas, 'RGB'),
                                   pygame.image.tobytes(self.game.ui_surface, 'RGB')))
        self.assertEqual(presentations[0], presentations[1])

    def test_real_frames_render_bite_gust_hurt_and_defeat_after_mp_depletion(self):
        model, scene = self.encounter(3)
        original_attributes = deepcopy(self.game.attributes.to_dict())
        events, frame_calls, cues = [], [], []
        original_drain = model.drain_events
        def drain():
            batch = original_drain()
            events.extend(deepcopy(batch))
            return batch
        original_frame = scene.sprites.frame
        def frame(actor, state, elapsed):
            frame_calls.append((actor, state))
            return original_frame(actor, state, elapsed)
        original_play = scene.action_audio.play
        def play(cue):
            cues.append(cue)
            return original_play(cue)
        enemy_actions = []
        action_object = None
        with patch.object(model, 'drain_events', drain), \
                patch.object(scene.sprites, 'frame', frame), \
                patch.object(scene.action_audio, 'play', play):
            for _ in range(16000):
                if model.waiting_for_player:
                    self.command(scene, 'guard' if len(enemy_actions) < 8 else 'attack')
                scene.update(.04)
                current = model.current_action
                if current is not None and current is not action_object:
                    action_object = current
                    if current.actor == 'enemy':
                        enemy_actions.append((current.action, model.enemy.mp))
                self.draw(scene)
                if model.ended:
                    for _ in range(15):
                        scene.update(.04)
                        self.draw(scene)
                    break
            else:
                self.fail('Real Cave Bat encounter did not finish')
        self.assertEqual(model.phase, 'victory')
        self.assertEqual(enemy_actions[:8], [
            ('cave_bat_bite', 5), ('cave_bat_wing_gust', 3),
            ('cave_bat_bite', 3), ('cave_bat_wing_gust', 1),
            ('cave_bat_bite', 1), ('cave_bat_bite', 1),
            ('cave_bat_bite', 1), ('cave_bat_bite', 1)])
        for state in ('idle', 'attack', 'cast', 'hurt', 'defeat'):
            self.assertIn(('bat', state), frame_calls)
        self.assertFalse(any(actor == 'cave_bat' for actor, _ in frame_calls))
        self.assertEqual(sum(action == 'cave_bat_wing_gust'
                             for action, _ in enemy_actions), 2)
        self.assertTrue(any(event['type'] == 'impact' and event['actor'] == 'enemy'
                            and event['action'] == 'cave_bat_wing_gust' for event in events))
        self.assertFalse(any(event.get('action') in ('bite', 'wing_gust') for event in events))
        self.assertTrue(cues)
        self.assertTrue(set(cues) <= {'step', 'land', 'swing', 'focus', 'release',
                                     'impact', 'guard_hit'})
        self.assertEqual(self.game.attributes.to_dict(), original_attributes)


if __name__ == '__main__':
    unittest.main()
