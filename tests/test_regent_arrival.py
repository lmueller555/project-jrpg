"""The real mill report commits one arrival without moving its player witness."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from main import Game
from quests import MILL_QUEST, REGENT_QUEST
from regent_arrival import ArrivalAudio, RegentArrival
from test_mill_battle_gameplay import key, click, seed_mill_handoff


def seed_mill_report(game):
    """Prior repair fixture only; the completion dialogue and receipt are real."""
    seed_mill_handoff(game)
    assert game.accept_quest(MILL_QUEST)
    for record in game.quests.definitions[MILL_QUEST]['objectives']:
        if record['id'] != 'report':assert game.quests.complete_objective(MILL_QUEST, record['id'])
    assert game.mill_quest.restore({'version':1,'inspected':['mechanism','race','intake'],
        'prepared':True,'spell_done':True,'encouraged':True,'restored':True,
        'verified':True,'resolved':False})
    game.world = game.town
    preferred = game.mill_quest.points['halden_resolution']
    point = next((pygame.Vector2(preferred)+offset for offset in ((0,0),(0,12),(12,0),(-12,0),(0,-12),(24,0))
                  if game.town.can_stand(pygame.Vector2(preferred)+offset)), None)
    assert point is not None
    game.player.position.update(point)
    game.camera.reset()
    game.quest_ui.reset();game.quests.drain_events()
    assert game.save_progress()


def acknowledge_report(game):
    assert game.mill_quest._speak('resolution', game.mill_quest._resolve)
    for _ in range(100):
        if not game.social.active:break
        key(game, pygame.K_SPACE)
    assert not game.social.active
    assert game.regent_arrival.state == 'pending'


class RegentArrivalTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='regent-arrival-')
        self.addCleanup(directory.cleanup);self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'
        self.g = self.game();seed_mill_report(self.g)

    def tearDown(self):pygame.quit()

    def game(self, title=False, size=(960,640)):
        game = Game(fullscreen=False, start_on_title=title, window_size=size,
                    save_path=self.path, settings_path=self.directory/'settings.json')
        game.audio.set_effects(0);pygame.event.clear()
        return game

    def start(self):
        acknowledge_report(self.g)
        self.g.update(.05,(0,0),False)
        self.assertTrue(self.g.regent_arrival.active)
        return self.g.regent_arrival

    def reach(self, shot):
        scene = self.g.regent_arrival
        for _ in range(3000):
            if scene.shot == shot:return scene
            if scene.dialogue is not None:key(self.g, pygame.K_SPACE)
            self.g.update(.1,(0,0),False)
        self.fail(('Did not reach arrival shot',shot,scene.shot))

    def test_unread_or_cancelled_report_cannot_request_arrival_or_reward(self):
        self.assertTrue(self.g.mill_quest._speak('resolution',self.g.mill_quest._resolve))
        key(self.g,pygame.K_SPACE)
        self.assertEqual(self.g.regent_arrival.state,'waiting')
        self.assertNotEqual(self.g.quests.status(MILL_QUEST),'completed')
        self.g.social.cancel_script()
        self.assertEqual(self.g.regent_arrival.state,'waiting')
        self.assertEqual(self.g.quests.status(REGENT_QUEST),'locked')
        self.assertFalse(self.g.regent_arrival.request())

    def test_report_receipt_and_completed_mill_are_saved_together(self):
        acknowledge_report(self.g)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['regent_arrival'],{'version':1,'state':'pending'})
        self.assertEqual(self.g.quests.status(MILL_QUEST),'completed')
        self.assertEqual(self.g.quests.status(REGENT_QUEST),'available')
        self.assertEqual(saved['regent_quest']['stage'],'idle')
        self.assertTrue(RegentArrival.valid_journey(saved))
        self.assertNotIn(self.g.regent_quest.aldric,self.g.town.npcs)
        self.assertFalse(self.g.regent_arrival.request())

    def test_skip_preserves_player_and_repair_and_reveals_caravan_without_accepting(self):
        scene = self.start()
        before = (self.g.world,tuple(self.g.player.position),self.g.inventory.to_dict(),set(self.g.social.flags))
        click(self.g,scene.skip_rect.center)
        self.assertFalse(scene.active);self.assertEqual(scene.state,'seen')
        self.assertEqual(scene.finished_reason,'skipped')
        self.assertEqual((self.g.world,tuple(self.g.player.position),self.g.inventory.to_dict(),set(self.g.social.flags)),before)
        self.assertTrue(self.g.mill_quest.restored)
        self.assertEqual(self.g.quests.status(REGENT_QUEST),'available')
        self.assertEqual(self.g.regent_quest.stage,'idle')
        self.assertIn(self.g.regent_quest.aldric,self.g.town.npcs)
        self.assertLess(self.g.regent_quest.aldric.position.distance_to(self.g.regent_quest.points['aldric_arrival']),45)
        self.assertEqual(json.loads(self.path.read_text())['regent_arrival']['state'],'seen')
        self.assertFalse(scene.finish('skipped'))

    def test_direct_travel_api_is_blocked_until_arrival_finishes(self):
        scene = self.start()
        link = next(link for link in self.g.town.data['world_links'] if link['id']=='town_to_upstream')
        self.g.player.position.update(link['position']);self.g.transfer_cooldown=0
        self.assertTrue(self.g.household_action)
        self.assertFalse(self.g.travel_link(link))
        self.assertIs(self.g.world,self.g.town)
        scene.finish('skipped')
        self.assertFalse(self.g.household_action)
        self.assertTrue(self.g.travel_link(link))
        self.assertIs(self.g.world,self.g.mill_quest.upstream)

    def test_skip_while_paused_resumes_world_music_and_stops_owned_effects(self):
        scene = self.start();key(self.g,pygame.K_ESCAPE)
        self.assertTrue(scene.paused)
        click(self.g,scene.skip_rect.center)
        self.assertFalse(scene.paused);self.assertFalse(self.g.music.paused)
        self.assertEqual(self.g.music.desired_track,'eldenmere')
        self.assertEqual(scene.audio.channels,[])

    def test_pending_reload_replays_from_start_without_repeating_reward(self):
        scene = self.start();self.reach('locals')
        inventory = self.g.inventory.to_dict();position = tuple(self.g.player.position)
        self.assertTrue(self.g.save_progress())
        loaded = self.game(title=True)
        self.assertTrue(loaded.has_saved_journey)
        self.assertTrue(loaded.begin_journey(True))
        self.assertTrue(loaded.regent_arrival.active)
        self.assertEqual(loaded.regent_arrival.shot,'mill_close')
        self.assertEqual(loaded.regent_arrival.dialogue_index,0)
        self.assertEqual(loaded.inventory.to_dict(),inventory)
        self.assertEqual(tuple(loaded.player.position),position)
        self.assertEqual(loaded.quests.status(MILL_QUEST),'completed')
        self.assertEqual(loaded.quests.status(REGENT_QUEST),'available')

    def test_legacy_completed_journey_migrates_seen_without_playback(self):
        self.start();self.g.regent_arrival.finish('skipped')
        data = json.loads(self.path.read_text());data.pop('regent_arrival')
        self.path.write_text(json.dumps(data))
        loaded = self.game(title=True)
        self.assertTrue(loaded.has_saved_journey)
        self.assertTrue(loaded.begin_journey(True))
        self.assertEqual(loaded.regent_arrival.state,'seen')
        self.assertFalse(loaded.regent_arrival.active)
        self.assertEqual(loaded.quests.status(REGENT_QUEST),'available')
        self.assertIn(loaded.regent_quest.aldric,loaded.town.npcs)

    def test_new_game_resets_pending_and_does_not_reuse_receipt(self):
        self.start()
        self.assertTrue(self.g.begin_journey(False,show_cinematic=False))
        self.assertEqual(self.g.regent_arrival.state,'waiting')
        self.assertFalse(self.g.regent_arrival.active)
        self.assertEqual(self.g.quests.status(MILL_QUEST),'locked')

    def test_saved_seen_journey_does_not_replay(self):
        self.start();self.g.regent_arrival.finish('skipped')
        loaded = self.game(title=True);loaded.begin_journey(True)
        self.assertFalse(loaded.regent_arrival.active)
        self.assertEqual(loaded.regent_arrival.state,'seen')

    def test_world_clocks_and_all_residents_freeze_while_reading(self):
        scene = self.start();self.reach('gate_greeting')
        self.g.update(.5,(0,0),False)
        before = (self.g.elapsed_ms,tuple(self.g.player.position),
                  [(id(n),tuple(n.position)) for n in self.g.persistent_npcs],self.g.mill_quest.mira.position.copy())
        self.g.update(20,(1,1),True)
        after = (self.g.elapsed_ms,tuple(self.g.player.position),
                 [(id(n),tuple(n.position)) for n in self.g.persistent_npcs],self.g.mill_quest.mira.position.copy())
        self.assertEqual(before,after)
        self.assertEqual(scene.dialogue_index,0)
        self.assertEqual(self.g.music.desired_track,'eldenmere')

    def test_escape_and_focus_pause_cinematic_and_music_without_world_menu(self):
        scene = self.start();self.g.update(.2,(0,0),False)
        key(self.g,pygame.K_ESCAPE);self.assertTrue(scene.paused)
        before = (scene.elapsed,scene.phase_time)
        self.g.update(1,(0,0),False)
        self.assertEqual((scene.elapsed,scene.phase_time),before)
        self.assertTrue(self.g.music.paused);self.assertFalse(self.g.pause.is_open)
        key(self.g,pygame.K_ESCAPE);self.assertFalse(scene.paused)
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST));self.g.handle_events()
        self.g.update(1,(0,0),False)
        self.assertEqual((scene.elapsed,scene.phase_time),before)
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED));self.g.handle_events()
        self.g.update(.2,(0,0),False)
        self.assertGreater(scene.elapsed,before[0]);self.assertFalse(self.g.music.paused)

    def test_event_batch_advances_only_one_page_and_ignores_repeat(self):
        scene = self.start();self.reach('gate_greeting');self.g.update(.5,(0,0),False)
        for _ in range(3):pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE,repeat=False))
        self.g.handle_events()
        self.assertEqual((scene.dialogue_index,scene.page_index),(1,0))
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE,repeat=True));self.g.handle_events()
        self.assertEqual((scene.dialogue_index,scene.page_index),(1,0))

    def test_queued_skip_click_cannot_open_map_pause_or_advance_world_dialogue(self):
        scene = self.start()
        scale = min(self.g.window.get_width()//480,self.g.window.get_height()//320)
        point = tuple(round(n*scale) for n in scene.skip_rect.center)
        for event in [pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point),
                      pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=point),
                      pygame.event.Event(pygame.KEYDOWN,key=pygame.K_m,repeat=False),
                      pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,repeat=False),
                      pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e,repeat=False)]:pygame.event.post(event)
        self.assertTrue(self.g.handle_events())
        self.assertFalse(scene.active);self.assertFalse(self.g.map_open)
        self.assertFalse(self.g.pause.is_open);self.assertFalse(self.g.social.active)
        self.assertEqual(self.g.quests.status(REGENT_QUEST),'available')

    def test_all_shots_finish_by_normal_player_input_and_seen_saves_once(self):
        scene = self.start();observed = [];speakers = set()
        for _ in range(4000):
            if not scene.active:break
            if not observed or observed[-1] != scene.shot:
                observed.append(scene.shot)
                self.g.draw()  # Every real plate, actor manifest and phase pose must render.
            if scene.dialogue is not None:
                speakers.add(scene.dialogue['speaker']);key(self.g,pygame.K_SPACE)
            self.g.update(.1,(0,0),False)
        self.assertFalse(scene.active)
        self.assertEqual(observed,[p['id'] for p in scene.data['phases']])
        self.assertTrue({'aldric','guard','local','clerk','serene','tomas'}<=speakers)
        self.assertEqual(scene.finished_reason,'finished')
        self.assertEqual(self.g.quests.status(REGENT_QUEST),'available')
        self.assertTrue(self.g.saved_journey['mill_quest']['restored'])

    def test_native_large_text_and_letterboxed_views_render_shared_profiles(self):
        scene = self.start();self.reach('serene_window')
        self.g.update(.5,(0,0),False)
        for size, text_scale in (((480,320),1.5),((1120,760),1.0)):
            self.g.window = pygame.display.set_mode(size, pygame.RESIZABLE)
            self.g.audio.text_scale = text_scale
            self.g.draw()
            self.assertEqual(scene.caption_layout.portrait_key,'serene')
            self.assertIs(scene.portraits['serene'],self.g.social.portraits['serene'])
            self.assertTrue(pygame.Rect(0,0,480,320).contains(scene.caption_rect))
            self.assertFalse(scene.caption_rect.colliderect(scene.skip_rect))
            self.assertIn('thoughts',' '.join(scene.caption_layout.name_lines))
            self.assertEqual(self.g.to_canvas((-1,-1)),None)

    def test_gate_opens_at_its_hinge_and_remains_visible_beside_clear_passage(self):
        scene=self.start();self.reach('gate_admission');scene._load()
        leaf=scene.scenery['gate']['gate_leaf']
        closed, origin=scene.gate_leaf_frame(leaf)
        closed_world=origin+scene.camera_position
        for _ in range(10):self.g.update(.1,(0,0),False)
        opened, origin=scene.gate_leaf_frame(leaf)
        open_world=origin+scene.camera_position
        self.assertLessEqual(opened.get_width(),closed.get_width()*.1)
        self.assertGreater(opened.get_bounding_rect().height,0)
        self.assertEqual(opened.get_height(),closed.get_height())
        self.assertEqual(open_world,closed_world)
        self.assertLess(open_world.x+opened.get_width(),550)

    def test_moving_frames_keep_foot_anchor_and_valid_loop_dimensions(self):
        scene = self.start();scene._load()
        for identifier, art in scene.actor_art.items():
            self.assertEqual(len(art['anchor']),2)
            for pose, sequence in art['loops'].items():
                self.assertTrue(sequence,(identifier,pose))
                for image, duration in sequence:
                    self.assertEqual(image.get_size(),tuple(art['canvas']))
                    self.assertGreater(duration,0)
            for phase in scene.data['phases']:
                for record in phase['actors']:
                    if record['id']!=identifier:continue
                    for pose in ('pose','before_pose','after_pose'):
                        if pose in record:self.assertIn(record[pose],set(art['poses'])|set(art['loops']))

    def test_cross_validation_rejects_impossible_receipts(self):
        waiting = copy.deepcopy(self.g.saved_journey)
        self.assertTrue(RegentArrival.valid_journey(waiting))
        for bad in ({'version':True,'state':'waiting'}, {'version':1,'state':'bogus'},
                    {'version':1,'state':'waiting','elapsed':8}):
            data = copy.deepcopy(waiting);data['regent_arrival']=bad
            self.assertFalse(RegentArrival.valid_journey(data))
        for state in ('pending','seen'):
            data = copy.deepcopy(waiting);data['regent_arrival']['state']=state
            self.assertFalse(RegentArrival.valid_journey(data))
        self.start();data = copy.deepcopy(self.g.saved_journey)
        data['regent_arrival']['state']='waiting'
        self.assertFalse(RegentArrival.valid_journey(data))
        data = copy.deepcopy(self.g.saved_journey);data['regent_quest']['stage']='assigned'
        self.assertFalse(RegentArrival.valid_journey(data))

    def test_invalid_receipt_disables_continue_without_mutating_title_world(self):
        self.start();data = json.loads(self.path.read_text());data['regent_arrival']['state']='waiting'
        self.path.write_text(json.dumps(data))
        loaded = self.game(title=True)
        self.assertFalse(loaded.has_saved_journey)
        self.assertEqual(loaded.regent_arrival.state,'waiting')
        self.assertEqual(loaded.quests.status(MILL_QUEST),'locked')

    def test_reduced_motion_camera_is_static_without_changing_dialogue(self):
        scene = self.start();self.reach('gate_approach')
        self.g.audio.reduced_motion = True
        position = scene.camera_position.copy()
        self.g.update(.4,(0,0),False)
        self.assertEqual(scene.camera_position,position)
        self.reach('gate_greeting');self.g.update(.5,(0,0),False)
        self.assertIsNotNone(scene.dialogue)

    def test_large_font_shared_portrait_box_paginates_without_expiring(self):
        scene = self.start();self.reach('bridge_damage')
        self.g.update(.5,(0,0),False)
        self.g.audio.text_scale = 1.5
        scene.dialogue_index = 0
        painter = self.g.ui.painter(self.g.ui_surface)
        scene._layout(painter)
        self.assertGreater(len(scene.caption_pages),1)
        self.assertLessEqual(max(len(page) for page in scene.caption_pages),3)
        self.assertTrue(pygame.Rect(0,0,480,320).contains(scene.caption_rect))
        text = scene.dialogue['text']
        self.g.update(100,(0,0),False)
        self.assertEqual(scene.dialogue['text'],text)
        key(self.g,pygame.K_SPACE)
        self.assertEqual(scene.dialogue_index,0)
        self.assertEqual(scene.page_index,1)


class ArrivalAudioOwnershipTests(unittest.TestCase):
    def test_pause_and_cleanup_never_touch_a_channel_reused_by_another_owner(self):
        game = SimpleNamespace(audio=SimpleNamespace(effects_volume=1.))
        audio = ArrivalAudio(game);sound=object();other_sound=object()
        own = MagicMock();own.get_sound.return_value=sound
        reused = MagicMock();reused.get_sound.return_value=other_sound
        audio.mode='travel';audio.channels=[(own,sound),(reused,sound)]
        audio.update(0,'travel',paused=True,gain=.25)
        own.pause.assert_called_once();reused.pause.assert_not_called()
        own.set_volume.assert_called_once_with(.25)
        reused.set_volume.assert_not_called()
        audio.stop()
        own.stop.assert_called_once();reused.stop.assert_not_called()
        self.assertEqual(audio.channels,[])

    def test_muting_effects_stops_only_owned_sound_and_never_global_music(self):
        game = SimpleNamespace(audio=SimpleNamespace(effects_volume=0.))
        audio = ArrivalAudio(game);sound=object();channel=MagicMock()
        channel.get_sound.return_value=sound;audio.channels=[(channel,sound)]
        with patch('pygame.mixer.music.stop') as music_stop, patch('pygame.mixer.stop') as global_stop:
            audio.update(.1,'travel')
        channel.stop.assert_called_once();music_stop.assert_not_called();global_stop.assert_not_called()
        self.assertEqual(audio.channels,[])


if __name__ == '__main__':unittest.main()
