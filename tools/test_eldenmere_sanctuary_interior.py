"""Verify sanctuary art, story anchors, door access and lossless review timelines."""
from collections import deque
import json
from pathlib import Path
import re
import unittest
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/eldenmere/sanctuary_interior'
SOURCE=ROOT/'assets/source/terrain/eldenmere/sanctuary_interior'
TERRAIN=PACK.parent


def load(path):return json.loads(path.read_text())


def opened(path,mode='RGBA'):
    with Image.open(path) as image:return image.convert(mode)


def box(rect):
    x,y,w,h=rect;return x,y,x+w,y+h


class SanctuaryInteriorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe=load(SOURCE/'recipe.json');cls.meta=load(PACK/'interiors.json')
        cls.rooms={r['id']:load(PACK/r['room']) for r in cls.meta['rooms']}

    def test_native_prop_materials_sizes_alpha_and_source_exports(self):
        palette=load(PACK/'palette.json')['materials']
        colors={(*bytes.fromhex(c[1:]),255) for ramp in palette.values() for c in ramp.values()}
        self.assertEqual(len(self.recipe['props']),18)
        for spec in self.recipe['props']:
            image=opened(PACK/f"props/{spec['id']}.png")
            self.assertEqual(list(image.size),spec['size'])
            self.assertEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
            self.assertTrue(all(p in colors for p in image.get_flattened_data() if p[3]),spec['id'])
            self.assertEqual(image.tobytes(),opened(SOURCE/f"parts/{spec['id']}_native.png").tobytes())
        glyph=opened(TERRAIN/'cottage/smoke/frame_01.png').crop((88,45,93,50))
        self.assertEqual(glyph.tobytes(),opened(PACK/'props/steam_glyph.png').tobytes())
        self.assertIsNotNone(glyph.getbbox())

    def test_independent_navigation_to_all_objects_portals_and_story_anchors(self):
        expected_sizes={'bedroom':[10,10],'hall':[12,10],'dining':[16,10]}
        for name,meta in self.rooms.items():
            self.assertEqual(meta['floor_tiles'],expected_sizes[name])
            x0,y0,w,h=meta['floor_rect'];self.assertEqual([w,h],[n*24 for n in expected_sizes[name]])
            blocked=opened(PACK/name/'blocking.png','L');expected=Image.new('L',blocked.size)
            for obj in meta['objects']:
                rect=obj.get('floor_rect')
                if not rect:continue
                x,y,rw,rh=rect
                self.assertTrue(x0<=x and y0<=y and x+rw<=x0+w and y+rh<=y0+h,obj['id'])
                expected.paste(255,box(rect))
            self.assertEqual(expected.tobytes(),blocked.tobytes())
            free=set()
            for y in range(y0+6,y0+h-5,2):
                for x in range(x0+12,x0+w-11,2):
                    if not blocked.crop((x-12,y-6,x+12,y+6)).getbbox():free.add((x,y))
            start=tuple(meta['navigation_start']);visited=set();q=deque([start])
            while q:
                p=q.popleft()
                if p in visited or p not in free:continue
                visited.add(p);x,y=p;q.extend(((x-2,y),(x+2,y),(x,y-2),(x,y+2)))
            self.assertEqual(len(visited),meta['reachable_centres'])
            self.assertIn(tuple(meta['hero_foot']),visited)
            for obj in meta['objects']:
                if obj.get('access'):self.assertIn(tuple(obj['access']),visited,f"{name}/{obj['id']}")
            for p in meta['portals']:
                self.assertIn(tuple(p['access']),visited);self.assertIn(tuple(p['spawn']),visited)
            for a in meta['story_anchors']:
                if a.get('access'):self.assertIn(tuple(a['access']),visited)

    def test_connected_portal_plan_and_exterior_threshold_alignment(self):
        visited={'bedroom'};edges=[]
        for link in self.meta['links']:
            room,portal=link['a'];self.assertIn(portal,{p['id'] for p in self.rooms[room]['portals']})
            if 'b' in link:
                other,back=link['b'];self.assertIn(back,{p['id'] for p in self.rooms[other]['portals']})
                edges.append((room,other))
            else:
                self.assertEqual((room,portal),('hall','courtyard'))
                exterior=load(TERRAIN/'sanctuary/sanctuary.json')
                self.assertEqual(link['door_world_rect'],exterior['door_world_rect'])
                self.assertEqual(link['exterior_foot'],exterior['character']['foot'])
                entry=self.rooms['hall']['entry_rect'];self.assertEqual(entry[2],32)
                gx,_,gw,_=exterior['ground_rect'];dx,_,dw,_=exterior['door']['rect']
                ideal=24+(dx+dw/2-gx)/gw*self.rooms['hall']['floor_rect'][2]
                self.assertLessEqual(abs(entry[0]+entry[2]/2-ideal),1)
                threshold=opened(TERRAIN/'cottage_interior/tiles/entry_threshold.png')
                wall=opened(PACK/'hall/walls.png')
                self.assertEqual(wall.crop((entry[0],entry[1],entry[0]+24,entry[1]+8)).tobytes(),threshold.tobytes())
                self.assertEqual(wall.crop((entry[0]+24,entry[1],entry[0]+32,entry[1]+8)).tobytes(),threshold.crop((0,0,8,8)).tobytes())
        for _ in range(3):
            for a,b in edges:
                if a in visited:visited.add(b)
                if b in visited:visited.add(a)
        self.assertEqual(visited,set(self.rooms));self.assertFalse(self.meta['engine_transfers_implemented'])

    def test_approved_inspection_lines_and_three_household_provisions(self):
        text=(ROOT/'docs/narrative/game_01/CH01_MQ01.md').read_text()
        section=text.split('**Optional inspect lines:**',1)[1].split('**Exit:**',1)[0]
        approved=dict(re.findall(r'^- (.*?) — Caelen: "(.*?)"$',section,re.M));seen={}
        for obj in self.rooms['bedroom']['objects']+self.rooms['bedroom']['story_anchors']:
            if obj.get('inspect_key'):
                self.assertEqual(obj['approved_inspect_text'],approved[obj['inspect_key']]);seen[obj['inspect_key']]=obj['approved_inspect_text']
        self.assertEqual(set(seen),set(approved));self.assertEqual(len(seen),6)
        deliveries={r['household']:r['sprite'] for r in self.rooms['dining']['objects'] if r.get('household')}
        self.assertEqual(deliveries,{'halden':'medicine_tray','elira':'food_oil_basket','venn':'care_basket'})
        for room in self.rooms.values():
            for obj in room['objects']:
                if 'parent' in obj:self.assertIsNone(obj['floor_rect'])
        self.assertFalse(self.meta['later_revelations_displayed']);self.assertFalse(self.meta['cast_designs_added'])

    def test_animation_locality_fixed_furniture_and_six_steam_poses(self):
        for name,meta in self.rooms.items():
            first=opened(PACK/name/meta['frames'][0]['image'],'RGB')
            allowed=opened(PACK/name/'daylight_mask.png','L')
            glow=opened(PACK/name/'floor_glow_mask.png','L');allowed=ImageChops.lighter(allowed,glow.point(lambda a:255 if a else 0))
            if meta['hearth_position']:
                hx,hy=meta['hearth_position']
                for mask in ('fire','embers','rim'):
                    source=opened(TERRAIN/f'cottage_hearth/masks/{mask}.png','L')
                    target=Image.new('L',allowed.size);target.paste(source,(hx,hy));allowed=ImageChops.lighter(allowed,target)
                steam=[]
                for i in range(1,7):
                    image=opened(PACK/name/f'steam/frame_{i:02}.png');steam.append(image)
                    allowed=ImageChops.lighter(allowed,image.getchannel('A'))
                self.assertGreater(len({p.tobytes() for p in steam}),2)
                glyph=opened(PACK/'props/steam_glyph.png');ox,oy=meta['steam_origin']
                for phase,actual in enumerate(steam):
                    expected=Image.new('RGBA',actual.size)
                    for seed in (0,3):
                        age=(phase+seed)%6;expected.alpha_composite(glyph,(ox-2+age//3,oy-2-age))
                    self.assertEqual(expected.tobytes(),actual.tobytes())
            seen=set()
            for record in meta['frames']:
                frame=opened(PACK/name/record['image'],'RGB');seen.add(frame.tobytes())
                diff=ImageChops.difference(first,frame);diff.paste((0,0,0),(0,0),allowed)
                self.assertIsNone(diff.getbbox(),name)
            self.assertGreater(len(seen),1,name)

    def test_export_layers_reconstruct_scenes_and_actors_remain_unchanged(self):
        hero=opened(ROOT/'assets/characters/caelan/idle_front.png')
        for name,meta in self.rooms.items():
            fx,fy=meta['hero_foot'];objects=meta['objects'];by_id={r['id']:r for r in objects}
            for i in (0,1,17,35):
                expected=opened(PACK/name/'structure.png');expected.alpha_composite(opened(PACK/name/f'lighting/frame_{i+1:02}.png'))
                draws=[]
                for obj in objects:
                    image=opened(TERRAIN/f'cottage_hearth/frames/frame_{i%4+1:02}.png') if obj['id']=='hearth' else opened(ROOT/obj['image_from_repo_root'])
                    self.assertEqual(list(image.size),obj['frame_size'])
                    draws.append((obj['sort_y'],1 if 'parent' in obj else 0,image,obj['position']))
                if meta['steam_origin']:
                    draws.append((by_id['counter']['sort_y'],2,opened(PACK/name/f'steam/frame_{i%6+1:02}.png'),[0,0]))
                draws.append((fy+6,3,hero,[fx-12,fy-30]))
                for _,_,image,pos in sorted(draws,key=lambda r:(r[0],r[1])):expected.alpha_composite(image,tuple(pos))
                actual=opened(PACK/name/meta['frames'][i]['image'],'RGB')
                self.assertEqual(actual.tobytes(),expected.convert('RGB').tobytes())
            for record in meta['frames']:
                image=opened(PACK/name/record['image'],'RGB')
                for y in range(36):
                    for x in range(24):
                        p=hero.getpixel((x,y))
                        if p[3]:self.assertEqual(image.getpixel((fx-12+x,fy-30+y)),p[:3])

    def test_lossless_individual_and_combined_gif_timelines(self):
        for name,meta in self.rooms.items():
            elapsed=0
            with Image.open(PACK/name/'room_review.gif') as gif:
                self.assertEqual(gif.info['loop'],0)
                for i in range(gif.n_frames):
                    gif.seek(i);duration=gif.info['duration'];self.assertEqual(duration%300,0)
                    actual=gif.convert('RGB').crop((0,84,meta['room_size'][0]*4,84+meta['room_size'][1]*4))
                    for tick in range(elapsed//300,(elapsed+duration)//300):
                        native=opened(PACK/name/meta['frames'][tick]['image'],'RGB')
                        self.assertEqual(actual.tobytes(),native.resize((native.width*4,native.height*4),Image.Resampling.NEAREST).tobytes())
                    elapsed+=duration
                self.assertEqual(elapsed,10800);gif.seek(0)
                self.assertEqual(gif.convert('RGB').tobytes(),opened(PACK/name/'room_review.png','RGB').tobytes())
        with Image.open(PACK/'interiors_review.gif') as gif:
            self.assertEqual(gif.n_frames,36)
            for i in range(36):
                gif.seek(i);self.assertEqual(gif.info['duration'],300);actual=gif.convert('RGB')
                for column in self.meta['review_columns']:
                    room=self.rooms[column['room']];native=opened(PACK/column['room']/room['frames'][i]['image'],'RGB')
                    self.assertEqual(actual.crop(box(column['rect'])).tobytes(),native.resize((native.width*2,native.height*2),Image.Resampling.NEAREST).tobytes())
            gif.seek(0);self.assertEqual(gif.convert('RGB').tobytes(),opened(PACK/'interiors_review.png','RGB').tobytes())
        for path in [PACK/'interiors_review.png',PACK/'connections_review.png',*[PACK/name/'room_review.png' for name in self.rooms]]:
            with Image.open(path) as image:self.assertEqual(image.mode,'RGB')


if __name__=='__main__':unittest.main()
