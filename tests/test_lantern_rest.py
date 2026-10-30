"""The home break conserves materials and carries questions to Serene."""
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
from tools.capture_lantern_rest import seed_elira_checkpoint, MAIN_SCENES, FIRST_SIX

ROOT = Path(__file__).resolve().parents[1]
LANTERN = 'CH01_MQ04'


class LanternRestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'journey.json'
        self.g = self.game();self.c = self.g.lantern_quest
        seed_elira_checkpoint(self.g);self.g.save_progress()

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
                    for a in (self.c.liam, self.c.tomas, self.c.serene)]))

    def position(self, key, scene='eldenmere.playable'):
        """Move only Caelan; companions must reach their own stations normally."""
        world = self.g._scene_by_id(scene);self.g.world = world
        desired = self.c.village_points['reflection'] if key == 'break_invitation' else self.c.rest_points[key]
        for radius in (0, 8, 16, 24, 32):
            for offset in ((0, radius), (-radius, 0), (radius, 0), (0, -radius)):
                candidate = pygame.Vector2(desired)+offset
                if world.can_stand(candidate):
                    self.g.player.position.update(candidate)
                    self.g.transfer_cooldown = 0;self.g.camera.reset();return
        self.fail(('No clear station', key, scene, desired))

    def read(self):
        identifier = self.g.social.script_identifier
        for _ in range(350):
            if not self.g.social.active or self.g.social.script_identifier != identifier:return
            self.assertFalse(self.g.social.choosing);self.g.social.advance()
        self.fail(('Unfinished scene', identifier))

    def scene(self, kind, finish=True):
        self.until(lambda: self.c._target() == kind)
        self.assertTrue(self.c.interact(), (kind, self.c.stage))
        self.assertEqual(self.g.social.script_identifier, 'lantern_'+kind)
        if finish:self.read()

    def leave_elira(self):
        self.position('break_invitation');self.scene('break_invitation')
        self.assertEqual(self.c.stage, 'collecting_route')

    def collect(self):
        self.leave_elira();self.position('collection');self.scene('collect_frame')
        self.until(lambda: self.c.action is None and self.c.stage == 'materials_collected')
        self.assertEqual(self.c.rest.frame_location, 'held')

    def home(self):
        self.collect();self.position('home', 'liam_house');self.scene('home_welcome')
        self.until(lambda: self.c.action is None and self.c.stage == 'materials_home')
        self.assertEqual(self.c.rest.frame_location, 'home')

    def rest(self):self.home();self.scene('snack')

    def paper(self):
        self.rest();self.scene('paper_practice')
        self.until(lambda: self.c.action is None and self.c.stage == 'paper_tried')

    def finish_break(self):
        self.paper();self.scene('brothers');self.scene('liam_questions')
        self.assertEqual(self.c.stage, 'home_break_done')

    def greet_serene(self):
        self.finish_break();self.position('sanctuary', 'sanctuary_hall')
        self.scene('sanctuary_welcome')
        self.assertEqual(self.c.stage, 'serene_welcomed')

    def finish_section(self):
        self.greet_serene()
        for kind in ('returning_life', 'remembering', 'sanctuary_close'):self.scene(kind)
        self.assertEqual(self.c.stage, 'serene_heard')

    def reload(self):
        self.g.save_progress();other = self.game(True)
        self.assertTrue(other.begin_journey(True), other.save_error)
        self.g = other;self.c = other.lantern_quest
        self.g.opening_fade = 0;self.g.transfer_cooldown = 0

    def frame_surface(self):return next(p for p in self.c.surface_props if p['id'] == 'craft_surface')

    def test_existing_pr2_checkpoint_continues_without_replaying_village_visits(self):
        self.reload()
        self.assertEqual(self.c.to_dict(), {'version': 1, 'stage': 'elira_visited'})
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_SIX[:4])
        self.assertFalse(self.g.social.active)
        self.until(lambda: self.c._target() == 'break_invitation')

    def test_unread_break_invitation_cannot_move_materials_or_grant_credit(self):
        self.position('break_invitation');self.scene('break_invitation', False)
        self.g.social.advance();self.g.social.cancel();self.tick()
        self.assertEqual(self.c.stage, 'elira_visited')
        self.assertEqual(self.c.rest.frame_location, 'workshop')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_SIX[:4])

    def test_unread_collection_keeps_the_original_frame_on_miras_table(self):
        self.leave_elira();self.position('collection');self.scene('collect_frame', False)
        self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.c.stage, 'collecting_route')
        self.assertEqual(self.c.rest.frame_location, 'workshop')
        prop = self.frame_surface()
        self.assertTrue(self.c.surface_prop_visible(prop))
        self.assertIs(prop['surface'], prop['states']['ready'])

    def test_reload_before_pickup_contact_restores_workshop_not_a_second_frame(self):
        self.leave_elira();self.position('collection');self.scene('collect_frame')
        self.assertIsNotNone(self.c.action)
        self.reload()
        self.assertEqual(self.c.stage, 'collecting_route')
        self.assertEqual(self.c.rest.frame_location, 'workshop')
        self.assertIsNone(self.c.action)
        self.scene('collect_frame')
        self.until(lambda: self.c.stage == 'materials_collected')
        self.assertEqual(self.c.rest.frame_location, 'held')

    def test_carried_checkpoint_reloads_with_one_carried_frame_and_unchanged_credit(self):
        self.collect();self.reload()
        self.assertEqual(self.c.stage, 'materials_collected')
        self.assertEqual(self.c.rest.frame_location, 'held')
        self.assertTrue(hasattr(self.c.liam, 'story_sprite'))
        prop = self.frame_surface()
        self.assertTrue(not self.c.surface_prop_visible(prop) or prop['surface'] is not prop['states']['ready'])
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_SIX[:4])

    def test_all_directional_carry_frames_preserve_approved_heads_legs_and_ground_clearance(self):
        meta = self.c.rest.pose_meta
        body = self.g.town.image(meta['body_sheet'])
        frame = self.g.town.image(meta['frame_sheet'])
        self.assertEqual(set(meta['carry']), {'front', 'back', 'left', 'right'})
        for direction, spec in meta['carry'].items():
            self.assertEqual(len(spec['walk']), 4)
            for index, record in enumerate([spec['idle'], *spec['walk']]):
                with self.subTest(direction=direction, frame=index):
                    source_path = ROOT/record['source_path']
                    self.assertEqual(hashlib.sha256(source_path.read_bytes()).hexdigest(), record['source_sha256'])
                    source = self.g.town.image(record['source_path'])
                    body_pose = body.subsurface(record['rect'])
                    ox, oy = record['native_offset']
                    for x, y, width, height in record['preserved_regions']:
                        expected = source.subsurface((x, y, width, height))
                        actual = body_pose.subsurface((ox+x, oy+y, width, height))
                        self.assertEqual(pygame.image.tobytes(actual, 'RGBA'),
                                         pygame.image.tobytes(expected, 'RGBA'))
                    frame_pose = frame.subsurface(record['rect'])
                    self.assertGreater(frame_pose.get_bounding_rect().width, 0)
                    self.assertLess(frame_pose.get_bounding_rect().bottom,
                                    body_pose.get_bounding_rect().bottom)
                    self.assertGreaterEqual(record['ground_clearance_pixels'], 1)
                    joints = [pygame.Vector2(p) for p in record['joints']]
                    for first, second, length in zip(joints, joints[1:], meta['arm_lengths']):
                        self.assertAlmostEqual(first.distance_to(second), length, places=4)

    def test_carried_render_changes_with_real_direction_and_walk_phase(self):
        self.collect()
        surfaces = {}
        for direction in ('front', 'back', 'left', 'right'):
            self.c.liam.facing = direction;self.c.liam.moving = False
            self.c.rest.render(0.)
            idle = self.c.liam.story_sprite
            self.c.liam.moving = True;self.c.liam.walk_ms = 160
            self.c.rest.render(0.)
            self.assertIsNot(self.c.liam.story_sprite, idle)
            surfaces[direction] = pygame.image.tobytes(self.c.liam.story_sprite, 'RGBA')
        self.assertEqual(len(set(surfaces.values())), 4)

    def test_cancelled_home_welcome_keeps_frame_carried_until_placement(self):
        self.collect();self.position('home', 'liam_house');self.scene('home_welcome', False)
        self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.c.stage, 'materials_collected')
        self.assertEqual(self.c.rest.frame_location, 'held')
        self.reload()
        self.assertEqual(self.c.rest.frame_location, 'held')

    def test_interrupted_placement_restores_the_last_committed_carrier(self):
        self.collect();self.position('home', 'liam_house');self.scene('home_welcome')
        self.assertIsNotNone(self.c.action);self.reload()
        self.assertEqual(self.c.stage, 'materials_collected')
        self.assertEqual(self.c.rest.frame_location, 'held')
        self.scene('home_welcome')
        self.until(lambda: self.c.stage == 'materials_home')
        self.assertEqual(self.c.rest.frame_location, 'home')

    def test_practice_is_a_draft_and_interruption_cannot_finish_the_lantern(self):
        self.rest();self.scene('paper_practice')
        self.assertIsNotNone(self.c.action);self.reload()
        self.assertEqual(self.c.stage, 'rested')
        self.assertEqual(self.c.rest.frame_location, 'home')
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'finish_lantern'), 'queued')
        self.scene('paper_practice')
        self.until(lambda: self.c.stage == 'paper_tried')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_SIX[:4])

    def test_liam_remains_visibly_occupied_during_the_brothers_conversation(self):
        self.paper();self.scene('brothers', False)
        frames = set()
        for _ in range(16):
            self.tick(.1)
            self.assertTrue(hasattr(self.c.liam, 'story_sprite'))
            frames.add(pygame.image.tobytes(self.c.liam.story_sprite, 'RGBA'))
        self.assertGreater(len(frames), 1)
        self.assertIs(self.g.play_routines[0].liam_owner, self.c)
        self.assertFalse(self.g.play_routines[0].active)
        self.assertFalse(self.g.block_routines[0].active)
        self.g.social.cancel()
        self.assertEqual(self.c.stage, 'paper_tried')

    def test_break_credit_waits_for_liams_questions_after_rest_and_practice(self):
        self.paper();self.scene('brothers');self.scene('liam_questions', False)
        self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.c.stage, 'brothers_spoken')
        self.assertEqual(self.g.quests.objective_status(LANTERN, 'take_break'), 'active')
        self.scene('liam_questions')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_SIX[:5])

    def test_father_is_the_existing_home_actor_and_mother_stays_at_school(self):
        father = self.c.father;self.home()
        self.assertEqual([a for w in self.g.scenes.values() for a in w.npcs
                          if a.data['id'] == 'liam_father'], [father])
        self.assertIn(father, self.c.liam_home.npcs)
        self.assertIn(self.c.mother, self.c.school.npcs)
        self.assertNotIn(self.c.mother, self.c.liam_home.npcs)
        self.assertIn('liam_father', self.g.social.data['speakers'])

    def test_daisy_food_activity_does_not_gate_the_break_or_borrow_the_dog(self):
        dog = self.g.play_routines[0].daisy
        bone = self.g.bone_routines[0]
        if bone.active:bone.request_release();self.until(lambda: not bone.active)
        dog.begin_activity('food', self.c.liam_home)
        self.finish_break()
        self.assertEqual(self.c.stage, 'home_break_done')
        self.assertFalse(dog.play_owned)
        self.assertEqual(sum(dog in w.npcs for w in self.g.scenes.values()), 1)
        self.assertIs(self.g.play_routines[0].liam_owner, self.c)

    def test_held_bone_remains_one_independent_toy_during_home_conversations(self):
        dog = self.g.play_routines[0].daisy;bone = self.g.bone_routines[0]
        dog.cooldowns = {'food': 999999, 'water': 999999}
        dog.state = 'pause';dog.activity = 'wander'
        bone.cooldown_ms = 999999
        self.assertTrue(bone.begin(kind='rug', playful=False))
        self.until(lambda: bone.bone['state'] == 'mouth')
        self.assertTrue(dog.play_owned)
        before = bone.bone
        self.home();self.scene('snack', False)
        self.assertIs(bone.bone, before)
        self.assertIn(bone.bone['state'], ('mouth', 'paws', 'ground'))
        self.assertEqual(len(bone.surface_props), 1)
        visible = bone.surface_prop_visible(bone.surface_props[0])
        self.assertEqual(visible, bone.bone['state'] == 'ground')
        self.assertFalse(self.g.play_routines[0].active)
        self.g.social.cancel()

    def test_serene_handoff_keeps_the_same_actor_in_the_sanctuary(self):
        serene = self.c.serene;self.greet_serene();before = serene.position.copy()
        self.tick(.5)
        self.assertEqual(self.c._world(serene), self.c.sanctuary)
        self.assertLess(serene.position.distance_to(before), 2)
        self.assertEqual([a for w in self.g.scenes.values() for a in w.npcs
                          if a.data['id'] == 'mother_serene'], [serene])
        self.assertEqual(self.g.regent_quest.stage, 'done')

    def test_sanctuary_conversations_commit_separately_and_only_after_reading(self):
        self.greet_serene()
        for kind, prior, after in (('returning_life', 'serene_welcomed', 'faith_discussed'),
                                   ('remembering', 'faith_discussed', 'remembrance_discussed'),
                                   ('sanctuary_close', 'remembrance_discussed', 'serene_heard')):
            with self.subTest(scene=kind):
                self.scene(kind, False);self.g.social.advance();self.g.social.cancel()
                self.assertEqual(self.c.stage, prior)
                self.scene(kind);self.assertEqual(self.c.stage, after)

    def test_six_objective_endpoint_stays_active_and_keeps_materials_at_home(self):
        self.finish_section();self.reload()
        self.assertEqual(self.c.to_dict(), {'version': 1, 'stage': 'serene_heard'})
        self.assertEqual(self.g.quests.status(LANTERN), 'active')
        self.assertEqual(self.g.quests.states[LANTERN]['completed_objectives'], FIRST_SIX)
        self.assertEqual(self.c.rest.frame_location, 'home')
        self.assertEqual(list(self.c.journal_objectives()), FIRST_SIX)
        self.assertNotIn('CH01_MQ04_COMPLETE', self.g.social.flags)
        self.assertNotIn('CH01_MQ05', self.g.quests.definitions)
        self.g.quest_ui.selected_quest = LANTERN
        self.assertFalse(any(text.startswith(('Next:', 'Later:')) for text, *_ in self.g.quest_ui._journal_rows()))
        self.assertNotIn(self.c.marker_for('mother_serene'), ('!', '?'))
        self.assertEqual(self.c.marker_for('liam'), '?')

    def test_reloading_each_committed_checkpoint_restores_material_location_and_scene(self):
        steps = (('break_invitation', 'break_invitation', 'eldenmere.playable', 'collecting_route', 'workshop'),
                 ('collect_frame', 'collection', 'eldenmere.playable', 'materials_collected', 'held'),
                 ('home_welcome', 'home', 'liam_house', 'materials_home', 'home'),
                 ('snack', 'home', 'liam_house', 'rested', 'home'),
                 ('paper_practice', 'paper', 'liam_house', 'paper_tried', 'home'),
                 ('brothers', 'paper', 'liam_house', 'brothers_spoken', 'home'),
                 ('liam_questions', 'paper', 'liam_house', 'home_break_done', 'home'),
                 ('sanctuary_welcome', 'sanctuary', 'sanctuary_hall', 'serene_welcomed', 'home'),
                 ('returning_life', 'sanctuary', 'sanctuary_hall', 'faith_discussed', 'home'),
                 ('remembering', 'sanctuary', 'sanctuary_hall', 'remembrance_discussed', 'home'),
                 ('sanctuary_close', 'sanctuary', 'sanctuary_hall', 'serene_heard', 'home'))
        for kind, station, world, stage, location in steps:
            with self.subTest(scene=kind):
                self.position(station, world);self.scene(kind)
                self.until(lambda: self.c.action is None and self.c.stage == stage)
                self.reload()
                self.assertEqual(self.c.stage, stage)
                self.assertEqual(self.c.rest.frame_location, location)
                self.assertFalse(self.g.social.active)

    def test_prior_repairs_lantern_and_decorations_remain_after_the_break(self):
        self.finish_section()
        self.assertTrue(self.g.mill_quest.mill_restored)
        self.assertFalse(self.g.opening_conclusion.mill_stopped)
        self.assertTrue(self.g.venn_visit.repaired)
        self.assertEqual(self.g.elira_visit.lantern, 'table')
        for prop in self.c.village.surface_props:
            with self.subTest(prop=prop['id']):
                self.assertTrue(self.c.village.surface_prop_visible(prop))
                if 'selected' in prop['states']:
                    self.assertIs(prop['surface'], prop['states']['selected'])

    def test_unearned_future_stage_and_mismatched_objective_prefix_are_rejected(self):
        self.collect();self.g.save_progress();data = json.loads(self.path.read_text())
        for stage, count in (('materials_home', 5), ('serene_heard', 4), ('rested', 6), ('invented_stage', 4)):
            with self.subTest(stage=stage):
                invalid = copy.deepcopy(data);invalid['lantern_quest']['stage'] = stage
                invalid['quests']['quests'][LANTERN]['completed_objectives'] = FIRST_SIX[:count]
                self.assertFalse(type(self.c).valid_journey(invalid))

    def test_new_game_releases_father_serene_and_material_poses(self):
        self.finish_section();self.assertTrue(self.g.begin_journey(False, show_cinematic=False))
        self.assertEqual(self.c.stage, 'idle')
        self.assertEqual(self.g.quests.status(LANTERN), 'locked')
        self.assertIsNone(self.g.play_routines[0].liam_owner)
        self.assertIsNone(self.g.play_routines[0].pending_liam_owner)
        self.assertIn(self.c.father, self.c.liam_home.npcs)
        self.assertFalse(hasattr(self.c.father, 'request_conversation'))
        self.assertEqual(self.c.school.npcs, [])
        self.assertFalse(any(self.c.surface_prop_visible(p) for p in self.c.surface_props))
        self.assertFalse(any(self.c.rest.surface_prop_visible(p) for p in self.c.rest.surface_props))


if __name__ == '__main__':unittest.main()
