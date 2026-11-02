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

    def test_gate_camera_holds_while_the_whole_party_shrinks_into_the_landscape(self):
        phase = self.frame('gate_admission', 0)
        actors = [actor for actor in phase['actors'] if actor['id'] in ('aldric', 'clerk', 'caravan')]
        self.assertEqual({actor['id'] for actor in actors}, {'aldric', 'clerk', 'caravan'})
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

    def test_guards_are_near_the_posts_and_clear_of_the_approaching_party(self):
        phase = self.frame('gate_approach', 0)
        guards = [actor for actor in phase['actors'] if actor['id'] == 'guard']
        self.assertEqual(len(guards), 2)
        # Actual painted cap/base centers, rather than the old far-away duty
        # stations. The west/east guards each move nearer their own gatepost.
        stations = ((pygame.Vector2(481, 296), pygame.Vector2(530, 375)),
                    (pygame.Vector2(670, 287), pygame.Vector2(690, 345)))
        for actor, (post, old_station) in zip(guards, stations):
            self.assertLess(self.scene.actor_position(actor).distance_to(post),
                            old_station.distance_to(post)*.9)
        for index in range(round(phase['min_seconds']*20)+1):
            self.scene.phase_time = index/20
            for actor in phase['actors']:
                if actor['id'] not in ('aldric', 'clerk', 'caravan'):
                    continue
                position = self.scene.actor_position(actor)
                for guard in guards:
                    self.assertGreater(position.distance_to(self.scene.actor_position(guard)), 30.)

    def test_caravan_follows_aldric_through_the_same_gate_aperture(self):
        phase = self.frame('gate_admission', 0)
        crossings = {}
        for actor in phase['actors']:
            if actor['id'] not in ('aldric', 'clerk', 'caravan'):
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
        self.assertEqual(set(crossings), {'aldric', 'clerk', 'caravan'})
        self.assertLess(crossings['aldric'][0], crossings['clerk'][0])
        self.assertLess(crossings['clerk'][0], crossings['caravan'][0])
        self.assertLess(abs(crossings['aldric'][1]-crossings['caravan'][1]), 5)
        self.assertTrue(all(510 <= x <= 640 for _, x in crossings.values()))

    def test_turn_poses_precede_rear_walk_and_scaled_feet_stay_on_road(self):
        phase = self.frame('gate_admission', 0)
        for actor in phase['actors']:
            if actor['id'] not in ('aldric', 'clerk', 'caravan'):
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

    def test_approach_greeting_and_admission_start_share_exact_party_feet(self):
        stations = []
        for shot, seconds in (('gate_approach', 1.5), ('gate_greeting', 0), ('gate_admission', 0)):
            phase = self.frame(shot, seconds)
            stations.append({actor['id']: self.scene.actor_position(actor)
                             for actor in phase['actors'] if actor['id'] in ('aldric', 'clerk', 'caravan')})
        self.assertEqual(set(stations[0]), {'aldric', 'clerk', 'caravan'})
        self.assertEqual(stations[0], stations[1])
        self.assertEqual(stations[1], stations[2])
        clerk = next(actor for actor in self.scene.phase['actors'] if actor['id'] == 'clerk')
        self.assertEqual(clerk['route_offset'], [0, 24])
        centerline = {**clerk, 'route_offset': [0, 0]}
        for seconds in (0., 2., 5., 10.):
            self.scene.phase_time = seconds
            offset = self.scene.actor_position(clerk)-self.scene.actor_position(centerline)
            scale = self.scene._route_sample(clerk)[1]
            self.assertEqual(offset.x, 0.)
            self.assertAlmostEqual(offset.y, 24*scale)

    def test_gate_party_does_not_severely_interpenetrate_guard_or_horse_silhouettes(self):
        """The historical name covers ground clearance/occlusion, not 2-D body separation."""
        def silhouette(actor):
            image = self.scene._frame(actor)
            scale = self.scene._actor_scale(actor)
            if scale != 1.:
                image = pygame.transform.scale(image, tuple(max(1, round(n*scale)) for n in image.get_size()))
            anchor = pygame.Vector2(self.scene.actor_art[actor['id']]['anchor'])*scale
            origin = self.scene.actor_position(actor)-anchor
            origin = pygame.Vector2(round(origin.x), round(origin.y))
            mask = pygame.mask.from_surface(image)
            self.assertGreater(mask.count(), 0)
            # Only the bottom four native pixels are boot/hoof/wheel contacts;
            # a coat, horse's body or wagon canopy is not a ground footprint.
            bottom = image.get_bounding_rect().bottom
            contacts = [origin+(x, y)
                        for y in range(bottom-max(1, round(4*scale)), bottom)
                        for x in range(image.get_width()) if mask.get_at((x, y))]
            self.assertTrue(contacts)
            return mask, origin, scale, contacts

        checked = 0
        same_depth_checked = {'aldric': 0, 'clerk': 0}
        depth_unit = self.scene.data['routes']['gate_road']['depth_unit']
        for shot in ('gate_approach', 'gate_greeting', 'gate_admission'):
            phase = self.frame(shot, 0)
            for index in range(round(phase['min_seconds']*10)+1):
                self.scene.phase_time = index/10
                people = [actor for actor in phase['actors'] if actor['id'] in ('aldric', 'clerk')]
                obstacles = [actor for actor in phase['actors'] if actor['id'] in ('guard', 'caravan')]
                for person in people:
                    mask, origin, scale, contacts = silhouette(person)
                    for obstacle in obstacles:
                        other, other_origin, other_scale, other_contacts = silhouette(obstacle)
                        context = (shot, self.scene.phase_time, person['id'], obstacle['id'])
                        if obstacle['id'] == 'guard':
                            offset = tuple(round(b-a) for a, b in zip(origin, other_origin))
                            fraction = mask.overlap_area(other, offset)/min(mask.count(), other.count())
                            self.assertLessEqual(fraction, .05, (*context, fraction))
                        else:
                            # Recover separation of ground planes from the
                            # perspective scale s=1/(1+depth/depth_unit), not
                            # route_start/end or matching spacing metadata.
                            # At comparable depths require a boot-sized margin
                            # between actual painted ground contacts. Further
                            # along the bend even the foot roots can project
                            # almost together despite distinct physical depths.
                            depth_gap = depth_unit*abs(1/scale-1/other_scale)
                            contact_gap = min(a.distance_to(b) for a in contacts for b in other_contacts)
                            contact_gap /= min(scale, other_scale)
                            self.assertGreaterEqual(max(depth_gap, contact_gap), 12.,
                                                    (*context, depth_gap, contact_gap))
                            if depth_gap < 12.:
                                same_depth_checked[person['id']] += 1
                        checked += 1
        self.assertGreater(checked, 900)
        for identifier, count in same_depth_checked.items():
            self.assertGreater(count, 0, identifier)

        # Full projected-body overlap is legitimate only with correct depth
        # drawing. Exercise both orders using real art and the production draw,
        # not a separately sorted test composite or a relaxed overlap limit.
        for shot, seconds, identifier, nearer in (
                ('gate_approach', .5, 'clerk', 'clerk'),
                ('gate_admission', 0., 'clerk', 'clerk'),
                ('gate_admission', 3.1, 'clerk', 'caravan'),
                ('gate_admission', 8.2, 'aldric', 'caravan')):
            with self.subTest(shot=shot, seconds=seconds, person=identifier, nearer=nearer):
                phase = self.frame(shot, seconds)
                actors = {actor['id']: actor for actor in phase['actors']
                          if actor['id'] in (identifier, 'caravan')}
                farther = 'caravan' if nearer == identifier else identifier
                self.assertGreater(self.scene.actor_position(actors[nearer]).y,
                                   self.scene.actor_position(actors[farther]).y)
                layers = {}
                for actor_id, actor in actors.items():
                    layer = pygame.Surface((480, 320), pygame.SRCALPHA)
                    self.scene._draw_actor(layer, actor, self.scene.camera_position)
                    layers[actor_id] = layer
                # Opaque, differently coloured overlap pixels distinguish
                # which actor won, without alpha-blending/background ambiguity.
                overlap = pygame.mask.from_surface(layers[identifier], 254).overlap_mask(
                    pygame.mask.from_surface(layers['caravan'], 254), (0, 0))
                self.assertGreater(overlap.count(), 0)
                canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
                self.scene.draw(canvas, pygame.Surface((480, 320), pygame.SRCALPHA))
                compared = 0
                for bounds in overlap.get_bounding_rects():
                    for y in range(bounds.top, bounds.bottom):
                        for x in range(bounds.left, bounds.right):
                            point = (x, y)
                            if (overlap.get_at(point) and
                                    layers[nearer].get_at(point) != layers[farther].get_at(point)):
                                self.assertEqual(canvas.get_at(point), layers[nearer].get_at(point), point)
                                compared += 1
                self.assertGreater(compared, 0)

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
        self.assertIn('crossroads_establishing', phases)
        black = [alpha for name, _, alpha in observations if name == 'gate_departure_black']
        self.assertTrue(black)
        self.assertEqual(set(black), {255})
        establishing = [(seconds, alpha) for name, seconds, alpha in observations
                if name == 'crossroads_establishing']
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
