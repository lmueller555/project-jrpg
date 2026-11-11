#!/usr/bin/env python3
"""Render real item menus/effects using disposable, explicitly injured fixtures."""
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import pygame
from test_item_gameplay import ItemGameplayTests
from test_mill_battle_gameplay import key

OUT = ROOT/'docs/reviews/consumables'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fixture = ItemGameplayTests();fixture.setUp()
    game = fixture.game
    evidence = {'fixtures': [
        'Disposable completed-Mill setup; no user save/settings paths.',
        'Caelan starts at 40 HP / 0 MP; Mira is later set KO to demonstrate revival.',
        'Real authored cave encounter, shortened travel and ready ATB; no edited enemy HP/outcomes.',
        'Keyboard/mouse item commands and production effects; no complete-victory claim.'], 'captures': {}}

    def capture(name):
        game.draw();path = OUT/(name+'.png');pygame.image.save(game.window, path)
        evidence['captures'][name] = {
            'text_scale': game.audio.text_scale,
            'inventory': game.inventory.to_dict()['items'],
            'battle_resources': ({member.identifier: {'hp': member.hp, 'mp': member.mp}
                                  for member in game.combat.model.party} if game.combat.active else None)}

    try:
        game.inventory_ui.open();game.inventory_ui.category_index = 2
        game.inventory_ui.selected = 'potion';key(game, pygame.K_RETURN)
        capture('field_recipient_100')
        game.audio.set_text_scale(1.5);capture('field_recipient_150')
        key(game, pygame.K_ESCAPE);key(game, pygame.K_ESCAPE)
        game.audio.set_text_scale(1.)
        fixture.cave();fixture.ready()
        fixture.click_command('items');capture('battle_items_100')
        game.audio.set_text_scale(1.5);capture('battle_items_150')
        fixture.click_command('item:potion');capture('battle_recipient_150')
        fixture.click_command('ally:player');game.update(.5, (0, 0), False)
        capture('potion_impact_150');game.update(.5, (0, 0), False)
        game.combat.model.combatant('mira').hp = 0;game.combat.model._sync_party_activity()
        fixture.ready();fixture.click_command('items');fixture.click_command('item:revival_salts')
        fixture.click_command('ally:mira');game.update(.5, (0, 0), False)
        capture('revival_impact_150');game.update(.5, (0, 0), False)
        fixture.ready();fixture.click_command('items');fixture.click_command('item:smoke_bomb')
        game.update(.5, (0, 0), False);capture('smoke_impact_150')
        (OUT/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    finally:
        game.elemental_bosses.stop_audio();game.combat.stop_audio();game.music.stop()
        fixture.doCleanups()
    print('Captured '+str(len(evidence['captures']))+' production consumable views')


if __name__ == '__main__':main()
