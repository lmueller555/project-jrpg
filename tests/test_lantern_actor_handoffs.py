"""Quest borrowing preserves real residents, household toys and dog ownership."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
import unittest

import pygame

from main import Game
from lantern_actors import ResidentPose


class LanternActorHandoffTests(unittest.TestCase):
    def setUp(self):
        self.game = Game(fullscreen=False, start_on_title=False, save_path=None)
        self.shared = self.game.play_routines[0]
        self.blocks = self.game.block_routines[0]
        self.bone = self.game.bone_routines[0]
        self.owner = object()
        self.game.player.position.update(430, 600)
        self.shared.cooldown_ms = self.blocks.cooldown_ms = self.bone.cooldown_ms = 999999
        self.shared.daisy.cooldowns = {'food': 999999, 'water': 999999}
        self.shared.daisy.duration_ms = 999999

    def tearDown(self):
        pygame.quit()

    def tick(self):
        before = {actor: (self.shared.worlds[actor], actor.position.copy())
                  for actor in (self.shared.liam, self.shared.daisy)}
        self.game.update(1/30, (0, 0), False)
        self.assertEqual(len(self.blocks.blocks), 5)
        self.assertEqual(len({block['id'] for block in self.blocks.blocks}), 5)
        self.assertLessEqual(sum(block['state'] == 'held' for block in self.blocks.blocks), 1)
        for actor, (world, position) in before.items():
            current = self.shared.worlds[actor]
            self.assertEqual(sum(npc is actor for room in self.game.scenes.values()
                                 for npc in room.npcs), 1)
            if current is world:
                self.assertLessEqual(actor.position.distance_to(position), 64/30+1e-6)

    def until(self, predicate, limit=120):
        for _ in range(limit*30):
            if predicate():return
            self.tick()
        self.fail((self.shared.state, self.blocks.state,
                   tuple(self.shared.liam.position), tuple(self.shared.daisy.position)))

    def claim(self):
        self.until(lambda: self.shared.request_liam(self.owner))
        self.assertIs(self.shared.liam_owner, self.owner)
        self.assertFalse(self.shared.active)
        self.assertFalse(self.blocks.active)
        self.assertTrue(all(block['state'] == 'box' for block in self.blocks.blocks))
        self.assertIsNone(self.blocks.held)

    def test_idle_claim_is_exclusive_and_releases_without_new_cycles(self):
        self.assertTrue(self.shared.request_liam(self.owner))
        self.assertFalse(self.shared.begin())
        self.assertFalse(self.blocks.begin())
        self.assertFalse(self.shared.request_liam(object()))
        self.assertIsNone(self.shared.pending_liam_owner)
        self.assertTrue(self.shared.release_liam(self.owner))
        self.assertIsNone(self.shared.liam_owner)

    def test_chase_returns_both_real_participants_through_door(self):
        self.assertTrue(self.shared.begin(drink=False))
        self.until(lambda: self.shared.state == 'chase')
        self.assertFalse(self.shared.request_liam(self.owner))
        self.claim()
        self.assertIs(self.shared.worlds[self.shared.liam], self.shared.home)
        self.assertIs(self.shared.worlds[self.shared.daisy], self.shared.home)
        self.assertFalse(self.shared.daisy.play_owned)
        transfers = [(event['transfer'], event['scene']) for event in self.shared.events
                     if 'transfer' in event]
        self.assertIn(('liam', 'liam_house'), transfers)
        self.assertIn(('daisy', 'liam_house'), transfers)

    def test_claim_during_one_sided_exit_returns_liam_without_sending_daisy_out(self):
        self.assertTrue(self.shared.begin(drink=False))
        self.until(lambda: self.shared.state == 'exit_daisy')
        self.assertIs(self.shared.worlds[self.shared.daisy], self.shared.home)
        self.claim()
        self.assertFalse(self.shared.daisy.play_owned)
        self.assertIs(self.shared.worlds[self.shared.daisy], self.shared.home)

    def test_nap_wakes_promptly_instead_of_waiting_for_whole_rest(self):
        self.assertTrue(self.shared.begin(drink=False))
        self.until(lambda: self.shared.state == 'nap')
        self.shared.rest_duration = 999999
        self.assertFalse(self.shared.request_liam(self.owner))
        self.until(lambda: self.shared.request_liam(self.owner), limit=3)
        self.assertIsNone(self.shared.liam.action)
        self.assertIsNone(self.shared.liam.sort_y)
        self.assertFalse(self.shared.daisy.play_owned)

    def test_held_block_finishes_contact_and_is_returned_before_claim(self):
        self.assertTrue(self.blocks.begin(accident=False, forget=False))
        self.until(lambda: self.blocks.held is not None)
        held_id = self.blocks.held['id']
        self.assertFalse(self.shared.request_liam(self.owner))
        self.assertIsNotNone(self.blocks.held)
        self.claim()
        self.assertTrue(any(event.get('return') == held_id for event in self.blocks.events))
        self.assertIsNone(self.shared.liam.work_renderer)

    def test_accident_cleanup_returns_all_blocks_and_releases_daisy(self):
        dog = self.shared.daisy
        dog.position.update(126, 180);dog.state = 'pause';dog.activity = None
        self.assertTrue(self.blocks.begin(accident=True, forget=False))
        self.until(lambda: any(block['state'] == 'scattered' for block in self.blocks.blocks))
        self.claim()
        self.assertFalse(dog.play_owned)
        self.assertIsNone(dog.play_pose)
        self.assertIsNone(self.blocks.forgotten_id)

    def test_request_during_cleanup_includes_the_already_forgotten_block(self):
        self.assertTrue(self.blocks.begin(accident=False, forget=True))
        self.until(lambda: self.blocks.mode == 'cleanup' and self.blocks.forgotten_id is not None)
        self.claim()
        self.assertIsNone(self.blocks.forgotten_id)

    def test_forgotten_block_waits_until_active_chase_has_returned(self):
        self.assertTrue(self.blocks.begin(accident=False, forget=True))
        self.until(lambda: self.blocks.completed_cycles == 1)
        self.assertIsNotNone(self.blocks.forgotten_id)
        self.blocks.cooldown_ms = 999999
        self.assertTrue(self.shared.begin(drink=False))
        self.until(lambda: self.shared.state == 'chase')
        self.assertFalse(self.shared.request_liam(self.owner))
        self.assertFalse(self.blocks.active)
        self.claim()
        self.assertIsNone(self.blocks.forgotten_id)

    def test_reset_cancels_a_pending_block_claim_and_restores_five_toys(self):
        self.assertTrue(self.blocks.begin(accident=False, forget=False))
        self.until(lambda: self.blocks.held is not None)
        self.assertFalse(self.shared.request_liam(self.owner))
        self.assertTrue(self.shared.release_liam(self.owner, reset=True))
        self.assertFalse(self.blocks.active)
        self.assertTrue(all(block['state'] == 'box' for block in self.blocks.blocks))
        self.assertIsNone(self.blocks.held)
        self.assertIsNone(self.shared.liam_owner)
        self.assertIsNone(self.shared.pending_liam_owner)
        self.assertIs(self.shared.worlds[self.shared.liam], self.shared.home)
        self.assertEqual(tuple(self.shared.liam.position), self.shared._liam_home_position)

    def test_independent_held_bone_survives_liam_claim_and_reset(self):
        dog = self.shared.daisy
        dog.state = 'pause';dog.activity = 'wander'
        self.assertTrue(self.bone.begin(kind='rug', playful=False))
        self.until(lambda: self.bone.bone['state'] == 'mouth')
        self.assertTrue(self.shared.request_liam(self.owner))
        self.assertTrue(self.bone.active)
        self.assertEqual(self.bone.bone['state'], 'mouth')
        self.shared.liam.story_following = True
        self.assertTrue(self.shared.release_liam(self.owner, reset=True))
        self.assertFalse(self.shared.liam.story_following)
        self.assertTrue(self.bone.active)
        self.assertEqual(self.bone.bone['state'], 'mouth')
        self.assertTrue(dog.play_owned)

    def test_resident_pose_moves_the_existing_teacher_blocker_and_restores_art(self):
        home = self.shared.home
        actor = next(npc for npc in home.npcs if npc.data['id'] == 'liam_mother')
        original = actor.sprite(0)
        pose = ResidentPose(actor, home)
        self.assertIs(next(npc for npc in home.npcs if npc.data['id'] == 'liam_mother'), actor)
        actor.position.update(250, 180);actor.facing = 'left';actor.moving = True;actor.walk_ms = 140
        pose.sync()
        self.assertEqual(actor.blocker.center, (250, 180))
        self.assertIs(actor.story_sprite, pose.walks['left'][1][0])
        actor.request_conversation('right');pose.sync()
        self.assertIs(actor.story_sprite, pose.idles['right'])
        actor.position.update(actor.data['position']);pose.release()
        self.assertIs(actor.sprite(0), original)
        self.assertFalse(hasattr(actor, 'story_sprite'))
        self.assertFalse(hasattr(actor, 'request_conversation'))
        self.assertEqual(actor.blocker.center, tuple(actor.data['position']))


if __name__ == '__main__':
    unittest.main()
