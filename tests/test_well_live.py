"""Gameplay lifecycle and ownership checks for the activated well replacement.

These use Game.update and the production world. The source-pack tests separately
protect authored pixels; no test here treats completion as visual approval.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pygame

from well_live_test_support import LiveWellCase
from rendering import WorldCanvas


class LiveWellIntegration(LiveWellCase):
    def test_source_selector_is_idempotent_and_preserves_physics(self):
        from tools.build_eldenmere_hd import ROOT, integrate_live_well
        recipe = json.loads((ROOT/'assets/source/maps/eldenmere/town_hd/recipe.json').read_text())
        town = deepcopy(self.world.data)
        unchanged = {key: deepcopy(town.get(key)) for key in
                     ('collision', 'navigation_allowed', 'doors', 'destinations', 'player_probe_size')}
        integrate_live_well(town, recipe)
        first = deepcopy(town)
        integrate_live_well(town, recipe)
        self.assertEqual(town, first)
        self.assertEqual(town['well_runtime'], recipe['well_runtime'])
        for key, value in unchanged.items():
            self.assertEqual(town.get(key), value, key)
        bad = deepcopy(recipe)
        bad['well_runtime']['world_origin_logical'][0] += 1
        with self.assertRaises(ValueError):
            integrate_live_well(deepcopy(town), bad)

    def test_native_depth_passes_recombine_and_caller_cannot_poison_cache(self):
        self.to_phase('lower')
        layers = self.well.draw_layers(self.game.elapsed_ms)
        self.assertEqual(len(layers), 2)
        combined = WorldCanvas((72, 88), pygame.SRCALPHA)
        for depth, image, position in layers:
            self.assertEqual(tuple(position), (492, 800))
            self.assertEqual(image.native.get_size(), (144, 176))
            combined.blit(image, (0, 0))
        expected = pygame.image.tobytes(self.well.sprite(self.game.elapsed_ms).native, 'RGBA')
        self.assertEqual(pygame.image.tobytes(combined.native, 'RGBA'), expected)
        layers[0][1].fill('#ff00ff')
        self.assertEqual(pygame.image.tobytes(self.well.sprite(self.game.elapsed_ms).native, 'RGBA'), expected)
        info = self.well.cache_info()
        self.assertLessEqual(info['entries'], info['limit'])
        self.assertLessEqual(info['surface_bytes'], info['max_surface_bytes'])

    def test_full_trip_keeps_one_pail_and_waters_each_bed_once(self):
        self.start_trip()
        phases, places, sampled = set(), set(), {'lower': set(), 'raise': set()}
        for _ in range(120*60):
            self.game.update(1/60, (0, 0), False)
            state = self.well.snapshot()
            selection = self.actor.presentation_selection()
            phases.add(state.phase_id)
            places.add(self.actor.pail_location)
            self.assertIn(self.actor.pail_location, ('actor', 'well', 'rest'))
            self.assertEqual(selection['water_units'], self.actor.water_units)
            self.assertEqual(bool(selection['pail_visible']),
                             self.actor.pail_location == 'actor')
            if self.actor.pail_location == 'well':
                self.assertEqual(state.pail_owner, 'well')
                self.assertTrue(self.well.bucket_on_rope)
            if state.phase_id in sampled:
                sampled[state.phase_id].add(state.crank_sample)
            if self.actor.completed_cycles:
                break
        self.assertEqual(self.actor.completed_cycles, 1)
        self.assertTrue({'attach', 'engage', 'guide_into_shaft', 'lower', 'fill',
                         'raise', 'secure', 'detach'} <= phases)
        self.assertEqual(sampled, {'lower': set(range(16)), 'raise': set(range(16))})
        self.assertEqual(places, {'actor', 'well', 'rest'})
        self.assertEqual(self.actor.watered_beds,
                         [bed['id'] for bed in self.actor.behavior['beds']])
        watered = [event for event in self.actor.events if event['type'] == 'watered']
        self.assertEqual([event['units'] for event in watered], [5, 4, 3, 2, 1, 0])
        self.assertEqual(self.actor.water_units, 0)
        self.assertEqual(self.actor.pail_location, 'rest')
        self.assertIsNone(self.well.owner)
        cues = list(self.actor.well_events)
        self.assertEqual([event.cue_id for event in cues],
                         ['attached', 'water_contact', 'mouth_submerged',
                          'fill_complete', 'water_exit', 'detached', 'completed'])
        self.assertEqual(len({event.event_id for event in cues}), len(cues))

    def test_pause_and_focus_loss_freeze_actor_and_model_together(self):
        self.to_phase('lower')
        self.game.update(.3, (0, 0), False)
        before = self.signature()
        self.game.pause.is_open = True
        self.game.update(3, (0, 0), False)
        self.assertEqual(self.signature(), before)
        self.game.pause.close()
        self.game._music_focused = False
        self.game.update(3, (0, 0), False)
        self.assertEqual(self.signature(), before)
        self.game._music_focused = True
        self.game.update(1/60, (0, 0), False)
        self.assertNotEqual(self.well.snapshot().phase_elapsed_ms,
                            before[0]['phase_elapsed_ms'])
        for owner, flag in ((self.game, 'map_open'), (self.game.quest_ui, 'journal_open')):
            before = self.signature()
            setattr(owner, flag, True)
            self.game.update(3, (0, 0), False)
            self.assertEqual(self.signature(), before)
            setattr(owner, flag, False)
        door = next(door for door in self.world.doors if door.data['id'] == 'home_a')
        self.assertTrue(self.game.enter(door))
        before = self.signature()
        self.game._music_focused = False
        self.game.update(3, (0, 0), False)
        self.assertEqual(self.signature(), before)

    def test_gameplay_launch_and_well_draw_do_not_require_optional_pillow(self):
        script = '''
import builtins
original = builtins.__import__
def import_without_pillow(name, *args, **kwargs):
    if name.split('.')[0] == 'PIL':
        raise ModuleNotFoundError('Pillow deliberately unavailable')
    return original(name, *args, **kwargs)
builtins.__import__ = import_without_pillow
from main import Game
game = Game(fullscreen=False, start_on_title=False)
assert game.town.well.sprite(0).native.get_size() == (144, 176)
game.town.draw(game.canvas, (408, 768), game.player, 0, include_ui=False)
game.music.stop()
'''
        result = subprocess.run([sys.executable, '-c', script],
                                cwd=Path(__file__).resolve().parents[1],
                                text=True, capture_output=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_repeated_render_is_read_only_and_uses_warm_caches(self):
        self.to_phase('fill')
        self.native()
        self.actor.sprite(self.game.elapsed_ms)
        before = self.signature()
        with patch.object(pygame.image, 'load', side_effect=AssertionError('draw reopened artwork')):
            for _ in range(8):
                self.native()
                self.actor.sprite(self.game.elapsed_ms)
        self.assertEqual(self.signature(), before)

    def test_room_visit_preserves_same_actor_and_operation(self):
        self.to_phase('lower')
        self.game.update(.25, (0, 0), False)
        before = self.well.snapshot()
        door = next(door for door in self.world.doors if door.data['id'] == 'home_a')
        self.assertTrue(self.game.enter(door))
        self.game.update(.25, (0, 0), False)
        after = self.well.snapshot()
        self.assertEqual(after.operation_id, before.operation_id)
        self.assertEqual(after.phase_id, 'lower')
        self.assertGreater(after.phase_elapsed_ms, before.phase_elapsed_ms)
        self.assertIs(self.well.owner, self.actor)
        self.assertEqual(self.actor.pail_location, 'well')
        self.assertTrue(self.game.enter(self.game.world.doors[0]))
        self.assertIs(self.game.world, self.world)
        self.assertEqual(sum(actor is self.actor for actor in self.world.npcs), 1)

    def test_new_game_resets_actor_and_well_as_one_ambient_checkpoint(self):
        self.to_phase('fill')
        old_token = self.actor.operation_token
        self.assertTrue(self.game.begin_journey(False, show_cinematic=False))
        self.assertEqual(self.actor.state, 'rest')
        self.assertEqual(self.actor.pail_location, 'rest')
        self.assertEqual(self.actor.water_units, 0)
        self.assertIsNone(self.well.owner)
        self.assertEqual(self.well.snapshot().phase_id, 'idle')
        self.assertFalse(self.well.mechanism.signal_ready(old_token, 'loading'))

    def test_continue_reconstructs_rest_without_saving_transient_mechanism(self):
        self.to_phase('raise')
        payload = self.game.journey_snapshot()
        self.assertNotIn('well_mechanism', payload)
        self.assertNotIn('gardener', payload)
        self.game.saved_journey = deepcopy(payload)
        self.assertTrue(self.game.begin_journey(True))
        self.assertEqual(self.actor.state, 'rest')
        self.assertEqual(self.actor.pail_location, 'rest')
        self.assertEqual(self.well.snapshot().phase_id, 'idle')
        self.assertIsNone(self.well.owner)

    def test_reduced_motion_keeps_functional_operation_and_native_density(self):
        self.world.reduced_motion = True
        self.to_phase('lower')
        before = self.well.snapshot()
        image = self.well.sprite(self.game.elapsed_ms)
        self.assertEqual(image.get_size(), (72, 88))
        self.assertEqual(image.native.get_size(), (144, 176))
        self.assertEqual(self.actor.sprite(0).native.get_size(), (96, 96))
        self.game.update(.5, (0, 0), False)
        self.assertGreater(self.well.snapshot().phase_elapsed_ms, before.phase_elapsed_ms)
        self.assertNotEqual(self.well.snapshot().bucket_grip_local, before.bucket_grip_local)


if __name__ == '__main__':
    import unittest
    unittest.main()
