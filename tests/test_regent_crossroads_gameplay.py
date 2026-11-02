"""Read-only art, real arrival input/update/draw, and the crossroads handoff.

Earlier mill work uses the established arrival fixture. Story progression is
never seeded with shot indices, dialogue indices, actor positions or clocks.
The constructor rejection probes substitute decoded manifests, not asset files.
"""
from __future__ import annotations

import copy
import json
import math
import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

import speech_bubble
import test_regent_arrival as arrival_tests
from quests import MILL_QUEST, REGENT_QUEST
from regent_aerial import APPROACH_SPEED, DURATION, GROUND_PARTY
from regent_arrival import RegentArrival, SCENE
from regent_road_pan import RoadWhipPan
from test_mill_battle_gameplay import click, key
from ui_style import MUTED


def pixels(surface):
    return pygame.image.tobytes(surface, 'RGBA')


def world_state(game):
    """Include simulation clocks and rewards, not just the player's position."""
    cached = game._overworld_world
    return copy.deepcopy({
        'world': game.world.data['id'],
        'player': (tuple(game.player.position), game.player.facing,
                   game.player.moving, game.player.walk_ms),
        'elapsed_ms': game.elapsed_ms,
        'camera': game.camera.position(),
        'residents': tuple((world.data['id'], actor.data['id'], tuple(actor.position),
                            getattr(actor, 'walk_ms', None), getattr(actor, 'clock', None))
                           for world in game.scenes.values() for actor in world.npcs),
        'doors': tuple((world.data['id'], door.data['id'], door.progress, door.target_open)
                       for world in game.scenes.values() for door in world.doors),
        'cached_residents': (tuple((actor.data['id'], tuple(actor.position),
                                   getattr(actor, 'clock', None)) for actor in cached.npcs)
                             if cached is not None else None),
        'wildlife': cached.wildlife.to_dict() if cached is not None else None,
        'inventory': game.inventory.to_dict(),
        'attributes': game.attributes.to_dict(),
        'quests': game.quests.to_dict(),
        'mill': game.mill_quest.to_dict(),
        'regent': game.regent_quest.to_dict(),
        'flags': set(game.social.flags),
    })


def visual_state(scene):
    """Pause/focus flags may change; the underlying shot must not."""
    return (scene.active, scene.state, scene.phase_index, scene.phase_time,
            scene.elapsed, scene.dialogue_index, scene.page_index,
            tuple(scene.camera_position), scene.road_pan_sample,
            tuple((actor['id'], tuple(scene.actor_position(actor)),
                   scene.actor_pose(actor), scene._actor_scale(actor))
                  for actor in scene.phase['actors']),
            scene._reference_clock, scene._reference_camera)


