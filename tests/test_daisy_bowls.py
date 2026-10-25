"""Registered fill-state art and two accessible, static bowls in Daisy's home."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import json
from pathlib import Path
import unittest

import pygame
from PIL import Image
import main

ROOT=main.ROOT
PACK=ROOT/'assets/terrain/eldenmere/liam_home/bowls'


def read(path):return json.loads(path.read_text())
def pixels(im):return list(getattr(im,'get_flattened_data',im.getdata)())


class DaisyBowlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game=main.Game(fullscreen=False,start_on_title=False)
        cls.room=cls.game._scene_by_id('liam_house')
        cls.meta=read(PACK/'bowls.json')
        cls.recipe=read(ROOT/'assets/maps/eldenmere/liam_house/house.json')

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_food_and_water_have_full_half_and_empty_native_variants(self):
        self.assertFalse(self.meta['animated'])
        self.assertEqual(self.meta['frame_size'],[24,24])
        self.assertEqual(set(self.meta['bowls']),{'food','water'})
        wood=read(ROOT/self.meta['wood_palette_source'])['palette']
        water=read(ROOT/self.meta['water_palette_source'])['palette']
        colors=set(wood.values())|set(water.values())|set(self.meta['food_palette'].values())
        allowed={tuple(bytes.fromhex(c[1:]))+(255,) for c in colors}
        bounds=set()
        for kind,record in self.meta['bowls'].items():
            self.assertEqual(list(record['states']),['full','half_full','empty'])
            self.assertEqual([s['fill_fraction'] for s in record['states'].values()],[1,.5,0])
            images=[]
            for state,spec in record['states'].items():
                im=Image.open(ROOT/spec['image_from_repo_root']).convert('RGBA');images.append(im.tobytes())
                self.assertEqual(im.size,(24,24));bounds.add(im.getbbox())
                self.assertEqual(set(im.getchannel('A').tobytes()),{0,255})
                self.assertTrue(all(not p[3] or p in allowed for p in pixels(im)))
            self.assertEqual(len(set(images)),3)
            counts=[s['content_pixels'] for s in record['states'].values()]
            self.assertGreater(counts[0],counts[1]);self.assertGreater(counts[1],0);self.assertEqual(counts[2],0)
            self.assertGreater(counts[1]/counts[0],.25)
            self.assertLess(counts[1]/counts[0],.75)
        self.assertEqual(len(bounds),1)

    def test_only_the_recessed_contents_change_between_states(self):
        mask=Image.open(PACK/self.meta['content_mask']).convert('L')
        for kind,record in self.meta['bowls'].items():
            empty=Image.open(ROOT/record['states']['empty']['image_from_repo_root']).convert('RGBA')
            for state,spec in record['states'].items():
                im=Image.open(ROOT/spec['image_from_repo_root']).convert('RGBA')
                for y in range(24):
                    for x in range(24):
                        if not mask.getpixel((x,y)):self.assertEqual(im.getpixel((x,y)),empty.getpixel((x,y)))
        food=Image.open(ROOT/self.meta['bowls']['food']['states']['empty']['image_from_repo_root'])
        water=Image.open(ROOT/self.meta['bowls']['water']['states']['empty']['image_from_repo_root'])
        self.assertEqual(food.tobytes(),water.tobytes())

    def test_retained_layers_and_spritesheet_reconstruct_all_six_states(self):
        sheet=Image.open(PACK/self.meta['sheet']).convert('RGBA')
        self.assertEqual(sheet.size,(72,48))
        for row,kind in enumerate(self.meta['sheet_rows']):
            for col,state in enumerate(self.meta['sheet_columns']):
                record=self.meta['bowls'][kind]['states'][state]
                expected=Image.open(ROOT/record['image_from_repo_root']).convert('RGBA')
                rebuilt=Image.new('RGBA',(24,24))
                for relative in record['layers_from_repo_root']:rebuilt.alpha_composite(Image.open(ROOT/relative).convert('RGBA'))
                self.assertEqual(rebuilt.tobytes(),expected.tobytes())
                self.assertEqual(sheet.crop((col*24,row*24,col*24+24,row*24+24)).tobytes(),expected.tobytes())

    def test_bowls_are_side_by_side_full_and_static_with_future_states_linked(self):
        entities={r['id']:r for r in self.room.entities}
        food=entities['daisy_food_bowl'];water=entities['daisy_water_bowl']
        self.assertEqual(food['position'][1],water['position'][1])
        self.assertEqual(water['position'][0]-food['position'][0],20)
        self.assertGreater(food['position'][0],self.recipe['rug']['position'][0]+self.recipe['rug']['frame_size'][0])
        for entity in (food,water):
            self.assertEqual(entity['state'],'full')
            self.assertEqual(entity['frames'],[entity['state_images']['full']])
            self.assertEqual(len(entity['surfaces']),1)
            self.assertEqual(set(entity['state_images']),{'full','half_full','empty'})
            self.assertTrue(all((ROOT/p).is_file() for p in entity['state_images'].values()))
            self.assertEqual(entity['content_target'],[entity['position'][0]+12,entity['position'][1]+12])
        self.assertEqual([n.data['id'] for n in self.room.npcs],self.recipe['household'])
        self.assertTrue(all('routine' not in n.data for n in self.room.npcs))

    def test_small_footprints_and_refill_access_do_not_block_existing_residents(self):
        for record in self.recipe['bowls']:
            entity=next(e for e in self.room.entities if e['id']==record['id'])
            x,y=record['position'];fx,fy,fw,fh=self.meta['floor_rect']
            self.assertEqual(entity['floor_rect'],[x+fx,y+fy,fw,fh])
            self.assertFalse(self.room.can_stand(pygame.Rect(entity['floor_rect']).center,(2,2)))
            self.assertEqual(self.room.data['destinations'][record['id']],record['access'])
            self.assertTrue(self.room.can_stand(record['access']))
            for npc in self.room.npcs:self.assertFalse(npc.blocker.colliderect(entity['floor_rect']))
        self.assertTrue(self.room.can_stand(self.room.data['spawn']))
        self.assertTrue(self.room.can_stand(self.room.data['destinations']['daisy_rest_space']))


if __name__=='__main__':unittest.main()
