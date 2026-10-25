"""Opening story checkpoints, actor ownership and optional bedroom inspection."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pygame

from opening import OpeningSequence
from quests import OPENING_QUEST, QuestLog
from social import SocialSystem


class Actor:
    def __init__(self, identifier):
        self.data = {'id': identifier}
        self.position = pygame.Vector2(288, 214) if identifier == 'mother_serene' else pygame.Vector2(160, 262)
        self.probe_size = (12, 8)
        self.state_ms = 0
        self.scene_id = 'sanctuary_dining'
        self.story_paused = False
        self.draw_anchor = (12, 30)
        self.idles = {direction: pygame.Surface((24, 36), pygame.SRCALPHA)
                      for direction in ('front', 'left', 'right', 'back')}

    @property
    def blocker(self):
        return pygame.Rect(round(self.position.x)-6, round(self.position.y)-4, 12, 8)

    def select_step(self, step, position, scene_id, facing):
        self.state = step
        self.position.update(position)
        self.scene_id = scene_id
        self.facing = facing
        self.state_ms = 0

    def end_conversation(self):
        pass

    def _duration(self):
        return 1000


class World:
    def __init__(self, identifier):
        self.size = (432, 336)
        self.probe_size = (24, 12)
        self.npcs = []
        self.entities = [
            {'id': 'chair_west', 'position': [120, 174], 'rect': pygame.Rect(120, 174, 24, 36)},
            {'id': 'chair_east', 'position': [192, 174], 'rect': pygame.Rect(192, 174, 24, 36)},
            {'id': 'bed', 'position': [36, 108], 'rect': pygame.Rect(36, 108, 48, 72),
             'surfaces': [pygame.Surface((48, 72), pygame.SRCALPHA)]}]
        self.data = {'id': identifier, 'spawn': [216, 294], 'destinations': {
            'bed': [60, 186], 'books': [108, 90], 'notes': [168, 156],
            'drawing': [60, 90], 'wardrobe': [228, 120]}}

    def can_stand(self, point, size=None, ignore_npc=None, player_blocker=None):
        return (12 <= point[0] <= self.size[0]-12 and
                6 <= point[1] <= self.size[1]-6 and
                not any(actor is not ignore_npc and actor.blocker.collidepoint(point)
                        for actor in self.npcs))

    def image(self, path):
        surface = pygame.Surface((24, 36), pygame.SRCALPHA)
        surface.fill('#bc8f70')
        return surface


class Player:
    def __init__(self):
        self.position = pygame.Vector2(60, 186)
        self.facing = 'front'
        self.moving = False
        self.walk_ms = 0

    def update(self, direction, seconds, world, running=False):
        delta = pygame.Vector2(direction)
        self.moving = False
        if delta.length_squared():
            candidate = self.position+delta.normalize()*72*seconds
            if world.can_stand(candidate):
                self.position.update(candidate)
                self.moving = True
                self.walk_ms += seconds*1000


class Fixture:
    def __init__(self):
        self.scenes = {identifier: World(identifier) for identifier in
                       ('eldenmere.playable', 'sanctuary_bedroom', 'sanctuary_hall', 'sanctuary_dining')}
        self.town = self.scenes['eldenmere.playable']
        self.world = self.town
        self.persistent_npcs = [Actor('mother_serene'), Actor('tomas')]
        self._routine_worlds = {actor: self.scenes['sanctuary_dining'] for actor in self.persistent_npcs}
        self.scenes['sanctuary_dining'].npcs.extend(self.persistent_npcs)
        self.player = Player()
        self.quest_ui = SimpleNamespace(journal_open=False)
        self.map_open = False
        self.quests = QuestLog()
        self.social = SocialSystem(self)
        self.save_count = 0

    def _scene_by_id(self, identifier):
        return self.scenes[identifier]

    def save_progress(self):
        self.save_count += 1


class OpeningSequenceTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((480, 320))
        self.game = Fixture()
        self.opening = OpeningSequence(self.game)

    def tearDown(self):
        pygame.quit()

    def finish_dialogue(self):
        for _ in range(60):
            if not self.game.social.active:
                return
            self.game.social.advance()
            self.opening.update(0)
        self.fail('Script did not finish')

    def finish_until(self, stage, limit=1500):
        for _ in range(limit):
            if self.opening.stage == stage:
                return
            if self.game.social.active:
                self.game.social.advance()
            self.opening.update(1/60)
        self.fail(('Scene stalled', self.opening.stage, self.opening._phase,
                   self.opening.action_name))

    def reach_breakfast(self):
        self.opening.start_new_game()
        self.finish_until('explore')
        self.game.world = self.game._scene_by_id('sanctuary_dining')
        self.game.player.position.update(self.game.world.data['spawn'])
        self.opening.on_enter_scene()
        self.assertEqual(self.game.social.script_identifier, 'opening_greeting')
        self.finish_dialogue()
        for _ in range(600):
            self.opening.update(1/60)
            if self.game.social.script_identifier == 'opening_breakfast':
                return
        self.fail('Breakfast arrival/sit did not finish')

    def test_default_is_ambient_and_snapshot_validation_is_atomic(self):
        self.assertEqual(self.opening.stage, 'disabled')
        self.assertFalse(self.opening.active)
        self.assertFalse(self.opening.locks_player)
        self.assertTrue(self.opening.can_speak('mother_serene'))
        for data in (None, {}, {'version': True, 'stage': 'wake'},
                     {'version': 1, 'stage': 'missing'},
                     {'version': 1, 'stage': 'wake', 'extra': 1}):
            self.assertFalse(self.opening.restore(data))
            self.assertEqual(self.opening.stage, 'disabled')

    def test_wake_uses_one_existing_cast_and_releases_control(self):
        original = set(self.game.persistent_npcs)
        self.opening.start_new_game()
        self.assertEqual(self.game.world.data['id'], 'sanctuary_bedroom')
        self.assertFalse(self.game.player.story_visible)
        self.assertTrue(self.opening.locks_player)
        self.assertFalse(self.opening.can_speak('mother_serene'))
        self.assertTrue(self.opening.can_speak('some_other_villager'))
        tomas = self.game.persistent_npcs[1]
        self.assertEqual(tomas.scene_id, 'sanctuary_hall')
        for actor in original:
            self.assertEqual(sum(scene.npcs.count(actor) for scene in self.game.scenes.values()), 1)
            self.assertTrue(actor.story_paused)
        self.finish_until('explore')
        self.assertEqual(self.opening.stage, 'explore')
        self.assertFalse(self.opening.locks_player)
        self.assertFalse(hasattr(self.game.player, 'story_visible'))
        self.assertEqual(set(self.game.persistent_npcs), original)
        self.assertEqual(tomas.scene_id, 'sanctuary_dining')
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')

    def test_wake_keeps_pillow_head_fixed_and_quilt_below_the_face(self):
        self.opening.start_new_game()
        self.finish_dialogue()
        saw_mask = False
        for _ in range(120):
            self.opening.update(1/120)
            if self.opening.action_name != 'wake_up':
                break
            _, record = self.opening._frame('wake_up', self.opening._action_time)
            position = self.game.player.story_position
            if record['kind'] == 'pillow_head':
                self.assertEqual(tuple(position), (60, 153))
            if self.opening._bed_occlusion:
                saw_mask = True
                chin = position[1]-record['draw_anchor'][1]+record['head_bottom']
                self.assertGreater(self.opening._bed_occlusion[1], chin)
                self.assertLessEqual(self.opening._bed_occlusion[1]+self.opening._bed_occlusion[3], 180)
        self.assertTrue(saw_mask)
        self.assertEqual(self.opening.stage, 'explore')
        self.assertEqual(tuple(self.game.player.position), (90, 186))
        self.assertFalse(hasattr(self.game.player, 'story_position'))

    def test_breakfast_invites_before_walk_and_chairs_never_move(self):
        chairs = [list(entity['position']) for entity in self.game.scenes['sanctuary_dining'].entities]
        self.reach_breakfast()
        self.assertEqual(self.opening.stage, 'breakfast')
        self.assertEqual(tuple(self.game.player.position), (108, 200))
        self.assertEqual(tuple(self.game.player.story_position), (138, 200))
        self.assertEqual([entity['position'] for entity in self.game.world.entities], chairs)
        self.finish_until('assignment')
        self.assertEqual([entity['position'] for entity in self.game.world.entities], chairs)
        self.assertTrue(self.game.world.can_stand(self.game.player.position))
        self.assertEqual(tuple(self.game.player.position), (108, 200))
        self.assertFalse(hasattr(self.game.player, 'story_sprite'))
        self.assertTrue(self.opening.can_speak('mother_serene'))
        self.assertFalse(self.opening.can_speak('tomas'))
        self.assertTrue(all(actor.story_paused for actor in self.game.persistent_npcs))
        self.assertTrue(self.opening._cup_placed)
        self.assertEqual(tuple(self.opening._cup_position), (146, 189))
        self.game.quests.accept(OPENING_QUEST)
        self.opening.update(0)
        self.assertEqual(self.opening.stage, 'acceptance')
        self.assertEqual(self.game.social.script_identifier, 'opening_acceptance')
        self.finish_dialogue()
        self.assertEqual(self.opening.stage, 'done')
        self.assertTrue(all(not actor.story_paused for actor in self.game.persistent_npcs))
        self.assertTrue(all(not hasattr(actor, 'story_sprite') for actor in self.game.persistent_npcs))

    def test_fast_dialogue_cannot_skip_required_actions_or_sound_beats(self):
        self.opening.start_new_game()
        self.finish_dialogue()
        self.assertEqual(self.opening.stage, 'wake')
        self.assertTrue(self.opening.in_action)
        self.opening.update(.2)
        self.assertTrue(hasattr(self.game.player, 'story_sprite'))
        self.assertEqual(self.opening.stage, 'wake')
        self.finish_until('explore')
        self.assertIn('bedsheet', self.opening.drain_sound_events())
        self.game.world = self.game._scene_by_id('sanctuary_dining')
        self.game.player.position.update(216, 294)
        self.opening.on_enter_scene()
        observed = set()
        sounds = []
        for _ in range(1500):
            if self.opening.action_name:
                observed.add(self.opening.action_name)
            self.finish_dialogue()
            self.opening.update(1/60)
            sounds.extend(self.opening.drain_sound_events())
            if self.opening.stage == 'assignment':
                break
        self.assertEqual(self.opening.stage, 'assignment')
        self.assertTrue({'walk_to_breakfast', 'sit', 'plate', 'eat', 'cup', 'stand'} <= observed)
        self.assertTrue({'footstep', 'chair', 'plate', 'bite', 'cup'} <= set(sounds))
        self.assertEqual(sounds.count('plate'), 1)
        self.assertEqual(sounds.count('cup'), 1)
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')
        self.assertEqual(self.opening.drain_sound_events(), [])

    def test_scene_camera_focus_is_stable_across_breakfast_dialogue_and_motion(self):
        self.opening.start_new_game()
        self.assertEqual(self.opening.camera_focus(), (74, 150))
        self.finish_until('explore')
        self.assertIsNone(self.opening.camera_focus())

        self.game.world = self.game._scene_by_id('sanctuary_dining')
        self.game.player.position.update(216, 294)
        self.opening.on_enter_scene()
        for _ in range(1500):
            self.assertEqual(self.opening.camera_focus(), (210, 185))
            self.finish_dialogue()
            self.opening.update(1/60)
            if self.opening.stage == 'assignment':
                break
        self.assertIsNone(self.opening.camera_focus())

    def test_wood_steps_match_two_contacts_per_walk_cycle_and_stop_when_idle(self):
        for _ in range(28):
            self.opening.record_footsteps(72/50)
        self.assertEqual(self.opening.drain_sound_events(), ['footstep', 'footstep'])
        self.opening.record_footsteps(10)
        self.opening.record_footsteps(0)
        self.opening.record_footsteps(11)
        self.assertEqual(self.opening.drain_sound_events(), [])

    def test_blocked_arrival_waits_instead_of_teleporting(self):
        self.opening.start_new_game()
        self.finish_until('explore')
        self.game.world = self.game._scene_by_id('sanctuary_dining')
        self.game.player.position.update(self.game.world.data['spawn'])
        before = self.game.player.position.copy()
        self.opening.on_enter_scene()
        with patch('opening.find_path', return_value=None):
            self.finish_dialogue()
            for _ in range(120):
                self.opening.update(1/60)
        self.assertEqual(self.game.player.position, before)
        self.assertTrue(self.opening.controls_player)
        self.assertFalse(self.game.social.locked)
        self.assertEqual(self.opening.stage, 'breakfast')

    def test_scene_restore_replays_but_accepted_progress_never_regresses(self):
        self.assertTrue(self.opening.restore({'version': 1, 'stage': 'wake'}))
        self.assertTrue(self.game.social.scripted)
        self.assertEqual(self.game.social.script_identifier, 'opening_wake')
        self.finish_dialogue()
        self.assertTrue(self.opening.restore({'version': 1, 'stage': 'breakfast'}))
        self.assertFalse(self.opening.controls_player)
        self.assertEqual(self.game.social.script_identifier, 'opening_greeting')
        self.assertEqual(tuple(self.game.player.position), (216, 294))
        self.game.quests.accept(OPENING_QUEST)
        self.assertTrue(self.opening.restore({'version': 1, 'stage': 'wake'}))
        self.assertEqual(self.opening.stage, 'done')
        self.assertFalse(self.game.social.locked)
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'active')
        self.assertTrue(all(not actor.story_paused for actor in self.game.persistent_npcs))

    def test_inspection_is_optional_and_requires_nearby_free_bedroom_control(self):
        self.opening.start_new_game()
        self.assertFalse(self.opening.inspect_nearby())
        self.finish_until('explore')
        self.game.player.position.update(108, 90)
        self.assertEqual(self.opening.interaction_hint(), 'E: inspect bookshelf')
        self.assertTrue(self.opening.inspect_nearby())
        self.assertEqual(self.game.social.script_identifier, 'bedroom_inspect_books')
        self.assertEqual(self.game.social.page['speaker'], 'caelan')
        self.finish_until('explore')
        self.assertEqual(self.opening.stage, 'explore')
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')
        self.game.player.position.update(300, 280)
        self.assertEqual(self.opening.interaction_hint(), '')
        self.assertFalse(self.opening.inspect_nearby())
        self.game.player.position.update(108, 90)
        self.game.quest_ui.journal_open = True
        self.assertFalse(self.opening.inspect_nearby())

    def test_assignment_accept_save_window_restores_followup_without_reacceptance(self):
        self.game.quests.accept(OPENING_QUEST)
        self.game.quests.drain_events()
        self.assertTrue(self.opening.restore({'version': 1, 'stage': 'assignment'}))
        self.assertEqual(self.opening.stage, 'acceptance')
        self.assertEqual(self.game.social.script_identifier, 'opening_acceptance')
        self.assertEqual(self.game.quests.drain_events(), [])
        self.finish_dialogue()
        self.assertEqual(self.opening.stage, 'done')

    def test_held_station_finishes_handoff_then_freezes_for_conversation(self):
        self.opening.stage = 'assignment'
        actor = self.game.persistent_npcs[0]
        actor.conversation_requested = True
        actor.conversation_ready = False
        actor._conversation_safe = lambda: actor.state_ms >= 400
        self.opening.update(.8)
        self.assertTrue(actor.conversation_ready)
        self.assertLess(actor.state_ms, 450)
        before = actor.state_ms
        self.opening.update(.5)
        self.assertEqual(actor.state_ms, before)


if __name__ == '__main__':
    unittest.main()
