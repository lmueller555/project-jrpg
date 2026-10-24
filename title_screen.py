"""Responsive, mouse/keyboard title menu over Eldenmere's dawn vista."""
import math
from pathlib import Path

import pygame

ROOT=Path(__file__).resolve().parent
SIZE=(640,360)


class TitleScreen:
    def __init__(self,game):
        self.game=game
        self.scene=pygame.Surface(SIZE)
        self.ui=pygame.Surface(SIZE,pygame.SRCALPHA)
        self.canvas=self.scene
        self.background=game.town.image('assets/ui/title/eldenmere_dawn.png',False)
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
        self.sans=lambda size:pygame.font.Font(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'),size)
        self.logo_small=self.serif(30)
        self.logo_large=self.serif(43)
        self.menu_font=self.serif(16)
        self.detail_font=self.sans(8)
        self.heading_font=self.serif(21)
        self.selected=0
        self.settings=False
        self.elapsed=0.0
        self.fade=0.0
        self.music_enabled=True
        self.music_started=False
        self.options=('New Game','Continue','Settings','Quit')
        self.rows=[pygame.Rect(250,247+i*21,140,21) for i in range(4)]
        self.settings_rows=[pygame.Rect(226,265+i*25,188,23) for i in range(3)]

    def start_music(self):
        if not self.music_enabled:return
        try:
            if not pygame.mixer.get_init():pygame.mixer.init()
            pygame.mixer.music.load(str(ROOT/'assets/ui/title/eldenmere_theme.wav'))
            pygame.mixer.music.set_volume(.45)
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
        if event.type==pygame.MOUSEMOTION:
            row=self._row_at(self.to_canvas(event.pos))
            if row is not None:self.selected=row
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            row=self._row_at(self.to_canvas(event.pos))
            if row is not None:
                self.selected=row
                return self.activate()
        if event.type==pygame.KEYDOWN and not getattr(event,'repeat',False):
            if event.key in (pygame.K_UP,pygame.K_w,pygame.K_DOWN,pygame.K_s):
                step=-1 if event.key in (pygame.K_UP,pygame.K_w) else 1
                count=3 if self.settings else 4
                self.selected=(self.selected+step)%count
                if not self.settings and self.selected==1:self.selected=(self.selected+step)%count
            elif event.key in (pygame.K_RETURN,pygame.K_SPACE):return self.activate()
            elif event.key==pygame.K_ESCAPE:
                if self.settings:self.settings=False;self.selected=2
        return True

    def activate(self):
        if self.settings:
            if self.selected==0:self.game.toggle_fullscreen()
            elif self.selected==1:
                self.music_enabled=not self.music_enabled
                if self.music_enabled:self.start_music()
                elif self.music_started:pygame.mixer.music.stop();self.music_started=False
            else:self.settings=False;self.selected=2
        elif self.selected==0:
            self.fade=.001
            if self.music_started:pygame.mixer.music.fadeout(650)
        elif self.selected==2:self.settings=True;self.selected=0
        elif self.selected==3:return False
        return True

    def update(self,seconds):
        self.elapsed+=seconds
        if self.fade:
            self.fade+=seconds
            if self.fade>=.65:
                self.game.on_title=False
                self.game.opening_fade=.5
                self.game.player.moving=False
                self.game._mouse_held=False

    def centered(self,text,font,y,color='#f7eed5',shadow=True):
        rendered=font.render(text,False,color)
        x=(SIZE[0]-rendered.get_width())//2
        if shadow:
            self.canvas.blit(font.render(text,False,'#263c35'),(x+1,y+2))
        self.canvas.blit(rendered,(x,y))

    def atmosphere(self):
        t=self.elapsed
        # Rotate the painted wheel within its elliptical perspective footprint.
        self.canvas.blit(self.wheel_frames[int(t*3)%48],(237,201))
        layer=pygame.Surface(SIZE,pygame.SRCALPHA)
        # Anchors are authored on the painted water, chimney and lantern.
        for i,(x,y) in enumerate(((230,235),(266,257),(300,274),(117,332),(183,345),(245,352))):
            phase=(t*.45+i*.31)%1
            alpha=round(45*math.sin(phase*math.pi))
            pygame.draw.line(layer,(235,240,204,alpha),(x+phase*4,y),(x+phase*4+3,y))
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

    def draw(self):
        self.canvas=self.scene
        self.canvas.blit(self.background,(0,0))
        self.atmosphere()
        width,height=self.game.window.get_size()
        scale=max(width/SIZE[0],height/SIZE[1])
        size=(math.ceil(SIZE[0]*scale),math.ceil(SIZE[1]*scale))
        self.game.window.blit(pygame.transform.scale(self.scene,size),
                              ((width-size[0])//2,(height-size[1])//2))
        # The scene covers every aspect ratio; UI fits entirely inside it.
        self.canvas=self.ui
        self.canvas.fill((0,0,0,0))
        # Shadow and fine gold rules keep the logo readable over the sky.
        self.centered('THE BROKEN',self.logo_small,22)
        self.centered('COVENANT',self.logo_large,53)
        pygame.draw.line(self.canvas,'#c9b67b',(257,108),(299,108))
        pygame.draw.line(self.canvas,'#c9b67b',(341,108),(383,108))
        pygame.draw.polygon(self.canvas,'#f1d68f',[(320,104),(324,108),(320,112),(316,108)])
        self.centered('E L D E N M E R E',self.detail_font,119,'#f7eed5')

        panel=pygame.Surface((190,106),pygame.SRCALPHA)
        panel.fill((18,39,32,220))
        self.canvas.blit(panel,(225,241))
        pygame.draw.line(self.canvas,'#9b9a70',(242,241),(398,241))
        pygame.draw.line(self.canvas,'#9b9a70',(242,346),(398,346))
        labels=(('Display: '+('Fullscreen' if self.game.fullscreen else 'Windowed'),
                 'Music: '+('On' if self.music_enabled else 'Off'),'Back')
                if self.settings else self.options)
        rows=self.settings_rows if self.settings else self.rows
        if self.settings:self.centered('Settings',self.menu_font,243)
        for i,(label,row) in enumerate(zip(labels,rows)):
            disabled=not self.settings and i==1
            active=i==self.selected
            if active and not disabled:
                pygame.draw.rect(self.canvas,'#344e3e',row)
                # Small lantern selection marker.
                pygame.draw.rect(self.canvas,'#ceb676',(row.left+8,row.centery-3,5,7),1)
                pygame.draw.line(self.canvas,'#ceb676',(row.left+9,row.centery-5),(row.left+11,row.centery-5))
                self.canvas.set_at((row.left+10,row.centery),(255,218,132))
            color='#7f8d7d' if disabled else ('#ffe1a0' if active else '#eee2c0')
            self.centered(label,self.menu_font,row.y+1,color,False)
        if not self.settings and self.selected==1:
            self.centered('No saved journey yet',self.detail_font,350,'#d2c8a7',False)
        else:self.centered('Click to choose  /  Arrow keys + Enter',self.detail_font,350,'#d2c8a7',False)
        scale=min(width/SIZE[0],height/SIZE[1])
        size=(round(SIZE[0]*scale),round(SIZE[1]*scale))
        self.game.window.blit(pygame.transform.scale(self.ui,size),
                              ((width-size[0])//2,(height-size[1])//2))
        if self.fade:
            shade=pygame.Surface((width,height),pygame.SRCALPHA)
            shade.fill((11,24,22,min(255,round(self.fade/.65*255))))
            self.game.window.blit(shade,(0,0))
        pygame.display.flip()
