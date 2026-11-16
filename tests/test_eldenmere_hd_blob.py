"""Staged native art, all neighborhoods and independently enumerated seam joins."""
from pathlib import Path
from hashlib import sha256
from itertools import product
import json
import unittest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/grass_dirt_hd'
SOURCE=ROOT/'assets/source/terrain/eldenmere/grass_dirt_hd'
REVIEW=ROOT/'docs/reviews/eldenmere_hd_blob'
OFFSETS=((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1))
def image(path):
    with Image.open(path) as raw:return raw.convert('RGBA')
def canonical(raw):
    bits=[bool(raw&(1<<i)) for i in range(8)]
    for i,a,b in ((1,0,2),(3,2,4),(5,4,6),(7,6,0)):bits[i]=bits[i] and bits[a] and bits[b]
    return sum(1<<i for i,v in enumerate(bits) if v)
def world_mask(occupied,center):
    return canonical(sum(1<<i for i,(dx,dy) in enumerate(OFFSETS) if (center[0]+dx,center[1]+dy) in occupied))
class EldenmereHDBlobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((PACK/'tileset.json').read_text());cls.rec=json.loads((SOURCE/'recipe.json').read_text())
        cls.tiles={r['mask']:image(PACK/r['file']) for r in cls.meta['tiles']}
    def test_density_units_and_staged_status_are_explicit(self):
        m=self.meta
        self.assertEqual(m['logical_tile_size'],[24,24]);self.assertEqual(m['artwork_tile_size'],[48,48])
        self.assertEqual(m['artwork_pixels_per_world_pixel'],2);self.assertEqual(m['rect_space'],'artwork')
        self.assertEqual(m['artwork_quarter_size'],[24,24]);self.assertEqual(m['count'],47)
        self.assertEqual(m['integration_status'],'not_integrated');self.assertEqual(m['visual_approval'],'not_reviewed_by_user')
    def test_all_raw_neighborhoods_select_the_exact_canonical_shape(self):
        expected={canonical(raw) for raw in range(256)}
        self.assertEqual(len(expected),47);self.assertEqual(set(self.tiles),expected)
        self.assertEqual(len(self.meta['lookup_256']),256)
        for raw,index in enumerate(self.meta['lookup_256']):self.assertEqual(self.meta['tiles'][index]['mask'],canonical(raw),raw)
    def test_masks_are_distinct_have_opaque_centers_and_hard_alpha(self):
        self.assertEqual(len(list((PACK/'dirt').glob('*.png'))),47)
        self.assertEqual(len({im.getchannel('A').tobytes() for im in self.tiles.values()}),47)
        for mask,im in self.tiles.items():
            self.assertEqual(im.size,(48,48));self.assertEqual(im.getpixel((24,24))[3],255)
            self.assertLessEqual(set(im.getchannel('A').tobytes()),{0,255})
    def test_atlas_and_coverage_match_individual_tiles_with_empty_last_slot(self):
        atlas=image(PACK/'dirt_blob_47.png');coverage=image(PACK/'coverage_47.png')
        self.assertEqual(atlas.size,(384,288))
        for r in self.meta['tiles']:
            x,y,w,h=r['rect'];box=(x,y,x+w,y+h)
            self.assertEqual(atlas.crop(box).tobytes(),self.tiles[r['mask']].tobytes())
            self.assertEqual(coverage.crop(box).getchannel('A').tobytes(),self.tiles[r['mask']].getchannel('A').tobytes())
        self.assertIsNone(atlas.crop((336,240,384,288)).getbbox())
    def test_each_dirt_shape_is_one_connected_surface(self):
        for mask,im in self.tiles.items():
            occupied={(x,y) for y in range(48) for x in range(48) if im.getpixel((x,y))[3]}
            pending=[(24,24)];seen=set(pending)
            while pending:
                x,y=pending.pop()
                for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if p in occupied and p not in seen:seen.add(p);pending.append(p)
            self.assertEqual(seen,occupied,mask)

    def test_twenty_quarters_reconstruct_every_shape(self):
        self.assertEqual(len(list((PACK/'quarters').glob('*.png'))),20)
        for r in self.meta['tiles']:
            rebuilt=Image.new('RGBA',(48,48))
            for i,path in enumerate(r['quarters']):
                q=image(PACK/path);self.assertEqual(q.size,(24,24));rebuilt.alpha_composite(q,(i%2*24,i//2*24))
            self.assertEqual(rebuilt.tobytes(),self.tiles[r['mask']].tobytes(),r['mask'])
    def test_all_2048_compatible_horizontal_vertical_joins(self):
        comparisons=0
        for vertical in (False,True):
            first=(0,0);second=(0,1) if vertical else (1,0)
            positions={(p[0]+dx,p[1]+dy) for p in (first,second) for dx,dy in OFFSETS}|{first,second}
            optional=sorted(positions-{first,second});self.assertEqual(len(optional),10)
            for flags in product((False,True),repeat=len(optional)):
                occupied={first,second}|{p for p,on in zip(optional,flags) if on}
                ma,mb=world_mask(occupied,first),world_mask(occupied,second);a,b=self.tiles[ma],self.tiles[mb]
                edgea=a.crop((0,47,48,48) if vertical else (47,0,48,48))
                edgeb=b.crop((0,0,48,1) if vertical else (0,0,1,48))
                self.assertEqual(edgea.tobytes(),edgeb.tobytes(),(vertical,ma,mb));comparisons+=1
        self.assertEqual(comparisons,2048)
    def test_material_variants_match_palette_and_have_compatible_borders(self):
        palettes=self.rec['palette']
        for group,role in (('grass','grass'),('dirt','dirt')):
            colors={tuple(bytes.fromhex(c[1:]))+(255,) for c in palettes[role].values()}
            base=tuple(bytes.fromhex(palettes[role]['base'][1:]))+(255,)
            for path in self.meta['materials'][group]:
                im=image(PACK/path);raw=im.tobytes();pixels={tuple(raw[i:i+4]) for i in range(0,len(raw),4)}
                self.assertLessEqual(set(pixels),colors)
                for i in range(48):
                    for point in ((0,i),(47,i),(i,0),(i,47)):self.assertEqual(im.getpixel(point),base)
                # Actual authored 2× detail: a nearest-enlarged 24px image would
                # have zero non-uniform aligned 2×2 blocks.
                fine=sum(len({im.getpixel((x+dx,y+dy)) for dx in range(2) for dy in range(2)})>1 for y in range(0,48,2) for x in range(0,48,2))
                self.assertGreater(fine,25,path)
    def test_retained_sources_and_output_hashes(self):
        for r in self.rec['sources']:self.assertEqual(sha256((SOURCE/r['file']).read_bytes()).hexdigest(),r['sha256'])
        exports=json.loads((REVIEW/'exports.json').read_text())
        for r in exports['outputs']:self.assertEqual(sha256((ROOT/r['file']).read_bytes()).hexdigest(),r['sha256'])
    def test_offline_layout_reconstructs_with_recorded_variants(self):
        rec=json.loads((REVIEW/'layout.json').read_text());rebuilt=Image.new('RGBA',(960,768))
        for y,row in enumerate(rec['cells']):
            for x,c in enumerate(row):
                tile=image(PACK/self.meta['materials']['grass'][c['grass']])
                if c['fill'] is not None:tile=image(PACK/self.meta['materials']['dirt'][c['fill']])
                elif c['mask'] is not None:tile.alpha_composite(self.tiles[c['mask']])
                rebuilt.alpha_composite(tile,(x*48,y*48))
        self.assertEqual(rebuilt.tobytes(),image(REVIEW/'layout_native.png').tobytes())
    def test_rebuild_is_deterministic_and_nonwriting_check_passes(self):
        from tools.build_eldenmere_grass_dirt_hd import build
        outputs=build(check=True)
        for path in outputs:
            self.assertTrue(path.startswith(('assets/terrain/eldenmere/grass_dirt_hd/','docs/reviews/eldenmere_hd_blob/')),path)
if __name__=='__main__':unittest.main()
