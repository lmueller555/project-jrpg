"""Check mill layers, wheel direction, falling race grade and running/stopped scenes."""

import json
from math import cos, radians, sin
from pathlib import Path
import unittest

from PIL import Image, ImageChops, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/watermill'
BRIDGE=PACK.parent/'bridge'
STREAM=PACK.parent/'stream'
GROUND=PACK.parent/'grass_dirt'


def load(path):
    return json.loads(path.read_text())


def opened(path):
    return Image.open(path).convert('RGBA')


class WatermillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=load(PACK/'mill.json'); cls.scene=load(PACK/'review_scene.json')
        cls.palette=load(PACK/'palette.json')['materials']
        cls.building=opened(PACK/cls.meta['building']); cls.stopped=opened(PACK/cls.meta['stopped'])
        cls.wheels=[opened(PACK/f['image']) for f in cls.meta['wheel']['frames']]
        cls.effects=[opened(PACK/f['effects']) for f in cls.meta['running']['frames']]
        cls.running=[opened(PACK/f['image']) for f in cls.meta['running']['frames']]

    def test_native_contract_materials_and_static_building(self):
        self.assertEqual(self.meta['tile_size'],[24,24]); self.assertEqual(self.meta['prefab_size'],[144,168])
        self.assertEqual(self.meta['wheel']['size'],[48,48])
        for material,ramp in load(BRIDGE/'palette.json')['materials'].items():
            self.assertEqual(self.palette[material],ramp)
        allowed={tuple(bytes.fromhex(c[1:])) for ramp in self.palette.values() for c in ramp.values()}
        for image in (self.building,self.stopped,*self.wheels,*self.effects,*self.running):
            self.assertLessEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
            self.assertTrue(all(not p[3] or p[:3] in allowed for p in image.get_flattened_data()))
        self.assertEqual(self.building.size,(144,168)); self.assertEqual(self.stopped.size,(144,168))
        sheet=opened(PACK/self.meta['sheet']); self.assertEqual(sheet.size,(144,1008))
        allowed_motion=Image.new('L',(144,168)); d=ImageDraw.Draw(allowed_motion)
        x,y=self.meta['wheel']['position']; d.rectangle((x,y,x+47,y+47),fill=255)
        for effect in self.effects: allowed_motion=ImageChops.lighter(allowed_motion,effect.getchannel('A'))
        for phase,frame in enumerate(self.running):
            expected=self.building.copy(); expected.alpha_composite(self.wheels[phase],(x,y)); expected.alpha_composite(self.effects[phase])
            self.assertEqual(frame.tobytes(),expected.tobytes())
            self.assertEqual(frame.size,(144,168))
            self.assertEqual(sheet.crop((0,phase*168,144,(phase+1)*168)).tobytes(),frame.tobytes())
            difference=ImageChops.difference(frame.convert('RGB'),self.running[0].convert('RGB'))
            self.assertIsNone(ImageChops.multiply(difference,ImageChops.invert(allowed_motion).convert('RGB')).getbbox())
        expected=self.building.copy(); expected.alpha_composite(self.wheels[0],(x,y))
        self.assertEqual(self.stopped.tobytes(),expected.tobytes())
        for effect in self.effects:
            self.assertIsNone(effect.crop((0,0,144,124)).getbbox())
            for yy in range(168):
                for xx in range(144):
                    if effect.getpixel((xx,yy))[3]: self.assertTrue(77<=xx<=108 and 124<=yy<=147)

    def test_observed_wheel_rotation_and_wet_paddle_contact(self):
        wheel=self.meta['wheel']; self.assertEqual(wheel['direction'],'clockwise')
        self.assertEqual(wheel['spokes'],8); self.assertEqual(wheel['paddles'],8)
        self.assertEqual(wheel['symmetric_repeat_degrees'],45)
        self.assertEqual(wheel['implied_full_turn_ms'],9600)
        self.assertEqual(len({f.tobytes() for f in self.wheels}),6)
        wood={(*bytes.fromhex(c[1:]),255) for c in self.palette['wood'].values()}
        for phase,info in enumerate(wheel['frames']):
            self.assertEqual(info['angle_degrees'],phase*7.5); self.assertEqual(info['duration_ms'],200)
            self.assertEqual(self.wheels[phase].size,(48,48))
            for spoke,center in enumerate(info['paddle_centers']):
                theta=radians(phase*7.5+spoke*45)
                expected=(23.5+22.5*cos(theta),23.5+22.5*sin(theta))
                for a,b in zip(center,expected,strict=True): self.assertAlmostEqual(a,b,places=3)
                x,y=[min(47,max(0,round(v))) for v in center]
                self.assertIn(self.wheels[phase].getpixel((x,y)),wood,(phase,spoke,center))
        # The tagged bottom paddle travels left, agreeing with the observed westward current.
        bottom=[f['paddle_centers'][2] for f in wheel['frames']]
        self.assertTrue(all(a[0]>b[0] for a,b in zip(bottom,bottom[1:])))
        self.assertEqual(self.scene['race_flow_at_wheel'],'W')
        race_tile=next(r for r in self.meta['race']['tiles'] if r['id']=='channel_10_from_e')
        a,b,w,h=race_tile['rect']
        exported=[opened(PACK/p).crop((a,b,a+w,b+h)) for p in self.meta['race']['frames']]
        for phase in range(6):
            for x in range(24):
                self.assertEqual(exported[(phase+1)%6].getpixel((x,11)),exported[phase].getpixel(((x+2)%24,11)))
        px,py=self.scene['mill_position']; wx,wy=wheel['position']
        contact=(round(px+wx+23.5),py+wy+47)
        self.assertEqual((contact[0]//24,contact[1]//24),(26,11))
        self.assertTrue(8<=contact[1]%24<16)
        heights=self.meta['elevations']
        self.assertLess(heights['wheel_axle']-heights['wheel_radius'],heights['race_water'])
        self.assertGreater(heights['floor_and_landing'],heights['race_water'])

    def test_race_reachability_grade_blockage_and_safe_landing(self):
        race=self.scene['race']; self.assertEqual(len(race),30)
        by_cell={tuple(p['cell']):p for p in race}
        self.assertEqual(len(by_cell),len(race))
        self.assertEqual(race[0]['cell'],[17,4]); self.assertEqual(race[-1]['cell'],[17,11])
        vectors={'N':(0,-1),'E':(1,0),'S':(0,1),'W':(-1,0)}
        opposite={'N':'S','E':'W','S':'N','W':'E'}
        reached=set(); point=tuple(race[0]['cell'])
        while point not in reached:
            reached.add(point); record=by_cell[point]; out=record['outputs'][0]
            if out=='stream': break
            dx,dy=vectors[out]; destination=(point[0]+dx,point[1]+dy)
            self.assertIn(destination,by_cell); self.assertEqual(by_cell[destination]['input'],opposite[out])
            self.assertGreaterEqual(record['water_elevation_pixels'],by_cell[destination]['water_elevation_pixels'])
            point=destination
        self.assertEqual(reached,set(by_cell))
        self.assertEqual(race[0]['water_elevation_pixels'],18); self.assertEqual(race[-1]['water_elevation_pixels'],16)
        self.assertEqual(by_cell[26,11]['water_elevation_pixels'],17)
        stream=load(STREAM/'review_scene.json')
        for x,y in ((17,4),(17,11)):
            self.assertIsNotNone(stream['water_masks'][y][x])
            self.assertIsNotNone(stream['water_masks'][y-1][x]); self.assertIsNotNone(stream['water_masks'][y+1][x])
        blocked=next(i for i,p in enumerate(race) if p['cell']==self.scene['obstruction_cell'])
        self.assertEqual([p['stopped_mode'] for p in race],['full']*blocked+['blocked']+['dry']*(len(race)-blocked-1))
        self.assertEqual(by_cell[26,11]['stopped_mode'],'dry')
        px,py=self.scene['mill_position']; x,y,w,h=self.meta['building_ground_rect']
        for xx in range(px+x,px+x+w,24):
            for yy in range(py+y,py+y+h,24): self.assertNotIn((xx//24,yy//24),by_cell)
        x,y,w,h=self.meta['landing_rect']; foot=self.scene['worker']['foot']
        self.assertTrue(px+x<=foot[0]<px+x+w and py+y<=foot[1]<py+y+h)
        self.assertEqual(opened(ROOT/self.scene['worker']['image_from_repo_root']).size,(24,36))
        old_worker=next(c for c in stream['characters'] if c['name']=='male_03')
        restored={tuple(p) for p in self.scene['restored_cells']}
        x,y=old_worker['position']
        for yy in range(y,y+36):
            for xx in range(x,x+24): self.assertIn((xx//24,yy//24),restored)
        # The blocked tile has supplied water on the west side and no through-flow to the east.
        blockage=opened(PACK/self.meta['race']['blocked'])
        water={(*bytes.fromhex(c[1:]),255) for c in self.palette['water'].values()}
        self.assertEqual(sum(blockage.getpixel((23,t)) in water for t in range(8,16)),0)
        self.assertEqual(sum(blockage.getpixel((0,t)) in water for t in range(8,16)),8)

    def test_scene_reconstruction_locality_and_exact_review_gifs(self):
        scene=self.scene; gm=load(GROUND/'tileset.json'); stream=load(STREAM/'review_scene.json')
        grass=[opened(GROUND/p) for p in gm['grass']['images']]
        dirt={t['mask']:opened(GROUND/t['image']) for t in gm['tiles']}
        fills=[opened(GROUND/p) for p in gm['dirt_interiors']['images']]
        worker=opened(ROOT/scene['worker']['image_from_repo_root'])
        cells={tuple(p) for p in scene['yard_dirt_cells']}; joins=cells|{tuple(p) for p in scene['dirt_join_cells']}
        offsets=[(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)]
        atlases=[opened(PACK/p) for p in self.meta['race']['frames']]
        dry=opened(PACK/self.meta['race']['dry']); blockage=opened(PACK/self.meta['race']['blocked'])
        rectangles={r['id']:r['rect'] for r in self.meta['race']['tiles']}
        allowed=Image.new('L',(528,624)); d=ImageDraw.Draw(allowed)
        for p in scene['race']:
            x,y=p['cell']; d.rectangle((x*24,y*24,x*24+23,y*24+23),fill=255)
        for x,y in scene['restored_cells']: d.rectangle((x*24,y*24,x*24+23,y*24+23),fill=255)
        gifs={name:Image.open(PACK/name) for name in ('review_scene.gif','stopped_scene.gif','mill_closeup.gif','stopped_closeup.gif','states_review.gif')}
        for gif in gifs.values():
            self.addCleanup(gif.close); self.assertEqual(gif.n_frames,6); self.assertEqual(gif.info['loop'],0)
        native_states={}
        for phase in range(6):
            background=Image.new('RGBA',(720,624))
            for y,row in enumerate(scene['grass_variants']):
                for x,variant in enumerate(row): background.paste(grass[variant],(x*24,y*24))
            previous=opened(BRIDGE/f'scene_frames/frame_{phase+1:02}.png'); background.paste(previous,(0,0))
            for x,y in scene['restored_cells']:
                tile=grass[scene['grass_variants'][y][x]].copy(); mask=stream['dirt_masks'][y][x]; fill=stream['dirt_fill_variants'][y][x]
                if mask is not None: tile.alpha_composite(fills[fill] if fill is not None else dirt[mask])
                background.paste(tile,(x*24,y*24))
            for x,y in cells:
                raw=sum(1<<i for i,(dx,dy) in enumerate(offsets) if (x+dx,y+dy) in joins)
                mask=gm['tiles'][gm['lookup_256'][raw]]['mask']; background.alpha_composite(dirt[mask],(x*24,y*24))
            for state in ('running','stopped'):
                native=background.copy()
                for p in scene['race']:
                    a,b,w,h=rectangles[p['route']]; mode='full' if state=='running' else p['stopped_mode']
                    tile=atlases[phase].crop((a,b,a+w,b+h)) if mode=='full' else dry.crop((a,b,a+w,b+h)) if mode=='dry' else blockage
                    x,y=p['cell']; native.alpha_composite(tile,(x*24,y*24))
                native.alpha_composite(self.running[phase] if state=='running' else self.stopped,tuple(scene['mill_position']))
                native.alpha_composite(worker,tuple(scene['worker']['position'])); native=native.convert('RGB')
                actual=Image.open(PACK/scene['states'][state][phase]['image']).convert('RGB')
                self.assertEqual(actual.size,(720,624)); self.assertEqual(native.tobytes(),actual.tobytes())
                native_states[state,phase]=native
                changes=ImageChops.difference(actual.crop((0,0,528,624)),previous.convert('RGB'))
                self.assertIsNone(ImageChops.multiply(changes,ImageChops.invert(allowed).convert('RGB')).getbbox())
                full=gifs['review_scene.gif' if state=='running' else 'stopped_scene.gif']
                close=gifs['mill_closeup.gif' if state=='running' else 'stopped_closeup.gif']
                for gif in (full,close): gif.seek(phase); self.assertEqual(gif.info['duration'],200)
                self.assertEqual(actual.resize((2160,1872),Image.Resampling.NEAREST).tobytes(),full.convert('RGB').tobytes())
                crop=actual.crop(scene['review']['closeup_rect']).resize((864,960),Image.Resampling.NEAREST)
                self.assertEqual(crop.tobytes(),close.convert('RGB').tobytes())
            comparison=gifs['states_review.gif']; comparison.seek(phase); self.assertEqual(comparison.info['duration'],200)
            self.assertEqual(comparison.size,(1392,832))
            for col,state in enumerate(('running','stopped')):
                crop=native_states[state,phase].crop((504,96,720,336)).resize((648,720),Image.Resampling.NEAREST)
                self.assertEqual(crop.tobytes(),comparison.convert('RGB').crop((col*696+24,80,col*696+672,800)).tobytes())


if __name__=='__main__':
    unittest.main()
