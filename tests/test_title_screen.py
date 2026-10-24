"""Title lifecycle, actual menu input, and responsive mouse hit testing."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import unittest
from unittest.mock import patch
import pygame
import main


class TitleTests(unittest.TestCase):
    def setUp(self):
        self.game=main.Game(window_size=(1280,720),fullscreen=False)
        pygame.event.clear()

    def tearDown(self):pygame.quit()

    def position(self,row):
        width,height=self.game.window.get_size()
        scale=min(width/640,height/360)
        x,y=row.center
        return (round((width-640*scale)/2+x*scale),round((height-360*scale)/2+y*scale))

    def click(self,row):
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=self.position(row)))
        return self.game.handle_events()

    def test_launch_shows_title_and_world_does_not_run_behind_menu(self):
        actor=self.game.persistent_npcs[0]
        initial=(tuple(self.game.player.position),actor.state_ms,self.game.elapsed_ms)
        self.game.update(3,(1,0),True)
        self.assertTrue(self.game.on_title)
        self.assertEqual((tuple(self.game.player.position),actor.state_ms,self.game.elapsed_ms),initial)
        self.assertEqual([r.centerx for r in self.game.title.rows],[320]*4)

    def test_new_game_click_fades_then_enters_real_playable_world(self):
        self.assertTrue(self.click(self.game.title.rows[0]))
        self.assertTrue(self.game.on_title)
        self.game.update(.3)
        self.assertTrue(self.game.on_title)
        self.game.update(.4)
        self.assertFalse(self.game.on_title)
        self.game.draw()
        self.game.update(.6,(0,0),False)
        self.game.player.position.update(456,936)
        self.game.update(.1,(1,0),False)
        self.assertGreater(self.game.player.position.x,456)

    def test_continue_disabled_and_keyboard_skips_it(self):
        self.assertTrue(self.click(self.game.title.rows[1]))
        self.assertEqual(self.game.title.fade,0)
        self.assertTrue(self.game.on_title)
        self.game.title.selected=0
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_DOWN))
        self.game.handle_events()
        self.assertEqual(self.game.title.selected,2)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_UP))
        self.game.handle_events()
        self.assertEqual(self.game.title.selected,0)

    def test_settings_display_toggle_and_escape_back(self):
        self.click(self.game.title.rows[2])
        self.assertTrue(self.game.title.settings)
        with patch.object(self.game,'toggle_fullscreen') as toggle:
            self.click(self.game.title.settings_rows[0])
            toggle.assert_called_once_with()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
        self.game.handle_events()
        self.assertFalse(self.game.title.settings)
        self.assertEqual(self.game.title.selected,2)
        self.game.draw()

    def test_quit_click_and_keyboard_selection_exit_cleanly(self):
        self.assertFalse(self.click(self.game.title.rows[3]))
        self.game.title.selected=3
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
        self.assertFalse(self.game.handle_events())

    def test_music_setting_toggles_and_missing_audio_device_is_nonfatal(self):
        self.click(self.game.title.rows[2])
        self.click(self.game.title.settings_rows[1])
        self.assertFalse(self.game.title.music_enabled)
        with patch.object(self.game.title,'start_music') as start:
            self.click(self.game.title.settings_rows[1])
            self.assertTrue(self.game.title.music_enabled)
            start.assert_called_once_with()
        with patch('pygame.mixer.get_init',return_value=None),patch('pygame.mixer.init',side_effect=pygame.error('No audio device')):
            self.game.title.start_music()
        self.assertFalse(self.game.title.music_started)

    def test_hover_and_click_stay_aligned_on_wide_and_tall_displays(self):
        for size in ((1280,720),(1024,768),(1920,810),(800,800)):
            with self.subTest(size=size):
                self.game.window=pygame.display.set_mode(size,pygame.RESIZABLE)
                self.game.draw()
                point=self.position(self.game.title.rows[2])
                pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION,pos=point,rel=(0,0),buttons=(0,0,0)))
                self.game.handle_events()
                self.assertEqual(self.game.title.selected,2)
                self.assertEqual(self.game.title._row_at(self.game.title.to_canvas(point)),2)
                self.assertTrue(0<=point[0]<size[0] and 0<=point[1]<size[1])

    def test_animation_changes_scene_without_changing_menu_placement(self):
        self.game.draw()
        before=pygame.image.tobytes(self.game.title.scene,'RGB')
        self.game.update(1.5)
        self.game.draw()
        after=pygame.image.tobytes(self.game.title.scene,'RGB')
        self.assertNotEqual(before,after)
        self.assertEqual(self.game.title.rows[0].centerx,320)

    def test_display_receives_one_opaque_frame_with_visible_scenery(self):
        class DisplayProbe:
            def __init__(self,surface):self.surface=surface;self.calls=[]
            def get_size(self):return self.surface.get_size()
            def blit(self,source,position):
                self.calls.append((source,position))
                return self.surface.blit(source,position)

        display=self.game.window
        probe=DisplayProbe(display)
        self.game.window=probe
        try:
            self.game.draw()
            self.assertEqual(len(probe.calls),1)
            frame,position=probe.calls[0]
            self.assertEqual(position,(0,0))
            self.assertIs(frame,self.game.title.frame)
            self.assertIsNone(frame.get_alpha())
            self.assertFalse(frame.get_flags() & pygame.SRCALPHA)
            self.assertEqual(pygame.image.tobytes(display,'RGB'),pygame.image.tobytes(frame,'RGB'))
            # Empty UI regions must retain the painted scene, not black.
            for native in ((20,150),(500,180),(420,325)):
                self.assertEqual(self.game.title.ui.get_at(native).a,0)
                point=tuple(value*2 for value in native)
                self.assertEqual(display.get_at(point)[:3],self.game.title.scene.get_at(native)[:3])
                self.assertNotEqual(display.get_at(point)[:3],(0,0,0))
        finally:self.game.window=display

    def test_composite_rebuilds_after_resize_and_keeps_background_animation(self):
        self.game.draw()
        original=self.game.title.frame
        for size in ((1024,768),(1920,810),(800,800)):
            self.game.window=pygame.display.set_mode(size,pygame.RESIZABLE)
            self.game.draw()
            frame=self.game.title.frame
            self.assertEqual(frame.get_size(),size)
            self.assertIsNot(frame,original)
            self.assertIsNone(frame.get_alpha())
            self.assertEqual(self.game.window.get_at((0,0))[:3],frame.get_at((0,0))[:3])
            self.assertNotEqual(frame.get_at((0,0))[:3],(0,0,0))
            original=frame
        before=pygame.image.tobytes(original,'RGB')
        self.game.update(1.5)
        self.game.draw()
        self.assertIs(original,self.game.title.frame)
        self.assertNotEqual(before,pygame.image.tobytes(original,'RGB'))


if __name__=='__main__':unittest.main()
