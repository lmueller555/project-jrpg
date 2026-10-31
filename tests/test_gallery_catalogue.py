"""Every advertised replay reaches its production boundary in a fresh Game."""
import gc
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from main import Game
from cutscene_gallery import GALLERY_ENTRIES, GALLERY_BY_ID, GalleryPlayback


class GalleryCatalogueTests(unittest.TestCase):
    def tearDown(self):
        pygame.quit()
        gc.collect()

    def preview(self):
        game = Game(fullscreen=False, start_on_title=False)
        game._is_gallery_preview = True
        pygame.event.clear()
        return game

    def test_catalogue_metadata_is_unique_readable_and_repo_local(self):
        self.assertEqual(len(GALLERY_ENTRIES), len(GALLERY_BY_ID))
        for entry in GALLERY_ENTRIES:
            with self.subTest(scene=entry.id):
                self.assertRegex(entry.id, r'^[a-z][a-z0-9_]+$')
                self.assertTrue(entry.name.strip())
                self.assertTrue(entry.description.strip())
                self.assertTrue(entry.controls.strip())
                self.assertEqual(Path(entry.thumbnail).parent.as_posix(), 'assets/ui/gallery')
                self.assertEqual(Path(entry.thumbnail).name, entry.id+'.png')
        # Coverage must extend beyond both standalone framing cinematics.
        for chapter in ('Prologue', 'A Day Like Any Other', 'Mira’s Mill Quest',
                        'The Regent’s Road', 'Liam’s First Lantern', 'Elden Vale'):
            self.assertTrue(any(entry.chapter == chapter for entry in GALLERY_ENTRIES), chapter)

    def test_registry_cannot_fixture_a_normal_or_persistent_game(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'journey.json'
            sentinel = b'{"untouched":"legacy journey"}\n'
            path.write_bytes(sentinel)
            game = Game(fullscreen=False, save_path=path)
            for preview_flag in (False, True):
                game._is_gallery_preview = preview_flag
                with self.assertRaises(ValueError):GALLERY_ENTRIES[0].start(game)
                self.assertEqual(path.read_bytes(), sentinel)
            game.save_store.path = None
            game._is_gallery_preview = False
            with self.assertRaises(ValueError):GALLERY_ENTRIES[0].start(game)

    def test_completion_hold_does_not_drive_another_story_cue(self):
        playback = GalleryPlayback(None)
        calls = []
        playback.watch(lambda: True, lambda: calls.append('extra interaction'))
        playback.update(.1)
        self.assertTrue(playback.settling)
        self.assertFalse(playback.finished)
        playback.update(.6)
        self.assertTrue(playback.finished)
        self.assertEqual(calls, [])

    def test_native_cinematic_skip_completes_the_selected_preview_only(self):
        for identifier in ('later_journey', 'regent_arrival'):
            with self.subTest(scene=identifier):
                game = self.preview()
                playback = GALLERY_BY_ID[identifier].start(game)
                if identifier == 'later_journey':game.opening_cinematic.skip()
                else:game.regent_arrival.finish('skipped')
                playback.update(.7)
                self.assertTrue(playback.finished)
                self.assertFalse(game.opening.active)
                self.assertFalse(game.combat.active)
                self.assertFalse(game.save_store.enabled)
                game.music.stop();pygame.quit()
                game = None;playback = None;gc.collect()

    def play_to_boundary(self, identifier, reduced_motion=False):
        game = self.preview()
        game.audio.reduced_motion = reduced_motion
        with patch.object(game.save_store, 'write', side_effect=AssertionError('Preview wrote a save')):
            playback = GALLERY_BY_ID[identifier].start(game)
            self.assertTrue(game.world.can_stand(game.player.position), identifier)
            scripts = set();actions = set()
            visit_steps = set();basket_states = set()
            if identifier == 'sheep_basket_visit':
                wildlife = game.world.wildlife
                wildlife_roster = tuple((id(actor), actor.id) for actor in wildlife.actors)
                garden_before = game.world.garden_orchard.to_dict()
                produce_before = game.world.garden_orchard.portable_positions()
                witness = tuple(game.player.position)
                self.assertEqual(wildlife.vignette['phase'], 'idle')
                self.assertFalse(wildlife.worker.wildlife_owned)
            # 300 seconds covers the full 252.57-second opening without skipping
            # shots. The pasture visit takes about 62 seconds; other fixtures
            # finish in under 40 seconds with brisk dialogue input.
            for _ in range(9000):
                if game.social.active:
                    scripts.add(game.social.script_identifier)
                    game.handle_events([pygame.event.Event(pygame.KEYDOWN,
                                                           key=pygame.K_SPACE, repeat=False)])
                if game.regent_arrival.active:
                    game.handle_events([pygame.event.Event(pygame.KEYDOWN,
                                                           key=pygame.K_SPACE, repeat=False)])
                for controller in (game.mill_quest, game.lantern_quest):
                    if controller.action:actions.add(controller.action)
                if not playback.settling:game.update(1/30, (0, 0), False)
                if identifier == 'sheep_basket_visit':
                    if wildlife.vignette['phase'] == 'visit':visit_steps.add(wildlife.vignette['step'])
                    basket_states.add(wildlife.vignette['basket'])
                playback.update(1/30)
                self.assertFalse(game.combat.active, identifier+' launched unintended combat')
                if playback.finished:break
            self.assertTrue(playback.finished, (identifier, game.lantern_quest.stage,
                            game.mill_quest.action, game.social.script_identifier))
            self.assertTrue(game.world.can_stand(game.player.position), identifier)
            self.assertFalse(game.save_store.enabled)
            self.assertFalse(game.social.active)
            # Authored casts remain single actors, even when borrowed by quests.
            worlds = list(game.scenes.values())
            if game._overworld_world is not None:worlds.append(game._overworld_world)
            actors = [actor for world in worlds for actor in world.npcs]
            self.assertEqual(len(actors), len({id(actor) for actor in actors}))
            if identifier == 'later_journey':
                self.assertEqual(game.opening_cinematic.finished_reason, 'completed')
                self.assertEqual(game.opening.stage, 'disabled')
            elif identifier == 'regent_arrival':
                self.assertEqual(game.regent_arrival.state, 'seen')
                self.assertEqual(game.regent_arrival.audio.channels, [])
            elif identifier == 'millrace_threat':
                self.assertIn('mill_encounter_intro', scripts)
                self.assertFalse(game.mill_quest.encounter_cutscene_active)
                self.assertTrue(game.mill_quest.encounter_pending)
                self.assertFalse(game.mill_quest.encounter_cleared)
            elif identifier == 'mill_small_spell':
                self.assertIn('spell', actions)
                self.assertIn('mill_encouragement', scripts)
                self.assertTrue(game.mill_quest.encouraged)
            elif identifier == 'halden_medicine':
                self.assertTrue(game.halden_visit.medicine)
                self.assertIn('halden_arrival', scripts)
            elif identifier == 'tomas_sack':
                self.assertIn(1, game.halden_visit.stored)
                self.assertIsNone(game.halden_visit.tomas_job)
            elif identifier == 'grain_extra_sack':
                self.assertTrue(game.world.grain_farm.state['scene_done'])
                self.assertIn('grain_farm_extra_sack', scripts)
            elif identifier == 'garden_quiet_care':
                controller = game.world.garden_orchard
                self.assertEqual(controller.state['gardener']['phase'], 'rest')
                self.assertTrue(controller.state['gardener']['read'])
                self.assertIn('garden_quiet_care', scripts)
                self.assertEqual(tuple(controller.portable_positions()['plant'][0]), (-546, 1141))
                self.assertEqual(tuple(controller.actors[0].position), (-552, 1164))
                self.assertTrue(game.world.can_stand(controller.actors[0].position,
                                                    controller.actors[0].probe_size,
                                                    controller.actors[0]))
                self.assertFalse(controller.actors[0].wildlife_owned)
            elif identifier == 'sheep_basket_visit':
                from purposeful_wildlife import HOMES, VISIT, WORKER_HOME, valid_state
                self.assertEqual(visit_steps, set(range(len(VISIT))))
                self.assertEqual(basket_states, {'home', 'hand', 'pen'})
                self.assertEqual(wildlife.vignette['phase'], 'done')
                self.assertEqual(wildlife.vignette['basket'], 'home')
                self.assertEqual(tuple(wildlife.worker.position), WORKER_HOME)
                self.assertFalse(wildlife.worker.wildlife_owned)
                self.assertTrue(valid_state(wildlife.to_dict()))
                self.assertEqual(tuple((id(actor), actor.id) for actor in wildlife.actors), wildlife_roster)
                self.assertEqual({actor.id for actor in wildlife.actors}, set(HOMES))
                self.assertEqual(len(wildlife.actors), 9)
                self.assertEqual(sum(actor is wildlife.worker for actor in game.world.npcs), 1)
                self.assertEqual(game.world.garden_orchard.to_dict(), garden_before)
                self.assertEqual(game.world.garden_orchard.portable_positions(), produce_before)
                self.assertEqual(tuple(game.player.position), witness)
                self.assertEqual(game.camera.framing_height, 320)
                self.assertGreater(playback.elapsed, 60)
                self.assertLess(playback.elapsed, 75)
            elif identifier == 'bridge_tea':
                self.assertEqual(game.world.bridge_crew.state['tea_beat'], 5)
                self.assertIn('bridge_crew_tea', scripts)
            elif identifier == 'lantern_frame':
                self.assertEqual(game.lantern_quest.stage, 'frame_ready')
                self.assertTrue({'assemble', 'lift'} <= actions)
            elif identifier == 'lantern_finishing':
                self.assertEqual(game.lantern_quest.stage, 'lantern_finished')
                self.assertTrue({'finish_prepare', 'finish_cover', 'finish_pickup'} <= actions)
            elif identifier == 'lantern_putaway':
                self.assertEqual(game.lantern_quest.stage, 'done')
                self.assertIn('finish_place', actions)
        return scripts, actions

    def test_reduced_motion_encounter_still_reads_warning_and_stops_before_battle(self):
        self.play_to_boundary('millrace_threat', reduced_motion=True)


# One discovered test per public entry makes missing/failed playback visible in
# the regression report instead of hiding the catalogue behind one count.
for _entry in GALLERY_ENTRIES:
    def _completion(self, identifier=_entry.id):self.play_to_boundary(identifier)
    _completion.__name__ = 'test_'+_entry.id+'_production_completion'
    setattr(GalleryCatalogueTests, _completion.__name__, _completion)


if __name__ == '__main__':unittest.main()
