"""Object transfers remain coherent through live scene input and restoration.

These checks cover ownership and cue boundaries. Natural anatomy and camera
readability still require inspection of the actual scene frames.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import pygame

import test_sanctuary_arrival_state as state_tests
from sanctuary_care import SanctuaryCare


class SanctuaryArrivalObjectTests(unittest.TestCase):
    def setUp(self):
        self.driver = state_tests.SanctuaryArrivalStateTests()
        self.driver.setUp()
        self.addCleanup(self.driver.doCleanups)
        self.game = self.driver.g
        self.owner = self.game.sanctuary_arrival

    def wait(self, predicate, *, advance=False, step=.05):
        for _ in range(6000):
            if predicate():return
            if advance and self.owner.dialogue is not None:self.driver.press()
            self.driver.tick(step)
        self.fail(('Interaction did not finish', self.owner.beat,
                   self.owner.actors.get('mira').pose, self.owner.error))

    def prop(self, name):
        return [record for _, record in self.owner._care_props
                if record['id'] == name]

    def assert_kit_representation(self):
        self.assertEqual(len(self.prop('arrival_kit')),
                         int(self.owner.care.kit_owner == 'world'))

    def test_kit_and_cloth_transfer_once_after_the_authored_actions(self):
        owner = self.owner
        self.wait(lambda: owner.active and owner.care.action == 'place')
        self.assertEqual(owner.care.kit_owner, 'mira')
        self.assert_kit_representation()
        observed_world_kit = False
        deposit = owner.performance['poses']['place']['cue_ms']['kit_deposit']
        for _ in range(200):
            if owner.care.action != 'place':break
            self.assert_kit_representation()
            self.assertEqual(owner.care.kit_owner,
                             'world' if owner.care.elapsed_ms >= deposit else 'mira')
            self.assertFalse(owner.actors['mira'].moving)
            observed_world_kit |= owner.care.kit_owner == 'world'
            self.driver.tick(.025)
        else:self.fail('Kit placement did not finish')
        self.assertTrue(observed_world_kit)
        self.assertEqual(owner.care.kit_owner, 'world')
        kit_position = tuple(self.prop('arrival_kit')[0]['position'])

        self.wait(lambda: owner.care.action == 'take_cloth')
        self.assertEqual(owner.care.cloth_owner, 'linen')
        self.wait(lambda: owner.care.cloth_owner == 'mira')
        self.assertEqual(tuple(self.prop('arrival_kit')[0]['position']), kit_position)
        self.wait(lambda: owner.care.action == 'treat', advance=True)
        self.assertEqual(owner.care.cloth_owner, 'mira')
        self.wait(lambda: owner.care.cloth_owner == 'worker')
        self.wait(lambda: not owner.care.busy)
        self.assertEqual(owner.actors['worker_a'].pose, 'arm_rest')
        self.assertEqual(tuple(self.prop('arrival_kit')[0]['position']), kit_position)

        self.wait(lambda: owner.beat == 4 and owner.dialogue is not None, advance=True)
        self.driver.press()
        self.assertEqual(owner.care.action, 'retrieve')
        self.assertEqual(owner.care.kit_owner, 'world')
        states = []
        pickup = owner.performance['poses']['retrieve']['cue_ms']['kit_pickup']
        stow = owner.performance['poses']['retrieve']['cue_ms']['kit_stow']
        for _ in range(200):
            if not owner.care.busy:break
            self.assert_kit_representation()
            expected = ('stowed' if owner.care.elapsed_ms >= stow else
                        'mira' if owner.care.elapsed_ms >= pickup else 'world')
            self.assertEqual(owner.care.kit_owner, expected)
            self.assertFalse(owner.actors['mira'].moving)
            states.append(owner.care.kit_owner)
            self.driver.press()  # Fast confirmations cannot skip the action.
            self.driver.tick(.025)
        else:self.fail('Kit retrieval did not finish')
        self.assertIn('mira', states)
        self.assertEqual(owner.care.kit_owner, 'stowed')
        self.assert_kit_representation()
        self.wait(lambda: owner.actors['mira'].moving)
        self.assertFalse(self.prop('arrival_kit'))

    def test_runner_releases_one_fixed_bundle_and_does_not_restart(self):
        owner = self.owner
        self.wait(lambda: owner.active and owner.actors['runner'].moving)
        self.assertFalse(owner._runner_delivered)
        self.assertFalse(self.prop('arrival_linen_runner'))
        self.wait(lambda: owner.actors['runner'].pose == 'runner_place')
        self.assertFalse(owner._runner_delivered)
        for _ in range(200):
            if owner.care.runner_linen_placed:break
            self.assertFalse(self.prop('arrival_linen_runner'))
            self.driver.tick(.025)
        else:self.fail('Linen placement did not finish')
        self.assertEqual(len(self.prop('arrival_linen_runner')), 1)
        self.wait(lambda: owner._runner_delivered)
        position = tuple(self.prop('arrival_linen_runner')[0]['position'])
        runner_position = tuple(owner.actors['runner'].position)
        for _ in range(40):
            self.driver.tick(.25)
            self.assertEqual(len(self.prop('arrival_linen_runner')), 1)
            self.assertEqual(tuple(self.prop('arrival_linen_runner')[0]['position']), position)
            self.assertEqual(tuple(owner.actors['runner'].position), runner_position)
            self.assertFalse(owner.actors['runner'].moving)

    def test_pause_and_focus_freeze_care_ownership_pose_and_transfer_clock(self):
        owner = self.owner
        self.wait(lambda: owner.active and owner.care.action == 'place')

        def state():
            return (owner.care.action, owner.care.elapsed_ms,
                    owner.care.kit_owner, owner.care.cloth_owner,
                    owner.actors['mira'].pose_ms,
                    tuple((r['id'], tuple(r['position'])) for _, r in owner._care_props))

        self.game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False),
                                 pygame.event.Event(pygame.KEYUP, key=pygame.K_ESCAPE)])
        self.assertTrue(owner.paused)
        before = state()
        self.driver.tick(2)
        self.assertEqual(state(), before)
        self.game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False),
                                 pygame.event.Event(pygame.KEYUP, key=pygame.K_ESCAPE)])
        self.game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        before = state()
        self.driver.tick(2)
        self.assertEqual(state(), before)
        self.game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.wait(lambda: owner.care.kit_owner == 'world')
        self.assert_kit_representation()

    def test_continue_during_retrieval_rebuilds_the_unacknowledged_care_beat(self):
        owner = self.owner
        self.wait(lambda: owner.beat == 4 and owner.dialogue is not None, advance=True)
        self.driver.press()
        self.wait(lambda: owner.care.kit_owner == 'mira')
        self.assertTrue(self.game.save_progress())
        restored = self.driver.game()
        self.assertTrue(restored.begin_journey(True), restored.save_error)
        self.driver.g = self.game = restored
        restored.opening_fade = restored.transfer_cooldown = 0
        self.driver.tick()
        self.owner = owner = restored.sanctuary_arrival
        self.assertEqual(owner.beat, 4)
        self.assertEqual(owner.dialogue_index, 0)
        self.assertEqual(owner.care.kit_owner, 'world')
        self.assertEqual(owner.care.cloth_owner, 'worker')
        self.assert_kit_representation()
        self.wait(lambda: owner.completed, advance=True)
        self.assertEqual(owner.care.kit_owner, 'stowed')
        self.assertFalse(self.prop('arrival_kit'))
        self.assertEqual(len(self.prop('arrival_linen_runner')), 1)

    def test_page_acknowledges_the_group_then_returns_to_his_ledger(self):
        owner = self.owner
        self.wait(lambda: owner.dialogue is not None
                  and owner.dialogue['id'] == 'royal_handoff.1', advance=True)
        page = owner.actors['page']
        self.driver.tick(.05)
        self.assertEqual(page.pose, 'read_attention')
        self.driver.press()
        self.wait(lambda: page.pose == 'read_resume')
        self.assertEqual(owner.beat, 5)
        for _ in range(3):self.driver.press()
        self.wait(lambda: owner.beat == 6)
        self.assertEqual(page.pose, 'read')
        self.assertFalse(page.moving)

    def test_a_large_update_crosses_each_transfer_cue_only_once(self):
        scene = SimpleNamespace(
            actors={'mira': SimpleNamespace(pose=None, pose_ms=0, moving=False),
                    'worker_a': SimpleNamespace(pose=None, pose_ms=0),
                    'runner': SimpleNamespace()},
            blocking=SimpleNamespace(busy=lambda key: True),
            _care_finished=Mock(), _play_care_sound=Mock())
        care = SanctuaryCare(scene, self.owner.performance)
        care.start('setup', ['place', 'take_cloth'])
        duration = sum(frame['duration_ms']
                       for action in ('place', 'take_cloth')
                       for frame in self.owner.performance['poses'][action]['frames'])
        care.update(duration/1000 + .5)
        self.assertFalse(care.busy)
        self.assertEqual(care.kit_owner, 'world')
        self.assertEqual(care.cloth_owner, 'mira')
        scene._care_finished.assert_called_once_with('setup')
        self.assertEqual(scene._play_care_sound.call_count, 2)
        care.update(5)
        self.assertEqual(scene._play_care_sound.call_count, 2)
        scene._care_finished.assert_called_once_with('setup')


if __name__ == '__main__':unittest.main()
