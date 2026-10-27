"""Finish one lantern, show the real mother, then close the afternoon safely."""
import copy
import hashlib
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
from tools.capture_lantern_finish import seed_serene_checkpoint, MAIN_SCENES, OBJECTIVES, FIRST_SIX

ROOT = Path(__file__).resolve().parents[1]
LANTERN = 'CH01_MQ04'
STEPS = (
    ('finish_invitation', 'finish_invited', 6, 'home'),
    ('home_return', 'home_rejoined', 6, 'home'),
    ('purpose', 'purpose_chosen', 6, 'home'),
    ('final_panel', 'panel_ready', 6, 'home'),
    ('dry_fit', 'fit_ready', 6, 'home'),
    ('fasten_covering', 'covered', 6, 'home'),
    ('finished_lantern', 'lantern_finished', 7, 'held'),
    ('school_welcome', 'school_met', 7, 'held'),
    ('show_mother', 'mother_shown', 7, 'held'),
    ('homeward', 'homeward', 7, 'held'),
    ('put_away', 'put_away', 7, 'home'),
    ('farewell', 'done', 8, 'home'),
)


class LanternFinishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'journey.json'
        self.g = self.game();self.c = self.g.lantern_quest
        seed_serene_checkpoint(self.g);self.g.save_progress()

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
        self.fail(('Timed out', self.c.stage, self.c.action, self.g.social.script_identifier,
                   self.g.world.data['id'], tuple(self.g.player.position), self.c._ready,
                   [(a.data['id'], self.c._world(a).data['id'], tuple(a.position))
                    for a in (self.c.liam, self.c.tomas, self.c.serene, self.c.mother)]))

    def position(self):
        """Move only Caelan; production followers must reach the scene themselves."""
        world, station = self.c.finish_part._where()
        self.assertIsNotNone(world, self.c.stage);self.g.world = world
        for radius in (0, 8, 16, 24, 32):
            for offset in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                candidate = pygame.Vector2(self.c.finish_points[station])+offset
                if world.can_stand(candidate):
                    self.g.player.position.update(candidate)
                    self.g.opening_fade = 0;self.g.transfer_cooldown = 0
                    self.g.camera.reset();return
        self.fail(('No clear scene station', station, world.data['id']))

    def read(self):
        identifier = self.g.social.script_identifier
        for _ in range(350):
            if not self.g.social.active or self.g.social.script_identifier != identifier:return
            self.assertFalse(self.g.social.choosing);self.g.social.advance()
        self.fail(('Unfinished scene', identifier))

    def scene(self, kind, finish=True):
        self.position();self.until(lambda: self.c._target() == kind)
        self.assertTrue(self.c.interact(), (kind, self.c.stage))
        self.assertEqual(self.g.social.script_identifier, 'lantern_'+kind)
        if finish:self.read()

    def step(self, entry):
        kind, stage, count, location = entry
        self.scene(kind)
        self.until(lambda: self.c.action is None and self.c.stage == stage)
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], OBJECTIVES[:count])
        self.assertEqual(self.c.finish_part.frame_location, location)
        self.assertEqual(self.g.quests.status(LANTERN), 'completed' if stage == 'done' else 'active')

    def through(self, kind):
        for entry in STEPS:
            self.step(entry)
            if entry[0] == kind:return
        self.fail(('Unknown scene', kind))

    def reload(self):
        self.g.save_progress();other = self.game(True)
        self.assertTrue(other.begin_journey(True), other.save_error)
        self.g = other;self.c = other.lantern_quest
        self.g.opening_fade = 0;self.g.transfer_cooldown = 0

    def assert_one_actor(self, actor):
        self.assertEqual([a for w in self.g.scenes.values() for a in w.npcs
                          if a.data['id'] == actor.data['id']], [actor])

    def test_real_pr3_save_continues_without_repeating_serene_or_previous_visits(self):
        original = json.loads(self.path.read_text())
        self.assertEqual(original['lantern_quest'], {'version': 1, 'stage': 'serene_heard'})
        self.assertEqual(original['quests']['quests'][LANTERN]['completed_objectives'], FIRST_SIX)
        self.reload()
        self.assertFalse(self.g.social.active)
        self.assertEqual(self.c.to_dict(), {'version': 1, 'stage': 'serene_heard'})
        self.assertEqual(self.c.finish_part.frame_location, 'home')
        self.scene('finish_invitation')
        self.assertEqual(self.c.stage, 'finish_invited')

    def test_each_unread_scene_is_cancel_safe_and_each_checkpoint_reloads(self):
        for entry in STEPS:
            kind, stage, count, location = entry
            with self.subTest(scene=kind):
                previous = self.c.to_dict().copy()
                objectives = list(self.g.quests.states[LANTERN]['completed_objectives'])
                ownership = self.c.finish_part.frame_location
                self.scene(kind, False);self.g.social.advance();self.g.social.cancel()
                self.assertEqual(self.c.to_dict(), previous)
                self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], objectives)
                self.assertEqual(self.c.finish_part.frame_location, ownership)
                self.assertIsNone(self.c.action)
                self.reload()
                self.assertEqual(self.c.to_dict(), previous)
                self.step(entry);self.reload()
                self.assertEqual(self.c.stage, stage)
                self.assertEqual(self.c.finish_part.frame_location, location)
                self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], OBJECTIVES[:count])
                self.assertFalse(self.g.social.active)

    def test_interrupted_prepare_cover_pickup_and_storage_restore_last_committed_object(self):
        action_scenes = {'dry_fit', 'fasten_covering', 'finished_lantern', 'put_away'}
        for entry in STEPS:
            kind, stage, count, location = entry
            with self.subTest(scene=kind):
                if kind in action_scenes:
                    previous = self.c.to_dict().copy()
                    ownership = self.c.finish_part.frame_location
                    credit = list(self.g.quests.states[LANTERN]['completed_objectives'])
                    self.scene(kind)
                    self.assertIsNotNone(self.c.action)
                    self.assertEqual(self.c.to_dict(), previous)
                    self.reload()
                    self.assertIsNone(self.c.action)
                    self.assertEqual(self.c.to_dict(), previous)
                    self.assertEqual(self.c.finish_part.frame_location, ownership)
                    self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], credit)
                self.step(entry)

    def test_covering_and_inspection_do_not_award_finish_credit_until_safe_pickup(self):
        self.through('fasten_covering')
        self.assertEqual(self.c.stage, 'covered')
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'finish_lantern'), 'active')
        self.scene('finished_lantern', False);self.g.social.cancel()
        self.assertEqual(self.c.stage, 'covered')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_SIX)
        self.step(STEPS[6])
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'finish_lantern'), 'completed')

    def test_one_unlit_lantern_changes_form_then_moves_home_to_hands_and_back(self):
        finish = self.c.finish_part
        self.assertFalse(finish.art['frame_is_lit'])
        expected_forms = {'serene_heard': 'bare', 'finish_invited': 'bare',
                          'home_rejoined': 'bare', 'purpose_chosen': 'bare',
                          'panel_ready': 'panel', 'fit_ready': 'partial'}
        rest_frame = next(p for p in self.c.rest.surface_props if p['id'] == 'home_frame')
        final_frame = next(p for p in finish.surface_props if p['id'] == 'home_lantern')
        for entry in STEPS:
            self.step(entry)
            with self.subTest(stage=self.c.stage):
                self.assertEqual(finish.frame_form, expected_forms.get(self.c.stage, 'finished'))
                self.assertFalse(self.c.rest.surface_prop_visible(rest_frame))
                self.assertEqual(finish.surface_prop_visible(final_frame), finish.frame_location == 'home')
                if finish.frame_location == 'home':
                    self.assertIs(final_frame['surface'], final_frame['states'][finish.frame_form])
                self.assert_one_actor(self.c.liam)

    def test_showing_mother_is_not_an_early_completion_or_report_back(self):
        self.through('show_mother')
        self.assertEqual(self.c.stage, 'mother_shown')
        self.assertEqual(self.g.quests.status(LANTERN), 'active')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], OBJECTIVES[:7])
        self.assertNotIn('CH01_MQ04_COMPLETE', self.g.social.flags)
        self.step(STEPS[9]);self.step(STEPS[10])
        self.assertEqual(self.g.quests.status(LANTERN), 'active')
        self.scene('farewell', False);self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.c.stage, 'put_away')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], OBJECTIVES[:7])

    def test_final_callback_completes_atomically_once_without_ready_to_report_notice(self):
        self.through('put_away')
        self.g.quests.drain_events();self.g.quest_ui.reset()
        self.scene('farewell', False)
        self.assertEqual(self.g.quests.status(LANTERN), 'active')
        self.read()
        self.assertEqual(self.c.stage, 'done')
        self.assertEqual(self.g.quests.status(LANTERN), 'completed')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], OBJECTIVES)
        events = self.g.quests.drain_events()
        self.assertEqual(sum(e['kind'] == 'completed' and e['quest_id'] == LANTERN for e in events), 1)
        self.assertFalse(any(e['kind'] == 'ready' for e in events))
        self.assertIn('CH01_MQ04_COMPLETE', self.g.social.flags)
        for _ in range(3):
            self.tick();self.c.finish_part.finish('farewell')
        self.assertFalse(any(e['kind'] == 'completed' for e in self.g.quests.drain_events()))
        notices = list(self.g.quest_ui.notices)
        if self.g.quest_ui.current_notice is not None:notices.append(self.g.quest_ui.current_notice)
        self.assertFalse(any(e['kind'] == 'ready' for e in notices))
        self.reload()
        self.assertEqual(self.c.to_dict(), {'version': 1, 'stage': 'done'})
        self.assertEqual(self.g.quests.status(LANTERN), 'completed')
        self.assertFalse(self.g.quests.drain_events())
        self.g.quest_ui.selected_quest = LANTERN
        rows = [text for text, *_ in self.g.quest_ui._journal_rows()]
        self.assertFalse(any('Report back' in text or 'Ready to report' in text for text in rows))
        self.assertNotIn('CH01_MQ05', self.g.quests.definitions)

    def test_existing_mother_teaches_at_school_and_father_remains_home(self):
        mother = self.c.mother;father = self.c.father
        self.through('show_mother')
        self.assert_one_actor(mother);self.assert_one_actor(father)
        self.assertIn(mother, self.c.school.npcs);self.assertIn(father, self.c.liam_home.npcs)
        self.assertNotIn(mother, self.c.liam_home.npcs)
        for child in self.c.children.values():self.assertIn(child, self.c.school.npcs)
        self.step(STEPS[9]);self.step(STEPS[10]);self.step(STEPS[11]);self.reload()
        self.assert_one_actor(self.c.mother);self.assert_one_actor(self.c.father)
        self.assertIn(self.c.mother, self.c.school.npcs)
        self.assertIn(self.c.father, self.c.liam_home.npcs)
        for child in self.c.children.values():self.assertIn(child, self.c.school.npcs)

    def test_optional_mira_and_post_storage_father_do_not_replay_outdated_instructions(self):
        self.through('finished_lantern')
        self.g.world = self.c._world(self.c.mira)
        self.assertIn(self.c.mira, self.g.world.npcs)
        for offset in ((32, 0), (-32, 0), (0, 32), (0, -32)):
            point = self.c.mira.position+offset
            if self.g.world.can_stand(point):
                self.g.player.position.update(point);break
        else:self.fail('No clear player station beside the actual Mira')
        self.c._ready = False
        self.assertIsNone(self.c._target())
        self.assertTrue(self.g.social.start(self.c.mira))
        self.assertEqual(self.g.social.script_identifier, 'lantern_mira_done')
        self.assertEqual(self.g.social.page['speaker'], 'mira')
        self.g.social.cancel()
        self.assertEqual(self.c.stage, 'lantern_finished')
        self.assertEqual(self.c.finish_part.frame_location, 'held')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], OBJECTIVES[:7])
        for entry in STEPS[7:11]:self.step(entry)
        self.assertIn(self.c.father, self.g.world.npcs)
        self.c._ready = False
        self.assertIsNone(self.c._target())
        self.assertTrue(self.g.social.start(self.c.father))
        self.assertEqual(self.g.social.script_identifier, 'lantern_father_done')
        self.assertEqual(self.g.social.page['speaker'], 'liam_father')
        self.g.social.cancel()
        self.assertEqual(self.c.stage, 'put_away')
        self.assertEqual(self.c.finish_part.frame_location, 'home')
        self.assertEqual(self.g.quests.status(LANTERN), 'active')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], OBJECTIVES[:7])

    def test_done_releases_liam_and_keeps_tomas_serene_at_afternoon_stations(self):
        self.through('farewell')
        self.until(lambda: self.c._world(self.c.tomas) is self.c.sanctuary and
                   not self.c.tomas.story_following and self.g.play_routines[0].liam_owner is None)
        self.assertIsNone(self.g.play_routines[0].liam_owner)
        self.assertIsNone(self.g.play_routines[0].pending_liam_owner)
        self.assertFalse(self.c._liam_claimed)
        self.assertFalse(hasattr(self.c.liam, 'story_sprite'))
        self.assertFalse(self.c.tomas.story_following)
        self.assertIs(self.c._world(self.c.serene), self.c.sanctuary)
        self.assertIs(self.c._world(self.c.tomas), self.c.sanctuary)
        self.assert_one_actor(self.c.liam);self.assert_one_actor(self.c.tomas);self.assert_one_actor(self.c.serene)
        for _ in range(12):self.tick(.5)
        self.assertIsNone(self.g.play_routines[0].liam_owner)
        self.assertIsNone(self.c._target())

    def test_reloaded_done_does_not_reclaim_followers_or_replay_notices(self):
        self.through('farewell');self.reload()
        for _ in range(16):self.tick(.5)
        self.assertEqual(self.c.stage, 'done')
        self.assertIsNone(self.g.play_routines[0].liam_owner)
        self.assertIsNone(self.g.play_routines[0].pending_liam_owner)
        self.assertFalse(self.c._liam_claimed)
        self.assertFalse(self.g.social.active)
        self.assertIsNone(self.g.quest_ui.current_notice)
        self.assertFalse(self.g.quest_ui.notices)
        self.assertEqual(self.c.finish_part.frame_location, 'home')

    def test_completed_lantern_allows_an_ordinary_block_session_without_reclaiming_liam(self):
        self.through('farewell')
        shared = self.g.play_routines[0];blocks = self.g.block_routines[0]
        shared.cooldown_ms = 999999
        self.assertTrue(blocks.begin(accident=False, forget=False))
        self.until(lambda: blocks.active)
        self.assertIs(shared.liam_owner, blocks)
        for _ in range(20):self.tick(.1)
        self.assertEqual(self.c.stage, 'done')
        self.assertIs(shared.liam_owner, blocks)
        self.assertIsNone(shared.pending_liam_owner)
        self.assertFalse(hasattr(self.c.liam, 'story_sprite'))
        self.assertTrue(self.g.begin_journey(False))
        self.assertEqual(self.c.stage, 'idle')
        self.assertIsNone(shared.liam_owner);self.assertIsNone(shared.pending_liam_owner)
        self.assertFalse(blocks.active);self.assertIsNone(blocks.forgotten_id)
        self.assertIs(shared.worlds[self.c.liam], self.c.liam_home)
        self.assertFalse(any(self.c.finish_part.surface_prop_visible(p) for p in self.c.finish_part.surface_props))

    def test_final_carry_preserves_original_heads_and_leg_motion_in_every_direction(self):
        meta = self.c.finish_part.pose_meta
        body = self.g.town.image(meta['body_sheet']);frame = self.g.town.image(meta['frame_sheet'])
        self.assertEqual(set(meta['carry']), {'front', 'back', 'left', 'right'})
        for direction, spec in meta['carry'].items():
            self.assertEqual(len(spec['walk']), 4)
            for index, record in enumerate([spec['idle'], *spec['walk']]):
                with self.subTest(direction=direction, frame=index):
                    source_path = ROOT/record['source_path']
                    self.assertEqual(hashlib.sha256(source_path.read_bytes()).hexdigest(), record['source_sha256'])
                    source = self.g.town.image(record['source_path'])
                    body_pose = body.subsurface(record['rect']);ox, oy = record['native_offset']
                    for x, y, width, height in record['preserved_regions']:
                        self.assertEqual(pygame.image.tobytes(body_pose.subsurface((ox+x, oy+y, width, height)), 'RGBA'),
                                         pygame.image.tobytes(source.subsurface((x, y, width, height)), 'RGBA'))
                    held = frame.subsurface(record['rect'])
                    self.assertGreater(held.get_bounding_rect().width, 0)
                    self.assertLess(held.get_bounding_rect().bottom, body_pose.get_bounding_rect().bottom)
                    self.assertGreaterEqual(record['ground_clearance_pixels'], 1)
                    joints = [pygame.Vector2(p) for p in record['joints']]
                    for a, b, length in zip(joints, joints[1:], meta['arm_lengths']):
                        self.assertAlmostEqual(a.distance_to(b), length, places=4)

    def test_finished_carry_uses_actual_facing_and_walk_frames(self):
        self.through('finished_lantern');surfaces = {}
        for direction in ('front', 'back', 'left', 'right'):
            self.c.liam.facing = direction;self.c.liam.moving = False
            self.c.finish_part.render(0.);idle = self.c.liam.story_sprite
            self.c.liam.moving = True;self.c.liam.walk_ms = 160
            self.c.finish_part.render(0.)
            self.assertIsNot(self.c.liam.story_sprite, idle)
            surfaces[direction] = pygame.image.tobytes(self.c.liam.story_sprite, 'RGBA')
        self.assertEqual(len(set(surfaces.values())), 4)

    def test_daisy_and_the_existing_bone_are_independent_of_finishing(self):
        dog = self.g.play_routines[0].daisy;bone = self.g.bone_routines[0]
        dog.cooldowns = {'food': 999999, 'water': 999999}
        dog.state = 'pause';dog.activity = 'wander';bone.cooldown_ms = 999999
        self.assertTrue(bone.begin(kind='rug', playful=False))
        self.until(lambda: bone.bone['state'] == 'mouth')
        before = bone.bone
        self.through('purpose');self.scene('final_panel', False)
        self.assertIs(bone.bone, before)
        self.assertIn(bone.bone['state'], ('mouth', 'paws', 'ground'))
        self.assertEqual(len(bone.surface_props), 1)
        self.assertEqual(bone.surface_prop_visible(bone.surface_props[0]), bone.bone['state'] == 'ground')
        self.assert_one_actor(dog)
        self.assertFalse(self.g.play_routines[0].active)
        self.g.social.cancel()
        for entry in STEPS[3:]:self.step(entry)
        self.assertIs(bone.bone, before)
        self.assertEqual(len(bone.surface_props), 1)
        self.assert_one_actor(dog)

    def test_prior_repairs_memorial_and_selected_decorations_persist_after_completion(self):
        self.through('farewell');self.reload()
        self.assertTrue(self.g.mill_quest.mill_restored)
        self.assertFalse(self.g.opening_conclusion.mill_stopped)
        self.assertTrue(self.g.venn_visit.repaired)
        self.assertEqual(self.g.elira_visit.lantern, 'table')
        for prop in self.c.village.surface_props:
            with self.subTest(prop=prop['id']):
                self.assertTrue(self.c.village.surface_prop_visible(prop))
                if 'selected' in prop['states']:self.assertIs(prop['surface'], prop['states']['selected'])

    def test_forged_final_snapshots_and_mismatched_completion_are_rejected(self):
        self.through('farewell');self.g.save_progress()
        data = json.loads(self.path.read_text());self.assertTrue(type(self.c).valid_journey(data))
        for stage, status, count in (('done', 'active', 8), ('done', 'completed', 7),
                                     ('mother_shown', 'completed', 8), ('covered', 'active', 7),
                                     ('lantern_finished', 'active', 6), ('put_away', 'ready', 8)):
            with self.subTest(stage=stage, status=status, count=count):
                invalid = copy.deepcopy(data);invalid['lantern_quest']['stage'] = stage
                invalid['quests']['quests'][LANTERN] = {'status': status, 'completed_objectives': OBJECTIVES[:count]}
                self.assertFalse(type(self.c).valid_journey(invalid))

    def test_new_game_removes_finished_props_and_releases_all_final_cast(self):
        self.through('farewell');self.assertTrue(self.g.begin_journey(False))
        self.assertEqual(self.c.stage, 'idle')
        self.assertEqual(self.g.quests.status(LANTERN), 'locked')
        self.assertIsNone(self.g.play_routines[0].liam_owner)
        self.assertIsNone(self.g.play_routines[0].pending_liam_owner)
        self.assertFalse(self.c.school.npcs)
        self.assertFalse(any(self.c.finish_part.surface_prop_visible(p) for p in self.c.finish_part.surface_props))
        for actor in (self.c.father, self.c.mother, self.c.serene, self.c.tomas):
            self.assertIsNone(getattr(actor, 'story_sprite', None), actor.data['id'])


if __name__ == '__main__':unittest.main()
