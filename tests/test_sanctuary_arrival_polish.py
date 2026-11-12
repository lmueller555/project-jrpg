"""Presentation regressions exercised through the real Gallery scene.

The checks observe rendered assets, occupied ground and visible state rather
than depending on the director's particular routes or frame numbering.
"""
from itertools import combinations
import gc
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from main import Game


def pixels(surface):
    return pygame.image.tobytes(surface, 'RGBA')


class SanctuaryArrivalPolishTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.games = []

    def tearDown(self):
        for game in self.games:
            if game.gallery_session is not None:game.gallery_session.close()
            game.regional_audio.reset()
            game.music.stop()
        self.games.clear()
        pygame.quit()
        gc.collect()
        self.folder.cleanup()

    def scene(self):
        directory = Path(self.folder.name)
        parent = Game(fullscreen=False, start_on_title=True,
                      save_path=directory/'journey.json',
                      settings_path=directory/'settings.json')
        parent.audio.effects_volume = 0
        self.games.append(parent)
        self.assertTrue(parent.open_gallery())
        self.assertTrue(parent.launch_gallery_scene('sanctuary_arrival'), parent.gallery.error)
        session = parent.gallery_session
        return parent, session, session.game, session.game.sanctuary_arrival

    def key(self, parent, key=pygame.K_SPACE):
        return parent.handle_events([
            pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False),
            pygame.event.Event(pygame.KEYUP, key=key)])

    def until(self, parent, predicate, *, advance=True, limit=5000, seconds=.1):
        for _ in range(limit):
            if predicate():return
            if parent.gallery_session is None:self.fail('Gallery ended before the requested state')
            owner = parent.gallery_session.game.sanctuary_arrival
            if advance and owner.dialogue is not None:self.key(parent)
            parent.update(seconds)
        self.fail('The scene did not reach the requested state')

    def test_speakers_and_native_art_keep_page_and_workers_distinct(self):
        _, _, game, owner = self.scene()
        speakers = game.social.data['speakers']
        self.assertEqual(speakers['regent_clerk']['portrait'], 'regent_page')
        canonical = game.world.image('assets/story/regent_arrival/actors/portraits/clerk.png')
        self.assertEqual(pixels(game.social.portraits['regent_page']), pixels(canonical))
        self.assertNotEqual(speakers['arrival_caretaker']['portrait'],
                            speakers['arrival_worker']['portrait'])
        self.assertNotIn(speakers['arrival_worker']['portrait'], ('male_03', 'regent_survivor'))
        for role in ('arrival_caretaker', 'arrival_worker'):
            self.assertIn(speakers[role]['portrait'], game.social.portraits)

        page = owner.actors['page']
        self.assertEqual(set(page.idles), {'front', 'back', 'left', 'right'})
        for direction in page.idles:
            self.assertEqual(page.idles[direction].get_size(), (24, 36))
            self.assertGreaterEqual(len(page.walks[direction]), 8)
            self.assertGreaterEqual(len({pixels(frame) for frame in page.walks[direction]}), 6)
            for frame in (page.idles[direction], *page.walks[direction]):
                self.assertEqual(frame.get_size(), (24, 36))
                self.assertLessEqual(set(pixels(frame)[3::4]), {0, 255})
        reading = page.pose_animations['read']
        self.assertGreaterEqual(len(reading['frames']), 6)
        self.assertFalse(reading['loop'])
        for frame in reading['frames']:self.assertEqual(frame.get_size(), (24, 36))

        workers = []
        for key in ('worker_a', 'worker_b'):
            actor = owner.actors[key]
            actor.pose = 'injured'
            workers.append(pixels(actor.sprite(0)))
        survivor = game.world.image('assets/story/regent_emergency/poses/rest_front.png')
        self.assertNotEqual(workers[0], workers[1])
        self.assertTrue(all(body != pixels(survivor) for body in workers))

    def test_live_gallery_movement_keeps_every_cast_members_feet_separate(self):
        parent, session, game, owner = self.scene()
        observed_movement = False
        observed_departure = False
        for _ in range(5000):
            if owner.completed:break
            for first, second in combinations(owner.actors.values(), 2):
                self.assertFalse(
                    game.world.probe_rect(first.position, first.probe_size).colliderect(
                        game.world.probe_rect(second.position, second.probe_size)),
                    (owner.shot, first.key, tuple(first.position), second.key, tuple(second.position)))
            for actor in owner.actors.values():
                self.assertTrue(game.world.can_stand(actor.position, actor.probe_size, actor),
                                (owner.shot, actor.key, tuple(actor.position)))
            if owner.beat == 0 and owner.actors['caelan'].moving:
                observed_movement = True
                viewport = pygame.Rect(game.camera.position(), (480, 320))
                self.assertTrue(viewport.collidepoint(owner.actors['caelan'].position))
            observed_departure |= owner.beat == 7 and owner.actors['caelan'].moving
            if owner.dialogue is not None:self.key(parent)
            parent.update(.1)
        else:self.fail('The coordinated scene stalled')
        self.assertTrue(owner.completed)
        self.assertTrue(observed_movement)
        self.assertTrue(observed_departure)
        self.until(parent, lambda: session.playback.finished, advance=False)
        self.assertTrue(session.playback.finished)

    def test_leaving_a_dialogue_page_open_does_not_restart_the_supply_run(self):
        parent, _, _, owner = self.scene()
        self.until(parent, lambda: owner.dialogue is not None, advance=False)
        line = (owner.beat, owner.dialogue_index)
        for _ in range(150):parent.update(.1)
        runner = owner.actors['runner']
        delivered = tuple(runner.position)
        self.assertFalse(runner.moving)
        for _ in range(300):
            parent.update(.1)
            self.assertEqual(tuple(runner.position), delivered)
            self.assertFalse(runner.moving)
        self.assertEqual((owner.beat, owner.dialogue_index), line)

    def test_rope_frames_keep_all_post_pixels_at_the_same_world_position(self):
        _, _, game, owner = self.scene()
        rope = owner.rail
        posts = game.world.image(rope.art['posts'])
        locations = [(x, y, posts.get_at((x, y)))
                     for y in range(posts.get_height()) for x in range(posts.get_width())
                     if posts.get_at((x, y)).a]
        self.assertTrue(locations)
        rope.set_progress(0, game.world)
        self.assertFalse(game.world.can_stand((1008, 396)))
        self.assertFalse(game.world.can_stand((979, 394)))
        self.assertTrue(game.world.can_stand(game.world.data['public_approaches']['cave']))
        opening = []
        elapsed = 0
        progress = [0.]
        for frame in rope.art['rope_frames']:
            progress.append((elapsed+frame['duration_ms']/2)/rope.duration_ms)
            elapsed += frame['duration_ms']
        progress.append(1.)
        for index, portion in enumerate(progress):
            rope.set_progress(portion, game.world)
            image = rope.record['surfaces'][0]
            self.assertEqual(image.get_size(), posts.get_size())
            self.assertEqual(rope.record['position'], rope.art['position'])
            self.assertEqual(tuple(rope.record['rect'].topleft), tuple(rope.art['position']))
            for x, y, expected in locations:
                self.assertEqual(image.get_at((x, y)), expected, (index, x, y))
            opening.append(pixels(image))
        self.assertTrue(rope.opened)
        self.assertNotEqual(opening[0], opening[-1])
        self.assertGreaterEqual(len(set(opening)), 8)
        self.assertTrue(game.world.can_stand((1008, 396)))
        self.assertFalse(game.world.can_stand((979, 394)))
        self.assertTrue(game.world.can_stand(game.world.data['public_approaches']['cave']))

    def test_pause_and_focus_freeze_the_caretaker_and_rope_during_release(self):
        parent, _, _, owner = self.scene()
        self.until(parent, lambda: owner._rail_pending and .1 < owner.rail.progress < .8)
        voice = Mock()
        owner.rail._sound = object()
        voice.get_sound.return_value = owner.rail._sound
        owner.rail._voice = voice
        before = (owner.rail.progress, pixels(owner.rail.record['surfaces'][0]),
                  tuple(owner.actors['caretaker'].position))
        self.key(parent, pygame.K_p)
        voice.pause.assert_called()
        parent.update(2)
        self.assertEqual((owner.rail.progress, pixels(owner.rail.record['surfaces'][0]),
                          tuple(owner.actors['caretaker'].position)), before)
        self.key(parent, pygame.K_p)
        voice.pause.reset_mock()
        parent.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        voice.pause.assert_called()
        parent.update(2)
        self.assertEqual((owner.rail.progress, pixels(owner.rail.record['surfaces'][0]),
                          tuple(owner.actors['caretaker'].position)), before)
        voice.unpause.reset_mock()
        parent.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        voice.unpause.assert_called()
        self.until(parent, lambda: owner.completed)
        self.assertTrue(owner.rail.opened)
        self.key(parent, pygame.K_ESCAPE)
        voice.stop.assert_called()

    def test_rope_contact_stays_within_natural_reach_until_the_free_end_is_released(self):
        parent, _, game, owner = self.scene()
        keeper = owner.actors['caretaker']
        rope = owner.rail
        action = owner.art['actors']['caretaker']['poses']['unhook']
        keeper.position.update(rope.art['caretaker_position'])
        keeper.moving = False
        keeper.pose = 'unhook'
        game.camera.focus((1008, 406), 0)

        def frame_at(frames, elapsed):
            for frame in frames:
                if elapsed < frame['duration_ms']:return frame
                elapsed -= frame['duration_ms']
            return frames[-1]

        for elapsed in range(rope.art['contact_ms']+50, rope.art['guided_until_ms'], 100):
            keeper.pose_ms = elapsed
            rope.set_progress(elapsed/rope.duration_ms, game.world)
            hand_frame = frame_at(action['frames'], elapsed)
            rope_frame = frame_at(rope.art['rope_frames'], elapsed)
            grip = pygame.Vector2(hand_frame['grip'])
            hand_world = keeper.position-pygame.Vector2(keeper.draw_anchor)+grip
            rope_world = pygame.Vector2(rope.art['position'])+rope_frame['free_end']
            # The global standard permits a small deliberate contact gap.
            # Exact coincidence previously forced an oversized reaching arm.
            self.assertLessEqual(hand_world.distance_to(rope_world),4,elapsed)
            hand = keeper.sprite(0).get_at(tuple(map(int, grip)))
            endpoint = game.world.image(rope_frame['file']).get_at(tuple(rope_frame['free_end']))
            self.assertEqual(hand.a, 255)
            self.assertEqual(endpoint.a, 255)
            parent.draw()
            self.assertEqual(tuple(keeper.position),tuple(rope.art['caretaker_position']))

        # Unhooking opens the passage at the visual cue, rather than waiting
        # until the rope has settled or allowing passage through a taut rope.
        rope.set_progress((rope.art['release_ms']-1)/rope.duration_ms,game.world)
        self.assertFalse(game.world.can_stand((1008,396)))
        rope.set_progress(rope.art['release_ms']/rope.duration_ms,game.world)
        self.assertTrue(game.world.can_stand((1008,396)))

    def test_gallery_restart_during_release_restores_the_closed_barrier(self):
        parent, session, _, owner = self.scene()
        before = parent._progress_signature()
        self.until(parent, lambda: owner._rail_pending and .1 < owner.rail.progress < .8)
        self.assertTrue(self.key(parent, pygame.K_r))
        self.assertTrue(session.closed)
        replacement = parent.gallery_session.game.sanctuary_arrival
        self.assertIsNot(replacement, owner)
        self.assertFalse(replacement.completed)
        self.assertEqual(replacement.beat, 0)
        self.assertFalse(replacement.rail.opened)
        self.assertEqual(replacement.rail.progress, 0)
        self.assertEqual(parent._progress_signature(), before)

    def test_gallery_restart_during_kit_retrieval_discards_partial_prop_ownership(self):
        parent, session, game, owner = self.scene()
        before = parent._progress_signature()
        self.until(parent, lambda: owner.care.action == 'retrieve'
                   and owner.care.kit_owner == 'mira')
        props = [record for _, record in owner._care_props]
        self.assertTrue(props)
        self.assertTrue(self.key(parent, pygame.K_r))
        self.assertTrue(session.closed)
        replacement = parent.gallery_session.game.sanctuary_arrival
        self.assertIsNot(replacement, owner)
        self.assertEqual(replacement.beat, 0)
        self.assertEqual(replacement.care.kit_owner, 'stowed')
        self.assertEqual(replacement.care.cloth_owner, 'linen')
        self.assertFalse(replacement.care.runner_linen_placed)
        self.assertTrue(all(record not in game.world.entities for record in props))
        self.assertEqual(parent._progress_signature(), before)


if __name__ == '__main__':unittest.main()
