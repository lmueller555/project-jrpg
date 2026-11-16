"""Staged vegetation geometry, silhouettes, fixed supports and review evidence."""
from hashlib import sha256
import json
from pathlib import Path
import unittest
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1];PACK=ROOT/'assets/terrain/vegetation_hd';SOURCE=ROOT/'assets/source/terrain/vegetation_hd';REVIEW=ROOT/'docs/reviews/world_vegetation_hd'
def im(path):
    with Image.open(path) as source:return source.convert('RGBA')
def gray(path):
    with Image.open(path) as source:return source.convert('L')
def colors(image):
    raw=image.tobytes();return {tuple(raw[i:i+4]) for i in range(0,len(raw),4) if raw[i+3]}
class VegetationHDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((PACK/'plants.json').read_text());cls.rec=json.loads((SOURCE/'recipe.json').read_text());cls.items={r['id']:r for r in cls.meta['plants']};cls.idles={name:im(PACK/r['idle']) for name,r in cls.items.items()};cls.frames={name:[im(PACK/f['file']) for f in r['frames']] for name,r in cls.items.items()}
    def test_explicit_units_status_inventory_and_three_variants_per_family(self):
        m=self.meta;self.assertEqual(m['artwork_pixels_per_world_pixel'],2);self.assertEqual(m['logical_tile_size'],[24,24]);self.assertEqual(m['integration_status'],'not_integrated');self.assertEqual(m['visual_approval'],'not_reviewed_by_user');self.assertEqual(m['design_count'],51);self.assertEqual(m['family_count'],17)
        self.assertEqual(sum(r['animated'] for r in self.items.values()),36)
        for family,ids in m['families'].items():
            self.assertEqual(len(ids),3);self.assertEqual(len({self.idles[name].tobytes() for name in ids}),3,family);self.assertEqual(len({self.idles[name].getchannel('A').tobytes() for name in ids}),3,family)
        self.assertTrue(all(r['interaction_cues'] is False for r in self.items.values()))
    def test_canvases_anchors_and_existing_scale_contracts(self):
        for name,r in self.items.items():
            image=self.idles[name];self.assertEqual(list(image.size),r['artwork_size']);self.assertEqual([v*2 for v in r['logical_size']],r['artwork_size']);self.assertEqual([v*2 for v in r['draw_anchor_logical']],r['root_anchor_artwork']);self.assertEqual(r['depth_baseline_logical'],r['draw_anchor_logical'][1])
            gx,gy,gw,gh=r['ground_rect_logical'];ax,ay=r['draw_anchor_logical'];self.assertTrue(gx<=ax<=gx+gw and gy<=ay<=gy+gh,name)
            if r['animation_kind']=='local_leaf_clusters':self.assertEqual(r['logical_size'],[96,120]);self.assertEqual(r['ground_rect_logical'],[36,96,24,24])
            elif r['family']=='tall_reeds':self.assertEqual(r['logical_size'],[24,48])
            elif r['family'] in ('shrub','grass','flowers'):self.assertEqual(r['logical_size'],[24,24])
    def test_hard_alpha_palette_no_key_color_and_clear_canvas_margins(self):
        allowed={tuple(bytes.fromhex(c[1:]))+(255,) for ramp in self.rec['palette'].values() for c in ramp.values()}
        for name,sequence in self.frames.items():
            for image in sequence:
                self.assertLessEqual(set(image.getchannel('A').tobytes()),{0,255});self.assertLessEqual(colors(image),allowed,name);self.assertNotIn((255,0,255,255),colors(image));box=image.getbbox();self.assertEqual(list(self.idles[name].getbbox()),self.items[name]['occupied_rect_artwork']);self.assertTrue(box[0]>0 and box[1]>0 and box[2]<image.width and box[3]<image.height,name)
    def test_native_detail_exceeds_uniform_twofold_old_pixels(self):
        for name,image in self.idles.items():
            fine=sum(len({image.getpixel((x+dx,y+dy)) for dx in (0,1) for dy in (0,1)})>1 for y in range(0,image.height,2) for x in range(0,image.width,2));self.assertGreater(fine,15,name)
    def test_single_artwork_pixel_silhouette_contour(self):
        color=tuple(bytes.fromhex(self.rec['palette']['outline']['base'][1:]))+(255,)
        from PIL import ImageFilter
        for name,image in self.idles.items():
            alpha=image.getchannel('A');boundary=ImageChops.subtract(alpha,alpha.filter(ImageFilter.MinFilter(3)))
            for y in range(image.height):
                for x in range(image.width):
                    if boundary.getpixel((x,y)):self.assertEqual(image.getpixel((x,y)),color,name)
    def test_idle_is_exact_first_frame_and_sheet_reconstructs_every_pose(self):
        for name,r in self.items.items():
            idle=self.idles[name];self.assertEqual(self.frames[name][0].tobytes(),idle.tobytes());sheet=im(PACK/r['sheet']);self.assertEqual(sheet.size,(idle.width*len(r['frames']),idle.height))
            for image,f in zip(self.frames[name],r['frames']):
                x,y,w,h=f['sheet_rect_artwork'];self.assertEqual(sheet.crop((x,y,x+w,y+h)).tobytes(),image.tobytes())
    def test_packed_idle_atlas_is_exact_and_rectangles_do_not_overlap(self):
        atlas=im(PACK/'idle_atlas.png');rectangles=[]
        for name,r in self.items.items():
            x,y,w,h=r['atlas_rect_artwork'];self.assertTrue(0<=x<x+w<=atlas.width and 0<=y<y+h<=atlas.height);self.assertEqual(atlas.crop((x,y,x+w,y+h)).tobytes(),self.idles[name].tobytes())
            for a,b,c,d in rectangles:self.assertFalse(x<a+c and a<x+w and y<b+d and b<y+h)
            rectangles.append((x,y,w,h))
    def test_trunks_roots_and_supports_stay_fixed(self):
        for name,r in self.items.items():
            if not r['animated']:continue
            idle=self.idles[name];fixed=im(PACK/r['fixed']);mask=fixed.getchannel('A');self.assertTrue(mask.getbbox(),name)
            for image in self.frames[name]:
                # Paste over a common blank to compare only the fixed authored support.
                self.assertEqual(Image.composite(image,Image.new('RGBA',image.size),mask).tobytes(),fixed.tobytes(),name)
                row=r['fixed_rows_from_artwork'];self.assertEqual(image.crop((0,row,image.width,image.height)).tobytes(),idle.crop((0,row,idle.width,idle.height)).tobytes(),name)
    def test_wind_is_local_horizontal_and_loop_registration_is_stable(self):
        for name,r in self.items.items():
            sequence=self.frames[name]
            if not r['animated']:self.assertEqual(len(sequence),1);self.assertIsNone(r['wind']['cycle_ms']);continue
            self.assertEqual(len(sequence),9);self.assertEqual(sum(f['duration_ms'] for f in r['frames']),5400);self.assertGreater(len({i.tobytes() for i in sequence}),1,name);self.assertEqual(sequence[-1].tobytes(),sequence[0].tobytes(),name);self.assertEqual(r['wind']['max_displacement_artwork'],1)
            idle=self.idles[name]
            for image in sequence:
                self.assertEqual(image.getbbox()[1::2],idle.getbbox()[1::2],name)
                if r['animation_kind']=='local_leaf_clusters':self.assertEqual(image.getchannel('A').tobytes(),idle.getchannel('A').tobytes(),name)
    def test_tree_layers_reconstruct_all_frames_and_preserve_wood(self):
        from tools.build_world_vegetation_hd import tree_frame
        for name,r in self.items.items():
            if r['animation_kind']!='local_leaf_clusters':continue
            native=self.idles[name];fixed=im(PACK/r['fixed']);back=im(PACK/r['backing']);parts=[{'id':p['id'],'image':im(PACK/p['file']),'position_artwork':p['position_artwork'],'delay':p['phase_delay']} for p in r['clusters']];self.assertGreaterEqual(len(parts),1)
            for phase,image in enumerate(self.frames[name]):self.assertEqual(tree_frame(native,fixed,back,parts,phase).tobytes(),image.tobytes())
    def test_review_gif_timeline_matches_png_frames_losslessly(self):
        for name,folder in [('trees','trees'),('small_plants','small_plants'),('eldenmere','scenes/eldenmere'),('northern_woodland','scenes/northern_woodland'),('wetland','scenes/wetland')]:
            expected=[im(REVIEW/folder/f'frame_{phase:02}.png').convert('RGB').tobytes() for phase in range(9)];decoded=[]
            with Image.open(REVIEW/(name+'.gif')) as animation:
                total=0
                for phase in range(animation.n_frames):
                    animation.seek(phase);duration=animation.info['duration'];self.assertEqual(duration%600,0);decoded.extend([animation.convert('RGB').tobytes()]*(duration//600));total+=duration
            self.assertEqual(total,5400);self.assertEqual(decoded,expected,name)
    def test_scene_reconstruction_depth_sort_and_registered_root_placements(self):
        from tools.build_world_water_hd import clipped
        layout=json.loads((REVIEW/'layout.json').read_text());ground=ROOT/'assets/terrain/eldenmere/grass_dirt_hd';gm=json.loads((ground/'tileset.json').read_text());grass=[im(ground/p) for p in gm['materials']['grass']];earth=im(ground/gm['materials']['dirt'][0]);water=ROOT/'assets/terrain/water_hd'
        # First and peak-breeze phases check roots, layer ownership and occlusion.
        for fixture in layout['scenes']:
            cells={tuple(r['cell']):r for r in fixture['water_cells']}
            for phase in (0,2):
                scene=Image.new('RGBA',tuple(fixture['size_artwork']))
                for y in range(14):
                    for x in range(20):
                        tile=earth.copy() if 8<=x<=10 else grass[(x//4+y//3)%4].copy()
                        if (x,y) in cells:
                            c=cells[x,y];mask=c['mask'];source=im(water/f"surfaces/{fixture['water_family']}/deep_0_{c['texture_phase']}/still.png");tile.alpha_composite(clipped(source,gray(water/f'masks/water_{mask:03}.png')));tile.alpha_composite(im(water/f"banks/{fixture['bank_family']}/0/mask_{mask:03}.png"))
                        scene.alpha_composite(tile,(x*48,y*48))
                def plant(p):
                    r=self.items[p['id']];image=self.frames[p['id']][(phase+p['phase_offset'])%9] if r['animated'] else self.idles[p['id']];x,y=p['root_artwork'];ax,ay=r['root_anchor_artwork'];scene.alpha_composite(image,(x-ax,y-ay))
                for p in fixture['placements']:
                    if p['layer']=='ground':plant(p)
                entries=[(p['root_artwork'][1],0,p) for p in fixture['placements'] if p['layer']!='ground']+[(a['root_artwork'][1],1,a) for a in fixture['actors']]
                for _,kind,p in sorted(entries,key=lambda e:(e[0],e[1])):
                    if kind:scene.alpha_composite(im(ROOT/p['file']),(p['root_artwork'][0]-p['anchor_artwork'][0],p['root_artwork'][1]-p['anchor_artwork'][1]))
                    else:plant(p)
                self.assertEqual(scene.tobytes(),im(REVIEW/'scenes'/fixture['id']/f'frame_{phase:02}.png').tobytes())
    def test_grass_remains_decorative_and_has_no_implicit_gameplay_registration(self):
        for r in self.items.values():
            self.assertIn('not_registered',r['collision']);self.assertFalse(r['interaction_cues'])
            if r['family']=='grass':self.assertIn('shared contact-responsive grass is unchanged',r['contact_behavior'])
        self.assertIn('No maps',self.meta['activation']);self.assertIn('pause/focus',self.meta['integration_followup'])
    def test_source_hashes_outputs_and_deterministic_scoped_export(self):
        for r in self.rec['sources']:self.assertEqual(sha256((SOURCE/r['file']).read_bytes()).hexdigest(),r['sha256'])
        for r in json.loads((REVIEW/'exports.json').read_text())['outputs']:self.assertEqual(sha256((ROOT/r['file']).read_bytes()).hexdigest(),r['sha256'])
        from tools.build_world_vegetation_hd import build
        expected=build(check=True)
        for path in expected:self.assertTrue(path.startswith(('assets/terrain/vegetation_hd/','docs/reviews/world_vegetation_hd/')))
        actual={p.relative_to(ROOT).as_posix() for directory in (PACK,REVIEW) for p in directory.rglob('*') if p.is_file() and p.name not in ('README.md','preservation.json')};self.assertEqual(actual,set(expected))
if __name__=='__main__':unittest.main()
