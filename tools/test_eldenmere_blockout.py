"""Independently verify the town's footprints, water grades and quest access."""
from collections import deque
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'docs/world/eldenmere/blockout'


def rectangle_cells(rect):
    x,y,w,h=rect
    return {(xx,yy) for yy in range(y,y+h) for xx in range(x,x+w)}


class EldenmereBlockoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads((PACK/'blockout.json').read_text())

    def test_footprints_are_in_bounds_dry_disjoint_and_on_one_level(self):
        p=self.plan
        self.assertEqual(p['size_tiles'],[64,56])
        self.assertEqual(p['tile_size_px'],24)
        self.assertTrue(p['planning_only'])
        self.assertFalse(p['engine_map_implemented'])
        occupied=set()
        water={tuple(r) for r in p['water_cells']}
        for b in p['buildings']:
            tiles=rectangle_cells(b['rect'])
            self.assertFalse(tiles&occupied,b['id'])
            self.assertFalse(tiles&water,b['id'])
            self.assertTrue(all(0<=x<64 and 0<=y<56 for x,y in tiles))
            self.assertEqual(len({p['ground_levels'][y][x] for x,y in tiles}),1)
            self.assertNotIn(tuple(b['door']),tiles)
            occupied|=tiles
        sizes={r['id']:r['rect'][2:] for r in p['buildings']}
        self.assertEqual(sizes['elira'],[3,3])
        self.assertEqual(sizes['halden'],[4,3])
        self.assertEqual(sizes['venn'],[5,3])

    def test_every_water_run_descends_below_banks_and_branches_rejoin_downstream(self):
        p=self.plan
        main={(x,y):height for x,y,height in p['stream_flow']}
        runs={'brook':p['stream_flow'],**p['branch_flows']}
        for name,nodes in runs.items():
            for x,y,h in nodes:
                self.assertGreater(p['ground_levels'][y][x],h,(name,x,y,h))
            for a,b in zip(nodes,nodes[1:]):
                self.assertGreaterEqual(a[2]+1e-9,b[2],(name,a,b))
                # The brook's one-cell bank bends may move one cell sideways per row.
                self.assertLessEqual(abs(a[0]-b[0])+abs(a[1]-b[1]),2 if name=='brook' else 1)
        for name,nodes in p['branch_flows'].items():
            link=next(r for r in p['off_map_water_connections'] if r['branch']==name)
            self.assertEqual(nodes[0][:2],link['entry'])
            self.assertEqual(nodes[0][1],0)
            self.assertEqual(link['source_map'],'northern_woodland')
            x,y,h=nodes[-1]
            self.assertAlmostEqual(h,main[(x,y)],places=6,msg=name)
            self.assertGreater(nodes[-1][1],nodes[0][1])
        mill={(x,y) for x,y,_ in p['branch_flows']['mill_race']}
        irrigation={(x,y) for x,y,_ in p['branch_flows']['irrigation']}
        self.assertFalse(mill&irrigation)
        # The approved wheel needs a westward underside current; the gate flows south.
        nodes=p['branch_flows']['mill_race']
        self.assertTrue(any(a[:2]==[44,15] and b[:2]==[43,15] for a,b in zip(nodes,nodes[1:])))
        nodes=p['branch_flows']['irrigation']
        self.assertTrue(any(a[:2]==[60,27] and b[:2]==[60,28] for a,b in zip(nodes,nodes[1:])))

    def test_stream_bridges_have_dry_level_ends_and_do_not_lift_water(self):
        p=self.plan
        water={tuple(r) for r in p['water_cells']}
        bridges=[r for r in p['crossings'] if r['kind']=='stream_bridge']
        self.assertEqual(len(bridges),2)
        for bridge in bridges:
            x,y,w,h=bridge['rect']
            self.assertEqual(h,2)
            self.assertEqual(bridge['level'],1)
            self.assertEqual(bridge['orientation'],'east-west')
            for xx,yy in rectangle_cells(bridge['rect']):
                self.assertEqual(p['ground_levels'][yy][xx],bridge['level'])
            ends={(xx,yy) for xx in (x,x+w-1) for yy in range(y,y+h)}
            self.assertFalse(ends&water)
            self.assertTrue(rectangle_cells(bridge['rect'])&water)

    def test_independent_walk_graph_reaches_every_door_task_and_exit(self):
        p=self.plan
        roads={tuple(r) for r in p['road_cells']}
        water={tuple(r) for r in p['water_cells']}
        stairs={tuple(r) for r in p['stairs_cells']}
        decks=set().union(*(rectangle_cells(r['rect']) for r in p['crossings']))
        buildings=set().union(*(rectangle_cells(r['rect']) for r in p['buildings']))
        self.assertFalse(roads&buildings)
        self.assertFalse((roads&water)-decks)
        levels=p['ground_levels']
        def connected(a,b):
            x,y=a;xx,yy=b
            change=abs(levels[y][x]-levels[yy][xx])
            return (b in roads and (change==0 or (change==1 and a in stairs and b in stairs)))
        start=tuple(next(r['door'] for r in p['buildings'] if r['id']=='sanctuary'))
        reached={start};queue=deque([start])
        while queue:
            a=queue.popleft();x,y=a
            for b in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if b not in reached and b in roads and connected(a,b):
                    reached.add(b);queue.append(b)
        destinations=[r['door'] for r in p['buildings']]+[r.get('approach',r['position']) for r in p['landmarks']]
        self.assertEqual(len(destinations),14)
        for point in destinations:
            self.assertIn(tuple(point),reached,point)
        routes={r['id']:r for r in p['quest_routes']}
        self.assertEqual(routes['first_visit']['nodes'],['sanctuary','halden'])
        self.assertEqual(routes['tomas_return']['nodes'],['halden','sanctuary'])
        self.assertEqual(routes['elira_first']['nodes'][1:3],['elira','venn'])
        self.assertEqual(routes['venn_first']['nodes'][1:4],['venn','gate','elira'])
        for record in routes.values():
            for segment in record['segments']:
                for a,b in zip(segment['path'],segment['path'][1:]):
                    self.assertEqual(abs(a[0]-b[0])+abs(a[1]-b[1]),1)
                    self.assertTrue(connected(tuple(a),tuple(b)))


if __name__=='__main__':
    unittest.main()
