"""Exploration followers preserve traversed routes and authored story ownership."""
import os
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from party_travel import PartyTravel, SPACING, _TravelActor
from social import SocialSystem


class World:
    def __init__(self, obstacles=(), *, is_overworld=False):
        self.npcs = []
        self.obstacles = list(obstacles)
        self.is_overworld = is_overworld
        self.data = {'id': 'test_room'}

    def can_stand(self, position):
        probe = pygame.Rect(round(position[0])-3, round(position[1])-3, 6, 6)
        return (0 <= probe.left and probe.right <= 240 and 0 <= probe.top and probe.bottom <= 180
                and not any(probe.colliderect(block) for block in self.obstacles))


def actor(identifier):
    return SimpleNamespace(identifier=identifier, position=pygame.Vector2(), facing='front',
                           moving=False, visible=False, walk_ms=0., story_following=True,
                           trail_distance=0., draw_anchor=(12, 34))


def game(active=('caelan', 'lucan', 'rhea'), world=None):
    members = {identifier: {'available': True} for identifier in ('caelan', 'mira', 'lucan', 'rhea', 'edran')}
    return SimpleNamespace(
        world=world or World(), player=SimpleNamespace(position=pygame.Vector2(30, 70),
                                                       facing='front', running=False),
        party=SimpleNamespace(active_ids=active, members=members),
        social=SimpleNamespace(active=False, locked=False), pause=SimpleNamespace(is_open=False))


def walk(controller, destination, speed=60):
    player = controller.game.player
    delta = pygame.Vector2(destination)-player.position
    steps = max(1, round(delta.length()))
    step = delta/steps
    observations = []
    for _ in range(steps):
        player.position += step
        controller.update(1/speed)
        observations.append(tuple(tuple(actor.position) for actor in controller.actors()))
    return observations


