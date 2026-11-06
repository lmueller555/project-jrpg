"""Cup contact, room geometry and transient ownership for MQ02's homecoming."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

import main
from npc_routines import find_path
from sanctuary_return import SOURCE, SOURCE_CUP, TABLE


class SanctuaryReturnTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.game = main.Game(fullscreen=False, start_on_title=True,
            save_path=Path(self.temp.name)/'journey.json',
            settings_path=Path(self.temp.name)/'settings.json')
        self.scene = self.game.mill_quest.sanctuary_return
        self.game.world = self.scene.dining
        self.game.player.position.update(264, 128)
        self.game.audio.set_music(0);self.game.audio.set_effects(0)

    def tearDown(self):pygame.quit()

    def finish_action(self):
        for _ in range(1200):
            if not self.scene.action_active:return
            self.scene.update(.05)
            self.assertTrue(self.scene.dining.can_stand(self.game.player.position))
        self.fail(('Unfinished cup action', self.scene.action, tuple(self.game.player.position)))

    def test_family_staging_uses_existing_actors_and_walkable_stations(self):
        originals = (self.scene.serene, self.scene.tomas)
        self.assertFalse(self.scene.ready)
        self.assertFalse(self.scene.start_cups())
        self.assertTrue(self.scene.prepare())
        self.assertTrue(self.scene.prepare())
        for actor in originals:
            self.assertEqual(sum(actor is a for w in self.game.scenes.values() for a in w.npcs), 1)
            self.assertIs(self.game._routine_worlds[actor], self.scene.dining)
            self.assertTrue(actor.story_paused)
        self.assertTrue(self.scene.dining.can_stand(SOURCE))
        self.assertTrue(self.scene.dining.can_stand(TABLE))
        self.assertIsNotNone(find_path(self.scene.dining, SOURCE, TABLE,
                                      self.scene.dining.probe_size, None))
        self.assertFalse(any(a.story_visible for a in self.game.regent_quest.party))

    def test_collection_and_actual_placement_are_separate_once_only_boundaries(self):
        self.scene.prepare();held = Mock();placed = Mock()
        self.assertTrue(self.scene.start_cups(held))
        self.assertTrue(self.scene.locks_player)
        self.assertFalse(self.scene.place_cups(placed))
        visited = set()
        for _ in range(1200):
            visited.add(self.scene.action)
            if not self.scene.action_active:break
            self.scene.update(.05)
        self.assertTrue({'collect', 'pickup', 'carry', 'hold'} <= visited)
        held.assert_called_once_with()
        self.assertTrue(self.scene.holding_cups)
        self.assertFalse(self.scene.placed)
        self.assertFalse(self.scene.locks_player)
        self.assertLess(self.game.player.position.distance_to(TABLE), .01)
        self.assertTrue(self.scene.place_cups(placed))
        self.scene.update(.05)
        self.scene.update(.3)
        placed.assert_not_called()
        self.assertTrue(self.scene.holding_cups)
        self.finish_action()
        placed.assert_called_once_with()
        self.assertTrue(self.scene.placed)
        self.assertFalse(self.scene.holding_cups)
        self.scene.update(10)
        placed.assert_called_once_with()
        self.assertFalse(self.scene.start_cups())

    def test_focus_and_menus_freeze_collection_without_catchup(self):
        self.scene.prepare();self.scene.start_cups()
        self.scene.update(.05)
        before = self.game.player.position.copy();clock = self.scene.action_time
        self.game._music_focused = False;self.scene.update(10)
        self.assertEqual(self.game.player.position, before)
        self.assertEqual(self.scene.action_time, clock)
        self.game._music_focused = True;self.game.map_open = True;self.scene.update(10)
        self.assertEqual(self.game.player.position, before)
        self.game.map_open = False;self.game.quest_ui.journal_open = True;self.scene.update(10)
        self.assertEqual(self.game.player.position, before)
        self.game.quest_ui.journal_open = False
        self.scene.update(.05)
        self.assertLess(self.game.player.position.distance_to(before), 3.)

    def test_interrupted_pickup_resets_without_committing_and_release_keeps_tableware(self):
        self.scene.prepare();callback = Mock();self.scene.start_cups(callback)
        self.scene.update(.1)
        self.scene.restore(reported=True, placed=False)
        callback.assert_not_called()
        self.assertFalse(self.scene.holding_cups)
        self.assertFalse(self.scene.action_active)
        self.assertTrue(all(self.scene.surface_prop_visible(p)
                            for p in self.scene.surface_props if p['kind'] == 'source'))
        self.scene.restore(reported=True, placed=True, complete=True)
        self.scene.release()
        self.assertTrue(all(self.scene.surface_prop_visible(p)
                            for p in self.scene.surface_props if p['kind'] == 'table'))
        sentinel = pygame.Surface((1, 1));self.scene.serene.story_sprite = sentinel
        self.scene.update(10);self.scene.release()
        self.assertIs(self.scene.serene.story_sprite, sentinel)
        self.scene.reset()
        self.assertFalse(any(self.scene.surface_prop_visible(p) for p in self.scene.surface_props))

    def test_authored_body_padding_and_cup_contact_share_the_room_baseline(self):
        self.scene.prepare();player = self.game.player
        for facing in ('front', 'back', 'left', 'right'):
            self.scene._pose(facing)
            padded_origin = player.position-pygame.Vector2(player.story_draw_anchor)+pygame.Vector2(8, 24)
            normal_origin = player.position-pygame.Vector2(self.scene.dining.data['player_draw_anchor'])
            self.assertEqual(padded_origin, normal_origin)
            wrist_pixel = (11, 48) if facing == 'left' else (28, 48)
            wrist = player.position+pygame.Vector2(wrist_pixel)-pygame.Vector2(player.story_draw_anchor)
            self.assertEqual(self.scene._cup_origin()+pygame.Vector2(3, 5), wrist)
            if facing == 'left':self.assertLess(wrist.x, player.position.x)
            if facing == 'right':self.assertGreater(wrist.x, player.position.x)
        # Walking is always the existing approved drawing, without body warps.
        self.scene._clear_player_pose();self.game.player.position.update(SOURCE)
        self.assertTrue(self.scene._move(TABLE, .05) is False)
        frames = [image for image, _ in player.walks[player.facing]]
        self.assertTrue(any(player.story_sprite is image for image in frames))
        self.assertEqual(player.story_draw_anchor, tuple(self.scene.dining.data['player_draw_anchor']))
        # The collection's last authored reach touches the same cup location
        # shown on the sideboard, so contact never jumps between two assets.
        player.position.update(SOURCE);self.scene._reach(2)
        self.assertEqual(tuple(self.scene._cup_origin()), SOURCE_CUP)


if __name__ == '__main__':unittest.main()
