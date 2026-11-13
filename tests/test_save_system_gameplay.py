"""Real Game save/load, autosave events, defeat and isolated playtests."""
from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame

from main import Game
from quest_playtest import prepare_quest
from save_library import SaveLibrary


class SaveSystemGameplayTests(unittest.TestCase):
    def setUp(self):
        folder=TemporaryDirectory();self.addCleanup(folder.cleanup);self.addCleanup(pygame.quit)
        self.root=Path(folder.name)
        self.path=self.root/'journey.json'
        self.game=Game(window_size=(960,640),fullscreen=False,start_on_title=False,
                       save_path=self.path,settings_path=self.root/'settings.json')
        self.game.audio.set_music(0);self.game.audio.set_effects(0)
        self.game.opening_fade=self.game.transfer_cooldown=0
        pygame.event.clear()

    def autos(self, game=None):
        g=game or self.game
        return g.saves.library.autos(g.saves.campaign)

    def station(self, world, *, game=None):
        g=game or self.game
        g.world=world
        g.player.position.update(world.data['spawn'])
        g.opening_fade=g.transfer_cooldown=0

    def test_scene_autosave_waits_for_arrival_and_repeated_transfers_do_not_rotate(self):
        g=self.game
        self.station(g._scene_by_id('sanctuary_dining'))
        g.transfer_cooldown=.25
        g.saves.update(.1)
        self.assertEqual(self.autos(),[])
        g.transfer_cooldown=0;g.saves.update(.1)
        self.assertEqual(len(self.autos()),1)
        self.assertEqual(self.autos()[0]['payload']['player']['scene'],'sanctuary_dining')
        for _ in range(4):
            self.station(g.town);g.saves.update(.2)
            self.station(g._scene_by_id('sanctuary_dining'));g.saves.update(.2)
        g.saves.update(61)
        self.assertEqual(len(self.autos()),1)
        self.station(g.town);g.saves.update(.1)
        self.assertEqual(len(self.autos()),2)

    def test_no_elapsed_time_autosaves_and_pause_focus_do_not_spend_scene_cooldown(self):
        g=self.game
        self.station(g._scene_by_id('sanctuary_dining'));g.saves.update(.1)
        deadline=g.saves.scene_deadline
        clock=g.saves.clock
        g.pause.open();g.saves.update(100)
        g.pause.close();g._music_focused=False;g.saves.update(100)
        self.assertEqual(g.saves.clock,clock)
        self.assertEqual(g.saves.scene_deadline,deadline)
        g._music_focused=True;g.saves.update(100)
        self.assertEqual(len(self.autos()),1)

    def test_battle_autosave_bypasses_scene_throttle_and_keeps_manual_slot(self):
        g=self.game
        self.assertTrue(g.saves.manual(1))
        manual=deepcopy(g.saves.library.manual(1))
        self.station(g._scene_by_id('sanctuary_dining'));g.saves.update(.1)
        g.saves.request_battle('test:reward')
        g.saves.update(.1)
        self.assertEqual(len(self.autos()),2)
        self.assertEqual(self.autos()[0]['metadata']['reason'],'battle')
        g.saves.request_battle('test:reward');g.saves.update(.1)
        self.assertEqual(len(self.autos()),2)
        self.assertEqual(g.saves.library.manual(1),manual)

    def test_blocked_placement_defers_autosave_and_failed_write_retries_without_rotation(self):
        g=self.game
        self.station(g._scene_by_id('sanctuary_dining'))
        with patch.object(g.world,'can_stand',return_value=False):g.saves.update(.1)
        self.assertEqual(self.autos(),[])
        with patch('save_game.os.replace',side_effect=OSError('disk full')):g.saves.update(.1)
        self.assertEqual(self.autos(),[])
        self.assertIsNotNone(g.saves.pending_scene)
        g.saves.update(11)
        self.assertEqual(len(self.autos()),1)

    def test_manual_overwrite_requires_confirmation_and_cancel_preserves_slot(self):
        g=self.game
        self.assertTrue(g.saves.manual(1))
        before=g.saves.library.manual(1)
        g.pause.open();g.save_menu.open('save');g.draw()
        g.save_menu.activate()
        self.assertTrue(g.save_menu.confirming)
        self.assertFalse(g.save_menu.confirm_yes)
        g.save_menu.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN,repeat=False))
        self.assertFalse(g.save_menu.confirming)
        self.assertEqual(g.saves.library.manual(1),before)

    def test_load_restores_slot_and_cooldown_without_creating_an_autosave(self):
        g=self.game
        self.station(g._scene_by_id('sanctuary_dining'));g.saves.update(.1)
        self.assertTrue(g.saves.manual(1))
        saved=g.saves.library.manual(1)
        row=('Slot 1',saved,('manual',1))
        g.inventory.add_many({'potion':1})
        self.station(g.town)
        self.assertTrue(g.saves.load(row))
        self.assertEqual(g.world.data['id'],'sanctuary_dining')
        self.assertEqual(g.inventory.to_dict(),saved['payload']['inventory'])
        self.assertGreater(g.saves.scene_deadline,59)
        g.saves.update(1)
        self.assertEqual(len(self.autos()),1)

    def test_latest_quick_load_skips_corrupt_autosave_payload(self):
        g=self.game
        g.saves.request_battle('one');g.saves.update(.1)
        g.saves.request_battle('two');g.saves.update(.1)
        name=g.saves.library._index(g.saves.campaign)['files'][0]
        file=g.saves.library.root/name
        entry=json.loads(file.read_text());entry['payload']['player']['scene']='invalid.scene'
        file.write_text(json.dumps(entry))
        row=g.saves.latest('auto')
        self.assertTrue(row[1]['metadata']['event'].endswith(':one'))
        self.assertTrue(g.saves.load(row))

    def test_game_over_preserves_all_saves_and_loads_the_last_manual_snapshot(self):
        g=self.game
        self.assertTrue(g.saves.manual(1))
        g.saves.request_battle('safe');g.saves.update(.1)
        g.save_progress()
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        g.player.position.update(g.combat.position+(0,24));g.player.facing='back'
        self.assertTrue(g.combat.interact());g.combat.transition=None
        owner=g.combat
        owner.model.player.hp=0;owner.model.phase='defeat'
        self.assertFalse(g.save_progress())
        self.assertTrue(owner._settle())
        self.assertTrue(g.game_over)
        self.assertFalse(g.combat.active)
        g.update(100,(1,0),True);g.draw()
        self.assertFalse(g.save_progress())
        after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(after,before)
        self.assertEqual(g.save_menu.mode,'game_over')
        g.save_menu.activate()
        self.assertFalse(g.game_over)
        self.assertGreater(g.attributes.current_hp,0)
        self.assertFalse(g.combat.active)

    def test_new_game_keeps_old_manual_and_autosave_histories(self):
        g=self.game
        g.saves.manual(1);g.saves.request_battle('one');g.saves.update(.1)
        campaign=g.saves.campaign
        before=deepcopy(g.saves.library.autos(campaign))
        self.assertTrue(g.begin_journey(False,show_cinematic=False))
        self.assertNotEqual(g.saves.campaign,campaign)
        self.assertEqual(g.saves.library.autos(campaign),before)
        self.assertEqual(g.saves.library.manual(1)['metadata']['campaign'],campaign)

    def test_playtest_autosaves_and_loading_never_modify_normal_journey(self):
        g=self.game
        g.saves.manual(1);g.save_progress()
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        child=Game(fullscreen=False,start_on_title=False,_preview_window=pygame.Surface((960,600)),_quest_playtest=True)
        child.audio.set_music(0);child.audio.set_effects(0)
        prepare_quest(child,'CH01_MQ02')
        child.saves.library=SaveLibrary(self.root/'playtests'/'CH01_MQ02'/'checkpoint.json')
        child.saves.begin()
        child.saves.request_battle('playtest:one')
        child.saves.update(.1)
        self.assertEqual(len(self.autos(child)),1)
        self.assertFalse(child.save_store.enabled)
        self.assertFalse(child.save_progress())
        row=child.saves.latest('auto')
        self.assertTrue(child.saves.load(row))
        child.show_game_over();child.draw()
        self.assertEqual(child.save_menu.selected,1)
        child.save_menu.selected=1;child.save_menu.activate()
        self.assertFalse(child.game_over)
        after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()
               and 'playtests' not in p.relative_to(self.root).parts}
        self.assertEqual(after,before)

    def test_save_browser_pages_and_game_over_render_at_small_and_large_text_sizes(self):
        g=self.game
        g.saves.manual(1)
        for size in (1.,1.25,1.5):
            # Use supported preferences rather than assuming UI implementation sizes.
            g.audio.set_text_scale(size)
            g.save_menu.open('load');g.draw()
            for _ in range(6):g.save_menu.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_DOWN,repeat=False))
            g.draw()
            self.assertEqual(len(g.save_menu.buttons),4)
            self.assertTrue(all(pygame.Rect(0,0,480,320).contains(rect) for _,rect in g.save_menu.buttons))
            g.show_game_over();g.draw();g.game_over=False

    def test_return_to_title_from_game_over_does_not_save_defeat(self):
        g=self.game
        g.save_progress();before=self.path.read_bytes()
        g.show_game_over();g.save_menu.selected=3;g.save_menu.activate()
        self.assertTrue(g.on_title)
        self.assertEqual(self.path.read_bytes(),before)

    def test_real_victory_autosave_contains_committed_rewards_and_reload_does_not_duplicate(self):
        from test_mill_battle_gameplay import acknowledge_battle_result
        g=self.game
        g.player.position.update(g.combat.position+(0,24));g.player.facing='back'
        self.assertTrue(g.combat.interact());g.combat.transition=None
        owner=g.combat;scene=owner.scene
        scene.model.enemy.hp=0;scene.model.phase='victory'
        self.assertTrue(owner._begin_victory())
        self.assertEqual(self.autos(),[])
        acknowledge_battle_result(g,scene)
        self.assertFalse(g.combat.active)
        self.assertEqual(len(self.autos()),1)
        self.assertEqual(self.autos()[0]['metadata']['reason'],'battle')
        entry=deepcopy(self.autos()[0]);payload=entry['payload']
        self.assertNotIn('post_battle',payload)
        self.assertTrue(payload['battle_rewards']['receipts'])
        inventory=deepcopy(g.inventory.to_dict());levels=deepcopy(g.character_progression.to_dict())
        self.assertTrue(g.saves.load(('Latest autosave',entry,('auto',g.saves.campaign,0))))
        self.assertEqual(g.inventory.to_dict(),inventory)
        self.assertEqual(g.character_progression.to_dict(),levels)
        self.assertFalse(g.combat.active)
        self.assertEqual(len(self.autos()),1)

    def test_real_escape_autosaves_after_resource_settlement(self):
        g=self.game
        g.player.position.update(g.combat.position+(0,24));g.player.facing='back'
        self.assertTrue(g.combat.interact());g.combat.transition=None
        g.combat.model.player.hp-=1
        hp=g.combat.model.player.hp
        g.combat.model.phase='fled'
        self.assertTrue(g.combat._settle())
        g.saves.update(.1)
        self.assertEqual(len(self.autos()),1)
        self.assertEqual(self.autos()[0]['payload']['character_attributes']['current_hp'],hp)
        self.assertEqual(self.autos()[0]['payload']['battle_rewards']['receipts'],[])

    def test_playtest_autosave_can_be_loaded_after_closing_and_reopening_the_quest(self):
        parent=self.game
        parent.on_title=True
        self.assertTrue(parent.open_quest_playtests())
        self.assertTrue(parent.launch_quest_playtest('CH01_MQ02'))
        session=parent.quest_playtest_session
        session.game.saves.update(.1)
        campaign=session.game.saves.campaign
        self.assertEqual(len(self.autos(session.game)),1)
        session.close()
        self.assertTrue(parent.launch_quest_playtest('CH01_MQ02'))
        session=parent.quest_playtest_session
        self.assertNotEqual(session.game.saves.campaign,campaign)
        row=next(row for row in session.game.saves.entries(all_campaigns=True)
                 if row[1] and row[1]['metadata']['campaign']==campaign)
        self.assertTrue(session.game.saves.load(row))
        self.assertEqual(session.game.saves.campaign,campaign)
        session.close()
        self.assertFalse(self.path.exists())

    def test_new_game_archives_a_resume_checkpoint_even_without_manual_or_autosaves(self):
        g=self.game
        self.assertTrue(g.save_progress())
        campaign=g.saves.campaign
        self.assertTrue(g.begin_journey(False,show_cinematic=False))
        row=next(row for row in g.saves.entries(all_campaigns=True) if row[2][0]=='resume')
        self.assertEqual(row[1]['metadata']['campaign'],campaign)
        self.assertTrue(g.saves.load(row))
        self.assertEqual(g.saves.campaign,campaign)

    def test_failed_new_game_archive_preserves_existing_resume_checkpoint(self):
        g=self.game
        self.assertTrue(g.save_progress())
        before=self.path.read_bytes()
        with patch('save_game.os.replace',side_effect=OSError('read only')):
            self.assertFalse(g.begin_journey(False,show_cinematic=False))
        self.assertTrue(g.on_title)
        self.assertEqual(self.path.read_bytes(),before)

    def test_game_over_without_saves_disables_both_quick_load_choices(self):
        g=self.game
        g.show_game_over();g.draw()
        self.assertIsNone(g.save_menu.rows[0][1])
        self.assertIsNone(g.save_menu.rows[1][1])
        g.save_menu.activate()
        self.assertTrue(g.game_over)
        g.save_menu.selected=1;g.save_menu.activate()
        self.assertTrue(g.game_over)

    def test_autosave_rejects_a_clear_footprint_in_an_inescapable_small_pocket(self):
        g=self.game
        point=tuple(g.player.position)
        with patch.object(g.world,'can_stand',side_effect=lambda candidate:tuple(candidate)==point):
            g.saves.request_battle('pocket');g.saves.update(.1)
        self.assertEqual(self.autos(),[])
        self.assertEqual(len(g.saves.pending_battles),1)
        self.assertTrue(g.saves.pending_battles[0].endswith(':pocket'))

    def test_replaying_a_battle_after_slot_load_creates_a_new_recovery_save(self):
        g=self.game
        self.assertTrue(g.saves.manual(1))
        row=next(row for row in g.saves.entries() if row[2]==('manual',1))
        g.saves.request_battle('boss:fixed');g.saves.update(.1)
        first=deepcopy(self.autos()[0])
        self.assertTrue(g.saves.load(row))
        g.opening_fade=g.transfer_cooldown=0
        g.saves.request_battle('boss:fixed');g.saves.update(.1)
        self.assertEqual(len(self.autos()),2)
        self.assertNotEqual(self.autos()[0]['metadata']['event'],first['metadata']['event'])
        branch=g.saves.branch
        self.assertTrue(g.save_progress())
        restored=Game(fullscreen=False,start_on_title=True,save_path=self.path)
        restored.audio.set_music(0);restored.audio.set_effects(0)
        self.assertTrue(restored.begin_journey(True))
        restored.opening_fade=restored.transfer_cooldown=0
        self.assertEqual(restored.saves.branch,branch)
        restored.saves.request_battle('boss:fixed');restored.saves.update(.1)
        self.assertEqual(len(self.autos(restored)),2)

    def test_legacy_checkpoint_imports_once_and_continue_uses_the_imported_identity(self):
        g=self.game
        data=g.journey_snapshot();data.pop('save_context')
        self.path.write_text(json.dumps(data))
        original=self.path.read_bytes()
        loaded=Game(fullscreen=False,start_on_title=True,save_path=self.path)
        self.assertEqual(self.path.read_bytes(),original)
        self.assertEqual(loaded.saves.library.manual(1)['metadata']['reason'],'legacy')
        imported=loaded.saves.library.manual(1)
        self.assertTrue(loaded.begin_journey(True))
        self.assertEqual(loaded.saves.campaign,imported['metadata']['campaign'])
        self.assertEqual(loaded.saves.library.manual(1),imported)

    def test_title_continue_falls_back_to_readable_slot_when_resume_file_is_corrupt(self):
        g=self.game
        self.assertTrue(g.saves.manual(1))
        self.path.write_text('{broken')
        loaded=Game(fullscreen=False,start_on_title=True,save_path=self.path)
        self.assertTrue(loaded.has_saved_journey)
        self.assertTrue(loaded.begin_journey(True))
        self.assertEqual(loaded.world.data['id'],g.world.data['id'])

    def test_mouse_slot_selection_paging_and_overwrite_confirmation_use_real_input(self):
        g=self.game
        self.assertTrue(g.saves.manual(1))
        before=deepcopy(g.saves.library.manual(1))
        def click(logical):
            scale,_,origin=g._ensure_ui_surface()
            point=tuple(round(origin[i]+logical[i]*scale) for i in (0,1))
            self.assertTrue(g.handle_events([
                pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point),
                pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=point)]))
        g.pause.open();g.save_menu.open('save');g.draw()
        click(g.save_menu.buttons[1][1].center)
        self.assertIsNotNone(g.saves.library.manual(2))
        g.inventory.add_many({'potion':1})
        g.draw();click(g.save_menu.buttons[0][1].center)
        self.assertTrue(g.save_menu.confirming)
        click((305,182))
        self.assertEqual(g.saves.library.manual(1),before)
        g.draw();click(g.save_menu.buttons[0][1].center)
        click((175,182))
        self.assertFalse(g.save_menu.confirming)
        self.assertNotEqual(g.saves.library.manual(1)['payload']['inventory'],before['payload']['inventory'])
        click(g.save_menu.next_rect.center);g.draw()
        self.assertEqual(g.save_menu.buttons[0][0],4)
        click(g.save_menu.buttons[-1][1].center)
        self.assertIsNotNone(g.saves.library.manual(8))

    def test_embedded_playtest_load_browser_mouse_coordinates_include_toolbar_offset(self):
        parent=self.game
        parent.on_title=True
        self.assertTrue(parent.open_quest_playtests())
        self.assertTrue(parent.launch_quest_playtest('CH01_MQ02'))
        session=parent.quest_playtest_session;g=session.game
        g.saves.update(.1)
        campaign=g.saves.campaign
        g.save_menu.open('load')
        index=next(i for i,row in enumerate(g.save_menu.rows) if row[2][0]=='auto')
        g.save_menu.selected=index;parent.draw()
        def click(logical):
            scale,_,origin=g._ensure_ui_surface()
            point=tuple(round(session.viewport_rect.topleft[i]+origin[i]+logical[i]*scale) for i in (0,1))
            self.assertTrue(parent.handle_events([
                pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point),
                pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=point)]))
        rect=next(rect for i,rect in g.save_menu.buttons if i==index)
        click(rect.center)
        self.assertTrue(g.save_menu.confirming)
        click((175,182))
        self.assertFalse(g.save_menu.is_open)
        self.assertEqual(g.saves.campaign,campaign)
        self.assertFalse(parent.save_store.path.exists())
        session.close()

    def test_malformed_slot_payload_can_be_browsed_and_rejected_without_mutating_progress(self):
        g=self.game
        self.assertTrue(g.saves.manual(1))
        file=g.saves.library.root/'manual_01.json'
        entry=json.loads(file.read_text())
        entry['payload']['party']=[]
        entry['payload']['character_levels']='broken'
        file.write_text(json.dumps(entry))
        before=g._progress_signature()
        g.save_menu.open('load');g.draw()
        row=g.save_menu.rows[0]
        self.assertFalse(g.saves.load(row))
        self.assertTrue(g.save_menu.is_open)
        self.assertEqual(g._progress_signature(),before)

    def test_defeat_automatically_opens_game_over_after_a_focus_and_pause_aware_presentation(self):
        g=self.game
        g.save_progress();before=self.path.read_bytes()
        g.player.position.update(g.combat.position+(0,24));g.player.facing='back'
        self.assertTrue(g.combat.interact());g.combat.transition=None
        owner=g.combat
        owner.model.player.hp=0;owner.model.phase='defeat'
        owner.scene.paused=True
        owner.update(2)
        self.assertFalse(g.game_over)
        owner.scene.paused=False;owner.scene.focused=False
        owner.update(2)
        self.assertFalse(g.game_over)
        owner.scene.focused=True
        owner.update(.5)
        self.assertFalse(g.game_over)
        owner.update(1.)
        self.assertTrue(g.game_over)
        self.assertEqual(self.path.read_bytes(),before)
