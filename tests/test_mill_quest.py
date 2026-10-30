"""Play MQ02's real callbacks, actions, companion and saved checkpoints."""
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
from test_mill_battle_gameplay import finish_mill_battle, read_social

ROOT=Path(__file__).resolve().parents[1]


class MillQuestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'journey.json'
        self.g=self.game();self.c=self.g.mill_quest
        self.handoff()

    def tearDown(self):pygame.quit()

    def game(self,title=False):
        g=main.Game(fullscreen=False,start_on_title=title,save_path=self.path,
                    settings_path=Path(self.temp.name)/'settings.json')
        g.audio.set_music(0);g.audio.set_effects(0);pygame.event.clear()
        return g

    def handoff(self):
        """Seed completed prior household work through its public quest APIs."""
        g=self.g
        self.assertTrue(g.accept_quest(OPENING_QUEST))
        for key in ('halden','elira','venn'):
            self.assertTrue(g.quests.complete_objective(OPENING_QUEST,key))
        g._sync_inventory();g.halden_visit.restore();g.elira_visit.restore();g.venn_visit.restore()
        self.assertTrue(g.quests.turn_in(OPENING_QUEST,'mother_serene'))
        self.assertTrue(g.quests.unlock(MILL_QUEST))
        g.opening_conclusion.restore({'version':1,'stage':'done'})
        g.opening.restore({'version':1,'stage':'disabled'})
        g.opening_fade=0;g.transfer_cooldown=0
        g.social.blocked.clear();g.quests.drain_events();g.save_progress()

    def tick(self,seconds=.05):self.g.update(seconds,(0,0),False)

    def until(self,predicate,seconds=30):
        for _ in range(round(seconds/.05)):
            if predicate():return
            self.tick()
        self.fail(('Timed out',self.c.stage,self.c.action,self.g.world.data['id']))

    def read_current(self):
        identifier=self.g.social.script_identifier
        for _ in range(100):
            if not self.g.social.active or self.g.social.script_identifier!=identifier:return
            self.assertFalse(self.g.social.choosing)
            self.g.social.advance()
        self.fail('Unfinished '+str(identifier))

    def read_all(self):
        read_social(self.g)

    def clear_position(self,world,point):
        point=pygame.Vector2(point)
        for offset in ((0,0),(0,8),(0,-8),(8,0),(-8,0),(0,12),(0,-12)):
            value=point+offset
            if world.can_stand(value):return value
        self.fail(('No clear station',world.data['id'],tuple(point)))

    def at(self,key,upstream=False,companion=True):
        world=self.g._scene_by_id('upstream') if upstream else self.g.town
        if self.g.world is not world:
            # Exercise the reversible world connection; no direct scene teleport.
            self.link_to(world.data['id'])
        self.walk(self.clear_position(world,self.c.points[key]))
        self.g.player.facing='right';self.g.transfer_cooldown=0
        if companion and self.g.quests.status(MILL_QUEST)=='active':
            self.until(lambda:self.c.mira in world.npcs and self.c.mira.position.distance_to(self.g.player.position)<=76)

    def link_to(self,scene_id):
        origin=self.g.world
        link=next(l for l in origin.data['world_links']
                  if json.loads((ROOT/l['destination']).read_text())['id']==scene_id)
        self.walk(link['position']);self.read_all();self.g.transfer_cooldown=0
        self.assertTrue(self.g.travel_link(link))
        self.assertEqual(self.g.world.data['id'],scene_id)
        self.until(lambda:self.c.mira in self.g.world.npcs)

    def walk(self,goal,new_scene=None):
        world=self.g.world
        route=find_path(world,self.g.player.position,goal,world.probe_size,None)
        self.assertIsNotNone(route,(world.data['id'],tuple(self.g.player.position),goal))
        for corner in route:
            for _ in range(600):
                if self.g.combat.active:
                    finish_mill_battle(self.g)
                elif (getattr(self.c, 'encounter_cutscene_active', False) or
                      (self.g.social.active and
                       str(self.g.social.script_identifier).startswith('mill_encounter'))):
                    self.read_all()
                    if self.g.combat.active:finish_mill_battle(self.g)
                if self.g.world is not world:
                    self.assertEqual(self.g.world.data['id'],new_scene);return
                delta=pygame.Vector2(corner)-self.g.player.position
                if delta.length()<.04:break
                self.g.update(min(.05,delta.length()/72),delta,False)
            else:self.fail(('Player stalled',world.data['id'],corner))
        if new_scene:
            door=next(d for d in world.doors if pygame.Vector2(d.data['anchor']).distance_to(goal)<2)
            direction=(0,-1) if door.data['entry_side']=='north' else (0,1)
            for _ in range(120):
                if self.g.world is not world:break
                self.g.update(1/60,direction,False)
            self.assertEqual(self.g.world.data['id'],new_scene)

    def recruit(self):
        mira=self.c.mira
        self.g.world=self.g.town
        # Speak from clear ground near the existing workbench.
        candidates=[mira.position+offset for offset in ((0,28),(28,0),(-28,0),(0,-28))]
        pos=next(p for p in candidates if self.g.town.can_stand(p))
        self.g.player.position.update(pos)
        self.assertTrue(self.g.social.start(mira))
        self.assertEqual(self.g.social.script_identifier,'mill_reunion')
        self.read_all()
        self.assertEqual(self.g.quests.status(MILL_QUEST),'active')
        self.assertEqual(self.g.quests.objective_status(MILL_QUEST,'meet_mira'),'completed')

    def inspect(self,key,upstream=False):
        self.at(key,upstream)
        self.assertTrue(self.c.interact())
        self.assertEqual(self.g.social.script_identifier,'mill_'+key)
        self.read_current()

    def diagnose(self):
        self.recruit();self.inspect('mechanism');self.inspect('race')
        self.assertEqual(self.g.social.script_identifier,'mill_diagnosis')
        self.read_current()
        self.assertEqual(self.g.quests.objective_status(MILL_QUEST,'diagnose_mill'),'completed')
        self.read_all()
        self.assertTrue(self.c.warned)

    def prepare(self):
        self.diagnose();self.inspect('intake',True)
        self.at('bypass',True);self.assertTrue(self.c.interact())
        self.assertEqual(self.g.social.script_identifier,'mill_prepare')
        self.read_all();self.assertEqual(self.c.action,'prepare')
        self.until(lambda:self.c.action is None)
        self.assertTrue(self.c.prepared)

    def cast(self,acknowledge=True):
        self.prepare();self.at('spell',True)
        self.assertTrue(self.c.interact());self.assertEqual(self.g.social.script_identifier,'mill_spell_intro')
        self.read_all();self.assertEqual(self.c.action,'spell')
        self.until(lambda:self.c.spell_done)
        self.assertFalse(self.c.mill_restored)
        self.assertTrue(self.g.social.script_identifier.startswith('mill_encouragement'))
        if acknowledge:self.read_all();self.assertTrue(self.c.encouraged)

    def repair(self):
        self.cast();self.at('lever',True)
        self.assertTrue(self.c.interact());self.assertEqual(self.g.social.script_identifier,'mill_repair')
        self.read_all();self.assertEqual(self.c.action,'repair')
        self.until(lambda:self.c.action is None)
        self.assertTrue(self.c.mill_restored)

    def verify(self):
        self.repair();self.at('mill_station')
        self.assertTrue(self.c.interact());self.assertEqual(self.g.social.script_identifier,'mill_verify')
        self.read_current();self.assertTrue(self.c.verified)

    def reload(self):
        self.g.save_progress();other=self.game(True)
        self.assertTrue(other.begin_journey(True))
        self.g=other;self.c=other.mill_quest;other.opening_fade=0

    def test_unread_reunion_does_not_accept_or_detach_mira(self):
        mira=self.c.mira;start=mira.position.copy()
        self.g.player.position.update(start+(0,28))
        self.assertTrue(self.g.social.start(mira));self.g.social.advance();self.g.social.cancel()
        self.assertEqual(self.g.quests.status(MILL_QUEST),'available')
        self.assertFalse(mira.quest_mode);self.assertEqual(mira.position,start)

    def test_recruitment_uses_existing_actor_and_preserves_one_mira(self):
        original=self.c.mira;self.recruit()
        self.assertIs(self.c.mira,original);self.assertTrue(original.quest_mode)
        self.assertEqual(sum(original in w.npcs for w in self.g.scenes.values()),1)
        self.assertEqual(set(original.walks),{'front','back','left','right'})

    def test_diagnosis_needs_both_read_inspections_and_final_exchange(self):
        self.recruit();self.at('mechanism');self.assertTrue(self.c.interact())
        self.g.social.cancel();self.assertNotIn('mechanism',self.c.inspected)
        self.inspect('mechanism')
        self.assertNotEqual(self.g.quests.objective_status(MILL_QUEST,'diagnose_mill'),'completed')
        self.inspect('race');self.assertEqual(self.g.social.script_identifier,'mill_diagnosis')
        self.g.social.cancel()
        self.assertNotEqual(self.g.quests.objective_status(MILL_QUEST,'diagnose_mill'),'completed')
        self.at('race');self.assertTrue(self.c.interact());self.read_all()
        self.assertEqual(self.g.quests.objective_status(MILL_QUEST,'diagnose_mill'),'completed')

    def test_upstream_connection_is_reversible_with_one_companion(self):
        self.diagnose();actor=self.c.mira
        self.link_to('upstream');self.assertTrue(self.g.world.can_stand(self.g.player.position))
        self.assertIs(self.c.mira,actor)
        self.link_to(self.g.town.data['id'])
        self.assertEqual(sum(actor in w.npcs for w in self.g.scenes.values()),1)
        self.assertFalse(self.c.mill_restored)

    def test_companion_traverses_real_workshop_door_without_cloning(self):
        self.recruit();actor=self.c.mira
        self.walk((636,438),'mira');self.walk((178,250))
        self.until(lambda:actor in self.g.world.npcs)
        self.assertEqual(sum(actor in w.npcs for w in self.g.scenes.values()),1)
        self.assertTrue(self.g.world.can_stand(self.g.player.position))
        door=self.g.world.doors[0]
        self.walk(door.data['anchor'],self.g.town.data['id'])
        self.walk((636,474));self.until(lambda:actor in self.g.town.npcs)
        self.assertIs(actor,self.c.mira)

    def test_preparation_is_a_timed_action_and_does_not_restore_mill(self):
        self.diagnose();self.inspect('intake',True);self.at('bypass',True)
        self.assertTrue(self.c.interact());self.g.social.cancel();self.assertFalse(self.c.prepared)
        self.assertTrue(self.c.interact());self.read_all()
        self.assertFalse(self.c.prepared);self.assertEqual(self.c.action,'prepare')
        self.until(lambda:self.c.prepared)
        self.assertFalse(self.c.spell_done);self.assertFalse(self.c.mill_restored)
        self.assertTrue(self.g.opening_conclusion.mill_stopped)

    def test_small_spell_succeeds_before_encouragement_and_keeps_mill_stopped(self):
        self.cast(False)
        self.assertFalse(self.c.encouraged);self.assertFalse(self.c.mill_restored)
        self.assertEqual(self.g.quests.objective_status(MILL_QUEST,'small_spell'),'completed')
        self.assertTrue(self.g.opening_conclusion.mill_stopped)
        self.assertFalse(hasattr(self.g.player,'story_sprite'))
        saved=json.loads(self.path.read_text())['mill_quest']
        self.assertTrue(saved['spell_done']);self.assertFalse(saved['encouraged'])

    def test_spell_preserves_body_and_visibly_clears_only_the_small_recess(self):
        self.prepare();self.at('spell',True)
        idle=self.g.town.image('assets/characters/caelan/idle_right.png')
        expected_head=pygame.image.tobytes(idle.subsurface((0,0,24,14)),'RGBA')
        expected_legs=pygame.image.tobytes(idle.subsurface((0,25,24,11)),'RGBA')
        def recess():
            image=pygame.Surface((8,8))
            self.g.world.draw(image,(504,324),self.g.player,self.g.elapsed_ms,include_ui=False)
            return pygame.image.tobytes(image,'RGB')
        before=recess()
        unchanged={p['id']:pygame.image.tobytes(p['surface'],'RGBA') for p in self.c.surface_props
                   if p['id'] in ('intake_screen','lever','millrace_flow','bypass')}
        self.assertTrue(self.c.interact());self.read_all()
        checked=0
        for _ in range(200):
            if self.c.spell_done:break
            self.tick()
            art=getattr(self.g.player,'story_sprite',None)
            if art is not None:
                x,y=self.g.player.story_draw_anchor
                self.assertEqual(pygame.image.tobytes(art.subsurface((x-12,y-30,24,14)),'RGBA'),expected_head)
                self.assertEqual(pygame.image.tobytes(art.subsurface((x-12,y-5,24,11)),'RGBA'),expected_legs)
                checked+=1
        self.assertTrue(self.c.spell_done);self.assertGreater(checked,10)
        self.assertNotEqual(recess(),before)
        for prop in self.c.surface_props:
            if prop['id'] in unchanged:
                self.assertEqual(pygame.image.tobytes(prop['surface'],'RGBA'),unchanged[prop['id']],prop['id'])
        self.assertFalse(self.c.mill_restored)

    def test_encouragement_only_references_seen_venn_failure(self):
        self.g.venn_visit.magicks_failed=True;self.g.venn_visit.method='magicks'
        self.g.social.flags.add('CH01_MQ01_VENN_MAGICKS_FAILED')
        self.cast(False)
        self.assertEqual(self.g.social.script_identifier,'mill_encouragement_failed')
        self.assertTrue(any('Venn' in l['text'] for l in self.g.social._source_lines))

    def test_tools_history_gets_encouragement_without_invented_failure(self):
        self.assertFalse(self.g.venn_visit.magicks_failed)
        self.cast(False)
        self.assertEqual(self.g.social.script_identifier,'mill_encouragement')
        self.assertFalse(any('Venn' in l['text'] for l in self.g.social._source_lines))

    def test_walkaway_and_reload_preserve_success_but_not_unread_encouragement(self):
        self.cast(False);self.g.social.cancel();self.reload()
        self.assertTrue(self.c.spell_done);self.assertFalse(self.c.encouraged)
        self.assertIsNone(self.c.action);self.assertFalse(hasattr(self.g.player,'story_sprite'))
        self.at('spell',True);self.assertTrue(self.c.interact())
        self.assertTrue(self.g.social.script_identifier.startswith('mill_encouragement'))
        self.read_all();self.assertTrue(self.c.encouraged);self.assertIsNone(self.c.action)

    def test_pause_inventory_map_and_journal_freeze_spell(self):
        self.prepare();self.at('spell',True);self.assertTrue(self.c.interact());self.read_all()
        self.until(lambda:self.c.action_time>.15 and hasattr(self.g.player,'story_sprite'))
        state=(self.c.action,self.c.action_time,self.g.player.story_sprite)
        for owner,field in [(self.g.pause,'is_open'),(self.g.inventory_ui,'is_open'),
                            (self.g,'map_open'),(self.g.quest_ui,'journal_open')]:
            setattr(owner,field,True);self.tick(.5);setattr(owner,field,False)
            self.assertEqual((self.c.action,self.c.action_time,self.g.player.story_sprite),state)
        self.assertFalse(self.c.spell_done)

    def test_interrupted_spell_restarts_from_safe_idle_on_load(self):
        self.prepare();self.at('spell',True);self.assertTrue(self.c.interact());self.read_all()
        self.until(lambda:self.c.action_time>.15)
        self.reload();self.assertTrue(self.c.prepared);self.assertFalse(self.c.spell_done)
        self.assertIsNone(self.c.action);self.assertFalse(hasattr(self.g.player,'story_sprite'))
        self.assertTrue(self.g.world.can_stand(self.g.player.position))

    def test_physical_repair_restarts_world_wheel_and_survives_reload(self):
        self.repair();mill=next(e for e in self.g.town.entities if e['id']=='mill')
        self.assertFalse(self.g.opening_conclusion.mill_stopped)
        self.assertFalse(mill['animation_stopped']);self.assertFalse(self.c.verified)
        self.reload();self.assertTrue(self.c.mill_restored)
        self.assertFalse(next(e for e in self.g.town.entities if e['id']=='mill')['animation_stopped'])
        self.assertEqual(self.g.quests.status(MILL_QUEST),'active')

    def test_final_verification_does_not_finish_unread_resolution(self):
        self.verify()
        self.assertFalse(self.c.resolved)
        self.assertNotEqual(self.g.quests.status(MILL_QUEST),'completed')
        halden=self.g.halden_visit.halden
        self.g.player.position.update(self.clear_position(self.g.town,halden.position+(0,28)))
        self.assertTrue(self.g.social.start(halden));self.assertEqual(self.g.social.script_identifier,'mill_resolution')
        self.g.social.cancel();self.assertFalse(self.c.resolved)
        self.g.social.blocked.clear();self.assertTrue(self.g.social.start(halden));self.read_all()
        self.assertTrue(self.c.resolved);self.assertEqual(self.g.quests.status(MILL_QUEST),'completed')
        self.reload();self.assertTrue(self.c.resolved)
        self.assertEqual(sum(self.c.mira in w.npcs for w in self.g.scenes.values()),1)

    def test_new_game_resets_companion_intake_and_mill(self):
        self.repair();actor=self.c.mira
        self.assertTrue(self.g.begin_journey(False, show_cinematic=False))
        self.assertEqual(self.g.quests.status(MILL_QUEST),'locked')
        self.assertFalse(self.c.prepared);self.assertFalse(self.c.spell_done)
        self.assertFalse(self.c.mill_restored);self.assertFalse(actor.quest_mode)
        self.assertEqual(sum(actor in w.npcs for w in self.g.scenes.values()),1)
        self.assertFalse(next(e for e in self.g.town.entities if e['id']=='mill')['animation_stopped'])

    def test_upstream_checkpoint_is_valid_saved_location(self):
        self.prepare();self.reload()
        self.assertEqual(self.g.world.data['id'],'upstream')
        self.assertTrue(self.c.prepared);self.assertFalse(self.c.spell_done)
        self.assertEqual(sum(self.c.mira in w.npcs for w in self.g.scenes.values()),1)

    def test_old_available_handoff_without_mill_record_loads_normally(self):
        self.g.save_progress();data=json.loads(self.path.read_text());data.pop('mill_quest')
        self.path.write_text(json.dumps(data));other=self.game(True)
        self.assertTrue(other.begin_journey(True))
        self.assertEqual(other.quests.status(MILL_QUEST),'available')
        self.assertFalse(other.mill_quest.mill_restored)

    def test_old_placeholder_ready_or_completed_migrates_to_unfinished_quest(self):
        for status in ('ready','completed'):
            data=self.g.quests.to_dict()
            data['quests'][MILL_QUEST]={'status':status,'completed_objectives':['meet_mira']}
            quests=QuestLog();self.assertTrue(quests.restore(data))
            self.assertEqual(quests.status(MILL_QUEST),'active')
            self.assertEqual(quests.objective_status(MILL_QUEST,'meet_mira'),'completed')
            self.assertEqual(quests.objective_status(MILL_QUEST,'diagnose_mill'),'active')
            self.g.save_progress();journey=json.loads(self.path.read_text())
            journey.pop('mill_quest');journey['quests']=data
            self.path.write_text(json.dumps(journey));other=self.game(True)
            self.assertTrue(other.begin_journey(True))
            self.assertEqual(other.quests.status(MILL_QUEST),'active')
            self.assertFalse(other.mill_quest.mill_restored)
            self.assertTrue(other.mill_quest.mira.quest_mode)

    def test_impossible_mill_progress_rejected_before_loading(self):
        self.g.save_progress();data=json.loads(self.path.read_text())
        record=data['mill_quest'];record['restored']=True
        self.path.write_text(json.dumps(data));other=self.game(True)
        self.assertFalse(other.has_saved_journey)
        self.assertFalse(other.mill_quest.mill_restored)
        # Dropping the new record cannot manufacture post-recruitment facts.
        self.g.save_progress();data=json.loads(self.path.read_text());data.pop('mill_quest')
        data['quests']['quests'][MILL_QUEST]={'status':'active','completed_objectives':['meet_mira','diagnose_mill']}
        self.path.write_text(json.dumps(data));other=self.game(True)
        self.assertFalse(other.has_saved_journey)


if __name__=='__main__':unittest.main()
