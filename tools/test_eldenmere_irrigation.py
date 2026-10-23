"""Check irrigation module joins, flow direction, network and scene playback."""

import json
from pathlib import Path
import unittest

from PIL import Image


ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/irrigation'
VECTORS={'N':(0,-1),'E':(1,0),'S':(0,1),'W':(-1,0)}
OPPOSITE={'N':'S','E':'W','S':'N','W':'E'}


class IrrigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((PACK/'tileset.json').read_text())
        cls.records={r['id']:r for r in cls.meta['routes']}
        cls.frames=[Image.open(PACK/f['image']).convert('RGBA') for f in cls.meta['frames']]
        cls.tiles={}; cls.layers={}
        for record in cls.records.values():
            x,y,w,h=record['rect']
            cls.tiles[record['id']]=[f.crop((x,y,x+w,y+h)) for f in cls.frames]
            cls.layers[record['id']]=[Image.open(PACK/record[k]).convert('RGBA') for k in ('bank','water_mask')]

    def test_native_contract_and_localized_motion(self):
        self.assertEqual(len(self.records),40)
        self.assertEqual(self.meta['tile_size'],[24,24])
        self.assertEqual(self.meta['cycle_duration_ms'],1200)
        palette=json.loads((PACK/'palette.json').read_text())['materials']
        allowed={tuple(bytes.fromhex(c[1:])) for ramp in palette.values() for c in ramp.values()}
        sheet=Image.open(PACK/self.meta['image']).convert('RGBA')
        self.assertEqual(sheet.size,(192,720))
        for i,frame in enumerate(self.frames):
            self.assertEqual(frame.size,(192,120))
            self.assertEqual(sheet.crop((0,i*120,192,(i+1)*120)).tobytes(),frame.tobytes())
        for name,record in self.records.items():
            bank,mask=self.layers[name]
            images=self.tiles[name]
            self.assertEqual(len({image.tobytes() for image in images}),6,name)
            for image in images:
                self.assertEqual(image.size,(24,24))
                self.assertLessEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
                self.assertTrue(all(not p[3] or p[:3] in allowed for p in image.get_flattened_data()))
            for phase in range(1,6):
                for y in range(24):
                    for x in range(24):
                        if images[0].getpixel((x,y))==images[phase].getpixel((x,y)):continue
                        fx=False
                        if 'effect_bounds' in record:
                            a,b,w,h=record['effect_bounds']; fx=a<=x<a+w and b<=y<b+h
                        if not fx:
                            self.assertEqual(mask.getpixel((x,y))[3],255,(name,x,y))
                            self.assertEqual(bank.getpixel((x,y))[3],0,(name,x,y))

    def test_structural_connections_and_flow_translation(self):
        # Every output may join any module with a matching input, including intakes/outlets.
        for first in self.records.values():
            for port in first['outputs']:
                if port not in VECTORS:continue
                for second in self.records.values():
                    if second['input']!=OPPOSITE[port]:continue
                    for a,b in zip(self.layers[first['id']],self.layers[second['id']],strict=True):
                        for t in range(24):
                            pa,pb={'E':((23,t),(0,t)),'W':((0,t),(23,t)),
                                   'S':((t,23),(t,0)),'N':((t,0),(t,23))}[port]
                            self.assertEqual(a.getpixel(pa),b.getpixel(pb),(first['id'],second['id'],port,t))
        # Observe the exported pixels: straight currents advance exactly two pixels each phase.
        for name,direction in (('channel_10_from_w','E'),('channel_10_from_e','W'),
                               ('channel_05_from_n','S'),('channel_05_from_s','N')):
            images=self.tiles[name]
            dx,dy=VECTORS[direction]
            for phase in range(6):
                before,after=images[phase],images[(phase+1)%6]
                for t in range(24):
                    x,y=(t,11) if dx else (11,t)
                    previous=((x-2*dx)%24,(y-2*dy)%24)
                    self.assertEqual(after.getpixel((x,y)),before.getpixel(previous),(name,phase,t))

    def test_review_network_is_connected_and_directed(self):
        scene=json.loads((PACK/'review_scene.json').read_text())
        cells={tuple(p['cell']):self.records[p['route']] for p in scene['channels']}
        starts=[p for p,r in cells.items() if r['kind']=='inlet']
        self.assertEqual(len(starts),1)
        source_scene=json.loads((PACK/scene['base_scene']).read_text())
        for x,y in starts:
            self.assertIsNotNone(source_scene['water_masks'][y][x])
        reached=set(); pending=starts[:]
        while pending:
            point=pending.pop()
            if point in reached:continue
            reached.add(point)
            record=cells[point]
            for port in record['outputs']:
                if port=='receiver':continue
                dx,dy=VECTORS[port]; destination=(point[0]+dx,point[1]+dy)
                self.assertIn(destination,cells,(point,port))
                self.assertEqual(cells[destination]['input'],OPPOSITE[port])
                pending.append(destination)
        self.assertEqual(reached,set(cells))
        self.assertEqual(sum(r['kind']=='outlet' for r in cells.values()),3)

    def test_scene_reconstructs_and_gifs_match(self):
        scene=json.loads((PACK/'review_scene.json').read_text())
        old=json.loads((PACK/scene['base_scene']).read_text())
        ground=PACK.parent/'grass_dirt'; stream=PACK.parent/'stream'
        gm=json.loads((ground/'tileset.json').read_text()); sm=json.loads((stream/'tileset.json').read_text())
        grass=[Image.open(ground/p).convert('RGBA') for p in gm['grass']['images']]
        fills=[Image.open(ground/p).convert('RGBA') for p in gm['dirt_interiors']['images']]
        dirt={t['mask']:Image.open(ground/t['image']).convert('RGBA') for t in gm['tiles']}
        banks=Image.open(stream/sm['banks']).convert('RGBA'); masks=Image.open(stream/sm['water_masks']).convert('RGBA')
        surfaces=[[Image.open(stream/f['image']).convert('RGBA') for f in v['frames']] for v in sm['surface']['variants']]
        width,height=scene['grid_size']; base=Image.new('RGBA',(width*24,height*24))
        for y in range(height):
            for x in range(width):
                base.paste(grass[scene['grass_variants'][y][x]],(x*24,y*24))
                if y<len(old['dirt_masks']) and old['dirt_masks'][y][x] is not None:
                    mask,fill=old['dirt_masks'][y][x],old['dirt_fill_variants'][y][x]
                    base.alpha_composite(fills[fill] if fill is not None else dirt[mask],(x*24,y*24))
        gif=Image.open(PACK/scene['review']['gif']); self.addCleanup(gif.close)
        closeup=Image.open(PACK/scene['review']['closeup_gif']); self.addCleanup(closeup.close)
        modules=Image.open(PACK/'modules_review.gif'); self.addCleanup(modules.close)
        for image in (gif,closeup,modules):
            self.assertEqual(image.n_frames,6); self.assertEqual(image.info['loop'],0)
        occupied={tuple(p['cell']) for p in scene['channels']}
        for phase,frame in enumerate(scene['frames']):
            image=base.copy()
            for y,row in enumerate(old['water_masks']):
                for x,mask in enumerate(row):
                    if mask is None:continue
                    record=sm['tiles'][sm['lookup_256'][mask]]; tx,ty,w,h=record['rect']; box=(tx,ty,tx+w,ty+h)
                    tile=Image.new('RGBA',(24,24)); variant=old['water_surface_variants'][y][x]
                    tile.paste(surfaces[variant][phase],(0,0),masks.crop(box).getchannel('A'))
                    image.alpha_composite(Image.alpha_composite(tile,banks.crop(box)),(x*24,y*24))
            for placement in scene['channels']:
                x,y=placement['cell']; image.alpha_composite(self.tiles[placement['route']][phase],(x*24,y*24))
            for character in scene['characters']:
                self.assertNotIn(tuple(v//24 for v in character['foot']),occupied)
                sprite=Image.open(ROOT/character['image_from_repo_root']).convert('RGBA')
                self.assertEqual(sprite.size,(24,36)); image.alpha_composite(sprite,tuple(character['position']))
            native=image.convert('RGB'); self.assertEqual(native.tobytes(),Image.open(PACK/frame['image']).tobytes())
            for animated in (gif,closeup,modules):
                animated.seek(phase); self.assertEqual(animated.info['duration'],200)
            scale=scene['review']['scale']
            enlarged=native.resize((native.width*scale,native.height*scale),Image.Resampling.NEAREST)
            self.assertEqual(enlarged.tobytes(),gif.convert('RGB').tobytes())
            crop=native.crop(scene['review']['closeup_rect']); scale=scene['review']['closeup_scale']
            self.assertEqual(crop.resize((crop.width*scale,crop.height*scale),Image.Resampling.NEAREST).tobytes(),closeup.convert('RGB').tobytes())
            module_rgb=modules.convert('RGB')
            for record in self.records.values():
                x,y=record['index']%8*168+12,record['index']//8*196+48
                expected=Image.alpha_composite(grass[0],self.tiles[record['id']][phase]).convert('RGB')
                self.assertEqual(module_rgb.crop((x,y,x+144,y+144)).tobytes(),expected.resize((144,144),Image.Resampling.NEAREST).tobytes())


if __name__=='__main__':
    unittest.main()
