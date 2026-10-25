"""The new home is a connected, enterable household, separate from the Venns."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'

import unittest
import pygame
import main


class LiamFamilyHomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game=main.Game(fullscreen=False,start_on_title=False)
        cls.recipe=main.read_json(main.ROOT/'assets/maps/eldenmere/liam_house/house.json')
        cls.room=main.World(main.ROOT/cls.game.town.data['interior_scenes']['liam_house'],cls.game.town._images)

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_home_is_south_of_sanctuary_on_lower_ground_without_moving_other_buildings(self):
        world=self.game.town;recipe=self.recipe
        self.assertLess(recipe['position'][0]+144,366)  # Entire roof west of lane.
        self.assertGreaterEqual(recipe['position'][1],384)  # South of terrace wall.
        home_rect=pygame.Rect(recipe['ground_rect'])
        original=main.read_json(main.ROOT/'assets/maps/eldenmere/terrain_foundation/scene.json')
        for building in original['buildings']:
            self.assertFalse(home_rect.colliderect(building['ground_rect_pixels']))
        self.assertFalse(world.can_stand(home_rect.center))
        self.assertTrue(world.can_stand(recipe['approach']))
        self.assertTrue(world.can_stand((384,546)))
        for x in range(288,385,2):self.assertTrue(world.can_stand((x,546)),x)
        self.assertIn('liam_house',{x['id'] for x in world.data['landmarks']})

    def test_family_assignment_does_not_replace_venn_or_place_npcs_early(self):
        expected=['liam','liam_mother','liam_father','daisy']
        self.assertEqual(self.room.data['household'],expected)
        self.assertEqual(self.room.data['npcs'],[])
        self.assertEqual(self.room.data['quests'],[])
        family=main.read_json(main.ROOT/'assets/characters/liam_family/family.json')
        self.assertEqual(family['home']['scene'],'liam_house')
        self.assertNotEqual(self.game.town.data['interior_scenes']['venn'],self.game.town.data['interior_scenes']['liam_house'])
        venn=main.read_json(main.ROOT/self.game.town.data['interior_scenes']['venn'])
        self.assertEqual(venn['name'],'Venn family cottage')
        self.assertEqual({x['id'] for x in self.game.town.data['persistent_npcs']},{'mother_serene','tomas'})

    def test_wide_furnished_room_has_two_beds_four_seats_and_clear_access(self):
        world=self.room
        self.assertEqual(world.data['size_tiles'],[16,10])
        self.assertEqual(world.size,(432,336))
        ids={e['id'] for e in world.entities}
        self.assertTrue({'parents_bed','liam_bed','chair_north','chair_south','chair_east','chair_west','hearth','counter','washbasin','pantry'}<=ids)
        for target in world.data['destinations'].values():self.assertTrue(world.can_stand(target),target)
        self.assertTrue(world.can_stand(world.data['spawn']))
        self.assertFalse(world.can_stand((60,240)))  # Liam's bed footprint.
        self.assertFalse(world.can_stand((174,150)))  # Retained partition.
        self.assertTrue(world.can_stand(self.recipe['daisy_rest_space'],(12,8)))

    def test_native_animated_exterior_and_matching_door(self):
        entity=next(x for x in self.game.town.entities if x['id']=='liam_house')
        self.assertEqual(entity['position'],self.recipe['position'])
        self.assertEqual(len(entity['surfaces']),18)
        self.assertGreater(len({pygame.image.tobytes(im,'RGBA') for im in entity['surfaces']}),1)
        door=next(d for d in self.game.town.doors if d.data['id']=='liam_house')
        rect=pygame.Rect(door.data['position'],door.frames[0].get_size())
        rect.move_ip(-entity['position'][0],-entity['position'][1])
        self.assertEqual(pygame.image.tobytes(entity['surfaces'][0].subsurface(rect),'RGBA'),pygame.image.tobytes(door.frames[0],'RGBA'))
        self.assertEqual(len(door.frames),5)
        self.assertEqual(door.data['destination'],self.game.town.data['interior_scenes']['liam_house'])
        self.assertEqual(self.room.doors[0].data['arrival_door'],'liam_house')


if __name__=='__main__':unittest.main()
