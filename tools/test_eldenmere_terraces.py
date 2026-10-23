"""Validate exported terrace joins, stationary masonry, routing and playback."""

import json
from pathlib import Path
import unittest

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/terraces'
CHANNELS=PACK.parent/'irrigation'
GROUND=PACK.parent/'grass_dirt'


def load(path):
    return json.loads(path.read_text())


class TerraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=load(PACK/'tileset.json')
        cls.records={r['id']:r for r in cls.meta['tiles']}
        cls.atlases=[Image.open(PACK/f['image']).convert('RGBA') for f in cls.meta['frames']]
        cls.spillways=[Image.open(PACK/f).convert('RGBA') for f in cls.meta['prefabs']['spillway_south']['frames']]

    def test_native_contract_palette_and_fixed_geometry(self):
        self.assertEqual(self.meta['tile_size'],[24,24])
        self.assertEqual(self.meta['wall_height_pixels'],24)
        self.assertEqual(len(self.records),20)
        self.assertEqual(sum(r['animated'] for r in self.records.values()),2)
        self.assertEqual(self.meta['cycle_duration_ms'],1200)
        palette=load(PACK/'palette.json')['materials']
        for material,ramp in load(CHANNELS/'palette.json')['materials'].items():
            self.assertEqual(palette[material],ramp)
        self.assertEqual(palette['stone']['base'],palette['dirt']['stone'])
        allowed={tuple(bytes.fromhex(c[1:])) for ramp in palette.values() for c in ramp.values()}
        sheet=Image.open(PACK/'terraces.png').convert('RGBA')
        self.assertEqual(sheet.size,(120,576))
        for phase,atlas in enumerate(self.atlases):
            self.assertEqual(atlas.size,(120,96))
            self.assertEqual(sheet.crop((0,phase*96,120,(phase+1)*96)).tobytes(),atlas.tobytes())
            self.assertLessEqual(set(atlas.getchannel('A').get_flattened_data()),{0,255})
            self.assertTrue(all(not p[3] or p[:3] in allowed for p in atlas.get_flattened_data()))
            for record in self.records.values():
                if record['animated']: continue
                x,y,w,h=record['rect']
                tile=Image.open(PACK/record['image']).convert('RGBA')
                self.assertEqual(tile.size,(24,24))
                self.assertEqual(atlas.crop((x,y,x+w,y+h)).tobytes(),tile.tobytes())
        stairs=Image.open(PACK/self.meta['prefabs']['stairs_south']['image']).convert('RGBA')
        self.assertEqual(stairs.size,(48,48))
        self.assertEqual(self.meta['prefabs']['stairs_south']['treads'],4)
        self.assertEqual(self.meta['prefabs']['stairs_south']['elevation_change_pixels'],24)
        for row in range(2):
            for col in range(2):
                part=Image.open(PACK/self.records[f'stairs_south_{row}_{col}']['image']).convert('RGBA')
                self.assertEqual(part.tobytes(),stairs.crop((col*24,row*24,(col+1)*24,(row+1)*24)).tobytes())
        # Alternative fronts can mix without a gap or color discontinuity at joins.
        for left in range(3):
            for right in range(3):
                a=Image.open(PACK/f'tiles/wall_front_{left:02}.png').convert('RGBA')
                b=Image.open(PACK/f'tiles/wall_front_{right:02}.png').convert('RGBA')
                self.assertEqual([a.getpixel((23,y)) for y in range(24)],[b.getpixel((0,y)) for y in range(24)])

    def test_spillway_motion_stays_in_water_and_ports_connect(self):
        prefab=self.meta['prefabs']['spillway_south']
        structure=Image.open(PACK/prefab['structure']).convert('RGBA')
        mask=Image.open(PACK/prefab['water_mask']).convert('RGBA')
        self.assertEqual(structure.size,(24,48))
        self.assertEqual(len({f.tobytes() for f in self.spillways}),6)
        for phase,frame in enumerate(self.spillways):
            self.assertEqual(frame.getchannel('A').tobytes(),self.spillways[0].getchannel('A').tobytes())
            for y in range(48):
                for x in range(24):
                    if structure.getpixel((x,y))[3]:
                        self.assertEqual(frame.getpixel((x,y)),structure.getpixel((x,y)))
                    if frame.getpixel((x,y))!=self.spillways[0].getpixel((x,y)):
                        self.assertEqual(mask.getpixel((x,y))[3],255)
            for y in (0,47):
                self.assertEqual([x for x in range(24) if mask.getpixel((x,y))[3]],list(range(8,16)))
            # The actual exported current advances down by two pixels through both ports.
            after=self.spillways[(phase+1)%6]
            for y in (2,3,4,5,44,45,46,47):
                self.assertEqual(after.getpixel((11,y)),frame.getpixel((11,y-2)))
        # Lower port's earth banks and shallow water match the approved channel material.
        channel_meta=load(CHANNELS/'tileset.json')
        channel=next(r for r in channel_meta['routes'] if r['id']=='channel_05_from_n')
        atlas=Image.open(CHANNELS/channel_meta['frames'][0]['image']).convert('RGBA')
        a,b,w,h=channel['rect']; tile=atlas.crop((a,b,a+w,b+h))
        for x in (6,7,8,15,16,17):
            self.assertEqual(self.spillways[0].getpixel((x,47)),tile.getpixel((x,0)))

    def test_upper_to_lower_routing_and_character_clearance(self):
        scene=load(PACK/'review_scene.json'); meta=load(CHANNELS/'tileset.json')
        records={r['id']:r for r in meta['routes']}
        cells={tuple(p['cell']):records[p['route']] for p in scene['channels']}
        cells[14,15]=records['inlet_s']
        for y in (20,21): cells[13,y]={'input':'N','outputs':['S']}
        vectors={'N':(0,-1),'E':(1,0),'S':(0,1),'W':(-1,0)}
        opposite={'N':'S','E':'W','S':'N','W':'E'}
        reached=set(); pending=[(14,15)]
        while pending:
            point=pending.pop()
            if point in reached: continue
            reached.add(point)
            for port in cells[point]['outputs']:
                if port=='receiver': continue
                dx,dy=vectors[port]; target=(point[0]+dx,point[1]+dy)
                self.assertIn(target,cells,(point,port))
                self.assertEqual(cells[target]['input'],opposite[port])
                pending.append(target)
        self.assertEqual(reached,set(cells))
        self.assertEqual(scene['spillway']['position'],[13*24,20*24])
        self.assertEqual(scene['stairs']['position'],[8*24,20*24])
        for c in scene['characters']:
            self.assertNotIn(tuple(v//24 for v in c['foot']),cells,c['name'])
            with Image.open(ROOT/c['image_from_repo_root']) as sprite:
                self.assertEqual(sprite.size,(24,36))
        self.assertEqual({c['level'] for c in scene['characters'] if 'level' in c},{'upper','lower'})

    def test_scene_and_review_playback_reconstruct_from_exports(self):
        scene=load(PACK/'review_scene.json'); gm=load(GROUND/'tileset.json'); cm=load(CHANNELS/'tileset.json')
        grass=[Image.open(GROUND/p).convert('RGBA') for p in gm['grass']['images']]
        dirt={t['mask']:Image.open(GROUND/t['image']).convert('RGBA') for t in gm['tiles']}
        channels={r['id']:r for r in cm['routes']}
        tiles={name:Image.open(PACK/r['image']).convert('RGBA') for name,r in self.records.items() if not r['animated']}
        stairs=Image.open(PACK/'stairs_south.png').convert('RGBA')
        offsets=[(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)]
        dirt_cells={tuple(p) for p in scene['dirt_cells']}
        connected_dirt=dirt_cells|{tuple(p) for p in scene['dirt_join_cells']}
        gifs=[Image.open(PACK/name) for name in ('review_scene.gif','terrace_closeup.gif','modules_review.gif')]
        for gif in gifs:
            self.addCleanup(gif.close); self.assertEqual(gif.n_frames,6); self.assertEqual(gif.info['loop'],0)
        for phase in range(6):
            native=Image.new('RGBA',(480,624))
            for y,row in enumerate(scene['grass_variants']):
                for x,variant in enumerate(row): native.paste(grass[variant],(24*x,24*y))
            old=Image.open(CHANNELS/f'review_scene_frame_{phase+1:02}.png').convert('RGBA')
            native.paste(old.crop((0,0,480,384)),(0,0))
            for x,y in dirt_cells:
                raw=sum(1<<i for i,(dx,dy) in enumerate(offsets) if (x+dx,y+dy) in connected_dirt)
                mask=gm['tiles'][gm['lookup_256'][raw]]['mask']
                native.alpha_composite(dirt[mask],(24*x,24*y))
            for p in scene['structures']: native.alpha_composite(tiles[p['tile']],tuple(p['position']))
            atlas=Image.open(CHANNELS/cm['frames'][phase]['image']).convert('RGBA')
            for p in scene['channels']:
                a,b,w,h=channels[p['route']]['rect']; x,y=p['cell']
                native.alpha_composite(atlas.crop((a,b,a+w,b+h)),(24*x,24*y))
            native.alpha_composite(stairs,tuple(scene['stairs']['position']))
            native.alpha_composite(self.spillways[phase],tuple(scene['spillway']['position']))
            for c in scene['characters']:
                if 'level' in c: native.alpha_composite(Image.open(ROOT/c['image_from_repo_root']).convert('RGBA'),tuple(c['position']))
            native=native.convert('RGB')
            actual=Image.open(PACK/scene['frames'][phase]['image']).convert('RGB')
            self.assertEqual(native.tobytes(),actual.tobytes())
            self.assertEqual(native.crop((0,0,480,384)).tobytes(),old.convert('RGB').crop((0,0,480,384)).tobytes())
            for gif in gifs:
                gif.seek(phase); self.assertEqual(gif.info['duration'],200)
            self.assertEqual(native.resize((1440,1872),Image.Resampling.NEAREST).tobytes(),gifs[0].convert('RGB').tobytes())
            crop=native.crop(scene['review']['closeup_rect'])
            self.assertEqual(crop.resize((1344,960),Image.Resampling.NEAREST).tobytes(),gifs[1].convert('RGB').tobytes())
            for index,r in enumerate(self.records.values()):
                x,y,w,h=r['rect']; tile=self.atlases[phase].crop((x,y,x+w,y+h))
                bg=grass[0].copy(); bg.alpha_composite(tile)
                a,b=index%5*176+12,index//5*196+48
                self.assertEqual(bg.convert('RGB').resize((144,144),Image.Resampling.NEAREST).tobytes(),
                                 gifs[2].convert('RGB').crop((a,b,a+144,b+144)).tobytes())


if __name__=='__main__':
    unittest.main()
