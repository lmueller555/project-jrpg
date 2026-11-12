"""Dialogue actions and personal props remain coherent across travel and saves."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import pygame
import test_sanctuary_arrival_state as state_tests
from prop_presentation import personal_prop_visible

class ArrivalPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.driver=state_tests.SanctuaryArrivalStateTests();self.driver.setUp()
        self.addCleanup(self.driver.doCleanups)
        self.g=self.driver.g
    def test_personal_props_require_authored_stationary_use(self):
        self.assertFalse(personal_prop_visible(SimpleNamespace(moving=True),True))
        self.assertFalse(personal_prop_visible(SimpleNamespace(moving=False)))
        self.assertTrue(personal_prop_visible(SimpleNamespace(moving=False),True))
        with patch.object(self.g.regent_quest.scene_actions,'_weapon',side_effect=AssertionError('Floating travel weapon')):
            self.g.regent_quest.scene_actions.draw_world(pygame.Surface((480,320)),(0,0))
    def test_care_instruction_precedes_retrieval_and_kit_never_follows_walking(self):
        d=self.driver;o=self.g.sanctuary_arrival
        d.until(lambda:o.beat==4 and o.dialogue is not None)
        self.assertEqual(tuple(o.actors['mira'].position),(716,318))
        self.assertTrue(o._kit)
        d.press();self.assertGreater(o._action_remaining,0)
        for _ in range(20):
            d.tick(.1)
            if o.actors['mira'].moving:
                self.assertFalse(o._kit)
                self.assertNotIn([708,326],[r['position'] for _,r in o._care_props])
                break
        else:self.fail('Mira never departed after retrieving her kit')
        d.until(lambda:o.completed)
        expected=[r['position'] for _,r in o._care_props]
        self.assertEqual(len(expected),2)
        other=d.game();self.assertTrue(other.begin_journey(True))
        self.assertEqual([r['position'] for _,r in other.sanctuary_arrival._care_props],expected)
        self.assertFalse(other.sanctuary_arrival._kit)
    def test_treatment_contact_is_registered_to_the_existing_dressing(self):
        d=self.driver;o=self.g.sanctuary_arrival
        d.until(lambda:o.beat==1)
        mira=o.actors['mira'];worker=o.actors['worker_a']
        mira.pose='treat';mira.pose_ms=900;worker.pose='offer_arm';worker.pose_ms=900
        self.assertEqual(tuple(mira.position-pygame.Vector2(mira.draw_anchor)+pygame.Vector2(16,34)),
                         tuple(worker.position-pygame.Vector2(worker.draw_anchor)+pygame.Vector2(24,24)))
        self.assertGreater(mira.sprite(0).get_at((16,34)).a,0)
    def test_wounded_worker_has_contextual_post_scene_interaction(self):
        d=self.driver;o=self.g.sanctuary_arrival;d.until(lambda:o.completed)
        self.g.player.position.update(688,348);self.g.player.facing='back'
        self.g.transfer_cooldown=0
        self.assertTrue(self.g.sanctuary_reserve.interact())
        text=' '.join(line['text'] for line in self.g.social._source_lines)
        self.assertIn('dressing',text)
        self.assertNotIn('quiet',text)
    def test_dialogue_keeps_eight_checkpoints_and_twenty_eight_boxes(self):
        o=self.g.sanctuary_arrival
        self.assertEqual(len(o.manifest['beats']),8)
        lines=[line for b in o.manifest['beats'] for line in b['lines']]
        self.assertEqual(len(lines),28)
        self.assertEqual(len({line['id'] for line in lines}),28)

    def test_care_sound_pauses_on_focus_event_and_stops_on_reset(self):
        self.driver.tick()
        owner=self.g.sanctuary_arrival
        sound=object()
        class Voice:
            paused=False;stopped=False
            def get_sound(self):return sound
            def set_volume(self,value):pass
            def pause(self):self.paused=True
            def unpause(self):self.paused=False
            def stop(self):self.stopped=True
        voice=Voice();owner._care_sound=sound;owner._care_voice=voice
        self.g.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        self.assertTrue(voice.paused)
        self.g.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.assertFalse(voice.paused)
        owner.reset();self.assertTrue(voice.stopped)
