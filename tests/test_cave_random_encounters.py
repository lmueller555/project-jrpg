"""Authored cave pools, honest walking distance and durable random handoffs."""
from collections import Counter
from copy import deepcopy
import math
import unittest

from cave_random_encounters import (CaveRandomEncounters, CONFIG_PATH, SAVE_KEY,
                                    load_encounters, valid_ticket)


OUTER = [456,1280]
MIDDLE = [1100,1200]
DEEP = [1680,970]


class CaveEncounterCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.owner = CaveRandomEncounters(seed=90210)
        cls.config = deepcopy(cls.owner.data)

    def fresh(self, seed=90210):
        return CaveRandomEncounters(seed=seed)

    def force_remaining(self, owner, distance):
        state = owner.to_dict()
        state['remaining'] = distance
        self.assertTrue(owner.restore(state))

    def test_approved_roster_weights_levels_and_distance_range(self):
        c = self.owner
        self.assertEqual((c.minimum_distance,c.mode_distance,c.maximum_distance,c.safe_exit_distance),
                         (384,624,864,96))
        self.assertEqual(len(c.data['formations']),14)
        sizes = {}
        for name, area in c.data['areas'].items():
            self.assertEqual(sum(area['weights'].values()),100)
            counts = Counter()
            for formation,weight in area['weights'].items():
                members = c.data['formations'][formation]
                self.assertLessEqual(len(members),4)
                self.assertLessEqual(members.count('lithrusk'),1)
                self.assertLessEqual(members.count('veylume'),1)
                counts[len(members)] += weight
            sizes[name] = dict(counts)
        self.assertEqual(sizes, {'outer':{1:55,2:45,3:0,4:0},
                                 'middle':{1:40,2:50,3:10,4:0},
                                 'deep':{1:35,2:45,3:15,4:5}})
        self.assertEqual(c.data['areas']['outer']['levels'],{'cave_bat':[2,2],'lithrusk':[2,2]})
        self.assertEqual(c.data['areas']['middle']['levels']['veylume'],[3,3])
        self.assertEqual(c.data['areas']['deep']['levels']['veylume'],[3,4])

    def test_actual_room_polygons_and_corridors_choose_local_pool_and_safe_places(self):
        c = self.owner
        expected = {tuple(OUTER):('outer','cave_outer'),tuple(MIDDLE):('middle','cave_hollow'),
                    tuple(DEEP):('deep','cave_depths'),(270,780):('middle','cave_grotto'),
                    (1660,1420):('deep','cave_depths'),(1260,1580):('middle','cave_hollow')}
        for position, pair in expected.items():
            with self.subTest(position=position):
                r = c.region_at(position)
                self.assertEqual((r['area'],r['battlefield']),pair)
        for position in ((288,1660),(288,1740),(1220,970),(1810,600),(2060,300),(1220,1050)):
            with self.subTest(safe=position):
                self.assertIsNone(c.region_at(position)['area'])
        self.assertIsNone(c.region_at((0,0)))
        self.assertIsNone(c.region_at((-1,500)))
        self.assertIsNone(c.region_at((2401,500)))
        # This connector lies outside both named rooms: its authored tube owns
        # the region, rather than a nearest-room guess across solid rock.
        self.assertEqual(c.region_at((780,1255))['area'],'middle')

    def test_counter_pauses_for_safe_places_zero_motion_ineligible_and_other_scenes(self):
        c = self.fresh()
        initial = c.to_dict()
        for point in (OUTER, MIDDLE, DEEP):
            self.assertIsNone(c.advance(0,point))
            self.assertIsNone(c.advance(1000,point,eligible=False))
            self.assertIsNone(c.travel(point,[point[0]+100,point[1]],scene_id='eldenmere.playable'))
        self.assertEqual(c.to_dict(),initial)
        self.assertIsNone(c.advance(10000,[1810,600]))
        after = c.to_dict()
        self.assertEqual(after['remaining'],initial['remaining'])
        self.assertEqual(after['rng_state'],initial['rng_state'])
        self.assertTrue(after['was_safe'])
        self.assertIsNone(c.advance(100,OUTER))
        self.assertAlmostEqual(c.remaining_distance,initial['remaining']-100)

    def test_room_changes_share_one_countdown_and_safe_exit_only_adds_small_floor(self):
        c = self.fresh()
        before = c.to_dict()
        for point in (OUTER,MIDDLE,DEEP):self.assertIsNone(c.advance(100,point))
        self.assertAlmostEqual(c.remaining_distance,before['remaining']-300)
        self.assertEqual(c.to_dict()['rng_state'],before['rng_state'])
        self.force_remaining(c,10)
        c.advance(300,[1810,600])
        self.assertEqual(c.remaining_distance,10)
        c.advance(20,DEEP)
        self.assertEqual(c.remaining_distance,76)
        self.assertEqual(c.to_dict()['rng_state'],before['rng_state'])

    def test_long_and_short_frames_trigger_at_the_same_travelled_position(self):
        start,end = [456,1280],[680,1270]
        large,small = self.fresh(),self.fresh()
        self.force_remaining(large,101.25)
        self.force_remaining(small,101.25)
        a = large.travel(start,end)
        previous = start
        b = None
        for index in range(1,1201):
            current = [start[axis]+(end[axis]-start[axis])*index/1200 for axis in (0,1)]
            b = small.travel(previous,current)
            if b:break
            previous = current
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertAlmostEqual(math.dist(start,a['position']),101.25)
        for axis in (0,1):self.assertAlmostEqual(a['position'][axis],b['position'][axis],places=8)
        for key in a.keys()-{'position'}:self.assertEqual(a[key],b[key])
        self.assertTrue(valid_ticket(a))
        self.assertTrue(valid_ticket(b))

    def test_safe_boundary_travel_counts_exactly_only_unprotected_ground(self):
        # The apron ends at y1608. Both a long frame and 150 one-pixel frames
        # spend 98 eligible pixels from1660 to1510; no doorway grace is rerolled.
        large,small = self.fresh(),self.fresh()
        initial = large.remaining_distance
        large.travel([288,1660],[288,1510])
        for y in range(1660,1510,-1):small.travel([288,y],[288,y-1])
        self.assertAlmostEqual(large.remaining_distance,initial-98)
        self.assertAlmostEqual(small.remaining_distance,large.remaining_distance)
        self.assertEqual(small.to_dict()['rng_state'],large.to_dict()['rng_state'])

    def test_exact_threshold_on_closed_safe_edge_produces_a_valid_durable_ticket(self):
        for half_span in (.5,.00001):
            with self.subTest(half_span=half_span):
                c = self.fresh()
                self.force_remaining(c,half_span)
                ticket = c.travel([288,1608-half_span],[288,1608+half_span])
                self.assertIsNotNone(ticket)
                self.assertLess(ticket['position'][1],1608)
                self.assertLess(1608-ticket['position'][1],.001)
                self.assertTrue(c.valid_ticket(ticket))
                self.assertTrue(c.valid_snapshot(c.to_dict()))

    def test_distances_are_bounded_middle_weighted_and_roster_draws_match_weights(self):
        c = self.fresh(seed=35672)
        thresholds = []
        counts = Counter()
        for _ in range(4000):
            thresholds.append(c.remaining_distance)
            ticket = c.advance(1000,DEEP)
            counts[ticket['formation']] += 1
            self.assertTrue(c.finish(ticket['receipt']))
        self.assertTrue(all(384 <= value <= 864 for value in thresholds))
        self.assertAlmostEqual(sum(thresholds)/len(thresholds),624,delta=7)
        middle = sum(576 <= value < 672 for value in thresholds)
        tails = sum(384 <= value < 480 or 768 <= value <= 864 for value in thresholds)
        self.assertGreater(middle,tails)
        for formation,weight in self.config['areas']['deep']['weights'].items():
            with self.subTest(formation=formation):
                self.assertAlmostEqual(counts[formation]/40,weight,delta=2)
        for _ in range(100):
            ticket = c.advance(1000,OUTER)
            self.assertLessEqual(len(ticket['members']),2)
            self.assertTrue(all(member['enemy_id'] != 'veylume' and member['level'] == 2
                                for member in ticket['members']))
            c.finish()

    def test_pending_handoff_reload_and_finish_are_detached_deterministic_and_idempotent(self):
        c = self.fresh()
        ticket = c.advance(1000,DEEP)
        snapshot = c.to_dict()
        resumed = self.fresh(seed=1)
        self.assertTrue(resumed.restore(snapshot))
        self.assertEqual(resumed.pending,ticket)
        self.assertEqual(resumed.travel(DEEP,[1681,970]),ticket)
        self.assertEqual(resumed.to_dict(),snapshot)
        ticket['members'].clear()
        self.assertTrue(resumed.pending['members'])
        self.assertFalse(resumed.finish('cave:wrong'))
        self.assertEqual(resumed.to_dict(),snapshot)
        self.assertTrue(resumed.finish(snapshot['pending']['receipt']))
        self.assertTrue(c.finish())
        self.assertEqual(resumed.to_dict(),c.to_dict())
        fresh = resumed.to_dict()
        self.assertFalse(resumed.finish())
        self.assertEqual(resumed.to_dict(),fresh)
        self.assertIsNone(resumed.pending)
        self.assertTrue(384 <= resumed.remaining_distance <= 864)

    def test_invalid_snapshots_and_tickets_never_mutate_a_valid_controller(self):
        c = self.fresh()
        c.advance(1000,DEEP)
        valid = c.to_dict()
        invalid = []
        for field,value in (('version',True),('identity',-1),('rng_state',2**32),('sequence',False),
                            ('threshold',383),('threshold',865),('threshold',float('nan')),
                            ('remaining',1),('was_safe',1)):
            state = deepcopy(valid);state[field] = value;invalid.append(state)
        for field,value in (('area',{}),('formation',[]),('battlefield',None),('position',[0,0]),
                            ('combat_seed',False),('receipt','cave:00000000:1'),('location','through_wall')):
            state = deepcopy(valid);state['pending'][field] = value;invalid.append(state)
        state = deepcopy(valid);state['pending']['members'][0]['level'] = 100;invalid.append(state)
        state = deepcopy(valid);state['extra'] = 1;invalid.append(state)
        for state in invalid:
            with self.subTest(state=state):
                self.assertFalse(c.restore(state))
                self.assertFalse(CaveRandomEncounters.valid_snapshot(state))
                self.assertEqual(c.to_dict(),valid)
        for ticket in (None,[],{},True):self.assertFalse(valid_ticket(ticket))
        for field in ('area','formation','battlefield','location'):
            for value in ([],{},True,None):
                bad = deepcopy(valid['pending']);bad[field] = value
                with self.subTest(ticket_field=field,value=value):
                    self.assertFalse(c.valid_ticket(bad))
                    self.assertFalse(valid_ticket(bad))
        for args in ((True,DEEP),(-1,DEEP),(float('inf'),DEEP),(1,[True,2])):
            with self.subTest(args=args),self.assertRaises(ValueError):c.advance(*args)

    def test_old_journeys_are_accepted_and_pending_journey_requires_exact_origin(self):
        self.assertTrue(CaveRandomEncounters.valid_journey({'player':{'scene':'sanctuary_cave'}}))
        c = self.fresh();ticket = c.advance(1000,DEEP)
        data = {SAVE_KEY:c.to_dict(),'player':{'scene':'sanctuary_cave','position':ticket['position']}}
        self.assertTrue(CaveRandomEncounters.valid_journey(data))
        for field,value in (('scene','eldenmere.playable'),('position',[1681,970])):
            bad = deepcopy(data);bad['player'][field] = value
            self.assertFalse(CaveRandomEncounters.valid_journey(bad))

    def test_invalid_roster_authoring_is_rejected_and_loading_detaches_config(self):
        for change in ('weight_total','negative_weight','five_enemies','two_casters','outside_level',
                       'missing_room','route_gap','overlapping_band','safe_exit'):
            data = deepcopy(self.config)
            if change == 'weight_total':data['areas']['outer']['weights']['bat'] += 1
            elif change == 'negative_weight':data['areas']['outer']['weights']['bat'] = -1
            elif change == 'five_enemies':data['formations']['bat_quartet'] += ['cave_bat']
            elif change == 'two_casters':data['formations']['bat_veylume'] = ['veylume','veylume']
            elif change == 'outside_level':data['areas']['outer']['levels']['cave_bat'] = [2,4]
            elif change == 'missing_room':data['rooms'].pop('quiet_shelf')
            elif change == 'route_gap':data['routes']['main']['bands'][0]['first'] = 1
            elif change == 'overlapping_band':data['routes']['main']['bands'][1]['first'] = 3
            elif change == 'safe_exit':data['distance_tiles']['safe_exit'] = 16
            with self.subTest(change=change),self.assertRaises(ValueError):load_encounters(data)
        result = load_encounters(self.config)
        result['formations']['bat'].clear()
        self.assertEqual(self.config['formations']['bat'],['cave_bat'])


if __name__ == '__main__':unittest.main()
