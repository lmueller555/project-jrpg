"""Staged architecture: preserved entrances, layer ownership and native reviews."""
from hashlib import sha256
import json
from pathlib import Path
import unittest
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1];PACK=ROOT/'assets/terrain/eldenmere/exteriors_hd';SOURCE=ROOT/'assets/source/terrain/eldenmere/exteriors_hd';REVIEW=ROOT/'docs/reviews/eldenmere_exteriors_hd'
def im(path):
    with Image.open(path) as source:return source.convert('RGBA')
def gray(path):
    with Image.open(path) as source:return source.convert('L')
def colors(image):
    raw=image.tobytes();return {tuple(raw[i:i+4]) for i in range(0,len(raw),4) if raw[i+3]}
def palette(ramp):return {tuple(bytes.fromhex(c[1:]))+(255,) for c in ramp.values()}
def dark_area(image):return sum(c[3]>0 and max(c[:3])<90 for c in image.getdata())
class ExteriorsHDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((PACK/'manifest.json').read_text());cls.rec=json.loads((SOURCE/'recipe.json').read_text());cls.buildings={r['id']:r for r in cls.meta['buildings']};cls.props={r['id']:r for r in cls.meta['props']}
    def test_units_staged_status_inventory_and_four_roof_palettes(self):
        m=self.meta;self.assertEqual(m['artwork_pixels_per_world_pixel'],2);self.assertEqual(m['integration_status'],'not_integrated');self.assertEqual(m['visual_approval'],'not_reviewed_by_user');self.assertEqual(len(self.buildings),14);self.assertEqual(len(self.props),24);self.assertEqual(len(m['bindings']),11)
        self.assertEqual({r['roof'] for r in self.buildings.values()},{'slate','terracotta','moss','heather'})
        self.assertEqual(sum(r['kind']=='landmark' for r in self.buildings.values()),4)
    def test_binding_snapshot_preserves_every_existing_entrance_contract(self):
        # Validate the versioned audit snapshot, not a permanent freeze on live maps.
        self.assertEqual(self.meta['bindings'],self.rec['existing_building_audit']);self.assertEqual(json.loads((REVIEW/'audit.json').read_text())['live_consumers'],self.meta['bindings'])
        for binding in self.meta['bindings']:
            r=self.buildings[binding['new_design']];self.assertEqual(r['logical_size'],binding['logical_size']);self.assertEqual(r['door_rect_logical'],binding['door_rect_local_logical']);self.assertEqual(binding['frame_duration_ms'],100);self.assertEqual(len(binding['legacy_door_frames']),5);self.assertEqual(binding['open_radius'],30);self.assertEqual(binding['close_radius'],38);self.assertTrue(binding['requires_open'])
            x,y=binding['position_logical'];dx,dy,w,h=r['door_rect_logical'];self.assertEqual([x+dx,y+dy],binding['door_world_position_logical']);self.assertAlmostEqual(binding['entry_anchor_world_logical'][0],x+dx+w/2);self.assertTrue(binding['destination']);self.assertEqual(len(binding['spawn']),2)
            self.assertEqual(binding['sort_y_logical'],y+r['depth_baseline_logical'])
    def test_canvases_and_portal_coverage_are_explicit(self):
        for r in self.buildings.values():
            structure=im(PACK/r['structure']);self.assertEqual(list(structure.size),r['artwork_size']);self.assertEqual([v*2 for v in r['logical_size']],r['artwork_size']);x,y,w,h=[v*2 for v in r['door_rect_logical']];self.assertIsNone(structure.crop((x,y,x+w,y+h)).getbbox(),r['id'])
            self.assertEqual(r['door']['position_logical'],r['door_rect_logical'][:2]);self.assertEqual(r['door']['logical_size'],r['door_rect_logical'][2:]);self.assertEqual(r['door']['closing_order'],[4,3,2,1,0]);self.assertFalse(r['door']['loop'])
    def test_drawn_doors_have_five_states_and_opening_reveals_dark_interior(self):
        for r in self.buildings.values():
            frames=[im(PACK/f['file']) for f in r['door']['frames']];self.assertEqual(len(frames),5);self.assertEqual(len({image.tobytes() for image in frames}),5)
            for f,image in zip(r['door']['frames'],frames):self.assertEqual(f['duration_ms'],100);self.assertEqual(list(image.size),[v*2 for v in r['door']['logical_size']]);self.assertEqual(image.getchannel('A').getextrema(),(255,255))
            dark=[dark_area(image) for image in frames];self.assertGreater(dark[-1],dark[0]+frames[0].width*frames[0].height*.35,r['id']);self.assertTrue(all(b>=a for a,b in zip(dark,dark[1:])),(r['id'],dark))
    def test_closed_open_and_door_sheets_reconstruct_exactly(self):
        for r in self.buildings.values():
            structure=im(PACK/r['structure']);sheet=im(PACK/r['door_sheet']);self.assertEqual(sheet.size,(structure.width*5,structure.height));x,y=[v*2 for v in r['door']['position_logical']]
            for phase,f in enumerate(r['door']['frames']):
                result=structure.copy();result.alpha_composite(im(PACK/f['file']),(x,y))
                if r['wheel']:result.alpha_composite(im(PACK/r['wheel']['frames'][0]['file']),tuple(v*2 for v in r['wheel']['position_logical']))
                self.assertEqual(sheet.crop((phase*structure.width,0,(phase+1)*structure.width,structure.height)).tobytes(),result.tobytes())
                if phase in (0,4):self.assertEqual(im(PACK/r['closed' if phase==0 else 'open']).tobytes(),result.tobytes())
    def test_window_masks_only_select_glass_and_optional_warm_panes(self):
        glass=palette(self.rec['palette']['glass']);warm=palette(self.rec['palette']['lamplight'])
        for r in self.buildings.values():
            mask=gray(PACK/r['window_mask']);structure=im(PACK/r['structure']);self.assertLessEqual(set(mask.tobytes()),{0,255});self.assertIsNotNone(mask.getbbox());allowed=glass|warm if r['kind']=='home' else glass;count=0
            for y in range(mask.height):
                for x in range(mask.width):
                    if mask.getpixel((x,y)):self.assertIn(structure.getpixel((x,y)),allowed,r['id']);count+=1
            self.assertLess(count,mask.width*mask.height*.08,r['id'])
    def test_ambient_layers_leave_structure_and_doors_fixed(self):
        for r in self.buildings.values():
            closed=im(PACK/r['closed']);mask=gray(PACK/r['window_mask']);self.assertEqual(len(r['ambient']['frames']),18);self.assertEqual(sum(f['duration_ms'] for f in r['ambient']['frames']),3600)
            for f,fx in zip(r['ambient']['frames'],r['ambient']['effects']):
                smoke=im(PACK/fx['smoke']);glow=im(PACK/fx['windowlight']);self.assertEqual(glow.getchannel('A').tobytes(),mask.tobytes());expected=closed.copy();expected.alpha_composite(glow);expected.alpha_composite(smoke);self.assertEqual(expected.tobytes(),im(PACK/f['file']).tobytes());self.assertLessEqual(set(smoke.getchannel('A').tobytes()),{0,255})
                if not r['ambient']['smoke_optional']:self.assertIsNone(smoke.getbbox())
            self.assertEqual(r['ambient']['reduced_motion'],r['closed'])
    def test_smoke_starts_at_authored_chimney_and_stays_in_canvas(self):
        specs={r['id']:r for r in self.rec['designs']}
        for r in self.buildings.values():
            if not r['ambient']['smoke_optional']:continue
            spec=specs[r['id']];bx,by,br,bb=spec['body_bounds_logical'];emit_x=round((bx+(br-bx)*spec['chimney_normalized_x'])*2);emit_y=round(by*2+spec['chimney_normalized_y']/spec['source_door_normalized'][1]*(spec['door_rect_logical'][1]*2-by*2))
            smoke=im(PACK/r['ambient']['effects'][0]['smoke']);box=smoke.getbbox();self.assertTrue(box[0]>=0 and box[1]>=0 and box[2]<=smoke.width and box[3]<=smoke.height);self.assertLessEqual(box[3],emit_y);self.assertGreater(box[3],emit_y-8);self.assertTrue(box[0]<emit_x<box[2])
    def test_wheel_preserves_position_axle_and_full_turn_speed(self):
        r=self.buildings['mill']['wheel'];self.assertEqual(r['logical_size'],[48,48]);self.assertEqual(r['position_logical'],[88,94]);self.assertEqual(r['axle_center_logical'],[112,118]);self.assertEqual(len(r['frames']),48);self.assertEqual(len(r['frames'])*r['step_degrees'],360);self.assertEqual(sum(f['duration_ms'] for f in r['frames']),r['full_turn_ms']);self.assertEqual(r['full_turn_ms'],9600)
        idle=im(PACK/'mill/wheel_idle.png');hub=im(PACK/r['fixed_hub']);mask=hub.getchannel('A');frames=[]
        for phase,f in enumerate(r['frames']):
            image=im(PACK/f['file']);self.assertEqual(image.size,(96,96));expected=idle.rotate(-phase*7.5,resample=Image.Resampling.NEAREST,center=(48,48));expected.alpha_composite(hub);self.assertEqual(expected.tobytes(),image.tobytes());self.assertEqual(Image.composite(image,Image.new('RGBA',image.size),mask).tobytes(),hub.tobytes());box=image.getbbox();self.assertTrue(box[0]>0 and box[1]>0 and box[2]<96 and box[3]<96);frames.append(image)
        self.assertGreater(len({f.tobytes() for f in frames}),12)
    def test_props_have_plausible_scale_and_fixed_mounts(self):
        self.assertEqual(self.props['boots']['logical_size'],[12,12]);self.assertEqual(self.props['watering_can']['logical_size'],[16,14])
        for r in self.props.values():
            idle=im(PACK/r['idle']);self.assertEqual(list(idle.size),r['artwork_size']);self.assertEqual([v*2 for v in r['logical_size']],r['artwork_size']);self.assertEqual([v*2 for v in r['draw_anchor_logical']],r['anchor_artwork'])
            sequence=[im(PACK/p) for p in r['frames']]
            if r['animation']=='static':self.assertEqual(len(sequence),1);continue
            self.assertEqual(len(sequence),18);self.assertEqual(r['cycle_ms'],3600);self.assertGreater(len({f.tobytes() for f in sequence}),1,r['id'])
            fixed_rows=12 if r['animation']=='hanging' else 16
            for image in sequence:self.assertEqual(image.crop((0,0,image.width,fixed_rows)).tobytes(),idle.crop((0,0,idle.width,fixed_rows)).tobytes(),r['id'])
    def test_hard_alpha_named_palette_and_native_detail(self):
        allowed=set().union(*(palette(r) for r in self.rec['palette'].values()),*(palette(r) for r in self.rec['roof_palettes'].values()))
        paths=[r['structure'] for r in self.buildings.values()]+[r['idle'] for r in self.props.values()]
        for path in paths:
            image=im(PACK/path);self.assertLessEqual(set(image.getchannel('A').tobytes()),{0,255});self.assertLessEqual(colors(image),allowed,path);self.assertNotIn((255,0,255,255),colors(image))
        for r in self.buildings.values():
            image=im(PACK/r['closed']);fine=sum(len({image.getpixel((x+dx,y+dy)) for dx in (0,1) for dy in (0,1)})>1 for y in range(0,image.height,2) for x in range(0,image.width,2));self.assertGreater(fine,300)
    def test_scene_props_do_not_block_recorded_door_approaches(self):
        layout=json.loads((REVIEW/'layout.json').read_text())
        for scene in layout['scenes']:
            for b in scene['buildings']:
                r=self.buildings[b['id']];x,y,w,h=r['door_approach_local_logical'];ax=b['position_artwork'][0]+x*2;ay=b['position_artwork'][1]+y*2;ar=ax+w*2;ab=ay+h*2
                for p in scene['props']:
                    image=im(PACK/self.props[p['id']]['idle']);l,t,right,bottom=image.getbbox();px,py=p['position_artwork'];self.assertFalse(ax<px+right and px+l<ar and ay<py+bottom and py+t<ab,(scene['id'],b['id'],p['id']))
    def test_native_scene_reconstructs_from_recorded_layers(self):
        layout=json.loads((REVIEW/'layout.json').read_text());ground=ROOT/'assets/terrain/eldenmere/grass_dirt_hd';gm=json.loads((ground/'tileset.json').read_text());grass=[im(ground/p) for p in gm['materials']['grass']];dirt=im(ground/gm['materials']['dirt'][0])
        for fixture in layout['scenes']:
            scene=Image.new('RGBA',tuple(fixture['size_artwork']))
            for y in range(14):
                for x in range(20):scene.alpha_composite(dirt if 8<=y<=10 else grass[(x//3+y//4)%4],(x*48,y*48))
            for b in fixture['buildings']:scene.alpha_composite(im(PACK/self.buildings[b['id']]['closed']),tuple(b['position_artwork']))
            for p in fixture['props']:scene.alpha_composite(im(PACK/self.props[p['id']]['idle']),tuple(p['position_artwork']))
            for a in fixture['actors']:scene.alpha_composite(im(ROOT/a['file']),tuple(a['position_artwork']))
            self.assertEqual(scene.tobytes(),im(REVIEW/(fixture['id']+'_native.png')).tobytes())
    def test_gif_pixels_and_all_three_clock_types_are_exact(self):
        layout=json.loads((REVIEW/'layout.json').read_text());cases=[(name+'_ambience.gif','ambient/'+name,[200]*18) for name in ('standard_gardener','standard_craft','standard_weathered','mira','sanctuary')]+[('props_motion.gif','props_motion',[200]*18),('mill_wheel.gif','mill',[200]*48),('doors.gif','doors',layout['door_review']['durations_ms'])]
        for gif,folder,times in cases:
            expected=[]
            for phase,duration in enumerate(times):expected.extend([im(REVIEW/folder/f'frame_{phase:02}.png').convert('RGB').tobytes()]*(duration//100))
            actual=[]
            with Image.open(REVIEW/gif) as animation:
                total=0
                for phase in range(animation.n_frames):animation.seek(phase);duration=animation.info['duration'];total+=duration;self.assertEqual(duration%100,0);actual.extend([animation.convert('RGB').tobytes()]*(duration//100))
            self.assertEqual(total,sum(times));self.assertEqual(actual,expected,gif)
    def test_no_gameplay_registration_or_ordinary_decoration_cues(self):
        for r in list(self.buildings.values())+list(self.props.values()):self.assertFalse(r['interaction_cues']);self.assertIn('collision',r)
        self.assertIn('No runtime',self.meta['activation']);self.assertIn('entry anchors',self.meta['integration_followup']);self.assertIn('No gate/prop gameplay',self.props['garden_gate']['passability'])
    def test_source_hashes_output_inventory_and_reproducible_exports(self):
        for r in self.rec['sources']:self.assertEqual(sha256((SOURCE/r['file']).read_bytes()).hexdigest(),r['sha256'])
        for r in json.loads((REVIEW/'exports.json').read_text())['outputs']:self.assertEqual(sha256((ROOT/r['file']).read_bytes()).hexdigest(),r['sha256'])
        from tools.build_eldenmere_exteriors_hd import build
        outputs=build(check=True)
        for path in outputs:self.assertTrue(path.startswith(('assets/terrain/eldenmere/exteriors_hd/','docs/reviews/eldenmere_exteriors_hd/')))
        actual={p.relative_to(ROOT).as_posix() for folder in (PACK,REVIEW) for p in folder.rglob('*') if p.is_file() and p.name not in ('README.md','preservation.json')};self.assertEqual(actual,set(outputs))
if __name__=='__main__':unittest.main()
