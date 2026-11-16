"""Business art: glass stock, supports, registered entrances and staged plot plans."""
from hashlib import sha256
import json
from pathlib import Path
import unittest
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1];PACK=ROOT/'assets/terrain/eldenmere/business_exteriors_hd';SOURCE=ROOT/'assets/source/terrain/eldenmere/business_exteriors_hd';REVIEW=ROOT/'docs/reviews/eldenmere_business_exteriors_hd'
def im(path):
    with Image.open(path) as source:return source.convert('RGBA')
def gray(path):
    with Image.open(path) as source:return source.convert('L')
def colors(image):
    data=image.tobytes();return {tuple(data[i:i+4]) for i in range(0,len(data),4) if data[i+3]}
def palette(ramp):return {tuple(bytes.fromhex(c[1:]))+(255,) for c in ramp.values()}
class BusinessExteriorsHDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((PACK/'manifest.json').read_text());cls.rec=json.loads((SOURCE/'recipe.json').read_text());cls.items={r['id']:r for r in cls.meta['buildings']};cls.props={r['id']:r for r in cls.meta['props']}
    def test_inventory_units_status_and_geometry_shared_by_variants(self):
        m=self.meta;self.assertEqual(m['artwork_pixels_per_world_pixel'],2);self.assertEqual(m['integration_status'],'not_integrated');self.assertEqual(m['visual_approval'],'not_reviewed_by_user');self.assertEqual(len(self.items),4);self.assertEqual(len(self.props),6)
        for kind,size in [('inn',[192,240]),('item_shop',[168,192])]:
            a,b=[self.items[kind+'_'+v] for v in ('maintained','weathered')];self.assertEqual(a['logical_size'],size)
            for key in ('logical_size','ground_rect_logical','door_rect_logical'):self.assertEqual(a[key],b[key])
            self.assertNotEqual(im(PACK/a['closed']).tobytes(),im(PACK/b['closed']).tobytes())
        for r in self.items.values():self.assertEqual(r['artwork_size'],[v*2 for v in r['logical_size']]);self.assertEqual(list(im(PACK/r['closed']).size),r['artwork_size'])
    def test_doors_clear_shell_and_preserve_drawn_five_state_contract(self):
        for r in self.items.values():
            structure=im(PACK/r['structure']);x,y,w,h=[v*2 for v in r['door_rect_logical']];self.assertIsNone(structure.crop((x,y,x+w,y+h)).getbbox());frames=r['door']['frames'];self.assertEqual(len(frames),5);self.assertEqual(len({im(PACK/f['file']).tobytes() for f in frames}),5);self.assertFalse(r['door']['loop']);self.assertEqual(r['door']['closing_order'],[4,3,2,1,0])
            for f in frames:self.assertEqual(f['duration_ms'],100);self.assertEqual(im(PACK/f['file']).size,(w,h));self.assertEqual(im(PACK/f['file']).getchannel('A').getextrema(),(255,255))
    def test_closed_and_open_reconstruct_from_fixed_structure_door_sign_and_display(self):
        for r in self.items.values():
            for state,index in [('closed',0),('open',4)]:
                image=im(PACK/r['structure']);image.alpha_composite(im(PACK/r['door']['frames'][index]['file']),tuple(v*2 for v in r['door']['position_logical']))
                if r['display']:image.alpha_composite(im(PACK/r['display']['file']),tuple(v*2 for v in r['display']['rect_logical'][:2]))
                image.alpha_composite(im(PACK/self.props[r['sign']['prop']]['idle']),tuple(v*2 for v in r['sign']['position_logical']));self.assertEqual(image.tobytes(),im(PACK/r[state]).tobytes())
    def test_both_displays_have_four_potion_colors_and_weapon_armor_sections(self):
        sections=self.meta['display_sections'];self.assertEqual(len(sections),6)
        for variant in ('maintained','weathered'):
            display=im(PACK/f'displays/{variant}.png');self.assertEqual(display.size,(156,96))
            for family in ('potions','weapons','armor'):
                s=next(s for s in sections if s['variant']==variant and s['id']==family);x,y,w,h=s['rect_artwork'];image=display.crop((x,y,x+w,y+h));actual=colors(image)
                if family=='potions':
                    for color in ('red','blue','green','violet'):self.assertGreater(len(actual&palette(self.rec['palette']['potion_'+color])),0,(variant,color))
                    self.assertIn('round flasks',s['contents']);self.assertIn('square bottles',s['contents']);self.assertIn('conical vials',s['contents'])
                else:
                    self.assertGreater(len(actual&(palette(self.rec['palette']['steel'])|palette(self.rec['palette']['iron']))),1,(variant,family));self.assertEqual(s['contents'],['sword','round shield'] if family=='weapons' else ['helmet','breastplate'])
    def test_glass_stock_is_opaque_fixed_and_excluded_from_flicker(self):
        for r in self.items.values():
            if not r['display']:continue
            d=r['display'];self.assertEqual(d['inventory_binding'],'decorative_only');self.assertFalse(d['interaction_cues']);self.assertEqual(d['animation'],'none');x,y,w,h=[v*2 for v in d['rect_logical']];plate=im(PACK/d['file']);self.assertEqual(plate.getchannel('A').getextrema(),(255,255));self.assertIsNone(gray(PACK/r['window_mask']).crop((x,y,x+w,y+h)).getbbox());self.assertIsNone(im(PACK/r['structure']).crop((x,y,x+w,y+h)).getbbox())
            for f in r['ambient']['frames']:
                self.assertEqual(im(PACK/f['file']).crop((x,y,x+w,y+h)).tobytes(),plate.tobytes());self.assertIsNone(im(PACK/f['layers']['windowlight']).crop((x,y,x+w,y+h)).getbbox())
    def test_ambient_layers_reconstruct_and_supports_stay_registered(self):
        for r in self.items.values():
            frames=r['ambient']['frames'];self.assertEqual(len(frames),18);self.assertEqual(sum(f['duration_ms'] for f in frames),3600);self.assertEqual(r['ambient']['reduced_motion'],r['closed']);self.assertTrue(r['sign']['fixed_mount'])
            for f in frames:
                image=im(PACK/r['structure']);image.alpha_composite(im(PACK/r['door']['frames'][0]['file']),tuple(v*2 for v in r['door']['position_logical']))
                if r['display']:image.alpha_composite(im(PACK/r['display']['file']),tuple(v*2 for v in r['display']['rect_logical'][:2]))
                for layer in ('windowlight','awning','sign','smoke'):image.alpha_composite(im(PACK/f['layers'][layer]))
                self.assertEqual(image.tobytes(),im(PACK/f['file']).tobytes())
            if r['building_type']=='item_shop':
                self.assertTrue(all(im(PACK/f['layers']['smoke']).getbbox() is None for f in frames));self.assertGreater(len({im(PACK/f['layers']['awning']).tobytes() for f in frames}),1)
    def test_signs_sway_with_fixed_top_mount_and_other_props_are_static(self):
        for r in self.props.values():
            idle=im(PACK/r['idle']);self.assertEqual(list(idle.size),r['artwork_size']);self.assertEqual([v*2 for v in r['logical_size']],r['artwork_size']);frames=[im(PACK/p) for p in r['frames']];self.assertEqual(frames[0].tobytes(),idle.tobytes())
            if r['animation']=='static':self.assertEqual(len(frames),1);continue
            self.assertEqual(len(frames),18);self.assertEqual(r['cycle_ms'],3600);self.assertGreater(len({f.tobytes() for f in frames}),1)
            for image in frames:self.assertEqual(image.crop((0,0,image.width,12)).tobytes(),idle.crop((0,0,idle.width,12)).tobytes())
        self.assertEqual(self.props['travel_boots']['logical_size'],[12,12])
    def test_hard_alpha_palette_and_native_detail(self):
        allowed=set().union(*(palette(p) for p in self.rec['palette'].values()),*(palette(p) for p in self.rec['roof_palettes'].values()))
        for r in self.items.values():
            image=im(PACK/r['closed']);self.assertLessEqual(set(image.getchannel('A').tobytes()),{0,255});self.assertLessEqual(colors(image),allowed);fine=sum(len({image.getpixel((x+dx,y+dy)) for dx in (0,1) for dy in (0,1)})>1 for y in range(0,image.height,2) for x in range(0,image.width,2));self.assertGreater(fine,500)
        for variant in ('maintained','weathered'):self.assertNotIn((255,0,255,255),colors(im(PACK/f'displays/{variant}.png')))
    def test_candidate_plots_align_with_entries_and_retained_collision_snapshots(self):
        self.assertEqual(len(self.meta['candidate_placements']),2);self.assertEqual(len(self.rec['placement_checks']),7)
        for p in self.meta['candidate_placements']:
            r=self.items[p['design']];ox,oy=p['position_logical'];x,y,w,h=r['ground_rect_logical'];self.assertEqual(p['ground_rect_world_logical'],[ox+x,oy+y,w,h]);dx,dy,dw,dh=r['door_rect_logical'];self.assertEqual(p['entry_anchor_world_logical'],[ox+dx+dw/2,oy+r['logical_size'][1]+6]);self.assertEqual(p['proposed_path_centerline_logical'][0],p['entry_anchor_world_logical']);self.assertEqual(p['proposed_path_centerline_logical'][-1],p['connection_to_existing_lane_logical'])
            for a,b in zip(p['proposed_path_centerline_logical'],p['proposed_path_centerline_logical'][1:]):self.assertTrue(a[0]==b[0] or a[1]==b[1])
        for check in self.rec['placement_checks']:
            image=gray(SOURCE/check['file']);self.assertEqual(list(image.size),check['rect_world_logical'][2:]);self.assertEqual(image.getextrema(),(0,0));self.assertEqual(check['blocked_pixel_count'],0)
    def test_service_spec_is_future_work_and_does_not_sell_unique_story_gear(self):
        spec=json.loads((REVIEW/'integration_spec.json').read_text());self.assertEqual(spec['status'],'specification_only_not_implemented');self.assertEqual(spec['item_shop']['existing_consumable_ids'],['potion','ether','revival_salts','smoke_bomb','rest_kit']);self.assertIn('Never offer quest/key items',spec['item_shop']['gear']);self.assertIn('Mira',spec['item_shop']['gear']);self.assertIn('insufficient funds changes neither currency nor party state',spec['inn']['failure_cases']);self.assertIn('currency model and balance decisions',spec['shared_prerequisites'])
        self.assertTrue(all(not r['interaction_cues'] for r in list(self.items.values())+list(self.props.values())));self.assertIn('no live maps',self.meta['activation'])
    def test_native_street_scenes_reconstruct_at_character_scale(self):
        layout=json.loads((REVIEW/'layout.json').read_text());ground=ROOT/'assets/terrain/eldenmere/grass_dirt_hd';gm=json.loads((ground/'tileset.json').read_text());grass=[im(ground/p) for p in gm['materials']['grass']];dirt=im(ground/gm['materials']['dirt'][0])
        for f in layout['scenes']:
            scene=Image.new('RGBA',tuple(f['size_artwork']))
            for y in range(14):
                for x in range(20):scene.alpha_composite(dirt if 10<=y<=11 else grass[(x//4+y//3)%4],(x*48,y*48))
            for b in f['buildings']:scene.alpha_composite(im(PACK/self.items[b['id']]['closed']),tuple(b['position_artwork']))
            for a in f['actors']:scene.alpha_composite(im(ROOT/a['file']),tuple(a['position_artwork']))
            self.assertEqual(scene.tobytes(),im(REVIEW/('street_'+f['id']+'_native.png')).tobytes())
    def test_review_gif_timelines_match_native_frames_without_merchandise_flicker(self):
        for name in self.items:
            actual=[]
            with Image.open(REVIEW/(name+'.gif')) as sequence:
                total=0
                for frame in range(sequence.n_frames):sequence.seek(frame);duration=sequence.info['duration'];self.assertEqual(duration%200,0);actual.extend([sequence.convert('RGB').tobytes()]*(duration//200));total+=duration
            expected=[im(REVIEW/'ambient'/name/f'frame_{p:02}.png').convert('RGB').tobytes() for p in range(18)];self.assertEqual(total,3600);self.assertEqual(actual,expected)
    def test_sources_dependencies_and_scoped_reproducible_inventory(self):
        for r in self.rec['sources']+self.rec['placement_checks']:self.assertEqual(sha256((SOURCE/r['file']).read_bytes()).hexdigest(),r['sha256'])
        for r in self.rec['dependencies']:self.assertEqual(sha256((ROOT/r['file']).read_bytes()).hexdigest(),r['sha256'])
        for r in json.loads((REVIEW/'exports.json').read_text())['outputs']:self.assertEqual(sha256((ROOT/r['file']).read_bytes()).hexdigest(),r['sha256'])
        from tools.build_eldenmere_business_exteriors_hd import build
        expected=build(check=True)
        for path in expected:self.assertTrue(path.startswith(('assets/terrain/eldenmere/business_exteriors_hd/','docs/reviews/eldenmere_business_exteriors_hd/')))
        actual={p.relative_to(ROOT).as_posix() for folder in (PACK,REVIEW) for p in folder.rglob('*') if p.is_file() and p.name not in ('README.md','preservation.json')};self.assertEqual(actual,set(expected))
if __name__=='__main__':unittest.main()
