"""Temporary, non-story scene data for shared cinematic contract tests."""
import json
from pathlib import Path

import pygame


def write_scene(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    def image(filename, size, color):
        path = directory/filename
        path.parent.mkdir(parents=True, exist_ok=True)
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill(color)
        pygame.image.save(surface, path)

    image('background.png', (960, 480), '#192a40')
    actors, acting = [], {}
    for index, name in enumerate(('caelan', 'mira')):
        folder = directory/name
        for pose, color in (('stand', '#d8c49b'), ('step', '#b49b75'),
                            ('sit', '#b89b5d'), ('transition', '#875755')):
            image(f'{name}/{pose}.png', (24, 36), color)
        manifest = {'canvas': [24, 36], 'anchor': [12, 34],
                    'poses': {'stand': 'stand.png', 'sit': 'sit.png'},
                    'loops': {'stand': [{'file': 'stand.png', 'duration_ms': 200},
                                        {'file': 'step.png', 'duration_ms': 200}]},
                    'transitions': {'stand:sit': [
                        {'file': 'transition.png', 'duration_ms': 300}]}}
        (folder/'animation.json').write_text(json.dumps(manifest))
        actors.append({'id': name, 'manifest': f'{name}/animation.json',
                       'position': [260+index*60, 230]})
        acting[name] = [{'start': 0., 'pose': 'stand'},
                        {'start': 12., 'pose': 'sit'}]
    paragraph = (
        'This temporary passage exercises automatic pagination at several display '
        'sizes. Every word must remain readable, including the final page. The '
        'player advances the presentation clock while the shared portrait panel '
        'keeps its size steady. Pausing must preserve both the current words and '
        'their reading time. Resizing the display changes the layout without '
        'advancing the scene. No line in this fixture establishes game dialogue '
        'or a story event. The final sentence must remain visible for a useful '
        'interval before the passage ends.'
    )
    data = {'version': 1, 'id': 'cinematic_contract_fixture', 'duration': 60.,
            'canvas': [960, 480], 'viewport': [480, 320],
            'camera_bounds': [0, 0, 480, 160],
            'layers': [{'file': 'background.png'}],
            'actors': actors, 'acting': acting, 'dynamic_props': {},
            'shots': [
                {'id': 'establish', 'start': 0., 'end': 2.,
                 'from': [0, 0], 'to': [0, 0]},
                {'id': 'reveal', 'start': 2., 'end': 6.,
                 'from': [0, 0], 'to': [120, 60]},
                {'id': 'conversation', 'start': 6., 'end': 60.,
                 'from': [120, 60], 'to': [120, 60]}],
            'dialogue': [
                {'id': 'greeting', 'speaker': 'Caelan', 'start': 6., 'end': 12.,
                 'text': 'A short fixture passage checks the shared portrait panel.'},
                {'id': 'long_passage', 'speaker': 'Mira', 'start': 14., 'end': 52.,
                 'text': paragraph}]}
    path = directory/'scene.json'
    path.write_text(json.dumps(data))
    return path
