"""The reserve arrival replays its live controller without touching a journey."""
import gc,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from main import Game
from cutscene_gallery import GALLERY_BY_ID


class SanctuaryArrivalGalleryTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.path=Path(self.folder.name)/'journey.json'
        self.settings=Path(self.folder.name)/'settings.json'
        self.games=[]

    def tearDown(self):
        for game in self.games:
            if game.gallery_session is not None:game.gallery_session.close()
            game.regional_audio.reset();game.music.stop()
        self.games.clear();pygame.quit();gc.collect()

    def game(self, title=True):
        game=Game(fullscreen=False,start_on_title=title,save_path=self.path,settings_path=self.settings)
        game.audio.effects_volume=0;self.games.append(game);pygame.event.clear()
        return game

    def launch(self, parent):
        self.assertTrue(parent.open_gallery())
        self.assertTrue(parent.launch_gallery_scene('sanctuary_arrival'),parent.gallery.error)
        self.assertIsNotNone(parent.gallery_session)
        return parent.gallery_session

    def key(self,parent,key):
        return parent.handle_events([pygame.event.Event(pygame.KEYDOWN,key=key,repeat=False),
                                     pygame.event.Event(pygame.KEYUP,key=key)])

    def test_actual_scene_completes_and_preserves_saved_journey_parent_roster_and_settings(self):
        seed=self.game(False);self.assertTrue(seed.save_progress());seed.music.stop()
        raw=self.path.read_bytes()
        parent=self.game();before=parent._progress_signature()
        settings=self.settings.read_bytes() if self.settings.exists() else None
        session=self.launch(parent);child=session.game
        first_composition_checked=False;rail_opened=False
        blocked_count=child.world.blocked.count()
        self.assertTrue(child._is_gallery_preview);self.assertFalse(child.save_store.enabled)
        self.assertEqual(child.world.data['id'],'elden_vale_sanctuary')
        with patch.object(child.save_store,'write',side_effect=AssertionError('Gallery wrote a journey')):
            for frame in range(4500):
                if child.sanctuary_arrival.dialogue is not None and child.sanctuary_arrival.beat==0:
                    viewport=pygame.Rect(child.camera.position(),(480,320))
                    for key in ('caelan','mira','lucan','aldric','page','caretaker'):
                        self.assertTrue(viewport.collidepoint(child.sanctuary_arrival.actors[key].position),key)
                    first_composition_checked=True
                if child.sanctuary_arrival.completed:
                    rope=child.sanctuary_arrival.rail
                    rail=rope.record
                    posts=child.world.image(rope.art['posts'])
                    self.assertTrue(rope.opened)
                    self.assertEqual(rail['rect'].size,posts.get_size())
                    self.assertEqual(rail['position'],rope.art['position'])
                    self.assertEqual(child.world.blocked.count(),blocked_count)
                    rail_opened=True
                if child.social.active or child.sanctuary_arrival.dialogue is not None:
                    self.assertTrue(self.key(parent,pygame.K_SPACE))
                parent.update(.1)
                if parent.gallery_session is None:break
                if frame%5==0:parent.draw()
            else:self.fail('The arrival scene did not reach its Gallery boundary')
        self.assertTrue(first_composition_checked);self.assertTrue(rail_opened)
        self.assertTrue(session.playback.finished);self.assertTrue(session.closed)
        self.assertIsNone(parent.gallery.error)
        self.assertEqual(parent._progress_signature(),before)
        self.assertEqual(self.path.read_bytes(),raw)
        self.assertEqual(self.settings.read_bytes() if self.settings.exists() else None,settings)
        self.assertFalse(child.combat.active)
        self.assertEqual(child.world.data['id'],'elden_vale_sanctuary')

    def test_pause_focus_restart_and_early_exit_remain_inside_disposable_runtime(self):
        parent=self.game();before=parent._progress_signature()
        session=self.launch(parent);child=session.game
        parent.update(.2);self.assertTrue(session._cinematic_active())
        self.assertTrue(self.key(parent,pygame.K_p))
        self.assertTrue(child.sanctuary_arrival.paused)
        elapsed=child.sanctuary_arrival.elapsed
        parent.update(2);self.assertEqual(child.sanctuary_arrival.elapsed,elapsed)
        self.assertTrue(self.key(parent,pygame.K_p));self.assertFalse(child.sanctuary_arrival.paused)
        parent.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        elapsed=child.sanctuary_arrival.elapsed
        parent.update(2);self.assertEqual(child.sanctuary_arrival.elapsed,elapsed)
        parent.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.assertTrue(self.key(parent,pygame.K_r))
        self.assertIsNot(parent.gallery_session,session)
        self.assertTrue(session.closed)
        self.assertEqual(parent.gallery_session.entry.id,'sanctuary_arrival')
        self.assertTrue(self.key(parent,pygame.K_ESCAPE))
        self.assertIsNone(parent.gallery_session)
        self.assertEqual(parent._progress_signature(),before)
        self.assertFalse(self.path.exists());self.assertFalse(self.settings.exists())

    def test_entry_is_the_live_arrival_with_local_thumbnail(self):
        entry=GALLERY_BY_ID['sanctuary_arrival']
        self.assertIn('Emergency Arrival',entry.name)
        self.assertEqual(entry.thumbnail,'assets/ui/gallery/sanctuary_arrival.png')
        self.assertTrue((Path(__file__).resolve().parents[1]/entry.thumbnail).exists())
        self.assertIn('P: pause',entry.controls)
