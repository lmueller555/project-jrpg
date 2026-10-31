"""Physical beats run through real Game updates and durable checkpoints."""
from unittest import TestCase,mock
import test_grain_farm as farm_tests
import test_bridge_crew as bridge_tests


class FarmAudioEvents(TestCase):
    setUp=farm_tests.GrainFarmTests.setUp
    tearDown=farm_tests.GrainFarmTests.tearDown
    make_game=farm_tests.GrainFarmTests.make_game
    tick=farm_tests.GrainFarmTests.tick
    until=farm_tests.GrainFarmTests.until
    ready=farm_tests.GrainFarmTests.ready
    def test_only_two_loaded_sacks_and_no_idle_impacts(self):
        with mock.patch.object(self.g.regional_audio,'emit') as emit:
            self.ready();self.tick(300)
            self.assertEqual(sum(c.args[0]=='farm_place' for c in emit.call_args_list),2)
            self.assertTrue(any(c.args[1]=='rustle' for c in emit.call_args_list))
    def test_completed_load_restore_does_not_reemit(self):
        self.ready();state=self.f.to_dict();self.f.restore(state)
        with mock.patch.object(self.g.regional_audio,'emit') as emit:
            self.tick(300)
            self.assertFalse(any(c.args[0]=='farm_place' for c in emit.call_args_list))


class BridgeAudioEvents(TestCase):
    setUp=bridge_tests.BridgeCrewTests.setUp
    tearDown=bridge_tests.BridgeCrewTests.tearDown
    make_game=bridge_tests.BridgeCrewTests.make_game
    tick=bridge_tests.BridgeCrewTests.tick
    until=bridge_tests.BridgeCrewTests.until
    ready=bridge_tests.BridgeCrewTests.ready
    dialogue=bridge_tests.BridgeCrewTests.dialogue
    scene=bridge_tests.BridgeCrewTests.scene
    def test_cup_contacts_once_and_completed_restore_silent(self):
        with mock.patch.object(self.g.regional_audio,'emit') as emit:
            self.scene()
            keys=[c.args[0] for c in emit.call_args_list]
            for key in ('bridge_cup_stone','bridge_cup_tray','bridge_cup_return'):self.assertEqual(keys.count(key),1)
            self.c.restore(self.c.to_dict());emit.reset_mock();self.tick(300)
            self.assertFalse(any('cup' in c.args[0] for c in emit.call_args_list))
    def test_kettle_work_is_not_tool_contact(self):
        self.ready();self.c._stage('tea_pickup')
        self.c.mason.clock=.7;self.c.tender.clock=.59
        with mock.patch.object(self.g.regional_audio,'emit') as emit:
            self.tick()
            self.assertFalse(any(c.args[0]=='bridge_tool' for c in emit.call_args_list))
    def test_new_contact_keeps_full_duration_on_long_frame(self):
        from bridge_crew import SOURCE,HELP
        self.c.restore({'sorted':3,'tea_beat':1,'request_read':True,'greeted':[]})
        self.c.timer=.79
        self.g.audio.set_effects(1)
        self.g.update(.1,(0,0),False)
        self.assertIn('bridge_cup_stone',self.g.regional_audio.voices)
        self.assertEqual(self.g.regional_audio.voices['bridge_cup_stone'][3],0)
    def test_continue_completed_tea_does_not_replay_contacts(self):
        from tools.capture_lantern_quest import seed_previous_quests
        seed_previous_quests(self.g);self.g.world=self.g.overworld_world
        self.g.player.position.update(-2340,644)
        self.scene();self.assertTrue(self.g.save_progress())
        other=self.make_game(True);self.assertTrue(other.begin_journey(True))
        self.g=other;self.c=other.world.bridge_crew
        other.opening_fade=other.transfer_cooldown=0
        with mock.patch.object(other.regional_audio,'emit') as emit:
            self.tick(300)
            self.assertFalse(any('cup' in c.args[0] for c in emit.call_args_list))
