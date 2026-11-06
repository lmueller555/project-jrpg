"""Reserve conversations have real speakers and no progression side effects."""
import copy
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame

from sanctuary_reserve import HALL_ID, SCENE_ID, ReserveCaretaker, SanctuaryReserve


ROOT = Path(__file__).resolve().parents[1]


class SocialFixture:
    def __init__(self):
        self.data = {'speakers':{'caelan':{'name':'Caelan','portrait':'caelan'}}}
        self.portraits = {}
        self.locked = False
        self.script_identifier = None
        self.lines = None
        self.callback = None

    def start_script(self, lines, on_complete=None, identifier=None):
        if self.locked:return False
        self.locked = True
        self.lines = copy.deepcopy(lines)
        self.callback = on_complete
        self.script_identifier = identifier
        return True

    def finish(self, cancelled=False):
        callback = self.callback
        self.locked = False
        self.script_identifier = None
        self.callback = None
        if callback is not None and not cancelled:callback()


class WorldFixture:
    def __init__(self, identifier=SCENE_ID):
        self.data = {'id':identifier}
        self.size = (1152,768)
        self.npcs = []
        self.blocked = pygame.Mask(self.size)
        self.images = {}

    def image(self, path):
        if path not in self.images:
            self.images[path] = pygame.image.load(str(ROOT/path)).convert_alpha()
        return self.images[path]

    def can_stand(self, point, size=None, ignore_npc=None):return True


class SanctuaryReserveLifeTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode((480,320))
        closed = lambda:SimpleNamespace(is_open=False)
        self.game = SimpleNamespace(world=WorldFixture(),social=SocialFixture(),
            on_title=False, pause=closed(), inventory_ui=closed(),map_open=False,
            quest_ui=SimpleNamespace(journal_open=False),combat=SimpleNamespace(active=False),
            transfer_cooldown=0,player=SimpleNamespace(position=pygame.Vector2(212,480),facing='back'))
        self.reserve = SanctuaryReserve(self.game)

    def tearDown(self):pygame.quit()

    def approach(self, key):
        target = self.reserve.targets[key]
        self.game.player.position.update(target['approach'])
        delta = pygame.Vector2(target['position'])-self.game.player.position
        self.game.player.facing = ('right' if delta.x>0 else 'left') if abs(delta.x)>abs(delta.y) else ('front' if delta.y>0 else 'back')

    def test_scene_owns_three_unique_actors_and_matching_portraits(self):
        self.reserve.ensure_world();self.reserve.ensure_world()
        self.assertEqual(len(self.game.world.npcs),3)
        self.assertEqual(set(self.reserve.actors),
            {'reserve_caretaker','reserve_visitor_slate','reserve_visitor_plum'})
        for actor in self.reserve.actors.values():
            self.assertEqual(set(actor.idles),{'front','back','left','right'})
            speaker = self.game.social.data['speakers'][actor.data['id']]
            self.assertEqual(speaker['portrait'],actor.data['variant'])
            self.assertEqual(speaker['actor_id'],actor.data['id'])
            self.assertIn(speaker['portrait'],self.game.social.portraits)
        self.game.world = WorldFixture('eldenmere')
        self.reserve.update(10)
        self.assertFalse(self.reserve.active)
        self.assertFalse(self.game.world.npcs)

    def test_caretaker_uses_authored_pour_and_holds_bucket_while_speaking(self):
        self.reserve.ensure_world()
        actor = self.reserve.actors['reserve_caretaker']
        self.assertIsInstance(actor,ReserveCaretaker)
        self.reserve.update(7.)
        name, frame = actor._pose()
        self.assertEqual(frame.get('effect'),'pour')
        self.assertEqual(actor.sprite(0).get_size(),(48,48))
        actor.draw_foreground(pygame.Surface((480,320)),(100,200))
        self.approach('caretaker')
        self.assertTrue(self.reserve.interact())
        clock = actor.clock
        self.reserve.update(4)
        self.assertEqual(actor.clock,clock)
        self.assertTrue(actor.conversation_ready)
        self.assertEqual(actor._pose()[0],'idle_full.'+actor.facing)
        self.assertEqual(actor.sprite(0).get_size(),(48,48))
        self.game.social.finish()
        self.assertFalse(actor.conversation_ready)
        self.assertEqual(actor.facing,'right')

    def test_cancel_and_scene_departure_release_speech_pose_without_callbacks(self):
        self.approach('caretaker');self.assertTrue(self.reserve.interact())
        actor = self.reserve.actors['reserve_caretaker']
        self.game.social.finish(cancelled=True)
        self.reserve.update(.01)
        self.assertFalse(actor.conversation_ready)
        self.approach('caretaker');self.assertTrue(self.reserve.interact())
        self.game.world = WorldFixture('eldenmere')
        self.reserve.update(.01)
        self.assertFalse(actor.conversation_ready)
        self.assertFalse(self.reserve.interaction_hint())

    def test_views_menus_distance_and_facing_gate_interaction_and_animation(self):
        self.reserve.ensure_world();actor = self.reserve.actors['reserve_caretaker']
        self.approach('caretaker')
        self.assertIn('caretaker',self.reserve.interaction_hint())
        self.game.player.facing = 'front'
        self.assertFalse(self.reserve.interact())
        self.approach('caretaker')
        self.game.pause.is_open = True
        self.assertFalse(self.reserve.interact());self.reserve.update(20)
        self.assertEqual(actor.clock,0)
        self.game.pause.is_open = False
        self.game.map_open = True
        self.assertFalse(self.reserve.interact());self.reserve.update(20)
        self.assertEqual(actor.clock,0)
        self.game.map_open = False
        self.game.player.position.update(600,600)
        self.assertFalse(self.reserve.interact())

    def test_a_wall_prevents_interaction_from_a_nearby_but_separate_path(self):
        self.approach('cave')
        self.game.player.position.y += 15
        for x in range(980,1035):self.game.world.blocked.set_at((x,412),1)
        self.assertFalse(self.reserve.interact())

    def test_all_observations_are_non_rewarding_and_hall_has_no_duplicate_people(self):
        self.reserve.ensure_world()
        for scene, keys in ((SCENE_ID,('boundary','grove','cave','survey')),
                            (HALL_ID,('records','remembrance','cabinet'))):
            self.game.world = self.reserve._world if scene == SCENE_ID else WorldFixture(HALL_ID)
            for key in keys:
                self.approach(key)
                self.assertTrue(self.reserve.interact(),key)
                self.assertEqual({line['speaker'] for line in self.game.social.lines},{'caelan'})
                self.assertTrue(all(set(line)=={'speaker','text'} for line in self.game.social.lines))
                self.game.social.finish()
            if scene == HALL_ID:self.assertFalse(self.game.world.npcs)


if __name__ == '__main__':unittest.main()
