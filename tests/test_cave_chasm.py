"""The Echo rupture is a persistent blocked landmark, not a new travel route."""
from copy import deepcopy
import json,os,tempfile,unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from main import World,Game
from sanctuary_cave import SCENE_ID,SCENE_FILES,SanctuaryCave,migrate_chasm_checkpoint
from sanctuary_boss import valid_ticket,SanctuaryBoss
from npc_routines import find_path
from cave_chasm_fx import draw_aether,PERIOD_MS
from regional_audio import samples,RegionalAudio
from types import SimpleNamespace as NS
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1]

class CaveChasmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((480,320))
        cls.world=World(SCENE_FILES[SCENE_ID]);cls.chasm=cls.world.data['cave']['chasm']
    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_opening_blocks_full_feet_but_leaves_both_side_routes_and_inspection_reachable(self):
        world=self.world
        for point in ((2084,230),(2060,200),(2060,280),(2060,310)):
            self.assertFalse(world.can_stand(point),point)
        landing=self.chasm['safe_landing']
        for point in ((1900,300),(2250,270),(1940,492),(1810,600),(2070,344)):
            self.assertTrue(world.can_stand(point),point)
            self.assertIsNotNone(find_path(world,landing,point,world.probe_size,None),point)
        self.assertFalse(self.chasm['descendable'])
        self.assertEqual(world.doors,[])
        self.assertTrue(all(link['destination']!='subterranean' for link in world.data['cave']['links']))

    def test_migration_moves_matching_pending_records_without_replaying_progress(self):
        ticket={'version':1,'enemy_id':'vespermaw','level':7,'receipt':'boss:vespermaw',
                'scene':SCENE_ID,'position':[2084,230],'facing':'back','battlefield':'cave_echo_chamber',
                'combat_seed':23,'party_active':['caelan'],'party_resources':{'caelan':{'hp':100,'mp':20}}}
        self.assertTrue(valid_ticket(ticket))
        saved={'player':{'scene':SCENE_ID,'position':[2084,230]},
               'sanctuary_boss':{'version':1,'defeated':False,'intro_seen':True,'pending':ticket},
               'post_battle':{'kind':'cave_boss','scene':SCENE_ID,'position':[2084,230],'encounter':deepcopy(ticket)},
               'inventory':{'potion':2},'quests':{'MQ03':'pending'},'experience':543}
        before=deepcopy(saved);moved=migrate_chasm_checkpoint(saved)
        self.assertEqual(saved,before)
        self.assertEqual(moved['player']['position'],self.chasm['safe_landing'])
        self.assertTrue(SanctuaryBoss.valid_snapshot(moved['sanctuary_boss']))
        self.assertEqual(moved['sanctuary_boss']['pending'],moved['post_battle']['encounter'])
        self.assertEqual(moved['post_battle']['position'],moved['player']['position'])
        for key in ('inventory','quests','experience'):self.assertEqual(moved[key],saved[key])
        self.assertIs(migrate_chasm_checkpoint(moved),moved)
        # Invalid owners still reach ordinary validation rather than crashing migration.
        corrupt=deepcopy(saved);corrupt['sanctuary_boss']=['invalid']
        self.assertEqual(migrate_chasm_checkpoint(corrupt)['sanctuary_boss'],['invalid'])

    def test_unaffected_positions_and_other_scenes_are_not_relocated(self):
        for scene,point in ((SCENE_ID,[2060,360]),(SCENE_ID,[1900,300]),('eldenmere',[2084,230])):
            data={'player':{'scene':scene,'position':point}}
            self.assertIs(migrate_chasm_checkpoint(data),data)

    def test_aether_is_animated_periodic_viewport_culled_and_static_in_reduced_motion(self):
        bounds=(80,90,288,174)
        def render(time,reduced=False,camera=(0,0)):
            canvas=pygame.Surface((480,320),pygame.SRCALPHA)
            draw_aether(canvas,camera,bounds,time,reduced)
            return pygame.image.tobytes(canvas,'RGBA')
        self.assertNotEqual(render(0),render(1700))
        self.assertEqual(render(0),render(PERIOD_MS))
        self.assertEqual(render(0,True),render(1700,True))
        self.assertEqual(render(0,camera=(1000,1000)),bytes(480*320*4))

    def test_continue_relocates_an_older_checkpoint_without_changing_its_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'journey.json';settings=Path(directory)/'settings.json'
            game=Game(fullscreen=False,start_on_title=False,save_path=path,settings_path=settings)
            game.world=game._scene_by_id(SCENE_ID);game.player.position.update(2084,230)
            self.assertTrue(game.save_progress())
            raw=path.read_bytes();old=json.loads(raw)
            restored=Game(fullscreen=False,start_on_title=True,save_path=path,settings_path=settings)
            self.assertTrue(restored.has_saved_journey,restored.save_error)
            self.assertEqual(path.read_bytes(),raw)
            self.assertTrue(restored.begin_journey(True),restored.save_error)
            self.assertEqual(list(restored.player.position),self.chasm['safe_landing'])
            new=json.loads(path.read_text())
            for key in ('inventory','character_levels','character_abilities','sanctuary_boss','quests'):
                self.assertEqual(new[key],old[key],key)
            self.assertTrue(restored.world.can_stand(restored.player.position))
            game.music.stop();restored.music.stop()

    def effect_fixture(self):
        g=NS(world=self.world,player=NS(position=pygame.Vector2(2060,360)),
             on_title=False,on_gallery=False,gallery_session=None,_music_focused=True,
             social=NS(locked=False),combat=NS(active=False),quest_ui=NS(journal_open=False),
             opening=NS(locks_player=False),opening_cinematic=NS(active=False),
             regent_arrival=NS(active=False,state='done'),overworld_travel=NS(active=False),
             map_open=False,transfer_cooldown=0,opening_fade=0,household_action=False,
             audio=NS(effects_volume=1.,bind_effects=lambda owner:None))
        for key in ('pause','inventory_ui','party_ui','status_ui','world_map_viewer'):
            setattr(g,key,NS(is_open=False))
        return g

    def test_world_effect_clock_freezes_for_focus_dialogue_and_menus(self):
        g=self.effect_fixture();owner=SanctuaryCave(g);g.world.chasm_elapsed_ms=0
        owner.update(.5);self.assertEqual(g.world.chasm_elapsed_ms,500)
        for obj,key,value in ((g,'_music_focused',False),(g.social,'locked',True),
                              (g.pause,'is_open',True),(g.status_ui,'is_open',True),
                              (g.inventory_ui,'is_open',True),(g.combat,'active',True)):
            before=getattr(obj,key);setattr(obj,key,value);owner.update(1)
            self.assertEqual(g.world.chasm_elapsed_ms,500,key)
            setattr(obj,key,before)
        owner.update(.5);self.assertEqual(g.world.chasm_elapsed_ms,1000)

    def test_local_effect_audio_releases_for_volume_focus_dialogue_combat_and_departure(self):
        g=self.effect_fixture();g.world=NS(is_sanctuary_cave=True,data=self.world.data)
        audio=RegionalAudio(g)
        try:
            for obj,key,value in ((g.audio,'effects_volume',0),(g,'_music_focused',False),
                                  (g.social,'locked',True),(g.pause,'is_open',True),
                                  (g.combat,'active',True),(g,'on_title',True)):
                audio.update(1.);self.assertIn('cave.echo_rupture',audio.voices)
                before=getattr(obj,key);setattr(obj,key,value);audio.update(0)
                self.assertFalse(audio.voices,key);setattr(obj,key,before)
            audio.update(1.);g.player.position.update(288,1660);audio.update(0)
            self.assertFalse(audio.voices)
            g.player.position.update(2060,360);audio.update(1.)
            g.world=NS();audio.update(0);self.assertFalse(audio.voices)
        finally:audio.stop()

    def test_inspection_needs_no_reward_or_transfer_and_never_invents_an_absent_companion(self):
        for active in (('caelan','mira'),('caelan',)):
            g=self.effect_fixture();g.party=NS(active_ids=active)
            g.player.position.update(2070,344);g.social.start_script=Mock(return_value=True)
            owner=SanctuaryCave(g);before=owner.to_dict()
            self.assertTrue(owner.interact())
            lines=g.social.start_script.call_args.args[0]
            if 'mira' in active:self.assertEqual([line['speaker'] for line in lines],['mira','caelan','mira'])
            else:self.assertEqual([line['speaker'] for line in lines],['caelan'])
            self.assertFalse(any('bridge' in line['text'].lower() for line in lines))
            self.assertIs(g.world,self.world);self.assertEqual(owner.to_dict(),before)

    def test_chasm_ambience_is_bounded_original_pcm(self):
        data=samples('chasm',8000,1)
        self.assertEqual(len(data),48000)
        self.assertGreater(max(map(abs,data)),0)
        self.assertLess(max(map(abs,data)),5000)
