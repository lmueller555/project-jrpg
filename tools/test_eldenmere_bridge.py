"""Verify modular bridge joins, stable decking, bank elevation and scene playback."""

import json
from pathlib import Path
import unittest

from PIL import Image, ImageChops, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/bridge'
GROUND=PACK.parent/'grass_dirt'
STREAM=PACK.parent/'stream'
GATE=PACK.parent/'gate'


def load(path):
    return json.loads(path.read_text())


def opened(path):
    return Image.open(path).convert('RGBA')


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=load(PACK/'tileset.json'); cls.scene=load(PACK/'review_scene.json')
        cls.modules={r['id']:{key:opened(PACK/r[key]) for key in ('base','foreground')}
                     for r in cls.meta['modules']}
        cls.base=opened(PACK/cls.meta['base']); cls.front=opened(PACK/cls.meta['foreground'])
        cls.frames=[opened(PACK/f['image']) for f in cls.meta['frames']]
        cls.lanterns=[opened(PACK/f['lanterns']) for f in cls.meta['frames']]
        cls.wakes=[opened(PACK/f['water_wakes']) for f in cls.meta['frames']]
        cls.shadow=opened(PACK/cls.meta['water_shadow'])
        cls.palette=load(PACK/'palette.json')['materials']

    def test_native_contract_palette_layers_and_repeatable_joins(self):
        self.assertEqual(self.meta['tile_size'],[24,24]); self.assertEqual(self.meta['module_size'],[24,72])
        self.assertEqual(self.meta['prefab_size'],[96,72]); self.assertEqual(self.meta['ground_rect'],[0,12,96,48])
        self.assertEqual(self.meta['clear_deck_width_pixels'],48)
        self.assertEqual(self.meta['cycle_duration_ms'],1200)
        self.assertEqual(self.palette,load(GATE/'palette.json')['materials'])
        allowed={tuple(bytes.fromhex(c[1:])) for ramp in self.palette.values() for c in ramp.values()}
        sheet=opened(PACK/self.meta['sheet']); self.assertEqual(sheet.size,(96,432))
        for image in (self.base,self.front,self.shadow,*self.frames,*self.lanterns,*self.wakes):
            self.assertEqual(image.size,(96,72))
            self.assertLessEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
            self.assertTrue(all(not p[3] or p[:3] in allowed for p in image.get_flattened_data()))
        for phase,frame in enumerate(self.frames):
            expected=self.base.copy(); expected.alpha_composite(self.lanterns[phase]); expected.alpha_composite(self.front)
            self.assertEqual(frame.tobytes(),expected.tobytes())
            self.assertEqual(sheet.crop((0,phase*72,96,(phase+1)*72)).tobytes(),frame.tobytes())
            self.assertEqual(self.meta['frames'][phase]['duration_ms'],200)
        for layer in ('base','foreground'):
            expected=Image.new('RGBA',(96,72))
            for col,name in enumerate(self.meta['assembly']): expected.alpha_composite(self.modules[name][layer],(col*24,0))
            self.assertEqual(expected.tobytes(),getattr(self,'base' if layer=='base' else 'front').tobytes())
        joins=[('west','middle_a'),('west','middle_b'),('middle_a','middle_a'),('middle_b','middle_b'),
               ('middle_a','middle_b'),('middle_b','middle_a'),('middle_a','east'),('middle_b','east')]
        for first,second in joins:
            for y in range(60):
                self.assertEqual(self.modules[first]['base'].getpixel((23,y)),
                                 self.modules[second]['base'].getpixel((0,y)),(first,second,y))
            for y in range(72):
                self.assertEqual(self.modules[first]['foreground'].getpixel((23,y)),
                                 self.modules[second]['foreground'].getpixel((0,y)),(first,second,y))
        for middle in (['middle_a'],['middle_b','middle_a'],['middle_a','middle_b']*2):
            assembly=['west',*middle,'east']; image=Image.new('RGBA',(24*len(assembly),72))
            for col,name in enumerate(assembly): image.alpha_composite(self.modules[name]['base'],(24*col,0))
            self.assertEqual(set(image.crop((0,12,image.width,60)).getchannel('A').get_flattened_data()),{255})

    def test_motion_is_limited_to_lanterns_and_water(self):
        self.assertEqual(len({f.tobytes() for f in self.frames}),6)
        self.assertEqual(len({w.tobytes() for w in self.wakes}),6)
        allowed_motion=Image.new('L',(96,72))
        for image in self.lanterns: allowed_motion=ImageChops.lighter(allowed_motion,image.getchannel('A'))
        for frame in self.frames[1:]:
            difference=ImageChops.difference(frame.convert('RGB'),self.frames[0].convert('RGB'))
            self.assertIsNone(ImageChops.multiply(difference,ImageChops.invert(allowed_motion).convert('RGB')).getbbox())
        for layer in self.lanterns:
            self.assertIsNone(layer.crop((24,0,72,72)).getbbox())
            self.assertIsNone(layer.crop((0,12,96,72)).getbbox())
        water={tuple(bytes.fromhex(c[1:])) for c in self.palette['water'].values()}
        for layer in [self.shadow,*self.wakes]:
            for y in range(72):
                for x in range(96):
                    pixel=layer.getpixel((x,y))
                    if pixel[3]:
                        self.assertTrue(24<=x<72 and 60<=y<71)
                        self.assertIn(pixel[:3],water)
        self.assertTrue(self.meta['front_rail_draws_after_characters'])
        self.assertGreater(self.scene['layer_order'].index('foreground_rail'),self.scene['layer_order'].index('character'))

    def test_dry_equal_height_banks_water_clearance_and_character(self):
        scene=self.scene; stream=load(STREAM/'review_scene.json')
        self.assertEqual(scene['bank_elevations_pixels'],{'W':24,'E':24})
        self.assertEqual(scene['deck_elevation_pixels'],24)
        self.assertLess(scene['water_surface_elevation_pixels'],scene['deck_elevation_pixels'])
        self.assertEqual(scene['bridge_position'],[384,180])
        for y in (8,9):
            for x in (16,19): self.assertIsNone(stream['water_masks'][y][x])
            for x in (17,18): self.assertIsNotNone(stream['water_masks'][y][x])
        x,y=scene['bridge_position']; a,b,w,h=self.meta['ground_rect']
        foot=scene['character']['foot']
        self.assertTrue(x+a<=foot[0]<x+a+w and y+b<=foot[1]<y+b+h)
        self.assertEqual(opened(ROOT/scene['character']['image_from_repo_root']).size,(24,36))
        old_caelan=next(c for c in stream['characters'] if c['name']=='caelan')
        px,py=old_caelan['position']; restored={tuple(c) for c in scene['restored_cells']}
        for yy in range(py,py+36):
            for xx in range(px,px+24): self.assertIn((xx//24,yy//24),restored)
        gate_scene=load(GATE/'review_scene.json')
        for frame in scene['frames']:
            previous=gate_scene['frames'][frame['base_gate_frame']-1]
            self.assertEqual(previous['water_phase'],frame['water_phase'])
            self.assertEqual(previous['animation'],'idle_open')
            self.assertEqual(set(previous['downstream_modes']),{'full'})

    def test_scene_reconstruction_water_clipping_and_exact_gifs(self):
        scene=self.scene; gm=load(GROUND/'tileset.json'); stream=load(STREAM/'review_scene.json')
        grass=[opened(GROUND/p) for p in gm['grass']['images']]
        dirt={t['mask']:opened(GROUND/t['image']) for t in gm['tiles']}
        fills=[opened(GROUND/p) for p in gm['dirt_interiors']['images']]
        cells={tuple(p) for p in scene['east_dirt_cells']}; joins=cells|{tuple(p) for p in scene['dirt_join_cells']}
        offsets=[(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)]
        sprite=opened(ROOT/scene['character']['image_from_repo_root'])
        water={(*bytes.fromhex(c[1:]),255) for c in self.palette['water'].values()}
        gifs=[Image.open(PACK/p) for p in ('review_scene.gif','bridge_closeup.gif','modules_review.gif')]
        for gif in gifs:
            self.addCleanup(gif.close); self.assertEqual(gif.n_frames,6); self.assertEqual(gif.info['loop'],0)
        self.assertEqual(gifs[0].size,(1584,1872)); self.assertEqual(gifs[1].size,(960,720))
        allowed=Image.new('L',(480,624)); d=ImageDraw.Draw(allowed)
        d.rectangle((384,180,479,251),fill=255)
        for x,y in scene['restored_cells']: d.rectangle((x*24,y*24,x*24+23,y*24+23),fill=255)
        for phase,info in enumerate(scene['frames']):
            background=Image.new('RGBA',(528,624))
            for y,row in enumerate(scene['grass_variants']):
                for x,variant in enumerate(row): background.paste(grass[variant],(x*24,y*24))
            previous=opened(GATE/f"scene_frames/frame_{info['base_gate_frame']:03}.png")
            background.paste(previous,(0,0))
            for x,y in scene['restored_cells']:
                tile=grass[scene['grass_variants'][y][x]].copy()
                mask=stream['dirt_masks'][y][x]; fill=stream['dirt_fill_variants'][y][x]
                if mask is not None: tile.alpha_composite(fills[fill] if fill is not None else dirt[mask])
                background.paste(tile,(x*24,y*24))
            for x,y in cells:
                raw=sum(1<<i for i,(dx,dy) in enumerate(offsets) if (x+dx,y+dy) in joins)
                mask=gm['tiles'][gm['lookup_256'][raw]]['mask']
                background.alpha_composite(dirt[mask],(x*24,y*24))
            native=background.copy(); ox,oy=scene['bridge_position']
            for overlay in (self.shadow,self.wakes[phase]):
                clipped=overlay.copy()
                for y in range(72):
                    for x in range(96):
                        if clipped.getpixel((x,y))[3] and background.getpixel((ox+x,oy+y)) not in water:
                            clipped.putpixel((x,y),(0,0,0,0))
                native.alpha_composite(clipped,(ox,oy))
            native.alpha_composite(self.base,(ox,oy)); native.alpha_composite(self.lanterns[phase],(ox,oy))
            native.alpha_composite(sprite,tuple(scene['character']['position'])); native.alpha_composite(self.front,(ox,oy))
            actual=Image.open(PACK/info['image']).convert('RGB'); native=native.convert('RGB')
            self.assertEqual(native.tobytes(),actual.tobytes())
            changes=ImageChops.difference(actual.crop((0,0,480,624)),previous.convert('RGB'))
            self.assertIsNone(ImageChops.multiply(changes,ImageChops.invert(allowed).convert('RGB')).getbbox())
            for gif in gifs:
                gif.seek(phase); self.assertEqual(gif.info['duration'],200)
            self.assertEqual(actual.resize((1584,1872),Image.Resampling.NEAREST).tobytes(),gifs[0].convert('RGB').tobytes())
            closeup=actual.crop(scene['review']['closeup_rect']).resize((960,720),Image.Resampling.NEAREST)
            self.assertEqual(closeup.tobytes(),gifs[1].convert('RGB').tobytes())
            for col,name in enumerate(self.meta['assembly']):
                module=Image.new('RGBA',(24,72))
                for y in range(3): module.paste(grass[0],(0,y*24))
                module.alpha_composite(self.modules[name]['base'])
                module.alpha_composite(self.lanterns[phase].crop((col*24,0,(col+1)*24,72)))
                module.alpha_composite(self.modules[name]['foreground'])
                shown=gifs[2].convert('RGB').crop((col*252+42,56,col*252+210,560))
                self.assertEqual(module.convert('RGB').resize((168,504),Image.Resampling.NEAREST).tobytes(),shown.tobytes())


if __name__=='__main__':
    unittest.main()
