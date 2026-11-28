"""Controller ownership/clock fixtures, not production artwork acceptance.

The synthetic owners reserve native-size slots without decoding pictures.
Geometry and final imagery receive separate rig, export and Gallery reviews.
"""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from fire_veinhold_opening import FireVeinholdOpening

FRAME_BYTES = 960*640*4


class AudioFixture:
    def __init__(self, game):
        self.starts = []
        self.updates = []

    def reset(self):pass
    def stop(self):pass
    def pause(self):pass
    def resume(self):pass
    def prepare_ascent(self):pass
    def start(self, seconds=0):self.starts.append(seconds)
    def update(self, before, after, **kwargs):self.updates.append((before, after))


class OwnerFixture:
    records = []
    owners = []
    kind = 'prefix'
    duration = 42.

    def __init__(self, path, **kwargs):
        self.path = Path(path)
        self.slots = 0
        self.owners.append(self)

    def validate_duration(self, seconds):
        if seconds != self.duration:raise ValueError('Wrong fixture duration')

    def validate_segment(self, segment, seconds):self.validate_duration(seconds)

    @property
    def cache_info(self):
        return {'bytes':self.slots*FRAME_BYTES, 'surfaces':self.slots}

    def preload(self, *args, max_slots=None, **kwargs):
        self.slots = min(8, max_slots or 8)
        self.records.append((self.kind, 'preload', self.slots,
                             sum(owner.slots for owner in self.owners)))

    def samples(self, *args, **kwargs):
        seconds = args[1] if isinstance(args[0], str) else args[0]
        return {'local_time':seconds, 'phase':self.kind,
                'camera':{'fixture_time':seconds}, 'segment':'prefix'}

    def draw(self, target, state, **kwargs):
        self.preload(0.)
        target.fill('#234567' if self.kind == 'bridge_ascent' else '#123456')

    def close(self):
        self.slots = 0
        self.records.append((self.kind, 'close', 0,
                             sum(owner.slots for owner in self.owners)))


class FaceFixture(OwnerFixture):
    kind = 'face_reveal'
    duration = 5.


class AscentFixture(OwnerFixture):
    kind = 'bridge_ascent'
    duration = 8.


class AscentControllerTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 640))
        OwnerFixture.records = []
        OwnerFixture.owners = []
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'scene.json'
        data = {'version':1, 'id':'fire_veinhold_opening', 'render_size':[960,640],
                'logical_size':[480,320], 'shots':[
                    {'id':'prefix', 'gallery_id':'prefix_fixture', 'name':'Prefix fixture',
                     'description':'Synthetic clock fixture', 'type':'perspective_sequence',
                     'duration':42, 'sequence':'prefix.json', 'segment':'prefix'},
                    {'id':'face_reveal', 'gallery_id':'faces_fixture', 'name':'Faces fixture',
                     'description':'Synthetic face ownership fixture', 'type':'face_reveal',
                     'duration':5, 'performance':'faces.json'},
                    {'id':'bridge_ascent', 'gallery_id':'ascent_fixture', 'name':'Ascent fixture',
                     'description':'Synthetic ascent ownership fixture', 'type':'bridge_ascent',
                     'duration':8, 'performance':'ascent.json'}]}
        self.path.write_text(json.dumps(data))
        self.game = SimpleNamespace(audio=SimpleNamespace(reduced_motion=False,effects_volume=0),
                                    _music_focused=True,to_canvas=lambda point:point)
        for name, value in [('CinematicPerspective',OwnerFixture),
                            ('CinematicFaceReveal',FaceFixture),
                            ('PrologueFlightAudio',AudioFixture),('PrologueAlertAudio',AudioFixture)]:
            context = patch('fire_veinhold_opening.'+name,value)
            context.start();self.addCleanup(context.stop)
        context = patch.dict('sys.modules', {'cinematic_bridge_ascent':SimpleNamespace(
            CinematicBridgeAscent=AscentFixture)})
        context.start();self.addCleanup(context.stop)
        self.players = []

    def tearDown(self):
        for player in self.players:player.reset()
        pygame.quit()

    def player(self, shot_id=None):
        player = FireVeinholdOpening(self.game,shot_id,scene_path=self.path)
        self.players.append(player)
        return player

    def test_standalone_has_global47_offset_and_same_state_as_full_film(self):
        complete = self.player()
        single = self.player('bridge_ascent')
        self.assertEqual((complete.duration,single.duration,single.global_offset),(55.,8.,47.))
        for seconds in (0.,.5,1.5,4.,7.999,8.):
            self.assertEqual(complete.state_at(47.+seconds),single.state_at(seconds))
        single.start()
        self.assertEqual(single.alert_audio.starts,[47.])
        self.assertEqual(single.flight_audio.starts,[47.])
        self.assertEqual(single._face_reveals,{})

    def test_handoff_prefetch_is_four_then_drains_faces_before_active_eight(self):
        scene = self.player();scene.start()
        scene.update(42.)
        scene.update(4.5)
        face = next(iter(scene._face_reveals.values()))
        ascent = next(iter(scene._bridge_ascents.values()))
        self.assertEqual((face.slots,ascent.slots),(8,4))
        self.assertEqual(face.cache_info['bytes']+ascent.cache_info['bytes'],12*FRAME_BYTES)
        scene.render_frame(46.5)
        self.assertEqual((face.slots,ascent.slots),(8,4))
        scene.update(.5)
        self.assertEqual((face.slots,ascent.slots),(0,8))
        self.assertTrue(all(owner.slots==0 for owner in scene._perspectives.values()))
        self.assertEqual(scene.alert_audio.starts,[0.])
        self.assertEqual(scene.alert_audio.updates[-1],(46.5,47.))
        active = [row for row in OwnerFixture.records if row[:3]==('bridge_ascent','preload',8)]
        self.assertTrue(active)
        self.assertTrue(all(row[3]==8 for row in active))

    def test_pause_focus_and_host_focus_freeze_the_ascent_clock(self):
        scene=self.player('bridge_ascent');scene.start();scene.update(1.25)
        before=scene.state_at(scene.elapsed)
        pause=pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,repeat=False)
        scene.handle_event(pause);scene.update(.5)
        self.assertEqual(scene.state_at(scene.elapsed),before)
        scene.handle_event(pause)
        scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST));scene.update(.5)
        self.assertEqual(scene.state_at(scene.elapsed),before)
        scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.game._music_focused=False;scene.update(.5)
        self.assertEqual(scene.state_at(scene.elapsed),before)
        self.game._music_focused=True;scene.update(.25)
        self.assertEqual(scene.elapsed,1.5)

    def test_completion_at_eight_has_no_extra_endpoint_tick_and_releases_all_owners(self):
        for fps in (15,30,60,120):
            with self.subTest(fps=fps):
                scene=self.player('bridge_ascent');calls=[];scene.start(lambda:calls.append('done'))
                for _ in range(8*fps-1):scene.update(1/fps)
                self.assertTrue(scene.active)
                scene.update(1/fps)
                self.assertEqual((scene.elapsed,scene.finished_reason,calls),(8.,'completed',['done']))
                self.assertTrue(all(owner.slots==0 for owner in scene._bridge_ascents.values()))
                scene.update(5.);scene.skip();self.assertEqual(calls,['done'])

    def test_backward_picture_seek_closes_ascent_without_advancing_clock(self):
        scene=self.player();scene.start();scene.update(47.)
        self.assertTrue(any(owner.slots for owner in scene._bridge_ascents.values()))
        before=scene.elapsed
        scene._preload_at(44.,blocking=True)
        self.assertTrue(all(owner.slots==0 for owner in scene._bridge_ascents.values()))
        picture=scene.render_frame(44.)
        self.assertEqual(picture.get_at((0,0))[:3],(18,52,86))
        self.assertEqual(scene.elapsed,before)
        self.assertTrue(all(owner.slots==0 for owner in scene._bridge_ascents.values()))
        picture=scene.render_frame(48.)
        self.assertEqual(picture.get_at((0,0))[:3],(35,69,103))
        self.assertTrue(all(owner.slots==0 for owner in scene._face_reveals.values()))

    def test_backward_seek_drains_incoming_prefetch_outside_its_lookahead(self):
        scene=self.player();scene.start();scene.update(42.);scene.update(4.5)
        ascent=next(iter(scene._bridge_ascents.values()))
        self.assertFalse(scene._ascent_active)
        self.assertEqual(ascent.slots,4)
        before=scene.elapsed
        for seek in (44.,20.):
            for method in ('preload','render'):
                with self.subTest(seek=seek,method=method):
                    scene._preload_at(46.5,blocking=True)
                    self.assertEqual(ascent.slots,4)
                    if method=='preload':scene._preload_at(seek,blocking=True)
                    else:scene.render_frame(seek)
                    self.assertEqual(ascent.slots,0)
                    self.assertFalse(scene._ascent_active)
                    self.assertEqual(scene.elapsed,before)

    def test_skip_restart_and_completion_do_not_retain_ascent_reservations(self):
        scene=self.player('bridge_ascent');calls=[];scene.start(lambda:calls.append('skip'))
        scene.update(2.);scene.skip();scene.skip()
        self.assertEqual(calls,['skip'])
        self.assertTrue(all(owner.slots==0 for owner in scene._bridge_ascents.values()))
        scene.start();self.assertEqual(scene.elapsed,0.)
        self.assertEqual(scene.state_at(0.)['global_time'],47.)
        scene.reset();self.assertTrue(all(owner.slots==0 for owner in scene._bridge_ascents.values()))

    def test_invalid_later_bank_discards_every_partially_loaded_owner(self):
        class InvalidAscent(AscentFixture):
            def validate_duration(self, seconds):
                self.slots=4
                raise ValueError('Invalid ascent bank fixture')
        with patch.dict('sys.modules',{'cinematic_bridge_ascent':SimpleNamespace(
                CinematicBridgeAscent=InvalidAscent)}):
            scene=self.player()
            with self.assertRaisesRegex(ValueError,'Invalid ascent bank'):scene.start()
        self.assertEqual(scene._assets,{})
        self.assertEqual(scene._bridge_ascents,{})
        self.assertEqual(scene._face_reveals,{})
        self.assertTrue(all(owner.slots==0 for owner in OwnerFixture.owners))

    def test_failed_ascent_preload_releases_reservations_and_can_restart(self):
        class FailedPreload(AscentFixture):
            fail=True
            def preload(self,*args,**kwargs):
                super().preload(*args,**kwargs)
                if self.fail:raise ValueError('Ascent decode fixture')
        with patch.dict('sys.modules',{'cinematic_bridge_ascent':SimpleNamespace(
                CinematicBridgeAscent=FailedPreload)}):
            scene=self.player('bridge_ascent')
            with self.assertRaisesRegex(ValueError,'Ascent decode'):scene.start()
            self.assertFalse(scene.active)
            self.assertFalse(scene._ascent_active)
            self.assertTrue(all(owner.slots==0 for owner in OwnerFixture.owners))
            FailedPreload.fail=False
            scene.start()
            self.assertTrue(scene.active)
            self.assertEqual(scene.alert_audio.starts,[47.])


if __name__=='__main__':unittest.main()
