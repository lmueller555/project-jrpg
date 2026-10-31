"""Physical animation regressions for the bridge crew's authored bodies."""
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from main import Game
from bridge_crew import BridgeWorker, SOURCE, STACK, REJECT, KETTLE, HELP, SEAT, SAFE, SCENE_ID
from grain_farm import DIRECTIONS


class BridgeWorkerDirectionTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode((480, 320))

    def tearDown(self):pygame.quit()

    def test_both_cup_carriers_use_four_authored_directions_and_still_holds(self):
        for role, variant in (('mason', 'male_01'), ('tender', 'male_03')):
            with self.subTest(role=role):
                actor = BridgeWorker(role, variant, (0, 0))
                images = []
                for direction in DIRECTIONS:
                    actor.pose = 'cup';actor.facing = direction;actor.moving = True
                    actor.advance(0)
                    images.append(pygame.image.tobytes(actor.sprite(0), 'RGBA'))
                    self.assertIsNotNone(actor.attachment.get('cup_offset'))
                    actor.advance(.35)
                    actor.moving = False;actor.advance(0)
                    held = (pygame.image.tobytes(actor.sprite(0), 'RGBA'), actor.attachment)
                    for _ in range(60):actor.advance(1/30)
                    self.assertEqual(held, (pygame.image.tobytes(actor.sprite(0), 'RGBA'), actor.attachment))
                self.assertEqual(len(set(images)), 4)

    def test_stone_carrier_turns_and_keeps_rear_load_behind_his_body(self):
        actor = BridgeWorker('mason', 'male_01', (0, 0))
        images = []
        for direction in DIRECTIONS:
            actor.pose = 'carry';actor.facing = direction;actor.moving = True
            actor.advance(0)
            images.append(pygame.image.tobytes(actor.sprite(0), 'RGBA'))
            self.assertIsNotNone(actor.attachment.get('stone_offset'))
            if direction == 'back':self.assertEqual(actor.attachment.get('stone_layer'), 'back')
            actor.moving = False;actor.advance(0)
            held = (pygame.image.tobytes(actor.sprite(0), 'RGBA'), actor.attachment)
            actor.advance(2)
            self.assertEqual(held, (pygame.image.tobytes(actor.sprite(0), 'RGBA'), actor.attachment))
        self.assertEqual(len(set(images)), 4)

    def test_loaded_gait_survives_controller_writes_and_a_turn_restarts_it(self):
        actor = BridgeWorker('tender', 'male_03', (0, 0))
        actor.pose = 'cup';actor.facing = 'left';actor.moving = True;actor.advance(0)
        for _ in range(12):
            actor.moving = False
            actor.moving = True
            actor.advance(1/30)
        self.assertGreater(actor.clock, .35)
        self.assertGreater(actor.frame_index, 0)
        actor.facing = 'back';actor.advance(0)
        self.assertEqual(actor.frame_index, 0)

    def test_seated_sip_reaches_the_painted_mouth_and_returns_to_a_hold(self):
        actor = BridgeWorker('mason', 'male_01', (0, 0))
        frames = actor.clips['drink_front']['frames']
        mouth_frames = [frame for frame in frames if frame.get('mouth_offset') is not None]
        self.assertTrue(mouth_frames, 'The drink source must register its painted mouth.')
        for frame in mouth_frames:
            point = tuple(round(actor.draw_anchor[i]+frame['mouth_offset'][i]) for i in (0, 1))
            self.assertTrue(frame['image'].get_rect().collidepoint(point))
            self.assertGreaterEqual(frame['image'].get_at(point).a, 128,
                                    'The mouth landmark must lie on painted body pixels.')
        for key in ('sit_front', 'drink_front'):
            for frame in actor.clips[key]['frames']:
                self.assertIn('seat_contact', frame)
                point = tuple(round(actor.draw_anchor[i]+frame['seat_contact'][i]) for i in (0, 1))
                self.assertTrue(frame['image'].get_rect().collidepoint(point))
                self.assertGreaterEqual(frame['image'].get_at(point).a, 128,
                                        'The seated contact must lie on the painted hip.')
        offsets = [frame['cup_offset'] for frame in frames if frame.get('cup_offset') is not None]
        self.assertGreaterEqual(max(p[1] for p in offsets)-min(p[1] for p in offsets), 3)
        # Cup source is 6x6: its visible upper rim lies five pixels above its
        # lower-center anchor. At least one authored raised frame must meet
        # the painted mouth, rather than stopping at the old chest offset.
        touching = [frame for frame in mouth_frames
                    if abs(frame['cup_offset'][0]-frame['mouth_offset'][0]) <= 2
                    and abs(frame['cup_offset'][1]-5-frame['mouth_offset'][1]) <= 2]
        self.assertTrue(touching, 'The cup rim never reaches the mouth.')
        mouths = [frame['mouth_offset'] for frame in mouth_frames]
        self.assertLessEqual(max(p[0] for p in mouths)-min(p[0] for p in mouths), 2)


class BridgeWorkerPhysicalFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.g = Game(fullscreen=False, start_on_title=False,
                      save_path=root/'journey.json', settings_path=root/'settings.json')
        self.g.audio.set_music(0);self.g.audio.set_effects(0)
        self.g.opening_fade = self.g.transfer_cooldown = 0
        self.g.world = self.g.overworld_world
        self.g.player.position.update(-2340, 644)
        self.c = self.g.world.bridge_crew
        pygame.event.clear()

    def tearDown(self):pygame.quit()

    def tick(self):self.g.update(1/30, (0, 0), False)

    def until(self, predicate, limit=3000):
        for _ in range(limit):
            if predicate():return
            self.tick()
        self.fail((self.c.stage, self.c.state, [tuple(a.position) for a in self.c.actors]))

    def anchors(self, key):
        image = self.c.art[key]
        return [pygame.Vector2(position)+(image.get_width()//2, image.get_height())
                for _, _, surface, position in self.c.props() if surface is image]

    def read(self):
        self.assertTrue(self.g.overworld_travel.interact())
        self.assertEqual(self.g.social.script_identifier, SCENE_ID)
        while self.g.social.active:self.g.social.advance()

    def begin_tea(self):
        self.until(lambda:self.c.stage == 'ready')
        self.g.player.position.update(-2376, 642)
        self.assertTrue(self.g.overworld_travel.interact())
        self.until(lambda:self.c.stage == 'request');self.read()
        self.until(lambda:self.c.stage == 'exchange');self.read()

    def test_every_stone_remains_at_its_released_slot_when_the_count_commits(self):
        committed = []
        for _ in range(3000):
            before = self.c.state['sorted']
            previous = self.anchors('stone')
            self.assertEqual(len(previous), 4)  # three batch pieces + shaky support
            self.tick()
            after = self.c.state['sorted']
            if after != before:
                self.assertEqual(after, before+1)
                current = self.anchors('stone')
                self.assertLessEqual(previous[before].distance_to(current[before]), 1,
                                     ('Released stone jumped on commit', before, previous, current))
                expected = ((STACK[0]-7, STACK[1]-2),
                            (STACK[0], STACK[1]-2), (REJECT[0], REJECT[1]-2))[before]
                self.assertLessEqual(current[before].distance_to(expected), .01)
                committed.append(after)
            if after == 3:break
        self.assertEqual(committed, [1, 2, 3])

    def test_ordinary_mid_lift_greeting_freezes_body_and_held_stone_until_closed(self):
        self.g.player.position.update(-2376, 642)
        self.until(lambda:self.c.stage == 'lift' and self.c.timer > .35)
        self.assertTrue(self.g.overworld_travel.interact())
        self.assertEqual(self.g.social.script_identifier, 'bridge_crew_greeting')
        frozen = (self.c.timer, tuple(a.clock for a in self.c.actors),
                  tuple(tuple(p) for p in self.anchors('stone')))
        for _ in range(90):self.tick()
        self.assertEqual(frozen, (self.c.timer, tuple(a.clock for a in self.c.actors),
                                 tuple(tuple(p) for p in self.anchors('stone'))))
        while self.g.social.active:self.g.social.advance()
        self.until(lambda:self.c.state['sorted'] == 1)

    def test_seated_recovery_stays_on_the_bench_before_the_mason_walks_away(self):
        self.begin_tea()
        self.until(lambda:self.c.stage == 'sit_down')
        planted = self.c.mason.position.copy()
        self.assertLessEqual(planted.distance_to(SEAT), .15)
        down_frames = set()
        while self.c.stage == 'sit_down':
            self.assertEqual(self.c.mason.position, planted)
            down_frames.add(self.c.mason.frame_index);self.tick()
        self.assertGreater(len(down_frames), 1)
        # The resting hip must meet an actual bench plank pixel, rather than
        # a declared contact point floating above or beyond the furniture.
        contact = self.c.mason.position+self.c.mason.attachment['seat_contact']
        bench = self.c.art['bench']
        origin = next(position for _, _, surface, position in self.c.props() if surface is bench)
        local = (round(contact.x)-origin[0], round(contact.y)-origin[1])
        self.assertTrue(bench.get_rect().collidepoint(local))
        self.assertGreaterEqual(bench.get_at(local).a, 128)
        self.until(lambda:self.c.stage == 'stand_up')
        up_frames = set()
        while self.c.stage == 'stand_up':
            self.assertEqual(self.c.mason.position, planted)
            up_frames.add(self.c.mason.frame_index);self.tick()
        self.assertGreater(len(up_frames), 1)
        self.assertEqual(self.c.state['sorted'], 3)
        self.assertEqual(self.c.state['tea_beat'], 4)

    def test_cup_has_a_hand_or_a_supported_resting_place_through_the_tea_visit(self):
        self.until(lambda:self.c.stage == 'ready')
        self.g.player.position.update(-2376, 642)
        self.assertTrue(self.g.overworld_travel.interact())
        held_checks = 0
        for _ in range(3000):
            cups = self.anchors('cup');self.assertEqual(len(cups), 1)
            cup = cups[0]
            candidates = [pygame.Vector2(KETTLE)+(8,-11),
                          pygame.Vector2(-2368,600), pygame.Vector2(SAFE)+(0,-7)]
            for actor in self.c.actors:
                offset = actor.attachment.get('cup_offset')
                if offset is not None:
                    candidates.append(actor.position+offset)
                    if actor.attachment.get('gripped', True):
                        held_checks += 1
                        # Hands need to meet the cup's actual footprint. One
                        # free hand can stay at the side while the other holds.
                        cup_rect = pygame.Rect(round(cup.x)-3, round(cup.y)-6, 6, 6).inflate(4,4)
                        if (actor.position+offset).distance_to(cup) <= 1:
                            self.assertTrue(any(cup_rect.collidepoint(p) for p in actor.hand_positions),
                                            (self.c.stage, cup, actor.hand_positions))
            self.assertLessEqual(min(cup.distance_to(p) for p in candidates), 1,
                                 ('Cup moved without a hand or support', self.c.stage, cup, candidates))
            if self.c.stage in ('request','exchange'):self.read()
            if self.c.state['tea_beat'] == 5:break
            self.tick()
        self.assertEqual(self.c.state['tea_beat'], 5)
        self.assertGreater(held_checks, 30)
