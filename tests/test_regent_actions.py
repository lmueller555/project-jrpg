"""MQ03 visual beats keep bodies registered and never commit quest progress."""
import os
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from regent_actions import RegentActions
import test_regent_quest as quest_fixture


class RegentActionTests(unittest.TestCase):
    def setUp(self):
        fixture = quest_fixture.RegentQuestTests()
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.g = fixture.g;self.owner = fixture.c
        self.original_social = self.g.social
        self.view = RegentActions(self.owner)

    def tearDown(self):pygame.quit()

    def cue(self, kind, cue):
        lines = self.owner.lines[kind]
        index = next(i for i, line in enumerate(lines) if line.get('cue') == cue)
        self.owner.dialogue = kind
        self.owner._dialogue_lines = lines
        self.g.social = SimpleNamespace(active=True, script_identifier='regent_'+kind,
                                        page={'source_line': index})
        return index

    def test_legacy_arrival_uses_the_actual_selected_source(self):
        self.owner.dialogue = 'arrival'
        lines = self.owner.lines['arrival_unarmed']
        self.owner._dialogue_lines = lines
        self.g.social = SimpleNamespace(active=True, script_identifier='regent_arrival',
                                        page={'source_line': len(lines)-1})
        self.view.update(.1)
        self.assertIsNone(self.view.active_cue)
        self.assertFalse(hasattr(self.g.player, 'story_sprite'))

    def test_standing_tomas_keeps_his_standing_body_and_registered_feet(self):
        self.cue('welcome', 'tomas_eat')
        actor = self.owner.tomas;actor.position.update(108, 200)
        position = actor.position.copy()
        self.view.update(.1)
        self.assertIs(actor.story_sprite, actor.idles[actor.facing])
        self.assertFalse(hasattr(actor, 'story_position'))
        self.assertEqual(actor.position, position)

    def seat_tomas(self, ready=True):
        self.owner.points = {**self.owner.points, 'meal_seats': {
            'tomas': {'position': [138, 200], 'approach': [108, 200],
                      'anchor': [12, 30], 'sort_y': 206, 'facing': 'right',
                      'image': 'assets/story/sanctuary_opening/poses/tomas_seated.png',
                      'flip_x': True}}}
        self.owner.tomas.position.update(108, 200)
        self.owner.stage = 'welcome';self.owner._meal_ready = ready

    def test_meal_seating_waits_for_arrival_and_uses_the_actual_chair(self):
        self.seat_tomas(False)
        self.view.update(.1)
        self.assertFalse(hasattr(self.owner.tomas, 'story_position'))
        self.owner._meal_ready = True;self.view.update(.5)
        self.assertEqual(self.owner.tomas.story_position, (138, 200))
        self.assertEqual(self.owner.tomas.story_draw_anchor, (12, 30))
        self.assertEqual(self.owner.tomas.story_sort_y, 206)
        self.assertEqual(tuple(self.owner.tomas.position), (108, 200))

    def test_tomas_eats_with_seated_drawings_only_at_his_registered_seat(self):
        self.seat_tomas();self.cue('welcome', 'tomas_eat')
        self.view.update(.5)
        self.assertEqual(self.view.active_cue, 'tomas_eat')
        self.assertEqual(self.owner.tomas.story_sprite.get_size(), (24, 36))
        self.assertEqual(self.owner.tomas.story_position, (138, 200))
        self.assertEqual(tuple(self.owner.tomas.position), (108, 200))

    def test_cancelled_meal_stays_seated_until_discussion_stands_them_up(self):
        self.seat_tomas();self.cue('welcome', 'meal_settle');self.view.update(.5)
        self.g.social.active = False;self.view.update(.1)
        self.assertEqual(self.owner.tomas.story_position, (138, 200))
        self.owner.stage = 'discussion';self.view.update(.1)
        self.assertFalse(hasattr(self.owner.tomas, 'story_position'))

    def test_reflow_and_time_never_replay_or_commit_the_same_line(self):
        self.cue('arrival', 'caelan_scabbard')
        before = self.g.quests.to_dict();position = self.g.player.position.copy()
        self.view.update(.1)
        self.assertEqual(self.view.active_cue, 'caelan_scabbard')
        self.assertEqual(self.g.player.story_draw_anchor, (20, 54))
        self.view.update(2)
        self.assertIsNone(self.view.active_cue)
        self.view.update(.1)
        self.assertIsNone(self.view.active_cue)
        self.assertEqual(self.g.player.position, position)
        self.assertEqual(self.g.quests.to_dict(), before)

    def test_pause_and_focus_freeze_transient_animation_without_catchup(self):
        self.cue('welcome', 'pass_bread');self.view.update(.1)
        self.g._music_focused = False;self.view.update(30)
        self.assertAlmostEqual(self.view.clock, .1)
        self.g._music_focused = True;self.g.map_open = True;self.view.update(30)
        self.assertAlmostEqual(self.view.clock, .1)
        self.g.map_open = False;self.view.update(.1)
        self.assertAlmostEqual(self.view.clock, .2)

    def test_cancellation_releases_own_pose_without_replacing_another_owner(self):
        self.cue('welcome', 'pass_bread');self.view.update(.1)
        sentinel = pygame.Surface((1, 1));self.g.player.story_sprite = sentinel
        self.g.social.active = False;self.view.update(.1)
        self.assertIs(self.g.player.story_sprite, sentinel)
        self.assertIsNone(self.view.active_cue)

    def test_handed_off_family_is_never_reposed_or_redirected(self):
        self.cue('welcome', 'tomas_eat')
        self.owner.handoff_tomas()
        sentinel = pygame.Surface((1, 1));self.owner.tomas.story_sprite = sentinel
        facing = self.owner.tomas.facing
        self.view.update(.1)
        self.assertIs(self.owner.tomas.story_sprite, sentinel)
        self.assertEqual(self.owner.tomas.facing, facing)

    def test_map_props_and_compact_sheathed_blade_render_without_changing_art(self):
        self.g.social = self.original_social
        self.assertTrue(self.g.acquire_weapon('caelan', 'caelan_gearblade'))
        self.cue('discussion', 'open_survey');self.view.update(.3)
        self.g.world = self.owner.dining
        canvas = pygame.Surface((480, 320), pygame.SRCALPHA)
        self.view.draw_world(canvas, (0, 0))
        self.assertEqual(self.view._weapon().get_size(), (9, 24))
        self.assertTrue(self.view._map_open)
        self.assertGreater(pygame.mask.from_surface(canvas).count(), 0)
        self.view.reset()
        self.assertFalse(self.view._map_open)

    def test_survivor_alarm_uses_registered_body_without_moving_physical_feet(self):
        self.g.world=self.owner.dining
        actor=self.owner.survivor
        self.owner._place(actor,self.owner.dining,self.owner.points['survivor_rest'])
        before=actor.position.copy()
        self.cue('attack_report','survivor_alarm');self.view.update(.1)
        self.assertEqual(actor.story_sprite.get_size(),(24,36))
        self.assertEqual(actor.story_draw_anchor,actor.draw_anchor)
        self.assertEqual(actor.position,before)
        self.view.reset()
        self.assertFalse(hasattr(actor,'story_sprite'))

    def test_lucan_disbelief_turns_toward_aldric_and_never_commits_progress(self):
        self.g.world=self.owner.dining
        self.owner._place(self.owner.lucan,self.owner.dining,(336,252))
        self.owner._place(self.owner.aldric,self.owner.dining,(228,200))
        before=self.owner.lucan.position.copy()
        progress=self.g.quests.to_dict()
        self.cue('attack_report','lucan_disbelief');self.view.update(.1)
        self.assertIs(self.owner.lucan.story_sprite,self.owner.lucan.idles[self.owner.lucan.facing])
        self.assertEqual(self.owner.lucan.facing,'left')
        self.assertEqual(self.owner.lucan.position,before)
        self.assertEqual(self.g.quests.to_dict(),progress)
        self.view.reset()
        self.assertFalse(hasattr(self.owner.lucan,'story_sprite'))

    def test_care_poses_register_the_existing_bench_and_release_cleanly(self):
        self.g.world=self.owner.dining;self.owner.stage='departure'
        worker=self.owner.survivor
        self.owner._place(worker,self.owner.dining,self.owner.points['survivor_rest'])
        self.owner._place(self.owner.serene,self.owner.dining,self.owner.points['serene_aid'])
        feet=worker.position.copy()
        prior_serene=getattr(self.owner.serene,'story_sprite',None)
        self.cue('departure','survivor_aid');self.view.update(.1)
        self.assertEqual(worker.position,feet)
        self.assertEqual(worker.story_position,tuple(self.owner.points['survivor_seat']['position']))
        self.assertEqual(worker.story_sort_y,self.owner.points['survivor_seat']['sort_y'])
        self.assertEqual(self.owner.serene.story_sprite.get_size(),(24,36))
        self.view.reset()
        self.assertFalse(hasattr(worker,'story_position'))
        self.assertIs(getattr(self.owner.serene,'story_sprite',None),prior_serene)

    def test_alternative_survivor_landing_never_forces_a_bench_drawing(self):
        self.g.world=self.owner.dining;self.owner.stage='departure'
        worker=self.owner.survivor
        alternative=(84,276)
        self.owner._place(worker,self.owner.dining,alternative)
        self.cue('departure','survivor_aid');self.view.update(.1)
        self.assertFalse(hasattr(worker,'story_position'))
        self.assertEqual(tuple(worker.position),alternative)
        # A later safe landing also releases an already-held bench drawing.
        worker.position.update(self.owner.points['survivor_rest']);self.view.update(.1)
        self.assertEqual(worker.story_position,tuple(self.owner.points['survivor_seat']['position']))
        worker.position.update(alternative);self.view.update(.1)
        self.assertFalse(hasattr(worker,'story_position'))
        self.assertEqual(tuple(worker.position),alternative)


if __name__ == '__main__':unittest.main()
