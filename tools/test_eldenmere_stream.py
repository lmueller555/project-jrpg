"""Check water animation, all blob joins, stationary banks and scene exports."""

import json
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "assets/terrain/eldenmere/stream"
FIELDS = [((0,-1),1),((1,-1),2),((1,0),4),((1,1),8),
          ((0,1),16),((-1,1),32),((-1,0),64),((-1,-1),128)]


class StreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = json.loads((PACK / "tileset.json").read_text())
        def parts(filename):
            atlas = Image.open(PACK / filename).convert("RGBA")
            return [atlas.crop((t['rect'][0],t['rect'][1],t['rect'][0]+24,t['rect'][1]+24)) for t in cls.meta['tiles']]
        cls.banks,cls.masks = parts(cls.meta['banks']),parts(cls.meta['water_masks'])
        cls.surfaces = [[Image.open(PACK / f['image']).convert('RGBA') for f in v['frames']] for v in cls.meta['surface']['variants']]
        cls.tiles = []
        for surfaces in cls.surfaces:
            phases = []
            for surface in surfaces:
                tiles = []
                for bank,mask in zip(cls.banks,cls.masks,strict=True):
                    tile = Image.new('RGBA',(24,24))
                    tile.paste(surface,(0,0),mask.getchannel('A'))
                    tiles.append(Image.alpha_composite(tile,bank))
                phases.append(tiles)
            cls.tiles.append(phases)

    def test_lookup_parts_and_composited_atlases(self):
        self.assertEqual(self.meta['count'],47)
        self.assertEqual(self.meta['tile_size'],[24,24])
        self.assertEqual(len(self.meta['frames']),6)
        self.assertEqual(self.meta['cycle_duration_ms'],1200)
        self.assertEqual(len(self.meta['lookup_256']),256)
        self.assertEqual(len({tile.tobytes() for tile in self.tiles[0][0]}),47)
        for variant in self.surfaces:
            for surface in variant:
                self.assertEqual(surface.size,(24,24))
                self.assertEqual(surface.getchannel('A').getextrema(),(255,255))
        for raw,index in enumerate(self.meta['lookup_256']):
            expected = raw
            for diagonal,a,b in ((2,1,4),(8,4,16),(32,16,64),(128,64,1)):
                if not (raw&a and raw&b): expected &= ~diagonal
            self.assertEqual(self.meta['tiles'][index]['mask'],expected)
        palette = json.loads((PACK / 'palette.json').read_text())['materials']
        allowed = {tuple(bytes.fromhex(c[1:])) for ramp in palette.values() for c in ramp.values()}
        sheet = Image.open(PACK / self.meta['image']).convert('RGBA')
        for phase,frame in enumerate(self.meta['frames']):
            self.assertEqual(frame['duration_ms'],200)
            atlas = Image.open(PACK / frame['image']).convert('RGBA')
            self.assertEqual(atlas.size,(192,144))
            self.assertEqual(atlas.crop((168,120,192,144)).getchannel('A').getextrema(),(0,0))
            self.assertEqual(sheet.crop((0,phase*144,192,(phase+1)*144)).tobytes(),atlas.tobytes())
            for index,record in enumerate(self.meta['tiles']):
                x,y,w,h = record['rect']
                image = self.tiles[0][phase][index]
                self.assertEqual(atlas.crop((x,y,x+w,y+h)).tobytes(),image.tobytes())
                self.assertLessEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
                self.assertTrue(all(not p[3] or p[:3] in allowed for p in image.get_flattened_data()))
                if phase==0:
                    for key,expected in (('bank',self.banks[index]),('water',self.masks[index])):
                        assembled = Image.new('RGBA',(24,24))
                        for part in record['quarters']:
                            quarter = Image.open(PACK / part[key]).convert('RGBA')
                            self.assertEqual(quarter.size,(12,12))
                            assembled.paste(quarter,tuple(part['position']))
                        self.assertEqual(assembled.tobytes(),expected.tobytes())

    def test_animation_only_changes_open_water(self):
        for variant in range(2):
            full_index = self.meta['lookup_256'][255]
            self.assertEqual(len({phase[full_index].tobytes() for phase in self.tiles[variant]}),6)
            for index in range(47):
                first = self.tiles[variant][0][index]
                for phase in range(1,6):
                    image = self.tiles[variant][phase][index]
                    self.assertEqual(first.getchannel('A').tobytes(),image.getchannel('A').tobytes())
                    changes = 0
                    for y in range(24):
                        for x in range(24):
                            if first.getpixel((x,y))!=image.getpixel((x,y)):
                                self.assertEqual(self.banks[index].getpixel((x,y))[3],0)
                                self.assertEqual(self.masks[index].getpixel((x,y))[3],255)
                                changes+=1
                    self.assertLess(changes,86)  # Preserve a quiet, steady body of water.

    def test_every_join_in_every_phase_and_surface_pair(self):
        for width,height,a,b in ((4,3,(1,1),(2,1)),(3,4,(1,1),(1,2))):
            points = [(x,y) for y in range(height) for x in range(width) if (x,y) not in (a,b)]
            for pattern in range(1024):
                cells = {a,b}|{p for i,p in enumerate(points) if pattern&1<<i}
                raw = [sum(bit for (dx,dy),bit in FIELDS if (x+dx,y+dy) in cells) for x,y in (a,b)]
                ia,ib = [self.meta['lookup_256'][mask] for mask in raw]
                for phase in range(6):
                    for va,vb in ((0,0),(0,1),(1,0),(1,1)):
                        left,right = self.tiles[va][phase][ia],self.tiles[vb][phase][ib]
                        for t in range(24):
                            pa,pb = ((23,t),(0,t)) if width==4 else ((t,23),(t,0))
                            self.assertEqual(left.getpixel(pa),right.getpixel(pb),(width,pattern,phase,va,vb,t))

    def test_scene_reconstruction_and_loop(self):
        scene = json.loads((PACK / 'review_scene.json').read_text())
        ground_pack = (PACK / scene['ground_pack']).parent
        ground_meta = json.loads((ground_pack / 'tileset.json').read_text())
        grass = [Image.open(ground_pack/p).convert('RGBA') for p in ground_meta['grass']['images']]
        fills = [Image.open(ground_pack/p).convert('RGBA') for p in ground_meta['dirt_interiors']['images']]
        dirt = {t['mask']:Image.open(ground_pack/t['image']).convert('RGBA') for t in ground_meta['tiles']}
        width,height = scene['grid_size']
        base = Image.new('RGBA',(width*24,height*24))
        for y in range(height):
            for x in range(width):
                base.paste(grass[scene['grass_variants'][y][x]],(x*24,y*24))
                mask,fill = scene['dirt_masks'][y][x],scene['dirt_fill_variants'][y][x]
                if mask is not None:
                    base.alpha_composite(fills[fill] if fill is not None else dirt[mask],(x*24,y*24))
        gif = Image.open(PACK / scene['review']['gif'])
        self.addCleanup(gif.close)
        self.assertEqual(gif.n_frames,6)
        self.assertEqual(gif.info['loop'],0)
        for phase,frame in enumerate(scene['frames']):
            image = base.copy()
            for y,row in enumerate(scene['water_masks']):
                for x,mask in enumerate(row):
                    if mask is not None:
                        variant = scene['water_surface_variants'][y][x]
                        image.alpha_composite(self.tiles[variant][phase][self.meta['lookup_256'][mask]],(x*24,y*24))
            for character in scene['characters']:
                foot = character['foot']
                self.assertIsNone(scene['water_masks'][foot[1]//24][foot[0]//24])
                sprite = Image.open(ROOT / character['image_from_repo_root']).convert('RGBA')
                self.assertEqual(sprite.size,(24,36))
                image.alpha_composite(sprite,tuple(character['position']))
            native = image.convert('RGB')
            self.assertEqual(native.tobytes(),Image.open(PACK / frame['image']).tobytes())
            gif.seek(phase)
            self.assertEqual(gif.info['duration'],200)
            scale = scene['review']['scale']
            review = native.resize((native.width*scale,native.height*scale),Image.Resampling.NEAREST)
            self.assertEqual(gif.convert('RGB').tobytes(),review.tobytes())
        closeup = Image.open(PACK / 'water_cycle_review.gif')
        self.addCleanup(closeup.close)
        self.assertEqual(closeup.n_frames,6)
        self.assertEqual(closeup.info['loop'],0)
        for phase in range(6):
            closeup.seek(phase)
            self.assertEqual(closeup.info['duration'],200)


if __name__ == '__main__':
    unittest.main()
