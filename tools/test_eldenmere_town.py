"""Check real asset registration, actor clearance, water grades and review pixels."""
from collections import deque
from functools import lru_cache
from pathlib import Path
import json
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/maps/eldenmere/terrain_foundation'


def load(path):return json.loads(path.read_text())


def opened(path):
    with Image.open(path) as im:return im.convert('RGBA')


class EldenmereTownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene=load(PACK/'scene.json')
        cls.plan=load(PACK/'adapted_plan.json')

    def test_native_approved_building_pixels_and_ground_registration(self):
        scene=self.scene
        self.assertEqual(scene['native_size'],[1536,1344])
        self.assertEqual(scene['size_tiles'],[64,56])
        self.assertEqual(scene['tile_size'],[24,24])
        self.assertFalse(scene['engine_map_implemented'])
        self.assertEqual({r['id'] for r in scene['buildings'] if r['placeholder']},{'mira','sanctuary'})
        occupied=set()
        for b in scene['buildings']:
            gx,gy,gw,gh=b['ground_rect_pixels']
            ground={(x,y) for y in range(gy//24,(gy+gh)//24) for x in range(gx//24,(gx+gw)//24)}
            self.assertFalse(occupied&ground,b['id']);occupied|=ground
            if b['placeholder']:continue
            source=ROOT/b['pack']
            meta=load(source/('mill.json' if b['id']=='mill' else 'cottage.json'))
            rect=meta['building_ground_rect'] if b['id']=='mill' else meta['ground_rect']
            self.assertEqual([b['position'][0]+rect[0],b['position'][1]+rect[1],*rect[2:]],b['ground_rect_pixels'])
        # Sample a full water repeat and the last smoke pose, retaining every opaque pixel.
        for tick in (0,1,5,17):
            frame=opened(PACK/scene['frames'][tick]['image'])
            for b in scene['buildings']:
                if b['placeholder']:continue
                source=ROOT/b['pack']
                if b['id']=='mill':
                    expected=opened(source/f'running/frame_{tick%6+1:02}.png')
                else:
                    expected=opened(source/'structure.png')
                    expected.alpha_composite(opened(source/'doors/frame_01.png'))
                    phase=(tick+b['smoke_offset'])%18+1
                    expected.alpha_composite(opened(source/f'lantern/frame_{phase:02}.png'))
                    expected.alpha_composite(opened(source/f'smoke/frame_{phase:02}.png'))
                ox,oy=b['position']
                actual=frame.crop((ox,oy,ox+expected.width,oy+expected.height))
                for source_pixel,actual_pixel in zip(expected.get_flattened_data(),actual.get_flattened_data()):
                    if source_pixel[3]==255:self.assertEqual(source_pixel,actual_pixel,b['id'])

    def test_probe_reaches_every_door_task_exit_and_scale_snapshot(self):
        nav=self.scene['navigation'];self.assertEqual(nav['probe_size'],[24,12])
        blocked=opened(PACK/'navigation/blocking.png').convert('L')
        allowed=opened(PACK/'navigation/allowed_routes.png').convert('L')
        w,h=blocked.size
        @lru_cache(None)
        def free(p):
            x,y=p
            return (12<=x<=w-12 and 6<=y<=h-6 and allowed.getpixel(p)>0
                    and not blocked.crop((x-12,y-6,x+12,y+6)).getbbox())
        start=tuple(nav['start']);queue=deque([start]);reached=set()
        while queue:
            p=queue.popleft()
            if p in reached or not free(p):continue
            reached.add(p);x,y=p;queue.extend(((x-2,y),(x+2,y),(x,y-2),(x,y+2)))
        self.assertEqual(len(reached),nav['reachable_centres'])
        for name,p in nav['destinations'].items():self.assertIn(tuple(p),reached,name)
        thresholds=[name for name in nav['destinations'] if name.endswith('_actual_threshold')]
        self.assertEqual(len(thresholds),6)
        for stair in self.scene['stairs']:
            self.assertEqual(stair['walkable_rect'][2:], [34,48])
            self.assertEqual(stair['orientation'],'north-south')
        self.assertFalse(nav['engine_collision_implemented'])

    def test_water_drops_bridge_ends_and_wheel_contact_match_source_assets(self):
        scene=self.scene
        for name,nodes in scene['water_flows'].items():
            for a,b in zip(nodes,nodes[1:]):self.assertGreaterEqual(a[2]+1e-8,b[2],name)
        self.assertEqual(scene['gate']['state'],'idle_jammed')
        irrigation=[r for r in scene['channels'] if r['branch']=='irrigation']
        gate_index=next(i for i,r in enumerate(irrigation) if r['cell']==[60,27])
        self.assertTrue(all(r['mode']=='full' for r in irrigation[:gate_index]))
        self.assertTrue(all(r['mode']=='trickle' for r in irrigation[gate_index:-1]))
        self.assertEqual(irrigation[-1]['mode'],'receiver')
        self.assertTrue(all(r['mode'] in ('full','receiver') for r in scene['channels'] if r['branch']=='mill_race'))
        self.assertEqual(sum(r['mode']=='trickle' for r in scene['spillways']),1)
        mill=next(r for r in scene['buildings'] if r['id']=='mill')
        meta=load(ROOT/mill['pack']/'mill.json');ox,oy=mill['position']
        landing=next(r for r in self.plan['crossings'] if r['id']=='mill_landing')
        self.assertEqual([ox+meta['landing_rect'][0],oy+meta['landing_rect'][1],*meta['landing_rect'][2:]],
                         [v*24 for v in landing['rect']])
        wx,wy=meta['wheel']['position'];bottom=oy+wy+47
        self.assertGreaterEqual(bottom,14*24+8)
        self.assertLess(bottom,14*24+16)
        race=[r for r in scene['channels'] if r['branch']=='mill_race']
        self.assertEqual(next(r['route'] for r in race if r['cell']==[43,14]),'channel_10_from_e')
        brook_cells={(x+dx,y) for x,y,_ in scene['water_flows']['brook'] for dx in (-1,0,1)}
        for bridge in scene['bridges']:
            x,y,w,h=bridge['rect'];self.assertEqual(h,2)
            self.assertEqual(bridge['position'],[x*24,y*24-12])
            self.assertEqual(bridge['assembly'][0],'west');self.assertEqual(bridge['assembly'][-1],'east')
            self.assertEqual(len(bridge['assembly']),w)
            self.assertTrue(all((xx,yy) not in brook_cells for xx in (x,x+w-1) for yy in range(y,y+h)))

    def test_all_scale_panels_keep_caelan_opaque_pixels_and_native_size(self):
        board=opened(PACK/'scale_checks.png').convert('RGB')
        self.assertEqual(board.size,(4160,1780))
        for i,r in enumerate(self.scene['scale_checks']):
            hero=opened(ROOT/f"assets/characters/caelan/idle_{r['facing']}.png")
            self.assertEqual(hero.size,(24,36))
            cx,cy,_,_=r['crop_tiles'];x0,y0=24+(i%4)*1032,118+(i//4)*840
            hx,hy=r['foot'][0]-12-cx*24,r['foot'][1]-30-cy*24
            for y in range(36):
                for x in range(24):
                    p=hero.getpixel((x,y))
                    if p[3]==255:
                        patch=board.crop((x0+(hx+x)*3,y0+(hy+y)*3,x0+(hx+x+1)*3,y0+(hy+y+1)*3))
                        self.assertEqual(set(patch.get_flattened_data()),{p[:3]},r['id'])

    def test_gif_is_exact_two_times_native_with_original_timing(self):
        with Image.open(PACK/'town_review.gif') as gif:
            self.assertEqual(gif.size,(3072,2808));self.assertEqual(gif.info['loop'],0)
            self.assertEqual(gif.n_frames,18)
            total=0
            for tick in range(gif.n_frames):
                gif.seek(tick);duration=gif.info['duration'];total+=duration
                self.assertEqual(duration,200)
                native=opened(PACK/self.scene['frames'][tick]['image']).convert('RGB')
                expected=native.resize((3072,2688),Image.Resampling.NEAREST)
                self.assertEqual(gif.convert('RGB').crop((0,84,3072,2772)).tobytes(),expected.tobytes())
            self.assertEqual(total,3600)


if __name__=='__main__':unittest.main()
