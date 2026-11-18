"""Behavioral checks for the staged well's independent operation controller."""
from dataclasses import FrozenInstanceError, asdict, is_dataclass
import math
from pathlib import Path
import json
import unittest

from PIL import Image

from well_mechanism import WellMechanism


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'assets/source/terrain/eldenmere/well_hd/mechanism/contract.json'
GATES = {'await_loading': 'loading', 'await_operator': 'operator',
         'await_retrieval': 'loading'}


def state(model):
    return model.snapshot()


def advance_to(model, phase, step=1/120, limit=30000):
    for _ in range(limit):
        if state(model).phase_id == phase:
            return state(model)
        model.update(step)
    raise AssertionError(f'Operation did not reach {phase}: {state(model)}')


def begin():
    model = WellMechanism()
    token = model.reserve('gardener', 'garden_pail')
    if token is None:
        raise AssertionError('An idle well rejected its first reservation')
    return model, token


def at_operator():
    model, token = begin()
    if not model.signal_ready(token, 'loading'):
        raise AssertionError('Loading readiness was rejected')
    advance_to(model, 'await_operator')
    return model, token


class WellMechanismTests(unittest.TestCase):
    def assertTreeAlmostEqual(self, first, second):
        if isinstance(first, dict):
            self.assertEqual(set(first), set(second))
            for key in first:
                self.assertTreeAlmostEqual(first[key], second[key])
        elif isinstance(first, (tuple, list)):
            self.assertEqual(len(first), len(second))
            for left, right in zip(first, second):
                self.assertTreeAlmostEqual(left, right)
        elif isinstance(first, float):
            self.assertAlmostEqual(first, second, places=8)
        else:
            self.assertEqual(first, second)

    def test_idle_and_readiness_holds_do_not_run_invisible_actions(self):
        model, token = begin()
        held = state(model)
        self.assertEqual(held.phase_id, 'await_loading')
        model.drain_events()
        model.update(900)
        self.assertEqual(state(model), held)
        self.assertEqual(model.drain_events(), ())
        self.assertFalse(model.signal_ready(token, 'operator'))
        self.assertEqual(state(model), held)
        self.assertTrue(model.signal_ready(token, 'loading'))
        parked = advance_to(model, 'await_operator')
        model.drain_events()
        model.update(900)
        self.assertEqual(state(model), parked)
        self.assertEqual(model.drain_events(), ())

    def test_calibrated_stations_are_clear_for_actual_player_and_gardener_probes(self):
        contract = json.loads(CONTRACT.read_text())
        town = json.loads((ROOT/'assets/maps/eldenmere/playable/map.json').read_text())
        with Image.open(ROOT/town['collision']) as source:
            collision = source.convert('L')
        for name, station in contract['stations'].items():
            for width, height in ((24, 12), (12, 8)):
                with self.subTest(station=name, probe=(width, height)):
                    x, y = station['feet_world_logical']
                    left, top = round(x)-width//2, round(y)-height//2
                    box = (left, top, left+width, top+height)
                    self.assertGreaterEqual(left, 0)
                    self.assertGreaterEqual(top, 0)
                    self.assertLessEqual(box[2], collision.width)
                    self.assertLessEqual(box[3], collision.height)
                    self.assertIsNone(collision.crop(box).getbbox())
    def test_busy_reservation_and_stale_operation_tokens_cannot_take_control(self):
        model, first = begin()
        self.assertIsNone(model.reserve('another_worker', 'another_pail'))
        self.assertIsNone(model.reserve('gardener', 'garden_pail'))
        model.abort(first)
        second = model.reserve('gardener', 'garden_pail')
        self.assertIsNotNone(second)
        self.assertNotEqual(first, second)
        before = state(model)
        self.assertFalse(model.signal_ready(first, 'loading'))
        self.assertIsNone(model.abort(first))
        self.assertEqual(state(model), before)

    def test_invalid_time_is_rejected_without_partial_state_or_events(self):
        model, token = begin()
        model.signal_ready(token, 'loading')
        model.update(.2)
        model.drain_events()
        before = state(model)
        for value in (-.001, math.inf, -math.inf, math.nan):
            with self.subTest(seconds=value):
                with self.assertRaises((ValueError, TypeError)):
                    model.update(value)
                self.assertEqual(state(model), before)
                self.assertEqual(model.drain_events(), ())

    def test_snapshots_and_operation_tokens_are_frozen_value_records(self):
        model, token = begin()
        snapshot = state(model)
        self.assertTrue(is_dataclass(snapshot))
        self.assertTrue(is_dataclass(token))
        with self.assertRaises(FrozenInstanceError):
            snapshot.phase_id = 'complete'
        with self.assertRaises(FrozenInstanceError):
            token.operation_id = 'stolen'
        self.assertIsInstance(snapshot.bucket_grip_local, tuple)
        self.assertIsInstance(snapshot.rope_origin_local, tuple)
        self.assertIsInstance(snapshot.rope_end_local, tuple)
        self.assertEqual(state(model), snapshot)

    def test_large_updates_and_small_updates_reach_the_same_gated_states(self):
        coarse, ct = begin(); fine, ft = begin()
        for station, target in (('loading', 'await_operator'),
                                ('operator', 'await_retrieval'),
                                ('loading', 'complete')):
            self.assertTrue(coarse.signal_ready(ct, station))
            self.assertTrue(fine.signal_ready(ft, station))
            coarse.update(1000)
            advance_to(fine, target)
            self.assertEqual(state(coarse).phase_id, target)
            self.assertTreeAlmostEqual(asdict(state(coarse)), asdict(state(fine)))
            self.assertTreeAlmostEqual([asdict(event) for event in coarse.drain_events()],
                                       [asdict(event) for event in fine.drain_events()])

    def test_observation_and_zero_time_do_not_mutate_the_operation(self):
        model, token = begin()
        model.signal_ready(token, 'loading')
        model.update(.3)
        model.drain_events()
        before = state(model)
        for _ in range(20):
            self.assertEqual(model.snapshot(), before)
            model.update(0)
        self.assertEqual(state(model), before)
        self.assertEqual(model.drain_events(), ())

    def test_hook_rope_and_bucket_stay_registered_through_the_whole_operation(self):
        model, token = begin()
        contract = json.loads(CONTRACT.read_text())
        rope_offset = contract['geometry']['hook_rope_offset_logical']
        previous = None
        seen = set()
        for _ in range(10000):
            snapshot = state(model)
            seen.add(snapshot.phase_id)
            if snapshot.phase_id in GATES:
                model.signal_ready(token, GATES[snapshot.phase_id])
                snapshot = state(model)
            self.assertTrue(all(math.isfinite(value)
                                for value in snapshot.bucket_grip_local))
            self.assertGreaterEqual(snapshot.water_units, 0)
            self.assertLessEqual(snapshot.water_units, 6)
            if snapshot.rope_deployed:
                self.assertEqual(snapshot.rope_end_local,
                                 tuple(snapshot.bucket_grip_local[i]+rope_offset[i]
                                       for i in (0, 1)))
                self.assertAlmostEqual(snapshot.rope_length,
                                       math.dist(snapshot.rope_origin_local,
                                                 snapshot.rope_end_local), places=8)
            if previous is not None:
                # 1/120s sampling must not contain the old character-height
                # handoff jump. A modest bound permits intended eased travel.
                self.assertLess(math.dist(previous.bucket_grip_local,
                                          snapshot.bucket_grip_local), 1)
            if snapshot.phase_id == 'complete':
                break
            previous = snapshot
            model.update(1/120)
        else:
            self.fail('A ready operator could not complete the mechanism')
        self.assertTrue({'attach', 'guide_into_shaft', 'lower', 'fill', 'raise',
                         'secure', 'detach', 'complete'} <= seen)

    def test_filling_requires_physical_contact_and_completes_before_retrieval(self):
        model, token = at_operator()
        model.signal_ready(token, 'operator')
        contact_seen = False
        for _ in range(10000):
            snapshot = state(model)
            if snapshot.phase_id == 'fill':
                self.assertTrue(snapshot.water_contact)
                self.assertTrue(snapshot.mouth_submerged)
                contact_seen = True
            if snapshot.phase_id == 'await_retrieval':
                self.assertEqual(snapshot.water_units, 6)
                break
            if snapshot.phase_id in ('engage', 'guide_into_shaft', 'lower'):
                self.assertEqual(snapshot.water_units, 0)
            model.update(1/120)
        else:
            self.fail('Drawing water did not reach retrieval')
        self.assertTrue(contact_seen)

    def test_reset_invalidates_the_old_operator_and_restores_a_clean_start(self):
        model, token = at_operator()
        model.signal_ready(token, 'operator')
        advance_to(model, 'lower')
        model.update(.4)
        model.reset()
        self.assertFalse(model.signal_ready(token, 'loading'))
        self.assertIsNone(model.abort(token))
        fresh = model.reserve('gardener', 'garden_pail')
        self.assertIsNotNone(fresh)
        self.assertNotEqual(fresh, token)
        self.assertEqual(state(model).phase_id, 'await_loading')
        self.assertEqual(state(model).water_units, 0)

    def test_tokens_from_another_controller_cannot_impersonate_its_operator(self):
        first, token = begin()
        second, other = begin()
        held = state(second)
        self.assertFalse(second.signal_ready(token, 'loading'))
        self.assertIsNone(second.abort(token))
        self.assertEqual(state(second), held)
        self.assertTrue(second.signal_ready(other, 'loading'))
        self.assertEqual(state(first).phase_id, 'await_loading')

    def test_physical_contact_events_cross_the_declared_water_plane(self):
        contract = json.loads(CONTRACT.read_text())
        water_y = contract['geometry']['water_plane_local'][1]
        base_offset = contract['pail']['base_offset_from_grip'][1]
        mouth_offset = contract['pail']['mouth_offset_from_grip'][1]
        model, token = at_operator()
        model.drain_events()
        model.signal_ready(token, 'operator')
        model.update(1000)
        events = {event.cue_id: event for event in model.drain_events()}
        self.assertIn('water_contact', events)
        self.assertIn('mouth_submerged', events)
        self.assertIn('water_exit', events)
        self.assertAlmostEqual(events['water_contact'].bucket_grip_local[1]+base_offset,
                               water_y, places=8)
        self.assertAlmostEqual(events['mouth_submerged'].bucket_grip_local[1]+mouth_offset,
                               water_y, places=8)
        self.assertAlmostEqual(events['water_exit'].bucket_grip_local[1]+base_offset,
                               water_y, places=8)
        self.assertLess(events['water_contact'].operation_elapsed_ms,
                        events['mouth_submerged'].operation_elapsed_ms)
        self.assertLess(events['mouth_submerged'].operation_elapsed_ms,
                        events['fill_complete'].operation_elapsed_ms)
        self.assertLess(events['fill_complete'].operation_elapsed_ms,
                        events['water_exit'].operation_elapsed_ms)

    def test_transfer_events_are_once_only_frozen_and_have_unique_operation_ids(self):
        model, token = begin()
        gathered = []
        for station in ('loading', 'operator', 'loading'):
            self.assertTrue(model.signal_ready(token, station))
            model.update(1000)
            gathered.extend(model.drain_events())
            self.assertEqual(model.drain_events(), ())
        names = [event.cue_id for event in gathered]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue({'attached', 'water_contact', 'mouth_submerged',
                         'fill_complete', 'water_exit', 'detached', 'completed'} <= set(names))
        self.assertEqual(len({event.event_id for event in gathered}), len(gathered))
        by_name = {event.cue_id: event for event in gathered}
        self.assertEqual(by_name['attached'].pail_owner, 'well')
        self.assertEqual(by_name['attached'].water_units, 0)
        self.assertEqual(by_name['fill_complete'].pail_owner, 'well')
        self.assertEqual(by_name['fill_complete'].water_units, 6)
        self.assertEqual(by_name['detached'].pail_owner, 'actor')
        self.assertEqual(by_name['detached'].water_units, 6)
        for event in gathered:
            with self.assertRaises(FrozenInstanceError):
                event.water_units = 100
        model.update(1000)
        self.assertEqual(model.drain_events(), ())
        next_token = model.reserve('gardener', 'garden_pail')
        self.assertIsNotNone(next_token)
        self.assertNotEqual(next_token.operation_id, token.operation_id)

    def test_abort_returns_the_real_full_pail_without_a_synthetic_transfer(self):
        model, token = at_operator()
        model.signal_ready(token, 'operator')
        advance_to(model, 'await_retrieval')
        before = state(model)
        self.assertEqual(before.water_units, 6)
        model.drain_events()
        recovery = model.abort(token)
        self.assertIsNotNone(recovery)
        self.assertEqual(recovery.pail_id, before.pail_id)
        self.assertEqual(recovery.pail_owner, before.pail_owner)
        self.assertEqual(recovery.water_units, before.water_units)
        self.assertEqual(recovery.bucket_grip_local, before.bucket_grip_local)
        self.assertEqual(recovery.bucket_region, before.bucket_region)
        self.assertEqual([event.cue_id for event in model.drain_events()], ['cancelled'])
        self.assertIsNone(model.abort(token))
        self.assertEqual(model.drain_events(), ())
        self.assertIsNone(model.reserve('another_worker', 'another_pail'))
        retained = model.reset()
        self.assertEqual(retained.pail_id, recovery.pail_id)
        self.assertEqual(retained.water_units, recovery.water_units)
        self.assertEqual(retained.recovery_id, recovery.recovery_id)
        self.assertIsNotNone(model.reserve('another_worker', 'another_pail'))

    def test_filling_holds_the_actual_stopped_crank_angle(self):
        contract = json.loads(CONTRACT.read_text())
        geometry = contract['geometry']
        expected = (geometry['lowered_grip_local'][1]-geometry['loading_grip_local'][1]) / geometry['rope_units_per_crank_turn']
        model, token = at_operator()
        model.signal_ready(token, 'operator')
        entering = advance_to(model, 'fill')
        self.assertAlmostEqual(entering.crank_turns, expected, places=10)
        self.assertAlmostEqual(entering.crank_phase, expected % 1, places=10)
        self.assertEqual(entering.crank_direction, 0)
        model.update(contract['phase_durations_ms']['fill']/2000)
        holding = state(model)
        self.assertEqual(holding.phase_id, 'fill')
        self.assertEqual(holding.crank_turns, entering.crank_turns)
        self.assertEqual(holding.crank_phase, entering.crank_phase)
        self.assertEqual(holding.crank_sample, entering.crank_sample)

    def test_contract_copies_cannot_retime_an_existing_operation(self):
        contract = json.loads(CONTRACT.read_text())
        model = WellMechanism(contract)
        token = model.reserve('gardener', 'garden_pail')
        contract['phase_durations_ms']['attach'] = 1
        exported = model.contract
        exported['phase_durations_ms']['attach'] = 1
        model.signal_ready(token, 'loading')
        model.update(.1)
        self.assertEqual(state(model).phase_id, 'attach')
        self.assertLess(state(model).phase_progress, 1)

    def test_reset_does_not_redeliver_a_completed_actor_owned_pail(self):
        model, token = begin()
        for station in ('loading', 'operator', 'loading'):
            model.signal_ready(token, station)
            model.update(1000)
        self.assertEqual(state(model).phase_id, 'complete')
        self.assertEqual(state(model).pail_owner, 'actor')
        self.assertIsNone(model.reset())
        self.assertIsNone(model.reset())
        self.assertEqual(state(model).phase_id, 'idle')
        self.assertEqual(state(model).water_units, 0)


if __name__ == '__main__':
    unittest.main()
