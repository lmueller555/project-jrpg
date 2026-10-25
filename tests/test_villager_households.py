"""Three household assignments, five new residents and one existing gardener."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from collections import deque
import json
import unittest
import pygame
import main


class VillagerHouseholdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game=main.Game(fullscreen=False,start_on_title=False)
        cls.registry=json.loads((main.ROOT/'assets/maps/eldenmere/households/households.json').read_text())
        cls.rooms={f['home']:cls.game._scene_by_id(f['home']) for f in cls.registry['households']}

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_three_pairs_and_exactly_five_new_residents(self):
        self.assertEqual([f['home'] for f in self.registry['households']],['home_a','home_b','home_c'])
        placed=[]
        for family in self.registry['households']:
            room=self.rooms[family['home']]
            self.assertEqual(room.data['household'],[family['mother']['id'],family['father']['id']])
            for role in ('mother','father'):
                m=family[role]
                actors=self.game.town.npcs if m.get('placement') else room.npcs
                actor=next(n for n in actors if n.data['id']==m['id'])
                self.assertEqual(actor.data['home_scene'],family['home'])
                self.assertEqual(actor.data['family_role'],role)
                self.assertEqual(actor.data['partner_id'],family['father' if role=='mother' else 'mother']['id'])
                if not m.get('placement'):
                    placed.append(actor);self.assertIsInstance(actor,main.StationaryNPC)
                    self.assertTrue(actor.data['sprite'].startswith(m['sprite_root']))
        self.assertEqual(len(placed),5);self.assertEqual(len({a.data['id'] for a in placed}),5)

    def test_gardener_is_not_cloned_or_replaced(self):
        all_actors=[a for w in self.game.scenes.values() for a in w.npcs]
        gardeners=[a for a in all_actors if a.data['id']=='sanctuary_gardener']
        self.assertEqual(len(gardeners),1);g=gardeners[0]
        self.assertIn(g,self.game.town.npcs)
        self.assertEqual(g.data['routine'],'watering')
        self.assertEqual(g.data['home_scene'],'home_a')
        self.assertNotIn(g,self.rooms['home_a'].npcs)
        self.assertEqual(g.behavior['water_source'],'well')
        self.assertEqual(g.behavior['rest_range_ms'],[180000,300000])

    def test_residents_leave_every_furnishing_and_exit_reachable(self):
        for room in self.rooms.values():
            for a in room.npcs:self.assertTrue(room.can_stand(a.position,a.data['probe_size'],a),(room.data['id'],a.data['id']))
            start=tuple(room.data['spawn']);self.assertTrue(room.can_stand(start))
            queue=deque([start]);seen={start};remaining={tuple(p) for p in room.data['destinations'].values()}
            remaining.update(tuple(d.data['anchor']) for d in room.doors)
            while queue and remaining:
                p=queue.popleft();remaining.discard(p)
                for q in ((p[0]-2,p[1]),(p[0]+2,p[1]),(p[0],p[1]-2),(p[0],p[1]+2)):
                    if q not in seen:
                        seen.add(q)
                        if room.can_stand(q):queue.append(q)
            self.assertFalse(remaining,(room.data['id'],remaining))

    def test_cached_rooms_reuse_same_people_and_have_no_dialogue(self):
        for key,room in self.rooms.items():
            self.assertIs(self.game._scene_by_id(key),room)
            ids=[id(a) for a in room.npcs]
            self.game.world=self.game.town
            self.assertTrue(self.game.enter(next(d for d in self.game.town.doors if d.data['id']==key)))
            self.assertEqual(ids,[id(a) for a in self.game.world.npcs])
            self.game.transfer_cooldown=0
            self.assertTrue(self.game.enter(room.doors[0]))
            self.game.transfer_cooldown=0
            for a in room.npcs:self.assertNotIn(a.data['id'],self.game.social.profiles)

    def test_story_and_liam_homes_retain_assignments(self):
        for key in ('halden','elira','venn'):
            room=self.game._scene_by_id(key)
            self.assertEqual(room.data.get('household',[]),[]);self.assertEqual(room.data['npcs'],[])
        room=self.game._scene_by_id('liam_house')
        self.assertEqual(room.data['household'],['liam','liam_mother','liam_father','daisy'])
        self.assertEqual(self.registry['children'],'unassigned')


if __name__=='__main__':unittest.main()