class RegentCrossroadsGameplayTests(unittest.TestCase):
    # Reuse the real report, startup and normal-input reach helpers, without
    # inheriting/re-discovering all of the original arrival test cases.
    game = arrival_tests.RegentArrivalTests.game
    setUp = arrival_tests.RegentArrivalTests.setUp
    start = arrival_tests.RegentArrivalTests.start
    reach = arrival_tests.RegentArrivalTests.reach

    def tearDown(self):
        if self.g.gallery_session is not None:
            self.g.gallery_session.close()
        self.g.regent_arrival.audio.stop()
        self.g.regent_arrival.bird_audio.stop()
        self.g.opening_audio.reset()
        self.g.regional_audio.reset()
        self.g.music.stop()
        pygame.quit()

    def question(self):
        """Leave the final Aldric question unread, through production input."""
        scene = self.reach('locals')
        self.g.update(2., (0, 0), False)
        last = len(scene.phase['dialogue'])-1
        for _ in range(100):
            if scene.dialogue_index == last:
                break
            self.assertEqual(scene.shot, 'locals')
            key(self.g, pygame.K_SPACE)
        else:
            self.fail('Could not read through to Aldric\'s final question')
        self.assertEqual(scene.dialogue, {
            'speaker': 'aldric', 'text': 'Were you here when it happened?'})
        return scene

    def middle_of_pan(self):
        scene = self.start()
        self.reach('road_pan')
        self.g.update(.4-scene.phase_time, (0, 0), False)
        self.assertEqual(scene.shot, 'road_pan')
        self.assertAlmostEqual(scene.phase_time, .4)
        return scene

    def test_pending_start_uses_main_focus_hook_before_any_scene_focus_event(self):
        arrival_tests.acknowledge_report(self.g)
        scene = self.g.regent_arrival
        self.assertFalse(scene.active)
        self.assertEqual(scene.state, 'pending')
        before = world_state(self.g)
        self.g.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        self.assertFalse(self.g._music_focused)
        self.g.update(5., (1, 1), True)
        self.assertTrue(scene.active)
        self.assertFalse(scene.focused)
        self.assertEqual((scene.shot, scene.phase_time, scene.elapsed), ('mill_close', 0., 0.))
        self.assertEqual(world_state(self.g), before)
        self.assertTrue(self.g.music.paused)
        key(self.g, pygame.K_SPACE)
        self.g.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.g.update(.1, (0, 0), False)
        self.assertTrue(scene.focused)
        self.assertAlmostEqual(scene.elapsed, .1)
        self.assertFalse(self.g.music.paused)
        self.assertEqual(world_state(self.g), before)

    def test_aerial_draw_uses_real_clerk_feet_and_negative_distance_gait_clock(self):
        scene = self.start()
        self.reach('aerial_descent')
        self.g.update(.2, (0, 0), False)
        with patch.object(scene.aerial, '_sprite', wraps=scene.aerial._sprite) as sprite:
            self.g.draw()
        clerk_calls = [call for call in sprite.call_args_list if call.args[1] == 'clerk']
        self.assertEqual(len(clerk_calls), 1)
        self.assertEqual(clerk_calls[0].args[2], 'overhead')
        overhead = scene.aerial_snapshot()['projected_actors']
        self.assertTrue(overhead['clerk']['moving'])
        self.assertLess(overhead['caravan']['road_distance'], overhead['clerk']['road_distance'])
        self.assertLess(overhead['clerk']['road_distance'], overhead['aldric']['road_distance'])

        self.g.update(6.-scene.phase_time, (0, 0), False)
        original_data = copy.deepcopy(scene.data)
        frozen = world_state(self.g)
        observed = []
        draw_actor = scene._draw_actor

        def record(canvas, actor, camera):
            rect = draw_actor(canvas, actor, camera)
            if actor['id'] != 'clerk':
                return rect
            self.assertEqual(scene.actor_pose(actor), 'walk_left')
            self.assertIsNotNone(scene._reference_clock)
            self.assertLess(scene._reference_clock, 0.)
            art = scene.actor_art['clerk']
            image = scene._frame(actor)
            frames = art['loops']['walk_left']
            index = next(i for i, (frame, _) in enumerate(frames) if frame is image)
            cycle = sum(duration for _, duration in frames)
            clock = ((scene._reference_clock*APPROACH_SPEED /
                      art['gaits']['walk_left']['stride_pixels']+actor['gait_offset']) % 1)*cycle
            expected = 0
            while clock >= frames[expected][1]:
                clock -= frames[expected][1]
                expected += 1
            self.assertEqual(index, expected)
            foot = scene.actor_position(actor)
            self.assertEqual(foot, pygame.Vector2(GROUND_PARTY['clerk']) +
                             (-scene._reference_clock*APPROACH_SPEED, 0))
            # Inspect an actual opaque support-boot pixel after the real blit,
            # not a transparent sprite-cell edge or only diagnostic metadata.
            bounds = image.get_bounding_rect()
            x = next(x for x in range(bounds.left, bounds.right)
                     if image.get_at((x, bounds.bottom-1)).a)
            point = foot-camera-pygame.Vector2(art['anchor'])+(x, bounds.bottom-1)
            self.assertEqual(canvas.get_at((round(point.x), round(point.y))),
                             image.get_at((x, bounds.bottom-1)))
            self.assertLessEqual(abs(rect.bottom-(foot-camera).y), 3)
            observed.append((index, tuple(foot), scene._reference_clock))
            return rect

        with patch.object(scene, '_draw_actor', side_effect=record):
            for _ in range(30):
                before = (scene.phase_index, scene.phase_time, scene.elapsed,
                          scene.dialogue_index, scene.page_index)
                snapshot = scene.aerial_snapshot()
                self.assertTrue(snapshot['ground_handoff'])
                self.assertEqual(snapshot['canopy']['coverage'], 0.)
                count = len(observed)
                self.g.draw()
                self.assertEqual(len(observed), count+1)
                self.assertEqual(observed[-1][1], tuple(snapshot['projected_actors']['clerk']['native_xy']))
                self.assertAlmostEqual(observed[-1][2], snapshot['seconds']-DURATION)
                self.assertEqual((scene.phase_index, scene.phase_time, scene.elapsed,
                                  scene.dialogue_index, scene.page_index), before)
                self.assertIsNone(scene._reference_clock)
                self.assertIsNone(scene._reference_camera)
                self.assertEqual(scene.data, original_data)
                self.assertEqual(world_state(self.g), frozen)
                self.g.update(.04, (0, 0), False)
        self.assertEqual({index for index, _, _ in observed}, set(range(8)))
        for first, second in zip(observed, observed[1:]):
            self.assertAlmostEqual(first[1][0]-second[1][0], APPROACH_SPEED*.04)
            self.assertEqual(first[1][1], second[1][1])
        self.assertLess(observed[-1][1][0], observed[0][1][0]-25)

    def test_real_playback_draws_clerk_at_every_walk_and_conversation_station(self):
        scene = self.start()
        expected = {
            'gate_approach': 'walk_left', 'gate_greeting': 'stand_left',
            'gate_admission': 'stand_left', 'crossroads_establishing': 'stand_left',
            'locals': 'stand_left', 'road_pan': 'stand_left', 'relief': 'read_left',
            'town_approach': 'walk_left', 'town_parking': 'walk_left',
        }
        seen = []
        frozen = world_state(self.g)
        inventory = copy.deepcopy(self.g.inventory.to_dict())
        attributes = copy.deepcopy(self.g.attributes.to_dict())
        quests = copy.deepcopy(self.g.quests.to_dict())
        with patch.object(self.g, 'save_progress', wraps=self.g.save_progress) as save:
            for _ in range(4000):
                if not scene.active:
                    break
                if not seen or seen[-1] != scene.shot:
                    seen.append(scene.shot)
                    if scene.shot in expected:
                        clerks = [actor for actor in scene.phase['actors'] if actor['id'] == 'clerk']
                        self.assertEqual(len(clerks), 1, scene.shot)
                        with patch.object(scene, '_draw_actor', wraps=scene._draw_actor) as draw:
                            self.g.draw()
                        calls = [call for call in draw.call_args_list if call.args[1]['id'] == 'clerk']
                        self.assertEqual(len(calls), 1, scene.shot)
                        self.assertEqual(scene.actor_pose(calls[0].args[1]), expected[scene.shot])
                if scene.dialogue is not None:
                    key(self.g, pygame.K_SPACE)
                self.g.update(.1, (1, 1), True)
                if scene.active:
                    self.assertEqual(world_state(self.g), frozen)
            else:
                self.fail(('Arrival did not finish through input', scene.shot))
            self.assertEqual(save.call_count, 1)
        self.assertEqual(seen, [phase['id'] for phase in scene.data['phases']])
        self.assertTrue(set(expected) <= set(seen))
        self.assertEqual((scene.state, scene.finished_reason), ('seen', 'finished'))
        self.assertEqual(self.g.inventory.to_dict(), inventory)
        self.assertEqual(self.g.attributes.to_dict(), attributes)
        self.assertEqual(self.g.quests.to_dict(), quests)
        self.assertEqual(self.g.quests.status(MILL_QUEST), 'completed')
        self.assertEqual(self.g.quests.status(REGENT_QUEST), 'available')
        self.assertEqual(self.g.regent_quest.stage, 'idle')
        self.assertEqual(self.g.music.desired_track, 'eldenmere')
        self.assertEqual(json.loads(self.path.read_text())['regent_arrival'],
                         {'version': 1, 'state': 'seen'})
        self.assertFalse(scene.finish())
        self.assertFalse(scene.request())
        self.assertFalse(scene.maybe_start())

    def test_final_question_must_be_read_and_pan_inputs_do_not_consume_bridge_pages(self):
        self.g.audio.text_scale = 1.5
        self.start()
        scene = self.question()
        frozen = world_state(self.g)
        self.g.draw()
        last = scene.dialogue_index
        pages = len(scene.caption_pages)
        self.g.update(120., (1, 1), True)
        self.g.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, repeat=True)])
        self.assertEqual((scene.shot, scene.dialogue_index, scene.page_index), ('locals', last, 0))
        for page in range(pages):
            self.assertEqual((scene.shot, scene.page_index), ('locals', page))
            key(self.g, pygame.K_SPACE)
        self.assertEqual((scene.shot, scene.phase_time), ('road_pan', 0.))
        self.assertEqual(scene.phase['min_seconds'], .8)
        self.assertIsNone(scene.dialogue)
        self.assertEqual(tuple(scene.camera_position), tuple(scene.crossroads_data['camera_junction']))
        for seconds in (.79, .02):
            before = visual_state(scene)
            for value in (pygame.K_SPACE, pygame.K_e, pygame.K_RETURN,
                          pygame.K_m, pygame.K_i, pygame.K_j):
                key(self.g, value)
                self.assertFalse(scene._batch_advanced)
            click(self.g, (240, 160))
            self.assertFalse(scene._batch_advanced)
            self.assertEqual(visual_state(scene), before)
            self.assertFalse(self.g.map_open or self.g.pause.is_open or self.g.social.active)
            self.assertFalse(self.g.quest_ui.journal_open or self.g.inventory_ui.is_open)
            self.g.update(seconds, (1, 1), True)
        self.assertEqual((scene.shot, scene.dialogue_index, scene.page_index), ('bridge_damage', 0, 0))
        self.g.update(90., (1, 1), True)
        self.g.draw()
        self.assertEqual((scene.shot, scene.dialogue_index, scene.page_index), ('bridge_damage', 0, 0))
        self.assertEqual(scene.dialogue, scene.phase['dialogue'][0])
        self.assertEqual(world_state(self.g), frozen)

    def test_pan_draw_is_deterministic_fresh_scenery_with_real_blur_and_speed_lines(self):
        scene = self.middle_of_pan()
        self.g.draw()
        state = visual_state(scene)
        frozen = world_state(self.g)
        sample = scene.road_pan_sample
        self.assertTrue(sample.active)
        self.assertGreater(sample.blur_px, 0)
        self.assertGreater(sample.streak_count, 0)
        background = scene.scenery['crossroads']['background']
        camera = scene.camera_position
        bounds = pygame.Rect(round(camera.x), round(camera.y), 480, 320)
        original = pixels(background.subsurface(bounds))
        source = background.subsurface(bounds).copy()
        expected = pixels(scene.road_pan.apply(source, sample))
        self.assertNotEqual(expected, pixels(source))
        with patch.object(RoadWhipPan, '_blur', wraps=RoadWhipPan._blur) as blur, \
                patch.object(RoadWhipPan, '_streaks', wraps=RoadWhipPan._streaks) as streaks:
            self.g.draw()
            window = pixels(self.g.window)
            self.assertEqual(pixels(self.g.canvas), expected)
            self.g.draw()
            self.assertEqual(pixels(self.g.canvas), expected)
            self.assertEqual(pixels(self.g.window), window)
            self.assertEqual((blur.call_count, streaks.call_count), (2, 2))
        self.assertEqual(pixels(background.subsurface(bounds)), original)
        self.assertEqual(visual_state(scene), state)
        self.assertEqual(world_state(self.g), frozen)
        self.g.update(.03, (1, 1), True)
        self.g.draw()
        self.assertNotEqual(pixels(self.g.window), window)
        self.assertEqual(world_state(self.g), frozen)

    def test_pause_focus_and_main_focus_hook_freeze_the_same_pan_clock_and_pixels(self):
        scene = self.middle_of_pan()
        state = visual_state(scene)
        frozen = world_state(self.g)
        for mode in ('escape', 'window_focus', 'main_focus_hook'):
            with self.subTest(mode=mode):
                if mode == 'escape':
                    key(self.g, pygame.K_ESCAPE)
                elif mode == 'window_focus':
                    self.g.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
                    self.assertFalse(scene.focused)
                else:
                    self.g._music_focused = False
                self.g.update(0., (0, 0), False)
                self.g.draw()
                frame = tuple(pixels(surface) for surface in (self.g.canvas, self.g.ui_surface, self.g.window))
                self.g.update(50., (1, 1), True)
                key(self.g, pygame.K_SPACE)
                self.g.draw()
                self.assertEqual(visual_state(scene), state)
                self.assertEqual(world_state(self.g), frozen)
                self.assertEqual(tuple(pixels(surface) for surface in
                                       (self.g.canvas, self.g.ui_surface, self.g.window)), frame)
                self.assertTrue(self.g.music.paused)
                self.assertFalse(self.g.pause.is_open)
                if mode == 'escape':
                    key(self.g, pygame.K_ESCAPE)
                elif mode == 'window_focus':
                    self.g.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
                else:
                    self.g._music_focused = True
                self.g.update(0., (0, 0), False)
                self.assertFalse(self.g.music.paused)
        self.g.update(.05, (1, 1), True)
        self.assertAlmostEqual(scene.phase_time, state[3]+.05)
        self.assertNotEqual(scene.road_pan_sample, state[8])
        self.assertEqual(world_state(self.g), frozen)

    def test_carrier_account_is_player_paced_and_relief_hard_cuts_to_exact_stations(self):
        scene = self.start()
        self.reach('locals')
        self.g.update(2., (0, 0), False)
        camera = tuple(scene.camera_position)
        stations = {actor['id']: tuple(scene.actor_position(actor)) for actor in scene.phase['actors']}
        frozen = world_state(self.g)
        self.reach('road_pan')
        self.assertEqual({actor['id']: tuple(scene.actor_position(actor))
                          for actor in scene.phase['actors']}, stations)
        self.g.update(.8, (0, 0), False)
        self.assertEqual(scene.shot, 'bridge_damage')
        self.assertEqual(tuple(scene.camera_position), tuple(scene.crossroads_data['camera_bridge']))
        # This is the Carrier speaking off camera, not a transported witness
        # or a second local actor standing by the ruined crossing.
        self.assertEqual(scene.phase['actors'], [])
        self.assertEqual([line['speaker'] for line in scene.phase['dialogue']], ['local', 'local'])
        accounts = copy.deepcopy(scene.phase['dialogue'])
        for index, line in enumerate(accounts):
            self.g.update(100., (1, 1), True)
            self.g.draw()
            self.assertEqual((scene.shot, scene.dialogue_index, scene.page_index), ('bridge_damage', index, 0))
            self.assertEqual(scene.dialogue, line)
            pages = len(scene.caption_pages)
            for page in range(pages):
                self.assertEqual((scene.shot, scene.dialogue_index, scene.page_index),
                                 ('bridge_damage', index, page))
                key(self.g, pygame.K_SPACE)
        self.assertEqual((scene.shot, scene.phase_time, scene.fade_alpha), ('relief', 0., 0))
        self.assertEqual(tuple(scene.camera_position), camera)
        self.assertEqual(scene.phase['camera']['from'], scene.phase['camera']['to'])
        self.assertEqual({actor['id']: tuple(scene.actor_position(actor))
                          for actor in scene.phase['actors']}, stations)
        self.g.update(.4, (0, 0), False)
        self.g.draw()
        self.assertEqual(scene.dialogue['speaker'], 'aldric')
        self.assertIn('elsewhere', scene.dialogue['text'])
        self.assertEqual(world_state(self.g), frozen)

    def test_large_font_controls_and_bridge_captions_are_after_the_native_effect_pass(self):
        scene = self.middle_of_pan()
        self.g.audio.text_scale = 1.5
        self.g.handle_events([pygame.event.Event(pygame.VIDEORESIZE, w=1120, h=760)])
        apply = RoadWhipPan.apply
        effects = []

        def record(pan, canvas, sample, **options):
            result = apply(pan, canvas, sample, **options)
            effects.append((canvas.get_size(), pixels(result)))
            return result

        with patch.object(RoadWhipPan, 'apply', autospec=True, side_effect=record):
            self.g.draw()
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0], ((480, 320), pixels(self.g.canvas)))
        self.assertIsNone(scene.caption_layout)
        self.assertEqual(scene.caption_pages, [])
        expected = pygame.transform.scale(self.g.canvas, self.g.ui_surface.get_size())
        painter = self.g.ui.painter(expected)
        painter.button(scene.skip_rect, 'Skip')
        painter.text('Esc · Pause', (12, scene.skip_rect.centery),
                     role='small', color=MUTED, anchor='midleft')
        self.assertEqual(pixels(self.g.ui_surface), pixels(expected))
        self.assertNotEqual(self.g.ui_surface.get_size(), self.g.canvas.get_size())
        self.assertGreater(painter.font().actual.get_height(),
                           self.g.ui.painter(self.g.canvas).font().actual.get_height())

        self.reach('bridge_damage')
        self.g.update(.5, (0, 0), False)
        with patch.object(RoadWhipPan, 'apply', autospec=True, side_effect=apply) as effect, \
                patch.object(speech_bubble, 'draw_dialogue_frame',
                             wraps=speech_bubble.draw_dialogue_frame) as frame, \
                patch.object(speech_bubble, 'draw_dialogue_prose',
                             wraps=speech_bubble.draw_dialogue_prose) as prose:
            self.g.draw()
        effect.assert_not_called()
        self.assertIs(frame.call_args.args[0].canvas, self.g.ui_surface)
        self.assertIs(prose.call_args.args[0].canvas, self.g.ui_surface)
        self.assertEqual(scene.caption_layout.portrait_key, 'arrival_local')
        self.assertIn('Carrier', ' '.join(scene.caption_layout.name_lines))
        self.assertGreater(len(scene.caption_pages), 1)
        self.assertTrue(pygame.Rect(0, 0, 480, 320).contains(scene.caption_rect))
        self.assertFalse(scene.caption_rect.colliderect(scene.skip_rect))
        camera = scene.camera_position
        photo = scene.scenery['crossroads']['background'].subsurface(
            pygame.Rect(round(camera.x), round(camera.y), 480, 320))
        self.assertEqual(pixels(self.g.canvas), pixels(photo))
        text = scene.dialogue['text']
        self.g.update(100., (0, 0), False)
        key(self.g, pygame.K_SPACE)
        self.assertEqual((scene.shot, scene.dialogue_index, scene.page_index), ('bridge_damage', 0, 1))
        self.assertEqual(scene.dialogue['text'], text)

    def test_reduced_motion_cuts_to_endpoint_without_effect_and_advances_in_one_update(self):
        self.g.audio.reduced_motion = True
        scene = self.start()
        self.question()
        self.g.draw()
        pages = len(scene.caption_pages)
        for _ in range(pages):
            key(self.g, pygame.K_SPACE)
        self.assertEqual((scene.shot, scene.phase_time), ('road_pan', 0.))
        sample = scene.road_pan_sample
        self.assertEqual(tuple(scene.camera_position), tuple(scene.crossroads_data['camera_bridge']))
        self.assertEqual((sample.progress, sample.camera_velocity), (1., (0., 0.)))
        self.assertEqual((sample.active, sample.strength, sample.blur_px, sample.streak_count),
                         (False, 0., 0., 0))
        frozen = world_state(self.g)
        with patch.object(RoadWhipPan, '_blur', wraps=RoadWhipPan._blur) as blur, \
                patch.object(RoadWhipPan, '_streaks', wraps=RoadWhipPan._streaks) as streaks, \
                patch.object(self.g.music, 'play', wraps=self.g.music.play) as music:
            self.g.draw()
            photo = scene.scenery['crossroads']['background'].subsurface(
                pygame.Rect(*scene.crossroads_data['camera_bridge'], 480, 320))
            self.assertEqual(pixels(self.g.canvas), pixels(photo))
            self.g.update(1/60, (1, 1), True)
            self.assertEqual((scene.shot, scene.dialogue_index, scene.page_index), ('bridge_damage', 0, 0))
            self.g.update(.4, (0, 0), False)
            self.assertEqual(scene.dialogue, scene.phase['dialogue'][0])
            blur.assert_not_called()
            streaks.assert_not_called()
            music.assert_not_called()
        self.assertEqual(world_state(self.g), frozen)

    def test_pan_and_bridge_cuts_never_restart_royalty(self):
        scene = self.start()
        with patch.object(self.g.music, 'play', wraps=self.g.music.play) as requests, \
                patch.object(self.g.music, '_start', wraps=self.g.music._start) as starts, \
                patch.object(pygame.mixer.music, 'load', wraps=pygame.mixer.music.load) as loads, \
                patch.object(pygame.mixer.music, 'play', wraps=pygame.mixer.music.play) as plays:
            self.reach('road_pan')
            self.assertEqual(self.g.music.current_track, 'royalty')
            self.reach('relief')
            self.g.update(30., (0, 0), False)
            self.g.draw()
            royalty = [call for call in requests.call_args_list if call.args[0] == 'royalty']
            self.assertEqual(len(royalty), 1)
            self.assertEqual(royalty[0].kwargs, {'fade_ms': 1000})
            self.assertEqual([call.args[0] for call in starts.call_args_list], ['royalty'])
            self.assertEqual([Path(call.args[0]).resolve() for call in loads.call_args_list],
                             [self.g.music.tracks['royalty']['path']])
            self.assertEqual(plays.call_count, 1)
            self.assertEqual(self.g.music.desired_track, 'royalty')
            self.assertEqual(self.g.music.current_track, 'royalty')
            self.assertEqual(scene.shot, 'relief')

    def test_skip_from_paused_pan_releases_audio_and_saves_seen_without_accept_or_reward(self):
        scene = self.middle_of_pan()
        before = (self.g.world, tuple(self.g.player.position), copy.deepcopy(self.g.inventory.to_dict()),
                  copy.deepcopy(self.g.attributes.to_dict()), copy.deepcopy(self.g.quests.to_dict()),
                  set(self.g.social.flags))
        key(self.g, pygame.K_ESCAPE)
        self.g.draw()
        self.assertTrue(scene.paused)
        with patch.object(scene.audio, 'stop', wraps=scene.audio.stop) as stop, \
                patch.object(scene.bird_audio, 'stop', wraps=scene.bird_audio.stop) as bird_stop, \
                patch.object(self.g.music, 'play', wraps=self.g.music.play) as music, \
                patch.object(self.g, 'save_progress', wraps=self.g.save_progress) as save:
            click(self.g, scene.skip_rect.center)
            self.assertEqual(save.call_count, 1)
            stop.assert_called_once()
            bird_stop.assert_called_once()
            music.assert_called_once_with('eldenmere')
        self.assertEqual((scene.active, scene.paused, scene.state, scene.finished_reason),
                         (False, False, 'seen', 'skipped'))
        self.assertEqual((self.g.world, tuple(self.g.player.position), self.g.inventory.to_dict(),
                          self.g.attributes.to_dict(), self.g.quests.to_dict(), set(self.g.social.flags)), before)
        self.assertEqual(self.g.quests.status(REGENT_QUEST), 'available')
        self.assertEqual(self.g.regent_quest.stage, 'idle')
        self.assertTrue(self.g.mill_quest.restored)
        self.assertFalse(self.g.music.paused)
        self.assertEqual(self.g.music.desired_track, 'eldenmere')
        self.assertEqual(self.g.music._duck_target, 1.)
        self.assertEqual(scene.audio.channels, [])
        self.assertEqual(scene.bird_audio.voices, {})
        saved = self.path.read_bytes()
        self.assertEqual(json.loads(saved)['regent_arrival'], {'version': 1, 'state': 'seen'})
        self.assertFalse(scene.finish('skipped'))
        self.assertFalse(scene.request())
        self.assertFalse(scene.maybe_start())
        self.assertEqual(self.path.read_bytes(), saved)
        self.g.update(1., (0, 0), False)
        self.assertEqual(self.g.music.current_track, 'eldenmere')
        self.assertFalse(scene.active)
        self.assertEqual(self.g.quests.status(REGENT_QUEST), 'available')
        self.assertEqual(self.g.regent_quest.stage, 'idle')
        self.assertEqual(self.g.inventory.to_dict(), before[2])
        self.assertEqual(self.g.attributes.to_dict(), before[3])


class RegentCrossroadsManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(SCENE.read_text())
        cls.manifest = json.loads((SCENE.parent/cls.data['crossroads_manifest']).read_text())

    def rejected(self, data, manifest, message):
        # The real constructor must reject before any Game/audio/art access.
        # Both authored files are still read; only their decoded records vary.
        with patch('regent_arrival.json.loads', side_effect=[data, manifest]), \
                patch('pygame.image.load') as load, self.assertRaisesRegex(ValueError, message):
            RegentArrival(object())
        load.assert_not_called()

    def test_scene_uses_authored_stations_and_question_pan_account_relief_order(self):
        phases = {phase['id']: phase for phase in self.data['phases']}
        order = list(phases)
        expected = ['crossroads_establishing', 'locals', 'road_pan', 'bridge_damage', 'relief']
        first = order.index(expected[0])
        self.assertEqual(order[first:first+len(expected)], expected)
        aliases = {'aldric': 'aldric', 'local': 'carrier', 'clerk': 'clerk', 'caravan': 'parked_caravan'}
        for shot in ('crossroads_establishing', 'locals', 'road_pan', 'relief'):
            phase = phases[shot]
            with self.subTest(shot=shot):
                self.assertEqual(phase['scene'], 'crossroads')
                self.assertEqual({actor['id'] for actor in phase['actors']}, set(aliases))
                for actor in phase['actors']:
                    self.assertEqual(actor['position'], self.manifest['actor_anchors'][aliases[actor['id']]])
                    self.assertFalse(any(key in actor for key in ('to', 'path', 'route')))
                self.assertEqual(phase['camera']['from'], self.manifest['camera_junction'])
        self.assertEqual(phases['road_pan']['min_seconds'], .8)
        self.assertEqual(phases['road_pan']['camera_track'], 'west_road')
        self.assertEqual(phases['road_pan']['dialogue'], [])
        self.assertEqual(phases['road_pan']['camera']['to'], self.manifest['camera_bridge'])
        self.assertEqual(phases['bridge_damage']['camera']['from'], self.manifest['camera_bridge'])
        self.assertEqual(phases['bridge_damage']['camera']['to'], self.manifest['camera_bridge'])
        self.assertEqual(phases['bridge_damage']['actors'], [])
        self.assertEqual([line['speaker'] for line in phases['bridge_damage']['dialogue']], ['local', 'local'])
        self.assertEqual(phases['locals']['dialogue'][-1],
                         {'speaker': 'aldric', 'text': 'Were you here when it happened?'})
        self.assertIn('flash', phases['bridge_damage']['dialogue'][0]['text'])
        self.assertIn('both sides', phases['bridge_damage']['dialogue'][1]['text'])
        self.assertEqual(phases['relief']['dialogue'][0]['speaker'], 'aldric')
        self.assertIn('elsewhere', phases['relief']['dialogue'][0]['text'])
        self.assertFalse(phases['relief'].get('fade_in') or phases['relief'].get('fade_out'))

    def test_constructor_rejects_out_of_plate_or_nonfinite_crossroads_cameras(self):
        width, height = self.manifest['canvas']
        invalid = ((-1, 0), (0, -1), (width-479, 0), (0, height-319),
                   (math.nan, 0), (0, math.inf), (True, 0), (0,))
        for endpoint in ('from', 'to'):
            for point in invalid:
                with self.subTest(endpoint=endpoint, point=point):
                    data = copy.deepcopy(self.data)
                    phase = next(phase for phase in data['phases'] if phase['id'] == 'locals')
                    phase['camera'][endpoint] = list(point)
                    self.rejected(data, self.manifest, 'camera leaves its plate')

    def test_constructor_rejects_invalid_effect_tracks_and_dialogue_during_pan(self):
        changes = (
            {'camera_track': 'unknown_effect'},
            {'scene': 'gate', 'camera': {'from': [380, 140], 'to': [380, 140]}},
            {'dialogue': [{'speaker': 'aldric', 'text': 'Not during the whip pan.'}]},
            {'camera': {'from': [3733, 623], 'to': self.manifest['camera_bridge']}},
            {'camera': {'from': self.manifest['camera_junction'], 'to': [433, 1203]}},
        )
        for change in changes:
            with self.subTest(change=change):
                data = copy.deepcopy(self.data)
                phase = next(phase for phase in data['phases'] if phase['id'] == 'road_pan')
                phase.update(change)
                self.rejected(data, self.manifest, 'geographic camera track')

    def test_constructor_validates_panorama_camera_track_before_loading_images(self):
        manifest = copy.deepcopy(self.manifest)
        manifest['camera_path'][10][0] = manifest['canvas'][0]-479
        self.rejected(self.data, manifest, 'viewport leaves panorama bounds')


if __name__ == '__main__':
    unittest.main()