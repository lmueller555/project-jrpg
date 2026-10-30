"""MQ04 village visits preserve people, objects and committed conversations."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import main
from tools.capture_lantern_village import seed_frame_checkpoint, MAIN_SCENES, FIRST_FOUR

LANTERN = 'CH01_MQ04'


class LanternVillageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'journey.json'
        self.g = self.game();self.c = self.g.lantern_quest
        seed_frame_checkpoint(self.g);self.g.save_progress()

    def tearDown(self):pygame.quit()

    def game(self, title=False):
        game = main.Game(fullscreen=False, start_on_title=title, save_path=self.path,
                         settings_path=Path(self.temp.name)/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0);pygame.event.clear()
        return game

    def tick(self, seconds=.05):self.g.update(seconds, (0, 0), False)

    def until(self, predicate, seconds=120):
        for _ in range(round(seconds/.05)):
            if predicate():return
            self.tick()
        self.fail(('Timed out', self.c.stage, self.g.social.script_identifier,
                   self.g.world.data['id'], tuple(self.g.player.position), self.c._ready,
                   [(a.data['id'], self.c._world(a).data['id'], tuple(a.position))
                    for a in (self.c.liam, self.c.tomas, self.c.mira)]))

    def position(self, key, scene='eldenmere.playable'):
        """Move only Caelan for focused checks; companions still use real paths."""
        world = self.g._scene_by_id(scene);self.g.world = world
        desired = self.c.points['workshop'] if key == 'departure' else self.c.village_points[key]
        for radius in (0, 8, 16, 24, 32):
            for offset in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                candidate = pygame.Vector2(desired)+offset
                if world.can_stand(candidate):
                    self.g.player.position.update(candidate)
                    self.g.transfer_cooldown = 0;self.g.camera.reset();return
        self.fail(('No clear station', key, scene, desired))

    def read(self):
        identifier = self.g.social.script_identifier
        for _ in range(300):
            if not self.g.social.active or self.g.social.script_identifier != identifier:return
            self.assertFalse(self.g.social.choosing)
            self.g.social.advance()
        self.fail(('Unfinished script', identifier))

    def scene(self, kind, finish=True):
        self.until(lambda: self.c._target() == kind)
        self.assertTrue(self.c.interact(), (kind, self.c.stage))
        self.assertEqual(self.g.social.script_identifier, 'lantern_'+kind)
        if finish:self.read()

    def depart(self):
        self.position('departure');self.scene('departure')
        self.assertEqual(self.c.stage, 'outing')

    def visit_mill(self):
        self.depart();self.position('mill')
        self.scene('mill_arrival');self.scene('mill_flour')
        self.assertEqual(self.c.stage, 'mill_visited')

    def visit_neighbours(self):
        self.visit_mill();self.position('venn', 'venn')
        self.scene('venn_arrival');self.scene('venn_preparations')
        self.assertEqual(self.c.stage, 'neighbours_visited')

    def greet_elira(self):
        self.visit_neighbours();self.position('elira', 'elira');self.scene('elira_welcome')
        self.assertEqual(self.c.stage, 'elira_welcomed')

    def farewell(self):
        self.greet_elira()
        for kind in ('elira_lantern', 'elira_memory', 'elira_company', 'elira_goodbye'):
            self.scene(kind)
        self.assertEqual(self.c.stage, 'elira_farewell')

    def finish_visits(self):
        self.farewell();self.position('reflection');self.scene('reflection')
        self.assertEqual(self.c.stage, 'elira_visited')

    def reload(self):
        self.g.save_progress();other = self.game(True)
        self.assertTrue(other.begin_journey(True), other.save_error)
        self.g = other;self.c = other.lantern_quest
        self.g.opening_fade = 0;self.g.transfer_cooldown = 0

    def frame_prop(self):return next(p for p in self.c.surface_props if p['id'] == 'craft_surface')

    def test_existing_pr1_checkpoint_continues_without_replaying_construction(self):
        self.reload()
        self.assertEqual(self.c.to_dict(), {'version': 1, 'stage': 'frame_ready'})
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_FOUR[:2])
        self.assertFalse(self.g.social.active)
        self.until(lambda: self.c._target() == 'departure')

    def test_unread_departure_cannot_release_the_outing(self):
        self.position('departure');self.scene('departure', False)
        self.g.social.advance();self.g.social.cancel();self.tick()
        self.assertEqual(self.c.stage, 'frame_ready')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_FOUR[:2])
        self.reload();self.assertEqual(self.c.stage, 'frame_ready')

    def test_departure_keeps_frame_and_drawing_at_miras_table(self):
        self.depart();self.position('mill');self.until(lambda: self.c._target() == 'mill_arrival')
        prop = self.frame_prop()
        self.assertTrue(self.c.surface_prop_visible(prop))
        self.assertIs(prop['surface'], prop['states']['ready'])
        drawing = next(p for p in self.c.surface_props if p['id'] == 'school_drawing')
        self.assertFalse(self.c.surface_prop_visible(drawing))
        self.assertFalse(hasattr(self.c.liam, 'story_sprite'))
        self.assertEqual(sum(p['id'] == 'craft_surface' for p in self.c.surface_props), 1)

    def test_mira_returns_to_her_original_bench_before_normal_work_resumes(self):
        self.depart()
        self.until(lambda: not self.c.mira.quest_mode)
        self.assertLess(self.c.mira.position.distance_to(self.g.mill_quest.bench_position), .3)
        self.assertEqual(sum(self.c.mira in world.npcs for world in self.g.scenes.values()), 1)
        before = self.c.mira.position.copy();self.tick(.5)
        self.assertEqual(self.c.mira.position, before)

    def test_out_of_order_household_visits_cannot_grant_future_scenes(self):
        self.depart()
        for key, scene, actor in (('venn', 'venn', self.c.venn_family['mother']),
                                   ('elira', 'elira', self.c.elira)):
            with self.subTest(scene=scene):
                self.position(key, scene);self.tick(.2)
                target = self.c._target()
                self.assertNotIn(target, ('venn_arrival', 'venn_preparations', 'elira_welcome',
                                          'elira_lantern', 'elira_memory', 'elira_company', 'elira_goodbye'))
                if self.c.try_conversation(actor):self.read()
                self.assertEqual(self.c.stage, 'outing')
                self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_FOUR[:2])

    def test_mill_greeting_does_not_skip_the_flour_conversation(self):
        self.depart();self.position('mill');self.scene('mill_arrival')
        self.assertEqual(self.c.stage, 'mill_met')
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'visit_neighbours'), 'active')
        self.scene('mill_flour', False);self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.c.stage, 'mill_met')
        self.reload();self.assertEqual(self.c.stage, 'mill_met')

    def test_neighbour_credit_requires_both_substantive_visits(self):
        self.visit_mill()
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_FOUR[:2])
        self.position('venn', 'venn');self.scene('venn_arrival')
        self.scene('venn_preparations', False);self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.c.stage, 'venn_met')
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'visit_neighbours'), 'active')
        self.scene('venn_preparations')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_FOUR[:3])

    def test_original_villagers_and_companions_are_reused(self):
        actors = (self.c.liam, self.c.tomas, self.c.halden, self.c.elira, *self.c.venn_family.values())
        original = {actor.data['id']: actor for actor in actors}
        self.finish_visits()
        for identifier, actor in original.items():
            with self.subTest(actor=identifier):
                found = [a for world in self.g.scenes.values() for a in world.npcs if a.data['id'] == identifier]
                self.assertEqual(found, [actor])

    def test_venn_child_stays_resting_and_earlier_repairs_remain_true(self):
        child = self.c.venn_family['child'];before = child.position.copy();pose = child.sprite(0)
        self.visit_neighbours()
        self.assertEqual(child.position, before)
        self.assertIs(child.sprite(0), pose)
        self.assertIn(child, self.c.venn_home.npcs)
        self.assertTrue(self.g.venn_visit.repaired)
        self.assertTrue(self.g.mill_quest.mill_restored)
        self.assertFalse(self.g.opening_conclusion.mill_stopped)
        self.assertEqual(self.g.regent_quest.stage, 'done')

    def test_elira_uses_the_same_already_retrieved_lantern(self):
        visit = self.g.elira_visit
        original = next(p for p in visit.surface_props if p['id'] == 'elira_lantern_table')
        self.finish_visits()
        self.assertEqual(visit.lantern, 'table')
        self.assertIs(next(p for p in visit.surface_props if p['id'] == 'elira_lantern_table'), original)
        self.assertTrue(visit.surface_prop_visible(original))
        self.assertIsNone(visit.action)
        self.assertEqual(self.g.quests.objective_status('CH01_MQ01', 'elira'), 'completed')
        self.assertFalse(any('lantern' in p['id'] for p in self.c.surface_props if p['scene'] == 'elira'))

    def test_cancelled_elira_conversations_preserve_each_committed_checkpoint(self):
        self.greet_elira()
        for kind, prior, after in (('elira_lantern', 'elira_welcomed', 'elira_remembering'),
                                   ('elira_memory', 'elira_remembering', 'elira_remembered'),
                                   ('elira_company', 'elira_remembered', 'elira_ready_to_leave'),
                                   ('elira_goodbye', 'elira_ready_to_leave', 'elira_farewell')):
            with self.subTest(scene=kind):
                self.scene(kind, False);self.g.social.advance();self.g.social.cancel()
                self.assertEqual(self.c.stage, prior)
                self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_FOUR[:3])
                self.scene(kind);self.assertEqual(self.c.stage, after)

    def test_final_credit_requires_leaving_eliras_home_and_reading_reflection(self):
        self.farewell()
        self.assertEqual(self.g.world.data['id'], 'elira')
        self.assertIsNone(self.c._target())
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'visit_elira'), 'active')
        self.position('reflection');self.scene('reflection', False)
        self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.c.stage, 'elira_farewell')
        self.scene('reflection')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_FOUR)

    def test_complete_section_remains_active_without_festival_or_next_unimplemented_task(self):
        self.finish_visits();self.reload()
        self.assertEqual(self.c.to_dict(), {'version': 1, 'stage': 'elira_visited'})
        self.assertEqual(self.g.quests.status(LANTERN), 'active')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_FOUR)
        self.assertNotIn('CH01_MQ05', self.g.quests.definitions)
        self.assertNotIn('CH01_MQ04_COMPLETE', self.g.social.flags)
        self.assertEqual(list(self.c.journal_objectives()), FIRST_FOUR)
        self.g.quest_ui.selected_quest = LANTERN
        self.assertFalse(any(text.startswith(('Next:', 'Later:')) for text, *_ in self.g.quest_ui._journal_rows()))
        for identifier in ('mira_worker', 'halden', 'venn_mother', 'venn_father', 'elira', 'tomas'):
            self.assertNotIn(self.c.marker_for(identifier), ('!', '?'))
        self.assertEqual(self.c.marker_for('liam'), '?')

    def test_reloading_each_visit_preserves_the_committed_story_not_the_page(self):
        steps = (('departure', 'departure', 'eldenmere.playable', 'outing'),
                 ('mill_arrival', 'mill', 'eldenmere.playable', 'mill_met'),
                 ('mill_flour', 'mill', 'eldenmere.playable', 'mill_visited'),
                 ('venn_arrival', 'venn', 'venn', 'venn_met'),
                 ('venn_preparations', 'venn', 'venn', 'neighbours_visited'),
                 ('elira_welcome', 'elira', 'elira', 'elira_welcomed'),
                 ('elira_lantern', 'elira', 'elira', 'elira_remembering'),
                 ('elira_memory', 'elira', 'elira', 'elira_remembered'),
                 ('elira_company', 'elira', 'elira', 'elira_ready_to_leave'),
                 ('elira_goodbye', 'elira', 'elira', 'elira_farewell'),
                 ('reflection', 'reflection', 'eldenmere.playable', 'elira_visited'))
        for kind, station, world, stage in steps:
            with self.subTest(scene=kind):
                self.position(station, world);self.scene(kind);self.reload()
                self.assertEqual(self.c.stage, stage)
                self.assertFalse(self.g.social.active)
                self.assertIs(self.frame_prop()['surface'], self.frame_prop()['states']['ready'])
                self.assertFalse(self.c.mira.quest_mode)
                self.assertLess(self.c.mira.position.distance_to(self.g.mill_quest.bench_position), .3)

    def test_invalid_stage_and_objective_combinations_are_rejected(self):
        self.visit_mill();self.g.save_progress();original = json.loads(self.path.read_text())
        for stage, prefix in (('elira_visited', 2), ('outing', 3), ('elira_remembered', 4),
                              ('invented_stage', 2)):
            with self.subTest(stage=stage, objectives=prefix):
                invalid = copy.deepcopy(original)
                invalid['lantern_quest']['stage'] = stage
                invalid['quests']['quests'][LANTERN]['completed_objectives'] = FIRST_FOUR[:prefix]
                self.assertFalse(type(self.c).valid_journey(invalid))
        self.path.write_text(json.dumps(original))
        self.assertTrue(type(self.c).valid_journey(original))

    def test_repeated_optional_conversations_do_not_repeat_visit_credit(self):
        self.finish_visits();progress = self.g.quests.to_dict()
        for actor in (self.c.liam, self.c.tomas):
            if self.c.try_conversation(actor):self.read()
        self.assertEqual(self.g.quests.to_dict(), progress)
        self.assertEqual(self.c.stage, 'elira_visited')

    def test_new_game_releases_outing_and_restores_the_school_households(self):
        self.finish_visits();self.assertTrue(self.g.begin_journey(False, show_cinematic=False))
        self.assertEqual(self.g.quests.status(LANTERN), 'locked')
        self.assertEqual(self.c.stage, 'idle')
        self.assertEqual(self.c.school.npcs, [])
        expected = {'liam': 'liam_house', 'liam_mother': 'liam_house', 'tessa': 'home_a',
                    'finn': 'home_a', 'rowan': 'home_b', 'ada': 'home_b', 'pippa': 'home_c'}
        for identifier, room in expected.items():
            with self.subTest(actor=identifier):
                rooms = [w.data['id'] for w in self.g.scenes.values()
                         if any(a.data['id'] == identifier for a in w.npcs)]
                self.assertEqual(rooms, [room])
        self.assertFalse(any(self.c.surface_prop_visible(p) for p in self.c.surface_props))


if __name__ == '__main__':unittest.main()
