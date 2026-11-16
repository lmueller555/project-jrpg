"""Display-resolution shop menu using the game's shared painter and controls."""
import pygame
from economy import purchase
from inventory import MAX_QUANTITY
from ui_style import FOREST, IVORY, INK, GOLD


class ShopUI:
    def __init__(self, game, services):
        self.game=game;self.services=services
        self.reset()
        self.close_rect=pygame.Rect(436,20,24,24)
        self.buy_rect=pygame.Rect(224,274,116,24)
        self.leave_rect=pygame.Rect(350,274,96,24)
        self.minus_rect=pygame.Rect(224,191,34,26)
        self.plus_rect=pygame.Rect(404,191,34,26)
        self.yes_rect=pygame.Rect(108,199,124,28)
        self.no_rect=pygame.Rect(248,199,124,28)
        self.detail_rect=pygame.Rect(224,94,218,85)

    @property
    def stock(self):return self.services.data['shop']['stock']
    @property
    def identifier(self):return list(self.stock)[self.index]

    def reset(self):
        self.is_open=False;self.index=0;self.quantity=1;self.confirming=False
        self.changed=False;self.notice='';self.detail_scroll=0;self._held=False

    def open(self):
        if not self.services.nearby('shop'):return False
        self.reset();self.is_open=True
        self.game.player.moving=self.game.player.running=False
        self.game.player.walk_ms=0
        self.game.ui.sound('confirm')
        return True

    def close(self):
        changed=self.changed
        self.reset()
        self.game.social.clear_pointer()
        if changed:self.game.saves.request_service('shop')
        self.game.ui.sound('back')

    def change_item(self, offset):
        self.index=(self.index+offset)%len(self.stock)
        self.quantity=1;self.notice='';self.detail_scroll=0
        self.game.ui.sound('move')

    def change_quantity(self, offset):
        capacity=MAX_QUANTITY-self.game.inventory.quantity(self.identifier)
        self.quantity=max(1,min(max(1,capacity),self.quantity+offset))
        self.notice=''

    def buy(self):
        ok,self.notice=purchase(self.game.inventory,self.game.wallet,self.stock,self.identifier,self.quantity)
        self.confirming=False
        self.changed |= ok
        self.game.ui.sound('confirm' if ok else 'back')
        return ok

    def handle_event(self,event):
        if not self.is_open:return False
        if not self.game._music_focused:return True
        if event.type == pygame.KEYDOWN and not getattr(event,'repeat',False):
            if event.key in (pygame.K_ESCAPE,pygame.K_BACKSPACE):
                if self.confirming:self.confirming=False
                else:self.close()
            elif event.key in (pygame.K_RETURN,pygame.K_KP_ENTER,pygame.K_SPACE,pygame.K_e):
                if self.confirming:self.buy()
                else:self.confirming=True
            elif not self.confirming:
                if event.key in (pygame.K_UP,pygame.K_w):self.change_item(-1)
                elif event.key in (pygame.K_DOWN,pygame.K_s):self.change_item(1)
                elif event.key in (pygame.K_LEFT,pygame.K_a):self.change_quantity(-1)
                elif event.key in (pygame.K_RIGHT,pygame.K_d):self.change_quantity(1)
                elif event.key == pygame.K_PAGEUP:self.change_quantity(10)
                elif event.key == pygame.K_PAGEDOWN:self.change_quantity(-10)
        elif event.type == pygame.MOUSEWHEEL and not self.confirming:
            self.detail_scroll=max(0,self.detail_scroll-event.y*14)
        elif event.type == pygame.MOUSEBUTTONUP and event.button==1:self._held=False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button==1 and not self._held:
            self._held=True;point=self.game.to_canvas(event.pos)
            if point is None:return True
            if self.confirming:
                if self.yes_rect.collidepoint(point):self.buy()
                elif self.no_rect.collidepoint(point):self.confirming=False
            elif self.close_rect.collidepoint(point) or self.leave_rect.collidepoint(point):self.close()
            elif self.buy_rect.collidepoint(point):self.confirming=True
            elif self.minus_rect.collidepoint(point):self.change_quantity(-1)
            elif self.plus_rect.collidepoint(point):self.change_quantity(1)
            else:
                for i in range(len(self.stock)):
                    if pygame.Rect(24,68+i*43,184,40).collidepoint(point):self.change_item(i-self.index);break
        return True

    def draw(self,canvas):
        if not self.is_open:return
        p=self.game.ui.painter(canvas);p.veil(210);p.panel((12,12,456,296),parchment=True)
        p.text('Item Shop',(24,21),role='heading',color=FOREST,bold=True)
        p.text(f'{self.game.wallet.gold} gold',(422,26),anchor='topright',color=FOREST)
        p.button(self.close_rect,'×')
        p.text('Select an item',(24,49),role='small',color=INK)
        for i,key in enumerate(self.stock):
            definition=self.game.inventory.definitions[key];rect=pygame.Rect(24,68+i*43,184,40)
            p.button(rect,'',selected=i==self.index)
            p.text(definition['name'],(rect.x+19,rect.y+3),color=GOLD if i==self.index else IVORY)
            p.text(f'{self.stock[key]} gold · Owned: {self.game.inventory.quantity(key)}',(rect.x+19,rect.y+23),role='small',color=IVORY)
        definition=self.game.inventory.definitions[self.identifier]
        p.text(definition['name'],(224,69),role='name',color=FOREST,bold=True)
        lines=p.wrap(definition['description'],self.detail_rect.width)
        height=p.font().get_linesize()+3
        self.detail_scroll=min(self.detail_scroll,max(0,len(lines)*height-self.detail_rect.height))
        p.clip(self.detail_rect)
        for i,line in enumerate(lines):p.text(line,(224,94+i*height-self.detail_scroll),color=INK)
        p.clip(None)
        p.text('Quantity',(224,176),role='small',color=INK)
        p.button(self.minus_rect,'−');p.button(self.plus_rect,'+')
        p.text(str(self.quantity),(330,204),anchor='center',color=FOREST)
        total=self.stock[self.identifier]*self.quantity
        p.text(f'Total: {total} gold',(224,225),color=FOREST,bold=True)
        for i,line in enumerate(p.wrap(self.notice or 'Arrows: select / quantity. Wheel: read.',218,role='small')[:2]):
            p.text(line,(224,245+i*p.font('small').get_linesize()),role='small',color=INK)
        p.button(self.buy_rect,'Buy');p.button(self.leave_rect,'Leave')
        if self.confirming:
            p.veil(190);p.panel((74,102,332,140),parchment=True)
            message=f'Buy {self.quantity} × {definition["name"]} for {total} gold?'
            for i,line in enumerate(p.wrap(message,292,role='name')):
                p.text(line,(94,122+i*(p.font('name').get_linesize()+3)),role='name',color=FOREST)
            p.button(self.yes_rect,'Confirm');p.button(self.no_rect,'Cancel')