class PartyTravelTests(unittest.TestCase):
    def test_story_arrival_publishes_the_same_passive_actor_before_leader_moves(self):
        context = game(active=('caelan','mira'))
        context.player.position.update(100,80)
        authored = SimpleNamespace(party_travelling=False)
        context.mill_quest = SimpleNamespace(mira=authored)
        travel = PartyTravel(context,actor_factory=actor)
        self.assertTrue(travel.stage_companion('mira',(100,104),facing='back'))
        mira, = travel.actors()
        self.assertTrue(authored.party_travelling)
        self.assertEqual(tuple(mira.position),(100,104))
        self.assertEqual(context.world.npcs,[])
        for _ in range(10):travel.update(1/60)
        self.assertIs(travel.actors()[0],mira)
        self.assertTrue(context.world.can_stand(mira.position))
        walk(travel,(140,80))
        self.assertIs(travel.actors()[0],mira)
        self.assertEqual(context.world.npcs,[])

    def test_story_arrival_cannot_introduce_an_unrecruited_or_blocked_follower(self):
        context = game(active=('caelan','mira'),world=World((pygame.Rect(95,88,10,8),)))
        context.player.position.update(100,80)
        travel = PartyTravel(context,actor_factory=actor)
        # Both endpoints are clear, but the short route crosses a solid wall.
        self.assertFalse(travel.stage_companion('mira',(100,110)))
        self.assertEqual(travel.actors(),())
        self.assertEqual(travel._actors,{})
        self.assertFalse(travel.stage_companion('lucan',(75,80)))
        self.assertEqual(travel._actors,{})
        context.world.is_overworld=True
        self.assertFalse(travel.stage_companion('mira',(75,80)))

    def test_two_authored_followers_remain_at_their_stations_until_the_leader_moves(self):
        context = game(active=('caelan','mira','lucan'))
        context.player.position.update(100,80)
        context.mill_quest = SimpleNamespace(mira=SimpleNamespace(party_travelling=False))
        travel = PartyTravel(context,actor_factory=actor)
        # These are the Sanctuary handoff offsets, including a >64px pair leg.
        positions = {'mira':(68,106),'lucan':(124,74)}
        self.assertTrue(travel.stage_companions(positions,{'mira':'back','lucan':'left'}))
        followers = travel.actors()
        self.assertEqual([value.identifier for value in followers],['mira','lucan'])
        for _ in range(120):travel.update(1/60)
        self.assertEqual([tuple(value.position) for value in followers],[(68,106),(124,74)])
        self.assertEqual([value.facing for value in followers],['back','left'])
        self.assertTrue(all(value.visible and not value.moving and value.walk_ms==0 for value in followers))
        self.assertEqual(tuple(travel._points[0]),positions['lucan'])
        self.assertEqual(tuple(travel._points[-1]),tuple(context.player.position))
        self.assertTrue(context.mill_quest.mira.party_travelling)
        self.assertEqual(context.world.npcs,[])
        walk(travel,(140,80))
        self.assertEqual(travel.actors(),followers)
        self.assertTrue(all(context.world.can_stand(value.position) for value in followers))
        self.assertTrue(all(tuple(value.position)!=positions[value.identifier] for value in followers))

    def test_invalid_multi_follower_handoff_does_not_reset_an_existing_formation(self):
        context = game(active=('caelan','mira','lucan'))
        context.player.position.update(100,80)
        travel = PartyTravel(context,actor_factory=actor)
        positions = {'mira':(68,106),'lucan':(124,74)}
        self.assertTrue(travel.stage_companions(positions))
        followers = travel.actors()
        def snapshot():
            return ([tuple(point) for point in travel._points],list(travel._distances),
                    [(id(value),tuple(value.position),value.visible,value.trail_distance,value.facing) for value in followers])
        before = snapshot()
        # Clear endpoints, but the tail-to-first-follower chord crosses a wall.
        context.world.obstacles.append(pygame.Rect(92,84,8,10))
        self.assertTrue(all(context.world.can_stand(point) for point in positions.values()))
        self.assertFalse(travel.stage_companions(positions))
        self.assertEqual(snapshot(),before)
        context.world.obstacles.clear()
        for invalid in ({'mira':(100,105),'lucan':(100,110)},
                        {'mira':(100,80),'lucan':(124,74)},
                        {'mira':(10,150),'lucan':(124,74)},
                        {'edran':(68,106),'lucan':(124,74)}):
            self.assertFalse(travel.stage_companions(invalid))
            self.assertEqual(snapshot(),before)
        self.assertFalse(travel.stage_companions(positions,{'mira':'north'}))
        self.assertEqual(snapshot(),before)
        self.assertEqual(travel.actors(),followers)

    def test_mq03_story_lucan_is_not_duplicated_by_a_preexisting_roster_member(self):
        context=game(active=('caelan','mira','lucan'))
        context.regent_quest=SimpleNamespace(sanctuary_escort_active=True)
        travel=PartyTravel(context,actor_factory=actor)
        travel.update(1/60)
        walk(travel,(130,70))
        self.assertEqual([value.identifier for value in travel.actors()],['mira'])
        context.regent_quest.sanctuary_escort_active=False
        travel.update(1/60)
        self.assertEqual([value.identifier for value in travel.actors()],['mira','lucan'])

    def test_winding_route_keeps_both_followers_on_the_traversed_side_of_wall(self):
        world = World((pygame.Rect(50, 30, 20, 60),))
        context = game(world=world)
        travel = PartyTravel(context, actor_factory=actor)
        travel.update(1/60)
        for point in ((30, 110), (90, 110), (90, 60)):
            samples = walk(travel, point)
            for positions in samples:
                for position in positions:self.assertTrue(world.can_stand(position), position)
        followers = travel.actors()
        self.assertEqual([value.identifier for value in followers], ['lucan', 'rhea'])
        self.assertAlmostEqual(followers[0].position.x, 90)
        self.assertAlmostEqual(followers[0].position.y, 60+SPACING)
        self.assertAlmostEqual(followers[1].position.x, 90)
        self.assertAlmostEqual(followers[1].position.y, 60+2*SPACING)
        self.assertEqual(followers[0].facing, 'back')
        self.assertTrue(followers[0].moving)
        self.assertGreater(followers[0].walk_ms, 0)
        self.assertEqual(world.npcs, [])

    def test_door_transfer_waits_for_clear_entry_and_never_reuses_old_coordinates(self):
        context = game()
        travel = PartyTravel(context, actor_factory=actor)
        travel.update(1/60)
        walk(travel, (110, 70))
        self.assertEqual(len(travel.actors()), 2)
        context.world = World()
        context.player.position.update(20, 20)
        self.assertEqual(travel.actors(), ())
        travel.update(1/60)
        self.assertEqual(travel.actors(), ())
        walk(travel, (40, 20))
        self.assertEqual(travel.actors(), ())
        walk(travel, (70, 20))
        self.assertEqual(len(travel.actors()), 2)
        for follower in travel.actors():
            self.assertEqual(follower.position.y, 20)
            self.assertGreaterEqual(follower.position.distance_to(context.player.position), 12)
        self.assertGreaterEqual(travel.actors()[0].position.distance_to(travel.actors()[1].position), 12)

    def test_changed_formation_and_availability_remove_reserves_without_healing(self):
        context = game()
        context.party.characters = {'lucan': SimpleNamespace(current_hp=0)}
        travel = PartyTravel(context, actor_factory=actor)
        travel.update(1/60)
        walk(travel, (100, 70))
        self.assertEqual([value.identifier for value in travel.actors()], ['lucan', 'rhea'])
        self.assertNotIn('edran', travel._actors)
        context.party.active_ids = ('caelan', 'rhea')
        travel.update(1/60)
        self.assertEqual([value.identifier for value in travel.actors()], ['rhea'])
        self.assertEqual(context.party.characters['lucan'].current_hp, 0)
        context.party.members['rhea']['available'] = False
        self.assertEqual(travel.actors(), ())

    def test_mira_routine_suspends_without_moving_then_releases_to_story_and_reserve(self):
        context = game(('caelan', 'mira'))
        mira = SimpleNamespace(position=pygame.Vector2(160, 40), quest_mode=False,
                               story_following=False, data={'id': 'mira'})
        context.mill_quest = SimpleNamespace(mira=mira)
        context.world.npcs.append(mira)
        travel = PartyTravel(context, actor_factory=actor)
        travel.update(1/60)
        walk(travel, (100, 70))
        self.assertEqual([value.identifier for value in travel.actors()], ['mira'])
        self.assertTrue(mira.party_travelling)
        self.assertEqual(mira.position, (160, 40))
        mira.quest_mode = True
        context.social.active = True
        travel.update(1/60)
        self.assertFalse(mira.party_travelling)
        self.assertEqual(travel.actors(), ())
        mira.quest_mode = False
        context.social.active = False
        travel.update(1/60)
        self.assertTrue(mira.party_travelling)
        context.party.active_ids = ('caelan',)
        travel.update(1/60)
        self.assertFalse(mira.party_travelling)
        self.assertEqual(mira.position, (160, 40))
        context.party.active_ids = ('caelan', 'mira')
        travel.update(1/60)
        travel.reset()
        self.assertFalse(mira.party_travelling)
        self.assertEqual(travel.actors(), ())

    def test_pause_dialogue_and_journal_freeze_positions_direction_and_walk_clock(self):
        context = game()
        travel = PartyTravel(context, actor_factory=actor)
        travel.update(1/60)
        walk(travel, (100, 70))
        snapshot = [(tuple(value.position), value.facing, value.walk_ms) for value in travel.actors()]
        for namespace, field in ((context.pause, 'is_open'), (context.social, 'active'),
                                 (context.social, 'locked'), (context, 'map_open')):
            setattr(namespace, field, True)
            travel.update(10)
            self.assertEqual([(tuple(value.position), value.facing, value.walk_ms) for value in travel.actors()], snapshot)
            setattr(namespace, field, False)
        context.quest_ui = SimpleNamespace(journal_open=True)
        travel.update(10)
        self.assertEqual([(tuple(value.position), value.facing, value.walk_ms) for value in travel.actors()], snapshot)

    def test_story_mira_keeps_her_formation_slot_for_the_other_follower(self):
        context = game(('caelan', 'mira', 'lucan'))
        mira = SimpleNamespace(quest_mode=True, story_following=True)
        context.mill_quest = SimpleNamespace(mira=mira)
        travel = PartyTravel(context, actor_factory=actor)
        travel.update(1/60)
        walk(travel, (100, 70))
        self.assertEqual([value.identifier for value in travel.actors()], ['lucan'])
        self.assertAlmostEqual(travel.actors()[0].position.x, 100-2*SPACING)
        self.assertFalse(mira.party_travelling)

    def test_npc_obstruction_stops_follower_on_route_until_it_clears(self):
        context = game(('caelan', 'lucan'))
        travel = PartyTravel(context, actor_factory=actor)
        travel.update(1/60)
        walk(travel, (60, 70))
        follower = travel.actors()[0]
        # Place an NPC-sized obstruction in the recorded trail after the leader
        # has already crossed it, as a routine NPC can do between updates.
        context.player.position.update(100, 70)
        travel.update(1/600)
        context.world.obstacles.append(pygame.Rect(48, 65, 6, 10))
        for _ in range(60):travel.update(1/60)
        self.assertLess(follower.position.x, 46)
        self.assertTrue(context.world.can_stand(follower.position))
        context.world.obstacles.clear()
        for _ in range(60):travel.update(1/60)
        self.assertAlmostEqual(follower.position.x, 100-SPACING)

    def test_teleport_and_miniature_overworld_hide_followers_but_reserve_is_supported(self):
        context = game(('caelan', 'lucan'))
        travel = PartyTravel(context, actor_factory=actor)
        travel.update(1/60)
        walk(travel, (100, 70))
        context.player.position.update(200, 140)
        travel.update(1/60)
        self.assertEqual(travel.actors(), ())
        context.world = World(is_overworld=True)
        travel.update(1/60)
        walk(travel, (160, 140))
        self.assertEqual(travel.actors(), ())
        context.world = World()
        context.world.data['id'] = 'elden_vale_sanctuary'
        context.overworld_travel = SimpleNamespace(remote=True, in_reserve=True)
        travel.update(1/60)
        walk(travel, (120, 140))
        self.assertEqual(len(travel.actors()), 1)

    def test_approved_directional_art_uses_native_canvas_and_character_foot_anchor(self):
        pygame.display.init()
        pygame.display.set_mode((1, 1))
        for identifier, anchor in (('mira', (16, 34)), ('lucan', (12, 34)),
                                   ('rhea', (10, 34)), ('edran', (12, 34))):
            value = _TravelActor(identifier)
            self.assertEqual(value.draw_anchor, anchor)
            for facing in ('front', 'back', 'left', 'right'):
                value.facing = facing
                self.assertEqual(value.sprite(0).get_size(), (32 if identifier=='mira' else 24, 36))
                value.moving = True
                value.walk_ms = 160
                self.assertEqual(value.sprite(0).get_size(), (32 if identifier=='mira' else 24, 36))
                value.moving = False

    def test_hidden_routine_cannot_start_an_invisible_conversation(self):
        social = SocialSystem.__new__(SocialSystem)
        social.actor = None
        social._scripted = False
        hidden = SimpleNamespace(party_travelling=True)
        self.assertFalse(social.start(hidden))


if __name__ == '__main__':unittest.main()
