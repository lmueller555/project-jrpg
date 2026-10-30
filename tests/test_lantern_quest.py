"""MQ04 opens with a child-owned craft, coherent actors and durable progress."""
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
from PIL import Image
import main
from tools.capture_lantern_quest import seed_previous_quests

LANTERN = 'CH01_MQ04'
ROOT = Path(__file__).resolve().parents[1]
OBJECTIVES = ['join_preparations', 'build_frame', 'visit_neighbours', 'visit_elira',
              'take_break', 'speak_serene', 'finish_lantern', 'show_mother']


class LanternQuestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'journey.json'
        self.g = self.game();self.c = self.g.lantern_quest
        seed_previous_quests(self.g)
        self.g.save_progress()

    def tearDown(self):pygame.quit()

    def game(self, title=False):
        game = main.Game(fullscreen=False, start_on_title=title, save_path=self.path,
                         settings_path=Path(self.temp.name)/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0);pygame.event.clear()
        return game

    def tick(self, seconds=.05):self.g.update(seconds, (0, 0), False)

    def until(self, predicate, seconds=150):
        for _ in range(round(seconds/.05)):
            if predicate():return
            self.tick()
        self.fail(('Timed out', self.c.stage, self.c.action, self.g.world.data['id'],
                   tuple(self.g.player.position), self.c._ready,
                   [(a.data['id'], self.c._world(a).data['id'], tuple(a.position))
                    for a in (self.c.tomas, self.c.liam, self.c.mother)]))

    def position(self, key, scene='eldenmere.playable'):
        """Place only the player; companions must still reach their own stations."""
        world = self.g._scene_by_id(scene)
        self.g.world = world
        point = pygame.Vector2(self.c.points[key])
        for radius in (0, 8, 16, 24, 32):
            for offset in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                value = point+offset
                if world.can_stand(value):
                    self.g.player.position.update(value)
                    self.g.transfer_cooldown = 0;self.g.camera.reset()
                    return
        self.fail(('No clear player station', key, scene))

    def read(self):
        identifier = self.g.social.script_identifier
        for _ in range(250):
            if not self.g.social.active or self.g.social.script_identifier != identifier:return
            self.assertFalse(self.g.social.choosing)
            self.g.social.advance()
        self.fail(('Unfinished scene', identifier))

    def scene(self, kind, finish=True):
        self.until(lambda: self.c._target() == kind)
        self.assertTrue(self.c.interact(), (kind, self.c.stage))
        self.assertEqual(self.g.social.script_identifier, 'lantern_'+kind)
        if finish:self.read()

    def invite(self):
        self.position('invitation');self.scene('invitation')
        self.assertEqual(self.c.stage, 'invited')
        self.assertEqual(self.g.quests.status(LANTERN), 'active')

    def classroom(self):
        self.invite();self.position('classroom', 'school');self.scene('classroom')
        self.assertEqual(self.c.stage, 'classroom')

    def design(self):
        self.classroom();self.scene('design')
        self.assertEqual(self.c.stage, 'designed')

    def permission(self):
        self.design();self.scene('permission')
        self.assertEqual(self.c.stage, 'permitted')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], ['join_preparations'])

    def workshop(self):
        self.permission();self.position('workshop');self.scene('workshop')
        self.assertEqual(self.c.stage, 'workshop')

    def try_shape(self):
        self.workshop();self.scene('test_shape')
        self.assertEqual(self.c.stage, 'tested')

    def assembled(self):
        self.try_shape();self.scene('assemble')
        self.until(lambda: self.c.action is None and self.c.stage == 'assembled')

    def lifted(self):
        self.assembled();self.scene('lift')
        self.until(lambda: self.c.action is None and self.c.stage == 'lifted')

    def frame_ready(self):
        self.lifted();self.scene('frame_ready')
        self.assertEqual(self.c.stage, 'frame_ready')

    def reload(self):
        self.g.save_progress();other = self.game(True)
        self.assertTrue(other.begin_journey(True), other.save_error)
        self.g = other;self.c = other.lantern_quest
        self.g.opening_fade = 0;self.g.transfer_cooldown = 0

    def test_new_game_keeps_the_quest_locked_before_regent_visit(self):
        self.assertTrue(self.g.begin_journey(False, show_cinematic=False))
        self.assertEqual(self.g.quests.status(LANTERN), 'locked')
        self.assertFalse(self.g.accept_quest(LANTERN))
        self.assertNotIn(LANTERN, self.g.quest_ui._visible_quests())

    def test_full_objective_chain_is_registered_before_later_sections_ship(self):
        record = self.g.quests.definitions[LANTERN]
        self.assertEqual([o['id'] for o in record['objectives']], OBJECTIVES)
        self.assertEqual(record['requires_quests'], ['CH01_MQ03'])
        self.assertNotIn('CH01_MQ05', self.g.quests.definitions)

    def test_unread_invitation_cannot_accept_the_quest(self):
        self.position('invitation');self.scene('invitation', False)
        self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.g.quests.status(LANTERN), 'available')
        self.assertEqual(self.c.stage, 'idle')
        self.reload();self.assertEqual(self.c.stage, 'idle')

    def test_cancelled_classroom_scene_does_not_advance_or_authorize_outing(self):
        self.invite();self.position('classroom', 'school');self.scene('classroom', False)
        self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.c.stage, 'invited')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], [])
        self.scene('classroom');self.assertEqual(self.c.stage, 'classroom')

    def test_design_and_mother_permission_are_separate_committed_scenes(self):
        self.design();self.scene('permission', False)
        self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.c.stage, 'designed')
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'join_preparations'), 'active')
        self.scene('permission')
        self.assertEqual(self.c.stage, 'permitted')
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'join_preparations'), 'completed')

    def test_leaving_before_permission_does_not_take_liam_out_of_school(self):
        self.classroom();self.position('workshop')
        self.tick(2)
        self.assertIs(self.c._world(self.c.liam), self.c.school)
        self.assertEqual(self.c.stage, 'classroom')
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'join_preparations'), 'active')

    def test_classroom_checkpoint_reloads_without_replaying_the_invitation(self):
        self.classroom();self.reload()
        self.assertEqual(self.c.stage, 'classroom')
        self.assertEqual(self.g.quests.status(LANTERN), 'active')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], [])
        self.assertFalse(self.g.social.active)
        self.assertIs(self.c._world(self.c.liam), self.c.school)

    def test_outing_uses_original_liam_teacher_children_and_tomas(self):
        originals = {a.data['id']: a for w in self.g.scenes.values() for a in w.npcs}
        self.classroom()
        ids = ('liam', 'liam_mother', 'tessa', 'finn', 'rowan', 'ada', 'pippa', 'tomas')
        for identifier in ids:
            with self.subTest(actor=identifier):
                found = [a for w in self.g.scenes.values() for a in w.npcs
                         if a.data['id'] == identifier]
                self.assertEqual(found, [originals[identifier]])
                self.assertIn(found[0], self.c.school.npcs)

    def test_regent_controller_does_not_pull_tomas_back_to_the_courtyard(self):
        self.classroom();position = self.c.tomas.position.copy()
        self.tick(.3)
        self.assertIs(self.g._routine_worlds[self.c.tomas], self.c.school)
        self.assertLess(self.c.tomas.position.distance_to(position), 8)
        self.assertEqual(self.g.regent_quest.stage, 'done')

    def test_mira_is_the_same_actor_and_remains_available_for_crafting(self):
        mira = self.g.mill_quest.mira;self.workshop()
        self.assertIs(self.c.mira, mira)
        self.assertEqual(sum(mira in w.npcs for w in self.g.scenes.values()), 1)
        self.tick(.5)
        self.assertIs(self.c._world(mira), self.g.town)
        self.assertEqual(self.c.stage, 'workshop')

    def test_unread_assembly_cannot_start_construction(self):
        self.try_shape();self.scene('assemble', False)
        self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.c.stage, 'tested')
        self.assertIsNone(self.c.action)
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'build_frame'), 'active')

    def test_reload_during_assembly_replays_the_action_without_granting_credit(self):
        self.try_shape();self.scene('assemble')
        self.assertIsNotNone(self.c.action)
        self.tick(.1);self.reload()
        self.assertEqual(self.c.stage, 'tested')
        self.assertIsNone(self.c.action)
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'build_frame'), 'active')
        self.scene('assemble')
        self.until(lambda: self.c.action is None and self.c.stage == 'assembled')

    def test_frame_credit_waits_for_lift_and_final_acknowledgment(self):
        self.lifted()
        self.assertTrue(hasattr(self.c.liam, 'story_sprite'))
        prop = next(p for p in self.c.surface_props if p['id'] == 'craft_surface')
        self.assertIs(prop['surface'], prop['states']['lifted'])
        self.reload()
        self.assertEqual(self.c.stage, 'lifted')
        self.assertTrue(hasattr(self.c.liam, 'story_sprite'))
        prop = next(p for p in self.c.surface_props if p['id'] == 'craft_surface')
        self.assertIs(prop['surface'], prop['states']['lifted'])
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'build_frame'), 'active')
        self.scene('frame_ready', False);self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.c.stage, 'lifted')
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'build_frame'), 'active')
        self.scene('frame_ready')
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'build_frame'), 'completed')
        self.assertEqual(self.g.quests.status(LANTERN), 'active')

    def test_frame_checkpoint_saves_without_completing_mq04_or_starting_festival(self):
        self.frame_ready();self.reload()
        self.assertEqual(self.c.stage, 'frame_ready')
        self.assertEqual(self.g.quests.status(LANTERN), 'active')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], OBJECTIVES[:2])
        self.assertNotIn('CH01_MQ05', self.g.quests.definitions)
        self.assertFalse(self.g.social.active)
        self.assertNotIn('CH01_MQ04_COMPLETE', self.g.social.flags)
        self.assertTrue(self.c.tracker_text())
        self.assertEqual(list(self.c.journal_objectives()), OBJECTIVES[:2])
        self.g.quest_ui.selected_quest = LANTERN
        rows = self.g.quest_ui._journal_rows()
        self.assertFalse(any(text.startswith(('Next:', 'Later:')) for text, *_ in rows))
        self.assertEqual(self.c.marker_for('mira_worker'),'?')
        self.until(lambda: self.c._target() == 'departure')

    def test_old_completed_regent_save_gains_mq04_without_replaying_earlier_quests(self):
        self.g.save_progress();data = json.loads(self.path.read_text())
        data.pop('lantern_quest');data['quests']['quests'].pop(LANTERN)
        self.path.write_text(json.dumps(data))
        other = self.game(True)
        self.assertTrue(other.begin_journey(True), other.save_error)
        self.assertEqual(other.quests.status(LANTERN), 'available')
        self.assertEqual(other.lantern_quest.stage, 'idle')
        self.assertEqual(other.quests.status('CH01_MQ03'), 'completed')
        self.assertEqual(other.regent_quest.stage, 'done')
        self.assertFalse(other.social.active)

    def test_active_quest_without_durable_record_is_rejected(self):
        self.invite();self.g.save_progress();data = json.loads(self.path.read_text())
        data.pop('lantern_quest');self.path.write_text(json.dumps(data))
        other = self.game(True)
        self.assertFalse(other.has_saved_journey)
        self.assertTrue(other.save_error)

    def test_save_rejects_stage_objective_mismatches_and_unearned_future_progress(self):
        self.invite();self.g.save_progress();data = json.loads(self.path.read_text())
        invalid = copy.deepcopy(data)
        invalid['lantern_quest']['stage'] = 'frame_ready'
        self.assertFalse(type(self.c).valid_journey(invalid))
        invalid = copy.deepcopy(data)
        invalid['lantern_quest']['stage'] = 'not_a_real_stage'
        self.assertFalse(type(self.c).valid_journey(invalid))
        invalid = copy.deepcopy(data)
        invalid['quests']['quests'][LANTERN]['completed_objectives'] = OBJECTIVES[:3]
        self.assertFalse(type(self.c).valid_journey(invalid))

    def test_overlay_panels_pause_construction_and_do_not_finish_the_frame(self):
        self.try_shape();self.scene('assemble')
        self.assertIsNotNone(self.c.action)
        for owner, field in ((self.g.pause, 'is_open'), (self.g.inventory_ui, 'is_open'),
                             (self.g, 'map_open'), (self.g.quest_ui, 'journal_open')):
            with self.subTest(panel=field):
                setattr(owner, field, True);self.tick(10);setattr(owner, field, False)
                self.assertIsNotNone(self.c.action)
                self.assertEqual(self.c.stage, 'tested')
        self.until(lambda: self.c.action is None and self.c.stage == 'assembled')

    def test_caelan_walks_to_each_contact_before_using_his_work_pose(self):
        self.try_shape()
        for kind, station, committed in (('assemble', self.c.points['assemble_player'], 'assembled'),
                                          ('lift', self.c.points['lift_player'], 'lifted')):
            with self.subTest(action=kind):
                self.scene(kind)
                self.assertIsNotNone(self.c.action)
                saw_movement = False;saw_contact = False
                for _ in range(240):
                    before = self.g.player.position.copy()
                    self.tick()
                    distance = self.g.player.position.distance_to(before)
                    self.assertLessEqual(distance, 72*.05+.001)
                    saw_movement |= distance > .01
                    if hasattr(self.g.player, 'story_sprite'):
                        saw_contact = True
                        self.assertLess(self.g.player.position.distance_to(station), .3)
                    self.assertEqual(self.g.quests.objective_status(LANTERN, 'build_frame'), 'active')
                    if self.c.action is None:break
                else:self.fail(('Contact action did not finish', kind))
                self.assertTrue(saw_movement, 'Caelan should approach the work instead of snapping to it.')
                self.assertTrue(saw_contact, 'Caelan should visibly help once he reaches the work.')
                self.assertEqual(self.c.stage, committed)

    def test_caelan_craft_poses_preserve_his_idle_head_legs_and_feet(self):
        meta = json.loads((ROOT/self.c.art['poses']['caelan']).read_text())
        source = Image.open(ROOT/'assets/characters/caelan/idle_right.png').convert('RGBA')
        sheet = Image.open(ROOT/meta['sheet']).convert('RGBA')
        ox, oy = meta['source_offset']
        self.assertTrue({'work', 'support'} <= set(meta['actions']))
        for kind, frames in meta['actions'].items():
            for index, frame in enumerate(frames):
                with self.subTest(action=kind, frame=index):
                    x, y, width, height = frame['rect']
                    pose = sheet.crop((x, y, x+width, y+height))
                    native = pose.crop((ox, oy, ox+24, oy+36))
                    self.assertEqual(native.crop((0, 0, 24, 14)).tobytes(),
                                     source.crop((0, 0, 24, 14)).tobytes())
                    self.assertEqual(native.crop((0, 25, 24, 36)).tobytes(),
                                     source.crop((0, 25, 24, 36)).tobytes())

    def test_repeat_interactions_cannot_duplicate_frame_credit(self):
        self.frame_ready();progress = self.g.quests.to_dict()
        for actor in (self.c.liam, self.c.mira, self.c.tomas):
            result = self.c.try_conversation(actor)
            if result:self.read()
        self.assertEqual(self.g.quests.to_dict(), progress)
        self.assertEqual(self.c.stage, 'frame_ready')

    def test_previous_world_repairs_remain_intact(self):
        self.frame_ready()
        self.assertTrue(self.g.mill_quest.mill_restored)
        self.assertFalse(self.g.opening_conclusion.mill_stopped)
        self.assertTrue(self.g.venn_visit.repaired)
        self.assertEqual(self.g.quests.status('CH01_MQ03'), 'completed')
        self.assertFalse(any('AUTHORIZ' in flag.upper() or 'EXCAVATION_STARTED' in flag.upper()
                             for flag in self.g.social.flags))

    def test_new_game_restores_school_children_to_their_households(self):
        self.frame_ready();self.assertTrue(self.g.begin_journey(False, show_cinematic=False))
        self.assertEqual(self.g.quests.status(LANTERN), 'locked')
        self.assertEqual(self.c.stage, 'idle')
        self.assertEqual(self.g.opening.stage, 'wake')
        expected = {'liam': 'liam_house', 'liam_mother': 'liam_house',
                    'tessa': 'home_a', 'finn': 'home_a', 'rowan': 'home_b',
                    'ada': 'home_b', 'pippa': 'home_c'}
        for identifier, scene in expected.items():
            with self.subTest(actor=identifier):
                rooms = [w.data['id'] for w in self.g.scenes.values()
                         if any(a.data['id'] == identifier for a in w.npcs)]
                self.assertEqual(rooms, [scene])
        self.assertEqual(self.c.school.npcs, [])
        self.assertIsNone(self.c.liam.work_renderer)


if __name__ == '__main__':unittest.main()
