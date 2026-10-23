"""Check workshop registration, animation, routes and exact review pixels."""
from collections import deque
import json
from pathlib import Path
import unittest
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/workshop'
SOURCE=ROOT/'assets/source/terrain/eldenmere/workshop'
TERRAIN=PACK.parent
BASE=ROOT/'assets/maps/eldenmere/terrain_foundation'
CHARM=TERRAIN/'sanctuary_charm'


def load(path):return json.loads(path.read_text())


def opened(path,mode='RGBA'):
    with Image.open(path) as image:return image.convert(mode)


def box(rect):
    x,y,w,h=rect;return x,y,x+w,y+h


class WorkshopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=load(PACK/'workshop.json');cls.recipe=load(SOURCE/'recipe.json')

    def test_native_materials_source_parts_and_ground_registration(self):
        meta=self.meta;recipe=self.recipe
        self.assertEqual(meta['prefab_size'],[168,168]);self.assertEqual(meta['ground_tiles'],[5,3])
        x,y=meta['position'];gx,gy,w,h=meta['ground_rect']
        self.assertEqual([x+gx,y+gy,w,h],[576,360,120,72])
        expected=Image.new('RGBA',(168,168))
        for p in recipe['bands']:
            image=opened(SOURCE/f"parts/{p['id']}.png")
            self.assertEqual(list(image.size),p['size']);expected.alpha_composite(image,tuple(p['position']))
        rack=next(p for p in recipe['props'] if p['id']=='tool_rack')
        expected.alpha_composite(opened(PACK/'props/tool_rack.png'),(rack['position'][0]-x,rack['position'][1]-y))
        self.assertEqual(expected.tobytes(),opened(PACK/'structure.png').tobytes())
        rest=expected.copy();rest.alpha_composite(opened(PACK/'sign/frame_01.png'))
        self.assertEqual(rest.tobytes(),opened(PACK/'closed.png').tobytes())
        materials=load(PACK/'palette.json')['materials']
        colors={(*bytes.fromhex(c[1:]),255) for ramp in materials.values() for c in ramp.values()}
        for path in [PACK/'structure.png',PACK/'closed.png',*(PACK/'props').glob('*.png')]:
            image=opened(path)
            self.assertEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
            self.assertTrue(all(p in colors for p in image.get_flattened_data() if p[3]),str(path))
        for p in recipe['props']:
            native=opened(PACK/f"props/{p['id']}.png");self.assertEqual(list(native.size),p['size'])
            self.assertEqual(native.tobytes(),opened(SOURCE/f"parts/{p['id']}_native.png").tobytes())
        dx,dy,dw,dh=meta['door']['rect']
        self.assertEqual(x+dx+dw/2,recipe['hero_foot'][0]);self.assertEqual(dw,28)
        self.assertLessEqual(y+dy+dh,432);self.assertFalse(meta['door']['animated'])

    def test_sign_ring_fixed_one_pixel_sway_and_complete_native_animation(self):
        structure=opened(PACK/'structure.png');plaque=opened(PACK/'props/cog_sign.png')
        sx,sy=self.recipe['sign_position'];poses=[]
        for phase,tilt in enumerate(self.recipe['sign_offsets'],1):
            expected=Image.new('RGBA',(168,168))
            for y in range(plaque.height):
                dx=round(tilt*y/(plaque.height-1))
                expected.alpha_composite(plaque.crop((0,y,plaque.width,y+1)),(sx+dx,sy+y))
            pose=opened(PACK/f'sign/frame_{phase:02}.png');poses.append(pose)
            self.assertEqual(pose.tobytes(),expected.tobytes())
            self.assertEqual(pose.crop((sx,sy,sx+18,sy+6)).tobytes(),poses[0].crop((sx,sy,sx+18,sy+6)).tobytes())
            image=structure.copy();image.alpha_composite(pose)
            # Bracket above the ring keeps its original structural pixels.
            self.assertEqual(image.crop((129,128,143,133)).tobytes(),structure.crop((129,128,143,133)).tobytes())
        self.assertEqual(len({p.tobytes() for p in poses}),3)
        self.assertEqual(self.meta['sign']['cycle_duration_ms'],5400)
        for tick in range(54):
            expected=structure.copy();expected.alpha_composite(poses[tick//3%9])
            expected.alpha_composite(opened(PACK/f'smoke/frame_{tick%18+1:02}.png'))
            self.assertEqual(expected.tobytes(),opened(PACK/f'frames/frame_{tick+1:02}.png').tobytes())

    def test_smoke_reuses_approved_pixels_without_clipping(self):
        ox,oy=self.recipe['smoke_origin'];dx,dy=ox-90,oy-47
        self.assertEqual(self.meta['smoke']['cycle_duration_ms'],3600)
        self.assertEqual(opened(PACK/'structure.png').getpixel((ox,oy))[3],255)
        for phase in range(1,19):
            original=opened(TERRAIN/f'cottage/smoke/frame_{phase:02}.png')
            actual=opened(PACK/f'smoke/frame_{phase:02}.png')
            expected=Image.new('RGBA',(168,168));expected.alpha_composite(original,(dx,dy))
            self.assertEqual(actual.tobytes(),expected.tobytes())
            self.assertEqual(sum(p[3]>0 for p in original.get_flattened_data()),sum(p[3]>0 for p in actual.get_flattened_data()))
            for y in range(original.height):
                for x in range(original.width):
                    p=original.getpixel((x,y))
                    if p[3]:self.assertEqual(actual.getpixel((x+dx,y+dy)),p)

    def test_independent_full_width_access_and_open_conversation_area(self):
        meta=load(PACK/'navigation/access.json');blocked=opened(PACK/'navigation/blocking.png','L')
        expected=opened(CHARM/'navigation/blocking.png','L')
        for p in meta['blockers']:expected.paste(255,box(p['rect']))
        self.assertEqual(blocked.tobytes(),expected.tobytes())
        self.assertIsNone(blocked.crop(box(self.recipe['conversation_rect'])).getbbox())
        allowed=opened(PACK/'navigation/allowed_routes.png','L')
        start=(636,480);visited={start};queue=deque([start])
        while queue:
            x,y=queue.popleft()
            for p in ((x-2,y),(x+2,y),(x,y-2),(x,y+2)):
                xx,yy=p
                if p in visited or not(516<=xx<912 and 336<=yy<516):continue
                if allowed.getpixel(p) and not blocked.crop((xx-12,yy-6,xx+12,yy+6)).getbbox():
                    visited.add(p);queue.append(p)
        for name in ['workshop_door','workbench','mira_scale','conversation_left','conversation_right','woodland_lane','upper_bridge']:
            self.assertIn(tuple(meta['destinations'][name]),visited,name)
        for x in range(552,746,2):self.assertIsNone(blocked.crop((x-12,474,x+12,486)).getbbox())
        reachable=opened(PACK/'navigation/reachable_centres.png','L')
        for name,p in meta['destinations'].items():self.assertEqual(reachable.getpixel(tuple(p)),255,name)
        self.assertFalse(meta['engine_collision_implemented'])

    def test_town_preserved_outside_workshop_yard_and_characters(self):
        before=opened(CHARM/'town_native.png','RGB');after=opened(PACK/'town_native.png','RGB')
        permitted=Image.new('L',before.size)
        x,y=self.meta['position'];w,h=self.meta['prefab_size'];permitted.paste(255,(x,y,x+w,y+h))
        for spec in self.recipe['props']:
            if 'position' in spec:
                x,y=spec['position'];w,h=spec['size'];permitted.paste(255,(x,y,x+w,y+h))
        for spec in self.recipe['grass']:
            x,y=spec['position'];permitted.paste(255,(x,y,x+24,y+24))
        for x,y in self.meta['apron']['changed_tile_bounds']:permitted.paste(255,(x*24,y*24,x*24+24,y*24+24))
        x,y=self.recipe['mira_foot'];permitted.paste(255,(x-12,y-30,x+12,y+6))
        diff=ImageChops.difference(before,after);self.assertIsNotNone(diff.getbbox())
        diff.paste((0,0,0),(0,0),permitted);self.assertIsNone(diff.getbbox())
        self.assertEqual(before.crop((144,48,516,456)).tobytes(),after.crop((144,48,516,456)).tobytes())
        self.assertFalse(self.meta['interior_included']);self.assertFalse(self.meta['mill_quest_solution_defined'])

    def test_scene_contains_native_roof_sign_and_reused_grass_motion(self):
        cx,cy,_,_=self.meta['review_crop'];bx,by=self.meta['position']
        grass=next(p for p in self.recipe['grass'] if p['id']=='yard_edge_grass');gx,gy=grass['position']
        bases=opened(TERRAIN/grass['pack']/'base.png');seen=set()
        for tick,record in enumerate(self.meta['frames']):
            native=opened(PACK/record['image'],'RGB');building=opened(PACK/f'frames/frame_{tick+1:02}.png')
            for y in range(124):
                for x in range(168):
                    p=building.getpixel((x,y))
                    if p[3]:self.assertEqual(native.getpixel((bx-cx+x,by-cy+y)),p[:3])
            sign=opened(PACK/f'sign/frame_{tick//3%9+1:02}.png')
            for y in range(133,153):
                for x in range(130,152):
                    p=sign.getpixel((x,y))
                    if p[3]:self.assertEqual(native.getpixel((bx-cx+x,by-cy+y)),p[:3])
            phase=(tick//3+grass['phase_offset'])%9
            pose=opened(TERRAIN/grass['pack']/f'frames/frame_{phase+1:02}.png')
            seen.add(native.crop((gx-cx,gy-cy,gx+16-cx,gy+24-cy)).tobytes())
            for y in range(24):
                for x in range(16):
                    p=pose.getpixel((x,y))
                    if p[3]:self.assertEqual(native.getpixel((gx-cx+x,gy-cy+y)),p[:3])
                    p=bases.getpixel((x,y))
                    if p[3]:self.assertEqual(native.getpixel((gx-cx+x,gy-cy+y)),p[:3])
        self.assertGreater(len(seen),2)

    def test_exact_actors_opaque_reviews_and_lossless_loop(self):
        cx,cy,w,h=self.meta['review_crop'];scale=self.meta['review_scale'];total=0
        actors=[(opened(ROOT/f'assets/characters/{name}/idle_front.png'),self.meta[key])
                for name,key in [('caelan','hero_foot'),('mira','mira_foot')]]
        with Image.open(PACK/'workshop_review.gif') as gif:
            self.assertEqual(gif.n_frames,54);self.assertEqual(gif.info['loop'],0)
            for i,record in enumerate(self.meta['frames']):
                native=opened(PACK/record['image'],'RGB');self.assertEqual(native.size,(w,h))
                for actor,(fx,fy) in actors:
                    for y in range(36):
                        for x in range(24):
                            p=actor.getpixel((x,y))
                            if p[3]:self.assertEqual(native.getpixel((fx-12-cx+x,fy-30-cy+y)),p[:3])
                gif.seek(i);self.assertEqual(gif.info['duration'],200);total+=gif.info['duration']
                expected=native.resize((w*scale,h*scale),Image.Resampling.NEAREST)
                self.assertEqual(gif.convert('RGB').crop((0,84,w*scale,84+h*scale)).tobytes(),expected.tobytes())
            self.assertEqual(total,10800);gif.seek(0)
            self.assertEqual(gif.convert('RGB').tobytes(),opened(PACK/'workshop_review.png','RGB').tobytes())
        for name in ['workshop_review.png','town_review.png','exterior_review.png']:
            with Image.open(PACK/name) as im:self.assertEqual(im.mode,'RGB')


if __name__=='__main__':unittest.main()
