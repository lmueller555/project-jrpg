"""One-shot scene actions use authored frames and an update-owned clock."""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from cinematic_actor_actions import ActionPlayer, load_actions

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT/'assets/story/regent_arrival/actors/iselin/animation.json'


def probe_action(hold_ms=None):
    """Reference existing approved drawings; this fixture introduces no artwork."""
    return {
        'entry': [{'pose': 'stand_left', 'duration_ms': 100},
                  {'pose': 'turn_left_back', 'duration_ms': 200}],
        'hold': {'pose': 'listen_left', 'duration_ms': hold_ms},
        'recovery': [{'pose': 'gesture_left', 'duration_ms': 120},
                     {'pose': 'stand_right', 'duration_ms': 80}],
        'rest_pose': 'stand_back',
    }


class CinematicActorActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.display.set_mode((80, 96))
        cls.record = json.loads(MANIFEST.read_text())
        cls.poses = {key: pygame.image.load(str(MANIFEST.parent/name)).convert_alpha()
                     for key, name in cls.record['poses'].items()}

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def clips(self, spec=None, *, path=MANIFEST, record=None):
        fixture = deepcopy(self.record if record is None else record)
        fixture['actions'] = {'probe': probe_action() if spec is None else spec}
        return load_actions(fixture, self.poses, path)

    def player(self, hold_ms=None):
        player = ActionPlayer(self.clips(probe_action(hold_ms)))
        self.assertTrue(player.play('probe', 'first-cue'))
        return player

    def test_absent_actions_preserve_legacy_manifest_and_idle_player(self):
        self.assertEqual(load_actions(self.record, self.poses, MANIFEST), {})
        player = ActionPlayer({})
        self.assertIsNone(player.frame)
        self.assertEqual(player.stage, 'idle')
        self.assertFalse(player.active)
        self.assertIsNone(player.cue_id)
        self.assertFalse(player.release())

    def test_individual_frame_and_timed_hold_boundaries_do_not_loop(self):
        # Each sample starts independently, so a large update must cross every
        # intervening stage just as a series of small updates would.
        samples = (
            (0, 'entry', 0, 'stand_left'),
            (.099999, 'entry', 0, 'stand_left'),
            (.1, 'entry', 1, 'turn_left_back'),
            (.299999, 'entry', 1, 'turn_left_back'),
            (.3, 'hold', None, 'listen_left'),
            (.449999, 'hold', None, 'listen_left'),
            (.45, 'recovery', 0, 'gesture_left'),
            (.569999, 'recovery', 0, 'gesture_left'),
            (.57, 'recovery', 1, 'stand_right'),
            (.649999, 'recovery', 1, 'stand_right'),
            (.65, 'rest', None, 'stand_back'),
            (10, 'rest', None, 'stand_back'),
        )
        for seconds, stage, index, pose in samples:
            with self.subTest(seconds=seconds):
                player = self.player(150)
                player.update(seconds)
                self.assertEqual(player.stage, stage)
                self.assertEqual(player.state['frame_index'], index)
                self.assertIs(player.frame, self.poses[pose])
                self.assertEqual(player.active, stage != 'rest')

    def test_large_and_partitioned_updates_select_the_same_authored_pose(self):
        one = self.player(150)
        divided = self.player(150)
        one.update(.603)
        for seconds in (.071, .133, .211, .188):
            divided.update(seconds)
        self.assertEqual(one.stage, divided.stage)
        self.assertIs(one.frame, divided.frame)
        self.assertEqual(one.state['frame_index'], divided.state['frame_index'])
        self.assertAlmostEqual(one.state['elapsed_ms'], divided.state['elapsed_ms'])

    def test_partitioned_recovery_reaches_exact_boundary_without_roundoff_delay(self):
        spec = probe_action()
        spec['entry'] = spec['entry'][:1]       # 100 ms, then indefinite hold.
        spec['recovery'] = spec['recovery'][:1] # 120 ms, then rest.

        def released():
            player = ActionPlayer(self.clips(spec))
            self.assertTrue(player.play('probe', 'partitioned-cue'))
            player.update(.3)
            self.assertEqual(player.stage, 'hold')
            self.assertTrue(player.release('partitioned-cue'))
            return player

        # Scene clocks produce deltas by subtracting successive timestamps.
        # Nominal 20 ms steps can therefore sum a few float bits below 120 ms.
        clocks = (.3, .32, .34, .36, .38, .40, .42)
        sampled = tuple(end-start for start, end in zip(clocks, clocks[1:]))
        for deltas in ((.02,)*6, sampled):
            with self.subTest(deltas=deltas):
                player = released()
                for delta in deltas[:-1]:player.update(delta)
                self.assertEqual(player.stage, 'recovery')
                player.update(deltas[-1])
                self.assertEqual(player.stage, 'rest')
                self.assertIs(player.frame, self.poses['stand_back'])

        player = released()
        player.update(.12-1e-11) # A genuine 1e-8 ms before the boundary.
        self.assertEqual(player.stage, 'recovery')
        self.assertIs(player.frame, self.poses['gesture_left'])
        player.update(1e-11)
        self.assertEqual(player.stage, 'rest')

    def test_indefinite_hold_waits_for_matching_release_then_recovers_once(self):
        player = self.player()
        player.update(20)
        self.assertEqual(player.stage, 'hold')
        self.assertIs(player.frame, self.poses['listen_left'])
        self.assertFalse(player.release('some-other-cue'))
        self.assertEqual(player.stage, 'hold')
        self.assertTrue(player.release('first-cue'))
        self.assertEqual(player.stage, 'recovery')
        self.assertIs(player.frame, self.poses['gesture_left'])
        self.assertFalse(player.release('first-cue'))
        player.update(.2)
        self.assertEqual(player.stage, 'rest')
        self.assertIs(player.frame, self.poses['stand_back'])
        self.assertFalse(player.release())

    def test_early_release_finishes_both_entry_frames_before_recovery(self):
        player = self.player()
        player.update(.05)
        self.assertTrue(player.release())
        self.assertTrue(player.state['release_requested'])
        self.assertFalse(player.release())
        player.update(.05)
        self.assertEqual(player.stage, 'entry')
        self.assertIs(player.frame, self.poses['turn_left_back'])
        player.update(.2)
        self.assertEqual(player.stage, 'recovery')
        self.assertIs(player.frame, self.poses['gesture_left'])
        player.update(.2)
        self.assertEqual(player.stage, 'rest')

    def test_cue_ledger_rejects_duplicates_and_busy_replacement_until_clear(self):
        player = self.player(150)
        player.update(.1)
        before = player.state
        self.assertFalse(player.play('probe', 'first-cue'))
        self.assertFalse(player.play('probe', 'second-cue'))
        self.assertEqual(player.state, before)
        player.update(1)
        self.assertFalse(player.play('probe', 'first-cue'))
        self.assertTrue(player.play('probe', 'second-cue'))
        player.update(1)
        self.assertFalse(player.play('probe', 'first-cue'))
        player.clear()
        self.assertIsNone(player.frame)
        self.assertEqual(player.stage, 'idle')
        self.assertTrue(player.play('probe', 'first-cue'))

    def test_frame_and_diagnostic_reads_cannot_advance_or_mutate_player(self):
        player = self.player()
        player.update(.125)
        before = player.state
        for _ in range(20):
            self.assertIs(player.frame, self.poses['turn_left_back'])
            changed = player.state
            changed['elapsed_ms'] = 99999
        self.assertEqual(player.state, before)
        player.update(0)
        self.assertEqual(player.state, before)

    def test_invalid_update_values_are_rejected_without_advancing(self):
        player = self.player()
        before = player.state
        for seconds in (-.001, math.nan, math.inf, -math.inf, True, '0.1', None):
            with self.subTest(seconds=seconds):
                with self.assertRaises(ValueError):player.update(seconds)
                self.assertEqual(player.state, before)

    def test_unknown_action_or_invalid_cue_cannot_start_a_player(self):
        player = ActionPlayer(self.clips())
        with self.assertRaises(ValueError):player.play('not-authored', 'cue')
        for cue in ('', None, 1, True):
            with self.subTest(cue=cue):
                with self.assertRaises(ValueError):player.play('probe', cue)
        self.assertEqual(player.stage, 'idle')

    def test_invalid_durations_fail_closed_in_every_action_stage(self):
        for stage in ('entry', 'hold', 'recovery'):
            for duration in (0, -1, math.nan, math.inf, -math.inf, True, '100'):
                spec = probe_action()
                frame = spec[stage] if stage == 'hold' else spec[stage][0]
                frame['duration_ms'] = duration
                with self.subTest(stage=stage, duration=duration):
                    with self.assertRaises(ValueError):self.clips(spec)
        for stage in ('entry', 'recovery'):
            spec = probe_action();spec[stage][0]['duration_ms'] = None
            with self.subTest(stage=stage, duration=None):
                with self.assertRaises(ValueError):self.clips(spec)

    def test_missing_frames_empty_phases_and_unknown_poses_fail_closed(self):
        invalid = []
        for stage in ('entry', 'recovery'):
            spec = probe_action();spec[stage] = [];invalid.append(spec)
        for stage in ('entry', 'hold', 'recovery'):
            spec = probe_action()
            frame = spec[stage] if stage == 'hold' else spec[stage][0]
            frame['pose'] = 'not-a-pose';invalid.append(spec)
            spec = probe_action()
            frame = spec[stage] if stage == 'hold' else spec[stage][0]
            frame.pop('pose');invalid.append(spec)
        spec = probe_action();spec['rest_pose'] = 'not-a-pose';invalid.append(spec)
        for index, spec in enumerate(invalid):
            with self.subTest(case=index):
                with self.assertRaises(ValueError):self.clips(spec)

    def test_malformed_action_maps_and_frame_containers_are_rejected(self):
        for actions in (None, [], 'probe', {'': probe_action()}, {'probe': []}):
            record = deepcopy(self.record);record['actions'] = actions
            with self.subTest(actions=actions):
                with self.assertRaises(ValueError):load_actions(record, self.poses, MANIFEST)
        for stage, value in (('entry', {}), ('entry', [None]), ('hold', []),
                             ('hold', None), ('recovery', 'gesture_left')):
            spec = probe_action();spec[stage] = value
            with self.subTest(stage=stage, value=value):
                with self.assertRaises(ValueError):self.clips(spec)

    def test_file_frames_are_loaded_locally_and_checked_against_actor_canvas(self):
        with tempfile.TemporaryDirectory(prefix='action-manifest-') as directory:
            folder = Path(directory)
            shutil.copyfile(MANIFEST.parent/'stand_left.png', folder/'entry.png')
            path = folder/'animation.json'
            spec = probe_action()
            spec['entry'][0] = {'file': 'entry.png', 'duration_ms': 100}
            record = deepcopy(self.record);record['actions'] = {'probe': spec}
            path.write_text(json.dumps(record))
            loaded = load_actions(json.loads(path.read_text()), self.poses, path)
            player = ActionPlayer(loaded);self.assertTrue(player.play('probe', 'file-cue'))
            self.assertEqual(pygame.image.tobytes(player.frame, 'RGBA'),
                             pygame.image.tobytes(self.poses['stand_left'], 'RGBA'))
            shutil.copyfile(ROOT/'assets/characters/iselin/native_idles/idle_front.png',
                            folder/'wrong-size.png')
            for filename in ('wrong-size.png', '../entry.png', str(MANIFEST.parent/'stand_left.png')):
                invalid = deepcopy(spec);invalid['entry'][0]['file'] = filename
                with self.subTest(file=filename):
                    with self.assertRaises(ValueError):self.clips(invalid, path=path)
            invalid = deepcopy(spec);invalid['entry'][0]['pose'] = 'stand_left'
            with self.assertRaises(ValueError):self.clips(invalid, path=path)
            (folder/'outside.png').symlink_to(MANIFEST.parent/'stand_left.png')
            invalid = deepcopy(spec);invalid['entry'][0]['file'] = 'outside.png'
            with self.assertRaises(ValueError):self.clips(invalid, path=path)


if __name__ == '__main__':unittest.main()
