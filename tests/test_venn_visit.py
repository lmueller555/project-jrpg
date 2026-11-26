"""Play direct tools and failed-magick fallback, with live dialogue and saves."""
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
from npc_routines import find_path
from quests import OPENING_QUEST as QUEST
from venn_visit import VennVisit, PIN_APPROACH, CHANNEL_APPROACH


class VennGameplayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'journey.json'
        self.game = self.new_game();self.visit = self.game.venn_visit

    def tearDown(self):pygame.quit()

    def new_game(self, title=False):
        game = main.Game(fullscreen=False, start_on_title=title, save_path=self.path,
                         settings_path=Path(self.directory.name)/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0);pygame.event.clear()
        return game

    def wait(self, seconds=1):
        for _ in range(round(seconds*60)):self.game.update(1/60, (0, 0), False)

    def key(self, key):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False))
        self.assertTrue(self.game.handle_events())

    def click(self, point=(2, 2)):
        w, h = self.game.window.get_size();scale = max(1, min(w//480, h//320))
        pos = (round((w-480*scale)/2+point[0]*scale), round((h-320*scale)/2+point[1]*scale))
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=pos))
        self.assertTrue(self.game.handle_events())

    def read_dialogue(self):
        for _ in range(80):
            if not self.game.social.active:return
            self.assertFalse(self.game.social.choosing);self.click()
        self.fail('Unfinished dialogue')

    def ready(self):
        self.game.accept_quest(QUEST);self.game.quests.complete_objective(QUEST, 'halden')
        self.game._sync_inventory();self.game.halden_visit.restore()
        self.game.world = self.visit.home;self.game.player.position.update(300, 218)
        self.game.player.facing = 'back';self.game.transfer_cooldown = 0
        self.game.update(0, (0, 0), False)

    def deliver(self):
        self.ready();self.assertTrue(self.game.social.start(self.visit.family['father']))
        self.read_dialogue();self.wait();self.assertTrue(self.visit.delivered)

    def inspect(self, key):
        self.game.world = self.game.town
        self.game.player.position.update(PIN_APPROACH if key=='pin' else CHANNEL_APPROACH)
        self.key(pygame.K_e);self.assertEqual(self.game.social.script_identifier, 'venn_'+key)
        self.read_dialogue();self.assertIn(key, self.visit.inspected)

    def choice(self):
        self.game.world = self.game.town;self.game.player.position.update(PIN_APPROACH)
        self.key(pygame.K_e)
        for _ in range(30):
            if self.game.social.choosing:return
            self.click()
        self.fail('No repair choices')

    def choose(self, method):
        self.choice();index = 0 if method=='tools' else 1
        self.click(self.game.social.choice_rects[index].center)
        self.assertEqual(self.visit.method, method);self.assertEqual(self.visit.action, 'repair')

    def finish_repair(self):
        states = set()
        for _ in range(900):
            if self.game.social.script_identifier=='venn_magicks_failed':self.read_dialogue()
            if self.visit.action is None:break
            states.add(self.visit.phase);self.game.update(1/60, (0, 0), False)
            self.assertTrue(self.game.town.can_stand(self.game.player.position))
        self.assertIsNone(self.visit.action);self.assertTrue(self.visit.repaired)
        self.assertFalse(hasattr(self.game.player, 'story_sprite'))
        self.assertEqual(self.game.quests.objective_status(QUEST, 'venn'), 'active')
        return states

    def walk(self, goal, new_scene=None):
        world = self.game.world
        route = find_path(world, self.game.player.position, goal, world.probe_size, None)
        self.assertIsNotNone(route, (world.data['id'], tuple(self.game.player.position), goal))
        for corner in route:
            for _ in range(900):
                if self.game.world is not world:
                    self.assertEqual(self.game.world.data['id'], new_scene);return
                delta = pygame.Vector2(corner)-self.game.player.position
                if delta.length()<.03:break
                self.game.update(min(1/30, delta.length()/72), delta, False)
                self.assertTrue(self.game.world is not world or world.can_stand(self.game.player.position))
            else:self.fail(('Walk stalled', world.data['id'], corner))
        if new_scene:
            door = next(d for d in world.doors if pygame.Vector2(d.data['anchor']).distance_to(goal)<2)
            direction = (0, -1) if door.data['entry_side']=='north' else (0, 1)
            for _ in range(90):
                if self.game.world is not world:break
                self.game.update(1/60, direction, False)
            self.assertEqual(self.game.world.data['id'], new_scene)

    def return_and_resolve(self):
        self.walk((1248, 726), 'venn');self.walk((300, 218))
        self.assertEqual(self.game.social.script_identifier, 'venn_resolution')
        self.read_dialogue();self.assertTrue(self.visit.completed)

    def finish_elira(self):
        from test_elira_visit import EliraGameplayTests
        helper = EliraGameplayTests();helper.game = self.game;helper.visit = self.game.elira_visit
        self.game.world = helper.visit.home;self.game.player.position.update(210, 224)
        self.game.social.blocked.clear();self.assertTrue(self.game.social.start(helper.visit.elira))
        self.read_dialogue();self.wait();helper.retrieve();helper.place();helper.resolve()
        self.assertTrue(helper.visit.completed)

    def test_family_present_with_child_resting_and_three_distinct_portraits(self):
        self.assertEqual(len(self.visit.family), 3)
        for role, actor in self.visit.family.items():
            self.assertEqual(sum(actor in w.npcs for w in self.game.scenes.values()), 1)
            self.assertIn('venn_'+role, self.game.social.portraits)
            self.assertEqual(len(actor.idles), 4)
        child = self.visit.family['child']
        self.assertEqual(child.story_position, (60, 112));self.assertEqual(child.blocker.size, (0, 0))
        self.game.world = self.visit.home;self.game.player.position.update(100, 138)
        self.game.update(1/60, (-1, 0), False)
        self.assertTrue(self.game.social.active)
        self.assertEqual(self.game.social.resolve_speaker(), child)
        self.assertLess(self.game.social.anchor_position()[0], child.position.x)
        before = self.game.quests.to_dict();self.read_dialogue();self.assertEqual(before, self.game.quests.to_dict())
        self.game.camera.reset();self.game.draw()

    def test_queued_visit_cannot_inspect_choose_repair_or_consume_supplies(self):
        self.game.accept_quest(QUEST);self.game._sync_inventory()
        before = self.game.inventory.to_dict();self.game.player.position.update(PIN_APPROACH)
        self.key(pygame.K_e);self.wait()
        self.assertEqual(before, self.game.inventory.to_dict())
        self.assertEqual(self.visit.inspected, set());self.assertFalse(self.visit._select_method('tools'))
        self.assertFalse(self.visit.repaired);self.assertEqual(self.game.quests.objective_status(QUEST, 'venn'), 'queued')

    def test_actual_door_and_parent_proximity_start_live_family_exchange(self):
        self.ready();self.game.world = self.game.town;self.game.player.position.update(1248, 754)
        self.walk((1248, 726), 'venn');self.walk((300, 218))
        self.assertEqual(self.game.social.script_identifier, 'venn_arrival')
        self.assertIs(self.game.social.resolve_speaker(), self.visit.family['mother'])
        previous = self.game.player.position.copy();self.game.update(.08, (1, 0), False)
        self.assertGreater(self.game.player.position.x, previous.x)
        self.assertTrue(self.game.social.active);self.assertFalse(self.game.household_action)

    def test_unread_arrival_never_hands_off_items(self):
        self.ready();self.game.social.start(self.visit.family['father'])
        self.game.player.position.update(360, 218);self.game.update(0, (0, 0), False)
        self.assertFalse(self.game.social.active);self.assertIsNone(self.visit.action)
        self.assertEqual(self.game.inventory.quantity('venn_supplies'), 1)
        self.assertFalse(self.visit.delivered)

    def test_supplies_transfer_at_contact_once_without_finishing_gate(self):
        self.ready();self.game.social.start(self.visit.family['father']);self.read_dialogue()
        self.wait(.3);self.assertEqual(self.game.inventory.quantity('venn_supplies'), 1)
        self.wait(.2);self.assertEqual(self.game.inventory.quantity('venn_supplies'), 0)
        self.assertEqual(self.game.inventory.quantity('elira_supplies'), 1)
        self.assertTrue(self.visit.delivered);self.assertFalse(self.visit.repaired)
        self.assertFalse(self.game.deliver_quest_item(QUEST, 'venn', 'venn'))
        self.wait();self.assertTrue(self.visit.surface_prop_visible(self.visit.surface_props[0]))

    def test_borrowed_lantern_stays_visible_until_set_down_before_other_hand_actions(self):
        self.ready();elira = self.game.elira_visit
        self.game.deliver_quest_item(QUEST, 'elira', 'elira')
        elira.restore({'version': 1, 'lantern': 'carried'})
        self.assertTrue(self.game.social.start(self.visit.family['father']))
        self.assertEqual(self.game.social.script_identifier, 'venn_hands_full')
        self.read_dialogue();self.wait(.2)
        self.assertFalse(self.visit.delivered);self.assertEqual(elira.lantern, 'carried')
        self.assertIsNotNone(getattr(self.game.player, 'story_sprite', None))
        self.assertFalse(self.visit._select_method('tools'))
        self.assertIsNone(self.visit.action);self.assertEqual(self.game.inventory.quantity('venn_supplies'), 1)

    def test_both_inspections_required_and_unread_inspection_does_not_count(self):
        self.deliver();self.inspect('pin')
        self.assertFalse(self.visit._select_method('tools'))
        self.game.player.position.update(CHANNEL_APPROACH);self.key(pygame.K_e)
        self.game.player.position.update(1380, 694);self.game.update(0, (0, 0), False)
        self.assertEqual(self.visit.inspected, {'pin'});self.assertFalse(self.visit.repaired)
        self.inspect('channel');self.assertEqual(self.visit.inspected, {'pin', 'channel'})

    def test_choice_requires_deliberate_click_and_walkaway_discards_callback(self):
        self.deliver();self.inspect('channel');self.inspect('pin');self.choice()
        for key in (pygame.K_SPACE, pygame.K_e):self.key(key)
        self.click((2, 2));self.assertIsNone(self.visit.method);self.assertTrue(self.game.social.choosing)
        self.game.player.position.update(1380, 670);self.game.update(0, (0, 0), False)
        self.assertFalse(self.game.social.locked);self.assertIsNone(self.visit.method)
        self.assertIsNone(self.game.social._choice_callback);self.assertIsNone(self.visit.action)

    def test_large_text_letterboxed_response_selects_exact_method(self):
        self.deliver();self.inspect('pin');self.inspect('channel')
        self.game.window = pygame.display.set_mode((1440, 810));self.game.audio.set_text_scale(1.5)
        self.choice();self.game.draw();rects = self.game.social.choice_rects
        self.assertEqual(len(rects), 2)
        for rect in rects:self.assertTrue(pygame.Rect(0, 0, 480, 320).contains(rect))
        self.click(rects[1].center);self.assertEqual(self.visit.method, 'magicks')
        self.assertFalse(self.game.social.locked);self.assertEqual(self.visit.phase, 'align_pin')

    def test_both_methods_animate_real_work_then_require_return_conversation(self):
        for method in ('tools', 'magicks'):
            with self.subTest(method=method):
                if method=='magicks':self.game = self.new_game();self.visit = self.game.venn_visit
                self.deliver();self.inspect('pin');self.inspect('channel');self.choose(method)
                states = self.finish_repair()
                self.assertIn('work_pin', states);self.assertIn('open', states)
                self.assertIn('clear_channel', states)
                if method=='magicks':
                    self.assertIn('attempt',states);self.assertIn('fizzle',states)
                    self.assertTrue(self.visit.magicks_failed)
                self.assertEqual(self.game.quests.objective_status(QUEST, 'elira'), 'active')
                self.return_and_resolve()
                self.assertEqual(self.game.quests.status(QUEST), 'active')
                self.assertIn('CH01_MQ01_VENN_METHOD_'+method.upper(), self.game.social.flags)

    def test_repair_preserves_cached_ground_collision_and_restores_downstream_flow(self):
        self.deliver();self.inspect('pin');self.inspect('channel')
        ground = self.game.town.ground[0]
        before = hashlib.sha256(pygame.image.tobytes(ground, 'RGB')).hexdigest()
        collision = self.game.town.blocked.count();self.choose('tools');self.finish_repair();self.wait(9)
        self.assertEqual(hashlib.sha256(pygame.image.tobytes(ground, 'RGB')).hexdigest(), before)
        self.assertEqual(self.game.town.blocked.count(), collision)
        self.assertFalse(self.game.town.can_stand((1452, 694)))
        self.assertTrue(all(self.visit.surface_prop_visible(p) for p in self.visit.water_props))
        self.assertEqual(self.visit._gate_frame(0)[0], 'idle_open')
        self.assertFalse(self.visit.surface_prop_visible(self.visit.surface_props[3]))
        self.assertFalse(any(self.visit.surface_prop_visible(p) for p in self.visit.surface_props if p['id']=='venn_held_water'))
        self.assertIn('venn_spillway', {p['id'] for p in self.visit.water_props})

    def test_choice_and_repair_pause_safely_under_inventory(self):
        self.deliver();self.inspect('pin');self.inspect('channel');self.choice()
        self.key(pygame.K_i);self.key(pygame.K_SPACE)
        self.assertIsNone(self.visit.method);self.key(pygame.K_i)
        self.click(self.game.social.choice_rects[0].center);self.wait(.3)
        phase = self.visit.phase;clock = self.visit.phase_time
        self.key(pygame.K_ESCAPE);self.game.update(10, (0, 1), False)
        self.assertEqual((self.visit.phase, self.visit.phase_time), (phase, clock))
        self.key(pygame.K_ESCAPE);self.finish_repair()

    def test_walkaway_resolution_keeps_repair_without_finishing_objective(self):
        self.deliver();self.inspect('pin');self.inspect('channel');self.choose('magicks');self.finish_repair()
        self.walk((1248, 726), 'venn');self.walk((300, 218))
        self.assertEqual(self.game.social.script_identifier, 'venn_resolution')
        self.game.player.position.update(360, 218);self.game.update(0, (0, 0), False)
        self.assertFalse(self.game.social.active);self.assertTrue(self.visit.repaired)
        self.assertEqual(self.game.quests.objective_status(QUEST, 'venn'), 'active')
        self.game.player.position.update(300, 218);self.game.social.blocked.clear()
        self.game.social.start(self.visit.family['father']);self.read_dialogue();self.assertTrue(self.visit.completed)

    def test_reload_inspections_interrupted_repair_and_repaired_boundary(self):
        self.deliver();self.inspect('pin')
        for stage in ('inspection', 'interrupted', 'repaired'):
            if stage=='interrupted':self.inspect('channel');self.choose('tools');self.wait(.5)
            if stage=='repaired':self.choose('magicks');self.finish_repair()
            self.game.save_progress();restored = self.new_game(True)
            self.assertTrue(restored.begin_journey(True), stage)
            v = restored.venn_visit
            self.assertEqual(v.inspected, {'pin'} if stage=='inspection' else {'pin', 'channel'})
            self.assertEqual(v.repaired, stage=='repaired');self.assertIsNone(v.action)
            self.assertTrue(restored.world.can_stand(restored.player.position))
            self.assertEqual(restored.inventory.quantity('venn_supplies'), 0)
            self.assertEqual(sum(v.family['father'] in w.npcs for w in restored.scenes.values()), 1)
            if stage=='repaired':self.assertTrue(all(v.surface_prop_visible(p) for p in v.water_props))
            self.game = restored;self.visit = v;self.game.opening_fade = 0

    def test_either_household_order_unlocks_report_without_automatic_turn_in(self):
        for elira_first in (True, False):
            with self.subTest(elira_first=elira_first):
                if not elira_first:self.game = self.new_game();self.visit = self.game.venn_visit
                self.ready()
                if elira_first:self.finish_elira()
                self.game.world = self.visit.home;self.game.player.position.update(300, 218)
                self.game.social.blocked.clear();self.game.social.start(self.visit.family['father']);self.read_dialogue();self.wait()
                self.inspect('pin');self.inspect('channel');self.choose('tools');self.finish_repair();self.return_and_resolve()
                if not elira_first:self.finish_elira()
                self.assertEqual(self.game.quests.status(QUEST), 'ready')
                self.assertEqual(self.game.quests.marker_for('mother_serene'), '?')
                self.assertEqual(self.game.inventory.entries('key_items'), [])

    def test_old_completed_saves_migrate_without_inventing_repair_method(self):
        self.ready();self.game.quests.complete_objective(QUEST, 'venn');self.game.save_progress()
        data = json.loads(self.path.read_text());data.pop('venn_visit');self.path.write_text(json.dumps(data))
        restored = self.new_game(True);self.assertTrue(restored.begin_journey(True))
        v = restored.venn_visit;self.assertTrue(v.repaired);self.assertIsNone(v.method)
        self.assertEqual(v.inspected, {'pin', 'channel'})
        self.assertEqual(restored.inventory.quantity('venn_supplies'), 0)

    def test_invalid_snapshots_and_cross_quest_progress_leave_save_untouched(self):
        self.deliver();self.inspect('pin');self.game.save_progress()
        good = json.loads(self.path.read_text())
        for record in [dict(version=True, inspected=[], method=None, repaired=False),
                       dict(version=1, inspected=['pin', 'pin'], method=None, repaired=False),
                       dict(version=1, inspected=['pin'], method='tools', repaired=True)]:
            self.assertFalse(VennVisit.valid_snapshot(record))
        bad = copy.deepcopy(good);bad['inventory']['deliveries'].remove(QUEST+'/venn')
        bad['inventory']['items']['venn_supplies'] = 1;raw = json.dumps(bad);self.path.write_text(raw)
        broken = self.new_game(True);self.assertFalse(broken.has_saved_journey)
        self.assertEqual(self.path.read_text(), raw)

    def test_new_game_clears_repair_supplies_and_visual_pose(self):
        self.deliver();self.inspect('pin');self.inspect('channel');self.choose('tools');self.wait(.5)
        self.assertTrue(self.game.begin_journey(False))
        self.assertEqual(self.visit.inspected, set());self.assertIsNone(self.visit.method)
        self.assertFalse(self.visit.repaired);self.assertFalse(self.visit.delivered);self.assertIsNone(self.visit.action)
        self.assertEqual(self.visit._gate_frame(0)[0], 'idle_jammed')
        self.assertEqual(self.game.quests.status(QUEST), 'available')


if __name__=='__main__':unittest.main()
