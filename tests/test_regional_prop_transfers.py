"""Completed-action transfers and actual body/prop compositing in the region."""
import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame

from main import Game
from garden_orchard import GARDEN_SCENE, HAND, PROGRAMS, STARTS
from grain_farm import DIRECTIONS, PICKUP_SECONDS, SOURCE
from bridge_crew import CUP_ACTION_SECONDS, HELP, KETTLE, REACH, SAFE, WORK_STONE
from purposeful_wildlife import BASKET_HOME, BASKET_PEN, VISIT, valid_state
from tools.capture_lantern_quest import seed_previous_quests


class RegionalPropTransfers(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.g=self.game()
        self.g.world=self.g.overworld_world

    def tearDown(self):
        pygame.quit()

    def game(self,title=False):
        game=Game(fullscreen=False,start_on_title=title,
                  save_path=self.root/'save.json',settings_path=self.root/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade=game.transfer_cooldown=0
        return game

    def garden_action(self,role,program,step,phase='work'):
        garden=self.g.world.garden_orchard
        state=garden.to_dict()
        point=STARTS[role]
        for action in program[:step]:point=action.get('target',point)
        state[role].update(phase=phase,read=phase=='scene',step=step,elapsed=0.,position=list(point))
        garden.restore(state)
        actor=next(a for a in garden.actors if a.role==role)
        self.g.player.position.update(actor.position+(30,20))
        return garden,actor

    def assert_composite(self,actor,record,behind):
        z,priority,prop,point=record
        body=actor.sprite(0)
        origin=(round(actor.position.x)-actor.draw_anchor[0],
                round(actor.position.y)-actor.draw_anchor[1])
        body_rect=body.get_rect(topleft=origin)
        prop_rect=prop.get_rect(topleft=point)
        overlap=body_rect.clip(prop_rect)
        canvas=pygame.Surface(body_rect.union(prop_rect).size,pygame.SRCALPHA)
        bounds=body_rect.union(prop_rect)
        layers=[record,(actor.position.y+6,2,body,origin)]
        for _,_,image,position in sorted(layers,key=lambda entry:(entry[0],entry[1])):
            canvas.blit(image,(position[0]-bounds.x,position[1]-bounds.y))
        checked=0
        for y in range(overlap.top,overlap.bottom):
            for x in range(overlap.left,overlap.right):
                b=body.get_at((x-body_rect.x,y-body_rect.y))
                p=prop.get_at((x-prop_rect.x,y-prop_rect.y))
                if b.a==p.a==255 and b!=p:
                    self.assertEqual(canvas.get_at((x-bounds.x,y-bounds.y)),b if behind else p)
                    checked+=1
        self.assertGreater(checked,0)
        if behind:
            for y in range(prop_rect.top,prop_rect.bottom):
                for x in range(prop_rect.left,prop_rect.right):
                    p=prop.get_at((x-prop_rect.x,y-prop_rect.y))
                    if p.a!=255:continue
                    if not body_rect.collidepoint(x,y) or body.get_at((x-body_rect.x,y-body_rect.y)).a==0:
                        self.assertEqual(canvas.get_at((x-bounds.x,y-bounds.y)),p)

    def test_every_garden_transfer_stays_with_its_owner_until_completion(self):
        for role,program,phase in [('gardener',PROGRAMS['gardener'],'work'),
                                   ('picker',PROGRAMS['picker'],'work'),
                                   ('gardener',GARDEN_SCENE,'scene')]:
            for step,action in enumerate(program):
                if not action.get('kind'):continue
                with self.subTest(role=role,phase=phase,item=action['item'],kind=action['kind']):
                    garden,actor=self.garden_action(role,program,step,phase)
                    item=action['item'];start=garden.portable_positions()[item][0].copy()
                    with patch.object(self.g.regional_audio,'emit') as emit:
                        for fraction in (0,.25,.5,.99):
                            garden.state[role]['elapsed']=action['duration']*fraction
                            garden._pose(actor)
                            self.assertEqual(garden.portable_positions()[item][0],start)
                            snapshot=garden.to_dict();garden.restore(snapshot)
                            self.assertEqual(garden.portable_positions()[item][0],start)
                        emit.assert_not_called()
                        garden.update(.1,self.g)
                        if action.get('sound'):self.assertEqual(emit.call_count,1)
                    expected=(pygame.Vector2(action['point']) if action['kind']=='put' else
                              actor.position+((0,-18) if actor.pose=='admire' else HAND))
                    self.assertEqual(garden.portable_positions()[item][0],expected)
                    snapshot=garden.to_dict();garden.restore(snapshot)
                    self.assertEqual(garden.portable_positions()[item][0],expected)

    def test_garden_carried_props_obey_facing_for_every_walk_frame(self):
        for role,item,phase in [('gardener','can','work'),('gardener','turnip_0','work'),
                                ('gardener','plant','scene'),('picker','apple_0','work')]:
            program=GARDEN_SCENE if phase=='scene' else PROGRAMS[role]
            step=next(i for i,a in enumerate(program) if a.get('carry')==item)
            garden,actor=self.garden_action(role,program,step,phase)
            for direction in DIRECTIONS:
                actor.facing=direction;actor.moving=True
                for frame in range(4):
                    actor.clock=frame*.17
                    position,_=garden.portable_positions()[item]
                    image=garden.art[item.split('_')[0]]
                    top=(round(position.x)-image.get_width()//2,round(position.y)-image.get_height())
                    record=next(p for p in garden.props() if p[2] is image and p[3]==top)
                    with self.subTest(item=item,direction=direction,frame=frame):
                        self.assert_composite(actor,record,direction=='back')
                actor.moving=False
                self.assert_composite(actor,record,direction=='back')

    def test_sacks_and_stones_stay_at_source_for_the_entire_grab(self):
        farm=self.g.world.grain_farm
        farm._stage('lift');farm.loader.advance(0)
        bridge=self.g.world.bridge_crew
        bridge._stage('lift');bridge.mason.advance(0)
        for fraction in (0,.25,.5,.99):
            farm.loader.clock=PICKUP_SECONDS*fraction
            sack=pygame.Vector2(farm.props()[2][3])+(6,10)
            self.assertEqual(sack,pygame.Vector2(SOURCE)+(0,-7))
            bridge.mason.clock=1.4*fraction
            self.assertEqual(bridge.stone_position(0),bridge.mason.position+(-3,-2))

    def test_existing_sack_stone_and_cup_rear_layers_render_behind_body(self):
        farm=self.g.world.grain_farm
        bridge=self.g.world.bridge_crew
        for kind,actor,stage,controller in [
                ('sack',farm.loader,'carry',farm),('stone',bridge.mason,'carry',bridge),
                ('cup',bridge.tender,'tea_across',bridge),('cup',bridge.mason,'sit_walk',bridge)]:
            if kind=='cup':bridge.state['cup_phase']='mason' if actor is bridge.mason else 'tender'
            controller._stage(stage);actor.facing='back';actor.moving=True;actor.advance(0)
            for frame in range(4):
                actor.advance(.18)
                image=farm.sack if kind=='sack' else bridge.art[kind]
                record=farm.props()[2] if kind=='sack' else next(p for p in controller.props() if p[2] is image)
                self.assert_composite(actor,record,True)
            actor.moving=False;actor.advance(0)
            record=farm.props()[2] if kind=='sack' else next(p for p in controller.props() if p[2] is image)
            self.assert_composite(actor,record,True)

    def test_cup_transfers_snap_at_each_completed_action(self):
        bridge=self.g.world.bridge_crew
        fixtures=[
            ('tea_pickup',1,False,'kettle','tender'),
            ('wobble',1,True,'tender','stone'),
            ('stone_pickup',1,True,'stone','tender_from_stone'),
            ('tray_setdown',1,True,'tender_from_stone','tray'),
            ('reach',2,True,'tray','mason'),
            ('cup_return',4,True,'mason','tender_return'),
            ('tray_place',4,True,'tender_return','kettle')]
        for stage,beat,read,before,after in fixtures:
            with self.subTest(stage=stage):
                bridge.restore({'sorted':3,'tea_beat':beat,'request_read':read,
                                'greeted':[],'cup_phase':before})
                bridge.tender.position.update(KETTLE if stage in ('tea_pickup','tray_place') else HELP)
                bridge.mason.position.update(REACH)
                bridge._stage(stage)
                bridge.mason.advance(0);bridge.tender.advance(0)
                start=bridge.cup_position.copy()
                duration=2. if stage=='reach' else CUP_ACTION_SECONDS
                for fraction in (0,.25,.5,.99):
                    bridge.timer=duration*fraction
                    for actor in bridge.actors:actor.clock=bridge.timer
                    self.assertEqual(bridge.cup_position,start)
                    self.assertEqual(bridge.state['cup_phase'],before)
                self.g.player.position.update(-2340,644)
                bridge.update(.1,self.g)
                self.assertEqual(bridge.state['cup_phase'],after)
                self.assertEqual(len([p for p in bridge.props() if p[2] is bridge.art['cup']]),1)
                if after in ('stone','tray','kettle'):
                    destination={'stone':pygame.Vector2(WORK_STONE)+(0,-9),
                                 'tray':pygame.Vector2(SAFE)+(0,-7),
                                 'kettle':pygame.Vector2(KETTLE)+(8,-11)}[after]
                    self.assertEqual(bridge.cup_position,destination)
                else:self.assertIsNotNone(bridge.cup_owner)

    def test_continue_preserves_every_committed_cup_owner(self):
        seed_previous_quests(self.g);self.g.world=self.g.overworld_world
        for beat,phase in [(1,'kettle'),(1,'tender'),(1,'stone'),(1,'tender_from_stone'),
                           (2,'tray'),(3,'mason'),(4,'tender_return'),(5,'kettle')]:
            with self.subTest(beat=beat,phase=phase):
                bridge=self.g.world.bridge_crew
                bridge.restore({'sorted':3,'tea_beat':beat,'request_read':True,
                                'greeted':[],'cup_phase':phase})
                self.g.player.position.update(-2340,644)
                self.assertTrue(self.g.save_progress())
                resumed=self.game(True)
                self.assertTrue(resumed.begin_journey(True))
                self.g=resumed
                self.assertEqual(resumed.world.bridge_crew.state['cup_phase'],phase)
                self.assertEqual(len([p for p in resumed.world.bridge_crew.props()
                                      if p[2] is resumed.world.bridge_crew.art['cup']]),1)

    def basket_action(self,step):
        garden=self.g.world.garden_orchard
        data=garden.to_dict()
        from purposeful_wildlife import WORKER_HOME, _basket_at
        data['gardener'].update(phase='rest',read=True,step=0,elapsed=0.,position=list(WORKER_HOME))
        garden.restore(data)
        wildlife=self.g.world.wildlife
        data=wildlife.to_dict()
        position=WORKER_HOME
        for action in VISIT[:step]:position=action.get('target',position)
        data['vignette'].update(phase='visit',step=step,elapsed=0.,contact=False,
                               position=list(position),basket=_basket_at(step,False),moving=False)
        wildlife.restore(data)
        self.g.player.position.update(wildlife.worker.position+(60,40))
        return wildlife

    def test_all_four_basket_transfers_snap_and_keep_ground_collision_until_grab(self):
        for step,action in enumerate(VISIT):
            if 'basket' not in action:continue
            with self.subTest(step=step):
                wildlife=self.basket_action(step)
                source=wildlife.basket_position()
                for fraction in (0,.25,.5,.99):
                    wildlife.vignette['elapsed']=action['duration']*fraction
                    wildlife._worker_pose()
                    self.assertEqual(wildlife.basket_position(),source)
                    self.assertEqual(bool(wildlife.ground_blockers()),wildlife.vignette['basket']!='hand')
                    self.assertTrue(valid_state(wildlife.to_dict()))
                    snapshot=wildlife.to_dict();wildlife.restore(snapshot)
                    self.assertEqual(wildlife.basket_position(),source)
                wildlife._visit(.1,self.g,self.g.world.probe_rect(self.g.player.position))
                self.assertEqual(wildlife.vignette['basket'],action['basket'])
                destination=(wildlife.worker.position+(0,-7) if action['basket']=='hand' else
                             pygame.Vector2(BASKET_HOME if action['basket']=='home' else BASKET_PEN))
                self.assertEqual(wildlife.basket_position(),destination)
                self.assertTrue(valid_state(wildlife.to_dict()))

    def test_basket_body_occlusion_for_every_direction_and_frame(self):
        step=next(i for i,a in enumerate(VISIT) if a.get('basket')=='hand')+1
        wildlife=self.basket_action(step)
        for direction in DIRECTIONS:
            wildlife.worker.facing=direction;wildlife.worker.moving=True
            for frame in range(4):
                wildlife.worker.clock=frame*.17
                record=next(p for p in wildlife.props() if p[2] is wildlife.basket)
                self.assert_composite(wildlife.worker,record,direction=='back')
            wildlife.worker.moving=False
            self.assert_composite(wildlife.worker,record,direction=='back')

    def test_legacy_mid_grab_basket_save_migrates_to_pre_snap_owner(self):
        step=next(i for i,a in enumerate(VISIT) if a.get('basket')=='hand')
        wildlife=self.basket_action(step)
        legacy=copy.deepcopy(wildlife.to_dict());legacy['version']=1
        legacy['vignette'].update(elapsed=1.,contact=True,basket='hand')
        self.assertTrue(valid_state(legacy))
        wildlife.restore(legacy)
        self.assertEqual(wildlife.to_dict()['version'],2)
        self.assertEqual(wildlife.vignette['basket'],'home')
        self.assertEqual(wildlife.basket_position(),pygame.Vector2(BASKET_HOME))
        self.assertTrue(wildlife.ground_blockers())
        self.assertTrue(valid_state(wildlife.to_dict()))
