"""Gate travel has visible depth and location changes have time to register."""
import copy
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from main import Game
from quests import REGENT_QUEST
from test_mill_battle_gameplay import click, key
from test_regent_arrival import acknowledge_report, seed_mill_report


class RegentArrivalStagingTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='arrival-staging-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'
        self.g = Game(fullscreen=False, start_on_title=False,
                      save_path=self.path, settings_path=self.directory/'settings.json')
        self.g.audio.set_effects(0)
        pygame.event.clear()
        seed_mill_report(self.g)
        acknowledge_report(self.g)
        self.g.update(.05, (0, 0), False)
        self.scene = self.g.regent_arrival
        self.assertTrue(self.scene.active)

    def tearDown(self):
        if self.g.gallery_session is not None:
            self.g.gallery_session.close()
        self.scene.audio.stop()
        self.g.opening_audio.reset()
        self.g.regional_audio.reset()
        self.g.music.stop()
        pygame.quit()

    def reach(self, shot):
        for _ in range(4000):
            if self.scene.shot == shot:
                return
            self.assertTrue(self.scene.active, ('Ended before', shot))
            if self.scene.dialogue is not None:
                key(self.g, pygame.K_SPACE)
            self.g.update(.05, (0, 0), False)
        self.fail(('Did not reach', shot, self.scene.shot))

    def frame(self, shot, seconds):
        """A nonpersistent visual probe; progression tests use ordinary input."""
        self.scene.phase_index = next(i for i, phase in enumerate(self.scene.data['phases'])
                                      if phase['id'] == shot)
        self.scene.phase_time = seconds
        self.scene.dialogue_index = self.scene.page_index = 0
        self.scene._load()
        return self.scene.phase

    def render(self):
        canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
        ui = pygame.Surface((480, 320), pygame.SRCALPHA)
        self.scene.draw(canvas, ui)
        return ui

    def test_gate_camera_holds_while_both_figures_shrink_into_the_landscape(self):
        phase = self.frame('gate_admission', 0)
        actors = [actor for actor in phase['actors'] if actor['id'] in ('aldric', 'caravan')]
        camera = self.scene.camera_position.copy()
        observations = {actor['id']: [] for actor in actors}
        for index in range(round(phase['min_seconds']*10)):
            self.scene.phase_time = index/10
            self.assertEqual(self.scene.camera_position, camera)
            for actor in actors:
                observations[actor['id']].append((self.scene.actor_position(actor),
                                                self.scene._actor_scale(actor)))
        for identifier, samples in observations.items():
            with self.subTest(actor=identifier):
                positions, scales = zip(*samples)
                self.assertLess(positions[-1].y, 296)
                self.assertLess(scales[-1], scales[0]*.65)
                self.assertTrue(all(b <= a+.001 for a, b in zip(scales, scales[1:])))
                self.assertGreater(positions[0].y-positions[-1].y, 90)

    def test_caravan_follows_aldric_through_the_same_gate_aperture(self):
        phase = self.frame('gate_admission', 0)
        crossings = {}
        for actor in phase['actors']:
            if actor['id'] not in ('aldric', 'caravan'):
                continue
            previous = self.scene.actor_position(actor)
            for index in range(1, round(phase['min_seconds']*40)):
                self.scene.phase_time = index/40
                position = self.scene.actor_position(actor)
                if previous.y > 296 >= position.y:
                    fraction = (previous.y-296)/(previous.y-position.y)
                    crossings[actor['id']] = (index/40, previous.x+(position.x-previous.x)*fraction)
                    break
                previous = position
            self.scene.phase_time = 0
        self.assertEqual(set(crossings), {'aldric', 'caravan'})
        self.assertLess(crossings['aldric'][0], crossings['caravan'][0])
        self.assertLess(abs(crossings['aldric'][1]-crossings['caravan'][1]), 5)
        self.assertTrue(all(510 <= x <= 640 for _, x in crossings.values()))

    def test_turn_poses_precede_rear_walk_and_scaled_feet_stay_on_road(self):
        phase = self.frame('gate_admission', 0)
        for actor in phase['actors']:
            if actor['id'] not in ('aldric', 'caravan'):
                continue
            with self.subTest(actor=actor['id']):
                poses = []
                for index in range(round(phase['min_seconds']*10)):
                    self.scene.phase_time = index/10
                    pose = self.scene.actor_pose(actor)
                    if not poses or poses[-1] != pose:
                        poses.append(pose)
                    canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
                    rect = self.scene._draw_actor(canvas, actor, self.scene.camera_position)
                    ground = self.scene.actor_position(actor)-self.scene.camera_position
                    self.assertLessEqual(abs(rect.bottom-ground.y), 3)
                self.assertIn(poses[0], ('stand_left', 'parked_left', 'walk_left'))
                turning = [pose for pose in poses if pose in ('turn_left_back', 'walk_left_back')]
                self.assertTrue(turning, poses)
                self.assertIn('walk_back', poses)
                self.assertLess(poses.index(turning[0]), poses.index('walk_back'))
                self.scene.phase_time = 0

    def test_gate_post_hides_only_actors_behind_it_and_keeps_road_aperture_clear(self):
        phase = self.frame('gate_admission', 2)
        phase['actors'] = []
        solid = pygame.Surface((80, 96), pygame.SRCALPHA)
        solid.fill('#ff00ff')
        self.scene.actor_art['aldric']['poses']['stand_left'] = solid
        actor = {'id': 'aldric', 'pose': 'stand_left', 'position': [670, 310]}
        phase['actors'].append(actor)
        camera = self.scene.camera_position
        post = (round(670-camera.x), round(250-camera.y))
        expected = self.scene.scenery['gate']['background'].get_at((670, 250))
        self.assertEqual(self.render().get_at(post)[:3], (255, 0, 255))
        actor['position'][1] = 296
        self.assertEqual(self.render().get_at(post)[:3], expected[:3])
        actor['position'] = [575, 296]
        aperture = (round(575-camera.x), round(280-camera.y))
        self.assertEqual(self.render().get_at(aperture)[:3], (255, 0, 255))

    def test_location_change_is_hidden_by_black_then_revealed_before_dialogue(self):
        self.reach('gate_admission')
        frozen = (self.g.elapsed_ms, tuple(self.g.player.position),
                  copy.deepcopy(self.g.inventory.to_dict()))
        observations = []
        while self.scene.shot != 'locals':
            self.assertIsNone(self.scene.dialogue)
            observations.append((self.scene.shot, self.scene.phase_time, self.scene.fade_alpha))
            self.g.update(.05, (1, 1), True)
            self.assertEqual((self.g.elapsed_ms, tuple(self.g.player.position),
                              self.g.inventory.to_dict()), frozen)
            self.assertLess(len(observations), 1000)
        phases = [name for name, _, _ in observations]
        self.assertIn('gate_departure_black', phases)
        self.assertIn('bridge_establishing', phases)
        black = [alpha for name, _, alpha in observations if name == 'gate_departure_black']
        self.assertTrue(black)
        self.assertEqual(set(black), {255})
        establishing = [(seconds, alpha) for name, seconds, alpha in observations
                        if name == 'bridge_establishing']
        self.assertGreater(establishing[0][1], 230)
        self.assertGreaterEqual(sum(alpha == 0 for _, alpha in establishing)*.05, 1.4)
        for _ in range(20):
            if self.scene.dialogue is not None:
                break
            self.g.update(.05, (0, 0), False)
        self.assertIsNotNone(self.scene.dialogue)
        text = self.scene.dialogue['text']
        self.g.update(30, (0, 0), False)
        self.assertEqual(self.scene.shot, 'locals')
        self.assertEqual(self.scene.dialogue['text'], text)

    def test_black_hold_draws_black_and_escape_focus_pause_its_clock(self):
        self.reach('gate_departure_black')
        self.assertEqual(self.render().get_at((240, 160))[:3], (0, 0, 0))
        before = (self.scene.shot, self.scene.phase_time, self.scene.fade_alpha)
        key(self.g, pygame.K_ESCAPE)
        self.g.update(3, (0, 0), False)
        self.assertEqual((self.scene.shot, self.scene.phase_time, self.scene.fade_alpha), before)
        key(self.g, pygame.K_ESCAPE)
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.g.handle_events()
        self.g.update(3, (0, 0), False)
        self.assertEqual((self.scene.shot, self.scene.phase_time, self.scene.fade_alpha), before)
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.g.handle_events()
        self.g.update(.1, (0, 0), False)
        self.assertGreater(self.scene.phase_time, before[1])

    def test_skip_during_black_preserves_quest_outcome_and_player_station(self):
        self.reach('gate_departure_black')
        before = (tuple(self.g.player.position), self.g.inventory.to_dict())
        click(self.g, self.scene.skip_rect.center)
        self.assertFalse(self.scene.active)
        self.assertEqual(self.scene.state, 'seen')
        self.assertEqual((tuple(self.g.player.position), self.g.inventory.to_dict()), before)
        self.assertEqual(self.g.quests.status(REGENT_QUEST), 'available')
        self.assertEqual(self.g.regent_quest.stage, 'idle')
        self.assertEqual(self.scene.audio.channels, [])
        self.assertEqual(self.g.saved_journey['regent_arrival'], {'version': 1, 'state': 'seen'})


if __name__ == '__main__':
    unittest.main()
