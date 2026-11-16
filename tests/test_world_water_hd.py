"""Staged water bank: geometry, compatible joins, layer ownership and clocks."""
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import unittest
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1];PACK=ROOT/'assets/terrain/water_hd';SOURCE=ROOT/'assets/source/terrain/water_hd';REVIEW=ROOT/'docs/reviews/world_water_hd'
def im(path):
    with Image.open(path) as source:return source.convert('RGBA')
def gray(path):
    with Image.open(path) as source:return source.convert('L')
def canonical(raw):
    for d,a,b in ((2,1,4),(8,4,16),(32,16,64),(128,64,1)):
        if not (raw&a and raw&b):raw&=~d
    return raw
OFFSETS=((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1))
def neighborhood(cells,p):return canonical(sum(1<<i for i,(dx,dy) in enumerate(OFFSETS) if (p[0]+dx,p[1]+dy) in cells))
def edge(image,last,vertical):return image.crop((0,47,48,48) if last and vertical else (47,0,48,48) if last else (0,0,48,1) if vertical else (0,0,1,48)).tobytes()
class WorldWaterHDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((PACK/'tileset.json').read_text());cls.rec=json.loads((SOURCE/'recipe.json').read_text());cls.shapes={r['mask']:r for r in cls.meta['shapes']};cls.banks={(r['family'],r['arrangement'],r['mask']):im(PACK/r['file']) for r in cls.meta['bank_tiles']}
    def test_units_inventory_and_staged_status(self):
        m=self.meta;self.assertEqual(m['artwork_pixels_per_world_pixel'],2);self.assertEqual(m['logical_tile_size'],[24,24]);self.assertEqual(m['artwork_tile_size'],[48,48]);self.assertEqual(m['integration_status'],'not_integrated');self.assertEqual(m['visual_approval'],'not_reviewed_by_user')
        self.assertEqual(len(m['bank_tiles']),470);self.assertEqual(len(m['water_surfaces']),64);self.assertEqual(len(m['quarters']),20);self.assertEqual(len(m['current_overlays']),24);self.assertEqual(len(m['effect_overlays']),4)
    def test_all_neighborhoods_and_original_coverage(self):
        self.assertEqual(set(self.shapes),{canonical(raw) for raw in range(256)})
        for raw,index in enumerate(self.meta['lookup_256']):self.assertEqual(self.meta['shapes'][index]['mask'],canonical(raw))
        for r in self.rec['geometry']:
            original=gray(SOURCE/r['file']).resize((48,48),Image.Resampling.NEAREST);export=gray(PACK/f"masks/{r['kind']}_{r['mask']:03}.png");self.assertEqual(original.tobytes(),export.tobytes());self.assertLessEqual(set(export.tobytes()),{0,255})
        for key,bank in self.banks.items():self.assertEqual(bank.getchannel('A').tobytes(),gray(PACK/self.shapes[key[2]]['bank_mask']).tobytes())
    def test_shore_water_and_shallow_layers_have_no_holes_or_land_overlap(self):
        for r in self.shapes.values():
            w=gray(PACK/r['water_mask']);b=gray(PACK/r['bank_mask']);s=gray(PACK/r['shallow_mask'])
            self.assertIsNone(ImageChops.multiply(w,b).getbbox());self.assertEqual(ImageChops.multiply(w,s).tobytes(),s.tobytes());self.assertIsNotNone(ImageChops.lighter(w,b).getbbox())
    def test_all_2048_geometrically_compatible_joins_for_every_bank_treatment(self):
        count=0
        for vertical in (False,True):
            a=(0,0);b=(0,1) if vertical else (1,0);optional=sorted(({(p[0]+dx,p[1]+dy) for p in (a,b) for dx,dy in OFFSETS}|{a,b})-{a,b})
            for flags in product((False,True),repeat=len(optional)):
                cells={a,b}|{p for p,on in zip(optional,flags) if on};ma,mb=neighborhood(cells,a),neighborhood(cells,b)
                for family in self.meta['bank_families']:
                    for va,vb in ((0,0),(0,1),(1,0),(1,1)):self.assertEqual(edge(self.banks[family,va,ma],True,vertical),edge(self.banks[family,vb,mb],False,vertical),(family,ma,mb,vertical))
                for key in ('water_mask','shallow_mask','depth_control'):self.assertEqual(edge(gray(PACK/self.shapes[ma][key]),True,vertical),edge(gray(PACK/self.shapes[mb][key]),False,vertical),(key,ma,mb))
                count+=1
        self.assertEqual(count,2048)
    def test_quarters_and_atlases_reconstruct_tiles(self):
        from tools.build_eldenmere_grass_dirt_hd import QUARTERS,state
        qs={r['id']:r for r in self.meta['quarters']}
        for mask,r in self.shapes.items():
            for family in self.meta['bank_families']:
                for v in (0,1):
                    assembled=Image.new('RGBA',(48,48))
                    for orient,(x,y,h,vertical,d) in QUARTERS.items():
                        key=orient+'_'+state(bool(mask&self.meta['neighbor_bits'][h]),bool(mask&self.meta['neighbor_bits'][vertical]),bool(mask&self.meta['neighbor_bits'][d]));assembled.alpha_composite(im(PACK/qs[key]['banks'][family][v]),(x,y))
                    self.assertEqual(assembled.tobytes(),self.banks[family,v,mask].tobytes())
            for bank in [r for r in self.meta['bank_tiles'] if r['mask']==mask]:
                x,y,w,h=bank['rect'];self.assertEqual(im(PACK/bank['atlas']).crop((x,y,x+w,y+h)).tobytes(),self.banks[bank['family'],bank['arrangement'],mask].tobytes())
    def test_every_water_frame_has_compatible_spatial_and_arrangement_borders(self):
        groups={}
        for r in self.meta['water_surfaces']:
            for phase,f in enumerate(r['frames']):groups.setdefault((r['family'],r['depth'],phase),[]).append(im(PACK/f['file']))
        for group,images in groups.items():
            for image in images:
                for vertical in (False,True):self.assertEqual(edge(image,True,vertical),edge(images[0],False,vertical),group)
    def test_frames_keep_base_fixed_and_reduced_motion_uses_explicit_still(self):
        for r in self.meta['water_surfaces']:
            still=im(PACK/r['still']);sequence=[im(PACK/f['file']) for f in r['frames']];self.assertEqual(len(sequence),6);self.assertTrue(all(f['duration_ms']==200 for f in r['frames']));self.assertEqual(sequence[-1].tobytes(),still.tobytes())
            self.assertEqual(len({p.tobytes() for p in sequence}),6)
            for image in sequence:
                self.assertEqual(image.getchannel('A').getextrema(),(255,255));changed=sum(a!=b for a,b in zip(image.getdata(),still.getdata()));self.assertLess(changed,200)
        self.assertEqual(self.meta['animation']['cycle_ms'],1200)
    def test_palette_and_native_detail(self):
        for r in self.meta['water_surfaces']:
            allowed={tuple(bytes.fromhex(c[1:]))+(255,) for c in self.rec['water_palettes'][r['family']].values()}
            for f in r['frames']:self.assertLessEqual(set(im(PACK/f['file']).getdata()),allowed)
        for (family,v,mask),image in self.banks.items():
            allowed={tuple(bytes.fromhex(c[1:]))+(255,) for c in self.rec['bank_palettes'][family].values()};self.assertLessEqual({c for c in image.getdata() if c[3]},allowed)
        sample=im(PACK/self.meta['water_surfaces'][0]['still']);fine=sum(len({sample.getpixel((x+dx,y+dy)) for dx in (0,1) for dy in (0,1)})>1 for y in range(0,48,2) for x in range(0,48,2));self.assertGreater(fine,35)
    def test_mixed_bank_material_selection_and_junction_atlases(self):
        from tools.build_world_water_hd import mix_banks
        for a,b in self.meta['supported_bank_pairs']:
            for vertical in (False,True):
                selector=Image.new('L',(48,48));selector.paste(255,(0,24,48,48) if vertical else (24,0,48,48))
                atlas=im(PACK/f"junctions/{a}_{b}_{'y' if vertical else 'x'}.png")
                for mask,r in self.shapes.items():
                    result=mix_banks(self.banks[a,0,mask],self.banks[b,0,mask],selector,self.meta['mix_contact_color']);self.assertEqual(result.getchannel('A').tobytes(),self.banks[a,0,mask].getchannel('A').tobytes());x,y,w,h=r['rect'];self.assertEqual(atlas.crop((x,y,x+w,y+h)).tobytes(),result.tobytes())
    def test_currents_and_effects_move_without_changing_receiving_coverage(self):
        for r in self.meta['current_overlays']:
            sequence=[im(PACK/p) for p in r['frames']];self.assertEqual(len({p.tobytes() for p in sequence}),6)
            for image in sequence:
                self.assertLessEqual(set(image.getchannel('A').tobytes()),{0,255})
                for vertical in (False,True):self.assertFalse(any(edge(image,False,vertical)));self.assertFalse(any(edge(image,True,vertical)))
        for r in self.meta['effect_overlays']:self.assertEqual(im(PACK/r['frames'][-1]).getbbox(),None)
    def test_gif_frames_match_pngs_and_animation_timing(self):
        for name in ('eldenmere','mountain','lake','marsh'):
            with Image.open(REVIEW/(name+'.gif')) as animation:
                total=0;self.assertEqual(animation.n_frames,6)
                for frame in range(6):animation.seek(frame);total+=animation.info['duration'];self.assertEqual(animation.convert('RGB').tobytes(),im(REVIEW/name/f'frame_{frame:02}.png').convert('RGB').tobytes())
                self.assertEqual(total,1200)
    def test_sources_hashes_and_reproducible_scoped_exports(self):
        for r in self.rec['sources']+self.rec['geometry']:self.assertEqual(sha256((SOURCE/r['file']).read_bytes()).hexdigest(),r['sha256'])
        for r in json.loads((REVIEW/'exports.json').read_text())['outputs']:self.assertEqual(sha256((ROOT/r['file']).read_bytes()).hexdigest(),r['sha256'])
        from tools.build_world_water_hd import build
        for path in build(check=True):self.assertTrue(path.startswith(('assets/terrain/water_hd/','docs/reviews/world_water_hd/')))
if __name__=='__main__':unittest.main()
