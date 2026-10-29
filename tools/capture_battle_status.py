"""Capture the real battle HUD and explicit resource display fixtures.

Uses disposable journeys. Pillow only crops/assembles rendered game frames.
Resource overrides illustrate warning colors and maximum-width numbers; they
do not change saved attributes, combat balance or the player's ordinary files.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.capture_combat import fixture
import pygame
from PIL import Image


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'work/battle-status')
    output = parser.parse_args(argv).output
    output.mkdir(parents=True, exist_ok=True)
    captures, panels = [], []

    def capture(game, filename):
        game.draw()
        pygame.image.save(game.window, str(output/filename))
        member = game.combat.model.player
        captures.append({'file': filename, 'window': list(game.window.get_size()),
                         'text_scale': game.audio.text_scale,
                         'hp': member.hp, 'max_hp': member.max_hp,
                         'mp': member.mp, 'max_mp': member.max_mp})

    with fixture() as game:
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 24))
        game.player.facing = 'back'
        game.camera.reset()
        for kind in (pygame.KEYDOWN, pygame.KEYUP):
            pygame.event.post(pygame.event.Event(kind, key=pygame.K_e, repeat=False))
        assert game.handle_events() and game.combat.active
        before = game.attributes.to_dict()
        game.update(6.25, (0, 0), False)
        scene, model = game.combat.scene, game.combat.model
        assert model.waiting_for_player
        capture(game, 'battle_ready.png')
        for hp, mp in ((140, 30), (70, 15), (35, 0)):
            model.player.hp, model.player.mp = hp, mp
            game.draw()
            image = Image.frombytes('RGB', game.ui_surface.get_size(),
                                    pygame.image.tobytes(game.ui_surface, 'RGB'))
            rect = scene.panel_rect
            panels.append(image.crop((rect.left*2, rect.top*2, rect.right*2, rect.bottom*2)))
        sheet = Image.new('RGB', (panels[0].width, sum(panel.height for panel in panels)))
        y = 0
        for panel in panels:
            sheet.paste(panel, (0, y)); y += panel.height
        sheet.save(output/'health_states.png')
        model.player.hp, model.player.mp = 140, 30
        game.windowed_size = (480, 320)
        game.window = pygame.display.set_mode((480, 320), pygame.RESIZABLE)
        game.audio.set_text_scale(1.5)
        capture(game, 'minimum_window_large_text.png')
        model.player.attributes['hp'], model.player.attributes['mp'] = 9999, 999
        model.player.hp, model.player.mp = 9999, 999
        capture(game, 'maximum_resources_large_text.png')
        assert game.attributes.to_dict() == before
    metadata = {'isolated_temporary_journey': True,
                'normal_journey_and_settings_untouched': True,
                'resource_values_are_display_fixtures': True,
                'health_states': [{'hp': 140, 'mp': 30, 'color': 'green'},
                                  {'hp': 70, 'mp': 15, 'color': 'yellow'},
                                  {'hp': 35, 'mp': 0, 'color': 'red'}],
                'captures': captures}
    (output/'status_verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps({'output': str(output), 'captures': len(captures), 'health_states': 3}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
