"""Responsive, mouse/keyboard title menu over Eldenmere's dawn vista."""
import math
from pathlib import Path

import pygame
from title_water import TitleWater
from audio_settings import AudioSettings
from pause_menu import SettingsPanel
from ui_style import UIStyle, GOLD, IVORY, BRASS, MUTED, DISABLED

ROOT=Path(__file__).resolve().parent
SIZE=(640,360)


class TitleScreen:
    settings_index = 2
    def __init__(self,game):
        self.game=game
        if not hasattr(game,'audio'):game.audio=AudioSettings()
        if not hasattr(game,'ui'):game.ui=UIStyle(game)
        self.scene=pygame.Surface(SIZE)
        self.ui=pygame.Surface(SIZE,pygame.SRCALPHA)
        self.canvas=self.scene
        self.frame=None
        self.background=game.town.image('assets/ui/title/eldenmere_dawn.png',False)
        self.water=TitleWater(game.town)
        wheel=pygame.transform.scale(self.background.subsurface((237,201,26,36)),(36,36)).convert_alpha()
        mask=pygame.Surface((36,36),pygame.SRCALPHA)
        pygame.draw.ellipse(mask,'white',(0,0,36,36))
        wheel.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        self.wheel_frames=[]
        for i in range(48):
            rotated=pygame.transform.rotate(wheel,-i*360/48)
            frame=pygame.Surface((36,36),pygame.SRCALPHA)
            frame.blit(rotated,rotated.get_rect(center=(18,18)))
            frame.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
            self.wheel_frames.append(pygame.transform.scale(frame,(26,36)))
        self.serif=lambda size:pygame.font.Font(str(ROOT/'assets/ui/fonts/DejaVuSerif.ttf'),size)
        self.selected=0
        self.settings=False
        self.elapsed=0.0
        self.fade=0.0
        self.continuing=False
        self.music_started=False
        self.options=('New Game','Continue','Settings','Quit')
        self.rows=[pygame.Rect(235,243+i*24,170,22) for i in range(4)]
        self.settings_panel=SettingsPanel(self,SIZE)
        self.settings_rows=self.settings_panel.rows
        self.slider_rects=self.settings_panel.slider_rects
        self._mouse_held=False
        self._pressed=None
        self._logo_fonts={}

    @property
    def music_enabled(self):return self.game.audio.music_volume>0

    @music_enabled.setter
    def music_enabled(self, enabled):
        if bool(enabled) != self.music_enabled:self.game.audio.toggle_music()

    def _sync_music(self):
        if not self.music_enabled:
            if self.music_started:pygame.mixer.music.stop();self.music_started=False
        elif not self.music_started and getattr(self.game,'on_title',True):
            self.start_music()

    def _adjust_volume(self,direction):
        return self.settings_panel._adjust(direction)

    def start_music(self):
        if not self.music_enabled:return
        try:
            if not pygame.mixer.get_init():pygame.mixer.init()
            pygame.mixer.music.load(str(ROOT/'assets/ui/title/eldenmere_theme.ogg'))
            pygame.mixer.music.set_volume(.45*self.game.audio.music_volume)
            pygame.mixer.music.play(-1,fade_ms=900)
            self.music_started=True
        except pygame.error:
            # Machines without an audio output can still launch and play.
            self.music_started=False

    def to_canvas(self,point):
        width,height=self.game.window.get_size()
        scale=min(width/SIZE[0],height/SIZE[1])
        return pygame.Vector2((point[0]-(width-SIZE[0]*scale)/2)/scale,
                              (point[1]-(height-SIZE[1]*scale)/2)/scale)

    def _row_at(self,point):
        rows=self.settings_rows if self.settings else self.rows
        return next((i for i,row in enumerate(rows) if row.collidepoint(point)),None)

    def handle_event(self,event):
        if self.fade:return True
        if self.settings:return self.settings_panel.handle_event(event)
        if event.type==pygame.MOUSEBUTTONUP and event.button==1:
            self._mouse_held=False;self._pressed=None
        elif event.type==pygame.MOUSEMOTION:
            row=self._row_at(self.to_canvas(event.pos))
            if row is not None and row!=self.selected:
                self.selected=row;self.game.ui.sound('move')
        elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            if self._mouse_held:return True
            self._mouse_held=True
            row=self._row_at(self.to_canvas(event.pos))
            if row is not None:
                self.selected=self._pressed=row
                return self.activate()
        elif event.type==pygame.KEYDOWN and not getattr(event,'repeat',False):
            if event.key in (pygame.K_UP,pygame.K_w,pygame.K_DOWN,pygame.K_s):
                step=-1 if event.key in (pygame.K_UP,pygame.K_w) else 1
                self.selected=(self.selected+step)%len(self.options)
                if self.selected==1 and not self.game.has_saved_journey:
                    self.selected=(self.selected+step)%len(self.options)
                self.game.ui.sound('move')
            elif event.key in (pygame.K_RETURN,pygame.K_KP_ENTER,pygame.K_SPACE):return self.activate()
        return True

    def activate(self):
        if self.settings:return self.settings_panel.activate()
        if self.selected==0:
            self.continuing=False
            self.fade=.001
            self.game.ui.sound('confirm')
            if self.music_started:pygame.mixer.music.fadeout(0 if getattr(self.game.audio,'reduced_motion',False) else 650)
        elif self.selected==1 and self.game.has_saved_journey:
            self.continuing=True
            self.fade=.001
            self.game.ui.sound('confirm')
            if self.music_started:pygame.mixer.music.fadeout(0 if getattr(self.game.audio,'reduced_motion',False) else 650)
        elif self.selected==2:
            self.settings=True;self.selected=0;self.settings_panel.reset()
            self.game.ui.sound('confirm')
        elif self.selected==3:
            self.game.ui.sound('confirm');return False
        return True

    def update(self,seconds):
        self.elapsed+=seconds
        if self.fade:
            self.fade+=seconds
            if self.fade>=(.01 if getattr(self.game.audio,'reduced_motion',False) else .65):
                self.game.begin_journey(self.continuing)

    def atmosphere(self):
        t=self.elapsed
        # Rotate the painted wheel within its elliptical perspective footprint.
        self.canvas.blit(self.wheel_frames[int(t*3)%48],(237,201))
        layer=pygame.Surface(SIZE,pygame.SRCALPHA)
        # Water has complete, independently authored surface and cascade layers.
        for x,y in ((278,142),(615,69)):
            for i in range(3):
                p=(t/5.4+i/3)%1
                pygame.draw.circle(layer,(226,225,206,round(22*math.sin(p*math.pi))),
                                   (round(x+8*p),round(y-15*p)),round(1+2*p))
        pulse=round(14+5*math.sin(t*4.1))
        pygame.draw.circle(layer,(255,192,75,pulse),(53,173),6)
        # A small bird pair crosses the open sky only once per long cycle.
        cycle=t%32
        if 14<cycle<22:
            for i in range(2):
                x=round((cycle-14)*55)-20-i*12
                y=42+i*5+round(math.sin(t*4+i))
                pygame.draw.lines(layer,(72,89,94,160),False,[(x-2,y),(x,y+1),(x+2,y)])
        self.canvas.blit(layer,(0,0))

    def _layout_menu(self,painter):
        row_height=max(22,painter.font('body').get_height()+4)
        stride=row_height+2
        footer=painter.font('small').get_height()+22
        panel=pygame.Rect(225,358-(stride*4+footer),190,stride*4+footer)
        self.rows[:]=[pygame.Rect(235,panel.top+7+index*stride,170,row_height)
                      for index in range(4)]
        return panel

    def _logo(self,painter,text,base_size,y):
        # Logo lettering is rasterized directly at the display's resolution.
        size=max(1,round(base_size*painter.scale))
        if size not in self._logo_fonts:self._logo_fonts[size]=self.serif(size)
        font=self._logo_fonts[size]
        center=painter.point((320,y))
        shadow=font.render(text,True,'#263c35')
        image=font.render(text,True,IVORY)
        self.ui.blit(shadow,shadow.get_rect(midtop=(center[0]+round(painter.scale),center[1]+round(painter.scale*2))))
        self.ui.blit(image,image.get_rect(midtop=center))

    def draw(self):
        self.canvas=self.scene
        self.canvas.blit(self.background,(0,0))
        self.water.draw(self.canvas,self.elapsed)
        self.atmosphere()
        width,height=self.game.window.get_size()
        if self.frame is None or self.frame.get_size()!=(width,height):
            self.frame=pygame.Surface((width,height)).convert()
            self.frame.set_alpha(None)
        cover=max(width/SIZE[0],height/SIZE[1])
        size=(math.ceil(SIZE[0]*cover),math.ceil(SIZE[1]*cover))
        self.frame.blit(pygame.transform.scale(self.scene,size),
                        ((width-size[0])//2,(height-size[1])//2))
        # This transparent layer already has its final display dimensions:
        # neither Atkinson body text nor serif logo pixels are enlarged later.
        fit=min(width/SIZE[0],height/SIZE[1])
        ui_size=(round(SIZE[0]*fit),round(SIZE[1]*fit))
        if self.ui.get_size()!=ui_size:self.ui=pygame.Surface(ui_size,pygame.SRCALPHA)
        self.ui.fill((0,0,0,0))
        painter=self.game.ui.painter(self.ui,SIZE)
        if self.settings:
            painter.veil(165)
            self.settings_panel.draw(painter)
        else:
            self._logo(painter,'THE BROKEN',30,22)
            self._logo(painter,'COVENANT',43,53)
            painter.line(BRASS,(257,108),(299,108))
            painter.line(BRASS,(341,108),(383,108))
            painter.lantern((320,108),size=9)
            painter.text('E L D E N M E R E',(320,120),role='small',anchor='midtop')
            menu_panel=self._layout_menu(painter)
            painter.panel(menu_panel)
            for index,(label,row) in enumerate(zip(self.options,self.rows)):
                disabled=index==1 and not self.game.has_saved_journey
                painter.button(row,label,selected=index==self.selected,
                               pressed=self._pressed==index and self._mouse_held,disabled=disabled)
            hint=('Saved journey unavailable' if self.game.save_error else 'No saved journey yet') if self.selected==1 and not self.game.has_saved_journey else 'Click or arrows + Enter'
            if painter.font('small').size(hint)[0]>menu_panel.width-16:
                hint=('Save unavailable' if self.game.save_error else 'No saved game') if self.selected==1 and not self.game.has_saved_journey else 'Arrows + Enter'
            painter.text(hint,(320,menu_panel.bottom-6),role='small',color=MUTED,anchor='midbottom')
        self.frame.blit(self.ui,((width-ui_size[0])//2,(height-ui_size[1])//2))
        if self.fade:
            duration=.01 if getattr(self.game.audio,'reduced_motion',False) else .65
            shade=pygame.Surface((width,height),pygame.SRCALPHA)
            shade.fill((11,24,22,min(255,round(self.fade/duration*255))))
            self.frame.blit(shade,(0,0))
        self.game.window.blit(self.frame,(0,0))
        pygame.display.flip()
