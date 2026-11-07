"""Reserve atmosphere uses scenery depth and bounded environmental audio."""
from array import array
import json
import math
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame

from audio_settings import AudioSettings
from elden_vale_sanctuary import SanctuaryReserveWorld
from regional_audio import DURATIONS, RegionalAudio, Source, samples
from sanctuary_atmosphere import SanctuaryAtmosphere


class SanctuaryParticleTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.display.set_mode((480,320))
        self.addCleanup(pygame.quit)

    def test_particle_count_and_surfaces_are_bounded_and_reduced_motion_is_static(self):
        world=NS(data={'fantasy_effects':{'grove':{'center':[120,100],
            'radius':[40,30],'count':200,'petal_count':200}}})
        field=SanctuaryAtmosphere(world)
        self.assertEqual(len(field.records),field.MAX_MOTES+field.MAX_PETALS)
        cached={id(surface) for surface in field._motes}
        cached.update(id(surface) for frames in field._petals for surface in frames)
        field.update(1200)
        moving=field.snapshot()['positions']
        field.update(7600)
        self.assertNotEqual(field.snapshot()['positions'],moving)
        self.assertTrue(all(id(record['surfaces'][0]) in cached for record in field.records))
        field.update(1200,reduced_motion=True)
        still=[(record['position'],id(record['surfaces'][0])) for record in field.records]
        field.update(120000,reduced_motion=True)
        self.assertEqual(still,[(record['position'],id(record['surfaces'][0])) for record in field.records])
        self.assertEqual(field.snapshot()['cached_surfaces'],len(cached))

    def test_authored_petal_frames_are_loaded_once_at_the_native_scale(self):
        root=Path(__file__).resolve().parents[1]
        loaded=[]
        def image(path):
            loaded.append(path)
            return pygame.image.load(root/path).convert_alpha()
        world=NS(image=image,data={'fantasy_effects':{'grove':{
            'center':[120,100],'radius':[40,30],'count':8,'petal_count':4,
            'petal_manifest':'assets/terrain/sanctuary_fantasy/grove/assets.json'}}})
        field=SanctuaryAtmosphere(world)
        self.assertEqual(len(loaded),9)
        self.assertEqual({surface.get_size() for frames in field._petals for surface in frames},{(8,8)})
        for clock in (0,800,2400,12000):field.update(clock)
        self.assertEqual(len(loaded),9,'Drawing must not load or rescale authored petal frames')

    def make_world(self,entities=()):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        root=Path(directory.name)
        def image(name,color,size=(480,320)):
            surface=pygame.Surface(size,pygame.SRCALPHA);surface.fill(color)
            path=root/(name+'.png');pygame.image.save(surface,path);return str(path)
        ground=image('ground','#203d31');collision=image('collision','black')
        records=[]
        for record in entities:
            colors=record.pop('colors');size=record.pop('size')
            frames=[image(record['id']+str(index),color,size) for index,color in enumerate(colors)]
            records.append({**record,'frames':frames,'frame_duration_ms':100,'phase_offset':0})
        data={'id':'elden_vale_sanctuary','name':'Reserve','size_pixels':[480,320],
              'ground_frames':[ground],'ground_frame_duration_ms':200,
              'collision':collision,'overview':ground,'player_probe_size':[24,12],
              'player_draw_anchor':[4,18],'spawn':[120,108],
              'entities':records,'foreground':[],'npcs':[],
              'landmarks':[{'name':'Grove','position':[120,100]}],
              'fantasy_effects':{'grove':{'center':[120,100],'radius':[0,0],
                  'count':1,'petal_count':0}}}
        path=root/'map.json';path.write_text(json.dumps(data))
        return SanctuaryReserveWorld(path)

    @staticmethod
    def actor(position=(120,108),visible=True):
        sprite=pygame.Surface((8,20),pygame.SRCALPHA);sprite.fill('#d49b62')
        return NS(position=pygame.Vector2(position),story_visible=visible,sprite=lambda:sprite)

    def test_roof_and_actor_occlude_motes_in_the_normal_world_depth_pass(self):
        for roof in (False,True):
            with self.subTest(roof=roof):
                entities=([{'id':'roof','position':[110,90],'sort_y':130,
                            'colors':['#8e7868'],'size':(24,24)}] if roof else [])
                world=self.make_world(entities)
                actor=self.actor(visible=not roof)
                bare=pygame.Surface((480,320));covered=bare.copy()
                world.atmosphere.enabled=False
                world.draw(bare,(0,0),actor,0,False)
                world.atmosphere.enabled=True
                world.draw(covered,(0,0),actor,0,False)
                self.assertEqual(pygame.image.tobytes(bare,'RGB'),
                                 pygame.image.tobytes(covered,'RGB'))
        # With neither occluder, the exact same mote must be visible.
        world=self.make_world();actor=self.actor(visible=False)
        world.atmosphere.enabled=False;world.draw(bare,(0,0),actor,0,False)
        world.atmosphere.enabled=True;world.draw(covered,(0,0),actor,0,False)
        self.assertNotEqual(pygame.image.tobytes(bare,'RGB'),pygame.image.tobytes(covered,'RGB'))

    def test_optional_asset_animation_freezes_without_changing_other_scenery(self):
        world=self.make_world([
            {'id':'crystal','position':[200,100],'sort_y':110,'size':(8,8),
             'colors':['#b482d1','#e0c3ed'],'reduced_motion_frame':0},
            {'id':'ordinary','position':[220,100],'sort_y':110,'size':(8,8),
             'colors':['#836137','#c5a267']}])
        actor=self.actor(visible=False);target=pygame.Surface((480,320))
        world.reduced_motion=True
        world.draw(target,(0,0),actor,100,False)
        self.assertEqual(target.get_at((202,102)),pygame.Color('#b482d1'))
        self.assertEqual(target.get_at((222,102)),pygame.Color('#c5a267'))
        world.reduced_motion=False
        world.draw(target,(0,0),actor,100,False)
        self.assertEqual(target.get_at((202,102)),pygame.Color('#e0c3ed'))


