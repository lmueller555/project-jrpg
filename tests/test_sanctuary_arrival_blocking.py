"""The authored arrival has clear feet, finite errands and a visible column."""
from itertools import combinations
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from main import Game, World
from sanctuary_arrival_blocking import SanctuaryBlocking, PRINCIPALS, feet

ROOT = Path(__file__).resolve().parents[1]


class SanctuaryBlockingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.display.set_mode((1, 1))
        cls.world = World(ROOT/'assets/maps/elden_vale_sanctuary/map.json')
        cls.manifest = json.loads((ROOT/'assets/story/sanctuary_arrival/scene.json').read_text())
        # Runtime posts and closed rope supplement the older static rock mask.
        cls.world.task_blockers = lambda: (pygame.Rect(976,388,6,4),
                                          pygame.Rect(1034,388,6,4),
                                          pygame.Rect(982,388,52,4))

    @classmethod
    def tearDownClass(cls):
        pygame.display.quit()

    def cast(self, beat=0):
        positions = dict(self.manifest['starts'])
        for phase in self.manifest['beats'][:beat]:positions.update(phase['goals'])
        return {key:SimpleNamespace(position=pygame.Vector2(position),probe_size=(24,12),
                                   moving=False,facing='front',walk_ms=0.,route=[])
                for key, position in positions.items()}

    def clear_feet(self, actors):
        for (key, first), (other, second) in combinations(actors.items(), 2):
            self.assertFalse(feet(first).colliderect(feet(second)), (key, other, first.position, second.position))
        for key, actor in actors.items():self.assertTrue(self.world.can_stand(actor.position,actor.probe_size),key)

    def advance(self, director, actors, dt):
        for _ in range(round(30/dt)):
            director.update(dt)
            self.clear_feet(actors)
            focus = director.initial_camera()
            if focus is not None:
                left = max(0,min(self.world.size[0]-480,round(focus[0]-240)))
                top = max(0,min(self.world.size[1]-320,round(focus[1]-112)))
                viewport = pygame.Rect(left,top,480,320)
                for key in PRINCIPALS:
                    x,y=actors[key].position
                    # Native heads and foot contacts both remain in the shot.
                    self.assertTrue(viewport.contains(pygame.Rect(round(x)-12,round(y)-30,24,36)),key)
            if not any(director.busy(key) for key in actors):return
        self.fail('Authored Sanctuary tracks did not finish')

    def test_all_beats_keep_clear_stations_and_paths_at_multiple_frame_rates(self):
        for dt in (1/5,1/15,1/30,1/60):
            with self.subTest(dt=dt):
                actors=self.cast();director=SanctuaryBlocking(self.world,actors,self.manifest)
                for beat, phase in enumerate(self.manifest['beats']):
                    director.begin(beat)
                    self.advance(director,actors,dt)
                    for key, point in phase['goals'].items():
                        goal=phase.get('keeper',{}).get('contact',point) if key=='caretaker' else point
                        self.assertLess(actors[key].position.distance_to(goal),.001,(beat,key))
                    if beat==7:
                        director.move_actor('caretaker',phase['keeper']['retreat'])
                        self.advance(director,actors,dt)
                self.assertEqual(tuple(actors['caelan'].position),(1008,406))
                self.assertEqual(tuple(actors['caretaker'].position),(1052,426))

    def test_resume_reconstructs_each_beat_without_reintroducing_crossings(self):
        for beat in range(8):
            with self.subTest(beat=beat):
                actors=self.cast(beat);director=SanctuaryBlocking(self.world,actors,self.manifest)
                director.begin(beat)
                self.advance(director,actors,.1)

    def test_every_principal_station_is_visible_above_foreground_furniture(self):
        # Use the actual CastActor artwork/anchors, including ledger and Mira's
        # wide working pose. Clear feet alone can still leave a body behind a
        # bench, memorial stele or tall flowers.
        game=Game(fullscreen=False,start_on_title=False,
                  _preview_window=pygame.Surface((480,320)))
        self.addCleanup(game.music.stop)
        self.addCleanup(game.regional_audio.reset)
        owner=game.sanctuary_arrival
        owner.prepare_preview();self.assertTrue(owner.start(force=True))
        self.addCleanup(owner.reset)
        for beat,phase in enumerate(owner.manifest['beats']):
            with self.subTest(beat=beat):
                owner.phase_index=beat
                for key,point in phase['goals'].items():owner.actors[key].position.update(point)
                for key,actor in owner.actors.items():
                    actor.route=[];actor.moving=False
                    actor.pose=phase['poses'].get(key);actor.pose_ms=10000
                owner._settled_facings()
                for key in PRINCIPALS:
                    actor=owner.actors[key];image=actor.sprite(0)
                    body=pygame.mask.from_surface(image)
                    anchor=actor.draw_anchor
                    origin=(round(actor.position.x)-anchor[0],round(actor.position.y)-anchor[1])
                    bounds=image.get_rect(topleft=origin)
                    for entity in game.world.entities:
                        if (entity['sort_y']<=actor.position.y+6
                                or not entity['rect'].colliderect(bounds)):continue
                        mask=pygame.mask.from_surface(entity['surfaces'][0])
                        offset=(origin[0]-entity['rect'].x,origin[1]-entity['rect'].y)
                        self.assertEqual(mask.overlap_area(body,offset),0,(beat,key,entity['id']))

    def test_runner_completes_one_delivery_and_long_dialogue_holds_still(self):
        actors=self.cast();director=SanctuaryBlocking(self.world,actors,self.manifest)
        director.begin(0);self.advance(director,actors,.1)
        before={key:(tuple(actor.position),actor.walk_ms) for key,actor in actors.items()}
        for _ in range(300):director.update(.1)
        self.assertEqual(tuple(actors['runner'].position),(800,350))
        self.assertEqual({key:(tuple(actor.position),actor.walk_ms) for key,actor in actors.items()},before)
        self.assertTrue(all(not actor.moving for actor in actors.values()))


if __name__ == '__main__':unittest.main()
