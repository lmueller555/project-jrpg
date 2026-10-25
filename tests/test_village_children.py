"""Five children, native four-pose motion packs and accessible compact beds."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from collections import deque
import hashlib
import json
from pathlib import Path
import re
import unittest

import pygame
from PIL import Image
import main

ROOT=main.ROOT
EXPECTED={'tessa':(10,'home_a',28),'finn':(6,'home_a',22),
          'rowan':(9,'home_b',27),'ada':(7,'home_b',24),'pippa':(8,'home_c',26)}
DIRECTIONS=('front','left','right','back')


def read(path):return json.loads(path.read_text())


def resolve(base,value):
    path=Path(value)
    return path if path.is_absolute() else ROOT/path if path.parts[:1]==('assets',) else base/path


def colors(data):
    if isinstance(data,str):
        if re.fullmatch(r'#[0-9a-fA-F]{6}',data):yield tuple(bytes.fromhex(data[1:]))+(255,)
    elif isinstance(data,dict):
        for value in data.values():yield from colors(value)
    elif isinstance(data,list):
        for value in data:yield from colors(value)


class VillageChildrenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game=main.Game(fullscreen=False,start_on_title=False)
        cls.registry=read(ROOT/'assets/maps/eldenmere/households/households.json')
        cls.families={f['home']:f for f in cls.registry['households']}
        cls.rooms={home:cls.game._scene_by_id(home) for home in cls.families}

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_five_named_children_have_correct_ages_and_linked_families(self):
        self.assertEqual(set(self.registry['children']),set(EXPECTED))
        found={}
        for home,family in self.families.items():
            room=self.rooms[home];parents=[family['mother']['id'],family['father']['id']]
            self.assertEqual(room.data['household'],parents+[c['id'] for c in family['children']])
            self.assertEqual(len(room.npcs),{'home_a':3,'home_b':4,'home_c':3}[home])
            for child in family['children']:
                name=child['id'];age,expected_home,height=EXPECTED[name]
                self.assertEqual(home,expected_home);self.assertEqual(child['age_years'],age)
                actor=next(a for a in room.npcs if a.data['id']==name)
                self.assertIsInstance(actor,main.StationaryNPC)
                self.assertEqual(actor.data['age_years'],age)
                self.assertEqual(actor.data['parents'],parents)
                self.assertEqual(actor.data['family_role'],'child')
                self.assertEqual(actor.data['home_scene'],home)
                self.assertEqual(actor.data['household_id'],family['id'])
                self.assertTrue(actor.data['sprite'].startswith(f'assets/characters/{name}/'))
                self.assertNotIn(name,found);found[name]=actor
        self.assertEqual(set(found),set(EXPECTED))

    def test_each_child_has_one_compact_twin_bed_and_private_room_collision(self):
        pack=read(ROOT/'assets/terrain/eldenmere/child_beds/beds.json')
        self.assertEqual(pack['frame_size'],[32,48])
        all_beds=[];collisions=[]
        for home,family in self.families.items():
            room=self.rooms[home];collisions.append(room.data['collision'])
            self.assertTrue(room.data['collision'].endswith(f'{home}/collision.png'))
            parent_bed=next(e for e in room.entities if e['id']=='bed')
            self.assertEqual(parent_bed['position'],[36,96])
            for child in family['children']:
                entity=next(e for e in room.entities if e['id']==child['id']+'_bed')
                self.assertEqual(entity['owner_child'],child['id'])
                self.assertEqual(entity['surfaces'][0].get_size(),(32,48))
                x,y=child['bed']['position'];fx,fy,fw,fh=pack['floor_rect']
                self.assertEqual(entity['floor_rect'],[x+fx,y+fy,fw,fh])
                self.assertFalse(room.can_stand((x+fx+fw/2,y+fy+fh/2),(2,2)))
                self.assertTrue(room.can_stand(child['bed']['access']),child['id'])
                all_beds.append(entity['id'])
        self.assertEqual(len(all_beds),5);self.assertEqual(len(set(all_beds)),5)
        self.assertEqual(len(set(collisions)),3)
        shared=Image.open(ROOT/'assets/maps/eldenmere/building_interiors/rooms/standard/collision.png').convert('L')
        for family in self.families.values():
            for child in family['children']:
                x,y=child['bed']['position'];fx,fy,fw,fh=pack['floor_rect']
                self.assertEqual(shared.getpixel((x+fx+fw//2,y+fy+fh//2)),0)

    def test_family_footprints_leave_all_beds_furnishings_and_exits_reachable(self):
        for home,room in self.rooms.items():
            for actor in room.npcs:
                self.assertTrue(room.can_stand(actor.position,actor.data['probe_size'],actor),(home,actor.data['id']))
            start=tuple(room.data['spawn']);self.assertTrue(room.can_stand(start))
            remaining={tuple(p) for p in room.data['destinations'].values()}
            remaining.update(tuple(d.data['anchor']) for d in room.doors)
            queue=deque([start]);seen={start}
            while queue and remaining:
                point=queue.popleft();remaining.discard(point)
                for candidate in ((point[0]-2,point[1]),(point[0]+2,point[1]),(point[0],point[1]-2),(point[0],point[1]+2)):
                    if candidate not in seen:
                        seen.add(candidate)
                        if room.can_stand(candidate):queue.append(candidate)
            self.assertFalse(remaining,(home,remaining))

    def test_home_reentry_reuses_children_and_the_gardener_remains_one_person(self):
        for home,room in self.rooms.items():
            identities={a.data['id']:id(a) for a in room.npcs}
            self.game.world=self.game.town;self.game.transfer_cooldown=0
            self.assertTrue(self.game.enter(next(d for d in self.game.town.doors if d.data['id']==home)))
            self.assertEqual(identities,{a.data['id']:id(a) for a in self.game.world.npcs})
            self.game.transfer_cooldown=0;self.assertTrue(self.game.enter(room.doors[0]))
            self.assertIs(self.game._scene_by_id(home),room)
        actors=[a for scene in self.game.scenes.values() for a in scene.npcs]
        self.assertEqual(sum(a.data['id']=='sanctuary_gardener' for a in actors),1)
        for name in EXPECTED:self.assertEqual(sum(a.data['id']==name for a in actors),1)
        liam=self.game._scene_by_id('liam_house')
        self.assertEqual(liam.data['household'],['liam','liam_mother','liam_father','daisy'])
        self.assertTrue(all(a.data['id'] not in EXPECTED for a in liam.npcs))

    def test_directional_idles_have_child_scale_palette_and_clear_eyes(self):
        for name,(age,home,height) in EXPECTED.items():
            base=ROOT/'assets/characters'/name;meta=read(base/'character.json')
            self.assertEqual(meta['id'],name);self.assertEqual(meta['age_years'],age)
            self.assertEqual(meta['home'],home);self.assertEqual(meta['frame_size'],[24,36])
            self.assertEqual(meta['visible_height_px'],height)
            allowed=set(colors(read(base/'palette.json')))
            self.assertTrue(allowed)
            for direction in DIRECTIONS:
                image=Image.open(base/f'idle_{direction}.png').convert('RGBA')
                detail=read(base/f'idle_{direction}.json')
                self.assertEqual(image.size,(24,36));self.assertEqual(image.getbbox()[3],35)
                self.assertEqual(set(image.getchannel('A').tobytes()),{0,255})
                if direction=='front':self.assertEqual(image.getbbox()[3]-image.getbbox()[1],height)
                eyes=detail['eyes']['top_pixels']
                self.assertEqual(len(eyes),0 if direction=='back' else 2 if direction=='front' else 1)
                for x,y in eyes:self.assertEqual(image.getpixel((x,y))[3],255)
                self.assertTrue(all(not pixel[3] or pixel in allowed for pixel in getattr(image,'get_flattened_data',image.getdata)()))
                rebuilt=Image.new('RGBA',image.size)
                self.assertTrue(detail['layers_from_repo_root'])
                for layer in detail['layers_from_repo_root']:rebuilt.alpha_composite(Image.open(ROOT/layer).convert('RGBA'))
                self.assertEqual(rebuilt.tobytes(),image.tobytes())
            for path,digest in meta.get('approved_reference_png_sha256',{}).items():
                self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)
            recipe=ROOT/'assets/source/characters'/name/'recipe.json'
            if recipe.exists():
                for path,digest in read(recipe).get('approved_png_sha256',{}).items():
                    self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)
        self.assertLess(EXPECTED['finn'][2],26)
        self.assertGreater(EXPECTED['tessa'][2],26)

    def test_all_walks_and_runs_have_four_distinct_retained_pixel_poses(self):
        for name in EXPECTED:
            root=ROOT/'assets/characters'/name
            allowed=set(colors(read(root/'palette.json')))
            for direction in DIRECTIONS:
                sets={}
                for action,duration in (('walk',140),('run',100)):
                    folder=root/f'{action}_{direction}';meta=read(folder/'animation.json')
                    self.assertEqual(len(meta['frames']),4)
                    unique=set()
                    for record in meta['frames']:
                        self.assertEqual(record['duration_ms'],duration)
                        image=Image.open(resolve(folder,record['file'])).convert('RGBA')
                        self.assertEqual(image.size,(24,36));self.assertEqual(set(image.getchannel('A').tobytes()),{0,255})
                        unique.add(image.tobytes())
                        self.assertTrue(all(not pixel[3] or pixel in allowed for pixel in getattr(image,'get_flattened_data',image.getdata)()))
                        self.assertTrue(record['layers_from_repo_root'])
                        rebuilt=Image.new('RGBA',image.size)
                        for layer in record['layers_from_repo_root']:rebuilt.alpha_composite(Image.open(ROOT/layer).convert('RGBA'))
                        self.assertEqual(rebuilt.tobytes(),image.tobytes())
                        if 'upper_body_offset' in record and 'shoulder_offset' in record:
                            self.assertEqual(record['upper_body_offset'],record['shoulder_offset'])
                    self.assertEqual(len(unique),4,(name,action,direction));sets[action]=unique
                self.assertNotEqual(sets['walk'],sets['run'],(name,direction))
        protected=read(ROOT/'assets/characters/liam_family/play_routine/animations.json')['approved_png_sha256']
        for path,digest in protected.items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)


if __name__=='__main__':unittest.main()
