"""Review the actual gate approach, stop and greeting through a disposable Gallery.

Only the initial shot is stationed. Every subsequent pose, cue, root position and
phase transition is selected by production updates; this is not an action-player
simulation or a fully played quest.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT/'docs/reviews/iselin_walk_stop'
CROP = (240, 170, 720, 590)
KEYS = ((.8, 'walking'), (1.24, 'handoff_before'), (1.25, 'handoff'),
        (1.29, 'contact'), (1.41, 'weight'), (1.53, 'closing'),
        (1.65, 'settle'), (1.75, 'root_stopped'), (1.83, 'idle_recovery'),
        (1.95, 'greeting_start'), (2.35, 'greeting'), (2.75, 'long_hold'))


def digest(path):return sha256(Path(path).read_bytes()).hexdigest()


def font(repository, size):
    from PIL import ImageFont
    return ImageFont.truetype(str(repository/'assets/ui/fonts/AtkinsonHyperlegible-Regular.ttf'), size)


def check_preservation():
    baseline = json.loads((REVIEW/'preservation_baseline.json').read_text())
    for name, value in baseline['sha256'].items():
        if not (ROOT/name).is_file() or digest(ROOT/name) != value:
            raise ValueError('Historical stop review preservation failed: '+name)
    return {'base_commit': baseline['base_commit'], 'count': len(baseline['sha256']),
            'all_unchanged': True}


class Review:
    def __init__(self, repository, directory):
        sys.path.insert(0, str(repository))
        import pygame
        from main import Game
        self.repository = repository
        self.pygame = pygame
        self.parent = Game(window_size=(960, 640), fullscreen=False, start_on_title=True,
                           save_path=Path(directory)/'journey.json',
                           settings_path=Path(directory)/'settings.json')
        self.parent.audio.set_music(0);self.parent.audio.set_effects(0)
        if not self.parent.open_gallery() or not self.parent.launch_gallery_scene('regent_arrival'):
            raise ValueError('Arrival Gallery could not start')
        self.session = self.parent.gallery_session
        self.child = self.session.game
        self.scene = self.child.regent_arrival
        self.parent.draw()
        self.station()

    def station(self):
        # The sole manufactured staging: begin the existing approach shot.
        self.scene.clear_actor_actions()
        self.scene.phase_index = next(i for i, p in enumerate(self.scene.data['phases'])
                                      if p['id'] == 'gate_approach')
        self.scene.phase_time = self.scene.elapsed = 0.
        self.scene.dialogue_index = self.scene.page_index = 0
        self.scene.active = True;self.scene.paused = False;self.scene.focused = True
        self.child._music_focused = True
        self.elapsed = 0.

    def advance(self, seconds):
        self.child.update(seconds, (0, 0), False)
        self.elapsed += seconds

    def actor(self):
        return next(a for a in self.scene.phase['actors'] if a['id'] == 'iselin')

    def state(self):
        actor = self.actor()
        frame = self.scene._frame(actor)
        return {'elapsed': round(self.elapsed, 9), 'shot': self.scene.shot,
                'shot_seconds': round(self.scene.phase_time, 9),
                'root': list(self.scene.actor_position(actor)),
                'camera': list(self.scene.camera_position),
                'action': self.scene.actor_action_state('iselin'),
                'rendered_frame_rgba_sha256': sha256(self.pygame.image.tobytes(frame, 'RGBA')).hexdigest(),
                'audio_mode': self.scene._audio_mode()}

    def image(self):
        from PIL import Image
        self.parent.draw()
        return Image.frombytes('RGB', self.parent.window.get_size(),
                               self.pygame.image.tobytes(self.parent.window, 'RGB'))

    def labelled(self, image, state, classification):
        from PIL import Image, ImageDraw
        crop = image.crop(CROP)
        result = Image.new('RGB', (crop.width, crop.height+56), '#e8edf2')
        result.paste(crop, (0, 56))
        draw = ImageDraw.Draw(result)
        draw.text((10, 5), classification, font=font(self.repository, 15), fill='#263c35')
        draw.text((10, 29), f't={state["elapsed"]:.2f}s / {state["shot"]} / {state["action"]["stage"]}',
                  font=font(self.repository, 14), fill='#263c35')
        return result

    def close(self):
        self.session.close()
        self.parent.opening_audio.reset();self.parent.regional_audio.reset()
        self.parent.music.stop();self.pygame.quit()


def write_gif(path, frames, exposure):
    from PIL import Image
    palette = frames[0].quantize(colors=256)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    durations = [exposure]*len(indexed)
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=durations,
                    loop=0, disposal=1, optimize=False)
    with Image.open(path) as image:
        if image.n_frames != len(indexed):raise ValueError('GIF changed sampled frame count')
        total = 0
        for index, expected in enumerate(indexed):
            image.seek(index)
            if image.info['duration'] != exposure:raise ValueError('GIF changed sampled exposure')
            if image.convert('RGB').tobytes() != expected.convert('RGB').tobytes():
                raise ValueError('GIF changed quantized sampled pixels')
            total += image.info['duration']
    return {'frames': len(indexed), 'total_ms': total, 'exposure_ms': exposure,
            'disposal': 1, 'decoded_pixels_and_exposures_verified': True}


def frame_board(repository, output):
    """Show the actual manifest's complete gate drawings on one fixed grid."""
    from PIL import Image, ImageDraw
    folder = repository/'assets/story/regent_arrival/actors/iselin'
    manifest = json.loads((folder/'animation.json').read_text())
    loop = 'gate_walk_left' if 'gate_walk_left' in manifest['loops'] else 'walk_left'
    idle = 'gate_stand_left' if 'gate_stand_left' in manifest['poses'] else 'stand_left'
    clip = manifest.get('actions', {}).get('stop_left')
    if clip is None:return None
    paths = [(folder/frame['file'], f'Walk {index+1:02}')
             for index, frame in enumerate(manifest['loops'][loop])]
    paths.extend((folder/frame['file'], f'Stop {index:02}')
                 for index, frame in enumerate(clip['entry'][1:], 1))
    paths.append((folder/manifest['poses'][idle], 'Standing idle'))
    board = Image.new('RGB', (900, 54+math.ceil(len(paths)/5)*236), '#e8edf2')
    draw = ImageDraw.Draw(board)
    draw.text((12, 8), 'ISELIN GATE / production 80x96 drawings at 2x / fixed registration',
              font=font(repository, 18), fill='#263c35')
    refs = []
    for index, (path, name) in enumerate(paths):
        image = Image.open(path).convert('RGBA')
        if image.size != (80, 96):raise ValueError('Unexpected cinematic frame canvas')
        large = image.resize((160, 192), Image.Resampling.NEAREST)
        x = 10+(index % 5)*180;y = 48+(index//5)*236
        board.paste(large, (x, y), large)
        draw.text((x, y+198), name, font=font(repository, 15), fill='#263c35')
        refs.append({'path': str(path.relative_to(repository)), 'sha256': digest(path),
                     'rgba_sha256': sha256(image.tobytes()).hexdigest()})
    board.save(output/'numbered_frames.png')
    return refs


def contact_board(repository, output, records, sprites):
    """Inspect actual selected surfaces at their world roots, without the pan.

    This is a diagnostic composition, not a screenshot or a new animation.
    Registration is fixed for the whole board; no foot is aligned per frame.
    """
    from PIL import Image, ImageDraw
    selected = ('handoff_before.png', 'contact.png', 'weight.png', 'closing.png',
                'settle.png', 'root_stopped.png', 'idle_recovery.png', 'greeting_start.png')
    board = Image.new('RGB', (1200, 790), '#e8edf2');draw = ImageDraw.Draw(board)
    draw.text((12, 8), 'WORLD REGISTRATION DIAGNOSTIC / actual selected art + actual root / no camera pan',
              font=font(repository, 18), fill='#263c35')
    draw.text((12, 34), 'Fixed world origin535,375; pale reference x565; full drawings remain intact. Inspection3x.',
              font=font(repository, 16), fill='#263c35')
    values = []
    for i, name in enumerate(selected):
        record = next(item for item in records if item['file'] == name)
        cell = Image.new('RGB', (100, 110), '#e8edf2');guide = ImageDraw.Draw(cell)
        guide.line((0, 100, 99, 100), fill='#b9c9c4')
        guide.line((30, 0, 30, 105), fill='#cbd7d3')
        origin = (round(record['root'][0]-535-40), round(record['root'][1]-375+100-92))
        image = sprites[name]
        cell.paste(image, origin, image)
        x = (i % 4)*300;y = 70+(i//4)*360
        board.paste(cell.resize((300, 330), Image.Resampling.NEAREST), (x, y))
        draw.text((x+10, y+334), f'{record["elapsed"]:.2f}s / rootx={record["root"][0]:.3f}',
                  font=font(repository, 14), fill='#263c35')
        values.append({'sample': name, 'world_root': record['root'],
                       'canvas_origin': list(origin), 'frame_sha256': record['rendered_frame_rgba_sha256']})
    board.save(output/'world_contact_board.png')
    return {'classification': 'Diagnostic composition of actual selected whole surfaces at fixed world registration, not a production screenshot.',
            'world_origin': [535, 375], 'camera_pan_removed': True,
            'common_canvas': [100, 110], 'common_ground_y': 100,
            'common_actor_anchor': [40, 92], 'inspection_scale': 3, 'samples': values}


def mechanics(review):
    scene = review.scene;pygame = review.pygame
    checks = {}
    review.station();review.advance(1.35)
    actor = review.actor()
    before = review.state()
    scene.paused = True;review.child.update(.5, (0, 0), False)
    checks['pause_freezes_action_root_camera'] = review.state() == before
    scene.paused = False
    scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    review.child.update(.5, (0, 0), False)
    checks['focus_freezes_action_root_camera'] = review.state() == before
    scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
    review.image();review.image()
    checks['draw_is_pure'] = review.state() == before
    state = scene.actor_action_state('iselin')
    if state['action'] == 'stop_left':
        checks['duplicate_cue_ignored'] = not scene.play_actor_action('iselin', 'stop_left', state['cue_id'])
        checks['duplicate_does_not_reset'] = review.state() == before
    review.advance(.6)
    checks['greeting_clears_action'] = scene.shot == 'gate_greeting' and scene.actor_action_state('iselin')['stage'] == 'idle'
    old = scene.actor_action_state('iselin')
    review.advance(2.)
    checks['long_read_does_not_replay_stop'] = scene.actor_action_state('iselin') == old
    review.station();review.advance(1.35)
    before_facts = (review.child.inventory.to_dict(), review.child.quests.to_dict())
    scene.finish('skipped')
    checks['skip_clears_action_without_rewards'] = (
        scene.actor_action_state('iselin')['stage'] == 'idle' and
        (review.child.inventory.to_dict(), review.child.quests.to_dict()) == before_facts)
    review.station();review.advance(1.35)
    checks['same_cue_restarts_after_clear'] = scene.actor_action_state('iselin')['stage'] != 'idle'
    review.session.close()
    checks['gallery_close_clears_child'] = scene.actor_action_state('iselin')['stage'] == 'idle'
    if not all(checks.values()):raise ValueError('Stop mechanic check failed: '+str(checks))
    return checks


def live_bank_evidence(review):
    """Check production-loaded surfaces against the frozen approval snapshot."""
    from PIL import Image
    repository = review.repository
    approval_path = repository/'assets/source/characters/iselin/cinematic_gate_left/approval.json'
    if not approval_path.exists():return None
    approval = json.loads(approval_path.read_text())
    art = review.scene.actor_art['iselin']
    if art['canvas'] != [80, 96] or art['anchor'] != [40, 92]:
        raise ValueError('Live gate registration differs from approval')
    surfaces = {f'gate_walk_left/frame_{index+1:02}.png': surface
                for index, (surface, _) in enumerate(art['loops']['gate_walk_left'])}
    surfaces.update({f'stop_left/frame_{index:02}.png': frame.image
                     for index, frame in enumerate(art['actions']['stop_left'].entry[1:], 1)})
    surfaces['gate_stand_left.png'] = art['poses']['gate_stand_left']
    if len(surfaces) != 25 or len(approval['files']) != 25:
        raise ValueError('Live gate must load the 25 approved complete drawings')
    values = {}
    for relative, surface in surfaces.items():
        name = 'assets/story/regent_arrival/actors/iselin/'+relative
        expected = approval['files'][name]
        rgba_hash = sha256(review.pygame.image.tobytes(surface, 'RGBA')).hexdigest()
        if (digest(repository/name) != expected['approved_file_sha256']
                or rgba_hash != expected['approved_rgba_sha256']):
            raise ValueError('Production gate image differs from approval: '+name)
        values[name] = {'approved_file_sha256': expected['approved_file_sha256'],
                        'loaded_rgba_sha256': rgba_hash}
    baseline_path = repository/'docs/reviews/iselin_native_integration/approved_assets.json'
    baseline = json.loads(baseline_path.read_text())
    if len(baseline['sha256']) != 69:raise ValueError('Expected the 69-image ordinary approval baseline')
    for name, value in baseline['sha256'].items():
        if digest(repository/name) != value:raise ValueError('Approved ordinary image changed: '+name)
    return {'source': 'Ordinary RegentArrival._load from the live production manifest; no bank or pose overrides.',
            'approval_snapshot': str(approval_path.relative_to(repository)),
            'approval_snapshot_sha256': digest(approval_path),
            'approved_cinematic_png_count': len(values), 'loaded_surfaces': values,
            'approved_ordinary_portrait_png_count': len(baseline['sha256']),
            'all_approved_ordinary_portrait_pngs_unchanged': True}


def compare_approved_capture(path, observations):
    """Compare selected images and staging with the user-approved timed review."""
    if path is None:return None
    original = json.loads(path.read_text())
    previous = {sample['elapsed']: sample for sample in original['timeline_samples']}
    checked = []
    for sample in observations:
        expected = previous[sample['elapsed']]
        for key in ('shot', 'root', 'camera', 'rendered_frame_rgba_sha256'):
            if sample[key] != expected[key]:
                raise ValueError(f'Live capture differs from approved preview at {sample["elapsed"]}: {key}')
        checked.append({'elapsed': sample['elapsed'],
                        'approved_rendered_frame_rgba_sha256': expected['rendered_frame_rgba_sha256']})
    if len(checked) != len(previous):raise ValueError('Approved preview sample count changed')
    return {'reference_name': path.name, 'reference_sha256': digest(path),
            'all_approved_timed_images_roots_and_cameras_match': True,
            'sample_count': len(checked), 'samples': checked}


def capture(args):
    from PIL import Image, ImageDraw
    args.out.mkdir(parents=True, exist_ok=True)
    proof = check_preservation() if args.check_preservation else None
    repository = args.repository.resolve()
    frames = [];observations = [];stills = [];sprites = {}
    # Split at the declared contact/timing samples as well as 50fps boundaries.
    # This uses ordinary production delta updates, never direct clock selection.
    frame_times = [round(.8+i*.02, 9) for i in range(101)]
    key_names = {time: name for time, name in KEYS}
    times = sorted(set([*frame_times, *key_names]))
    with tempfile.TemporaryDirectory(prefix='iselin-walk-stop-') as directory:
        review = Review(repository, directory)
        try:
            live_bank = live_bank_evidence(review)
            for seconds in times:
                remaining = seconds-review.elapsed
                while remaining > .02+1e-10:
                    review.advance(.02);remaining = seconds-review.elapsed
                if remaining > 1e-10:review.advance(remaining)
                state = review.state();image = review.image()
                if seconds in frame_times:
                    frames.append(review.labelled(image, state, args.classification))
                    observations.append(state)
                if seconds in key_names:
                    name = key_names[seconds]+'.png';image.save(args.out/name)
                    stills.append({'file': name, **state})
                    sprite = review.scene._frame(review.actor())
                    sprites[name] = Image.frombytes('RGBA', sprite.get_size(),
                        review.pygame.image.tobytes(sprite, 'RGBA'))
            gifs = {'normal.gif': write_gif(args.out/'normal.gif', frames, 20),
                    'slow.gif': write_gif(args.out/'slow.gif', frames, 80)}
            checks = mechanics(review) if args.check_mechanics else {}
        finally:review.close()
    approved_comparison = compare_approved_capture(args.approved_capture, observations)
    board = Image.new('RGB', (960, math.ceil(len(stills)/3)*260), '#e8edf2')
    draw = ImageDraw.Draw(board)
    for i, record in enumerate(stills):
        image = Image.open(args.out/record['file']).convert('RGB')
        image = image.resize((320, 213), Image.Resampling.NEAREST)
        x = (i % 3)*320;y = (i//3)*260;board.paste(image, (x, y))
        draw.text((x+8, y+219), f'{record["elapsed"]:.2f}s / {record["action"]["stage"]}',
                  font=font(repository, 15), fill='#263c35')
    board.save(args.out/'samples.png')
    references = frame_board(repository, args.out)
    contacts = contact_board(repository, args.out, stills, sprites)
    if args.check_preservation:proof = check_preservation()
    dependencies = ['regent_arrival.py', 'cinematic_actor_actions.py',
                    'tools/build_regent_iselin.py',
                    'docs/reviews/iselin_native_integration/approved_assets.json',
                    'assets/story/regent_arrival/scene.json',
                    'assets/story/regent_arrival/actors/iselin/animation.json']
    if (repository/'tools/export_iselin_gate_detail.py').is_file():
        dependencies.append('tools/export_iselin_gate_detail.py')
    for name in ('approval.json', 'recipe.json', 'registration.json'):
        candidate = 'assets/source/characters/iselin/cinematic_gate_left/'+name
        if (repository/candidate).is_file():dependencies.append(candidate)
    dependencies.extend(reference['path'] for reference in (references or []))
    report = {'repository_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'],
               cwd=repository, text=True).strip(), 'classification': args.classification,
              'working_tree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain=v1'],
                                          cwd=repository, text=True)),
              'capture_helper_sha256': digest(Path(__file__)),
              'fixture': 'Initial gate_approach shot stationed at0; then continuous production Game.update and Game.draw through real Gallery. No pose/action/frame overrides.',
              'dt': '.02s maximum, split at listed exact meaningful times',
              'gif_crop_window_pixels': list(CROP), 'gif_playback': gifs,
              'timeline_samples': observations, 'meaningful_samples': stills,
              'mechanic_checks': checks, 'production_frame_references': references,
              'live_bank_approval': live_bank, 'approved_preview_comparison': approved_comparison,
              'world_registration_diagnostic': contacts,
              'preservation': proof, 'input_sha256': {name: digest(repository/name) for name in dependencies},
              'output_sha256': {path.name: digest(path) for path in sorted(args.out.iterdir())
                                if path.suffix in ('.png', '.gif') and not path.name.startswith('before')}}
    (args.out/'capture.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Walk-stop capture complete:', args.out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=ROOT,
                        help='Read another checkout for a labelled historical comparison')
    parser.add_argument('--out', type=Path, default=Path(tempfile.gettempdir())/'iselin-walk-stop')
    parser.add_argument('--classification', default='ACTUAL ARRIVAL / WALK TO STOP TO GREETING')
    parser.add_argument('--approved-capture', type=Path,
                        help='Compare every selected image/root/camera with the approved timed review JSON')
    parser.add_argument('--check-preservation', action='store_true',
                        help='Explicitly verify this review historical art baseline')
    parser.add_argument('--check-mechanics', action='store_true')
    args = parser.parse_args()
    os.environ['SDL_VIDEODRIVER'] = 'dummy';os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
    capture(args)


if __name__ == '__main__':main()
