"""Held water, two-handed contact, release timing, occlusion and interruption."""
import os
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
import hashlib,json
from pathlib import Path
import tempfile
import unittest
import pygame
from PIL import Image
import main
from quests import OPENING_QUEST
from venn_visit import PIN_APPROACH

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'assets/story/venn/magicks'
class VennMagickTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'journey.json'
        self.g=main.Game(fullscreen=False,start_on_title=False,save_path=self.path,
                         settings_path=Path(self.temp.name)/'settings.json')
        self.g.audio.set_music(0);self.g.audio.set_effects(0)
        self.g.accept_quest(OPENING_QUEST);self.g.quests.complete_objective(OPENING_QUEST,'halden')
        self.g._sync_inventory();self.g.halden_visit.restore()
        self.g.deliver_quest_item(OPENING_QUEST,'venn','venn')
        self.v=self.g.venn_visit;self.v.inspected={'pin','channel'}
        self.g.world=self.g.town;self.g.player.position.update(PIN_APPROACH)
    def tearDown(self):pygame.quit()
    def tick(self,seconds=.02):self.g.update(seconds,(0,0),False)
    def phase(self,target):
        for _ in range(500):
            if self.v.phase==target:return
            self.tick()
        self.fail('Missing phase '+target)
    def start(self):self.assertTrue(self.v._select_method('magicks'))
    def finish(self):
        for _ in range(500):
            if self.v.action is None:return
            self.tick();self.assertTrue(self.g.town.can_stand(self.g.player.position))
        self.fail('Unfinished repair')
    def test_water_stays_held_until_gate_opens_then_debris_flushes(self):
        self.start();self.phase('work_pin');self.tick(.8)
        self.assertFalse(self.v.repaired);self.assertFalse(self.v.flowing)
        self.assertEqual(self.v.surface_props[3]['position'],[1446,680])
        self.assertFalse(any(self.v.surface_prop_visible(p) for p in self.v.water_props))
        self.assertEqual(self.v.magick_art.amount(self.v.phase,self.v.phase_time),1)
        self.phase('open');self.tick(.5)
        self.assertEqual(self.v._gate_frame(0)[0],'magick_opening')
        self.assertEqual(self.v.magick_art.amount(self.v.phase,self.v.phase_time),1)
        self.assertFalse(self.v.debris_cleared)
        self.phase('release_water');self.tick(.5)
        self.assertTrue(self.v.flowing);self.assertFalse(self.v.repaired)
        self.assertGreater(self.v.surface_props[3]['position'][1],680)
        self.assertTrue(any(self.v.surface_prop_visible(p) for p in self.v.water_props))
        self.finish();self.assertTrue(self.v.repaired);self.assertTrue(self.v.debris_cleared)
        self.assertFalse(hasattr(self.g.player,'story_sprite'))
        self.assertEqual(self.g.quests.objective_status(OPENING_QUEST,'venn'),'active')
    def test_casting_hand_holds_while_working_hand_contacts_pin(self):
        data=self.v.magick_art.data
        for name in ['hold_water','work_pin','open']:
            for f in data['animations'][name]['frames']:self.assertEqual(f['casting_hand'],[29,20])
        working=data['animations']['work_pin']['frames'][2]['working_hand']
        origin=pygame.Vector2(PIN_APPROACH)-pygame.Vector2(data['anchor'])
        self.assertEqual(tuple(origin+working),(1442,659))
        opening=Image.open(ART/'opening_gate.png').convert('RGBA')
        for i,f in enumerate(data['animations']['open']['frames']):
            x,y=origin+f['working_hand']
            self.assertEqual(x,1442)
            pixel=opening.getpixel((i*24+2,round(y)-636))
            self.assertIn(pixel[:3],[(115,126,122),(164,170,160)])
    def test_water_overlay_preserves_structure_and_exposes_dry_channel(self):
        gate=self.v.backgrounds[0].copy();gate.blit(self.v.gates['idle_jammed'][0],(0,0));before=gate.copy()
        water=self.v.magick_art.overlay_gate(gate,1,0)
        self.assertEqual(water.get_size(),(8,56))
        self.assertEqual(self.v.surface_props[4]['position'],[1448,620])
        changed=0
        for y in range(36):
            for x in range(24):
                if gate.get_at((x,y))!=before.get_at((x,y)):
                    changed+=1;self.assertIn(x,range(8,16))
                    self.assertIn(before.get_at((x,y))[:3],self.v.magick_art.colors)
        self.assertGreater(changed,10)
        self.assertNotIn(water.get_at((3,45))[:3],self.v.magick_art.colors)
    def test_source_layers_reconstruct_hard_alpha_native_poses(self):
        meta=self.v.magick_art.data;sheet=Image.open(ART/'poses.png').convert('RGBA')
        for name in ['casting_arm','body','working_arm','head']:
            self.assertTrue((ART/(name+'.png')).exists())
        layers=[Image.open(ART/(name+'.png')).convert('RGBA') for name in ['casting_arm','body','working_arm','head']]
        reconstructed=Image.new('RGBA',sheet.size)
        for layer in layers:reconstructed.alpha_composite(layer)
        self.assertEqual(reconstructed.tobytes(),sheet.tobytes())
        self.assertEqual(set(sheet.getchannel('A').tobytes()),{0,255})
        for phase,record in meta['animations'].items():
            for f in record['frames']:
                x,y,w,h=f['rect'];im=sheet.crop((x,y,x+w,y+h))
                self.assertEqual((w,h),(40,48));self.assertLess(im.getbbox()[2],40)
        self.assertTrue(all(not (ROOT/f'assets/story/venn/caelan/magicks_{i}.png').exists() for i in range(4)))
    def test_original_ground_and_collision_are_unchanged(self):
        def hashes():return [hashlib.sha256(pygame.image.tobytes(s,'RGB')).hexdigest() for s in self.g.town.ground]
        before=hashes();blocked=self.g.town.blocked.count()
        self.start();self.finish()
        self.assertEqual(hashes(),before);self.assertEqual(self.g.town.blocked.count(),blocked)
    def test_pause_and_inventory_freeze_held_water_and_gestures(self):
        self.start();self.phase('work_pin');self.tick(.6)
        for panel in [self.g.pause,self.g.inventory_ui]:
            state=(self.v.phase,self.v.phase_time,self.g.player.story_sprite,self.v.surface_props[4]['surface'])
            panel.is_open=True;self.tick(.5);panel.is_open=False
            self.assertEqual((self.v.phase,self.v.phase_time,self.g.player.story_sprite,self.v.surface_props[4]['surface']),state)
        self.finish()
    def test_interrupted_cast_loads_safely_without_replaying_old_animation(self):
        self.start();self.phase('work_pin');self.tick(.6);self.g.save_progress()
        other=main.Game(fullscreen=False,start_on_title=True,save_path=self.path)
        self.assertTrue(other.begin_journey(True));v=other.venn_visit
        self.assertEqual(v.method,'magicks');self.assertFalse(v.repaired)
        self.assertIsNone(v.action);self.assertFalse(hasattr(other.player,'story_sprite'))
        self.assertFalse(v.surface_prop_visible(v.surface_props[4]))
        self.assertTrue(other.town.can_stand(other.player.position))
        self.assertEqual(v._gate_frame(0)[0],'idle_jammed')

if __name__=='__main__':unittest.main()
