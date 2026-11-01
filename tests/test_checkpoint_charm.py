"""Production guard ownership, exact interruption, contacts and quiet repeats."""
import copy
import gc
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from main import Game
from overworld_travel import OverworldTravel
from checkpoint_charm import (ACTIONS, ART, BENCH, HOMES, ROUTES, SUPPLIES,
    WITNESS, CheckpointCharm, empty_state, progress_state, valid_state)
from tools.capture_lantern_quest import seed_previous_quests


class CheckpointCharmTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.g = self.make_game()
        self.g.opening.restore({'version': 1, 'stage': 'disabled'})
        self.g.world = self.g.overworld_world
        self.g.player.position.update(WITNESS)
        self.c = self.g.world.checkpoint_charm

    def tearDown(self):pygame.quit()

    def make_game(self, title=False):
        game = Game(fullscreen=False, start_on_title=title,
            save_path=self.root/'journey.json', settings_path=self.root/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        return game

    def tick(self, count=1, acknowledge=False):
        for _ in range(count):
            if acknowledge and self.g.social.active:self.g.social.advance()
            self.g.update(1/30, (0, 0), False)
            self.assertTrue(valid_state(self.c.to_dict()), self.c.to_dict())

    def until(self, predicate, acknowledge=False, limit=2400):
        for _ in range(limit):
            if predicate():return
            self.tick(acknowledge=acknowledge)
        self.fail(self.c.to_dict())

    def start(self):
        self.assertEqual(self.c.interaction_hint(self.g), 'E: Watch the checkpoint')
        self.assertTrue(self.g.overworld_travel.interact())

    def frame(self, role):
        actor = self.c.actors[role]
        return pygame.image.tobytes(actor.story_sprite or actor.sprite(self.g.elapsed_ms), 'RGBA')

    def seed_save(self):
        seed_previous_quests(self.g)
        self.g.world = self.g.overworld_world;self.g.player.position.update(WITNESS)
        self.assertTrue(self.g.save_progress())

    def test_full_scene_keeps_duty_existing_actors_closed_gate_and_quiet_repeat(self):
        actors = tuple(self.g.world.npcs);flags = set(self.g.social.flags)
        gates = [(gate['id'], gate['rect'].copy()) for gate in self.g.world.gates]
        self.start();stages = set();seated = False
        with mock.patch.object(self.g.regional_audio, 'play', return_value=False) as play:
            for _ in range(2400):
                self.tick(acknowledge=True);stages.add(self.c.stage)
                self.assertIn(self.c.duty_guard, self.c.actors.values())
                self.assertTrue(self.c.duty_guard.on_duty)
                if self.c.stage == 'banter':
                    seated = True
                    self.assertEqual(tuple(self.c.actors['owner'].position), SUPPLIES)
                    self.assertEqual(tuple(self.c.actors['borrower'].position), BENCH)
                    self.assertEqual(self.c.actors['owner'].facing, 'right')
                if self.c.stage == 'done':break
            self.assertEqual(self.c.stage, 'done')
            keys = [call.args[0].key for call in play.call_args_list
                    if call.args[0].key.startswith('checkpoint_contact_')]
            self.assertEqual(keys, ['checkpoint_contact_'+str(i) for i in range(5)])
            self.assertTrue(self.g.overworld_travel.interact())
            self.until(lambda: self.c.stage == 'done', acknowledge=True)
            self.assertEqual([call.args[0].key for call in play.call_args_list
                              if call.args[0].key.startswith('checkpoint_contact_')], keys)
        self.assertTrue(seated)
        self.assertTrue({'owner_sit', 'owner_stand', 'check', 'borrower_sit', 'borrower_stand'} <= stages)
        self.assertEqual(tuple(self.g.world.npcs), actors)
        self.assertEqual(self.g.social.flags, flags)
        self.assertEqual(self.c.state['read'], 7)
        for role, home in HOMES.items():self.assertEqual(tuple(self.c.actors[role].position), home)
        for gate, (identifier, rect) in zip(self.g.world.gates, gates):
            self.assertEqual((gate['id'], gate['rect']), (identifier, rect))
            self.assertFalse(self.g.world.can_stand(gate['position']))

    def test_every_route_stays_clear_with_witness_and_no_replaced_geometry(self):
        for stage, (role, route) in ROUTES.items():
            start = HOMES[role] if stage in ('owner_to_seat', 'borrower_out') else (
                SUPPLIES if stage == 'owner_home' else BENCH)
            actor = self.c.actors[role]
            for before, after in zip([start]+route, route):
                before = pygame.Vector2(before);after = pygame.Vector2(after)
                count = max(1, int(before.distance_to(after)))
                for i in range(count+1):
                    point = before.lerp(after, i/count)
                    self.assertTrue(self.g.world.can_stand(point, actor.probe_size, actor,
                        self.g.world.probe_rect(self.g.player.position)), (stage, point))

    def test_player_blocks_a_walk_then_guard_resumes_without_sliding(self):
        self.start();owner = self.c.actors['owner']
        self.g.player.position.update(owner.position+(0, 18))
        self.tick(120);point = owner.position.copy()
        self.tick(120)
        self.assertEqual(owner.position, point);self.assertFalse(owner.moving)
        self.assertEqual(self.c.stage, 'owner_to_seat')
        self.g.player.position.update(WITNESS)
        self.until(lambda: self.c.stage == 'owner_sit')

    def test_repeated_e_during_every_movement_and_contact_keeps_scene_ownership(self):
        self.start();tested = set();scripts = set()
        for _ in range(2400):
            stage = self.c.stage
            if stage in ROUTES or stage in ACTIONS:
                self.assertEqual(self.g.overworld_travel.interaction_hint(),
                                 'The guards are changing places')
                before = self.c.to_dict()
                # Exercise the production input route repeatedly in one beat.
                for _ in range(3):
                    self.g.handle_events([pygame.event.Event(pygame.KEYDOWN,
                        key=pygame.K_e, repeat=False), pygame.event.Event(
                        pygame.KEYUP, key=pygame.K_e)])
                    self.assertEqual(self.c.to_dict(), before)
                    self.assertFalse(self.g.social.active)
                    self.assertIsNone(self.g.social.script_identifier)
                tested.add(stage)
            elif self.g.social.active:
                scripts.add(self.g.social.script_identifier)
                self.g.social.advance()
            self.tick()
            if self.c.stage == 'done':break
        self.assertEqual(tested, set(ROUTES)|set(ACTIONS))
        self.assertEqual(self.c.stage, 'done')
        self.assertTrue(scripts)
        self.assertTrue(all(identifier.startswith('checkpoint_borrowed_seat_') for identifier in scripts))

    def test_active_scene_owns_near_guard_input_beyond_bench_and_releases_afterward(self):
        guard = self.c.actors['borrower']
        self.g.player.position.update(guard.position+(28, 0))
        self.assertEqual(self.g.overworld_travel.interaction_hint(), 'E: Speak with the road guard')
        self.assertTrue(self.g.overworld_travel.interact())
        self.assertEqual(self.g.social.script_identifier, 'overworld_guard_north_checkpoint')
        self.g.social.cancel();self.g.overworld_travel.update(0)
        self.g.player.position.update(WITNESS);self.start()
        self.g.player.position.update(guard.position+(28, 0))
        self.assertGreater(self.g.player.position.distance_to(BENCH), 44)
        before = self.c.to_dict()
        self.assertEqual(self.g.overworld_travel.interaction_hint(), 'The guards are changing places')
        self.assertTrue(self.g.overworld_travel.interact())
        self.assertEqual(self.c.to_dict(), before);self.assertFalse(self.g.social.active)
        south = next(actor for actor in self.g.world.npcs
                     if actor.data['id'] == 'road_guard:south_checkpoint:1')
        self.g.player.position.update(south.position+(28, 0))
        self.assertEqual(self.g.overworld_travel.interaction_hint(), 'E: Speak with the road guard')
        self.assertTrue(self.g.overworld_travel.interact())
        self.assertEqual(self.g.social.script_identifier, 'overworld_guard_south_checkpoint')
        self.g.social.cancel();self.g.overworld_travel.update(0)
        self.g.player.position.update(WITNESS)
        self.until(lambda: self.c.stage == 'done', acknowledge=True)
        self.g.player.position.update(guard.position+(28, 0))
        self.assertEqual(self.g.overworld_travel.interaction_hint(), 'E: Speak with the road guard')
        self.assertTrue(self.g.overworld_travel.interact())
        self.assertEqual(self.g.social.script_identifier, 'overworld_guard_north_checkpoint')

    def test_mid_walk_restore_retains_exact_feet_and_authored_frame(self):
        self.start();self.tick(33)
        snapshot = self.c.to_dict();frame = self.frame('owner')
        self.assertTrue(snapshot['moving'])
        self.tick(8);self.c.restore(snapshot)
        self.assertEqual(self.c.to_dict(), snapshot)
        self.assertTrue(self.c.actors['owner'].moving)
        self.assertEqual(self.frame('owner'), frame)

    def test_reset_from_return_walk_restores_original_watch_without_changing_live_idle_talk(self):
        self.start()
        self.until(lambda: self.c.stage == 'owner_home' and self.c.state['moving']
                   and self.c.state['facing'] == 'back', acknowledge=True)
        owner = self.c.actors['owner'];self.assertEqual(owner.facing, 'back')
        self.c.restore()
        self.assertEqual(self.c.to_dict(), empty_state())
        for actor in self.c.actors.values():
            self.assertEqual(actor.facing, actor.watch_facing)
            self.assertIsNone(actor._conversation_started_ms)
            self.assertIsNone(actor.story_sprite)
        owner.begin_conversation('right', self.g.elapsed_ms)
        self.c.update(90, self.g)
        self.assertEqual(owner.facing, 'right')
        self.assertIsNotNone(owner._conversation_started_ms)

    def test_exact_continue_matrix_for_all_scene_stages_route_segments_and_contacts(self):
        self.seed_save();snapshots = {}
        def collect():
            state = self.c.to_dict()
            if state['stage'] in ROUTES and not state['moving']:return
            if state['stage'] in ACTIONS and state['elapsed'] < .2:return
            key = (state['stage'], state['step'], state['contacts'],
                   state['read'], state['repeat_read'])
            if key in snapshots:return
            self.assertTrue(self.g.save_progress())
            raw = self.g.save_store.path.read_bytes()
            self.assertEqual(json.loads(raw)['overworld']['checkpoint_charm'], state)
            # Ambient idle breathing belongs to the world's unsaved renderer
            # clock. Compare it at the same timestamp; scene-owned sprites use
            # the exact controller clocks in the saved snapshot directly.
            timestamp = self.g.elapsed_ms
            frames = {role: pygame.image.tobytes(actor.story_sprite or
                actor.sprite(timestamp), 'RGBA') for role, actor in self.c.actors.items()}
            snapshots[key] = (raw, state, frames, timestamp)
        collect();self.start()
        for _ in range(2400):
            collect()
            if self.c.stage == 'done':break
            self.tick(acknowledge=True)
        self.assertEqual(self.c.stage, 'done')
        self.assertTrue(self.g.overworld_travel.interact())
        for _ in range(20):
            collect()
            if self.c.stage == 'done':break
            self.tick(acknowledge=True)
        self.assertEqual({key[0] for key in snapshots}, set(ROUTES)|set(ACTIONS)|
                         {'idle', 'opening', 'banter', 'closing', 'done', 'repeat'})
        for stage, (_, route) in ROUTES.items():
            self.assertEqual({key[1] for key in snapshots if key[0] == stage}, set(range(len(route))))
        for stage, (_, _, _, _, before) in ACTIONS.items():
            self.assertEqual({key[2] for key in snapshots if key[0] == stage}, {before, before+1})
        for stage, reads in [('opening', {0, 1}), ('banter', {2, 3, 4}), ('closing', {5, 6})]:
            self.assertEqual({key[3] for key in snapshots if key[0] == stage}, reads)
        self.assertEqual({key[4] for key in snapshots if key[0] == 'repeat'}, {0, 1})
        for key, (raw, state, frames, timestamp) in snapshots.items():
            with self.subTest(checkpoint=key):
                self.g.save_store.path.write_bytes(raw)
                resumed = self.make_game(True)
                self.assertTrue(resumed.has_saved_journey, resumed.save_error)
                self.assertEqual(resumed.saved_journey, json.loads(raw))
                self.assertTrue(resumed.begin_journey(True), resumed.save_error)
                controller = resumed.world.checkpoint_charm
                self.assertEqual(controller.to_dict(), state)
                for role, actor in controller.actors.items():
                    self.assertEqual(list(actor.position), state['positions'][role])
                    rendered = actor.story_sprite or actor.sprite(timestamp)
                    self.assertEqual(pygame.image.tobytes(rendered, 'RGBA'), frames[role])
                resumed.music.stop();resumed.regional_audio.stop()
                resumed = controller = None
                gc.collect()

    def test_read_line_stays_read_after_cancel_and_continue_at_seated_guard(self):
        self.seed_save();self.start()
        self.until(lambda: self.c.stage == 'opening' and self.g.social.active)
        first = self.g.social._source_lines[0]['text']
        self.g.social.advance();self.tick()
        self.assertEqual(self.c.state['read'], 1)
        second = self.g.social._source_lines[0]['text'];self.assertNotEqual(first, second)
        self.g.social.cancel();self.tick(3)
        self.assertFalse(self.g.social.active)
        self.assertTrue(self.g.save_progress());snapshot = self.c.to_dict()
        resumed = self.make_game(True)
        self.assertTrue(resumed.has_saved_journey, resumed.save_error)
        self.assertTrue(resumed.begin_journey(True))
        resumed.opening_fade = resumed.transfer_cooldown = 0
        self.g = resumed;self.c = resumed.world.checkpoint_charm
        self.assertEqual(self.c.to_dict(), snapshot)
        self.assertFalse(self.g.social.active)
        self.assertTrue(self.g.overworld_travel.interact())
        self.assertEqual(self.g.social._source_lines[0]['text'], second)

    def test_contacts_resume_once_even_when_muted_then_unmuted(self):
        self.start()
        with mock.patch.object(self.g.regional_audio, 'play', return_value=False) as play:
            self.until(lambda: self.c.stage == 'owner_sit' and self.c.state['contacts'] == 1)
            snapshot = self.c.to_dict();before = self.frame('owner')
            self.c.restore(snapshot);self.assertEqual(self.frame('owner'), before)
            self.g.audio.set_effects(1)
            self.until(lambda: self.c.stage == 'owner_stand', acknowledge=True)
            seat = [call.args[0] for call in play.call_args_list
                    if call.args[0].key == 'checkpoint_contact_0']
            self.assertEqual(len(seat), 1)
            self.assertEqual(seat[0].point(), BENCH)

    def test_first_internal_checkpoint_after_long_idle_loads_without_healing_save(self):
        self.seed_save()
        self.tick(2700)
        self.assertEqual(self.c.state['clock'], 0)
        path = self.g.save_store.path;first = []
        write = self.g.save_store.write
        def capture(payload):
            result = write(payload)
            if not first:first.append((path.read_bytes(), self.c.to_dict(), self.frame('owner')))
            return result
        with mock.patch.object(self.g.save_store, 'write', side_effect=capture) as saved:
            self.start()
        self.assertEqual(saved.call_count, 1)
        raw, snapshot, frame = first[0];payload = json.loads(raw)
        self.assertEqual(payload['overworld']['checkpoint_charm'], snapshot)
        self.assertTrue(OverworldTravel.valid_journey(payload))
        self.assertTrue(valid_state(snapshot));self.assertLess(snapshot['clock'], 60)
        self.assertEqual(path.read_bytes(), raw)
        resumed = self.make_game(True)
        self.assertTrue(resumed.has_saved_journey, resumed.save_error)
        self.assertEqual(resumed.saved_journey, payload)
        self.assertTrue(resumed.begin_journey(True))
        resumed.opening_fade = resumed.transfer_cooldown = 0
        self.g = resumed;self.c = resumed.world.checkpoint_charm
        self.assertEqual(self.c.to_dict(), snapshot)
        self.assertEqual(self.frame('owner'), frame)

    def test_strict_snapshot_validation_and_progress_projection(self):
        good = empty_state()
        for field, bad in [('stage', []), ('stage', {}), ('stage', 'missing'),
                           ('facing', []), ('contacts', 1), ('clock', 90),
                           ('elapsed', float('nan')), ('read', True)]:
            with self.subTest(field=field, bad=bad):
                value = copy.deepcopy(good);value[field] = bad
                self.assertFalse(valid_state(value))
        self.start();self.tick(12);good = self.c.to_dict()
        bad = copy.deepcopy(good);bad['positions']['owner'][0] += 1
        self.assertFalse(valid_state(bad))
        bad = copy.deepcopy(good);bad['positions']['borrower'][0] -= 1
        self.assertFalse(valid_state(bad))
        progress = progress_state(good);good['clock'] += .2
        good['positions']['owner'][1] += .2
        self.assertEqual(progress_state(good), progress)

    def test_synthetic_world_without_designated_guards_is_inert(self):
        controller = CheckpointCharm(SimpleNamespace(npcs=[]))
        self.assertFalse(controller.enabled);self.assertEqual(controller.actors, {})
        self.assertTrue(valid_state(controller.to_dict()))
        self.assertFalse(controller.interaction_hint(self.g))
        self.assertFalse(controller.interact(self.g))
        controller.update(90, self.g)
        self.assertEqual(controller.to_dict(), empty_state())

    def test_new_clips_have_real_seated_and_independent_walk_frames(self):
        metadata = json.loads((ART/'animation.json').read_text())
        self.assertEqual(metadata['canvas'], [40, 44])
        directions = ('front', 'back', 'left', 'right')
        for direction in directions:
            frames = self.c.clips['walk_'+direction]['frames']
            self.assertEqual(len(frames), 4)
            self.assertEqual(len({pygame.image.tobytes(frame['image'], 'RGBA') for frame in frames}), 4)
        left = self.c.clips['walk_left']['frames'][0]['image']
        right = self.c.clips['walk_right']['frames'][0]['image']
        self.assertNotEqual(pygame.image.tobytes(pygame.transform.flip(left, True, False), 'RGBA'),
                            pygame.image.tobytes(right, 'RGBA'))
        sit = self.c.clips['sit_front']['frames'][0]['image']
        self.assertLess(sit.get_bounding_rect().height,
                        self.c.clips['walk_front']['frames'][0]['image'].get_bounding_rect().height)


if __name__ == '__main__':unittest.main()
