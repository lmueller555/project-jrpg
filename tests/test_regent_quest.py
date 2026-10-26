"""MQ03 keeps Caelan a guide/host while adults own the road dispute."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import pygame
import main
from npc_routines import find_path
from quests import OPENING_QUEST, MILL_QUEST, QuestLog

ROOT=Path(__file__).resolve().parents[1]
REGENT='CH01_MQ03'


class RegentQuestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'journey.json'
        self.g=self.game();self.c=self.g.regent_quest
        self.previous_quests()

    def tearDown(self):pygame.quit()

    def game(self,title=False):
        game=main.Game(fullscreen=False,start_on_title=title,save_path=self.path,
                       settings_path=Path(self.temp.name)/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0);pygame.event.clear()
        return game

    def previous_quests(self):
        """Seed only completed earlier quests, using their public APIs/records."""
        g=self.g
        self.assertTrue(g.accept_quest(OPENING_QUEST))
        for key in ('halden','elira','venn'):self.assertTrue(g.quests.complete_objective(OPENING_QUEST,key))
        g._sync_inventory();g.halden_visit.restore();g.elira_visit.restore();g.venn_visit.restore()
        self.assertTrue(g.quests.turn_in(OPENING_QUEST,'mother_serene'))
        self.assertTrue(g.quests.unlock(MILL_QUEST))
        g.opening_conclusion.restore({'version':1,'stage':'done'})
        self.assertTrue(g.accept_quest(MILL_QUEST))
        for objective in g.quests.definitions[MILL_QUEST]['objectives']:
            self.assertTrue(g.quests.complete_objective(MILL_QUEST,objective['id']))
        self.assertTrue(g.quests.turn_in(MILL_QUEST,'mira_worker'))
        g.mill_quest.restore({'version':1,'inspected':['mechanism','race','intake'],
                             'prepared':True,'spell_done':True,'encouraged':True,
                             'restored':True,'verified':True,'resolved':True})
        g.opening.restore({'version':1,'stage':'disabled'})
        if g.quests.status(REGENT)=='locked':self.assertTrue(g.quests.unlock(REGENT))
        self.c.restore(None)
        g.world=g.town;g.opening_fade=0;g.transfer_cooldown=0
        g.social.blocked.clear();g.quests.drain_events();g.save_progress()

    def tick(self,seconds=.05):self.g.update(seconds,(0,0),False)

    def until(self,predicate,seconds=45):
        for _ in range(round(seconds/.05)):
            if predicate():return
            self.tick()
        self.fail(('Timed out',self.c.stage,self.g.social.script_identifier,
                   self.g.world.data['id'],tuple(self.g.player.position),
                   [(a.data['id'],tuple(a.position)) for a in self.c.party]))

    def clear_position(self,world,point):
        point=pygame.Vector2(point)
        for radius in (0,8,16,24,32):
            for offset in ((0,radius),(-radius,0),(radius,0),(0,-radius)):
                pos=point+offset
                if world.can_stand(pos):return pos
        self.fail(('Blocked station',world.data['id'],tuple(point)))

    def walk(self,goal,new_scene=None):
        world=self.g.world
        route=find_path(world,self.g.player.position,goal,world.probe_size,None)
        self.assertIsNotNone(route,(world.data['id'],tuple(self.g.player.position),tuple(goal)))
        for corner in route:
            for _ in range(600):
                if self.g.world is not world:
                    self.assertEqual(self.g.world.data['id'],new_scene);return
                delta=pygame.Vector2(corner)-self.g.player.position
                if delta.length()<.04:break
                self.g.update(min(.05,delta.length()/72),delta,False)
            else:self.fail(('Walking stalled',world.data['id'],corner,self.c.stage))
        if new_scene:
            door=next(d for d in world.doors if pygame.Vector2(d.data['anchor']).distance_to(goal)<2)
            direction=(0,-1) if door.data['entry_side']=='north' else (0,1)
            for _ in range(120):
                if self.g.world is not world:break
                self.g.update(1/60,direction,False)
            self.assertEqual(self.g.world.data['id'],new_scene)

    def at(self,key):
        self.walk(self.clear_position(self.g.world,self.c.points[key]))
        self.g.transfer_cooldown=0

    def read_current(self):
        identifier=self.g.social.script_identifier
        for _ in range(160):
            if not self.g.social.active or self.g.social.script_identifier!=identifier:return
            self.assertFalse(self.g.social.choosing)
            self.g.social.advance()
        self.fail('Unfinished dialogue '+str(identifier))

    def interact(self,kind):
        if kind in ('dispute','welcome','discussion') and not self.g.social.active:
            self.until(lambda:self.c._group_ready)
        if kind=='aftermath' and not self.g.social.active:
            self.until(lambda:self.c._aside_ready)
        if not self.g.social.active:self.assertTrue(self.c.interact(),(kind,self.c.stage))
        self.assertEqual(self.g.social.script_identifier,'regent_'+kind)

    def assign(self):
        self.at('preparations');self.interact('preparations');self.read_current()
        self.assertEqual(self.g.quests.status(REGENT),'active')
        self.assertEqual(self.c.stage,'assigned')

    def meet(self):
        self.assign();self.at('arrival');self.interact('arrival');self.read_current()
        self.assertEqual(self.g.quests.objective_status(REGENT,'meet_visitors'),'completed')
        self.assertEqual(self.c.stage,'met')

    def dispute(self,read=True):
        self.meet();self.at('road')
        self.until(lambda:self.c.stage=='dispute')
        self.interact('dispute')
        if read:
            self.read_current();self.assertEqual(self.c.stage,'releasing')

    def escort(self):
        self.dispute();self.until(lambda:self.c.stage=='escorting')
        self.at('courtyard');self.until(lambda:self.c.stage=='welcome')
        self.assertEqual(self.g.quests.objective_status(REGENT,'accompany_visit'),'completed')

    def welcome(self):
        self.escort();self.interact('welcome');self.read_current()
        self.assertEqual(self.c.stage,'hosted')

    def discussion(self,read=True):
        self.welcome();self.interact('discussion')
        if read:
            self.read_current();self.assertEqual(self.c.stage,'discussion')
            self.assertEqual(self.g.quests.objective_status(REGENT,'welcome_party'),'completed')

    def complete(self):
        self.discussion();self.at('aftermath');self.interact('aftermath');self.read_current()
        self.assertEqual(self.c.stage,'done');self.assertEqual(self.g.quests.status(REGENT),'completed')

    def reload(self):
        self.g.save_progress();other=self.game(True)
        self.assertTrue(other.begin_journey(True),other.save_error)
        self.g=other;self.c=other.regent_quest;other.opening_fade=0;other.transfer_cooldown=0

    def test_regent_is_locked_until_the_mill_quest_is_complete(self):
        self.assertTrue(self.g.begin_journey(False))
        self.assertEqual(self.g.quests.status(REGENT),'locked')
        self.assertFalse(self.g.accept_quest(REGENT))
        self.assertNotIn(REGENT,self.g.quest_ui._visible_quests())

    def test_old_completed_mill_save_unlocks_the_new_visit(self):
        self.g.save_progress();data=json.loads(self.path.read_text())
        data.pop('regent_quest');data['quests']['quests'].pop(REGENT)
        self.path.write_text(json.dumps(data));other=self.game(True)
        self.assertTrue(other.begin_journey(True),other.save_error)
        self.assertEqual(other.quests.status(REGENT),'available')
        self.assertEqual(other.regent_quest.stage,'idle')

    def test_objectives_give_caelan_only_guide_and_host_responsibilities(self):
        objectives=self.g.quests.definitions[REGENT]['objectives']
        self.assertEqual([o['id'] for o in objectives],
                         ['meet_visitors','accompany_visit','welcome_party','speak_serene'])
        for item in objectives:
            self.assertNotIn('receipt',json.dumps(item).lower())
            self.assertNotIn('adjudicat',json.dumps(item).lower())

    def test_unread_preparations_do_not_accept_the_visit(self):
        self.at('preparations');self.interact('preparations')
        self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.g.quests.status(REGENT),'available')
        self.assertEqual(self.c.stage,'idle')
        self.reload();self.assertEqual(self.c.stage,'idle')

    def test_arrival_requires_finishing_the_introduction(self):
        self.assign();self.at('arrival');self.interact('arrival')
        self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.c.stage,'assigned')
        self.assertEqual(self.g.quests.objective_status(REGENT,'meet_visitors'),'active')
        self.assertTrue(self.c.interact());self.read_current()
        self.assertEqual(self.c.stage,'met')

    def test_dispute_is_an_adult_conversation_without_a_player_choice(self):
        self.dispute(False)
        speakers={p['speaker'] for p in self.g.social._source_lines}
        self.assertTrue({'aldric','venn_father','road_foreman'}<=speakers)
        self.assertFalse(self.g.social.choosing)
        self.g.social.cancel();self.assertEqual(self.c.stage,'dispute')
        self.assertNotEqual(self.g.quests.objective_status(REGENT,'accompany_visit'),'completed')
        self.reload();self.assertEqual(self.c.stage,'dispute')

    def test_the_same_venn_actor_is_used_in_the_dispute(self):
        original=self.g.venn_visit.family['father'];self.dispute(False)
        self.assertIs(self.c.venn,original)
        self.assertEqual(sum(original in w.npcs for w in self.g.scenes.values()),1)
        self.assertEqual(sum(n.data['id']=='venn_father' for w in self.g.scenes.values() for n in w.npcs),1)

    def test_cart_release_and_courtyard_arrival_precede_escort_completion(self):
        self.dispute(False)
        cart=next(p for p in self.c.surface_props if p['id']=='venn_cart')
        start=pygame.Vector2(cart['position'])
        self.read_current();self.assertEqual(self.c.stage,'releasing')
        self.assertEqual(pygame.Vector2(cart['position']),start)
        self.assertNotEqual(self.g.quests.objective_status(REGENT,'accompany_visit'),'completed')
        self.assertFalse(self.g.town.can_stand(start+(37,26)))
        venn_start=self.c.venn.position.copy()
        self.tick()
        self.assertLessEqual(self.c.venn.position.distance_to(venn_start),8)
        self.assertLessEqual(pygame.Vector2(cart['position']).distance_to(start),8)
        self.until(lambda:pygame.Vector2(cart['position']).distance_to(start)>4)
        self.until(lambda:self.c.stage=='escorting')
        self.at('courtyard');self.until(lambda:self.c.stage=='welcome')
        self.until(lambda:self.c._delivery_done)
        self.assertGreater(pygame.Vector2(cart['position']).distance_to(start),100)
        self.assertFalse(self.g.town.can_stand(pygame.Vector2(cart['position'])+(37,26)))
        self.assertEqual(self.g.quests.objective_status(REGENT,'accompany_visit'),'completed')

    def test_releasing_cart_checkpoint_resumes_without_duplicate_actors(self):
        self.dispute();self.reload()
        self.assertEqual(self.c.stage,'releasing');self.assertTrue(self.c.cart_released)
        self.assertEqual(sum(self.c.venn in w.npcs for w in self.g.scenes.values()),1)
        self.assertEqual(sum(self.c.aldric in w.npcs for w in self.g.scenes.values()),1)
        self.until(lambda:self.c.stage=='escorting')
        self.assertNotEqual(self.g.quests.objective_status(REGENT,'accompany_visit'),'completed')

    def test_overlay_panels_pause_staging(self):
        self.meet()
        position=self.c.aldric.position.copy();stage=self.c.stage
        for owner,field in [(self.g.pause,'is_open'),(self.g.inventory_ui,'is_open'),
                            (self.g,'map_open'),(self.g.quest_ui,'journal_open')]:
            setattr(owner,field,True);self.tick(.5);setattr(owner,field,False)
            self.assertEqual(self.c.aldric.position,position)
            self.assertEqual(self.c.stage,stage)

    def test_welcome_dialogue_is_not_skipped_when_cancelled(self):
        self.escort();self.interact('welcome');self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.c.stage,'welcome')
        self.assertTrue(self.c.interact());self.read_current();self.assertEqual(self.c.stage,'hosted')

    def test_covenant_discussion_stays_unresolved_until_acknowledged(self):
        self.discussion(False);self.g.social.advance();self.g.social.cancel()
        self.reload()
        self.assertEqual(self.c.stage,'hosted')
        self.assertEqual(self.g.quests.objective_status(REGENT,'welcome_party'),'completed')
        self.assertEqual(self.g.quests.objective_status(REGENT,'speak_serene'),'active')
        self.assertTrue(self.c.interact());self.read_current()
        self.assertEqual(self.c.stage,'discussion')

    def test_final_personal_exchange_is_required_for_completion(self):
        self.discussion();self.at('aftermath');self.interact('aftermath')
        self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.g.quests.status(REGENT),'active')
        self.assertTrue(self.c.interact());self.read_current()
        self.assertEqual(self.g.quests.status(REGENT),'completed')
        self.assertEqual(self.c.stage,'done')

    def test_full_visit_preserves_mill_and_does_not_authorize_excavation(self):
        self.complete()
        self.assertTrue(self.g.mill_quest.mill_restored)
        self.assertFalse(next(e for e in self.g.town.entities if e['id']=='mill')['animation_stopped'])
        self.assertFalse(any('AUTHORIZ' in flag.upper() or 'EXCAVATION_STARTED' in flag.upper()
                             for flag in self.g.social.flags))
        self.assertNotIn('CH01_MQ04',self.g.quests.definitions)
        self.reload();self.assertEqual(self.g.quests.status(REGENT),'completed')
        self.assertTrue(self.g.mill_quest.mill_restored)

    def test_parked_cart_leaves_halden_accessible_after_the_visit(self):
        self.complete();self.until(lambda:self.c._delivery_done)
        halden=self.g.halden_visit.halden
        options=[halden.position+offset for offset in ((0,16),(20,0),(-20,0),(0,-16),(18,12),(-18,12))]
        self.assertTrue(any(self.g.town.can_stand(pos) and
                            find_path(self.g.town,self.g.player.position,pos,self.g.town.probe_size,None) is not None
                            for pos in options))

    def test_checkpoint_reload_keeps_one_aldric_and_does_not_replay_arrival(self):
        self.meet();self.reload()
        self.assertEqual(self.c.stage,'met')
        self.assertFalse(self.g.social.active)
        self.assertEqual(sum(self.c.aldric in w.npcs for w in self.g.scenes.values()),1)
        self.assertEqual(self.g.quests.objective_status(REGENT,'meet_visitors'),'completed')

    def test_new_game_resets_visit_and_actor_routines(self):
        self.complete();self.assertTrue(self.g.begin_journey(False))
        self.assertEqual(self.g.quests.status(REGENT),'locked')
        self.assertEqual(self.c.stage,'idle')
        self.assertFalse(self.c._owned)
        self.assertEqual(self.g.opening.stage,'wake')
        self.assertEqual(self.g._routine_worlds[self.c.tomas].data['id'],'sanctuary_hall')
        self.assertEqual(sum(self.g.venn_visit.family['father'] in w.npcs for w in self.g.scenes.values()),1)
        self.assertIn(self.g.venn_visit.family['father'],self.g.venn_visit.home.npcs)
        self.assertTrue(all(not actor.story_visible for actor in self.c.actors.values()))

    def test_invalid_or_cross_quest_visit_checkpoint_is_rejected(self):
        self.g.save_progress();good=json.loads(self.path.read_text())
        for record in ({'version':1,'stage':'unknown'}, {'version':True,'stage':'idle'},
                       {'version':1,'stage':'done'}, {'version':1,'stage':'assigned','extra':True}):
            bad=copy.deepcopy(good);bad['regent_quest']=record
            self.path.write_text(json.dumps(bad));other=self.game(True)
            self.assertFalse(other.has_saved_journey,record)
        self.path.write_text(json.dumps(good))

    def test_walkaway_from_unread_preparations_leaves_quest_available(self):
        self.at('preparations');self.interact('preparations');self.g.social.advance()
        self.walk(self.clear_position(self.g.town,self.c.points['arrival']))
        self.assertFalse(self.g.social.active)
        self.assertEqual(self.g.quests.status(REGENT),'available')
        self.assertEqual(self.c.stage,'idle')

    def test_active_visit_cannot_load_without_its_scene_checkpoint(self):
        self.assign();self.g.save_progress();data=json.loads(self.path.read_text())
        data.pop('regent_quest');self.path.write_text(json.dumps(data))
        other=self.game(True);self.assertFalse(other.has_saved_journey)

    def test_dialogue_contains_occasional_readable_emotional_expression(self):
        scenes=json.loads((ROOT/'assets/story/regent/scene.json').read_text())
        lines=[line for scene in scenes.values() for line in scene]
        cues=[line for line in lines if '(' in line['text'] and ')' in line['text']]
        self.assertGreaterEqual(len(cues),5)
        self.assertLess(len(cues),len(lines)//2)
        self.assertTrue({'aldric','serene','tomas'}<={line['speaker'] for line in cues})


if __name__=='__main__':unittest.main()
