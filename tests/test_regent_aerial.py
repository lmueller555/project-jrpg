"""The bird-led opening remains geographic, continuous and player-owned."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
import numpy as np

from main import Game
from quests import MILL_QUEST, REGENT_QUEST
from test_mill_battle_gameplay import click, key
from test_regent_arrival import acknowledge_report, seed_mill_report


AERIAL_SHOTS = ('aerial_region', 'aerial_bank', 'aerial_gate', 'aerial_descent')

# Observed dirt-lane centers in the actual 1536x1024 overhead painting, from
# the southeast approach to the opening. These are independent of the motion
# controller's route, and include the bend that the old straight route missed.
PAINTED_APPROACH_PIXELS = (
    (1163, 1023), (1102, 960), (1034, 900), (972, 850),
    (905, 800), (847, 755), (809, 720), (790, 690),
    (777, 650), (773, 600), (768, 550), (768.5, 514),
)


def approach_distance(point):
    point = pygame.Vector2(point)
    distances = []
    for first, second in zip(PAINTED_APPROACH_PIXELS, PAINTED_APPROACH_PIXELS[1:]):
        first, second = pygame.Vector2(first), pygame.Vector2(second)
        delta = second-first
        fraction = max(0., min(1., (point-first).dot(delta)/delta.length_squared()))
        distances.append(point.distance_to(first+delta*fraction))
    return min(distances)


class RegentAerialTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='regent-aerial-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.g = self.make_game(self.directory/'journey.json')
        self.other_games = []
        seed_mill_report(self.g)
        acknowledge_report(self.g)
        self.g.update(.05, (0, 0), False)
        self.scene = self.g.regent_arrival
        self.assertTrue(self.scene.active)
        self.phases = {phase['id']: phase for phase in self.scene.data['phases']}
        self.offsets = {}
        offset = 0.
        for shot in AERIAL_SHOTS:
            self.offsets[shot] = offset
            offset += self.phases[shot]['min_seconds']
        self.duration = offset

    def make_game(self, path, *, title=False):
        game = Game(fullscreen=False, start_on_title=title,
                    save_path=path, settings_path=self.directory/'settings.json')
        game.audio.set_effects(0)
        game.audio.set_music(0)
        pygame.event.clear()
        return game

    def tearDown(self):
        for game in [self.g, *self.other_games]:
            if game.gallery_session is not None:
                game.gallery_session.close()
            game.regent_arrival.audio.stop()
            game.regional_audio.reset()
            game.opening_audio.reset()
            game.music.stop()
        pygame.quit()

    def at(self, shot, fraction):
        return self.offsets[shot]+self.phases[shot]['min_seconds']*fraction

    def sample(self, seconds, reduced=False):
        return self.scene.aerial.sample(seconds, reduced_motion=reduced)

    def test_scene_dispatcher_renders_aerial_instead_of_looking_up_a_backdrop(self):
        self.frame('aerial_region', 1.)
        self.scene._load()
        canvas = pygame.Surface((480, 320))
        self.scene._draw_plate(canvas)
        self.assertGreater(int(pygame.surfarray.array3d(canvas).max()), 0)

    def test_gallery_draws_all_aerial_scenes_even_when_shot_ids_change(self):
        for renamed in (False, True):
            with self.subTest(renamed=renamed):
                parent = self.make_game(self.directory/('gallery-%s.json' % renamed), title=True)
                self.other_games.append(parent)
                self.assertTrue(parent.open_gallery())
                self.assertTrue(parent.launch_gallery_scene('regent_arrival'))
                scene = parent.gallery_session.game.regent_arrival
                expected = set()
                for phase in scene.data['phases']:
                    if phase['scene'] == 'aerial':
                        if renamed:phase['id'] = 'retimed_'+phase['id']
                        expected.add(phase['id'])
                scene._validate()
                observed = set()
                for _ in range(3000):
                    if parent.gallery_session is None:break
                    scene = parent.gallery_session.game.regent_arrival
                    if scene.active:
                        if scene.phase['scene'] == 'aerial':observed.add(scene.shot)
                        if scene.dialogue is not None:key(parent, pygame.K_SPACE)
                    parent.update(.1, (0, 0), False)
                    parent.draw()
                self.assertIsNone(parent.gallery_session)
                self.assertTrue(parent.on_gallery)
                self.assertEqual(observed, expected)

    def frame(self, shot, seconds):
        """Visual probe only; timeline tests below use production input."""
        self.scene.phase_index = next(i for i, phase in enumerate(self.scene.data['phases'])
                                      if phase['id'] == shot)
        self.scene.phase_time = seconds
        self.scene.dialogue_index = self.scene.page_index = 0

    def render(self):
        canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
        ui = pygame.Surface((480, 320), pygame.SRCALPHA)
        self.scene.draw(canvas, ui)
        return canvas

    def reach(self, shot):
        for _ in range(5000):
            if self.scene.shot == shot:
                return
            self.assertTrue(self.scene.active, ('Ended before', shot))
            if self.scene.dialogue is not None:
                key(self.g, pygame.K_SPACE)
            self.g.update(.05, (0, 0), False)
        self.fail(('Did not reach', shot, self.scene.shot))

    def world_signature(self):
        return (self.g.elapsed_ms, tuple(self.g.player.position),
                tuple((world.data['id'], actor.data['id'], tuple(actor.position))
                      for world in self.g.scenes.values() for actor in world.npcs),
                copy.deepcopy(self.g.inventory.to_dict()), set(self.g.social.flags))

    def test_overhead_approach_keeps_wheels_and_hooves_on_the_painted_road(self):
        self.scene._load()
        aerial = self.scene.aerial
        aerial._load()
        plane = aerial.planes['gate_overhead']
        x0, y0, width, height = plane['bounds_tiles']
        iw, ih = plane['image'].get_size()
        # Visible contacts observed on the source sprite, rather than the
        # vehicle's large transparent canvas or a diagnostic center point.
        contacts = {'caravan': ((59, 116), (101, 116), (60, 76),
                                (101, 76), (70, 50), (90, 50)),
                    'aldric': ((24, 55),)}
        checked = 0
        painted_checks = 0
        original_sprite = aerial._sprite
        for index in range(round(self.duration*4)):
            seconds = index/4
            snapshot = self.sample(seconds)
            if seconds < 18 or snapshot['ground_handoff'] or snapshot['canopy']['coverage'] > .05:
                continue
            drawn = {}

            def background_without_party(canvas, actor, pose, point, scale, clock, *args, **kwargs):
                if actor in contacts:
                    drawn[actor] = pygame.Vector2(point)
                elif actor == 'bird':
                    return original_sprite(canvas, actor, pose, point, scale, clock, *args, **kwargs)

            background = pygame.Surface((480, 320))
            with patch.object(aerial, '_sprite', side_effect=background_without_party):
                aerial.draw(background, seconds, lambda *_args, **_kwargs: None)
            inverse = np.linalg.inv(aerial._view_matrix(snapshot['view']))
            for actor, points in contacts.items():
                if actor not in drawn:
                    continue
                item = snapshot['projected_actors'][actor]
                # A route on the detail painting is not sufficient while that
                # painting is still transparent over a different-scale road.
                # Inspect the actual composed ground beneath the actor too.
                point = drawn[actor]
                if 3 <= point.x < 477 and 3 <= point.y < 317:
                    colors = [background.get_at((round(point.x)+dx, round(point.y)+dy))
                              for dx in range(-2, 3) for dy in range(-2, 3)]
                    tan = sum(c.r > c.g+10 and c.g > c.b+15 and c.r > 80 for c in colors)
                    self.assertGreaterEqual(tan/len(colors), .2, (seconds, actor, tuple(point)))
                    painted_checks += 1
                anchor = pygame.Vector2(aerial.actors[actor]['anchor'])
                for contact in points:
                    delta = (pygame.Vector2(contact)-anchor).rotate(item['screen_heading'])*item['scale']
                    screen = pygame.Vector2(item['screen_xy'])+delta
                    if not (2 <= screen.x < 478 and 2 <= screen.y < 318):
                        continue
                    world = inverse@np.array((screen.x, screen.y, 1.))
                    world = world[:2]/world[2]
                    pixel = ((world[0]-x0)/width*iw, (world[1]-y0)/height*ih)
                    if not (514 <= pixel[1] <= 1023):
                        continue
                    # The narrow bend is about 75--80 pixels across. Five
                    # pixels allow the painting's gravel/grass edge variation.
                    self.assertLessEqual(approach_distance(pixel), 43.,
                                         (seconds, actor, contact, tuple(pixel)))
                    checked += 1
        self.assertGreater(checked, 30)
        self.assertGreater(painted_checks, 5)

    def test_turning_an_overhead_vehicle_preserves_its_rear_ground_anchor(self):
        aerial = self.scene.aerial
        aerial._load()
        data = aerial.actors['caravan']
        marker = pygame.Surface(data['canvas'], pygame.SRCALPHA)
        anchor = data['anchor']
        pygame.draw.rect(marker, '#ff00ff', (anchor[0]-1, anchor[1]-1, 3, 3))
        data['poses']['overhead'] = marker
        for heading in (0, -25, -45, -70):
            with self.subTest(heading=heading):
                canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
                aerial._sprite(canvas, 'caravan', 'overhead', (240, 160), 1., 0., angle=-heading)
                pixels = pygame.surfarray.array3d(canvas)
                selected = (pixels[:, :, 0] == 255) & (pixels[:, :, 1] == 0) & (pixels[:, :, 2] == 255)
                xs, ys = np.nonzero(selected)
                self.assertGreater(len(xs), 0)
                self.assertLessEqual(pygame.Vector2(float(xs.mean()), float(ys.mean())).distance_to((240, 160)), 1.5)

    def test_post_canopy_zoom_has_real_walking_not_only_camera_motion(self):
        self.scene._load()
        snapshots = [(index/10, self.sample(index/10)) for index in range(round(self.duration*10))]
        clear = next(seconds for seconds, view in snapshots
                     if view['ground_handoff'] and view['canopy']['coverage'] == 0)
        times = [clear+.2+(self.duration-clear-.4)*fraction for fraction in (0., .2, .4, .6, .8, 1.)]
        actual = {'aldric': [], 'caravan': []}
        frames = {'aldric': set(), 'caravan': set()}
        original = self.scene._draw_actor

        def record(canvas, actor, camera):
            if actor['id'] in actual:
                actual[actor['id']].append(self.scene.actor_position(actor).copy())
                frames[actor['id']].add(pygame.image.tobytes(self.scene._frame(actor), 'RGBA'))
            return original(canvas, actor, camera)

        with patch.object(self.scene, '_draw_actor', side_effect=record):
            for seconds in times:
                self.frame('aerial_descent', seconds-self.offsets['aerial_descent'])
                self.render()
        for actor, positions in actual.items():
            with self.subTest(actor=actor):
                self.assertEqual(len(positions), len(times))
                self.assertTrue(all(b.x < a.x-.5 for a, b in zip(positions, positions[1:])))
                self.assertGreater(positions[0].x-positions[-1].x, 40.)
                self.assertLess(max(p.y for p in positions)-min(p.y for p in positions), 1.)
                self.assertGreater(len(frames[actor]), 1, 'A walking actor kept a single idle image')
        self.assertGreater(self.sample(times[0])['ground_viewport'][2],
                           self.sample(times[-1])['ground_viewport'][2])

    def test_descent_and_ground_approach_preserve_native_walking_velocity(self):
        self.scene._load()
        positions = {'aldric': [], 'caravan': []}
        original = self.scene._draw_actor

        def record(canvas, actor, camera):
            if actor['id'] in positions:
                positions[actor['id']].append(self.scene.actor_position(actor).copy())
            return original(canvas, actor, camera)

        with patch.object(self.scene, '_draw_actor', side_effect=record):
            self.frame('aerial_descent', self.phases['aerial_descent']['min_seconds']-.1)
            self.render()
            for seconds in (0., .1):
                self.frame('gate_approach', seconds)
                self.render()
        for actor, samples in positions.items():
            with self.subTest(actor=actor):
                self.assertEqual(len(samples), 3)
                before, after = samples[0]-samples[1], samples[1]-samples[2]
                self.assertGreater(before.x, 1.)
                self.assertLess(before.distance_to(after), .01)

    def test_bird_flies_west_then_banks_left_toward_the_southern_gate(self):
        west_views = [self.sample(self.at('aerial_region', t)) for t in (.2, .5, .8)]
        west = [pygame.Vector2(view['bird']['world_xy']) for view in west_views]
        self.assertTrue(all(b.x < a.x for a, b in zip(west, west[1:])))
        self.assertLess(max(p.y for p in west)-min(p.y for p in west), 5)
        # The rendered ground plane must travel with the bird. A diagnostic
        # camera point that moves while the viewport stays put is insufficient.
        viewport_pan = west_views[0]['view']['focus'][0]-west_views[-1]['view']['focus'][0]
        self.assertGreater(viewport_pan, (west[0].x-west[-1].x)*.5)
        self.assertGreater(west_views[-1]['landmarks']['eldenmere'][0],
                           west_views[0]['landmarks']['eldenmere'][0]+20)
        visible_flight = [self.sample(self.at('aerial_region', fraction))
                          for fraction in (.1, .25, .4, .55, .7, .85)]
        bird_x = [frame['bird']['screen_xy'][0] for frame in visible_flight]
        camera_roll = [frame['view']['roll'] for frame in visible_flight]
        self.assertGreater(max(bird_x)-min(bird_x), 5.)
        self.assertGreater(max(camera_roll)-min(camera_roll), .1)
        turn_start = pygame.Vector2(self.sample(self.at('aerial_bank', .02))['bird']['world_xy'])
        turn_end = pygame.Vector2(self.sample(self.at('aerial_bank', .98))['bird']['world_xy'])
        self.assertLess(turn_end.x, turn_start.x)
        self.assertGreater(turn_end.y, turn_start.y)
        south = [pygame.Vector2(self.sample(self.at('aerial_gate', t))['bird']['world_xy'])
                 for t in (.15, .5, .85)]
        self.assertTrue(all(b.y > a.y for a, b in zip(south, south[1:])))
        self.assertLess(max(p.x for p in south)-min(p.x for p in south), 5)
        for seconds in (2., self.at('aerial_bank', .5), self.at('aerial_gate', .6)):
            sample = self.sample(seconds)
            self.assertGreater(sample['camera']['altitude'], sample['bird']['altitude'])

    def test_camera_and_bird_do_not_teleport_at_flight_stage_boundaries(self):
        for seconds in list(self.offsets.values())[1:]:
            with self.subTest(seconds=seconds):
                before = self.sample(seconds-.001)
                after = self.sample(seconds+.001)
                for actor in ('bird', 'camera'):
                    self.assertLess(pygame.Vector2(before[actor]['world_xy']).distance_to(
                        after[actor]['world_xy']), 1.)
                    self.assertLess(abs(before[actor]['altitude']-after[actor]['altitude']), 2.)
                self.assertLess(abs(before['camera']['roll']-after['camera']['roll']), .1)
                self.assertLess(pygame.Vector2(before['view']['focus']).distance_to(
                    after['view']['focus']), 1.)
                self.assertLess(abs(before['view']['span']-after['view']['span']), 3.)
                self.assertLess(abs(before['view']['tilt']-after['view']['tilt']), .1)

    def test_flyover_crosses_the_actual_southern_checkpoint_from_inside_the_valley(self):
        region = json.loads((Path(__file__).resolve().parents[1]/
                            'assets/maps/overworld/elden_vale/region.json').read_text())
        gate = next(gate for gate in region['gates'] if gate['id'] == 'south_checkpoint')
        wall = next(wall for wall in region['walls'] if wall['id'] == 'south_wall')
        samples = [self.sample(self.at('aerial_gate', fraction))
                   for fraction in (0., .25, .5, .75, 1.)]
        positions = [pygame.Vector2(sample['bird']['world_xy']) for sample in samples]
        self.assertLess(positions[0].y, wall['y'])
        self.assertGreater(positions[-1].y, wall['y'])
        self.assertTrue(all(abs(position.x-gate['tile_position'][0]) <= 2.
                            for position in positions))
        # The actors must be present during the overhead beat, rather than
        # appearing for the first time after the camera reaches ground level.
        actors = [sample['projected_actors'] for sample in samples]
        self.assertTrue(any({'aldric', 'caravan'} <= set(frame) for frame in actors))
        self.assertTrue(any(sum('guard' in identifier for identifier in frame) >= 2
                            for frame in actors))
        self.assertTrue(any(len(frame) >= 4 and all(
            actor['view'] == 'overhead' and
            0 <= actor['screen_xy'][0] < 480 and 0 <= actor['screen_xy'][1] < 320
            for actor in frame.values()) for frame in actors))

    def test_repeated_draws_cannot_advance_the_analytic_camera_or_world(self):
        seconds = self.at('aerial_bank', .45)
        self.frame('aerial_bank', self.phases['aerial_bank']['min_seconds']*.45)
        before = copy.deepcopy(self.sample(seconds))
        world = self.world_signature()
        first = pygame.image.tobytes(self.render(), 'RGB')
        for _ in range(3):
            self.assertEqual(pygame.image.tobytes(self.render(), 'RGB'), first)
        self.sample(seconds+3.)
        self.assertEqual(self.sample(seconds), before)
        self.assertEqual(self.world_signature(), world)

    def test_actual_input_plays_all_four_aerial_beats_without_advancing_exploration(self):
        self.reach(AERIAL_SHOTS[0])
        frozen = self.world_signature()
        observed = []
        rendered = set()
        for _ in range(1500):
            if self.scene.shot == 'gate_approach':
                break
            self.assertIn(self.scene.shot, AERIAL_SHOTS)
            self.assertIsNone(self.scene.dialogue)
            if not observed or observed[-1] != self.scene.shot:
                observed.append(self.scene.shot)
            if self.scene.phase_time > 1.25 and self.scene.shot not in rendered:
                image = self.render()
                pixels = pygame.surfarray.array3d(image)
                self.assertGreater(float(pixels.std()), 15.)
                rendered.add(self.scene.shot)
            self.g.update(.05, (1, 1), True)
            self.assertEqual(self.world_signature(), frozen)
        self.assertEqual(observed, list(AERIAL_SHOTS))
        self.assertEqual(rendered, set(AERIAL_SHOTS))
        self.assertEqual(self.scene.shot, 'gate_approach')
        self.assertEqual(self.g.quests.status(MILL_QUEST), 'completed')
        self.assertEqual(self.g.quests.status(REGENT_QUEST), 'available')
        self.assertEqual(self.scene.state, 'pending')

    def test_descent_handoff_matches_the_ground_shot_without_a_black_frame(self):
        for reduced in (False, True):
            with self.subTest(reduced_motion=reduced):
                self.g.audio.reduced_motion = reduced
                duration = self.phases['aerial_descent']['min_seconds']
                self.frame('aerial_descent', duration)
                endpoint = pygame.image.tobytes(self.render(), 'RGB')
                self.assertEqual(self.scene.fade_alpha, 0)
                self.frame('gate_approach', 0.)
                self.assertEqual(self.scene.fade_alpha, 0)
                ground = self.render()
                self.assertEqual(endpoint, pygame.image.tobytes(ground, 'RGB'))
                self.frame('aerial_descent', duration-.05)
                near = pygame.surfarray.array3d(self.render()).astype('int16')
                target = pygame.surfarray.array3d(ground).astype('int16')
                self.assertLess(float(abs(near-target).mean()), 5.)

    def test_canopy_hides_the_only_ground_swap_under_actual_full_coverage(self):
        self.scene._load()
        start = self.offsets['aerial_descent']
        steps = round((self.duration-start)*40)
        samples = [(start+index/40, self.sample(start+index/40))
                   for index in range(steps+1)]
        flags = [snapshot['ground_handoff'] for _, snapshot in samples]
        self.assertFalse(flags[0])
        self.assertTrue(flags[-1])
        self.assertEqual(flags, sorted(flags))
        switches = [index for index in range(1, len(flags)) if flags[index] != flags[index-1]]
        self.assertEqual(len(switches), 1)
        handoff_time, handoff = samples[switches[0]]
        # The descent now gives the approaching party several readable seconds
        # before entering foliage, rather than covering the view almost at once.
        self.assertGreaterEqual(handoff_time-start, 4.)
        self.assertEqual(handoff['canopy']['coverage'], 1.)
        self.assertTrue(handoff['canopy']['full_occlusion'])

        def render_reference(seconds, color):
            called = []

            def draw_ground(target, *_args, **_kwargs):
                called.append(True)
                target.fill(color)

            canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
            self.scene.aerial.draw(canvas, seconds, draw_ground, reduced_motion=False)
            return pygame.surfarray.array3d(canvas), called

        # Both radically different ground scenes are actually rendered, but
        # the real opaque leaf pixels must hide every differing background pixel.
        pink, pink_called = render_reference(handoff_time, '#ff00ff')
        green, green_called = render_reference(handoff_time, '#00ff00')
        self.assertTrue(pink_called)
        self.assertTrue(green_called)
        self.assertTrue((pink == green).all())

        before_pink, _ = render_reference(start+.1, '#ff00ff')
        before_green, _ = render_reference(start+.1, '#00ff00')
        self.assertTrue((before_pink == before_green).all())
        after = self.duration-.1
        self.assertEqual(self.sample(after)['canopy']['coverage'], 0.)
        after_pink, _ = render_reference(after, '#ff00ff')
        after_green, _ = render_reference(after, '#00ff00')
        # Negative control: the references become visible after the canopy
        # clears, so invariance at the swap cannot come from an unused callback.
        changed = (after_pink != after_green).any(axis=2)
        self.assertGreater(float(changed.mean()), .5)

    def test_aerial_pause_and_focus_freeze_camera_then_skip_preserves_handoff(self):
        self.reach('aerial_bank')
        self.g.update(.3, (0, 0), False)
        before = (self.scene.phase_time, self.scene.elapsed,
                  copy.deepcopy(self.scene.aerial_snapshot()), self.world_signature())
        key(self.g, pygame.K_ESCAPE)
        self.g.update(3., (1, 1), True)
        self.assertEqual((self.scene.phase_time, self.scene.elapsed,
                          self.scene.aerial_snapshot(), self.world_signature()), before)
        key(self.g, pygame.K_ESCAPE)
        self.g.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        self.g.update(3., (1, 1), True)
        self.assertEqual((self.scene.phase_time, self.scene.elapsed,
                          self.scene.aerial_snapshot(), self.world_signature()), before)
        self.g.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.g.update(.1, (0, 0), False)
        self.assertGreater(self.scene.phase_time, before[0])
        inventory = self.g.inventory.to_dict()
        position = tuple(self.g.player.position)
        click(self.g, self.scene.skip_rect.center)
        self.assertFalse(self.scene.active)
        self.assertEqual(self.scene.state, 'seen')
        self.assertEqual(self.g.inventory.to_dict(), inventory)
        self.assertEqual(tuple(self.g.player.position), position)
        self.assertEqual(self.g.quests.status(REGENT_QUEST), 'available')
        self.assertEqual(self.g.saved_journey['regent_arrival'], {'version': 1, 'state': 'seen'})

    def test_reduced_motion_removes_follow_sway_and_camera_roll(self):
        for shot in AERIAL_SHOTS:
            with self.subTest(shot=shot):
                first = self.sample(self.at(shot, .25), reduced=True)
                last = self.sample(self.at(shot, .75), reduced=True)
                self.assertEqual(first['camera'], last['camera'])
                self.assertEqual(first['camera']['roll'], 0.)
                self.assertTrue(all(abs(value) < 100000 for value in first['bird']['screen_xy']))

    def test_gallery_replays_new_aerial_without_touching_the_journey(self):
        title = self.make_game(self.directory/'journey.json', title=True)
        self.other_games.append(title)
        saved = (self.directory/'journey.json').read_bytes()
        self.assertTrue(title.open_gallery())
        self.assertTrue(title.launch_gallery_scene('regent_arrival'))
        session = title.gallery_session
        child = session.game
        for _ in range(200):
            if child.regent_arrival.shot == 'aerial_region':
                break
            title.update(.05, (0, 0), False)
        self.assertEqual(child.regent_arrival.shot, 'aerial_region')
        title.draw()
        key(title, pygame.K_p)
        time = child.regent_arrival.phase_time
        title.update(3., (0, 0), False)
        self.assertEqual(child.regent_arrival.phase_time, time)
        key(title, pygame.K_p)
        title.update(.1, (0, 0), False)
        self.assertGreater(child.regent_arrival.phase_time, time)
        child.regent_arrival.finish('skipped')
        title.update(.8, (0, 0), False)
        self.assertIsNone(title.gallery_session)
        self.assertTrue(title.on_gallery)
        self.assertEqual((self.directory/'journey.json').read_bytes(), saved)


if __name__ == '__main__':
    unittest.main()
