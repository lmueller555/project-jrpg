"""Production composition stays isolated while rig artwork/controls are sought."""
from copy import deepcopy
import gc
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from cutscene_gallery import GALLERY_BY_ID
from main import Game
from mira_rig_preview import MiraRigPreview, POSES


class MiraRigPreviewTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init();pygame.display.set_mode((960, 640))
        self.game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                         _preview_window=pygame.Surface((960, 640)))
        self.study = MiraRigPreview(self.game)

    def tearDown(self):
        self.game.music.stop();self.game.opening_audio.reset()
        self.study = self.game = None
        pygame.quit();gc.collect()

    def test_pose_art_and_local_allocation_never_execute_actions_or_change_progress(self):
        before = self.game._progress_signature()
        resources = [(actor.identifier, actor.hp, actor.mp, actor.atb)
                     for actor in (*self.study.model.party, *self.study.model.enemies)]
        self.assertEqual(self.study.model.bots, ())
        self.study.rig.adjust('support', -1)
        self.study.rig.adjust('weapons', 1)
        self.assertTrue(self.study.rig.commit())
        for index, (state, _) in enumerate(POSES):
            self.assertIn(state, self.study.scene.mira_art.animations)
            self.study.select_pose(index)
            self.study.update(.05);self.study.draw()
        self.assertIsNone(self.study.model.current_action)
        self.assertEqual(resources, [(actor.identifier, actor.hp, actor.mp, actor.atb)
                                    for actor in (*self.study.model.party, *self.study.model.enemies)])
        self.assertEqual(self.game._progress_signature(), before)
        self.assertFalse(self.game.combat.active)
        self.assertFalse(self.game.save_store.enabled)

    def test_controls_freeze_on_focus_loss_and_render_inside_both_formations(self):
        for count in (2, 3):
            self.study.party_count = count;self.study._make_scene()
            for scale in (1., 1.5):
                with self.subTest(count=count, scale=scale):
                    self.game.audio.set_text_scale(scale);self.study.draw()
                    space = self.study.scene.party_rows['mira']['interactable']
                    self.assertTrue(space.contains(self.study.rig.rect))
                    for rect in self.study.rig.buttons.values():self.assertTrue(space.contains(rect))
                    for rect in self.study.buttons.values():
                        self.assertTrue(self.study.scene.commands_panel.contains(rect))
        self.study.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        elapsed = self.study.elapsed
        self.study.update(2.)
        self.study.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHTBRACKET)])
        self.assertEqual(self.study.elapsed, elapsed)
        self.study.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.study.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHTBRACKET)])
        self.assertEqual(self.study.state, 'attack')

    def test_gallery_fixture_is_bounded_and_does_not_recruit_preview_cast(self):
        before_party = deepcopy(self.game.party.to_dict())
        entry = GALLERY_BY_ID['mira_arm_rig']
        playback = entry.start(self.game)
        self.assertIsInstance(playback.review, MiraRigPreview)
        playback.review.draw()
        self.assertEqual(self.game.party.to_dict(), before_party)
        playback.update(45.)
        self.assertTrue(playback.settling)
        playback.update(.7)
        self.assertTrue(playback.finished)


class MiraRigGallerySessionTests(unittest.TestCase):
    def test_gallery_forwards_art_controls_and_exit_preserves_parent_files(self):
        with tempfile.TemporaryDirectory(prefix='mira-rig-gallery-') as folder:
            path = Path(folder)/'journey.json';settings = Path(folder)/'settings.json'
            path.write_text('{"sentinel":"existing journey"}\n')
            parent = Game(window_size=(960, 704), fullscreen=False,
                          save_path=path, settings_path=settings)
            before = path.read_bytes()
            try:
                self.assertTrue(parent.open_gallery())
                self.assertTrue(parent.launch_gallery_scene('mira_arm_rig'))
                session = parent.gallery_session
                study = session.playback.review
                session.draw()
                session.handle_events([pygame.event.Event(pygame.KEYDOWN,
                    key=pygame.K_RIGHTBRACKET, repeat=False)])
                self.assertEqual(study.state, 'attack')
                session.handle_events([pygame.event.Event(pygame.KEYDOWN,
                    key=pygame.K_3, repeat=False)])
                self.assertEqual(len(study.model.party), 3)
                session.update(.1);session.draw()
                # Focused Space commits routing; it does not toggle art playback.
                session.handle_events([pygame.event.Event(pygame.KEYDOWN,
                    key=pygame.K_TAB, repeat=False)])
                self.assertTrue(study.rig.focused)
                study.rig.adjust('support', -1);study.rig.adjust('weapons', 1)
                session.handle_events([pygame.event.Event(pygame.KEYDOWN,
                    key=pygame.K_SPACE, repeat=False)])
                self.assertEqual(study.rig.allocation['weapons'], 3)
                self.assertTrue(study.playing)
                # First Escape cancels the console, a second leaves the review.
                session.handle_events([pygame.event.Event(pygame.KEYDOWN,
                    key=pygame.K_ESCAPE, repeat=False)])
                self.assertIsNotNone(parent.gallery_session)
                self.assertFalse(study.rig.focused)
                # A real viewport-offset click selects skill art, not an action.
                session.draw()
                logical = study.buttons['bulwark'].center
                child = session.game
                canvas_scale, _, canvas_origin = child._ensure_ui_surface()
                position = (round(session.viewport_rect.x+canvas_origin[0]+logical[0]*canvas_scale),
                            round(session.viewport_rect.y+canvas_origin[1]+logical[1]*canvas_scale))
                session.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                    button=1, pos=position), pygame.event.Event(pygame.MOUSEBUTTONUP,
                    button=1, pos=position)])
                self.assertEqual(study.state, 'bulwark')
                self.assertIsNone(study.model.current_action)
                session.handle_events([pygame.event.Event(pygame.KEYDOWN,
                    key=pygame.K_SPACE, repeat=False)])
                self.assertFalse(study.playing)
                elapsed = session.playback.elapsed
                session.update(50.)
                self.assertEqual(session.playback.elapsed, elapsed)
                self.assertIsNotNone(parent.gallery_session)
                session.handle_events([pygame.event.Event(pygame.KEYDOWN,
                    key=pygame.K_ESCAPE, repeat=False)])
                self.assertIsNone(parent.gallery_session)
                self.assertEqual(path.read_bytes(), before)
                self.assertFalse(settings.exists())
            finally:
                if parent.gallery_session is not None:parent.gallery_session.close()
                parent.music.stop();pygame.quit();gc.collect()


if __name__ == '__main__':unittest.main()
