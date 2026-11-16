"""Directed HD waterworks: ports, flow ownership, elevation and reconstruction."""
from hashlib import sha256
import json
from pathlib import Path
import unittest
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1];PACK=ROOT/'assets/terrain/eldenmere/waterworks_hd';SOURCE=ROOT/'assets/source/terrain/eldenmere/waterworks_hd';REVIEW=ROOT/'docs/reviews/eldenmere_waterworks_hd'
PORTS={'N':1,'E':2,'S':4,'W':8};OPPOSITE={'N':'S','S':'N','E':'W','W':'E'}
def im(path):
    with Image.open(path) as source:return source.convert('RGBA')
def gray(path):
    with Image.open(path) as source:return source.convert('L')
def edge(image,d):return image.crop({'N':(0,0,48,1),'S':(0,47,48,48),'W':(0,0,1,48),'E':(47,0,48,48)}[d]).tobytes()
def ports(record):return [p for p,bit in PORTS.items() if record['ports']&bit]
class WaterworksHDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((PACK/'tileset.json').read_text());cls.rec=json.loads((SOURCE/'recipe.json').read_text());cls.records=cls.meta['channel_routes'];cls.images={(r['style'],r['id'],phase):im(PACK/path) for r in cls.records for phase,path in enumerate(r['frames'])}
    def test_units_status_and_inventory(self):
        m=self.meta;self.assertEqual(m['artwork_pixels_per_world_pixel'],2);self.assertEqual(m['logical_tile_size'],[24,24]);self.assertEqual(m['artwork_tile_size'],[48,48]);self.assertEqual(m['port_bits'],PORTS);self.assertEqual(m['integration_status'],'not_integrated');self.assertEqual(m['visual_approval'],'not_reviewed_by_user')
        self.assertEqual(len(self.records),120);self.assertEqual(len(m['spillways']),3);self.assertEqual(m['animation']['cycle_ms'],1200);self.assertTrue((PACK/m['palette']).is_file())
    def test_all_cardinal_route_inputs_and_outputs_are_complete(self):
        for style in self.meta['channel_treatments']:
            records=[r for r in self.records if r['style']==style];self.assertEqual(len(records),40)
            for mask in range(1,16):
                expected={p for p,bit in PORTS.items() if mask&bit};routes=[r for r in records if r['kind']=='channel' and r['ports']==mask];self.assertEqual({r['input'] for r in routes},expected)
                for r in routes:self.assertEqual(set(r['outputs']),expected-{r['input']});self.assertEqual(r['water_width_logical'],8)
            self.assertEqual(len([r for r in records if r['kind']=='inlet']),4);self.assertEqual(len([r for r in records if r['kind']=='outlet']),4)
    def test_geometry_only_envelopes_are_exact_at_twofold_density(self):
        for r in self.rec['geometry']:
            original=gray(SOURCE/r['file']).resize(tuple(n*2 for n in r['logical_size']),Image.Resampling.NEAREST);self.assertLessEqual(set(original.tobytes()),{0,255})
            if r['id']=='spillway_south':
                for spill in self.meta['spillways']:
                    exported=gray(PACK/spill['water_mask']) if r['kind']=='water' else im(PACK/spill['structure']).getchannel('A');self.assertEqual(exported.tobytes(),original.tobytes())
            else:
                for route in self.records:
                    prefix=f"shape_{route['ports']:02}" if route['kind']=='channel' else route['id']
                    if prefix==r['id']:
                        exported=gray(PACK/route['water_mask']) if r['kind']=='water' else im(PACK/route['bank']).getchannel('A');self.assertEqual(exported.tobytes(),original.tobytes())
    def test_all_compatible_same_treatment_ports_match_in_every_phase(self):
        joins=0
        for style in self.meta['channel_treatments']:
            records=[r for r in self.records if r['style']==style]
            for a in records:
                for direction in ports(a):
                    for b in records:
                        if OPPOSITE[direction] not in ports(b):continue
                        # Physical ports are compatible even when flow reverses;
                        # coherent routing additionally requires output -> input.
                        for phase in range(6):self.assertEqual(edge(self.images[style,a['id'],phase],direction),edge(self.images[style,b['id'],phase],OPPOSITE[direction]),(style,a['id'],b['id'],direction,phase))
                        joins+=1
        self.assertGreater(joins,2000)
    def test_animation_changes_only_water_or_declared_airborne_outlet_effects(self):
        for r in self.records:
            mask=gray(PACK/r['water_mask']);allowed=mask.copy()
            if r['kind']=='outlet':
                x,y,w,h=r['effect_bounds'];allowed.paste(255,(x*2,y*2,(x+w)*2,(y+h)*2))
            fixed=im(PACK/r['still']);bank=im(PACK/r['bank']);self.assertLessEqual(set(bank.getchannel('A').tobytes()),{0,255})
            for phase,path in enumerate(r['frames']):
                image=self.images[r['style'],r['id'],phase];diff=ImageChops.difference(image,fixed).convert('RGB');outside=ImageChops.multiply(diff.convert('L'),ImageChops.invert(allowed));self.assertIsNone(outside.getbbox(),r['id'])
                for y in range(48):
                    for x in range(48):
                        if bank.getpixel((x,y))[3]:self.assertEqual(image.getpixel((x,y)),bank.getpixel((x,y)))
    def test_outlet_droplets_move_inside_declared_bounds_and_cross_air_gap(self):
        for r in [r for r in self.records if r['kind']=='outlet' and r['style']=='earth']:
            mask=gray(PACK/r['water_mask']);air=[]
            for path in r['flow_frames']:
                alpha=im(PACK/path).getchannel('A');alpha=ImageChops.multiply(alpha,ImageChops.invert(mask));air.append(alpha)
            self.assertTrue(all(a.getbbox() for a in air[:4]));self.assertTrue(all(a.getbbox() is None for a in air[4:]));self.assertGreater(len({a.tobytes() for a in air}),3)
            centers=[]
            for a in air[:4]:
                points=[(x,y) for y in range(48) for x in range(48) if a.getpixel((x,y))];axis=1 if r['direction'] in ('N','S') else 0;centers.append(sum(p[axis] for p in points)/len(points))
            expected=1 if r['direction'] in ('S','E') else -1;self.assertGreater((centers[-1]-centers[0])*expected,4)
    def test_channel_flow_moves_in_four_directions_and_has_explicit_static_alternative(self):
        for direction,incoming in OPPOSITE.items():
            mask=PORTS[direction]|PORTS[incoming];r=next(r for r in self.records if r['style']=='earth' and r['kind']=='channel' and r['ports']==mask and r['input']==incoming);sequence=[im(PACK/p) for p in r['flow_frames']];self.assertEqual(len({p.tobytes() for p in sequence}),6)
            self.assertTrue((PACK/r['still']).is_file())
            # Outgoing half of a straight channel progresses toward its port.
            centers=[]
            for image in sequence[1:5]:
                coords=[]
                for y in range(48):
                    for x in range(48):
                        q=y if direction in ('N','S') else x
                        if image.getpixel((x,y))[3] and (q<24 if direction in ('N','W') else q>=24):coords.append(q)
                centers.append(sum(coords)/len(coords))
            self.assertGreater((centers[-1]-centers[1])*(1 if direction in ('S','E') else -1),6)
    def test_spillway_rise_ports_and_fixed_structure_reconstruction(self):
        for r in self.meta['spillways']:
            self.assertEqual(r['logical_size'],[24,48]);self.assertEqual(r['elevation_change_logical'],24);self.assertEqual(r['upper_landing'],'N');self.assertEqual(r['lower_landing'],'S');self.assertEqual(r['ports']['N']['water_interval_logical'],[8,16]);self.assertEqual(r['ports']['S']['water_interval_logical'],[8,16]);self.assertEqual(r['ports']['N']['elevation_logical'],24);self.assertEqual(r['ports']['S']['elevation_logical'],0)
            mask=gray(PACK/r['water_mask']);structure=im(PACK/r['structure']);self.assertIsNone(ImageChops.multiply(mask,structure.getchannel('A')).getbbox())
            for phase,path in enumerate(r['frames']):
                image=im(PACK/path);self.assertEqual(image.size,(48,96));effect=im(PACK/r['flow_frames'][phase]);self.assertEqual(ImageChops.multiply(effect.getchannel('A'),mask).tobytes(),effect.getchannel('A').tobytes())
                for y in range(96):
                    for x in range(48):
                        if structure.getpixel((x,y))[3]:self.assertEqual(image.getpixel((x,y)),structure.getpixel((x,y)))
                for row in (0,95):self.assertEqual(image.crop((16,row,32,row+1)).tobytes(),self.images['maintained','channel_05_from_n',phase].crop((16,0,32,1)).tobytes())
    def test_fall_streaks_progress_downward(self):
        for r in self.meta['spillways']:
            sequence=[im(PACK/p) for p in r['flow_frames']]
            down=up=0
            for a,b in zip(sequence,sequence[1:]):
                for y in range(20,54):
                    for x in range(20,28):
                        if a.getpixel((x,y))[3]:
                            down+=bool(b.getpixel((x,y+4))[3]);up+=bool(b.getpixel((x,y-4))[3])
            self.assertGreater(down,up)
    def test_native_scene_reconstructs_from_recorded_placements(self):
        from tools.build_world_water_hd import clipped,rgba
        layout=json.loads((REVIEW/'layout.json').read_text());ground=ROOT/'assets/terrain/eldenmere/grass_dirt_hd';gm=json.loads((ground/'tileset.json').read_text());grass=[im(ground/p) for p in gm['materials']['grass']];earth=im(ground/gm['materials']['dirt'][0]);natural=ROOT/'assets/terrain/water_hd'
        for phase in range(6):
            scene=Image.new('RGBA',tuple(layout['size_artwork']))
            for y in range(14):
                for x in range(20):scene.alpha_composite(grass[(x//3+y//4)%4],(x*48,y*48))
            for fixture in layout['placements']:
                ox,oy=fixture['origin_artwork'];style=fixture['style']
                for y in range(3):
                    for x in range(5):scene.alpha_composite(earth,(ox+x*48,oy+y*48))
                wall=im(ROOT/f'assets/terrain/eldenmere/terraces_hd/modules/{style}/wall_front_01.png')
                for x,y in fixture['wall_cells']:scene.alpha_composite(wall,(ox+x*48,oy+y*48))
                for tile in fixture['source_stream_tiles']:
                    x,y=tile['cell'];mask=tile['mask'];spatial=((ox//48+x)%2)+2*((oy//48+y)%2);water=im(natural/f'surfaces/temperate/deep_0_{spatial}/frame_{phase:02}.png');source=clipped(water,gray(natural/f'masks/water_{mask:03}.png'));source.alpha_composite(im(natural/f'banks/earth/0/mask_{mask:03}.png'));scene.alpha_composite(source,(ox+x*48,oy+y*48))
                for r in fixture['channel_cells']:
                    x,y=r['cell'];scene.alpha_composite(self.images[fixture['channel_style'],r['route'],phase],(ox+x*48,oy+y*48))
                spill=next(r for r in self.meta['spillways'] if r['style']==style);scene.alpha_composite(im(PACK/spill['frames'][phase]),tuple(fixture['spillway_position_artwork']));scene.alpha_composite(im(ROOT/'assets/characters/caelan/review_hd/idles/idle_front.png'),tuple(fixture['character_position_artwork']))
            self.assertEqual(scene.tobytes(),im(REVIEW/'scene'/f'frame_{phase:02}.png').tobytes())
    def test_route_atlases_reconstruct_every_frame(self):
        for style in self.meta['channel_treatments']:
            records=[r for r in self.records if r['style']==style]
            for phase in range(6):
                atlas=im(PACK/f'atlases/{style}_{phase:02}.png');self.assertEqual(atlas.size,(384,240))
                for index,r in enumerate(records):
                    x,y=index%8*48,index//8*48;self.assertEqual(atlas.crop((x,y,x+48,y+48)).tobytes(),self.images[style,r['id'],phase].tobytes())
    def test_review_route_reachability_and_actual_connections(self):
        layout=json.loads((REVIEW/'layout.json').read_text())
        for fixture in layout['placements']:
            style=fixture['channel_style'];cells={tuple(r['cell']):next(e for e in self.records if e['style']==style and e['id']==r['route']) for r in fixture['channel_cells']};self.assertIn((2,2),cells);self.assertIn((2,5),cells)
            # Traverse source intake -> bends -> fall -> receiver outlet.
            path=[(1,0),(1,1),(2,1),(2,2),'fall',(2,5),(2,6)]
            for a,b in zip(path,path[1:]):
                if a=='fall':self.assertEqual(cells[b]['input'],'N');continue
                if b=='fall':self.assertIn('S',cells[a]['outputs']);continue
                dx,dy=b[0]-a[0],b[1]-a[1];direction={(0,1):'S',(1,0):'E'}[dx,dy];self.assertIn(direction,cells[a]['outputs']);self.assertEqual(cells[b]['input'],OPPOSITE[direction])
            self.assertEqual(cells[path[-1]]['outputs'],['receiver'])
    def test_gif_pixels_and_timing_match_native_review_frames(self):
        with Image.open(REVIEW/'terrace_waterworks.gif') as sequence:
            self.assertEqual(sequence.n_frames,6);total=0
            for phase in range(6):sequence.seek(phase);total+=sequence.info['duration'];self.assertEqual(sequence.convert('RGB').tobytes(),im(REVIEW/'scene'/f'frame_{phase:02}.png').convert('RGB').tobytes())
            self.assertEqual(total,1200)
    def test_hashes_dependencies_and_scoped_reproducibility(self):
        for r in self.rec['geometry']:self.assertEqual(sha256((SOURCE/r['file']).read_bytes()).hexdigest(),r['sha256'])
        for r in self.rec['source_dependencies']:self.assertEqual(sha256((ROOT/r['file']).read_bytes()).hexdigest(),r['sha256'])
        for r in json.loads((REVIEW/'exports.json').read_text())['outputs']:self.assertEqual(sha256((ROOT/r['file']).read_bytes()).hexdigest(),r['sha256'])
        from tools.build_eldenmere_waterworks_hd import build
        for path in build(check=True):self.assertTrue(path.startswith(('assets/terrain/eldenmere/waterworks_hd/','docs/reviews/eldenmere_waterworks_hd/')))
if __name__=='__main__':unittest.main()
