"""Floor-clipped ambience, suspended clocks and safe original hum ownership."""
from array import array
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from elemental_room_fx import ElementalRoomEffects, HUM_GAIN, HUM_SECONDS, synth_hum

ROOT = Path(__file__).resolve().parents[1]


class ElementalRoomEffectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((1, 1))
        cls.data = json.loads((ROOT/'assets/maps/sanctuary_cave/map.json').read_text())
        collision = pygame.image.load(str(ROOT/cls.data['collision']))
        cls.blocked = pygame.mask.from_threshold(collision, (255, 255, 255, 255), (1, 1, 1, 255))

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def game(self):
        return SimpleNamespace(
            world=SimpleNamespace(data=self.data, blocked=self.blocked),
            player=SimpleNamespace(position=pygame.Vector2(768, 1632)),
            audio=SimpleNamespace(effects_volume=0., reduced_motion=False, bind_effects=Mock()),
            combat=SimpleNamespace(active=False), social=SimpleNamespace(active=False, locked=False),
            pause=SimpleNamespace(is_open=False), quest_ui=SimpleNamespace(journal_open=False),
            opening=SimpleNamespace(locks_player=False), opening_cinematic=SimpleNamespace(active=False),
            elemental_bosses=SimpleNamespace(acquisition_active=False), _music_focused=True,
            on_title=False, on_gallery=False, map_open=False, opening_fade=0, transfer_cooldown=0,
            gallery_session=None)

    def test_sparse_native_effects_intersect_actual_room_floor_and_collision(self):
        game = self.game();fx = ElementalRoomEffects(game)
        game.audio.bind_effects.assert_called_once_with(fx)
        for center in ((768, 1632), (1296, 528)):
            with self.subTest(center=center):
                game.player.position.update(center)
                camera = (center[0]-240, center[1]-160)
                canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
                fx.update(1.25);fx.draw(canvas, camera)
                actual = pygame.mask.from_surface(canvas, 0)
                expected = pygame.Mask(canvas.get_size())
                for room in fx._rooms.values():
                    expected.draw(room.floor, (room.bounds.x-camera[0], room.bounds.y-camera[1]))
                    self.assertLessEqual(len(room.particles), 12)
                    self.assertLessEqual(len(room.wisps), 3)
                    self.assertLess(room.layer.get_width()*room.layer.get_height(), 110000)
                self.assertGreater(actual.count(), 0)
                self.assertLess(actual.count(), 250)
                actual.erase(expected, (0, 0))
                self.assertEqual(actual.count(), 0, 'A mote, glow or heat wisp crossed the collision-clipped floor')
                outside = pygame.Surface((480, 320), pygame.SRCALPHA)
                fx.draw(outside, (0, 0))
                self.assertEqual(pygame.mask.from_surface(outside, 0).count(), 0)

    def test_reduced_motion_is_static_and_world_pause_conditions_freeze_clock(self):
        game = self.game();fx = ElementalRoomEffects(game)
        fx.update(.5)
        self.assertEqual(fx.elapsed, .5)
        for owner, key, value in ((game, '_music_focused', False), (game.pause, 'is_open', True),
                                  (game.social, 'active', True), (game.quest_ui, 'journal_open', True),
                                  (game.combat, 'active', True), (game, 'map_open', True),
                                  (game, 'on_title', True), (game, '_is_gallery_preview', True),
                                  (game.elemental_bosses, 'acquisition_active', True)):
            prior = getattr(owner, key, False)
            setattr(owner, key, value);fx.update(3.)
            self.assertEqual(fx.elapsed, .5, key)
            setattr(owner, key, prior)
        game.audio.reduced_motion = True
        first = pygame.Surface((480, 320), pygame.SRCALPHA)
        second = first.copy()
        fx.draw(first, (528, 1472));fx.update(100.);fx.draw(second, (528, 1472))
        self.assertEqual(fx.elapsed, .5)
        self.assertEqual(pygame.image.tobytes(first, 'RGBA'), pygame.image.tobytes(second, 'RGBA'))
        self.assertGreater(pygame.mask.from_surface(first, 0).count(), 0)
        game.audio.reduced_motion = False
        fx.update(.2)
        self.assertAlmostEqual(fx.elapsed, .7)

    def test_hum_pcm_is_original_periodic_bounded_stereo_and_ice_is_quieter(self):
        variants = []
        for element in ('fire', 'ice'):
            pcm = synth_hum(element, 8000, 2)
            self.assertIsInstance(pcm, array)
            self.assertEqual(len(pcm), 8000*HUM_SECONDS*2)
            self.assertTrue(all(left == right for left, right in zip(pcm[::2], pcm[1::2])))
            mono = pcm[::2]
            self.assertLess(max(abs(value) for value in mono), 1600)
            self.assertGreater(max(mono), 500)
            largest_step = max(abs(after-before) for before, after in zip(mono, mono[1:]))
            self.assertLessEqual(abs(mono[-1]-mono[0]), largest_step+1)
            self.assertEqual(pcm, synth_hum(element, 8000, 2))
            variants.append(pcm)
        self.assertNotEqual(*variants)
        self.assertLess(HUM_GAIN['ice'], HUM_GAIN['fire'])
        for args in (('water', 8000, 2), ('ice', 0, 2), ('fire', 8000, 6)):
            with self.assertRaises(ValueError):synth_hum(*args)

    def test_hum_loops_once_binds_volume_stops_on_pause_and_never_steals_a_reused_channel(self):
        game = self.game();game.audio.effects_volume = 1.
        fx = ElementalRoomEffects(game)
        channel = Mock();sound = Mock();borrowed = object();leased = [None]
        channel.get_sound.side_effect = lambda:leased[0]
        channel.play.side_effect = lambda item, **kwargs:leased.__setitem__(0, item)
        channel.stop.side_effect = lambda:leased.__setitem__(0, None)
        with patch('elemental_room_fx.pygame.mixer.get_init', return_value=(8000, -16, 2)), \
             patch('elemental_room_fx.pygame.mixer.find_channel', return_value=channel) as find, \
             patch('elemental_room_fx.pygame.mixer.Sound', return_value=sound):
            fx.sync_audio();fx.sync_audio()
            channel.play.assert_called_once_with(sound, loops=-1)
            find.assert_called_once_with(False)
            game.audio.effects_volume = .5;fx.refresh_volume()
            channel.set_volume.assert_called_with(HUM_GAIN['fire']*.5)
            game.pause.is_open = True;fx.sync_audio()
            channel.stop.assert_called_once_with()
            self.assertIsNone(fx._channel)
            game.pause.is_open = False;fx.sync_audio()
            self.assertEqual(channel.play.call_count, 2)
            leased[0] = borrowed;find.return_value = None
            fx.sync_audio();fx.stop_audio()
            self.assertIs(leased[0], borrowed)
            self.assertEqual(channel.stop.call_count, 1)
            self.assertEqual(channel.play.call_count, 2)
            self.assertIsNone(fx._channel)

    def test_real_dummy_mixer_accepts_pcm_and_switches_to_the_quieter_ice_hum(self):
        game = self.game();game.audio.effects_volume = 1.
        fx = ElementalRoomEffects(game)
        self.addCleanup(fx.stop_audio)
        fx.sync_audio()
        self.assertIsNotNone(fx._channel)
        self.assertIs(fx._channel.get_sound(), fx._sound)
        fire = fx._sound
        self.assertAlmostEqual(fire.get_length(), HUM_SECONDS, places=3)
        game.player.position.update(1296, 528)
        fx.sync_audio()
        self.assertEqual(fx._audio_room, 'nivareth')
        self.assertIsNot(fx._sound, fire)
        self.assertIs(fx._channel.get_sound(), fx._sound)
        self.assertLess(fx._channel.get_volume(), HUM_GAIN['fire'])
        channel = fx._channel
        fx.stop_audio()
        self.assertFalse(channel.get_busy())

    def test_leaving_room_battle_focus_mute_and_mixer_shutdown_release_only_owned_audio(self):
        game = self.game();game.audio.effects_volume = 1.
        for mutation in ('room', 'battle', 'focus', 'mute', 'mixer'):
            with self.subTest(mutation=mutation):
                fx = ElementalRoomEffects(game)
                channel = Mock();sound = Mock();channel.get_sound.return_value = sound
                fx._channel, fx._sound, fx._audio_room = channel, sound, 'embravyr'
                prior = (game.player.position.copy(), game.combat.active,
                         game._music_focused, game.audio.effects_volume)
                if mutation == 'room':game.player.position.update(288, 1660)
                elif mutation == 'battle':game.combat.active = True
                elif mutation == 'focus':game._music_focused = False
                elif mutation == 'mute':game.audio.effects_volume = 0.
                with patch('elemental_room_fx.pygame.mixer.get_init',
                           return_value=None if mutation == 'mixer' else (8000, -16, 2)):
                    fx.sync_audio()
                channel.stop.assert_called_once_with()
                self.assertIsNone(fx._channel)
                game.player.position.update(prior[0]);game.combat.active = prior[1]
                game._music_focused = prior[2];game.audio.effects_volume = prior[3]
        channel = Mock();channel.get_sound.side_effect = pygame.error('mixer quit')
        fx._channel, fx._sound = channel, object()
        fx.stop_audio()
        self.assertIsNone(fx._channel)
        channel.stop.assert_not_called()


if __name__ == '__main__':unittest.main()
