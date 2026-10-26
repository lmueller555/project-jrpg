"""A weak spell leaves the gate unchanged, then tools finish the actual repair."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import pygame
from PIL import Image
import main
from quests import OPENING_QUEST
from venn_visit import PIN_APPROACH, VennVisit

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'assets/story/venn/magicks'


class VennMagickTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'journey.json'
        self.g=self.new_game()
        self.g.accept_quest(OPENING_QUEST)
        self.g.quests.complete_objective(OPENING_QUEST,'halden')
        self.g._sync_inventory();self.g.halden_visit.restore()
        self.g.deliver_quest_item(OPENING_QUEST,'venn','venn')
        self.v=self.g.venn_visit;self.v.inspected={'pin','channel'}
        self.g.world=self.g.town;self.g.player.position.update(PIN_APPROACH)

    def new_game(self,title=False):
        game=main.Game(fullscreen=False,start_on_title=title,save_path=self.path,
                       settings_path=Path(self.temp.name)/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        return game

    def tearDown(self):pygame.quit()
    def tick(self,seconds=.02):self.g.update(seconds,(0,0),False)
    def start(self):self.assertTrue(self.v._select_method('magicks'))

    def phase(self,target):
        for _ in range(600):
            if self.v.phase==target:return
            self.tick()
        self.fail('Missing phase '+target)

    def failed_attempt(self):
        for _ in range(600):
            if self.v.magicks_failed:return
            self.assertFalse(self.v.repaired)
            self.assertFalse(self.v.flowing)
            self.assertFalse(self.v.debris_cleared)
            self.assertEqual(self.v._gate_frame(0)[0],'idle_jammed')
            self.assertEqual(self.v.surface_props[3]['position'],[1446,680])
            self.assertFalse(any(self.v.surface_prop_visible(p) for p in self.v.water_props))
            self.tick()
        self.fail('Spell did not fail')

    def read_dialogue(self):
        for _ in range(60):
            if not self.g.social.active:return
            self.assertFalse(self.g.social.choosing)
            self.g.social.advance()
        self.fail('Unfinished fallback dialogue')

    def finish_tools(self):
        phases=set()
        for _ in range(900):
            if self.v.action is None:break
            phases.add(self.v.phase);self.tick()
            self.assertTrue(self.g.town.can_stand(self.g.player.position))
        self.assertIsNone(self.v.action);self.assertTrue(self.v.repaired)
        self.assertFalse(hasattr(self.g.player,'story_sprite'))
        self.assertEqual(self.g.quests.objective_status(OPENING_QUEST,'venn'),'active')
        return phases

    def test_failed_cast_does_not_move_water_gate_or_debris_then_tools_repair(self):
        self.start();self.failed_attempt()
        self.assertEqual(self.v.method,'magicks')
        self.assertFalse(self.v.repaired);self.assertFalse(self.v.debris_cleared)
        self.assertFalse(self.v.flowing);self.assertIsNone(self.v.action)
        self.assertEqual(self.v._gate_frame(0)[0],'idle_jammed')
        self.assertEqual(self.g.social.script_identifier,'venn_magicks_failed')
        self.assertTrue(self.g.social.active)
        self.assertTrue(json.loads(self.path.read_text())['venn_visit']['magicks_failed'])
        self.read_dialogue()
        self.assertEqual(self.v.method,'magicks')
        self.assertEqual(self.v.action_method,'tools')
        phases=self.finish_tools()
        self.assertTrue({'work_pin','clear_channel','open'}<=phases)
        self.assertTrue(self.v.debris_cleared);self.assertTrue(self.v.flowing)

    def test_source_head_and_lower_body_remain_identical_to_idle(self):
        meta=self.v.magick_art.data
        sheet=Image.open(ART/'poses.png').convert('RGBA')
        idle=Image.open(ROOT/'assets/characters/caelan/idle_right.png').convert('RGBA')
        first=last=None
        for phase in meta['sequence']:
            for record in meta['animations'][phase]['frames']:
                x,y,w,h=record['rect'];pose=sheet.crop((x,y,x+w,y+h))
                self.assertEqual((w,h),(40,48))
                self.assertEqual(pose.crop((8,8,32,22)).tobytes(),idle.crop((0,0,24,14)).tobytes())
                self.assertEqual(pose.crop((8,33,32,44)).tobytes(),idle.crop((0,25,24,36)).tobytes())
                self.assertEqual(set(pose.getchannel('A').tobytes())-{0,255},set())
                if first is None:first=pose
                last=pose
        expected=Image.new('RGBA',(40,48));expected.alpha_composite(idle,(8,8))
        self.assertEqual(first.tobytes(),expected.tobytes())
        self.assertEqual(last.tobytes(),expected.tobytes())
        # Both paths now use upright practical work poses; their body must not
        # reintroduce the displaced hips or patched legs removed from casting.
        for mode in ('tools','hands'):
            for index in range(4):
                with self.subTest(work_pose=f'{mode}_{index}'):
                    pose=Image.open(ROOT/f'assets/story/venn/caelan/{mode}_{index}.png').convert('RGBA')
                    self.assertEqual(pose.crop((8,8,32,22)).tobytes(),idle.crop((0,0,24,14)).tobytes())
                    self.assertEqual(pose.crop((8,33,32,44)).tobytes(),idle.crop((0,25,24,36)).tobytes())
        self.assertTrue(all(not (ROOT/f'assets/story/venn/caelan/magicks_{i}.png').exists() for i in range(4)))

    def test_magic_is_a_small_blue_effect_that_disappears_before_idle(self):
        meta=self.v.magick_art.data
        energy=Image.open(ART/'energy.png').convert('RGBA')
        counts=[]
        for phase in meta['sequence']:
            for record in meta['animations'][phase]['frames']:
                x,y,w,h=record['rect'];effect=energy.crop((x,y,x+w,y+h))
                visible=[p for p in effect.getdata() if p[3]]
                counts.append(len(visible))
                self.assertLessEqual(len(visible),8)
                for r,g,b,a in visible:self.assertGreater(b,r)
        self.assertEqual(counts[0],0);self.assertEqual(counts[-1],0)
        self.assertGreater(max(counts),0)
        self.assertLess(len(set(counts)),len(counts))

    def test_pause_and_inventory_freeze_cast_and_fizzle(self):
        self.start()
        self.phase(self.v.magick_art.sequence[1]);self.tick(.3)
        for panel in [self.g.pause,self.g.inventory_ui]:
            state=(self.v.phase,self.v.phase_time,self.g.player.story_sprite)
            panel.is_open=True;self.tick(.5);panel.is_open=False
            self.assertEqual((self.v.phase,self.v.phase_time,self.g.player.story_sprite),state)
            self.assertFalse(self.v.magicks_failed)
        self.failed_attempt()

    def test_interrupted_attempt_reloads_safely_and_can_be_attempted(self):
        self.start();self.phase(self.v.magick_art.sequence[1]);self.tick(.2)
        self.g.save_progress()
        other=self.new_game(True);self.assertTrue(other.begin_journey(True))
        v=other.venn_visit
        self.assertEqual(v.method,'magicks');self.assertFalse(v.magicks_failed)
        self.assertFalse(v.repaired);self.assertIsNone(v.action)
        self.assertFalse(hasattr(other.player,'story_sprite'))
        self.assertTrue(other.town.can_stand(other.player.position))
        self.assertEqual(v._gate_frame(0)[0],'idle_jammed')
        self.assertTrue(v._select_method('magicks'))

    def test_failure_checkpoint_survives_reload_and_resumes_only_tools(self):
        self.start();self.failed_attempt()
        other=self.new_game(True);self.assertTrue(other.begin_journey(True))
        self.g=other;self.v=other.venn_visit
        self.assertTrue(self.v.magicks_failed);self.assertFalse(self.v.repaired)
        self.assertEqual(self.v.method,'magicks');self.assertIsNone(self.v.action)
        self.assertFalse(self.v._select_method('magicks'))
        self.g.opening_fade=0
        self.assertTrue(self.v.interact());self.read_dialogue()
        self.assertEqual(self.v.action_method,'tools')
        self.finish_tools()

    def test_walking_away_from_failure_does_not_replay_spell_or_complete_quest(self):
        self.start();self.failed_attempt()
        self.g.player.position.update(1380,670);self.tick(0)
        self.assertFalse(self.g.social.active);self.assertTrue(self.v.magicks_failed)
        self.assertIsNone(self.v.action);self.assertFalse(self.v.repaired)
        self.g.player.position.update(PIN_APPROACH)
        self.assertTrue(self.v.interact());self.read_dialogue()
        self.assertEqual(self.v.action_method,'tools')
        self.finish_tools()

    def test_completed_legacy_magick_save_stays_repaired(self):
        self.g.save_progress();data=json.loads(self.path.read_text())
        data['venn_visit']={'version':1,'inspected':['pin','channel'],'method':'magicks','repaired':True}
        self.path.write_text(json.dumps(data))
        other=self.new_game(True);self.assertTrue(other.begin_journey(True))
        self.assertTrue(other.venn_visit.repaired)
        self.assertFalse(other.venn_visit.magicks_failed)
        self.assertEqual(other.venn_visit._gate_frame(0)[0],'idle_open')

    def test_invalid_failure_snapshots_are_rejected(self):
        valid={'version':2,'inspected':['pin','channel'],'method':'magicks','repaired':False,'magicks_failed':True}
        self.assertTrue(VennVisit.valid_snapshot(valid))
        for change in [{'method':'tools'},{'magicks_failed':1},{'inspected':['pin']},{'version':True}]:
            self.assertFalse(VennVisit.valid_snapshot(dict(valid,**change)))

    def test_original_ground_collision_and_supplies_unchanged_by_spell(self):
        def hashes():return [hashlib.sha256(pygame.image.tobytes(s,'RGB')).hexdigest() for s in self.g.town.ground]
        before=hashes();blocked=self.g.town.blocked.count();inventory=self.g.inventory.to_dict()
        self.start();self.failed_attempt()
        self.assertEqual(hashes(),before);self.assertEqual(self.g.town.blocked.count(),blocked)
        self.assertEqual(self.g.inventory.to_dict(),inventory)


if __name__=='__main__':unittest.main()
