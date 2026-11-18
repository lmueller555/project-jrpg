"""Native art survives saved journeys, scene ownership and real presentation."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame

from save_game import SaveStore
from tools.capture_sanctuary_rescue import make_game

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'docs/reviews/iselin_native_integration'
DIRECTIONS=('front','left','right','back')


class NativeIntegrationTests(unittest.TestCase):
    def game(self,directory,*,title=False):
        game=make_game(directory,seed=False,embedded=False,title=title)
        self.addCleanup(pygame.quit)
        self.addCleanup(game.music.stop)
        return game

    def native(self,actor):
        self.assertEqual(actor.draw_anchor,(12,30))
        self.assertEqual(actor.blocker.size,(8,4))
        self.assertIsNone(getattr(actor,'detailed_sprite',None))
        self.assertEqual(set(actor.idles),set(DIRECTIONS))
        self.assertEqual(set(actor.walks),set(DIRECTIONS))
        for direction in DIRECTIONS:
            self.assertEqual(actor.walk_durations[direction],(35,)*16)
            self.assertTrue(all(image.get_size()==(24,36) for image in actor.walks[direction]))

    def test_approved_native_art_and_portrait_are_preserved_byte_for_byte(self):
        baseline=json.loads((REVIEW/'approved_assets.json').read_text())
        self.assertEqual(baseline['png_count'],69)
        for path,digest in baseline['sha256'].items():
            with self.subTest(path=path):self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(),digest)

    def test_preintegration_save_continues_without_replaying_or_changing_quest_facts(self):
        payload=json.loads((REVIEW/'legacy_escorting_save.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(SaveStore(Path(directory)/'journey.json').write(payload))
            game=self.game(directory,title=True)
            self.assertTrue(game.has_saved_journey,game.save_error)
            self.assertTrue(game.begin_journey(True),game.save_error)
            self.assertEqual(game.regent_quest.stage,'escorting')
            self.assertEqual(game.quests.to_dict(),payload['quests'])
            self.assertEqual(game.inventory.to_dict(),payload['inventory'])
            self.assertEqual(game.world.data['id'],payload['player']['scene'])
            self.assertEqual(list(game.player.position),payload['player']['position'])
            actor=game.regent_quest.iselin
            self.native(actor)
            self.assertTrue(actor.story_visible)
            self.assertEqual(actor.sprite(0).get_size(),(24,36))
            game.opening_fade=0
            game.camera.focus(actor.position,duration=0)
            game.draw()
            self.assertFalse(game.canvas.patches)

    def test_sanctuary_clone_uses_native_source_and_completion_returns_same_owner(self):
        from cutscene_gallery import _regent_checkpoint,_station
        with tempfile.TemporaryDirectory() as directory:
            game=self.game(directory)
            _regent_checkpoint(game,'sanctuary_arrival_pending')
            game._sync_story_party()
            _station(game,game._scene_by_id('elden_vale_sanctuary'),(444,642),'back')
            owner=game.regent_quest
            source=owner.iselin
            scene=game.sanctuary_arrival
            self.assertTrue(scene.maybe_start())
            clone=scene.actors['iselin']
            self.native(clone)
            self.assertFalse(source.story_visible)
            for direction in DIRECTIONS:
                clone.moving=True;clone.facing=direction;clone.walk_ms=105
                self.assertEqual(pygame.image.tobytes(clone.sprite(0),'RGBA'),
                                 pygame.image.tobytes(source.walks[direction][3],'RGBA'))
            # Restore the acknowledged completed checkpoint rather than award
            # completion, resources or quest progress through this art fixture.
            before=deepcopy(game.quests.to_dict())
            self.assertTrue(scene.restore({'version':1,'beat':7,'completed':True,'cave_entered':False}))
            scene.sync_residents()
            self.assertIs(owner.iselin,source)
            self.native(source)
            self.assertEqual(game.quests.to_dict(),before)

    def test_live_native_actor_freezes_under_pause_and_conversation_selects_idle(self):
        with tempfile.TemporaryDirectory() as directory:
            game=self.game(directory)
            actor=game.regent_quest.iselin
            actor.story_visible=True
            game.regent_quest._place(actor,game.town,(384,480))
            game.world=game.town;game.player.position.update(550,432)
            game.regent_quest._move(actor,(550,480),.105,74)
            before=(tuple(actor.position),actor.walk_ms)
            self.assertTrue(actor.moving)
            walking=actor.sprite(0)
            game.pause.open();game.update(.3,(0,0),False)
            self.assertEqual((tuple(actor.position),actor.walk_ms),before)
            game.pause.close()
            actor.request_conversation('left')
            self.assertIs(actor.sprite(0),actor.idles['left'])
            game.draw()
            actor.end_conversation()
            self.assertIs(actor.sprite(0),walking)
            self.assertFalse(game.canvas.patches)

    def test_native_arrival_gallery_pause_focus_and_close_preserve_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            game=self.game(directory,title=True)
            parent=(game.world,game.player.position.copy(),deepcopy(game.quests.to_dict()))
            self.assertTrue(game.open_gallery())
            self.assertTrue(game.launch_gallery_scene('regent_arrival'))
            session=game.gallery_session
            scene=session.game.regent_arrival
            scene.phase_index=next(i for i,p in enumerate(scene.data['phases']) if p['id']=='gate_admission')
            scene.phase_time=2
            before=(scene.phase_index,scene.phase_time,scene.elapsed)
            scene.paused=True;session.game.update(.25,(0,0),False)
            self.assertEqual((scene.phase_index,scene.phase_time,scene.elapsed),before)
            scene.paused=False
            scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
            session.game.update(.25,(0,0),False)
            self.assertEqual((scene.phase_index,scene.phase_time,scene.elapsed),before)
            scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
            session.game.update(.035,(0,0),False)
            self.assertGreater(scene.phase_time,before[1])
            game.draw()
            session.close()
            self.assertIs(game.world,parent[0])
            self.assertEqual(game.player.position,parent[1])
            self.assertEqual(game.quests.to_dict(),parent[2])
