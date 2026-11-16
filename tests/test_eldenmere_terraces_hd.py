"""Geometry, joins and reproducibility for the staged elevation bank."""
from hashlib import sha256
import json
from pathlib import Path
import unittest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/terraces_hd'
SOURCE=ROOT/'assets/source/terrain/eldenmere/terraces_hd'
REVIEW=ROOT/'docs/reviews/eldenmere_hd_terraces'
def image(path):
    with Image.open(path) as im:return im.convert('RGBA')
def edge(im,d):return im.crop({'N':(0,0,48,1),'S':(0,47,48,48),'W':(0,0,1,48),'E':(47,0,48,48)}[d]).tobytes()
class TerraceHDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((PACK/'tileset.json').read_text());cls.rec=json.loads((SOURCE/'recipe.json').read_text())
    def test_explicit_units_status_and_inventory(self):
        m=self.meta;self.assertEqual(m['artwork_pixels_per_world_pixel'],2);self.assertEqual(m['logical_tile_size'],[24,24]);self.assertEqual(m['artwork_tile_size'],[48,48])
        self.assertEqual(m['integration_status'],'not_integrated');self.assertEqual(m['visual_approval'],'not_reviewed_by_user')
        for key,count in [('wall_modules',42),('stair_variants',4),('landings',48),('terrace_prefabs',9)]:self.assertEqual(len(m[key]),count)
    def test_wall_coverage_preserves_logical_geometry(self):
        for r in self.meta['wall_modules']:
            with Image.open(SOURCE/r['logical_coverage_source']) as source:mask=source.convert('L').resize((48,48),Image.Resampling.NEAREST)
            im=image(PACK/r['file']);self.assertEqual(im.getchannel('A').tobytes(),mask.tobytes(),r['id']);self.assertEqual(im.size,(48,48))
            self.assertEqual(r['logical_size'],[24,24]);self.assertEqual(r['height_logical'],24)
    def test_atlas_reconstruction(self):
        for r in self.meta['wall_modules']:
            x,y,w,h=r['rect'];self.assertEqual(image(PACK/r['atlas']).crop((x,y,x+w,y+h)).tobytes(),image(PACK/r['file']).tobytes())
    def test_every_declared_wall_port_joins_across_styles(self):
        ports={}
        for r in self.meta['wall_modules']:
            im=image(PACK/r['file'])
            for d,kind in r['ports'].items():ports.setdefault(kind,[]).append((r['id'],d,edge(im,d)))
        for kind,values in ports.items():
            reference=values[0][2]
            for name,d,data in values:self.assertEqual(reference,data,(kind,name,d))
    def test_new_wall_and_stair_detail_palette_and_variation(self):
        allowed={tuple(bytes.fromhex(c[1:]))+(255,) for ramp in self.rec['palette'].values() for c in ramp.values()}
        paths=[r['file'] for r in self.meta['wall_modules']+self.meta['stair_variants']]
        for path in paths:
            im=image(PACK/path);self.assertLessEqual(set(im.getchannel('A').tobytes()),{0,255})
            raw=im.tobytes();colors={tuple(raw[i:i+4]) for i in range(0,len(raw),4)};self.assertLessEqual({c for c in colors if c[3]},allowed,path)
        fronts=[image(PACK/r['file']) for r in self.meta['wall_modules'] if r['module'].startswith('wall_front_')]
        self.assertEqual(len({im.tobytes() for im in fronts}),9)
        steps=[image(PACK/r['file']) for r in self.meta['stair_variants']];self.assertEqual(len({im.tobytes() for im in steps}),4)
        for im in fronts+steps:
            fine=sum(len({im.getpixel((x+dx,y+dy)) for dx in (0,1) for dy in (0,1)})>1 for y in range(0,im.height,2) for x in range(0,im.width,2))
            self.assertGreater(fine,40)
    def test_stair_geometry_and_quarter_reconstruction(self):
        for r in self.meta['stair_variants']:
            self.assertEqual(r['logical_size'],[48,48]);self.assertEqual(r['walkable_rect_logical'],[7,0,34,48]);self.assertEqual(r['elevation_change_logical'],24)
            self.assertEqual(r['tread_count'],4);self.assertEqual((r['upper_landing'],r['lower_landing']),('N','S'));self.assertEqual(r['nosing_rows_artwork'],[18,36,54,72])
            result=Image.new('RGBA',(96,96))
            for i,path in enumerate(r['quarters']):result.alpha_composite(image(PACK/path),(i%2*48,i//2*48))
            self.assertEqual(result.tobytes(),image(PACK/r['file']).tobytes())
    def test_landing_contacts_and_paving_world_phase(self):
        steps={r['id']:image(PACK/r['file']) for r in self.meta['stair_variants']}
        paving=ROOT/'assets/terrain/eldenmere/stone_paving_hd';pm=json.loads((paving/'tileset.json').read_text())
        for r in self.meta['landings']:
            im=image(PACK/r['file']);step=steps[r['stair_variant']];self.assertEqual(im.size,(96,48))
            upper=r['end']=='upper';self.assertEqual(im.crop((0,47,96,48) if upper else (0,0,96,1)).tobytes(),step.crop((0,0,96,1) if upper else (0,95,96,96)).tobytes())
            if r['surface']=='paving':
                for col in (0,1):
                    phase=r['texture_phase']^col;tile=image(paving/pm['interior_phases'][phase]);box=(col*48,0 if upper else 6,(col+1)*48,42 if upper else 48)
                    self.assertEqual(im.crop(box).tobytes(),tile.crop((0,box[1],48,box[3])).tobytes())
    def test_prefab_stairs_landings_and_height(self):
        for r in self.meta['terrace_prefabs']:
            im=image(PACK/r['file']);self.assertEqual(im.size,(288,288));self.assertEqual(r['upper_elevation_logical'],24)
            self.assertEqual(r['top_rect_logical'],[0,0,144,72]);self.assertEqual(r['stair_rect_logical'],[48,72,48,48])
            self.assertEqual(im.crop((96,144,192,240)).tobytes(),image(PACK/('stairs/'+r['stair_variant']+'.png')).tobytes())
            for end,box,phase in [('upper',(96,96,192,144),0),('lower',(96,240,192,288),2 if r['top_surface']=='paving' else 0)]:
                path=f"landings/{r['stair_variant']}/{r['top_surface']}_{end}_phase_{phase}.png";self.assertEqual(im.crop(box).tobytes(),image(PACK/path).tobytes())
            for w in r['wall_instances']:
                x,y=w['position_artwork'];self.assertFalse(y==144 and x in (96,144))
    def test_hashes_and_reproducible_scoped_export(self):
        for r in self.rec['sources']+self.rec['logical_envelopes']:self.assertEqual(sha256((SOURCE/r['file']).read_bytes()).hexdigest(),r['sha256'])
        for r in json.loads((REVIEW/'exports.json').read_text())['outputs']:self.assertEqual(sha256((ROOT/r['file']).read_bytes()).hexdigest(),r['sha256'])
        from tools.build_eldenmere_terraces_hd import build
        for path in build(check=True):self.assertTrue(path.startswith(('assets/terrain/eldenmere/terraces_hd/','docs/reviews/eldenmere_hd_terraces/')))
if __name__=='__main__':unittest.main()
