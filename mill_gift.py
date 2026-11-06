"""Player-paced, eighteen-second birthday gift insert at Mira's workshop.

The view owns transient shots and input only. MillQuest owns the durable gift
receipt and supplies the completion callback; dismissing/reloading never grants
an item from a partially read scene. All portraits/prose use gameplay's shared
textbox renderer, with literal asterisk emotes.
"""
from __future__ import annotations
import json,math
from pathlib import Path
import pygame
import speech_bubble
from ui_style import IVORY,MUTED
ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/'assets/story/mill_gift'
PHASES=('reveal','whole','handoff','gear','faces')

def smooth(value):
 value=max(0.,min(1.,value));return value*value*(3-2*value)

class MillGift:
 def __init__(self,game,*,asset_root=ASSETS):
  self.game=game;self.asset_root=Path(asset_root)
  self.manifest=json.loads((self.asset_root/'animation.json').read_text())
  if self.manifest.get('version')!=1 or [p['id'] for p in self.manifest['phases']]!=list(PHASES):
   raise ValueError('Invalid mill gift presentation')
  self.images=None;self._scaled={};self._click_sound=None;self._click_channel=None;self.reset()

 def reset(self):
  self.stop_audio()
  self.active=False;self.paused=False;self.focused=True
  self.elapsed=0.;self.phase_time=0.;self.phase_index=0
  self.dialogue_index=0;self.page_index=0
  self.sections=[];self.caption_pages=[];self.caption_lines=[];self.caption_layout=None
  self._on_complete=None;self._mouse_held=False;self._keys=set()
  self._batch_advanced=False;self._batch_pause=False;self._input_armed=False
  self._gear_clicked=False;self.finished_reason=None

 @property
 def shot(self):return PHASES[self.phase_index]
 @property
 def phase(self):return self.manifest['phases'][self.phase_index]
 @property
 def reduced_motion(self):return bool(getattr(self.game.audio,'reduced_motion',False))
 @property
 def dialogue(self):
  if not self.active:return None
  lines=self.sections[self.phase_index]
  return lines[self.dialogue_index] if self.dialogue_index<len(lines) else None
 @property
 def animation_seconds(self):
  return sum(p['min_seconds'] for p in self.manifest['phases'][:self.phase_index])+min(self.phase_time,self.phase['min_seconds'])

 def start(self,lines,on_complete=None):
  if self.active:return False
  groups={key:[] for key in PHASES};current=None;seen=[]
  for line in lines:
   cue=line.get('cue')
   if cue is not None:
    if cue not in PHASES or cue in seen:raise ValueError('Invalid gift shot cue')
    current=cue;seen.append(cue)
   if current is None or line.get('speaker') not in ('caelan','mira') or not line.get('text'):
    raise ValueError('Invalid gift dialogue')
   groups[current].append(dict(line))
  if seen!=list(PHASES) or any(not groups[key] for key in PHASES):
   raise ValueError('Gift dialogue must cover all five shots')
  self.reset();self.sections=[groups[key] for key in PHASES];self._on_complete=on_complete
  self.active=True;self.focused=bool(getattr(self.game,'_music_focused',True))
  return True

 def begin_input_batch(self):self._batch_advanced=False;self._batch_pause=False
 # Alias keeps the API easy to use alongside older cinematic controllers.
 begin_event_batch=begin_input_batch

 def _load(self):
  if self.images is not None:return
  self.images={key:pygame.image.load(str(self.asset_root/(key+'.png'))).convert_alpha()
               for key in ('workshop','blade','gear','blade_base')}
  self.images['handoff']=[pygame.image.load(str(self.asset_root/f['file'])).convert_alpha()
                          for f in self.manifest['frames']]
  self.images['gear_hands']=[pygame.image.load(str(self.asset_root/f['file'])).convert_alpha() for f in self.manifest['gear_hands']]

 def _layout(self,painter):
  self.caption_layout=None;self.caption_pages=[];self.caption_lines=[]
  line=self.dialogue
  if line is None:return
  profile=self.game.social.data['speakers'][line['speaker']]
  wrapped=painter.wrap(line['text'],speech_bubble.TEXT_WIDTH)
  self.caption_pages=[wrapped[i:i+speech_bubble.MAX_LINES] for i in range(0,len(wrapped),speech_bubble.MAX_LINES)]
  self.page_index=min(self.page_index,len(self.caption_pages)-1)
  self.caption_lines=self.caption_pages[self.page_index]
  names,top,line_height,height=speech_bubble.measure_dialogue(painter,profile['name'],self.caption_lines)
  panel=pygame.Rect((480-speech_bubble.PANEL_WIDTH)//2,310-math.ceil(height),speech_bubble.PANEL_WIDTH,math.ceil(height))
  portrait=pygame.Rect(panel.x+speech_bubble.PADDING,panel.y+12,speech_bubble.PORTRAIT_SIZE,speech_bubble.PORTRAIT_SIZE)
  self.caption_layout=speech_bubble.BubbleLayout(panel,portrait,(panel.x+speech_bubble.TEXT_OFFSET,panel.y+top),(),panel.midtop,
   None,False,False,profile['portrait'],name_lines=names,line_height=line_height)

 def advance(self):
  if (not self.active or self.paused or not self.focused or not self._input_armed
      or not getattr(self.game,'_music_focused',True) or self._batch_advanced or self.dialogue is None):return False
  self._batch_advanced=True
  self._layout(self.game.ui.painter(self.game.ui_surface))
  if self.page_index+1<len(self.caption_pages):self.page_index+=1
  else:self.dialogue_index+=1;self.page_index=0
  self._next_if_ready();return True

 def handle_event(self,event):
  if not self.active:return False
  if event.type==pygame.WINDOWFOCUSLOST:
   self.focused=False;self._keys.clear();self._mouse_held=False
  elif event.type==pygame.WINDOWFOCUSGAINED:self.focused=True
  elif event.type==pygame.KEYUP:self._keys.discard(event.key)
  elif event.type==pygame.MOUSEBUTTONUP and event.button==1:self._mouse_held=False
  elif self.focused and event.type==pygame.KEYDOWN:
   if getattr(event,'repeat',False) or event.key in self._keys:return True
   self._keys.add(event.key)
   if event.key==pygame.K_ESCAPE and not self._batch_pause:
    self.paused=not self.paused;self._batch_pause=True
   elif event.key in (pygame.K_SPACE,pygame.K_RETURN,pygame.K_e):self.advance()
  elif self.focused and event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
   if not self._mouse_held and self.game.to_canvas(event.pos) is not None:self.advance()
   self._mouse_held=True
  self._sync_audio()
  return True

 def _next_if_ready(self):
  if self.phase_time<self.phase['min_seconds'] or self.dialogue_index<len(self.sections[self.phase_index]):return
  if self.phase_index==len(PHASES)-1:
   callback=self._on_complete;self._on_complete=None;self.active=False;self.finished_reason='finished';self.stop_audio()
   if callback is not None:callback()
   return
  self.phase_index+=1;self.phase_time=0.;self.dialogue_index=0;self.page_index=0
  self.caption_layout=None;self.caption_pages=[];self.caption_lines=[]

 def update(self,seconds):
  self._sync_audio()
  if not self.active or self.paused or not self.focused or not getattr(self.game,'_music_focused',True):return
  seconds=max(0.,float(seconds));self.elapsed+=seconds;self.phase_time+=seconds
  self._input_armed=self.elapsed>=.1
  if self.shot=='gear' and self.phase_time>=3.1 and not self._gear_clicked:
   self._gear_clicked=True
   self._play_click()
  self._next_if_ready()

 def stop_audio(self):
  channel=getattr(self,'_click_channel',None)
  try:
   if channel is not None and channel.get_sound() is self._click_sound:channel.stop()
  except pygame.error:pass
  self._click_channel=None

 def _play_click(self):
  if not pygame.mixer.get_init() or float(self.game.audio.effects_volume)<=0:return
  try:
   if self._click_sound is None:self._click_sound=pygame.mixer.Sound(str(self.asset_root/'gear_click.ogg'))
   self._click_channel=self._click_sound.play()
   self._sync_audio()
  except (pygame.error,OSError):self._click_channel=None

 def _sync_audio(self):
  if self._click_channel is None:return
  try:
   if self._click_channel.get_sound() is not self._click_sound:
    self._click_channel=None;return
   self._click_channel.set_volume(.14*float(self.game.audio.effects_volume))
   if self.paused or not self.focused or not getattr(self.game,'_music_focused',True):self._click_channel.pause()
   else:self._click_channel.unpause()
  except pygame.error:self._click_channel=None

 def _scale(self,image,width,height=None):
  height=height or round(image.get_height()*width/image.get_width())
  key=(id(image),round(width),round(height))
  if key not in self._scaled:
   if len(self._scaled)>320:self._scaled.clear()
   self._scaled[key]=pygame.transform.scale(image,(max(1,round(width)),max(1,round(height))))
  return self._scaled[key]

 def _plate(self,canvas,center,zoom):
  plate=self.images['workshop'];w,h=480/zoom,320/zoom
  cx,cy=center
  rect=pygame.Rect(round(cx-w/2),round(cy-h/2),round(w),round(h)).clamp(plate.get_rect())
  pygame.transform.scale(plate.subsurface(rect),canvas.get_size(),canvas)

 def draw(self,canvas,ui_surface):
  self._load();q=smooth(self.phase_time/self.phase['min_seconds']);motion=1. if self.reduced_motion else q
  if self.shot in ('reveal','handoff','faces'):
   zoom=(.82+.025*motion) if self.shot=='reveal' else .85
   self._plate(canvas,(480,480),zoom)
   if self.shot=='reveal':frame=0
   elif self.shot=='handoff':frame=min(5,int(q*6))
   else:frame=6 if self.phase_time<.9 else 7
   pair=self.images['handoff'][frame]
   pair=self._scale(pair,320 if self.shot=='faces' else 300)
   # Keep the characters' heads and weapon above the common portrait panel.
   canvas.blit(pair,(240-pair.get_width()//2,214-pair.get_height()))
  elif self.shot=='whole':
   self._plate(canvas,(300,455),.95+.08*motion)
   blade=pygame.transform.rotate(self.images['blade'],90)
   blade=self._scale(blade,330)
   canvas.blit(blade,(75+round(8*motion),158-blade.get_height()//2))
  else:
   self._plate(canvas,(330,430),1.35)
   # Four authored hand drawings show the fixed grip and actual finger turn.
   # The final blue focus aligns with the blade; no elemental spell is cast.
   index=min(3,max(0,int((self.phase_time-.6)/.85)))
   if self.reduced_motion:index=3
   hands=self.images['gear_hands'][index]
   canvas.blit(hands,(0,3))
  # Very subtle transition on shot entry; dialogue has no timed dismissal.
  alpha=round(90*(1-smooth(self.phase_time/.22)))
  if alpha:
   veil=pygame.Surface(canvas.get_size(),pygame.SRCALPHA);veil.fill((12,20,16,alpha));canvas.blit(veil,(0,0))
  pygame.transform.scale(canvas,ui_surface.get_size(),ui_surface)
  painter=self.game.ui.painter(ui_surface);self._layout(painter)
  if self.caption_layout is not None:
   portrait=self.game.social.portraits[self.caption_layout.portrait_key]
   speech_bubble.draw_dialogue_frame(painter,self.caption_layout,portrait)
   speech_bubble.draw_dialogue_prose(painter,self.caption_layout,self.caption_lines,hint='Click to continue',
    show_indicator=self.reduced_motion or int(self.elapsed/.65)%2==0)
  painter.text('Esc · Resume' if self.paused else 'Esc · Pause',(12,310),role='small',color=MUTED,anchor='bottomleft')
  if self.paused or not self.focused or not getattr(self.game,'_music_focused',True):
   rect=pygame.Rect(193,20,94,26);painter.panel(rect)
   painter.text('Paused',rect.center,role='label',color=IVORY,bold=True,anchor='center')
