"""Gift shots are acknowledged, paused and registered without granting early."""
import os,json,hashlib,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy');os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from mill_gift import MillGift,PHASES,ASSETS
from ui_style import UIStyle
ROOT=Path(__file__).resolve().parents[1]

def fixture():
 pygame.init();pygame.display.set_mode((480,320))
 profiles=json.loads((ROOT/'assets/dialogue/eldenmere.json').read_text())['speakers']
 manifest=json.loads((ROOT/'assets/portraits/eldenmere/portraits.json').read_text())['portraits']
 portraits={p['portrait']:pygame.image.load(str(ROOT/'assets/portraits/eldenmere'/manifest[p['portrait']]['file'])).convert_alpha() for p in profiles.values()}
 g=SimpleNamespace(audio=SimpleNamespace(reduced_motion=False,text_scale=1.,effects_volume=0.),
  _music_focused=True,ui_surface=pygame.Surface((960,640)),to_canvas=lambda p:p,
  social=SimpleNamespace(data={'speakers':profiles},portraits=portraits))
 g.ui=UIStyle(g)
 return g

class MillGiftTests(unittest.TestCase):
 def setUp(self):
  self.game=fixture();self.scene=MillGift(self.game)
  self.lines=json.loads((ROOT/'assets/story/mill/scene.json').read_text())['gift'];self.callback=Mock()
 def tearDown(self):pygame.quit()
 def start(self):self.assertTrue(self.scene.start(self.lines,self.callback));self.scene.update(.1)
 def read_phase(self):
  while self.scene.dialogue is not None:
   self.scene.begin_input_batch();self.assertTrue(self.scene.advance())
 def test_all_five_shots_gate_completion_on_animation_and_reading(self):
  self.start();seconds=.1
  for shot,minimum in zip(PHASES,(3,3,4,5,3)):
   self.assertEqual(self.scene.shot,shot)
   self.read_phase();self.assertTrue(self.scene.active);self.callback.assert_not_called()
   self.scene.update(minimum-self.scene.phase_time);seconds+=minimum
  self.assertFalse(self.scene.active);self.callback.assert_called_once_with()
  self.scene.update(100);self.scene.advance();self.callback.assert_called_once_with()
 def test_unread_dialogue_holds_and_reset_never_grants(self):
  self.start();self.scene.update(100)
  self.assertEqual(self.scene.shot,'reveal');self.assertEqual(self.scene.dialogue_index,0)
  self.scene.reset();self.callback.assert_not_called();self.assertFalse(self.scene.active)
 def test_pause_focus_and_held_input_do_not_move_or_skip(self):
  self.start();self.scene.begin_input_batch()
  event=pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE,repeat=False)
  self.scene.handle_event(event);index=(self.scene.dialogue_index,self.scene.page_index)
  self.scene.begin_input_batch();self.scene.handle_event(event)
  self.assertEqual(index,(self.scene.dialogue_index,self.scene.page_index))
  self.scene.handle_event(pygame.event.Event(pygame.KEYUP,key=pygame.K_SPACE))
  self.scene.begin_input_batch();self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE,repeat=False))
  clock=self.scene.elapsed;self.scene.update(5);self.assertEqual(self.scene.elapsed,clock)
  self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST));self.scene.paused=False
  self.scene.update(5);self.assertEqual(self.scene.elapsed,clock)
 def test_shared_portraits_literal_emotes_and_large_text_fit(self):
  self.start();canvas=pygame.Surface((480,320))
  for scale in (1.,1.5):
   self.game.audio.text_scale=scale
   for i,shot in enumerate(PHASES):
    self.scene.phase_index=i;self.scene.phase_time=2.;self.scene.dialogue_index=0;self.scene.page_index=0
    for index,line in enumerate(self.scene.sections[i]):
     self.scene.dialogue_index=index;self.scene.draw(canvas,self.game.ui_surface)
     layout=self.scene.caption_layout
     self.assertTrue(pygame.Rect(0,0,480,320).contains(layout.panel))
     rendered=' '.join(' '.join(p) for p in self.scene.caption_pages)
     self.assertEqual(rendered,' '.join(line['text'].split()))
     self.assertEqual(layout.portrait_key,self.game.social.data['speakers'][line['speaker']]['portrait'])
 def test_mechanical_click_obeys_volume_pause_and_ownership(self):
  self.start();self.game.audio.effects_volume=.5
  channel=Mock();sound=Mock();sound.play.return_value=channel;channel.get_sound.return_value=sound
  self.scene._click_sound=sound
  self.scene.phase_index=3;self.scene.phase_time=3.;self.scene.update(.2)
  sound.play.assert_called_once_with();channel.set_volume.assert_called_with(.07)
  self.scene.paused=True;self.scene._sync_audio();channel.pause.assert_called_once_with()
  self.scene.paused=False;self.scene._sync_audio();channel.unpause.assert_called()
  self.scene.update(1);sound.play.assert_called_once_with()
  # A borrowed mixer channel may already be playing another owner's sound.
  channel.get_sound.return_value=object();self.scene.reset();channel.stop.assert_not_called()
 def test_muted_click_is_not_replayed_after_unmuting(self):
  self.start();self.scene.phase_index=3;self.scene.phase_time=3.;self.scene._click_sound=Mock()
  self.scene.update(.2);self.scene._click_sound.play.assert_not_called()
  self.game.audio.effects_volume=1.;self.scene.update(1);self.scene._click_sound.play.assert_not_called()
 def test_authored_handoff_has_eight_distinct_registered_drawings(self):
  records=self.scene.manifest['frames'];self.assertEqual(len(records),8)
  self.assertEqual(len({r['sha256'] for r in records}),8)
  for r in records:
   path=ASSETS/r['file'];self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),r['sha256'])
   image=pygame.image.load(str(path));self.assertEqual(image.get_size(),(256,144))
   self.assertTrue(image.get_rect().contains(image.get_bounding_rect()))
  self.assertEqual(sum(p['min_seconds'] for p in self.scene.manifest['phases']),18)
  self.assertEqual(len(self.scene.manifest['gear_hands']),4)
  for r in self.scene.manifest['gear_hands']:
   path=ASSETS/r['file'];self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),r['sha256'])
   self.assertEqual(pygame.image.load(str(path)).get_size(),(480,320))
if __name__=='__main__':unittest.main()
