"""Capture Characters, attribute icons and real hover tooltips."""
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from main import Game


def main():
    output = ROOT/'work/characters-menu'
    output.mkdir(parents=True, exist_ok=True)
    game = Game(fullscreen=False, start_on_title=False)
    game.audio.set_music(0)
    game.audio.set_effects(0)
    def key(value):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=value, repeat=False))
        pygame.event.post(pygame.event.Event(pygame.KEYUP, key=value, repeat=False))
        assert game.handle_events()

    key(pygame.K_ESCAPE);key(pygame.K_DOWN);key(pygame.K_RETURN)
    assert game.pause.options[game.pause.selected] == 'Characters'
    assert game.status_ui.is_open
    verification = []
    cases = [('characters_normal', (960, 640), 1.0, None),
             ('characters_hover_spr', (960, 640), 1.0, 'spr'),
             ('characters_hover_mag', (960, 640), 1.0, 'mag'),
             ('characters_hover_hp', (960, 640), 1.0, 'hp'),
             ('characters_hover_spr_large', (960, 640), 1.5, 'spr'),
             ('characters_hover_lck_large', (960, 640), 1.5, 'lck'),
             ('characters_hover_mp_small_large', (480, 320), 1.5, 'mp')]
    for name, size, text_scale, identifier in cases:
        game.window = pygame.display.set_mode(size)
        game.audio.set_text_scale(text_scale)
        game.draw()
        logical = game.status_ui.icon_rects[identifier].center if identifier else (15, 290)
        scale = max(1, min(size[0]//480, size[1]//320))
        point = ((size[0]-480*scale)//2+logical[0]*scale,
                 (size[1]-320*scale)//2+logical[1]*scale)
        pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=point, rel=(0, 0), buttons=(0, 0, 0)))
        assert game.handle_events()
        game.draw()
        tooltip = game.status_ui.tooltip_layout()
        assert (tooltip['attribute'] if tooltip else None) == identifier
        pygame.image.save(game.window, str(output/(name+'.png')))
        verification.append({'capture': name, 'window': size, 'text_scale': text_scale,
                             'hovered': identifier,
                             'tooltip_rect': list(tooltip['rect']) if tooltip else None,
                             'tooltip_text': ' '.join(tooltip['lines']) if tooltip else None})
    game.window = pygame.display.set_mode((960, 640))
    key(pygame.K_ESCAPE)
    assert game.pause.is_open and game.pause.overlay is None
    game.draw();pygame.image.save(game.window, str(output/'characters_pause_large.png'))
    (output/'verification.json').write_text(json.dumps({'attributes': game.attributes.to_dict(),
                                                       'captures': verification}, indent=2)+'\n')
    pygame.quit()
    print(output)


if __name__ == '__main__':main()
