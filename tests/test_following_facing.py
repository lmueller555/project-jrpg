"""Companion turn stability without changing collision-aware travel or gait."""
from collections import deque
import os
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from npc_following import (following_facing, idle_following_facing,
                           reset_following_facing, TURN_INTERVAL)


class Actor:
    def __init__(self, facing='front', following=True):
        self.position = pygame.Vector2()
        self.facing = facing
        self.story_following = following
        self.probe_size = (8, 8)
        self.walk_ms = 0.0
        self.moving = False


def step(actor, delta, seconds=1/60):
    with following_facing(actor, seconds):
        actor.position += delta
        # Emulate the final, possibly misleading navigation waypoint's turn.
        actor.facing = 'left'


class FollowingFacingTests(unittest.TestCase):
    def test_tiny_grid_axis_changes_and_diagonal_noise_do_not_flicker(self):
        actor = Actor()
        step(actor, (1, .98))
        self.assertEqual(actor.facing, 'right')
        for index in range(180):
            step(actor, (.98, 1) if index % 2 else (1, .98))
            self.assertEqual(actor.facing, 'right')
        # A stair-step route can present one different axis each video frame.
        for index in range(120):
            step(actor, (0, 1) if index % 2 else (1, 0))
            self.assertEqual(actor.facing, 'right')

    def test_real_turns_are_responsive_but_never_change_faster_than_hold(self):
        actor = Actor()
        changes = []
        previous = actor.facing
        for index in range(180):
            delta = ((1, 0), (0, 1), (-1, 0), (0, -1))[(index//12) % 4]
            step(actor, delta)
            if actor.facing != previous:
                changes.append((index+1)/60)
                previous = actor.facing
        self.assertGreater(len(changes), 8)
        self.assertTrue(all(after-before >= TURN_INTERVAL-1e-8
                            for before, after in zip(changes, changes[1:])))
        step(actor, (1, 0), .25)
        self.assertEqual(actor.facing, 'right')
        for _ in range(5):step(actor, (-1, 0))
        self.assertEqual(actor.facing, 'right')
        for _ in range(8):step(actor, (-1, 0))
        self.assertEqual(actor.facing, 'left')

    def test_turn_timing_and_distance_are_consistent_at_30_and_60_fps(self):
        runs = []
        for fps in (30, 60):
            actor = Actor()
            changes = []
            snapshots = []
            previous = actor.facing
            for index in range(2*fps):
                direction = (1, 0) if index < fps//2 else (0, 1) if index < fps else (-1, 0)
                step(actor, pygame.Vector2(direction)*60/fps, 1/fps)
                if actor.facing != previous:
                    changes.append((actor.facing, (index+1)/fps))
                    previous = actor.facing
                if index+1 in (fps//2, fps, fps*3//2, fps*2):
                    snapshots.append((tuple(actor.position), actor.facing))
            runs.append((actor, changes, snapshots))
        self.assertEqual(runs[0][2], runs[1][2])
        self.assertEqual([name for name, _ in runs[0][1]], [name for name, _ in runs[1][1]])
        for (_, first), (_, second) in zip(runs[0][1], runs[1][1]):
            self.assertLessEqual(abs(first-second), 1/30+1e-8)

    def test_pause_and_negative_time_do_not_consume_the_turn_interval(self):
        actor = Actor()
        step(actor, (1, 0))
        for _ in range(3):step(actor, (1, 0))
        for seconds in [0]*30+[-.1]*30:
            step(actor, (0, 0), seconds)
            self.assertEqual(actor.facing, 'right')
        for _ in range(4):step(actor, (-1, 0))
        self.assertEqual(actor.facing, 'right')
        for _ in range(8):step(actor, (-1, 0))
        self.assertEqual(actor.facing, 'left')

    def test_tiny_or_zero_motion_preserves_the_visible_facing(self):
        actor = Actor()
        step(actor, (1, 0))
        for delta in [(0, 0), (.001, -.001), (-.01, .01)]*30:
            step(actor, delta)
            self.assertEqual(actor.facing, 'right')

    def test_stop_and_relocation_start_a_fresh_responsive_follow(self):
        actor = Actor()
        step(actor, (1, 0))
        reset_following_facing(actor)
        step(actor, (-1, 0))
        self.assertEqual(actor.facing, 'left')
        actor.position.update(100, 100)
        step(actor, (0, -1))
        self.assertEqual(actor.facing, 'back')

    def test_short_stops_cannot_bypass_the_follow_turn_limit(self):
        from halden_visit import HaldenVisit
        actor = Actor()
        world = SimpleNamespace(
            probe_rect=lambda position: pygame.Rect(999, 999, 8, 8),
            can_stand=lambda *args: True)
        player = SimpleNamespace(position=pygame.Vector2(100, 0))
        controller = HaldenVisit.__new__(HaldenVisit)
        controller.tomas = actor
        controller.game = SimpleNamespace(world=world, player=player)
        controller.last_scene = world
        controller.trail = deque()
        controller.paths = {}
        controller._travel_room = lambda room, seconds: True
        direction = [1]

        def movement(value, room, goal, seconds, speed):
            value.position += (direction[0], 0)
            value.facing = 'right' if direction[0] > 0 else 'left'
            return False

        controller._move_path = movement
        for index in range(90):
            direction[0] = 1 if index % 2 == 0 else -1
            player.position.update(actor.position+(100, 0))
            controller._follow(1/60)
            self.assertEqual(actor.facing, 'right')
            # This is the actual proximity-stop branch, not a helper-only test.
            player.position.update(actor.position+(34, 0))
            controller._follow(1/60)
            self.assertEqual(actor.facing, 'right')
        for _ in range(30):controller._follow(1/60)
        direction[0] = -1
        player.position.update(actor.position+(100, 0))
        controller._follow(1/60)
        self.assertEqual(actor.facing, 'left')

    def test_a_consistent_turn_can_complete_across_brief_stops(self):
        actor = Actor()
        step(actor, (1, 0))
        first_change = None
        for index in range(20):
            step(actor, (-1, 0))
            if actor.facing == 'left' and first_change is None:
                first_change = (index*2+1)/60
            idle_following_facing(actor, 1/60)
        self.assertEqual(actor.facing, 'left')
        self.assertIsNotNone(first_change)
        self.assertGreaterEqual(first_change, TURN_INTERVAL-1e-8)

    def test_explicit_conversation_turns_and_nonfollowers_remain_immediate(self):
        actor = Actor()
        step(actor, (1, 0))
        actor.facing = 'back'
        self.assertEqual(actor.facing, 'back')
        step(actor, (-1, 0))
        self.assertEqual(actor.facing, 'left')
        actor.story_following = False
        with following_facing(actor, 1/60):
            actor.position += (0, 1)
            actor.facing = 'front'
        self.assertEqual(actor.facing, 'front')
        actor.story_following = True
        step(actor, (0, -1))
        self.assertEqual(actor.facing, 'back')

    def test_each_companion_has_independent_turn_history(self):
        first, second = Actor(), Actor()
        for _ in range(60):
            step(first, (1, 0))
            step(second, (0, -1))
        self.assertEqual((first.facing, second.facing), ('right', 'back'))

    def test_actual_quest_moves_keep_positions_routes_and_animation_time(self):
        from halden_visit import HaldenVisit
        from lantern_quest import LanternQuest
        from mill_quest import MillQuest
        for kind in (HaldenVisit, MillQuest, LanternQuest):
            results = []
            for following in (False, True):
                actor = Actor(facing='right', following=following)
                world = SimpleNamespace(
                    probe_rect=lambda position: pygame.Rect(999, 999, 8, 8),
                    can_stand=lambda *args: True)
                game = SimpleNamespace(world=world, town=world,
                                       player=SimpleNamespace(position=pygame.Vector2(1000, 1000)))
                controller = kind.__new__(kind)
                controller.game = game
                route = deque([(.6, 0), (.6, .4), (1.2, .4), (1.2, .8), (10, 10)])
                if kind is LanternQuest:
                    controller.paths = {actor: ((10, 10), route, False)}
                    controller.retries = {}
                    controller._world = lambda value: world
                    controller._move(actor, (10, 10), 1/60, 60)
                else:
                    controller.paths = {actor: ((10, 10), route)}
                    controller.retry = {}
                    if kind is HaldenVisit:
                        controller._move(actor, world, (10, 10), 1/60, 60)
                    else:
                        controller.mira = actor
                        controller._mira_world = controller.town = world
                        controller._move((10, 10), 1/60, 60)
                results.append((tuple(actor.position), list(route), actor.walk_ms, actor.facing))
            self.assertEqual(results[0][:3], results[1][:3], kind.__name__)
            self.assertEqual(results[0][3], 'front', kind.__name__)
            self.assertEqual(results[1][3], 'right', kind.__name__)


if __name__ == '__main__':unittest.main()
