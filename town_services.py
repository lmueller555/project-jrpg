"""Repeatable town services; menus and queued autosaves own no quest progress."""
from copy import deepcopy
import json
from pathlib import Path
import pygame
from economy import valid_gold
from shop_ui import ShopUI


class TownServices:
    def __init__(self, game):
        self.game = game
        self.data = json.loads((Path(__file__).parent/'assets/services/eldenmere.json').read_text())
        stock = self.data['shop']['stock']
        if (not stock or any(key not in game.inventory.definitions
                or game.inventory.definitions[key]['category'] != 'items'
                or not valid_gold(price) for key, price in stock.items())
                or not valid_gold(self.data['inn']['price'])):
            raise ValueError('Invalid town service definitions')
        self.shop = ShopUI(game, self)

    @property
    def is_open(self):return self.shop.is_open
    def reset(self):self.shop.reset()
    def handle_event(self,event):return self.shop.handle_event(event)
    def draw(self,canvas):self.shop.draw(canvas)

    def nearby(self, kind):
        g = self.game;record = self.data[kind]
        if not g.bed_rest.available(record):return False
        actor = next((n for n in g.world.npcs if n.data['id'] == record['keeper']), None)
        counter = next((e for e in g.world.entities if e['id'] == record['counter']), None)
        if actor is None or counter is None:return False
        # Speak across the front of the actual counter, never through its back
        # wall or from anywhere else in the room.
        rect = counter['rect']
        approach = pygame.Rect(rect.left-8, rect.bottom-10, rect.width+16, 36)
        return approach.collidepoint(g.player.position)

    def interaction_hint(self):
        for kind,record in self.data.items():
            if self.nearby(kind):return 'E: speak to '+record['speaker']
        return ''

    def interact(self):
        g = self.game
        for kind,record in self.data.items():
            if not self.nearby(kind):continue
            if kind == 'inn':return g.bed_rest.offer_inn(lambda:self.nearby('inn'))
            return g.social.start_choice(
                [{'speaker':record['speaker'],'text':record['offer']}],
                [{'text':'Buy','action':'buy'},{'text':'Leave','action':'leave'}],
                lambda action:self.shop.open() if action == 'buy' and self.nearby('shop') else None,
                identifier='item_shop_offer',prompt='Browse the shop?')
        return False

    def rest_profile(self):
        profile = deepcopy(self.game.world.data['rest_profile'])
        record = self.data['inn'];price = record['price']
        profile.update(service_id='inn',price=price,
            offer=[{'speaker':record['speaker'],'text':record['offer']}],
            prompt=f'Stay for {price} gold? '+record['recovery'],
            choices=[{'text':f'Stay — {price} gold','action':'rest'},
                     {'text':'Leave','action':'leave'}])
        return profile
