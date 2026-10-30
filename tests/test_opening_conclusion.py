"""Real report/doorway/arrival progression, interruption, migrations and reset."""
import os
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
import json
from pathlib import Path
import tempfile
import unittest
import pygame
import main
from quests import OPENING_QUEST, MILL_QUEST, QuestLog

class OpeningConclusionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'journey.json'
        self.game=self.make_game();self.c=self.game.opening_conclusion
    def tearDown(self):pygame.quit()
    def make_game(self,title=False):
        g=main.Game(fullscreen=False,start_on_title=title,save_path=self.path,
                    settings_path=Path(self.temp.name)/'settings.json')
        g.audio.set_music(0);g.audio.set_effects(0)
        return g
    def ready(self,order=('elira','venn')):
        g=self.game;g.accept_quest(OPENING_QUEST)
        for d in ('halden',*order):self.assertTrue(g.quests.complete_objective(OPENING_QUEST,d))
        g._sync_inventory();g.halden_visit.restore();g.elira_visit.restore();g.venn_visit.restore()
        g.world=g._routine_worlds[self.c.serene]
        g.player.position.update(self.c.serene.position+(0,32));g.player.facing='back';g.transfer_cooldown=0
        self.assertTrue(g.social.start(self.c.serene))
        for _ in range(300):
            if g.social.active:break
            g.update(.02,(0,0))
        self.assertTrue(g.social.active)
    def read(self):
        for _ in range(100):
            if not self.game.social.active:return
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE,repeat=False))
            self.game.handle_events()
        self.fail('Dialogue did not finish')
    def arrive(self):
        for _ in range(600):
            self.game.update(.05,(0,0))
            if self.c.stage=='waiting':break
        self.assertEqual(self.c.stage,'waiting')
        self.game.world=self.c.hall;self.game.player.position.update(184,258)
        self.game.update(.02,(0,0))
        self.assertEqual(self.game.social.script_identifier,'opening_mill_arrival')
    def test_report_arrival_and_handoff_once_in_both_household_orders(self):
        for order in [('elira','venn'),('venn','elira')]:
            if self.game.quests.status(OPENING_QUEST)!='available':
                self.game=self.make_game();self.c=self.game.opening_conclusion
            self.ready(order);self.read()
            self.assertEqual(self.game.quests.status(OPENING_QUEST),'ready')
            self.assertEqual(self.game.quests.status(MILL_QUEST),'locked')
            self.assertEqual(self.c.stage,'arrival')
            self.assertIn('CH01_MQ01_REPORTED',self.game.social.flags)
            self.arrive()
            self.assertEqual(sum(self.c.halden in w.npcs for w in self.game.scenes.values()),1)
            self.read();self.assertEqual(self.c.stage,'done')
            self.assertEqual(self.game.quests.status(OPENING_QUEST),'completed')
            self.assertEqual(self.game.quests.status(MILL_QUEST),'available')
            self.assertEqual(self.game.quest_ui._tracker_text(),'Find Mira at her workshop.')
            self.assertEqual(self.game.quest_ui._marker_for('mira_worker'),'!')
            self.assertFalse(self.c.serene.story_paused)
            self.assertTrue(next(r for r in self.game.town.entities if r['id']=='mill')['animation_stopped'])
            self.game.quests.drain_events()
            for _ in range(10):self.c.update(.05)
            self.assertFalse(self.game.quests.drain_events())
    def test_unfinished_report_and_arrival_do_not_advance(self):
        self.ready();self.game.social.advance();self.game.social.cancel()
        self.assertEqual(self.c.stage,'idle');self.assertFalse(self.c.mill_stopped)
        self.game.social.blocked.clear();self.assertTrue(self.game.social.start(self.c.serene))
        for _ in range(100):
            if self.game.social.active:break
            self.game.update(.02,(0,0))
        self.read();self.arrive();self.game.social.advance()
        self.game.player.position.update(288,282);self.game.update(.05,(0,0))
        self.assertFalse(self.game.social.locked);self.assertEqual(self.c.stage,'waiting')
        self.assertEqual(self.game.quests.status(OPENING_QUEST),'ready')
        self.assertEqual(self.game.quests.status(MILL_QUEST),'locked')
        self.game.player.position.update(184,258);self.game.update(.05,(0,0));self.read()
        self.assertEqual(self.c.stage,'done')
    def test_checkpoint_reload_waiting_done_and_new_game(self):
        self.ready();self.read();self.arrive();self.game.save_progress()
        g=self.make_game(True);self.assertTrue(g.begin_journey(True))
        self.assertEqual(g.opening_conclusion.stage,'waiting')
        self.game=g;self.c=g.opening_conclusion
        g.update(.02,(0,0));self.read();self.assertEqual(self.c.stage,'done')
        g.save_progress();g=self.make_game(True);self.assertTrue(g.begin_journey(True))
        self.assertEqual(g.opening_conclusion.stage,'done');self.assertFalse(g.quests.drain_events())
        self.assertTrue(g.begin_journey(False, show_cinematic=False));self.assertEqual(g.opening_conclusion.stage,'idle')
        self.assertEqual(g.quests.status(MILL_QUEST),'locked')
        self.assertIn(g.halden_visit.halden,g.halden_visit.home.npcs)
        self.assertFalse(next(r for r in g.town.entities if r['id']=='mill')['animation_stopped'])
    def test_old_completed_journey_skips_report_and_gets_missing_hook(self):
        self.ready();self.game.social.cancel();self.game.quests.turn_in(OPENING_QUEST,'mother_serene');self.game.save_progress()
        d=json.loads(self.path.read_text());d.pop('opening_conclusion');d['quests']['quests'].pop(MILL_QUEST)
        self.path.write_text(json.dumps(d));g=self.make_game(True)
        self.assertTrue(g.begin_journey(True));self.assertEqual(g.quests.status(OPENING_QUEST),'completed')
        self.assertEqual(g.opening_conclusion.stage,'arrival');self.assertEqual(g.quests.status(MILL_QUEST),'locked')
        self.game=g;self.c=g.opening_conclusion;self.arrive();self.read()
        self.assertEqual(g.quests.status(MILL_QUEST),'available')
    def test_pause_and_blocked_arrival_wait_safely(self):
        self.ready();self.read();c=self.c;g=self.game
        position=c.halden.position.copy();g.pause.is_open=True
        g.update(1,(0,0));self.assertEqual(c.halden.position,position)
        g.pause.is_open=False;g.world=c.hall;g.player.position.update(208,294)
        for _ in range(30):g.update(.05,(0,0))
        self.assertTrue(g.world.can_stand(g.player.position))
        self.assertNotIn(c.halden,c.hall.npcs)
        g.player.position.update(184,258);self.arrive();self.read()
        self.assertEqual(c.stage,'done')
    def test_arrival_checkpoint_and_large_text_do_not_skip_final_line(self):
        self.ready();self.read();self.game.save_progress()
        g=self.make_game(True);self.assertTrue(g.begin_journey(True))
        self.game=g;self.c=g.opening_conclusion
        self.assertEqual(self.c.stage,'arrival');self.arrive()
        g.audio.set_text_scale(1.5)
        g.window=pygame.display.set_mode((1100,750));g.draw()
        self.assertEqual(g.quests.status(MILL_QUEST),'locked')
        # Reflow retains the callback and only the final prose page can finish it.
        self.read();self.assertEqual(self.c.stage,'done')

    def test_locked_quest_and_invalid_snapshots(self):
        g=self.game
        self.assertNotIn(MILL_QUEST,g.quest_ui._visible_quests())
        self.assertFalse(g.accept_quest(MILL_QUEST))
        self.assertFalse(g.quests.unlock(MILL_QUEST))
        g.save_progress();d=json.loads(self.path.read_text())
        d['opening_conclusion']['stage']='done'
        self.assertFalse(self.c.valid_journey(d))
        d['opening_conclusion']['stage']='arrival';self.assertFalse(self.c.valid_journey(d))
        d['opening_conclusion']['stage']='idle';d['quests']['quests'][MILL_QUEST]['status']='available'
        self.assertFalse(QuestLog().restore(d['quests']))

if __name__=='__main__':unittest.main()