class Channel:
    def __init__(self):self.sound=None;self.gain=0;self.loops=None
    def get_sound(self):return self.sound
    def stop(self):self.sound=None
    def set_volume(self,value):self.gain=value
    def play(self,sound,loops=0):self.sound=sound;self.loops=loops


class SanctuaryAudioTests(unittest.TestCase):
    def setUp(self):
        self.game=NS(audio=AudioSettings(None),player=NS(position=pygame.Vector2()),
            overworld_travel=NS(active=False),on_title=False,opening_cinematic=NS(active=False),
            regent_arrival=NS(active=False,state='done'),combat=NS(active=False),
            pause=NS(is_open=False),inventory_ui=NS(is_open=False),party_ui=NS(is_open=False),
            world_map_viewer=NS(is_open=False),map_open=False,quest_ui=NS(journal_open=False),
            _music_focused=True,world=NS(is_sanctuary_reserve=True,data={'fantasy_effects':{
                'crystals':[{'position':[0,0],'near':20,'far':200}],
                'spring':{'position':[20,0],'near':20,'far':200}}}))
        self.audio=RegionalAudio(self.game);self.channels=[]
        def channel():
            result=Channel();self.channels.append(result);return result
        patcher=patch('regional_audio.pygame.mixer.find_channel',side_effect=channel)
        patcher.start();self.addCleanup(patcher.stop)
        patcher=patch.object(self.audio,'_sound',side_effect=lambda name:object())
        patcher.start();self.addCleanup(patcher.stop)

    def test_two_quiet_local_beds_attenuate_and_release_on_hall_or_region_transfer(self):
        self.audio.update(.1)
        self.assertEqual(set(self.audio.voices),{'sanctuary.crystal.0','sanctuary.spring'})
        self.assertTrue(all(channel.loops==-1 for channel in self.channels))
        near=self.channels[0].gain
        self.game.player.position.update(110,0);self.audio.update(.1)
        self.assertLess(self.channels[0].gain,near)
        old=list(self.channels)
        self.game.world=NS(region={'terrain':{'rivers':[{'points':[(0,0),(0,10)],'width':2}]}})
        self.game.overworld_travel.active=True
        self.audio.update(.1)
        self.assertTrue(all(channel.sound is None for channel in old))
        self.assertEqual(set(self.audio.voices),{'river'})
        self.game.world=NS(data={'id':'elden_vale_sanctuary_hall'})
        self.game.overworld_travel.active=False
        self.audio.update(0)
        self.assertFalse(self.audio.voices)

    def test_modals_focus_combat_mute_and_reset_release_all_reserve_voices(self):
        for owner,field in ((self.game.pause,'is_open'),(self.game.party_ui,'is_open'),
                            (self.game,'_music_focused'),(self.game.combat,'active'),
                            (self.game,'map_open'),(self.game.quest_ui,'journal_open')):
            with self.subTest(field=field):
                self.audio.reset();self.audio.update(.1);self.assertTrue(self.audio.voices)
                prior=getattr(owner,field);setattr(owner,field,not prior)
                self.audio.update(0);self.assertFalse(self.audio.voices)
                setattr(owner,field,prior)
        self.audio.reset();self.audio.update(.1)
        self.game.audio.set_effects(0);self.assertFalse(self.audio.voices)
        self.game.audio.set_effects(1);self.audio.update(1)
        self.assertTrue(self.audio.voices)
        self.audio.reset();self.assertFalse(self.audio.voices)
        self.assertEqual(self.audio.clock,0)

    def test_stale_bed_backend_failure_is_nonfatal_and_never_stops_a_foreign_sound(self):
        class UnavailableChannel:
            def get_sound(self):raise pygame.error('backend unavailable')
            def stop(self):raise AssertionError('No verified channel ownership')
        for paused in (False,True):
            with self.subTest(paused=paused):
                self.audio.reset();self.game.pause.is_open=paused
                self.game.world=NS(region={'terrain':{}})
                self.game.overworld_travel.active=True
                source=Source('old.river','river','water',(0,0),ambient=True)
                self.audio.voices[source.key]=(source,UnavailableChannel(),object(),0.)
                foreign=Channel();foreign.sound=object();unowned=foreign.sound
                other=Source('old.crystal','crystal','mineral',(0,0),ambient=True)
                self.audio.voices[other.key]=(other,foreign,object(),0.)
                self.audio.update(0)
                self.assertFalse(self.audio.voices)
                self.assertTrue(self.audio.failed)
                self.assertIs(foreign.sound,unowned)

    def test_new_material_pcm_is_original_quiet_deterministic_and_loop_bounded(self):
        fingerprints=[]
        for name in ('crystal','spring'):
            with self.subTest(sound=name):
                pcm=samples(name,8000,1)
                self.assertIsInstance(pcm,array)
                self.assertEqual(len(pcm),round(8000*DURATIONS[name]))
                self.assertEqual(pcm,samples(name,8000,1))
                self.assertTrue(500<max(abs(value) for value in pcm)<6000)
                rms=math.sqrt(sum(value*value for value in pcm)/len(pcm))
                self.assertTrue(100<rms<1500)
                self.assertLess(abs(pcm[-1]-pcm[0]),1500)
                stereo=samples(name,8000,2)
                self.assertEqual(stereo[::2],pcm);self.assertEqual(stereo[1::2],pcm)
                fingerprints.append(pcm.tobytes())
        self.assertNotEqual(*fingerprints)


if __name__=='__main__':unittest.main()
