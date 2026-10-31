"""Direction, grounded holds and registered prop ownership for regional work."""
import os
from pathlib import Path
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from grain_farm import FarmWorker, DIRECTIONS


class GrainWorkerAnimationTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode((480, 320))
        self.actor = FarmWorker('loader', 'male_02', (0, 0))

    def tearDown(self):pygame.quit()

    def test_carry_and_hold_use_the_actual_four_directions(self):
        images = []
        for direction in DIRECTIONS:
            self.actor.pose = 'carry';self.actor.facing = direction
            self.actor.moving = True;self.actor.advance(.1)
            self.assertEqual(self.actor.animation_key, 'carry_'+direction)
            images.append(pygame.image.tobytes(self.actor.sprite(0), 'RGBA'))
            self.actor.moving = False;self.actor.advance(.1)
            self.assertEqual(self.actor.animation_key, 'hold_'+direction)
            self.assertEqual(self.actor.clock, 0)
            self.assertIsNotNone(self.actor.attachment.get('sack_offset'))
        self.assertEqual(len(set(images)), 4)

    def test_back_carry_keeps_the_load_away_from_the_camera(self):
        self.actor.pose = 'carry';self.actor.facing = 'back';self.actor.moving = True
        self.actor.advance(0)
        self.assertEqual(self.actor.attachment.get('sack_layer'), 'back')
        self.actor.moving = False;self.actor.advance(0)
        self.assertEqual(self.actor.attachment.get('sack_layer'), 'back')

    def test_walking_does_not_restart_on_intermediate_controller_writes(self):
        self.actor.pose = 'carry';self.actor.facing = 'front'
        self.actor.moving = True;self.actor.advance(0)
        for _ in range(12):
            self.actor.moving = False
            self.actor.moving = True
            self.actor.advance(1/30)
        self.assertGreater(self.actor.clock, .35)
        self.assertNotEqual(self.actor.frame_index, 0)

    def test_blocked_carry_settles_into_a_still_grounded_hold(self):
        self.actor.pose = 'carry';self.actor.moving = True
        self.actor.advance(0);self.actor.advance(.35)
        self.actor.moving = False;self.actor.advance(.1)
        image = pygame.image.tobytes(self.actor.sprite(0), 'RGBA')
        attachment = self.actor.attachment
        for _ in range(60):self.actor.advance(1/30)
        self.assertEqual(image, pygame.image.tobytes(self.actor.sprite(0), 'RGBA'))
        self.assertEqual(attachment, self.actor.attachment)
        self.assertEqual(self.actor.clock, 0)

    def test_new_action_and_turn_start_the_authored_first_pose(self):
        self.actor.pose = 'carry';self.actor.moving = True
        self.actor.advance(0);self.actor.advance(.35)
        self.actor.moving = False;self.actor.pose = 'place';self.actor.facing = 'right'
        self.actor.action_duration = 1.2;self.actor.advance(.1)
        self.assertEqual(self.actor.frame_index, 0)
        self.actor.advance(.7)
        self.assertGreater(self.actor.frame_index, 0)
        self.actor.pose = 'push';self.actor.action_duration = .6
        self.actor.advance(.1)
        self.assertEqual(self.actor.frame_index, 0)

    def test_one_shot_lift_clamps_instead_of_repeating_a_reach(self):
        self.actor.pose = 'lift';self.actor.action_duration = 1.2
        self.actor.advance(0);self.actor.advance(3)
        self.assertEqual(self.actor.frame_index,
                         len(self.actor.clips['lift_front']['frames'])-1)
        last = self.actor.attachment
        self.actor.advance(5)
        self.assertEqual(self.actor.attachment, last)

    def test_dialogue_glance_settles_while_the_load_stays_in_its_grip(self):
        self.actor.pose = 'carry';self.actor.advance(0)
        held_offset = self.actor.attachment['sack_offset']
        self.actor.pose = 'look';self.actor.advance(0);self.actor.advance(.8)
        self.assertEqual(self.actor.frame_index,
                         len(self.actor.clips['look_left']['frames'])-1)
        image = pygame.image.tobytes(self.actor.sprite(0), 'RGBA')
        self.actor.advance(3.5)
        self.assertEqual(image, pygame.image.tobytes(self.actor.sprite(0), 'RGBA'))
        self.assertEqual(self.actor.attachment['sack_offset'], held_offset)

    def test_reverse_lift_returns_to_the_registered_lower_pose(self):
        self.actor.pose = 'lower';self.actor.reverse = True;self.actor.action_duration = .8
        self.actor.advance(0)
        self.assertEqual(self.actor.frame_index,
                         len(self.actor.clips['lift_front']['frames'])-1)
        self.actor.advance(.8)
        self.assertEqual(self.actor.frame_index, 0)

    def test_coworker_uses_authored_side_actions_without_mirroring_a_front_body(self):
        actor = FarmWorker('coworker', 'male_03', (0, 0))
        actor.pose = 'work';actor.facing = 'left';actor.advance(0)
        self.assertEqual(actor.animation_key, 'work_left')
        actor.pose = 'assist';actor.facing = 'right';actor.advance(0)
        self.assertEqual(actor.animation_key, 'assist_right')
        self.assertTrue(actor.hand_positions)
        self.assertTrue(any(point.x > 0 for point in actor.hand_positions))
        actor.pose = 'assist_low';actor.action_duration = .8;actor.advance(0)
        actor.advance(.8)
        self.assertEqual(actor.frame_index,
                         len(actor.clips['assist_low_right']['frames'])-1)
