"""The ridge landmark is reachable scenery, with no premature scene transition."""
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from main import Game
from overworld_travel import TOWN_EXIT, TOWN_RETURN, WORLD_ID

LANDMARK = 'ridge_sanctuary'
ROAD = 'sanctuary_approach'


from tools.capture_overworld_sanctuary import regional_path, walk


class OverworldSanctuaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'journey.json'
        self.g = self.game()
        self.g.player.position.update(TOWN_EXIT)
        self.g.update(.01, (0,0), False)
        self.assertEqual(self.g.world.data['id'], WORLD_ID)
        self.g.update(.4, (0,0), False)
        self.world = self.g.world

    def tearDown(self):pygame.quit()

    def game(self, title=False):
        game = Game(fullscreen=False, start_on_title=title,
                    save_path=self.path, settings_path=self.path.with_name('settings.json'))
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        return game

    @property
    def landmark(self):return next(p for p in self.world.region['landmarks'] if p['id'] == LANDMARK)
    @property
    def road(self):return next(r for r in self.world.region['roads'] if r['id'] == ROAD)

    def test_location_matches_the_northeastern_wooded_foothills(self):
        site = self.landmark
        self.assertEqual(site['tile_position'], [90,-66])
        self.assertEqual(site['kind'], 'sanctuary')
        self.assertTrue(site['always_known'])
        self.assertEqual(self.world.region['bounds_tiles'], [-256,-192,512,384])
        town = self.world.region['town']['tile_position']
        self.assertGreater(site['tile_position'][0], town[0])
        self.assertLess(site['tile_position'][1], town[1])
        walls = {w['id']:w for w in self.world.region['walls']}
        self.assertGreater(site['tile_position'][1], walls['north_wall']['y'])
        self.assertLess(site['tile_position'][1], walls['south_wall']['y'])
        self.assertTrue(any(s['id']=='ridge_sanctuary_reserve' for s in self.world.region['setpieces']))
        self.assertEqual(site['prop'], LANDMARK)
        position = self.world._tile_point(site['tile_position'])
        viewport = pygame.Rect(0,0,480,320);viewport.center = position
        miniature = [p for p in self.world._static_props(viewport) if p['key']==LANDMARK]
        self.assertEqual(len(miniature), 1)
        self.assertFalse(miniature[0].get('solid'))
        self.assertEqual(tuple(miniature[0]['position']), tuple(position))
        image, anchor = self.world._prop_image(LANDMARK)
        self.assertIsNotNone(image)
        self.assertTrue(image.get_rect().collidepoint(anchor))
        self.assertNotIn('destination', site)

    def test_normal_walking_connects_town_exit_to_the_complete_new_path(self):
        branch = self.world._tile_point(self.road['points'][0])
        walk(self.g, regional_path(self.world, self.g.player.position, branch))
        walk(self.g, [self.world._tile_point(p) for p in self.road['points']])
        target = self.world._tile_point(self.landmark['tile_position'])
        self.assertLess(self.g.player.position.distance_to(target), 1.)
        self.assertEqual(self.g.world.data['id'], WORLD_ID)
        self.assertTrue(self.world.can_stand(target))

    def test_walking_over_the_miniature_is_inert_in_both_directions(self):
        baseline = (self.g.quests.to_dict(), self.g.inventory.to_dict(), set(self.g.social.flags),
                    self.g.music.desired_track, set(self.g.scenes))
        for start, end in (((87,-66),(93,-66)), ((93,-66),(87,-66)),
                           ((90,-69),(90,-61)), ((90,-61),(90,-69))):
            self.g.player.position.update(self.world._tile_point(start))
            self.assertTrue(self.world.can_stand(self.g.player.position), start)
            walk(self.g, [self.world._tile_point(end)])
            self.assertFalse(self.g.social.active)
            self.assertFalse(self.g.combat.active)
            self.assertFalse(self.g.map_open)
            self.assertFalse(self.g.pause.is_open)
            self.assertEqual((self.g.quests.to_dict(), self.g.inventory.to_dict(), set(self.g.social.flags),
                              self.g.music.desired_track, set(self.g.scenes)), baseline)

    def test_known_map_location_does_not_require_a_new_save_field(self):
        self.g.overworld_travel.discovered = {'eldenmere'}
        self.assertTrue(self.g.save_progress())
        data = json.loads(self.path.read_text())
        data['overworld']['discovered'] = ['eldenmere']
        self.path.write_text(json.dumps(data))
        restored = self.game(True)
        self.assertTrue(restored.has_saved_journey)
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(restored.world.data['id'], WORLD_ID)
        ui = restored.map_ui._regional();ui._collect_landmarks()
        self.assertIn(LANDMARK, {p['id'] for p in ui.landmarks})
        self.assertIn(LANDMARK, {p['id'] for p in restored.minimap._places()})
        self.assertEqual(restored.saved_journey['overworld']['version'], 1)

    def test_starting_boundaries_remain_closed(self):
        for gate in self.world.gates:self.assertFalse(self.world.can_stand(gate['position']))
        self.assertFalse(self.world.can_stand(self.world._tile_point(self.world.region['bridge']['tile_position'])))
        for river in self.world.region['terrain']['rivers']:
            self.assertFalse(self.world.can_stand(self.world._tile_point(river['points'][6])))
        self.assertNotIn('CH01_OPENING_REGION_RELEASED', self.g.social.flags)
        self.assertNotIn('ELDEN_VALE_WEST_BRIDGE_REPAIRED', self.g.social.flags)

    def test_eldenmere_still_has_its_original_automatic_return(self):
        rect = self.world.town_entry_rect
        self.g.player.position.update(rect.right+36, rect.centery)
        for _ in range(80):
            self.g.update(.05, (-1,0), False)
            if self.g.world is self.g.town:break
        self.assertIs(self.g.world, self.g.town)
        self.assertEqual(tuple(self.g.player.position), TOWN_RETURN)
        self.assertEqual(self.g.player.facing, 'back')


if __name__ == '__main__':unittest.main()
