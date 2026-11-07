"""Nonblocking grass reacts to actual feet, holds, and recovers independently."""
from copy import deepcopy
import os
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from interactive_grass import DIRECTIONS, InteractiveGrass


def actor(position, *, running=False, facing='front', size=(24, 12)):
    return SimpleNamespace(position=pygame.Vector2(position), running=running,
                           facing=facing, probe_size=size)


def field(instances=None):
    """Distinct colors make selected rear/front poses independently observable."""
    surfaces = {}
    def pose(name, color):
        surfaces[name] = pygame.Surface((24, 32), pygame.SRCALPHA)
        surfaces[name].fill(color)
        return name
    idle = []
    for index in range(2):
        idle.append({'rear': pose('idle.rear.'+str(index), (0, 70+index*20, 0)),
                     'front': pose('idle.front.'+str(index), (0, 90+index*20, 0)),
                     'duration_ms': 100})
    parted = {}
    for direction_index, direction in enumerate(DIRECTIONS):
        parted[direction] = [{'rear': pose(direction+'.rear.'+str(index),
                                          (20+direction_index*40, index*60, 0)),
                              'front': pose(direction+'.front.'+str(index),
                                           (30+direction_index*40, index*60, 0))}
                             for index in range(3)]
    manifest = {'tall_grass': {'anchor': [12, 28], 'frame_size': [24, 32],
                              'contact_rect': [-10, -8, 20, 12],
                              'variants': {'test': {'idle': idle, 'parted': parted}}}}
    instances = instances or [{'id': 'a', 'variant': 'test', 'position': [100, 100]}]
    return InteractiveGrass(manifest, instances, surfaces.__getitem__)


class InteractiveGrassTests(unittest.TestCase):
    def test_standing_holds_the_same_opening_without_repeated_activations(self):
        grass = field();person = actor((100, 100), facing='right')
        before = tuple(person.position)
        for _ in range(120):grass.update(1/60, [person])
        state = grass.snapshot()['clumps'][0]
        self.assertEqual((state['state'], state['occupants'], state['activations']),
                         ('occupied', 1, 1))
        self.assertEqual(state['strength'], 1)
        self.assertEqual(state['direction'], 'east')
        person.facing = 'left'
        grass.update(.2, [person])
        self.assertEqual(grass.snapshot()['clumps'][0]['direction'], 'east')
        self.assertEqual(tuple(person.position), before)

    def test_travel_direction_comes_from_motion_and_running_parts_more_strongly(self):
        strengths = []
        for running in (False, True):
            grass = field();person = actor((65, 100), running=running, facing='left')
            grass.update(.01, [person])
            person.position.update(100, 100)
            grass.update(.2, [person])
            state = grass.snapshot()['clumps'][0]
            self.assertEqual(state['direction'], 'east')
            strengths.append(state['strength'])
        self.assertEqual(strengths, [1, 2])

    def test_swept_feet_catch_a_fast_crossing_without_false_diagonal_contacts(self):
        grass = field();person = actor((50, 100), running=True)
        grass.update(.01, [person])
        person.position.update(150, 100)
        grass.update(.2, [person])
        state = grass.snapshot()['clumps'][0]
        self.assertEqual((state['occupants'], state['activations']), (0, 1))
        self.assertEqual(state['strength'], 2)
        self.assertEqual(state['direction'], 'east')
        other = field();diagonal = actor((50, 80))
        other.update(.01, [diagonal])
        diagonal.position.update(80, 150)
        other.update(.2, [diagonal])
        self.assertEqual(other.snapshot()['clumps'][0]['activations'], 0)

    def test_recovery_waits_until_the_last_occupant_leaves_then_returns_to_idle(self):
        grass = field();first = actor((100, 100));second = actor((106, 100))
        grass.update(.2, [first, second])
        first.position.update(150, 100)
        for _ in range(60):grass.update(1/60, [first, second])
        self.assertEqual(grass.snapshot()['clumps'][0]['occupants'], 1)
        self.assertEqual(grass.snapshot()['clumps'][0]['strength'], 1)
        second.position.update(150, 100)
        for _ in range(60):grass.update(1/60, [first, second])
        state = grass.snapshot()['clumps'][0]
        self.assertEqual((state['state'], state['strength'], state['occupants']), ('idle', 0, 0))
        self.assertEqual(state['activations'], 1)

    def test_reentry_reverses_recovery_and_preserves_fixed_roots(self):
        grass = field();person = actor((100, 100))
        positions = [record['position'] for record in grass.entity_records]
        rects = [record['rect'].copy() for record in grass.entity_records]
        grass.update(.2, [person]);person.position.update(150, 100)
        grass.update(.1, [person]);grass.update(.2, [person])
        self.assertLess(grass.snapshot()['clumps'][0]['strength'], 1)
        person.position.update(100, 100);grass.update(.1, [person])
        self.assertEqual(grass.snapshot()['clumps'][0]['state'], 'occupied')
        self.assertEqual(grass.snapshot()['clumps'][0]['strength'], 1)
        self.assertEqual([record['position'] for record in grass.entity_records], positions)
        self.assertEqual([record['rect'] for record in grass.entity_records], rects)

    def test_reduced_motion_freezes_breeze_and_uses_static_occupied_pose(self):
        grass = field();person = actor((50, 100), running=True)
        grass.update(.1, [person], reduced_motion=True)
        initial = [record['surfaces'][0] for record in grass.entity_records]
        grass.update(10, [person], reduced_motion=True)
        self.assertEqual([record['surfaces'][0] for record in grass.entity_records], initial)
        person.position.update(100, 100)
        grass.update(.01, [person], reduced_motion=True)
        self.assertEqual(grass.snapshot()['clumps'][0]['strength'], 1)
        held = [record['surfaces'][0] for record in grass.entity_records]
        grass.update(10, [person], reduced_motion=True)
        self.assertEqual([record['surfaces'][0] for record in grass.entity_records], held)
        person.position.update(150, 100)
        grass.update(.2, [person], reduced_motion=True)
        grass.update(.2, [person], reduced_motion=True)
        self.assertEqual(grass.snapshot()['clumps'][0]['strength'], 0)
        self.assertEqual(grass.elapsed_ms, 0)

    def test_different_phase_offsets_do_not_synchronize_identical_clumps(self):
        grass = field([{'id': 'a', 'variant': 'test', 'position': [100, 100]},
                       {'id': 'b', 'variant': 'test', 'position': [130, 100], 'phase_ms': 100}])
        self.assertIsNot(grass.entity_records[0]['surfaces'][0],
                         grass.entity_records[2]['surfaces'][0])

    def test_actors_disappearing_or_becoming_hidden_release_the_vegetation(self):
        for disappear in (False, True):
            grass = field();person = actor((100, 100));grass.update(.2, [person])
            if not disappear:person.story_visible = False
            grass.update(1, [] if disappear else [person])
            self.assertEqual(grass.snapshot()['clumps'][0]['strength'], 0)

    def test_state_snapshots_are_detached_and_bad_time_cannot_mutate_the_field(self):
        grass = field();person = actor((100, 100));grass.update(.2, [person])
        snapshot = grass.snapshot();snapshot['clumps'][0]['position'][0] = -999
        self.assertEqual(grass.clumps[0].position, (100, 100))
        before = deepcopy(grass.snapshot())
        for seconds in (-1, float('nan'), float('inf'), True, '1'):
            with self.subTest(seconds=seconds):
                with self.assertRaises(ValueError):grass.update(seconds, [person])
                self.assertEqual(grass.snapshot(), before)


if __name__ == '__main__':unittest.main()
