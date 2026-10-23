"""Check gate poses, material/port contracts, delayed flow and review exports."""

import json
from pathlib import Path
import unittest

from PIL import Image, ImageChops, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/gate'
TERRACE=PACK.parent/'terraces'
CHANNELS=PACK.parent/'irrigation'
GROUND=PACK.parent/'grass_dirt'


def load(path):
    return json.loads(path.read_text())


class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=load(PACK/'sprite.json'); cls.scene=load(PACK/'review_scene.json')
        cls.animations={a['id']:a for a in cls.meta['animations']}
        cls.frames={name:[Image.open(PACK/f['image']).convert('RGBA') for f in a['frames']]
                    for name,a in cls.animations.items()}
        cls.palette=load(PACK/'palette.json')['materials']

    def test_native_palette_fixed_frame_and_transition_endpoints(self):
        self.assertEqual(self.meta['sprite_size'],[24,36])
        self.assertEqual(self.meta['ground_rect'],[0,12,24,24])
        self.assertEqual(self.meta['water_width_pixels'],8)
        self.assertEqual(len(self.animations),7)
        for material,ramp in load(TERRACE/'palette.json')['materials'].items():
            self.assertEqual(self.palette[material],ramp)
        allowed={tuple(bytes.fromhex(c[1:])) for ramp in self.palette.values() for c in ramp.values()}
        fixed=Image.open(PACK/self.meta['fixed_structure']).convert('RGBA')
        sheet=Image.open(PACK/self.meta['image']).convert('RGBA')
        self.assertEqual(sheet.size,(144,252))
        for name,animation in self.animations.items():
            self.assertEqual(animation['loop'],name.startswith('idle_'))
            self.assertEqual(len(animation['frames']),6)
            for info,frame in zip(animation['frames'],self.frames[name],strict=True):
                self.assertEqual(frame.size,(24,36)); self.assertEqual(info['duration_ms'],200)
                self.assertLessEqual(set(frame.getchannel('A').get_flattened_data()),{0,255})
                self.assertTrue(all(not p[3] or p[:3] in allowed for p in frame.get_flattened_data()))
                x,y,w,h=info['sheet_rect']
                self.assertEqual(sheet.crop((x,y,x+w,y+h)).tobytes(),frame.tobytes())
                for y in range(36):
                    for x in range(24):
                        if fixed.getpixel((x,y))[3] and not (19<=x<=21 and 14<=y<=25):
                            self.assertEqual(frame.getpixel((x,y)),fixed.getpixel((x,y)),(name,x,y))
        endpoints=[('opening','idle_closed','idle_open'),('closing','idle_open','idle_closed'),
                   ('repair','idle_jammed','idle_closed'),('jamming','idle_closed','idle_jammed')]
        for name,start,end in endpoints:
            self.assertEqual(self.frames[name][0].tobytes(),self.frames[start][0].tobytes())
            self.assertEqual(self.frames[name][-1].tobytes(),self.frames[end][-1].tobytes())
        self.assertEqual([f['lift'] for f in self.animations['opening']['frames']],[0,2,4,7,9,11])
        self.assertEqual([f['jam'] for f in self.animations['repair']['frames']],[3,3,2,1,0,0])

    def test_open_closed_jammed_water_and_steady_materials(self):
        water={(*bytes.fromhex(c[1:]),255) for c in self.palette['water'].values()}
        meta=load(CHANNELS/'tileset.json'); record=next(r for r in meta['routes'] if r['id']=='channel_05_from_n')
        for phase in range(6):
            atlas=Image.open(CHANNELS/meta['frames'][phase]['image']).convert('RGBA')
            a,b,w,h=record['rect']; tile=atlas.crop((a,b,a+w,b+h))
            for name,count in [('idle_open',8),('idle_closed',0),('idle_jammed',2)]:
                image=self.frames[name][phase]
                self.assertEqual(sum(image.getpixel((x,35)) in water for x in range(8,16)),count)
            for x in range(24):
                self.assertEqual(self.frames['idle_open'][phase].getpixel((x,35)),tile.getpixel((x,23)))
        # In idle states only the visible water moves; the board, pin and supports stay put.
        for name in ('idle_open','idle_closed','idle_jammed'):
            first=self.frames[name][0]
            for frame in self.frames[name][1:]:
                for y in range(36):
                    for x in range(24):
                        if frame.getpixel((x,y))!=first.getpixel((x,y)):
                            self.assertIn(frame.getpixel((x,y)),water)
                            self.assertIn(first.getpixel((x,y)),water)

    def test_local_routing_gravity_and_delayed_response(self):
        old=load(TERRACE/'review_scene.json'); routes={r['id']:r for r in load(CHANNELS/'tileset.json')['routes']}
        placements={tuple(p['cell']):p['route'] for p in old['channels']}
        self.assertEqual(placements[tuple(self.scene['gate_cell'])],'channel_05_from_n')
        self.assertEqual(self.scene['gate_position'],[264,420])
        self.assertEqual(self.scene['ground_elevation_pixels'],24)
        previous=(11,18); outgoing='S'; level=24; reached=[]
        directions={'N':(0,-1),'E':(1,0),'S':(0,1),'W':(-1,0)}
        opposite={'N':'S','E':'W','S':'N','W':'E'}
        for p in self.scene['downstream']:
            dx,dy=directions[outgoing]; point=tuple(p['cell'])
            self.assertEqual(point,(previous[0]+dx,previous[1]+dy))
            if 'route' in p:
                self.assertEqual(placements[point],p['route'])
                route=routes[p['route']]; self.assertEqual(route['input'],opposite[outgoing])
                self.assertEqual(len(route['outputs']),1)
                outgoing=route['outputs'][0]
            else:
                self.assertEqual(p['cell'],[13,20]); self.assertEqual(p['size'],[24,48])
                self.assertEqual(point[0]*24,old['spillway']['position'][0])
                self.assertEqual(point[1]*24,old['spillway']['position'][1])
                self.assertEqual(level,24); level=0; point=(13,21)
            previous=point; reached.append(tuple(p['cell']))
        self.assertEqual(outgoing,'receiver'); self.assertEqual(level,0)
        self.assertEqual(len(set(reached)),8)
        clock=self.scene['frames']
        self.assertEqual(len(clock),78)
        self.assertEqual(self.scene['cycle_duration_ms'],15600)
        recipe=load(ROOT/'assets/source/terrain/eldenmere/gate/recipe.json')
        self.assertEqual([p['delay'] for p in self.scene['downstream']],
                         [n*recipe['water_delay_ticks_per_cell'] for n in (1,2,3,4,6,7,8,9)])
        for tick,event in enumerate(clock):
            self.assertEqual(event['water_phase'],tick%6)
            for index,p in enumerate(self.scene['downstream']):
                source=clock[(tick-p['delay'])%len(clock)]
                pose=self.animations[source['animation']]['frames'][source['animation_frame']]
                expected='full' if pose['flow']>0.7 else 'trickle' if pose['flow']>0 else 'dry'
                self.assertEqual(event['downstream_modes'][index],expected)
        for index in range(8):
            self.assertEqual({f['downstream_modes'][index] for f in clock},{'dry','trickle','full'})

    def test_scene_reconstructs_and_gif_pixels_match(self):
        scene=self.scene; meta=load(CHANNELS/'tileset.json'); records={r['id']:r for r in meta['routes']}
        old=load(TERRACE/'review_scene.json')
        grass=[Image.open(GROUND/f'grass_{i:02}.png').convert('RGBA') for i in range(4)]
        channel_atlases=[Image.open(CHANNELS/f['image']).convert('RGBA') for f in meta['frames']]
        spillways=[Image.open(TERRACE/f'spillway/frame_{i+1:02}.png').convert('RGBA') for i in range(6)]
        effects=self.meta['downstream_responses']
        dry=Image.open(PACK/effects['dry']).convert('RGBA')
        trickles=[Image.open(PACK/p).convert('RGBA') for p in effects['trickle']]
        for atlas in (dry,*trickles): self.assertEqual(atlas.size,(72,72))
        gifs=[Image.open(PACK/name) for name in ('review_scene.gif','gate_closeup.gif')]
        for gif in gifs:
            self.addCleanup(gif.close); self.assertEqual(gif.n_frames,78); self.assertEqual(gif.info['loop'],0)
        self.assertEqual(gifs[0].size,(1440,1920)); self.assertEqual(gifs[1].size,(840,1068))
        allowed=Image.new('L',(480,624)); d=ImageDraw.Draw(allowed)
        d.rectangle((264,420,287,455),fill=255)
        for p in scene['downstream']:
            x,y=p['cell']; w,h=p['size']; d.rectangle((x*24,y*24,x*24+w-1,y*24+h-1),fill=255)
        for tick,event in enumerate(scene['frames']):
            phase=event['water_phase']; base=Image.open(TERRACE/f'review_scene_frame_{phase+1:02}.png').convert('RGBA')
            native=base.copy()
            for p,mode in zip(scene['downstream'],event['downstream_modes'],strict=True):
                x,y=p['cell']; name=p.get('route','spillway')
                if mode=='full':
                    if name=='spillway': replacement=spillways[phase]
                    else:
                        a,b,w,h=records[name]['rect']; replacement=channel_atlases[phase].crop((a,b,a+w,b+h))
                else:
                    atlas=dry if mode=='dry' else trickles[phase]
                    replacement=Image.new('RGBA',tuple(p['size']))
                    for r in effects['tiles']:
                        if r['id']==name:
                            a,b,w,h=r['rect']; replacement.paste(atlas.crop((a,b,a+w,b+h)),(0,r['half']*24))
                for dy in range(p['size'][1]//24): native.paste(grass[old['grass_variants'][y+dy][x]],(x*24,(y+dy)*24))
                native.alpha_composite(replacement,(x*24,y*24))
            x,y=scene['gate_cell']; native.paste(grass[old['grass_variants'][y][x]],(x*24,y*24))
            native.alpha_composite(self.frames[event['animation']][event['animation_frame']],tuple(scene['gate_position']))
            actual=Image.open(PACK/event['image']).convert('RGB'); native=native.convert('RGB')
            self.assertEqual(actual.size,(480,624)); self.assertEqual(actual.tobytes(),native.tobytes())
            changed=ImageChops.difference(actual,base.convert('RGB'))
            self.assertIsNone(ImageChops.multiply(changed,ImageChops.invert(allowed).convert('RGB')).getbbox())
            for gif in gifs:
                gif.seek(tick); self.assertEqual(gif.info['duration'],200)
            self.assertEqual(actual.resize((1440,1872),Image.Resampling.NEAREST).tobytes(),
                             gifs[0].convert('RGB').crop((0,48,1440,1920)).tobytes())
            crop=actual.crop(scene['review']['closeup_rect']).resize((840,1020),Image.Resampling.NEAREST)
            self.assertEqual(crop.tobytes(),gifs[1].convert('RGB').crop((0,48,840,1068)).tobytes())
        states=Image.open(PACK/'states_review.gif'); self.addCleanup(states.close)
        self.assertEqual(states.n_frames,6); self.assertEqual(states.info['loop'],0)
        for phase in range(6):
            states.seek(phase); self.assertEqual(states.info['duration'],200)
            for col,name in enumerate(('idle_open','idle_closed','idle_jammed')):
                native=Image.new('RGBA',(24,36)); native.paste(grass[0],(0,0)); native.paste(grass[0],(0,24))
                native.alpha_composite(self.frames[name][phase])
                # Compare the gate's actual nontransparent sprite pixels against the board crop.
                shown=states.convert('RGB').crop((col*240+24,160,col*240+216,448)).resize((24,36),Image.Resampling.NEAREST)
                for y in range(36):
                    for x in range(24):
                        pixel=self.frames[name][phase].getpixel((x,y))
                        if pixel[3]: self.assertEqual(shown.getpixel((x,y)),pixel[:3])


if __name__=='__main__':
    unittest.main()
