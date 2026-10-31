"""Directional, equipment-consistent checkpoint speakers and portrait identity."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame

from overworld_world import RoadGuard

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'assets/characters/road_guards'


def pixels(image):return pygame.image.tobytes(image,'RGBA')


class GuardArtTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode((480,320))
        self.world=SimpleNamespace(data={'id':'auratia.overworld'})
        self.guard=RoadGuard(self.world,{'id':'test','guard_position':(0,-100)})

    def tearDown(self):pygame.quit()

    def test_four_authored_views_preserve_asymmetric_equipment_without_mirroring(self):
        views={direction:self.guard._frames['idle_'+direction+'_0.png']
               for direction in ('front','back','left','right')}
        self.assertEqual(len({pixels(image) for image in views.values()}),4)
        self.assertNotEqual(pixels(pygame.transform.flip(views['left'],True,False)),pixels(views['right']))
        metadata=json.loads((ART/'animation.json').read_text())
        self.assertEqual(metadata['equipment']['shield_arm'],'physical left')
        self.assertEqual(self.guard.probe_size,(12,8))
        for image in self.guard._frames.values():
            self.assertEqual(image.get_size(),(40,44))
            self.assertEqual(image.get_bounding_rect().bottom,38)

    def test_greeting_finishes_once_and_does_not_cycle_the_hand_while_reading(self):
        self.guard.begin_conversation('left',100)
        self.assertIs(self.guard.sprite(300),self.guard._frames['gesture_left.png'])
        for time in (1300,2300,3300,10000):
            self.assertIn(self.guard.sprite(time),[
                self.guard._frames['idle_left_0.png'],self.guard._frames['idle_left_1.png']])
        self.guard.end_conversation()
        self.assertEqual(self.guard.facing,self.guard.watch_facing)
        self.assertIsNone(self.guard._conversation_started_ms)

    def test_closed_helmet_portrait_is_registered_to_the_guard_not_a_villager(self):
        manifest=json.loads((ROOT/'assets/portraits/eldenmere/portraits.json').read_text())
        profile=json.loads((ROOT/'assets/dialogue/eldenmere.json').read_text())['speakers']['road_guard']
        self.assertEqual(profile['portrait'],'road_guard')
        record=manifest['portraits'][profile['portrait']]
        self.assertEqual(record['sprite_root'],'assets/characters/road_guards')
        self.assertEqual(record['source'],'assets/source/characters/road_guards/portrait_generated.png')
        image=pygame.image.load(str(ROOT/'assets/portraits/eldenmere'/record['file']))
        self.assertEqual(image.get_size(),(72,72))
        civilian=pygame.image.load(str(ROOT/'assets/portraits/eldenmere/male_01_neutral.png')).convert_alpha()
        self.assertNotEqual(pixels(image.convert_alpha()),pixels(civilian))


class GuardInteractionTests(unittest.TestCase):
    def setUp(self):
        import main
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.game=main.Game(fullscreen=False,start_on_title=False,
            save_path=Path(self.temp.name)/'journey.json',settings_path=Path(self.temp.name)/'settings.json')
        self.game.audio.set_music(0);self.game.audio.set_effects(0)
        self.game.opening.restore({'version':1,'stage':'disabled'})
        self.game.world=self.game.overworld_world
        self.game.opening_fade=self.game.transfer_cooldown=0
        self.guards=[actor for actor in self.game.world.npcs if isinstance(actor,RoadGuard)]
        pygame.event.clear()

    def tearDown(self):pygame.quit()

    def start(self,guard,offset):
        game=self.game
        game.player.position.update(guard.position+offset)
        self.assertTrue(game.world.can_stand(game.player.position))
        game.transfer_cooldown=0
        self.assertTrue(game.overworld_travel.interact())
        self.assertIs(game.social.resolve_speaker(),guard)
        self.assertEqual(game.social.data['speakers']['road_guard']['portrait'],'road_guard')

    def clear_approach(self,guard,axis):
        # The first post at each checkpoint has a shelter behind it. Choose
        # real clear ground in the requested cardinal sector, without moving
        # the guard or weakening the regional collision geometry.
        for distance in (24,28,32,36,40):
            for lateral in (0,8,-8,16,-16):
                offset=pygame.Vector2(axis)*distance+pygame.Vector2(-axis[1],axis[0])*lateral
                if offset.length()<=52 and self.game.world.can_stand(guard.position+offset):
                    return offset
        self.fail(('No clear guard approach',guard.data['id'],axis))

    def test_all_four_guards_face_the_actual_approach_then_return_to_watch(self):
        expected={(0,1):'front',(0,-1):'back',(-1,0):'left',(1,0):'right'}
        self.assertEqual(len(self.guards),4)
        positions={guard:guard.position.copy() for guard in self.guards}
        flags=set(self.game.social.flags)
        for guard in self.guards:
            for axis,direction in expected.items():
                with self.subTest(guard=guard.data['id'],approach=direction):
                    offset=self.clear_approach(guard,axis)
                    self.start(guard,offset)
                    self.assertEqual(guard.facing,direction)
                    for other in self.guards:
                        if other is not guard:self.assertEqual(other.facing,other.watch_facing)
                    # A live conversation keeps its initial view instead of
                    # chasing every new player angle around the fixed post.
                    other_approach=self.clear_approach(guard,(-axis[0],-axis[1]))
                    self.game.player.position.update(guard.position+other_approach)
                    self.game.overworld_travel.update(.1)
                    self.assertEqual(guard.facing,direction)
                    self.game.social.cancel()
                    self.game.overworld_travel.update(0)
                    self.assertEqual(guard.facing,guard.watch_facing)
                    self.assertIsNone(self.game.overworld_travel._speaking_guard)
        self.assertEqual(self.game.social.flags,flags)
        for guard in self.guards:self.assertEqual(guard.position,positions[guard])
        for gate in self.game.world.gates:self.assertFalse(self.game.world.can_stand(gate['position']))

    def test_finishing_dialogue_restores_the_selected_watch_immediately(self):
        guard=self.guards[0]
        self.start(guard,(-28,0))
        for _ in range(20):
            if not self.game.social.locked:break
            self.game.social.advance()
        self.assertFalse(self.game.social.locked)
        self.assertEqual(guard.facing,guard.watch_facing)
        self.assertIsNone(self.game.overworld_travel._speaking_guard)

    def test_leaving_the_world_or_restoring_travel_releases_guard_pose(self):
        guard=self.guards[-1]
        self.start(guard,(28,0))
        self.game.social.cancel()
        self.game.overworld_travel.restore()
        self.assertEqual(guard.facing,guard.watch_facing)
        self.assertIsNone(self.game.overworld_travel._speaking_guard)
        self.start(guard,(-28,0))
        self.game.social.cancel()
        self.game.world=self.game.town
        self.game.overworld_travel.update(0)
        self.assertEqual(guard.facing,guard.watch_facing)
        self.assertIsNone(self.game.overworld_travel._speaking_guard)


if __name__=='__main__':unittest.main()
