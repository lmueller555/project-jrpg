"""Actual gated operation, continuous transfers and physical water contact.

Former 31-unit teleports, eight-frame clocks and retracted hooks are historical
construction details; these checks protect the replacement's live behavior.
"""
import math

from well_live_test_support import LiveWellCase


class WellDrawing(LiveWellCase):
    def test_shared_station_geometry_is_reachable_for_both_probe_sizes(self):
        self.assertEqual(self.well.data['loading_position'], [528, 894])
        self.assertEqual(self.well.data['operator_position'], [564, 866])
        for position in ([528, 894], [564, 894], [564, 866]):
            for size in (self.actor.probe_size, self.world.probe.get_size()):
                self.assertTrue(self.world.can_stand(position, size, self.actor),
                                (position, size))

    def test_loading_obstruction_waits_without_reserving_or_filling(self):
        self.game.player.position.update(self.well.data['loading_position'])
        self.start_trip()
        self.until(lambda: self.actor.state == 'to_well' and self.actor.waiting, 40)
        before = self.actor.position.copy()
        self.game.update(2, (0, 0), False)
        self.assertEqual(self.actor.position, before)
        self.assertEqual(self.actor.water_units, 0)
        self.assertEqual(self.well.snapshot().phase_id, 'idle')
        self.assertIsNone(self.well.owner)
        self.assertFalse(self.actor.blocker.colliderect(
            self.world.probe_rect(self.game.player.position)))
        self.game.player.position.update(480, 924)
        self.to_phase('lower', 15)

    def test_operator_gate_holds_the_attached_pail_until_arrival(self):
        self.to_phase('await_operator')
        self.game.player.position.update(self.well.data['operator_position'])
        self.game.update(3, (0, 0), False)
        self.assertTrue(self.actor.waiting)
        before = self.well.snapshot()
        self.assertEqual(before.phase_id, 'await_operator')
        self.assertEqual(before.required_station, 'operator')
        self.assertEqual(before.pail_owner, 'well')
        self.assertEqual(before.water_units, 0)
        self.game.update(1, (0, 0), False)
        self.assertEqual(self.well.snapshot(), before)
        self.assertFalse(self.actor.blocker.colliderect(
            self.world.probe_rect(self.game.player.position)))
        self.game.player.position.update(480, 924)
        self.to_phase('lower', 5)
        self.assertEqual(tuple(self.actor.position), (564, 866))
        self.assertEqual(self.actor.facing, 'left')

    def test_retrieval_gate_keeps_full_pail_until_actor_can_return(self):
        self.to_phase('secure')
        self.game.player.position.update(self.well.data['loading_position'])
        self.to_phase('await_retrieval', 4)
        self.game.update(3, (0, 0), False)
        before = self.well.snapshot()
        self.assertEqual(before.phase_id, 'await_retrieval')
        self.assertEqual(before.pail_owner, 'well')
        self.assertEqual(before.water_units, 6)
        self.assertEqual(tuple(before.bucket_grip_local), (36, 74))
        self.game.update(1, (0, 0), False)
        self.assertEqual(self.well.snapshot(), before)
        self.game.player.position.update(480, 924)
        self.to_phase('detach', 5)
        self.assertEqual(tuple(self.actor.position), (528, 894))
        self.assertEqual(self.actor.facing, 'back')

    def test_handoff_cues_keep_one_owner_and_a_small_natural_snap(self):
        observed = []
        self.to_phase('attach')
        for phase, cue in (('attach', .70), ('detach', .65)):
            self.to_phase(phase)
            last = None
            while self.well.snapshot().phase_id == phase:
                state = self.well.snapshot()
                selection = self.actor.presentation_selection()
                if last is not None and last[0].pail_owner != state.pail_owner:
                    before_state, before_selection = last
                    self.assertLess(before_state.phase_progress, cue)
                    self.assertGreaterEqual(state.phase_progress, cue)
                    hook = [528, 874]
                    for chosen in (before_selection, selection):
                        hand = [self.actor.position[i]-self.actor.draw_anchor[i]+
                                chosen['hand_grip_logical'][i] for i in (0, 1)]
                        self.assertLessEqual(math.dist(hand, hook), 4)
                    observed.append((before_state.pail_owner, state.pail_owner))
                self.assertIs(bool(selection['pail_visible']), state.pail_owner == 'actor')
                last = (state, selection)
                self.game.update(1/60, (0, 0), False)
        self.assertEqual(observed, [('actor', 'well'), ('well', 'actor')])

    def test_geometric_submersion_precedes_filling_and_water_ownership(self):
        self.to_phase('lower')
        saw_contact = saw_mouth = False
        while self.well.snapshot().phase_id == 'lower':
            state = self.well.snapshot()
            saw_contact |= state.water_contact
            saw_mouth |= state.mouth_submerged
            self.assertEqual(self.actor.water_units, 0)
            self.assertEqual(state.water_units, 0)
            self.assertEqual(state.pail_owner, 'well')
            if state.mouth_submerged:
                self.assertTrue(state.water_contact)
            self.game.update(1/60, (0, 0), False)
        self.assertTrue(saw_contact and saw_mouth)
        self.assertEqual(self.well.snapshot().phase_id, 'fill')
        self.assertTrue(self.well.snapshot().mouth_submerged)
        self.game.update(.8, (0, 0), False)
        self.assertGreater(self.actor.water_units, 0)
        self.assertLess(self.actor.water_units, 6)
        self.assertEqual(self.actor.water_units, self.well.snapshot().water_units)
        self.to_phase('raise', 2)
        self.assertEqual(self.actor.water_units, 6)

    def test_stopped_fill_holds_actual_nonzero_crank_and_pose(self):
        self.to_phase('fill')
        first = self.well.snapshot()
        pose = self.actor.presentation_selection()['pose_id']
        self.assertEqual(first.crank_direction, 0)
        self.assertNotEqual(first.crank_sample, 0)
        for _ in range(30):
            self.game.update(1/60, (0, 0), False)
            state = self.well.snapshot()
            self.assertEqual(state.crank_sample, first.crank_sample)
            self.assertEqual(state.crank_phase, first.crank_phase)
            self.assertEqual(self.actor.presentation_selection()['pose_id'], pose)

    def test_raise_reverses_real_crank_and_releases_full_pail_after_detach(self):
        self.to_phase('lower')
        self.assertEqual(self.well.snapshot().crank_direction, 1)
        self.to_phase('raise', 8)
        first = self.well.snapshot()
        self.assertEqual(first.crank_direction, -1)
        self.game.update(.3, (0, 0), False)
        second = self.well.snapshot()
        self.assertLess(second.crank_turns, first.crank_turns)
        self.assertLess(second.bucket_grip_local[1], first.bucket_grip_local[1])
        self.until(lambda: self.actor.state == 'return_to_sanctuary', 12)
        self.assertEqual(self.actor.water_units, 6)
        self.assertEqual(self.actor.pail_location, 'actor')
        self.assertTrue(self.actor.presentation_selection()['pail_visible'])
        self.assertIsNone(self.well.owner)


if __name__ == '__main__':
    import unittest
    unittest.main()
