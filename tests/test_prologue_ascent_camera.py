"""Actual crane geometry, entry phase and the rejected trailing-head framing."""
import json
import math
from pathlib import Path
import unittest

from cinematic_bridge_ascent import (DURATION, GATE, actor_states_at, camera_at,
                                     guard_states_at, project_world,
                                     reinforcement_states_at)
from cinematic_face_reveal import camera_at as frontal_camera
from cinematic_face_reveal import project_world as frontal_project
from cinematic_face_reveal import read_face_timing


def head_points(actor):
    """Small physical crown bounds, not an invented visible-foot annotation."""
    x, y, _ = actor['world_position_metres']
    for dx in (-.12, .12):
        for dy in (-.10, .22):
            for z in (actor['height_metres']-.22, actor['height_metres']):
                yield [x+dx, y+dy, z]


def heads_visible(camera, actors):
    for actor in actors:
        for point in head_points(actor):
            projected = project_world(point, camera)
            if projected is None or not (0 <= projected[0] < 960 and 0 <= projected[1] < 640):
                return False
    return True


class BridgeAscentCameraTests(unittest.TestCase):
    def test_entry_camera_and_actual_world_projection_match_the_frontal_endpoint(self):
        old, new = frontal_camera(5.), camera_at(0.)
        for field in ('position', 'target', 'up', 'principal_point'):
            for a, b in zip(old[field], new[field]):
                self.assertAlmostEqual(a, b, places=10)
        self.assertAlmostEqual(old['focal_pixels'], new['focal_pixels'], places=10)
        for x in (-6., 0., 6.):
            for y in (0., 40., 54.26, 100.):
                for z in (0., 1.8):
                    a, b = frontal_project([x, y, z], old), project_world([x, y, z], new)
                    if a is None:
                        self.assertIsNone(b)
                    else:
                        for first, second in zip(a, b):
                            self.assertAlmostEqual(first, second, places=8)

    def test_actual_previous_actor_timing_continues_for_ten_complete_cycles(self):
        previous = {row['id']: row for row in read_face_timing()}
        for t in (0., 1/60, .2, .4, .8, 2.2, 5.8, 8.):
            state = actor_states_at(t)
            for actor in state['runners']:
                timing = previous[actor['id']]
                expected = (5.+timing['phase_offset_seconds']+t) % timing['cycle_seconds']
                if timing['cycle_seconds']-expected < 1e-8:
                    expected = 0.
                self.assertAlmostEqual(actor['cycle_phase'], expected, places=8)
                self.assertEqual(actor['frame_index'], int(math.floor(expected*60+1e-8)))
                self.assertAlmostEqual(actor['world_position_metres'][1],
                    54.26+4*t+actor['offset_metres'], places=9)
        for first, last in zip(actor_states_at(0.)['runners'], actor_states_at(8.)['runners']):
            self.assertEqual(first['frame_index'], last['frame_index'])
            self.assertAlmostEqual(last['world_position_metres'][1]-first['world_position_metres'][1],32.)

    def test_all_native_camera_samples_have_a_continuous_nonflipping_basis(self):
        previous = None
        for index in range(481):
            camera = camera_at(index/60)
            for field in ('position', 'forward', 'right', 'up'):
                self.assertTrue(all(math.isfinite(value) for value in camera[field]))
            for axis in ('forward', 'right', 'up'):
                self.assertAlmostEqual(sum(value*value for value in camera[axis]),1., places=10)
            for a, b in (('forward','right'),('forward','up'),('right','up')):
                self.assertAlmostEqual(sum(x*y for x,y in zip(camera[a],camera[b])),0.,places=10)
            self.assertEqual(camera['right'],[-1.,0.,0.])
            if previous:
                self.assertGreater(sum(a*b for a,b in zip(previous['forward'],camera['forward'])),.995)
                self.assertGreater(sum(a*b for a,b in zip(previous['up'],camera['up'])),.995)
                self.assertGreaterEqual(camera['position'][2]+1e-8, previous['position'][2])
                self.assertGreaterEqual(camera['position'][1]+1e-8, previous['position'][1])
            previous = camera

    def test_all_three_physical_crowns_stay_inside_the_close_transition(self):
        for index in range(133):
            state = actor_states_at(index/60)
            self.assertTrue(heads_visible(state['camera'],state['runners']),f'Head clipping at {index}/60s')

    def test_retained_rejected_camera_reproduces_the_actual_crown_clipping(self):
        path = Path(__file__).parent/'fixtures/prologue_ascent_camera/rejected_1s.json'
        rejected = json.loads(path.read_text())
        actors = actor_states_at(rejected['local_time'])['runners']
        self.assertFalse(heads_visible(rejected['camera'],actors))
        crown = next(actor for actor in actors if actor['id']=='crown_soldier')
        point = project_world(crown['world_position_metres'],rejected['camera'])
        self.assertAlmostEqual(point[1],rejected['observed_crown_root_y'],places=6)
        self.assertTrue(heads_visible(camera_at(rejected['local_time']),actors))

    def test_final_world_span_fits_without_swapping_landings_or_actor_sides(self):
        camera = camera_at(DURATION)
        mainland = project_world([0.,0.,0.],camera)
        fortress = project_world([0.,299.0819285747636,0.],camera)
        self.assertTrue(0 < mainland[1] < fortress[1] < 640)
        left = project_world([.65,86.26,0.],camera)
        right = project_world([-.75,86.26,0.],camera)
        self.assertLess(left[0],480.)
        self.assertGreater(right[0],480.)

    def test_reduced_motion_preserves_the_essential_geometry_and_phase(self):
        for index in (0,12,24,48,60,96,132,240,348,480):
            self.assertEqual(camera_at(index/60,False),camera_at(index/60,True))
            normal = actor_states_at(index/60,False)
            reduced = actor_states_at(index/60,True)
            self.assertEqual(normal['runners'],reduced['runners'])

    def test_frozen_guards_keep_the_actual_shared_world_positions(self):
        path = Path(__file__).resolve().parents[1]/'assets/source/cinematics/fire_veinhold/continuation/scene_config.json'
        original = json.loads(path.read_text())
        start, end = original['bridges'][0]['start'], original['bridges'][0]['end']
        dx, dy = end[0]-start[0], end[1]-start[1]
        length = math.hypot(dx,dy)
        for t in (0.,1.,4.,8.):
            frozen = {row['id']:row for row in guard_states_at(t) if row['kind']=='frozen'}
            self.assertEqual(set(frozen),{row['id'] for row in original['guards']})
            for guard in original['guards']:
                x, y, _ = guard['position']
                expected = [((x-start[0])*dy-(y-start[1])*dx)/length,
                            ((x-start[0])*dx+(y-start[1])*dy)/length]
                actual = frozen[guard['id']]['world_position_metres']
                for a,b in zip(actual,expected):
                    self.assertAlmostEqual(a,b,places=7)

    def test_gate_clearances_happen_in_view_and_advancing_guards_have_time_to_read(self):
        first = reinforcement_states_at(0.)
        self.assertEqual(len(first),8)
        outside = [row for row in first if row['world_position_metres'][1] < GATE['near_y']]
        inside = [row for row in first if row['world_position_metres'][1] > GATE['far_y']]
        self.assertEqual((len(outside),len(inside)),(6,2))
        for actor in inside:
            # Floor-line crossing alone can leave a guard under the arch.
            # Allow at least one second outside the actual roof footprint.
            crossing = (actor['world_position_metres'][1]-GATE['near_y'])/4.
            self.assertTrue(5.5 < crossing < 7.)
            camera = camera_at(crossing)
            for height in (1.,GATE['roof_top_z']):
                point = project_world([actor['world_position_metres'][0],GATE['near_y'],height],camera)
                self.assertTrue(point and 0 < point[0] < 960 and 0 < point[1] < 640)
        camera = camera_at(4.5)
        current = {row['id']:row for row in reinforcement_states_at(4.5)}
        for actor in outside:
            point = project_world(current[actor['id']]['world_position_metres'],camera)
            self.assertTrue(point and 0 < point[0] < 960 and 0 < point[1] < 640,
                            'The first squad must enter the composition before the final hold.')
        last = reinforcement_states_at(8.)
        for a,b in zip(first,last):
            self.assertAlmostEqual(a['world_position_metres'][1]-b['world_position_metres'][1],32.)
            self.assertEqual(a['frame_index'],b['frame_index'])
        self.assertGreater(min(row['world_position_metres'][1] for row in last),86.26+50.)

    def test_retained_old_gate_stage_does_not_clear_both_roof_footprints(self):
        path = Path(__file__).parent/'fixtures/prologue_ascent_camera/rejected_gate_staging.json'
        previous = json.loads(path.read_text())
        final_y = [y-previous['speed']*DURATION for y in previous['start_y']]
        self.assertEqual(final_y,[292.,296.])
        self.assertGreater(final_y[1],GATE['near_y'])
        current = reinforcement_states_at(DURATION)[-2:]
        self.assertTrue(all(actor['world_position_metres'][1] < GATE['near_y']-1.
                            for actor in current))


if __name__ == '__main__':
    unittest.main()
