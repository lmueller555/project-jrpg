"""Staged paving: connected shapes, phase ports and actual substrate ownership."""
from pathlib import Path
from hashlib import sha256
from itertools import product
import json
import unittest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/stone_paving_hd'
SOURCE=ROOT/'assets/source/terrain/eldenmere/stone_paving_hd'
REVIEW=ROOT/'docs/reviews/eldenmere_hd_stone'
GROUND=ROOT/'assets/terrain/eldenmere/grass_dirt_hd'
OFFSETS=((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1))
def image(path):
    with Image.open(path) as im:return im.convert('RGBA')
def colors(im):
    data=im.tobytes();return {tuple(data[i:i+4]) for i in range(0,len(data),4) if data[i+3]}
def canonical(raw):
    bits=[bool(raw&(1<<i)) for i in range(8)]
    for i,a,b in ((1,0,2),(3,2,4),(5,4,6),(7,6,0)):bits[i]=bits[i] and bits[a] and bits[b]
    return sum(1<<i for i,v in enumerate(bits) if v)
def mask_at(occupied,point):return canonical(sum(1<<i for i,(dx,dy) in enumerate(OFFSETS) if (point[0]+dx,point[1]+dy) in occupied))
def palette(ramp):return {tuple(bytes.fromhex(c[1:]))+(255,) for c in ramp.values()}
class StonePavingHDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((PACK/'tileset.json').read_text());cls.rec=json.loads((SOURCE/'recipe.json').read_text())
        cls.entries={r['mask']:r for r in cls.meta['tiles']}
        cls.bodies={(m,p):image(PACK/r['body_files'][p]) for m,r in cls.entries.items() for p in range(4)}
        cls.contacts={(m,n):image(PACK/r['contact_files'][n]) for m,r in cls.entries.items() for n in ('grass','dirt')}
        cls.phases=[image(PACK/p) for p in cls.meta['interior_phases']]
    def test_units_staged_status_and_phase_rule_are_explicit(self):
        m=self.meta;self.assertEqual(m['artwork_pixels_per_world_pixel'],2)
        self.assertEqual(m['logical_tile_size'],[24,24]);self.assertEqual(m['artwork_tile_size'],[48,48]);self.assertEqual(m['rect_space'],'artwork')
        self.assertEqual(m['integration_status'],'not_integrated');self.assertEqual(m['visual_approval'],'not_reviewed_by_user')
        self.assertEqual(m['shape_count'],47);self.assertEqual(m['texture_phase_count'],4);self.assertIn('world_tile_x',m['texture_phase_rule'])
    def test_all_256_neighborhoods_and_47_distinct_connected_shapes(self):
        self.assertEqual(set(self.entries),{canonical(i) for i in range(256)})
        self.assertEqual(len(self.meta['lookup_256']),256)
        for raw,index in enumerate(self.meta['lookup_256']):self.assertEqual(self.meta['tiles'][index]['mask'],canonical(raw))
        self.assertEqual(len({im.getchannel('A').tobytes() for (m,p),im in self.bodies.items() if p==0}),47)
        for m in self.entries:
            im=self.bodies[m,0];occupied={(x,y) for y in range(48) for x in range(48) if im.getpixel((x,y))[3]}
            pending=[(24,24)];seen=set(pending)
            while pending:
                x,y=pending.pop()
                for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if p in occupied and p not in seen:seen.add(p);pending.append(p)
            self.assertEqual(seen,occupied,m)
            for p in range(4):self.assertEqual(self.bodies[m,p].getchannel('A').tobytes(),im.getchannel('A').tobytes())
    def test_atlases_coverage_and_empty_slot(self):
        coverage=image(PACK/self.meta['coverage'])
        for p,path in enumerate(self.meta['surface_atlases']):
            atlas=image(PACK/path);self.assertEqual(atlas.size,(384,288));self.assertIsNone(atlas.crop((336,240,384,288)).getbbox())
            for m,r in self.entries.items():
                x,y,w,h=r['rect'];box=(x,y,x+w,y+h)
                self.assertEqual(atlas.crop(box).tobytes(),self.bodies[m,p].tobytes())
                self.assertEqual(coverage.crop(box).getchannel('A').tobytes(),self.bodies[m,p].getchannel('A').tobytes())
        for n,path in self.meta['contact_atlases'].items():
            atlas=image(PACK/path);self.assertIsNone(atlas.crop((336,240,384,288)).getbbox())
            for m,r in self.entries.items():
                x,y,w,h=r['rect'];self.assertEqual(atlas.crop((x,y,x+w,y+h)).tobytes(),self.contacts[m,n].tobytes())
    def test_quarter_masks_reconstruct_every_shape(self):
        self.assertEqual(len(list((PACK/'quarters').rglob('*.png'))),60)
        for m,r in self.entries.items():
            result=Image.new('RGBA',(48,48))
            for i,path in enumerate(r['coverage_quarters']):
                im=image(PACK/path);self.assertEqual(im.size,(24,24));result.alpha_composite(im,(i%2*24,i//2*24))
            self.assertEqual(result.getchannel('A').tobytes(),self.bodies[m,0].getchannel('A').tobytes())
    def test_8192_phase_correct_body_joins_and_4096_contact_joins(self):
        body_count=contact_count=0
        for vertical in (False,True):
            a=(0,0);b=(0,1) if vertical else (1,0)
            optional=sorted(({(p[0]+dx,p[1]+dy) for p in (a,b) for dx,dy in OFFSETS}|{a,b})-{a,b});self.assertEqual(len(optional),10)
            for flags in product((False,True),repeat=10):
                occupied={a,b}|{p for p,on in zip(optional,flags) if on};ma,mb=mask_at(occupied,a),mask_at(occupied,b)
                def edge(im,last):return im.crop((0,47,48,48) if last and vertical else (47,0,48,48) if last else (0,0,48,1) if vertical else (0,0,1,48)).tobytes()
                for phase in range(4):
                    other=phase^(2 if vertical else 1)
                    self.assertEqual(edge(self.bodies[ma,phase],True),edge(self.bodies[mb,other],False),(vertical,ma,mb,phase));body_count+=1
                for n in ('grass','dirt'):
                    self.assertEqual(edge(self.contacts[ma,n],True),edge(self.contacts[mb,n],False),(vertical,ma,mb,n));contact_count+=1
        self.assertEqual(body_count,8192);self.assertEqual(contact_count,4096)
    def test_material_pattern_is_phase_continuous_and_has_native_detail(self):
        pattern=image(PACK/self.meta['surface_pattern']);self.assertEqual(pattern.size,(96,96))
        self.assertEqual(len({p.tobytes() for p in self.phases}),4)
        for p,im in enumerate(self.phases):self.assertEqual(im.tobytes(),pattern.crop((p%2*48,p//2*48,p%2*48+48,p//2*48+48)).tobytes())
        fine=sum(len({pattern.getpixel((x+dx,y+dy)) for dx in range(2) for dy in range(2)})>1 for y in range(0,96,2) for x in range(0,96,2))
        self.assertGreater(fine,250)
        for y in range(96):self.assertEqual(pattern.getpixel((0,y)),pattern.getpixel((95,y)))
        for x in range(96):self.assertEqual(pattern.getpixel((x,0)),pattern.getpixel((x,95)))
    def test_palette_hard_alpha_and_contact_coverage(self):
        stone=palette(self.rec['palette']['stone'])
        for (m,p),im in self.bodies.items():
            self.assertEqual(im.size,(48,48));self.assertLessEqual(set(im.getchannel('A').tobytes()),{0,255});self.assertLessEqual(colors(im),stone)
            for n in ('grass','dirt'):
                contact=self.contacts[m,n];self.assertLessEqual(colors(contact),palette(self.rec['palette'][n]))
                a=im.getchannel('A').tobytes();b=contact.getchannel('A').tobytes();self.assertFalse(any(x and y for x,y in zip(a,b)))
    def test_mixed_substrate_trim_selection_is_per_pixel_without_holes(self):
        from tools.build_eldenmere_stone_paving_hd import compose
        grass=(44,124,80,255);earth=(177,142,104,255)
        for m in self.entries:
            body=self.bodies[m,0];gt=self.contacts[m,'grass'];dt=self.contacts[m,'dirt']
            for condition in (lambda x,y:False,lambda x,y:True,lambda x,y:x>=24,lambda x,y:y>=24,lambda x,y:x+y>=47):
                substrate=Image.new('RGBA',(48,48));mask=Image.new('L',(48,48))
                for y in range(48):
                    for x in range(48):substrate.putpixel((x,y),earth if condition(x,y) else grass);mask.putpixel((x,y),255 if condition(x,y) else 0)
                result=compose(substrate,body,gt,dt,mask)
                for y in range(48):
                    for x in range(48):
                        core=body.getpixel((x,y));trim=(dt if condition(x,y) else gt).getpixel((x,y))
                        self.assertEqual(result.getpixel((x,y)),core if core[3] else trim if trim[3] else substrate.getpixel((x,y)))
    def test_scene_layers_and_terrain_reconstruct_at_three_material_junctions(self):
        meta=json.loads((REVIEW/'layout.json').read_text());gm=json.loads((GROUND/'tileset.json').read_text());gtiles={r['mask']:image(GROUND/r['file']) for r in gm['tiles']}
        grasses=[image(GROUND/p) for p in gm['materials']['grass']];dirt=[image(GROUND/p) for p in gm['materials']['dirt']]
        from tools.build_eldenmere_stone_paving_hd import compose
        scene=Image.new('RGBA',(960,768));mixed=0
        for y,row in enumerate(meta['cells']):
            for x,c in enumerate(row):
                tile=grasses[c['grass']].copy();mask=Image.new('L',(48,48))
                if c['dirt_fill'] is not None:tile=dirt[c['dirt_fill']].copy();mask=Image.new('L',(48,48),255)
                elif c['dirt_mask'] is not None:tile.alpha_composite(gtiles[c['dirt_mask']]);mask=gtiles[c['dirt_mask']].getchannel('A')
                phase=(x%2)+2*(y%2);self.assertEqual(c['texture_phase'],phase)
                m=c['paving_mask']
                if m is not None:
                    tile=compose(tile,self.bodies[m,phase],self.contacts[m,'grass'],self.contacts[m,'dirt'],mask)
                    mixed+=mask.getextrema()==(0,255)
                scene.alpha_composite(tile,(x*48,y*48))
        self.assertGreater(mixed,0);self.assertEqual(scene.tobytes(),image(REVIEW/'layout_clean_native.png').tobytes())
        moss=image(REVIEW/'moss_native.png');scene.alpha_composite(moss);self.assertEqual(scene.tobytes(),image(REVIEW/'layout_native.png').tobytes())
    def test_moss_is_sparse_and_only_deposited_on_stone_mortar(self):
        body=image(REVIEW/'stone_body_native.png');moss=image(REVIEW/'moss_native.png');joint={tuple(bytes.fromhex(self.rec['palette']['stone'][n][1:]))+(255,) for n in ('joint','shadow')}
        count=0
        for y in range(moss.height):
            for x in range(moss.width):
                if moss.getpixel((x,y))[3]:self.assertIn(body.getpixel((x,y)),joint);count+=1
        self.assertGreater(count,12)
        for path in self.meta['moss_accents']:
            patch=image(PACK/path);self.assertEqual(patch.size,(24,24));count=sum(bool(a) for a in patch.getchannel('A').tobytes());self.assertGreater(count,0);self.assertLess(count,144)
    def test_sources_output_hashes_and_deterministic_export(self):
        for r in self.rec['sources']:self.assertEqual(sha256((SOURCE/r['file']).read_bytes()).hexdigest(),r['sha256'])
        for r in json.loads((REVIEW/'exports.json').read_text())['outputs']:self.assertEqual(sha256((ROOT/r['file']).read_bytes()).hexdigest(),r['sha256'])
        from tools.build_eldenmere_stone_paving_hd import build
        for path in build(check=True):self.assertTrue(path.startswith(('assets/terrain/eldenmere/stone_paving_hd/','docs/reviews/eldenmere_hd_stone/')),path)
if __name__=='__main__':unittest.main()
