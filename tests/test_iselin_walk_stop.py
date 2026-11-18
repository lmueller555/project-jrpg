"""The authored gate stop owns its deceleration, clip clock and safe handoff."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from cinematic_actor_actions import load_actions
from main import Game
from regent_arrival import RegentArrival
from test_mill_battle_gameplay import click, key
from test_regent_arrival import acknowledge_report, seed_mill_report


class IselinWalkStopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='iselin-walk-stop-')
        cls.folder = Path(cls.directory.name)
        cls.path = cls.folder/'journey.json'
        cls.game = Game(fullscreen=False, start_on_title=False, window_size=(960, 640),
                        save_path=cls.path, settings_path=cls.folder/'settings.json')
        cls.game.audio.set_music(0);cls.game.audio.set_effects(0)
        seed_mill_report(cls.game)
        acknowledge_report(cls.game)
        cls.game.update(.05, (0, 0), False)
        if not cls.game.regent_arrival.active:
            raise AssertionError('The acknowledged arrival did not start')
        cls.game.regent_arrival._load()

    @classmethod
    def tearDownClass(cls):
        if cls.game.gallery_session is not None:cls.game.gallery_session.close()
        cls.game.regent_arrival.reset()
        cls.game.opening_audio.reset();cls.game.regional_audio.reset();cls.game.music.stop()
        pygame.quit();cls.directory.cleanup()

    def setUp(self):
        self.g = self.game
        self.g.on_title = False;self.g.on_gallery = False;self.g._music_focused = True
        self.g.pause.close();self.g.social.cancel_script()
        self.scene = self.g.regent_arrival
        self.start_approach()
        pygame.event.clear()

    def start_approach(self, scene=None):
        scene = self.scene if scene is None else scene
        self.assertTrue(scene.restore({'version': 1, 'state': 'pending'}))
        self.assertTrue(scene.maybe_start())
        # The journey prerequisites were acknowledged above. Only review
        # stationing skips the unrelated aerial shots; updates own the stop.
        scene.phase_index = next(i for i, phase in enumerate(scene.data['phases'])
                                 if phase['id'] == 'gate_approach')
        scene.phase_time = 0.
        scene.dialogue_index = scene.page_index = 0
        scene._load()
        return next(actor for actor in scene.phase['actors'] if actor['id'] == 'iselin')

    def actor(self, scene=None):
        scene = self.scene if scene is None else scene
        return next(actor for actor in scene.phase['actors'] if actor['id'] == 'iselin')

    def update(self, seconds):self.g.update(seconds, (0, 0), False)

    def state(self, scene=None):
        scene = self.scene if scene is None else scene
        return scene.actor_action_state('iselin')

    def test_clip_registration_handoff_and_rest_preserve_approved_surfaces(self):
        art = self.scene.actor_art['iselin'];clip = art['actions']['stop_left']
        self.assertEqual(art['canvas'], [80, 96]);self.assertEqual(art['anchor'], [40, 92])
        total = sum(frame.duration_ms for frame in (*clip.entry, *clip.recovery))
        self.assertEqual(total+clip.hold_duration_ms, 700)
        self.assertEqual(pygame.image.tobytes(clip.entry[0].image, 'RGBA'),
                         pygame.image.tobytes(art['loops']['gate_walk_left'][15][0], 'RGBA'))
        self.assertIs(clip.recovery[-1].image, art['poses']['gate_stand_left'])
        self.assertIs(clip.rest_image, art['poses']['gate_stand_left'])
        for index, image in enumerate([frame.image for frame in clip.entry]+[clip.hold_image]):
            with self.subTest(frame=index):
                self.assertEqual(image.get_size(), (80, 96))
                self.assertTrue(image.get_bounding_rect().width)
                self.assertLessEqual(set(pygame.image.tobytes(image, 'RGBA')[3::4]), {0, 255})

    def test_live_loader_uses_the_exact_approved_detailed_bank(self):
        # This fingerprint was recorded independently from the approved R2
        # review, before promotion. Reading only the production controller here
        # prevents a review-only bank override from satisfying integration.
        art = self.scene.actor_art['iselin'];clip = art['actions']['stop_left']
        surfaces = [image for image, _ in art['loops']['gate_walk_left']]
        surfaces += [frame.image for frame in clip.entry[1:]]
        surfaces.append(art['poses']['gate_stand_left'])
        self.assertEqual(len(surfaces), 25)
        self.assertEqual(sha256(b''.join(pygame.image.tobytes(image, 'RGBA')
                         for image in surfaces)).hexdigest(),
                         'c1a5b77c6724985715912cf76e04879f1fd7cde111e27f7ff512eea2cbb4efe5')
        self.assertEqual(art['gaits']['gate_walk_left']['stride_pixels'], 32)
        self.assertEqual([duration for _, duration in art['loops']['gate_walk_left']], [.035]*16)
        incoming = art['loops']['gate_incoming_left']
        self.assertEqual(len(incoming), 8)
        self.assertEqual(art['gaits']['gate_incoming_left']['stride_pixels'], 16)
        for index, (image, duration) in enumerate(incoming):
            with self.subTest(incoming_frame=index):
                self.assertEqual(duration, .035)
                self.assertEqual(pygame.image.tobytes(image, 'RGBA'),
                                 pygame.image.tobytes(art['loops']['gate_walk_left'][index][0], 'RGBA'))
        self.assertEqual(pygame.image.tobytes(clip.entry[-1].image, 'RGBA'),
                         pygame.image.tobytes(art['poses']['gate_stand_left'], 'RGBA'))

    def test_production_updates_select_the_approved_approach_stop_and_greeting(self):
        art = self.scene.actor_art['iselin'];clip = art['actions']['stop_left']
        samples = [(.84, art['loops']['gate_walk_left'][10][0]),
                   (.92, art['loops']['gate_walk_left'][11][0]),
                   (1.02, art['loops']['gate_walk_left'][12][0]),
                   (1.10, art['loops']['gate_walk_left'][13][0]),
                   (1.18, art['loops']['gate_walk_left'][14][0]),
                   (1.25, clip.entry[0].image)]
        samples += [(1.29 + index*.06, frame.image)
                    for index, frame in enumerate(clip.entry[1:])]
        samples += [(1.83, art['poses']['gate_stand_left']),
                    (1.96, art['poses']['gate_stand_left'])]
        elapsed = 0.
        for seconds, expected in samples:
            self.update(seconds-elapsed);elapsed = seconds
            with self.subTest(seconds=seconds):
                self.assertIs(self.scene._frame(self.actor()), expected)
        self.assertEqual(self.scene.shot, 'gate_greeting')
        self.assertEqual(self.state()['stage'], 'idle')

    def test_stop_anticipation_is_scoped_away_from_looping_travel(self):
        art = self.scene.actor_art['iselin']
        # The approved anticipation tail is not a generic repeating gait.
        # Preserve the complete original travel loop and check actual selectors
        # in shots that run long enough to wrap it more than once.
        self.assertEqual(sha256(b''.join(pygame.image.tobytes(image, 'RGBA')
                         for image, _ in art['loops']['walk_left'])).hexdigest(),
                         '209079655210d62d21b91a3ba05cb2716674e7c171497ab6f3365fd2494f9c6f')
        for index, phase in enumerate(self.scene.data['phases']):
            for actor in phase['actors']:
                if actor['id'] != 'iselin':continue
                with self.subTest(shot=phase['id']):
                    if actor['pose'] == 'gate_walk_left':
                        self.assertEqual(phase['id'], 'gate_approach')
                        self.assertEqual(actor['reference_pose'], 'gate_incoming_left')
                    if phase['id'] not in ('town_approach', 'town_parking'):continue
                    self.scene.clear_actor_actions()
                    self.scene.phase_index = index
                    for seconds in (.2, 1.4, 2.8):
                        self.scene.phase_time = seconds
                        self.assertEqual(self.scene.actor_pose(actor), 'walk_left')
                        self.assertTrue(any(self.scene._frame(actor) is image
                                            for image, _ in art['loops']['walk_left']))
                        self.assertFalse(any(self.scene._frame(actor) is image
                                             for image, _ in art['loops']['gate_walk_left']))

    def test_invalid_stop_annotations_cannot_create_impossible_motion(self):
        original = self.scene.data
        mutations = [
            lambda phase, actor: actor.update(stop=None),
            lambda phase, actor: actor['stop'].update(deceleration_seconds=0),
            lambda phase, actor: actor['stop'].update(deceleration_seconds=-.1),
            lambda phase, actor: actor['stop'].update(deceleration_seconds=float('nan')),
            lambda phase, actor: actor['stop'].update(deceleration_seconds=float('inf')),
            lambda phase, actor: actor['stop'].update(start_seconds=True),
            lambda phase, actor: actor['stop'].update(settle_seconds=-.1),
            lambda phase, actor: actor['stop'].update(action=''),
            lambda phase, actor: actor['stop'].update(unrecognized=1),
            lambda phase, actor: actor.update(move_seconds=1.5),
            lambda phase, actor: phase.update(min_seconds=1.5),
            lambda phase, actor: actor.update(path=[actor['position'], actor['to']]),
            lambda phase, actor: actor.update(route='gate_road'),
            lambda phase, actor: actor.update(to=list(actor['position'])),
            lambda phase, actor: actor.update(position=[float('nan'), 375]),
            lambda phase, actor: phase['actors'].append(deepcopy(actor)),
        ]
        try:
            for index, mutate in enumerate(mutations):
                data = deepcopy(original)
                phase = next(p for p in data['phases'] if p['id'] == 'gate_approach')
                actor = next(a for a in phase['actors'] if a['id'] == 'iselin')
                mutate(phase, actor);self.scene.data = data
                with self.subTest(case=index):
                    with self.assertRaises(ValueError):self.scene._validate()
        finally:self.scene.data = original

    def test_stop_loader_requires_a_known_finite_clip_matching_the_motion_duration(self):
        original = (self.scene.data, self.scene.scenery, self.scene.actor_art)
        try:
            for change in ({'action': 'not_authored'}, {'settle_seconds': .1}):
                self.scene.data = deepcopy(original[0]);self.scene.scenery = None
                phase = next(p for p in self.scene.data['phases'] if p['id'] == 'gate_approach')
                actor = next(a for a in phase['actors'] if a['id'] == 'iselin')
                actor['stop'].update(change)
                self.scene._validate()
                with self.subTest(change=change):
                    with self.assertRaises(ValueError):self.scene._load()
        finally:self.scene.data, self.scene.scenery, self.scene.actor_art = original

    def test_route_decelerates_without_a_position_or_velocity_jump(self):
        actor = self.actor()
        def point(seconds):
            self.scene.phase_time = seconds
            return self.scene.actor_position(actor)
        for seconds in (0., .1, .5, 1., 1.25):
            with self.subTest(unchanged_approach=seconds):
                self.assertAlmostEqual(point(seconds).x, 611-24*seconds)
                self.assertEqual(point(seconds).y, 375)
        self.assertEqual(point(1.25), pygame.Vector2(581, 375))
        self.assertAlmostEqual(point(1.5).x, 576.5)
        self.assertEqual(point(1.75), pygame.Vector2(575, 375))
        self.assertEqual(point(1.95), pygame.Vector2(575, 375))
        times = [1.25+index*.025 for index in range(21)]
        xs = [point(seconds).x for seconds in times]
        speeds = [(a-b)/.025 for a, b in zip(xs, xs[1:])]
        self.assertTrue(all(b <= a for a, b in zip(xs, xs[1:])))
        self.assertTrue(all(b < a for a, b in zip(speeds, speeds[1:])))
        epsilon = 1e-5
        before = (point(1.25-epsilon).x-point(1.25).x)/epsilon
        after = (point(1.25).x-point(1.25+epsilon).x)/epsilon
        final = (point(1.75-epsilon).x-point(1.75).x)/epsilon
        self.assertAlmostEqual(before, 24, places=5)
        self.assertAlmostEqual(after, before, delta=.001)
        self.assertAlmostEqual(final, 0, delta=.001)

    def test_other_party_tracks_camera_and_wagon_audio_keep_their_existing_timing(self):
        phase = self.scene.phase;actor = self.actor()
        self.assertEqual(phase['min_seconds'], 1.95)
        self.assertEqual(phase['camera']['move_seconds'], 1.5)
        self.assertEqual(actor['move_seconds'], 1.75)
        self.scene.phase_time = 1.5
        camera = self.scene.camera_position.copy()
        self.assertLess(self.scene.actor_position(actor).x, 581)
        self.assertGreater(self.scene.actor_position(actor).x, 575)
        for person in phase['actors']:
            if person['id'] not in ('caravan', 'lucan', 'clerk'):continue
            self.assertEqual(person['move_seconds'], 1.5)
            self.assertEqual(self.scene.actor_position(person), pygame.Vector2(person['to']))
        self.assertIsNone(self.scene._audio_mode())
        self.scene.phase_time = 1.9
        self.assertEqual(self.scene.camera_position, camera)
        self.assertIsNone(self.scene._audio_mode())

    def test_real_update_starts_the_clip_at_the_last_approved_walk_frame_once(self):
        actor = self.actor();art = self.scene.actor_art['iselin']
        self.update(1.25)
        self.assertEqual(self.state()['action'], 'stop_left')
        self.assertEqual(self.state()['stage'], 'entry')
        self.assertEqual(self.state()['elapsed_ms'], 0)
        self.assertEqual(pygame.image.tobytes(self.scene._frame(actor), 'RGBA'),
                         pygame.image.tobytes(art['loops']['gate_walk_left'][15][0], 'RGBA'))
        cue = self.state()['cue_id']
        for _ in range(20):self.update(.02)
        self.assertAlmostEqual(self.state()['elapsed_ms'], 400)
        before = self.state();self.g.draw();self.g.draw()
        self.assertEqual(self.state(), before)
        self.assertFalse(self.scene.play_actor_action('iselin', 'stop_left', cue))
        self.assertEqual(self.state(), before)

    def test_repeated_updates_reach_the_nominal_stop_cue_without_firing_early(self):
        # These actual scene updates accumulate a few representable steps
        # below 1.25s. They still represent the nominal cue boundary.
        for _ in range(50):self.update(.025)
        self.assertAlmostEqual(self.scene.phase_time, 1.25)
        self.assertEqual(self.state()['action'], 'stop_left')
        self.assertEqual(self.state()['stage'], 'entry')
        self.assertEqual(self.state()['frame_index'], 0)
        self.assertAlmostEqual(self.state()['elapsed_ms'], 0)
        self.start_approach()
        self.update(1.25-1e-11)
        self.assertEqual(self.state()['stage'], 'idle')
        self.update(1e-11)
        self.assertEqual(self.state()['action'], 'stop_left')
        self.assertEqual(self.state()['frame_index'], 0)
        self.assertAlmostEqual(self.state()['elapsed_ms'], 0)

    def test_crossing_the_cue_advances_only_elapsed_time_after_its_start(self):
        self.update(1.43)
        large = self.state();large_position = self.scene.actor_position(self.actor())
        large_image = pygame.image.tobytes(self.scene._frame(self.actor()), 'RGBA')
        self.start_approach()
        for seconds in (.5, .5, .25, .18):self.update(seconds)
        partitioned = self.state()
        self.assertEqual(partitioned['stage'], large['stage'])
        self.assertEqual(partitioned['frame_index'], large['frame_index'])
        self.assertAlmostEqual(partitioned['elapsed_ms'], large['elapsed_ms'])
        self.assertAlmostEqual(large['elapsed_ms'], 180)
        self.assertEqual(self.scene.actor_position(self.actor()), large_position)
        self.assertEqual(pygame.image.tobytes(self.scene._frame(self.actor()), 'RGBA'), large_image)

    def test_exact_stop_frame_boundary_survives_scene_timestamp_subtraction(self):
        # Entry contains 40ms followed by 60ms drawings. At 1.41s the action
        # age is 160ms, exactly the start of entry frame index 3. Subtracting
        # the 1.25s cue from adjacent scene timestamps must not leave index 2.
        def sample(parts):
            self.start_approach()
            for seconds in parts:self.update(seconds)
            return self.state()
        single = sample((1.41,))
        timestamps = (0., .5, 1., 1.25, 1.29, 1.35, 1.41)
        partitioned = sample(tuple(b-a for a, b in zip(timestamps, timestamps[1:])))
        for state in (single, partitioned):
            self.assertEqual(state['stage'], 'entry')
            self.assertEqual(state['frame_index'], 3)
            self.assertAlmostEqual(state['elapsed_ms'], 160)
        # This is 1e-8ms genuinely early, larger than the tolerated arithmetic
        # residue. It must retain the preceding drawing until time reaches it.
        early = sample((1.41-1e-11,))
        self.assertEqual(early['frame_index'], 2)
        self.assertLess(early['elapsed_ms'], 160)
        self.update(1e-11)
        self.assertEqual(self.state()['frame_index'], 3)

    def test_busy_action_at_the_stop_cue_is_rejected_consistently_across_partitions(self):
        # An external review action can overlap the authored cue. It finishes
        # at 1.30s, after the 1.25s cue but before the end of a large 1.40s update.
        # That update must not retroactively accept a cue rejected at its time.
        art = self.scene.actor_art['iselin'];original = art['actions']
        manifest = Path(__file__).resolve().parents[1]/'assets/story/regent_arrival/actors/iselin/animation.json'
        record = json.loads(manifest.read_text())
        record['actions'] = {'competing_review': {
            'entry': [{'pose': 'stand_left', 'duration_ms': 1200}],
            'hold': {'pose': 'stand_left', 'duration_ms': 50},
            'recovery': [{'pose': 'stand_left', 'duration_ms': 50}],
            'rest_pose': 'stand_left'}}
        art['actions'] = {**original, **load_actions(record, art['poses'], manifest)}
        try:
            def sample(parts):
                self.start_approach()
                self.assertTrue(self.scene.play_actor_action('iselin', 'competing_review', 'review:busy'))
                for seconds in parts:self.update(seconds)
                self.assertEqual(self.state()['action'], 'competing_review')
                self.assertEqual(self.state()['stage'], 'rest')
                return self.state()
            large = sample((1.4,))
            self.assertEqual(sample((.5, .5, .25, .15)), large)
        finally:art['actions'] = original

    def test_staged_update_catches_up_but_rendering_never_starts_or_rewinds_stop(self):
        actor = self.actor();self.scene.phase_time = 1.43
        self.g.draw();self.g.draw()
        self.assertEqual(self.state()['stage'], 'idle')
        self.update(0)
        self.assertEqual(self.state()['action'], 'stop_left')
        self.assertAlmostEqual(self.state()['elapsed_ms'], 180)
        before = (self.state(), self.scene.phase_time, self.scene.elapsed,
                  pygame.image.tobytes(self.scene._frame(actor), 'RGBA'))
        for _ in range(3):self.g.draw()
        self.assertEqual((self.state(), self.scene.phase_time, self.scene.elapsed,
                          pygame.image.tobytes(self.scene._frame(actor), 'RGBA')), before)
        self.update(0)
        self.assertEqual(self.state(), before[0])

    def test_pause_and_focus_loss_freeze_the_active_stop_and_root_together(self):
        self.update(1.4)
        def clocks():
            return self.state(), self.scene.phase_time, self.scene.actor_position(self.actor())
        before = clocks()
        key(self.g, pygame.K_ESCAPE);self.assertTrue(self.scene.paused)
        self.update(.5);self.assertEqual(clocks(), before)
        key(self.g, pygame.K_ESCAPE)
        self.g.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        self.update(.5);self.assertEqual(clocks(), before)
        self.g.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.g._music_focused = False
        self.update(.5);self.assertEqual(clocks(), before)
        self.g._music_focused = True
        self.update(.02)
        self.assertGreater(self.state()['elapsed_ms'], before[0]['elapsed_ms'])

    def test_settled_greeting_cannot_replay_stop_during_a_long_dialogue_hold(self):
        self.update(1.94)
        actor = self.actor();art = self.scene.actor_art['iselin']
        self.assertIs(self.scene._frame(actor), art['poses']['gate_stand_left'])
        self.assertEqual(self.scene.actor_position(actor), pygame.Vector2(575, 375))
        self.update(.02)
        self.assertEqual(self.scene.shot, 'gate_greeting')
        self.assertEqual(self.state()['stage'], 'idle')
        self.update(10)
        self.assertEqual(self.scene.shot, 'gate_greeting')
        self.assertIsNotNone(self.scene.dialogue)
        self.assertEqual(self.state()['stage'], 'idle')
        self.assertIs(self.scene._frame(self.actor()), art['poses']['gate_stand_left'])

    def test_reference_sampling_keeps_linear_aerial_gait_and_live_stop_state(self):
        self.update(1.4)
        before = (deepcopy(self.scene.data), self.state(), self.scene.phase_time, self.scene.elapsed)
        observed = []
        original = self.scene._draw_actor
        def draw(canvas, actor, camera):
            if actor['id'] == 'iselin':
                art = self.scene.actor_art['iselin']
                image = self.scene._frame(actor)
                observed.append((self.scene.actor_position(actor), image))
            return original(canvas, actor, camera)
        with patch.object(self.scene, '_draw_actor', side_effect=draw):
            self.scene.ground_reference_frame(pygame.Surface((480, 320)), seconds=-.2)
            self.scene.ground_reference_frame(pygame.Surface((480, 320)), seconds=0.)
        self.assertEqual(len(observed), 2)
        self.assertEqual(observed[0][0], pygame.Vector2(615.8, 375))
        self.assertEqual(observed[1][0], pygame.Vector2(611, 375))
        art = self.scene.actor_art['iselin']
        self.assertIs(observed[0][1], art['loops']['gate_incoming_left'][5][0])
        self.assertIs(observed[1][1], art['loops']['gate_incoming_left'][0][0])
        self.assertEqual(pygame.image.tobytes(observed[1][1], 'RGBA'),
                         pygame.image.tobytes(art['loops']['gate_walk_left'][0][0], 'RGBA'))
        self.assertEqual((self.scene.data, self.state(), self.scene.phase_time, self.scene.elapsed), before)
        self.assertIsNone(self.scene._reference_clock)

    def test_skip_and_pending_continue_discard_stop_without_reward_or_save_changes(self):
        self.assertTrue(self.g.save_progress())
        before = deepcopy(self.g.journey_snapshot())
        self.update(1.4)
        self.assertTrue(self.g.save_progress())
        payload = json.loads(self.path.read_text())
        expected = deepcopy(before);expected['save_context']['playtime'] += 1.4
        self.assertEqual(payload, expected)
        self.assertTrue(RegentArrival.valid_journey(payload))
        self.g.on_title = True
        self.assertTrue(self.g.begin_journey(True), self.g.save_error)
        self.assertEqual(self.scene.shot, 'sanctuary_close')
        self.assertEqual(self.state()['stage'], 'idle')
        self.start_approach();self.update(1.4)
        facts = (deepcopy(self.g.inventory.to_dict()), deepcopy(self.g.quests.to_dict()),
                 deepcopy(self.g.battle_rewards.to_dict()))
        click(self.g, self.scene.skip_rect.center)
        self.assertFalse(self.scene.active);self.assertEqual(self.state()['stage'], 'idle')
        self.assertEqual(self.scene.to_dict(), {'version': 1, 'state': 'seen'})
        self.assertEqual((self.g.inventory.to_dict(), self.g.quests.to_dict(),
                          self.g.battle_rewards.to_dict()), facts)

    def test_gallery_restart_and_close_dispose_real_stop_without_parent_mutation(self):
        self.scene.reset();self.assertTrue(self.g.save_progress())
        raw = self.path.read_bytes()
        parent = (self.g.world, tuple(self.g.player.position), deepcopy(self.g.quests.to_dict()),
                  deepcopy(self.g.inventory.to_dict()), deepcopy(self.g.saved_journey))
        self.g.on_title = True;self.assertTrue(self.g.open_gallery())
        self.assertTrue(self.g.launch_gallery_scene('regent_arrival'))
        session = self.g.gallery_session
        try:
            child = session.game.regent_arrival
            self.start_approach(child);session.update(1.4)
            self.assertEqual(self.state(child)['action'], 'stop_left')
            self.assertTrue(session.restart())
            self.assertEqual(self.state(child)['stage'], 'idle')
            session = self.g.gallery_session;child = session.game.regent_arrival
            self.assertEqual(child.shot, 'sanctuary_close')
            self.start_approach(child);session.update(1.4)
            self.assertEqual(self.state(child)['action'], 'stop_left')
            session.close();self.assertEqual(self.state(child)['stage'], 'idle')
            self.assertEqual(self.path.read_bytes(), raw)
            self.assertEqual((self.g.world, tuple(self.g.player.position), self.g.quests.to_dict(),
                              self.g.inventory.to_dict(), self.g.saved_journey), parent)
        finally:
            if self.g.gallery_session is not None:self.g.gallery_session.close()
            self.g.close_gallery();self.g.on_title = False


if __name__ == '__main__':unittest.main()
