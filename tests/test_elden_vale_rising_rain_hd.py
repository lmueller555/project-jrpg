"""Contracts for staged weather, anatomical registration and preview handoffs."""
import importlib.util
import json
import math
from pathlib import Path
import unittest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/overworld/elden_vale/rising_rain_hd/manifest.json'

class RisingRainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack=json.loads(PACK.read_text())
        spec=importlib.util.spec_from_file_location('rain_builder',ROOT/'tools/build_elden_vale_rising_rain_hd.py')
        cls.builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.builder)

    def test_upward_deterministic_bounded_particles_and_clear_route(self):
        a=self.builder.weather_instances(6000);b=self.builder.weather_instances(6100)
        self.assertEqual(a,self.builder.weather_instances(6000))
        by_id={p['id']:p for p in b if 'id' in p}
        moved=0
        for particle in a:
            if 'id' not in particle:continue
            other=by_id[particle['id']]
            self.assertFalse(380<particle['position'][0]<550)
            if other['position'][1]<particle['position'][1]:moved+=1
        self.assertGreater(moved,50)
        self.assertLessEqual(len(a),183)
        self.assertEqual(self.builder.weather_instances(12000),[])
        self.assertEqual(self.builder.phase_at(0),'signs')
        self.assertEqual(self.builder.phase_at(4500),'peak')
        for invalid in [-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):self.builder.phase_at(invalid)

    def test_reduced_motion_uses_dedicated_unmoving_assets(self):
        a=self.builder.weather_instances(3000,True)
        self.assertEqual(a,self.builder.weather_instances(9000,True))
        for item in a:self.assertTrue(self.pack['effects'][item['asset']]['reduced_motion'])
        self.assertFalse(self.pack['gameplay_effects'])

    def test_handoffs_seek_restore_without_duplicate_props(self):
        expected={'gather':[(3,'station'),(4,'actor'),(7,'actor')],
                  'deploy':[(0,'station'),(1,'actor'),(4,'actor'),(5,'station')],
                  'leaf':[(1,'station'),(2,'actor'),(6,'actor'),(7,'station')]}
        for action,checks in expected.items():
            clip=self.pack['actions'][action];restored=json.loads(json.dumps(clip))
            for frame,owner in checks:
                state=self.builder.action_state(clip,frame*220)
                self.assertEqual(state['owner'],owner)
                self.assertEqual(state['visible_instances'],1)
                self.assertEqual(state,self.builder.action_state(restored,frame*220))
            for cue in clip['ownership_cues']:
                if cue['contact_position_logical'] is None:continue
                hand=clip['frames'][cue['frame']]['grip_logical']
                self.assertLessEqual(math.dist(hand,cue['contact_position_logical']),6)

    def test_pose_density_sole_registration_and_grip_landmarks(self):
        for action,clip in self.pack['actions'].items():
            for index,frame in enumerate(clip['frames']):
                with self.subTest(action=action,frame=index):
                    image=Image.open(ROOT/frame['image']).convert('RGBA')
                    self.assertEqual(image.size,(96,112))
                    self.assertEqual(image.getbbox()[3],104)
                    self.assertLessEqual(set(image.getchannel('A').tobytes()),{0,255})
                    if self.builder.action_state(clip,index*220)['owner']=='actor':
                        gx,gy=[n*2 for n in frame['grip_logical']]
                        skin=[]
                        for y in range(max(0,int(gy)-4),min(112,int(gy)+5)):
                            for x in range(max(0,int(gx)-4),min(96,int(gx)+5)):
                                r,g,b,a=image.getpixel((x,y))
                                if a and r>170 and g>90 and b<190 and r>g*1.1:skin.append((x,y))
                        self.assertTrue(skin,'Grip should remain near a naturally drawn hand')
                        self.assertLessEqual(min(math.dist((gx,gy),p) for p in skin),4)

    def test_supports_masks_and_staged_icons(self):
        for kind in ('props','effects'):
            for record in self.pack[kind].values():
                image=Image.open(ROOT/record['image']).convert('RGBA')
                self.assertEqual(image.size,tuple(2*n for n in record['logical_size']))
                self.assertLessEqual(set(image.getchannel('A').tobytes()),{0,255})
                self.assertFalse(record['interaction_cues'])
        for name in ('post_left','post_right'):self.assertTrue(self.pack['props'][name]['fixed_support'])
        for record in self.pack['cartography'].values():
            with Image.open(ROOT/record['image']) as icon:self.assertEqual(icon.size,(64,64))
        self.assertEqual(self.pack['integration_status'],'not_integrated')

    def test_gif_timing_and_nonlooping_actions(self):
        review=ROOT/'docs/reviews/elden_vale_rising_rain_hd'
        for action in self.pack['actions']:
            image=Image.open(review/f'{action}.gif');duration=0
            self.assertNotIn('loop',image.info)
            for index in range(image.n_frames):image.seek(index);duration+=image.info['duration']
            self.assertEqual(duration,4*120+8*220)
            image.close()
        image=Image.open(review/'meadow.gif');duration=0
        for index in range(image.n_frames):image.seek(index);duration+=image.info['duration']
        self.assertEqual(duration,12000)
        image.close()
        flight=self.pack['wildlife']['clips']['flight']
        self.assertEqual(len(flight['frames']),8)
        self.assertTrue(flight['loop'])

    def test_fixed_post_contact_pixels_do_not_move(self):
        post=self.pack['props']['post_left']
        with Image.open(ROOT/post['image']) as image:box=image.getbbox()
        ax,ay=post['peg_anchor_logical']
        ox,oy=round(179-2*ax),round(194-2*ay)
        roi=(ox+box[0],oy+box[3]-4,ox+box[2],oy+box[3])
        with Image.open(ROOT/'docs/reviews/elden_vale_rising_rain_hd/deploy_contacts.png') as sheet:
            reference=sheet.crop(roi).tobytes()
            self.assertGreater(len(set(reference)),1)
            for index in range(8):
                x,y=(index%4)*480,(index//4)*320
                self.assertEqual(sheet.crop(tuple(n+(x if i%2==0 else y) for i,n in enumerate(roi))).tobytes(),reference)

    def test_native_sheets_reconstruct_frames(self):
        for clip in self.pack['actions'].values():
            with Image.open(ROOT/clip['sheet']) as sheet:
                for frame in clip['frames']:
                    x,y,w,h=frame['sheet_rect_artwork']
                    with Image.open(ROOT/frame['image']) as image:
                        self.assertEqual(sheet.crop((x,y,x+w,y+h)).tobytes(),image.tobytes())
