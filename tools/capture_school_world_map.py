"""Capture the real classroom map interaction and display-resolution viewer."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame

from main import Game
from npc_routines import find_path


def capture(output_dir=None):
    out = Path(output_dir).resolve() if output_dir is not None else ROOT/'docs/reviews/school_world_map'
    out.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix='school-world-map-')
    game = Game(window_size=(1440, 960), fullscreen=False, start_on_title=False,
                save_path=Path(temporary.name)/'journey.json',
                settings_path=Path(temporary.name)/'settings.json')
    try:
        game.audio.effects_volume = 0
        game.world = game._scene_by_id('school')
        display = game.world.data['world_map_display']
        path = find_path(game.world, game.world.data['spawn'], display['position'],
                         game.world.probe_size, None)
        assert path is not None
        game.player.position.update(display['position'])
        game.player.facing = 'back'
        game.camera.reset()
        game.location_seconds = 0
        game.draw()
        pygame.image.save(game.window, out/'classroom.png')
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, repeat=False))
        assert game.handle_events() and game.world_map_viewer.is_open
        game.draw()
        pygame.image.save(game.window, out/'world_map_fit.png')
        game.world_map_viewer.zoom_at(game.world_map_viewer.viewport.center, 5)
        region = json.loads((ROOT/'assets/maps/overworld/elden_vale/region.json').read_text())
        settlement = next(anchor for anchor in region['geography']['anchors']
                          if anchor['id'] == 'eldenmere')
        game.world_map_viewer.center.update(settlement['atlas_pixel'])
        game.world_map_viewer._clamp()
        game.draw()
        pygame.image.save(game.window, out/'world_map_detail.png')
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
        assert game.handle_events() and not game.world_map_viewer.is_open
        assert not game.pause.is_open
        report = {'actual_renderer': True, 'scene': game.world.data['id'],
                  'approach': display['position'], 'reachable_from_door': True,
                  'opened_with_e': True, 'closed_with_escape': True,
                  'image_size': list(game.world_map_viewer.image.get_size()),
                  'world_map_sha256': hashlib.sha256(game.world_map_viewer.image_path.read_bytes()).hexdigest(),
                  'detail_settlement': settlement['id'],
                  'detail_atlas_pixel': settlement['atlas_pixel'],
                  'captures': ['classroom.png', 'world_map_fit.png', 'world_map_detail.png']}
        (out/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))
    finally:
        pygame.quit()
        temporary.cleanup()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path,
                        help='Write a new review without replacing historical captures')
    args = parser.parse_args()
    capture(args.output_dir)
