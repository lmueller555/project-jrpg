"""Full-Game wildlife routes, ownership, quiet saves and safe interruption."""
import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from main import Game
from purposeful_wildlife import (BASKET_HOME, BASKET_PEN, CAT_ROUTE, FLOWERS,
    GATHER_ROUTES, GATHER_STEP, HOMES, PAT_STEP, REPLACED_PROP_IDS, RETURN_STEP,
    SHEEP_ROUTES, VISIT, WORKER_HOME, WORKER_ROUTE, valid_context, valid_state)
from tools.capture_lantern_quest import seed_previous_quests


class PurposefulWildlifeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.g=self.make_game()
        self.g.world=self.g.overworld_world;self.c=self.g.world.wildlife
        self.g.player.position.update(-280,1458)

    def tearDown(self):pygame.quit()

    def make_game(self,title=False):
        g=Game(fullscreen=False,start_on_title=title,save_path=self.root/'save.json',
               settings_path=self.root/'settings.json')
        g.audio.set_music(0);g.audio.set_effects(0)
        g.opening_fade=g.transfer_cooldown=0
        return g

    def tick(self,count=1):
        for _ in range(count):self.g.update(1/30,(0,0),False)

    def until(self,predicate,limit=4000,escort=False):
        for _ in range(limit):
            if predicate():return
            if escort:self.follow_worker()
            self.tick()
            self.assertTrue(valid_state(self.c.to_dict()),self.c.to_dict())
        self.fail(self.c.to_dict())

    def follow_worker(self):
        worker=self.c.worker.position
        if worker.y>1360:
            self.g.player.position.update(-280,1458);return
        for offset in ((60,40),(-60,40),(60,-40),(-60,-40),(0,60),(0,-60)):
            p=worker+offset
            if self.g.world.can_stand(p):self.g.player.position.update(p);return
        self.fail(('no escort landing',tuple(worker)))

    def finish_care(self):
        # A genuine durable GardenOrchard rest checkpoint is the only trigger.
        garden=self.g.world.garden_orchard
        state=garden.to_dict();state['gardener'].update(phase='rest',step=0,
            elapsed=0.,position=list(WORKER_HOME),read=True)
        garden.restore(state)
        self.g.player.position.update(-570,1206)

    def continue_game(self):
        seed_previous_quests(self.g);self.g.world=self.g.overworld_world
        self.assertTrue(self.g.save_progress())
        g=self.make_game(True);self.assertTrue(g.begin_journey(True))
        g.opening_fade=g.transfer_cooldown=0
        self.g=g;self.c=g.world.wildlife

    def test_fixed_roster_render_cache_and_no_animal_blockers(self):
        self.assertEqual(set(self.c.by_id),set(REPLACED_PROP_IDS)|{'farm_cat'})
        self.assertEqual(len(self.c.actors),9)
        self.assertFalse(any(a in self.g.world.npcs for a in self.c.actors))
        before=self.c.to_dict();actors=list(self.c.actors)
        for cache in (self.g.world._collision_cache,self.g.world._metadata_cache,self.g.world._render_cache):cache.clear()
        for _ in range(4):self.c.props()
        self.assertEqual(before,self.c.to_dict());self.assertEqual(actors,self.c.actors)
        sheep=self.c.by_id['south_sheep_a']
        self.assertTrue(self.g.world.can_stand(sheep.position,(16,8)))
        self.assertEqual(len(self.c.ground_blockers()),1)

    def test_all_authored_ground_segments_clear_and_sheep_contained(self):
        for route,probe in [(r,(16,8)) for r in SHEEP_ROUTES.values()]+[(r,(16,8)) for r in GATHER_ROUTES.values()]+[(CAT_ROUTE,(10,5)),(WORKER_ROUTE[:3],(10,6))]:
            for start,end in zip(route,route[1:]):
                start=pygame.Vector2(start);end=pygame.Vector2(end);count=max(1,int(start.distance_to(end))+1)
                for i in range(count+1):
                    point=start.lerp(end,i/count)
                    self.assertTrue(self.g.world.can_stand(point,probe,self.c.worker),(tuple(point),probe))
        for site in ((-280,1458),(1450,1430)):
            self.g.player.position.update(site)
            for _ in range(900):
                self.tick()
                for a in self.c.actors:
                    if a.species!='sheep':continue
                    bounds=pygame.Rect(-488,1404,232,214) if a.id.startswith('south') else pygame.Rect(1324,1332,256,178)
                    self.assertTrue(bounds.contains(self.g.world.probe_rect(a.position,a.probe_size)))
                    self.assertTrue(self.g.world.can_stand(a.position,a.probe_size,a))

    def test_animal_yields_to_player_and_recovers_without_blocking_passage(self):
        sheep=self.c.by_id['south_sheep_a']
        self.g.player.position.update(-438,1488)
        self.tick(300);before=sheep.position.copy();self.tick(90)
        self.assertEqual(before,sheep.position)
        self.assertFalse(self.g.world.probe_rect(sheep.position,sheep.probe_size).colliderect(self.g.world.probe_rect(self.g.player.position)))
        self.g.player.position.update(sheep.position)
        self.assertTrue(self.g.world.can_stand(self.g.player.position,(16,8)))
        self.tick(30)
        self.g.player.position.update(-280,1458);self.tick(120)
        self.assertNotEqual(before,sheep.position)

    def test_pause_dialogue_travel_distance_and_chunks_freeze_exactly(self):
        self.tick(20)
        for owner,field in ((self.g,'map_open'),(self.g.pause,'is_open'),(self.g.inventory_ui,'is_open'),
                            (self.g.world_map_viewer,'is_open'),(self.g.quest_ui,'journal_open'),(self.g,'on_title')):
            state=self.c.to_dict();setattr(owner,field,True);self.tick(30);setattr(owner,field,False)
            self.assertEqual(state,self.c.to_dict(),field)
        self.g.social.start_script([{'speaker':'caelan','text':'A moment.'}],identifier='wildlife_pause_test')
        state=self.c.to_dict();self.tick(30);self.assertEqual(state,self.c.to_dict());self.g.social.cancel()
        state=self.c.to_dict();world=self.g.world;self.g.world=self.g.town;self.tick(30)
        self.assertEqual(state,self.c.to_dict());self.g.world=world
        self.g.player.position.update(300,500);self.tick(60);self.assertEqual(state,self.c.to_dict())

    def test_birds_scatter_once_wait_eight_seconds_and_land_clear(self):
        bird=self.c.by_id['west_bird'];home=pygame.Vector2(HOMES[bird.id])
        self.g.player.position.update(home+(30,0))
        with mock.patch.object(self.g.regional_audio,'play') as play:
            self.tick();self.assertEqual(bird.state['mode'],'scatter');self.assertEqual(len([c for c in play.call_args_list if c.args[0].family=='wildlife']),1)
            source=next(c.args[0] for c in play.call_args_list if c.args[0].family=='wildlife')
            self.assertEqual(source.family,'wildlife');self.assertFalse(source.ambient)
            self.assertEqual(source.far,140);self.assertGreaterEqual(source.cooldown,4)
            self.tick(300);self.assertEqual(bird.state['mode'],'away');self.assertEqual(len([c for c in play.call_args_list if c.args[0].family=='wildlife']),1)
            self.g.player.position.update(home+(100,0))
            self.until(lambda:bird.state['mode']=='peck',300)
            cues=[c.args[0] for c in play.call_args_list if c.args[0].family=='wildlife']
            self.assertEqual(len(cues),2);self.assertEqual(cues[-1].sound,'bird')
        self.assertEqual(bird.position,home)
        self.g.player.position.update(home+(30,0));self.tick()
        self.g.player.position.update(home+(100,0));self.tick(180)
        self.assertNotEqual(bird.state['mode'],'peck')
        self.assertGreater(bird.state['cooldown'],0)

    def test_bird_waits_when_player_is_near_its_retreat_after_cooldown(self):
        bird=self.c.by_id['west_bird'];home=pygame.Vector2(HOMES[bird.id])
        self.g.player.position.update(home+(30,0))
        with mock.patch.object(self.g.regional_audio,'play') as play:
            self.until(lambda:bird.state['mode']=='away',150)
            self.g.player.position.update(home+(-90,0))
            self.tick(420)
            wings=[c.args[0] for c in play.call_args_list if c.args[0].sound=='wings']
            self.assertEqual(len(wings),1)
            self.assertEqual(bird.state['mode'],'away')
            self.assertEqual(bird.state['cooldown'],0.)
            self.g.player.position.update(home+(100,0))
            self.until(lambda:bird.state['mode']=='peck',300)
            wings=[c.args[0] for c in play.call_args_list if c.args[0].sound=='wings']
            self.assertEqual(len(wings),1)
        self.assertEqual(bird.position,home)

    def test_bird_retreat_folds_wings_and_return_keeps_flapping(self):
        bird=self.c.by_id['west_bird'];home=pygame.Vector2(HOMES[bird.id])
        self.g.player.position.update(home+(30,0))
        self.until(lambda:bird.state['mode']=='away',150)
        retreat=bird.position.copy();self.tick(30)
        folded=self.c.clips['bird_land_'+bird.facing]['images'][-1]
        self.assertIs(bird.sprite(),folded)
        self.tick(30)
        self.assertEqual(bird.position,retreat)
        self.assertIs(bird.sprite(),folded)
        self.g.player.position.update(home+(100,0))
        self.until(lambda:bird.state['mode']=='land',300)
        # Beyond the old landing clip's duration, the returning bird must
        # still change wing frames while its feet move toward the seeds.
        self.tick(20);before=bird.position.copy();frames=set()
        for _ in range(20):
            self.assertEqual(bird.state['mode'],'land')
            frames.add(pygame.image.tobytes(bird.sprite(),'RGBA'))
            self.tick()
        self.assertGreater(len(frames),1)
        self.assertLess(bird.position.distance_to(home),before.distance_to(home))
        self.until(lambda:bird.state['mode']=='peck',100)
        self.assertEqual(bird.position,home)

    def test_cat_full_short_route_and_butterflies_stay_on_real_petals(self):
        cat=self.c.by_id['farm_cat'];self.g.player.position.update(-470,1208)
        self.until(lambda:cat.state['mode']=='stretch',300)
        self.until(lambda:cat.state['mode']=='sit',600)
        self.assertEqual(tuple(cat.position),CAT_ROUTE[-1])
        self.until(lambda:cat.state['mode']=='sleep',700)
        self.assertEqual(tuple(cat.position),CAT_ROUTE[0])
        for key,flower in FLOWERS.items():
            self.g.player.position.update(pygame.Vector2(flower)+(50,30))
            butterfly=self.c.by_id[key];seen=set()
            for _ in range(300):
                self.tick();seen.add(butterfly.state['mode'])
                self.assertLessEqual(butterfly.position.distance_to(flower),9)
            self.assertEqual(seen,{'settle','flutter'})

    def test_only_finished_care_borrows_existing_worker_and_finishes_once(self):
        self.tick(60);self.assertEqual(self.c.vignette['phase'],'idle')
        self.finish_care();garden=self.g.world.garden_orchard
        original=garden.to_dict();items=garden.portable_positions();npcs=list(self.g.world.npcs)
        self.until(lambda:self.c.vignette['step']==PAT_STEP,escort=True)
        self.assertTrue(self.c.worker.wildlife_owned);self.assertEqual(garden.to_dict(),original)
        self.assertEqual(self.c.vignette['basket'],'pen');self.assertEqual(tuple(self.c.basket_position()),BASKET_PEN)
        self.until(lambda:self.c.vignette['phase']=='done',escort=True)
        self.assertFalse(self.c.worker.wildlife_owned);self.assertEqual(tuple(self.c.worker.position),WORKER_HOME)
        self.assertEqual(tuple(self.c.basket_position()),BASKET_HOME)
        self.assertEqual(garden.to_dict(),original);self.assertEqual(garden.portable_positions(),items)
        self.assertEqual(self.g.world.npcs,npcs)
        state=copy.deepcopy(self.c.vignette);self.tick(300);self.assertEqual(state,self.c.vignette)

    def test_blocked_gather_waits_for_real_contact_and_recovers(self):
        self.finish_care();self.until(lambda:self.c.vignette['step']==GATHER_STEP,escort=True)
        self.g.player.position.update(-324,1464)
        with mock.patch.object(self.g.regional_audio,'play') as play:
            self.tick(600)
            self.assertEqual(self.c.vignette['step'],GATHER_STEP)
            self.assertEqual(self.c.vignette['elapsed'],14.)
            self.assertFalse(any(c.args[0].sound=='sheep' for c in play.call_args_list))
        self.g.player.position.update(-280,1412)
        self.until(lambda:self.c.vignette['step']==PAT_STEP)
        for key,route in GATHER_ROUTES.items():self.assertEqual(tuple(self.c.by_id[key].position),route[-1])
        self.assertTrue(valid_state(self.c.to_dict()))

    def test_cat_never_blocks_returning_gardener_on_shared_visit(self):
        self.finish_care();self.g.player.position.update(-440,1370)
        self.until(lambda:self.c.vignette['phase']=='done',limit=3000)
        self.assertEqual(tuple(self.c.worker.position),WORKER_HOME)
        self.assertFalse(self.c.worker.wildlife_owned)

    def test_gardener_conversation_during_carry_and_nuzzle_pauses_and_resumes(self):
        self.finish_care()
        for step in (3,PAT_STEP):
            with self.subTest(step=step):
                self.until(lambda:self.c.vignette['step']==step,escort=True)
                self.tick(10)
                self.g.player.position.update(self.c.worker.position+(0,24))
                self.assertTrue(self.g.world.can_stand(self.g.player.position))
                self.assertIn('kitchen gardener',self.g.overworld_travel.interaction_hint())
                before=self.c.to_dict();basket=self.c.basket_position()
                self.assertTrue(self.g.overworld_travel.interact())
                self.assertEqual(self.g.social.script_identifier,'garden_orchard_greeting')
                self.assertEqual(before,self.c.to_dict())
                self.assertEqual(basket,self.c.basket_position())
                self.tick(90)
                self.assertEqual(before,self.c.to_dict())
                self.assertEqual(basket,self.c.basket_position())
                self.assertTrue(self.c.worker.wildlife_owned)
                self.assertEqual(self.g.world.garden_orchard.to_dict()['gardener']['position'],list(WORKER_HOME))
                while self.g.social.active:self.g.social.advance()
                self.follow_worker();self.tick()
                self.assertNotEqual(before,self.c.to_dict())
                self.assertTrue(self.c.worker.wildlife_owned)
        self.until(lambda:self.c.vignette['phase']=='done',escort=True)
        self.assertEqual(tuple(self.c.basket_position()),BASKET_HOME)
        self.assertEqual(tuple(self.c.worker.position),WORKER_HOME)
        self.assertFalse(self.c.worker.wildlife_owned)

    def test_continue_mid_walk_keeps_exact_worker_frame_and_reset_releases(self):
        self.finish_care();self.until(lambda:self.c.vignette['step']==3 and self.c.worker.moving,escort=True)
        self.tick(10)
        before=self.c.to_dict();frame=pygame.image.tobytes(self.c.worker.sprite(0),'RGBA')
        self.continue_game()
        self.assertEqual(before,self.c.to_dict());self.assertTrue(self.c.worker.moving)
        self.assertEqual(frame,pygame.image.tobytes(self.c.worker.sprite(0),'RGBA'))
        self.c.restore()
        self.assertFalse(self.c.worker.wildlife_owned)
        self.assertEqual(tuple(self.c.worker.position),WORKER_HOME)
        self.assertTrue(valid_state(self.c.to_dict()))

    def test_continue_during_nuzzle_preserves_owner_basket_clock_and_contact(self):
        self.finish_care();self.until(lambda:self.c.vignette['step']==PAT_STEP and self.c.vignette['elapsed']>.3,escort=True)
        before=self.c.to_dict();basket=self.c.basket_position();garden=self.g.world.garden_orchard.to_dict()
        self.continue_game();self.assertEqual(before,self.c.to_dict())
        self.assertEqual(basket,self.c.basket_position());self.assertEqual(garden,self.g.world.garden_orchard.to_dict())
        self.assertTrue(self.c.worker.wildlife_owned)
        with mock.patch.object(self.g.regional_audio,'play') as play:
            self.until(lambda:self.c.vignette['step']>PAT_STEP,escort=True)
            sheep=[call.args[0] for call in play.call_args_list if call.args[0].sound=='sheep']
            self.assertEqual(len(sheep),1)
        self.until(lambda:self.c.vignette['phase']=='done',escort=True)

    def test_contact_checkpoint_restore_does_not_replay_or_duplicate_basket(self):
        self.finish_care();self.until(lambda:self.c.vignette['step']==PAT_STEP and self.c.vignette['contact'],escort=True)
        before=self.c.to_dict();self.continue_game();self.assertEqual(before,self.c.to_dict())
        with mock.patch.object(self.g.regional_audio,'play') as play:
            self.until(lambda:self.c.vignette['step']>PAT_STEP,escort=True)
            self.assertFalse(any(call.args[0].sound=='sheep' for call in play.call_args_list))
        self.assertEqual(sum(prop[2] is self.c.basket for prop in self.c.props()),1)

    def test_animation_positions_and_cooldowns_do_not_dirty_progress(self):
        self.tick(3);self.g.save_progress();progress=self.c.progress_dict()
        with mock.patch.object(self.g.save_store,'write',wraps=self.g.save_store.write) as write:
            self.tick(180);self.assertEqual(write.call_count,0)
        self.assertEqual(progress,self.c.progress_dict())
        self.finish_care();self.until(lambda:self.c.vignette['step']==3,escort=True)
        self.follow_worker();self.tick(3);self.g.save_progress()
        with mock.patch.object(self.g.save_store,'write',wraps=self.g.save_store.write) as write:
            self.tick(10);self.assertEqual(write.call_count,0)
            self.g.save_progress();self.assertEqual(write.call_count,1)

    def test_schema_rejects_nonfinite_foreign_routes_and_inconsistent_loans(self):
        initial=self.c.to_dict();self.assertTrue(valid_state(initial))
        for field,value in [('position',[0,0]),('position',[True,1476]),('clock',float('nan')),
                ('elapsed',float('inf')),('cooldown',-1),('target',True),('target',900),('mode',[]),('facing',{})]:
            state=copy.deepcopy(initial);state['animals']['south_sheep_a'][field]=value
            self.assertFalse(valid_state(state),(field,value))
        for field,value in [('phase',[]),('step',True),('step',999),('position',[-532,5000]),('clock',float('nan')),('contact',1),('basket','apples')]:
            state=copy.deepcopy(initial);state['vignette'][field]=value
            self.assertFalse(valid_state(state),(field,value))
        self.finish_care();self.tick();active=self.c.to_dict()
        self.assertTrue(valid_context(active,self.g.world.garden_orchard.to_dict()))
        wrong=self.g.world.garden_orchard.to_dict();wrong['gardener']['phase']='work'
        self.assertFalse(valid_context(active,wrong))
        wrong=self.g.world.garden_orchard.to_dict();wrong['gardener']['position']=[-526,1190]
        self.assertFalse(valid_context(active,wrong))
        with self.assertRaises(ValueError):self.c.restore({'animals':{}})
