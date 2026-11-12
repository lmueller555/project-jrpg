"""Elemental channeling stays synchronized in the actual battle presentation.

Ownership/cue assertions complement internal visual review of the composed
animation. Passing these checks alone does not establish animation quality.
"""
import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from battle_scene import CombatSprites
import test_vespermaw_live_scene as live_scene_tests
from test_random_enemy_groups import clear_gauges


class VespermawChannelSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init(); pygame.font.init()
        pygame.display.set_mode((960,640))
        cls.sprites = CombatSprites()

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def scene(self):
        scene, canvas, game = live_scene_tests.VespermawLiveSceneTests.scene(self)
        for actor in scene.model.party:
            actor.attributes['hp'] = actor.hp = 9999
        return scene, canvas, game

    def channel(self, scene):
        model = scene.model
        for _ in range(2):
            clear_gauges(model); model.enemy.atb = 1
            scene.update(0)
            self.assertNotEqual(model.current_action.action, 'vespermaw_attune')
            scene.update(model.current_action.duration)
        self.assertEqual(model.vespermaw_turns, 2)
        clear_gauges(model); model.enemy.atb = 1
        scene.update(0)
        self.assertEqual(model.current_action.action, 'vespermaw_attune')
        return model.current_action

    def resources(self, scene):
        return [(actor.identifier,actor.hp,actor.mp,actor.atb)
                for actor in (*scene.model.party,*scene.model.enemies)]

    def test_form_crystal_and_fur_share_the_channel_cue_before_the_scheduled_turn(self):
        scene, canvas, game = self.scene()
        action = self.channel(scene)
        self.assertEqual(scene.model.vespermaw_element, 'fire')
        before = self.resources(scene)
        scene.update(action.impact_at-.02)
        state = scene._vespermaw_channel_state()
        self.assertEqual((state['from'],state['to']), ('fire','ice'))
        self.assertEqual(scene.model.vespermaw_element, 'fire')
        self.assertEqual(self.resources(scene), before)
        scene.draw(canvas,game.ui_surface)
        scene.update(.02)
        self.assertEqual(scene.model.vespermaw_element, 'ice')
        self.assertEqual(scene.model.vespermaw_turns, 2)
        scene.draw(canvas,game.ui_surface)
        scene.update(action.duration-action.elapsed)
        self.assertNotEqual(scene.model.current_action.action, 'vespermaw_attune')
        self.assertEqual(scene.model.current_action.actor,'enemy')
        self.assertEqual(scene.model.vespermaw_turns,2)
        scene.draw(canvas,game.ui_surface)

    def test_pause_and_focus_freeze_the_transform_without_advancing_other_combatants(self):
        scene, canvas, game = self.scene()
        action = self.channel(scene)
        scene.update(.8)
        before = (action.elapsed, scene._elapsed, self.resources(scene),
                  scene._vespermaw_channel_state())
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,repeat=False))
        self.assertTrue(scene.paused)
        scene.update(4)
        self.assertEqual((action.elapsed,scene._elapsed,self.resources(scene),
                          scene._vespermaw_channel_state()),before)
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,repeat=False))
        scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertFalse(scene.focused)
        scene.update(4)
        self.assertEqual((action.elapsed,scene._elapsed,self.resources(scene),
                          scene._vespermaw_channel_state()),before)
        scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        # Focus recovery keeps combat paused until an explicit resume.
        self.assertTrue(scene.paused)
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,repeat=False))
        scene.update(.1)
        self.assertGreater(action.elapsed,before[0])
        scene.draw(canvas,game.ui_surface)

    def test_crystal_stream_origins_are_distinct_and_remain_above_the_combat_hud(self):
        for size,text_scale in (((960,640),1),((480,320),1.5)):
            scene, canvas, game = live_scene_tests.VespermawLiveSceneTests.scene(self,size,text_scale)
            origins = [scene._cave_field.crystal_origin(element)
                       for element in ('fire','ice','water')]
            self.assertEqual(len(set(tuple(point) for point in origins)),3)
            self.assertEqual(sorted(point[0] for point in origins),[point[0] for point in origins])
            self.assertTrue(all(0 < point[1] < scene.panel_rect.top-20 for point in origins))
            self.channel(scene)
            scene.update(1.5)
            scene.draw(canvas,game.ui_surface)
            text = (scene.announcements.current or {}).get('text','').lower()
            for hint in ('weakness','counter','aqua edge','flame edge','ice edge'):
                self.assertNotIn(hint,text)


    def test_channel_sound_pauses_and_resumes_the_same_voice_then_stops_on_result(self):
        scene, _, _ = self.scene()
        action = self.channel(scene)
        scene.update(.4)
        audio = scene.channel_audio
        voice = Mock(); sound = object()
        voice.get_sound.return_value = sound
        audio.action = action; audio.sound = sound; audio.voice = voice; audio.played = True
        with patch.object(audio,'_sound',side_effect=AssertionError('Cue restarted')):
            scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,repeat=False))
            voice.pause.assert_called()
            voice.stop.assert_not_called()
            scene.update(3)
            scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,repeat=False))
            scene.update(.1)
            self.assertIs(audio.voice,voice)
            voice.unpause.assert_called()
            voice.stop.assert_not_called()
            scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
            voice.pause.assert_called()
            scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
            scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,repeat=False))
            scene.update(.1)
            self.assertIs(audio.voice,voice)
            scene.model._result('defeat')
            scene.update(0)
            voice.stop.assert_called_once()
            self.assertIsNone(audio.voice)

    def test_inactive_crystals_remain_in_the_background_and_only_current_form_pulses(self):
        from vespermaw_crystals import ElementalCrystals
        scene, canvas, game = self.scene()
        field = scene._cave_field
        self.assertEqual(len(field.data['elemental_crystals']),3)
        baseline = field.frame(0,True)
        for element in ('fire','ice','water'):
            x,y = field.crystal_origin(element)
            # The dim lens remains visible even with no active-state overlay.
            self.assertGreater(len(set(pygame.image.tobytes(
                baseline.subsurface((x-12,y-12,24,24)),'RGB'))),12)
            state = {'element':element}
            first = ElementalCrystals.strengths(0,state)
            later = ElementalCrystals.strengths(530,state)
            self.assertGreater(first[element],0)
            self.assertNotEqual(first[element],later[element])
            self.assertTrue(all(value==0 for key,value in first.items() if key!=element))
            self.assertEqual(ElementalCrystals.strengths(0,state,True),
                             ElementalCrystals.strengths(530,state,True))



if __name__=='__main__':unittest.main()
