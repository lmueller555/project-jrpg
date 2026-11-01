"""Record production checkpoint/participation at 30 Hz and 15 fps.

Only completed predecessor quests and initial player stations are fixtures.
Every route, contact, dialogue acknowledgment, optional response and return uses
Game.update and the production controllers. Site changes are separate labelled
clips. Regional effects use capture_regional_audio.Recorder's accepted-source
PCM/gain stream; this is offline rendering, not a recording of a live device.
Music is muted. No normalization, playback acceleration or replacement art.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pygame
from main import Game
from checkpoint_charm import WITNESS, HOMES, valid_state as valid_checkpoint
from regional_participation import STAND_POSITION, CAT_SCRIPT, MASONRY_SCRIPT
from tools.capture_lantern_quest import seed_previous_quests
from tools import capture_regional_audio as audio_capture

OUT = ROOT/'docs/reviews/checkpoint_charm'
ARCHIVE = Path(os.environ.get('CHECKPOINT_FRAME_ARCHIVE', '/tmp/checkpoint-evidence'))


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):return None
    if isinstance(value, dict):return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):return [clean(v) for v in value]
    return value


def write_json(path, value):
    path.write_text(json.dumps(clean(value), indent=2, allow_nan=False)+'\n')


def source_hashes():
    paths = [ROOT/name for name in ('main.py', 'overworld_world.py', 'overworld_travel.py',
        'checkpoint_charm.py', 'regional_participation.py', 'purposeful_wildlife.py',
        'bridge_crew.py', 'regional_audio.py', 'social.py', 'save_game.py',
        'tools/capture_checkpoint_charm.py', 'tools/capture_regional_audio.py',
        'assets/characters/caelan/participation_sit_front.png',
        'assets/maps/overworld/elden_vale/region.json')]
    paths += list((ROOT/'assets/characters/checkpoint_charm').rglob('*'))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file()}


def position(game, point):
    assert game.world.can_stand(point), ('Blocked initial capture point', point)
    game.player.position.update(point)
    game.camera.reset()


def make_game(root, name, point):
    folder = root/name
    folder.mkdir()
    game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                save_path=folder/'journey.json', settings_path=folder/'settings.json')
    game.audio.set_music(0)
    game.audio.set_effects(1)
    seed_previous_quests(game)
    game.world = game.overworld_world
    game.opening_fade = game.transfer_cooldown = game.location_seconds = 0
    position(game, point)
    return game


class Recorder(audio_capture.Recorder):
    def __init__(self, game, name):
        game.regional_audio.stop()
        audio_capture.OUT = OUT
        self.name = name
        self.trace = []
        self.inputs = []
        self.checks = {}
        self.frame_hashes = []
        self.stills = []
        self.last_state = None
        self.source_sha256 = source_hashes()
        assert game.canvas.get_size() == (480, 320)
        assert game.window.get_size() == (960, 640)
        super().__init__(game)
        self.native_process = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error',
            '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', '480x320',
            '-framerate', '15', '-i', '-', '-an', '-c:v', 'libx264rgb', '-crf', '0',
            '-preset', 'fast', str(ARCHIVE/(name+'_native_frames.mkv'))], stdin=subprocess.PIPE)

    def event(self, action, key, **data):
        if action == 'start':
            source = self.g.regional_audio.voices[key][0]
            data.update(source=list(source.point()), listener=list(self.g.player.position),
                distance=self.g.player.position.distance_to(source.point()),
                family=source.family, priority=source.priority, source_gain=source.gain,
                near=source.near, far=source.far, cooldown=source.cooldown)
        super().event(action, key, **data)

    def state(self):
        game = self.g
        world = game.overworld_world
        page = game.social.page
        cat = world.wildlife.by_id['farm_cat']
        return {'time': self.count/30, 'title': game.on_title, 'pause': game.pause.is_open,
            'listener': list(game.player.position), 'facing': game.player.facing,
            'player_story_pose': getattr(game.player, 'story_sprite', None) is not None,
            'player_can_stand': game.world.can_stand(game.player.position),
            'hint': game.overworld_travel.interaction_hint(),
            'checkpoint': world.checkpoint_charm.to_dict(),
            'participation': world.participation.to_dict(),
            'cat': {'position': list(cat.position), 'pose': cat.pose, 'state': dict(cat.state)},
            'bridge': {'stage': world.bridge_crew.stage, 'state': world.bridge_crew.to_dict()},
            'dialogue': {'id': game.social.script_identifier, 'page': game.social.page_index,
                         'lines': list(page['lines']) if page else None},
            'voices': {k: {'source': list(v[0].point()), 'gain': game.regional_audio._gain(v[0])}
                       for k, v in game.regional_audio.voices.items()}}

    def run(self, seconds, direction=(0, 0)):
        if pygame.Vector2(direction).length_squared():
            self.inputs.append({'time': self.count/30, 'action': 'movement',
                                'seconds': seconds, 'direction': list(direction)})
        for _ in range(round(seconds*30)):
            frame_number = self.count
            super().run(1/30, direction)
            assert self.g.camera._frame_height == 320, 'Normal gameplay zoom required'
            assert valid_checkpoint(self.g.overworld_world.checkpoint_charm.to_dict())
            assert len(self.g.regional_audio.voices) <= 4
            if frame_number % 2 == 0:
                native = pygame.image.tobytes(self.g.canvas, 'RGB')
                display = pygame.image.tobytes(self.g.window, 'RGB')
                self.native_process.stdin.write(native)
                self.frame_hashes.append({'frame': frame_number//2, 'time': frame_number/30,
                    'native_sha256': hashlib.sha256(native).hexdigest(),
                    'display_sha256': hashlib.sha256(display).hexdigest(),
                    'title_frame': self.g.on_title})
            state = self.state()
            signature = (state['title'], state['pause'], state['checkpoint']['stage'],
                state['checkpoint']['read'], state['checkpoint']['contacts'],
                state['participation']['seated'], state['cat']['pose'],
                state['dialogue']['id'], state['dialogue']['page'])
            if self.count % 15 == 0 or signature != self.last_state:self.trace.append(state)
            self.last_state = signature

    def key(self, key, *, repeat=False, count=1):
        self.inputs.append({'time': self.count/30, 'action': 'handle_events',
                            'key': pygame.key.name(key), 'repeat': repeat, 'count': count})
        assert self.g.handle_events([pygame.event.Event(pygame.KEYDOWN,
            key=key, repeat=repeat) for _ in range(count)])

    def still(self, name):
        self.g.draw()
        native = OUT/(name+'_native.png')
        display = OUT/(name+'.png')
        pygame.image.save(self.g.canvas, str(native))
        pygame.image.save(self.g.window, str(display))
        self.stills.append({'time': self.count/30, 'native': native.name, 'display': display.name})

    def walk(self, target, limit=15):
        target = pygame.Vector2(target)
        self.inputs.append({'time': self.count/30, 'action': 'walk_to', 'target': list(target)})
        # Record one route instruction instead of one input entry per frame.
        for _ in range(round(limit*30)):
            delta = target-self.g.player.position
            if delta.length() <= 1.5:return
            before = self.g.player.position.copy()
            self.run(1/30, delta)
            assert self.g.player.position.distance_to(before) > .001, ('Blocked player walk', before, target)
        raise AssertionError(('Player walk timeout', list(self.g.player.position), list(target)))

    def dialogue(self, seconds=2.2):
        while self.g.social.active:
            self.run(seconds)
            self.key(pygame.K_SPACE)
            self.run(1/30)

    def save_continue(self, controller, label):
        before = controller.to_dict()
        feet = list(self.g.player.position)
        assert self.g.save_progress()
        self.mark(label+': exact explicit checkpoint')
        self.still(label+'_before_continue')
        self.inputs.append({'time': self.count/30, 'action': 'title transition',
                            'method': 'on_title=True; production begin_journey(True)'})
        self.g.on_title = True
        self.run(.8)
        assert not self.g.regional_audio.voices
        assert self.g.begin_journey(True)
        after = controller.to_dict()
        self.checks[label+'_continue_exact_state'] = before == after
        self.checks[label+'_continue_exact_feet'] = feet == list(self.g.player.position)
        self.checks[label+'_continue_snapshot'] = {'before': before, 'after': after, 'feet': feet}
        assert before == after and feet == list(self.g.player.position)
        self.mark(label+': Continue restores the same scene action and feet')
        self.still(label+'_after_continue')
        self.run(.8)
        self.still(label+'_after_continue_visible')

    def close(self):
        self.g.regional_audio.observer = self.event
        self.native_process.stdin.close()
        assert self.native_process.wait() == 0
        # Decode the lossless archive and verify every actual native frame.
        archive = ARCHIVE/(self.name+'_native_frames.mkv')
        decoder = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(archive),
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
        for expected in self.frame_hashes:
            frame = decoder.stdout.read(480*320*3)
            assert hashlib.sha256(frame).hexdigest() == expected['native_sha256']
        assert decoder.stdout.read(1) == b'' and decoder.wait() == 0
        with np.errstate(divide='ignore'):super().close()
        (OUT/'regional_audio.mp4').replace(OUT/(self.name+'.mp4'))
        shutil.move(str(OUT/'review.wav'), str(ARCHIVE/(self.name+'.wav')))
        report = json.loads((OUT/'capture_report.json').read_text())
        report.update(method=__doc__, name=self.name, native_size=[480, 320],
            window_size=[960, 640], simulation_hz=30, video_fps=15,
            trace=self.trace, inputs=self.inputs, checks=self.checks, stills=self.stills,
            source_sha256=self.source_sha256, final_state=self.state(),
            lossless_native_frames=str(archive), source_pcm_wav=str(ARCHIVE/(self.name+'.wav')),
            all_native_frames_verified=True)
        write_json(OUT/(self.name+'_frames.json'), self.frame_hashes)
        write_json(OUT/(self.name+'_report.json'), report)
        (OUT/'capture_report.json').unlink()
        self.g.regional_audio.observer = None
        return report


def guard_clip(root):
    game = make_game(root, 'guard', WITNESS)
    controller = game.world.checkpoint_charm
    flags = sorted(game.social.flags)
    recorder = Recorder(game, 'guard_full')
    recorder.mark('North checkpoint: initial witness position; production E starts the finite scene')
    recorder.run(1)
    recorder.still('guard_initial')
    assert game.overworld_travel.interaction_hint() == 'E: Watch the checkpoint'
    recorder.key(pygame.K_e)
    assert controller.stage == 'owner_to_seat'
    recorder.key(pygame.K_e, repeat=True, count=8)
    recorder.key(pygame.K_e, count=3)
    recorder.checks['busy_input_does_not_restart'] = controller.stage == 'owner_to_seat' and controller.state['read'] == 0
    assert recorder.checks['busy_input_does_not_restart']
    recorder.until(lambda: controller.stage == 'owner_sit' and controller.state['elapsed'] >= .2)
    recorder.save_continue(controller, 'guard_seat_action')
    recorder.until(lambda: controller.stage == 'opening' and game.social.active)
    recorder.run(2.2)
    unread = controller.state['read']
    recorder.mark('Walk south to cancel an unread line without acknowledging it')
    recorder.walk((408, -2094))
    recorder.run(1)
    assert not game.social.locked and controller.state['read'] == unread
    recorder.still('guard_cancelled')
    recorder.mark('Return on foot; E resumes the same missing line')
    recorder.walk(WITNESS)
    recorder.run(1)
    assert not game.social.locked
    recorder.key(pygame.K_e)
    assert game.social.active and controller.state['read'] == unread
    recorder.checks['cancel_resumes_unread_line_with_e'] = True
    recorder.still('guard_resumed_line')
    saved_banter = False
    busy_near_guard = False
    deadline = recorder.count+120*30
    while controller.stage != 'done':
        assert recorder.count < deadline, ('Guard completion timeout', controller.to_dict())
        if game.social.active:
            if controller.stage == 'banter' and not saved_banter:
                recorder.mark('Borrower seated; the other guard checks stores while keeping watch')
                recorder.still('guard_banter')
                saved_banter = True
            recorder.run(2.2)
            recorder.key(pygame.K_SPACE)
            recorder.run(1/30)
        elif controller.stage in ('opening', 'banter', 'closing'):
            recorder.key(pygame.K_e)
            recorder.run(1/30)
        else:
            if (controller.stage == 'borrower_out' and not busy_near_guard
                    and min(actor.position.distance_to(game.player.position)
                            for actor in controller.actors.values()) < 50):
                recorder.mark('Repeated E beside the walking guard remains owned by the active scene')
                stage = controller.stage
                recorder.key(pygame.K_e, count=3)
                recorder.key(pygame.K_e, repeat=True, count=8)
                assert controller.stage == stage and not game.social.locked
                recorder.checks['busy_e_near_walking_guard_consumed'] = True
                busy_near_guard = True
            recorder.run(2/30)
    recorder.mark('Complete return: both original guards back at their duty positions')
    recorder.run(2)
    recorder.still('guard_returned')
    assert all(list(actor.position) == list(HOMES[role]) for role, actor in controller.actors.items())
    assert controller.state['read'] == 7 and controller.state['contacts'] == 5
    assert busy_near_guard
    assert sorted(game.social.flags) == flags
    recorder.checks.update(complete_return=True, acknowledged_lines=7, contacts=5,
                           story_flags_unchanged=True)
    recorder.mark('A later E visit uses the quieter two-line repeat')
    recorder.key(pygame.K_e)
    recorder.dialogue()
    recorder.until(lambda: controller.stage == 'done')
    recorder.run(1)
    assert controller.state['read'] == 7 and controller.state['contacts'] == 5
    assert len([e for e in recorder.events if e['action'] == 'start' and e['key'].startswith('checkpoint_contact_')]) == 5
    recorder.checks['five_contacts_once_across_continue_and_repeat'] = True
    return recorder.close()


def bench_clip(root):
    game = make_game(root, 'bench', STAND_POSITION)
    participation = game.world.participation
    recorder = Recorder(game, 'overlook_bench')
    recorder.mark('Site cut: overlook; production E sits on the existing bench')
    recorder.run(1)
    recorder.key(pygame.K_e)
    assert participation.state['seated']
    recorder.run(2)
    recorder.still('overlook_seated')
    recorder.key(pygame.K_e, repeat=True, count=6)
    assert participation.state['seated']
    recorder.mark('Production pause API opens the pause panel while the seat remains owned')
    recorder.inputs.append({'time': recorder.count/30, 'action': 'pause.open production API',
        'reason': 'Escape is the explicit seated stand/cancel affordance'})
    game.pause.open()
    recorder.run(1.2)
    assert participation.state['seated']
    recorder.still('overlook_paused')
    recorder.save_continue(participation, 'overlook_seat')
    assert participation.state['seated'] and not game.pause.is_open
    recorder.mark('E stands at clear canonical feet')
    recorder.key(pygame.K_e)
    assert not participation.state['seated'] and game.world.can_stand(game.player.position)
    recorder.run(1.5)
    recorder.still('overlook_stood_e')
    recorder.key(pygame.K_e)
    recorder.run(1.5)
    recorder.key(pygame.K_ESCAPE, repeat=True, count=3)
    assert participation.state['seated']
    recorder.mark('Escape stands and consumes that input')
    recorder.key(pygame.K_ESCAPE)
    assert not participation.state['seated'] and not game.pause.is_open
    recorder.run(1)
    recorder.key(pygame.K_e)
    recorder.run(1.5)
    recorder.mark('Directional movement releases the seat and walks away')
    recorder.run(.6, (1, 0))
    assert not participation.state['seated'] and game.world.can_stand(game.player.position)
    recorder.walk(STAND_POSITION)
    recorder.key(pygame.K_e)
    recorder.run(1.5)
    recorder.mark('Explicit production cancel releases the pose and retains clear feet')
    recorder.inputs.append({'time': recorder.count/30, 'action': 'participation.cancel production API'})
    assert participation.cancel(game)
    recorder.run(1.5)
    assert getattr(game.player, 'story_sprite', None) is None
    assert game.world.can_stand(game.player.position)
    recorder.still('overlook_cancelled')
    recorder.checks.update(repeat_e_ignored=True, repeat_escape_ignored=True,
        e_stand=True, escape_stand_consumes_input=True, movement_stand=True,
        cancellation_releases_pose=True, final_clear_feet=True)
    return recorder.close()


def cat_clip(root):
    game = make_game(root, 'cat', (-400, 1198))
    participation = game.world.participation
    cat = game.world.wildlife.by_id['farm_cat']
    recorder = Recorder(game, 'farm_cat')
    recorder.mark('Site cut: existing farm cat; E offers a quiet greeting')
    recorder.run(.5)
    assert participation.selected_target(game) == 'cat'
    recorder.key(pygame.K_e)
    assert game.social.script_identifier == CAT_SCRIPT
    recorder.run(1)
    recorder.mark('Walking away cancels before acknowledgment; the cat keeps its own routine')
    recorder.walk((-360, 1198))
    assert not game.social.locked and not participation.state['cat_greeted']
    recorder.still('farm_cat_cancelled')
    recorder.walk((-400, 1198))
    # Wait for the animal's real next resting point; never seed its mode/clock.
    if not participation._cat_available(game):
        recorder.mark('The cat follows its authored stretch, walk and return before another greeting')
        recorder.until(lambda: cat.state['mode'] in ('sleep', 'sit'), limit=60)
        candidates = [(cat.position.x+20, cat.position.y+16),
                      (cat.position.x+20, cat.position.y-16),
                      (cat.position.x-20, cat.position.y+16)]
        point = next(point for point in candidates if game.world.can_stand(point))
        recorder.walk(point)
    assert participation.selected_target(game) == 'cat'
    recorder.key(pygame.K_e)
    assert game.social.script_identifier == CAT_SCRIPT
    recorder.key(pygame.K_e, repeat=True, count=8)
    assert not participation.state['cat_greeted']
    recorder.still('farm_cat_greeting')
    recorder.dialogue()
    assert participation.state['cat_greeted']
    recorder.mark('The existing cat owner supplies the bounded silent acknowledgment')
    recorder.run(.6)
    recorder.still('farm_cat_acknowledged')
    recorder.key(pygame.K_e, repeat=True, count=5)
    recorder.run(3)
    recorder.checks.update(cancel_has_no_contact=True, greeted_through_e_and_dialogue=True,
        cat_owned_by_wildlife=True, acknowledgment_intentionally_silent=True,
        no_manufactured_cat_state=True)
    return recorder.close()


def masonry_clip(root):
    game = make_game(root, 'masonry', (-2420, 642))
    crew = game.world.bridge_crew
    recorder = Recorder(game, 'unfinished_masonry')
    recorder.mark('Site cut: unfinished bridge; workers sort blocks through real production updates')
    recorder.until(lambda: crew.state['sorted'] >= 1, limit=60)
    recorder.still('masonry_worker_progress')
    assert game.world.participation.selected_target(game) == 'masonry'
    recorder.mark('E inspects the existing unfinished masonry without starting tea or changing the crossing')
    recorder.key(pygame.K_e)
    assert game.social.script_identifier == MASONRY_SCRIPT
    recorder.key(pygame.K_e, repeat=True, count=8)
    assert not game.world.participation.state['masonry_read']
    recorder.still('masonry_inspection')
    recorder.dialogue(2.4)
    assert game.world.participation.state['masonry_read']
    recorder.mark('The same workers finish their finite sorting and resume tool work; bridge gap remains open')
    recorder.until(lambda: crew.state['sorted'] == 3 and crew.stage == 'ready', limit=90)
    recorder.until(lambda: any(e['action'] == 'start' and e['key'] == 'bridge_tool'
                             for e in recorder.events), limit=15)
    recorder.run(2)
    recorder.still('masonry_return')
    recorder.checks.update(real_worker_progress=True, sorted_blocks=crew.state['sorted'],
        inspection_acknowledged=True, tea_not_started=crew.state['tea_beat'] == 0,
        no_manufactured_worker_state=True, actual_tool_contact_audio=True)
    assert crew.state['tea_beat'] == 0
    return recorder.close()


CLIPS = {'guard': guard_clip, 'bench': bench_clip, 'cat': cat_clip, 'masonry': masonry_clip}


def finish_preview(reports):
    names = [r['name'] for r in reports]
    concat = OUT/'preview_concat.txt'
    concat.write_text(''.join("file '"+name+".mp4'\n" for name in names))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
        '-i', str(concat), '-c', 'copy', '-movflags', '+faststart',
        str(OUT/'checkpoint_charm_preview.mp4')], check=True)
    size = (OUT/'checkpoint_charm_preview.mp4').stat().st_size
    assert size <= 50*1024*1024, ('Library preview exceeds 50 MiB', size)
    summary = {'method': __doc__, 'clips': names, 'seconds': sum(r['seconds'] for r in reports),
        'preview_bytes': size, 'native_size': [480, 320], 'display_size': [960, 640],
        'simulation_hz': 30, 'video_fps': 15,
        'fixtures': ['completed MQ01–MQ03 predecessor quests', 'initial player stations only'],
        'limits': ['SDL dummy audio is not a live device recording',
            'Offline PCM preserves accepted production sources, gains and stops; no subjective listening claim',
            'Pause and title/Continue demonstrations call documented production APIs and are labelled in trace',
            'Cat acknowledgment is intentionally silent; no synthetic animal sound was added'],
        'checks': {r['name']: r['checks'] for r in reports}}
    write_json(OUT/'capture_summary.json', summary)
    files = sorted(p for p in OUT.iterdir() if p.is_file() and p.name != 'SHA256SUMS')
    (OUT/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clips', nargs='+', choices=list(CLIPS), default=list(CLIPS))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    reports = []
    with tempfile.TemporaryDirectory() as tmp, patch('pygame.mixer.find_channel', side_effect=audio_capture.Channel):
        for name in args.clips:
            print('Recording '+name, flush=True)
            reports.append(CLIPS[name](Path(tmp)))
            print('Finished '+name+': '+str(round(reports[-1]['seconds'], 2))+'s', flush=True)
    summary = finish_preview(reports)
    print(json.dumps({'clips': summary['clips'], 'seconds': summary['seconds'],
                      'preview_bytes': summary['preview_bytes']}), flush=True)
    pygame.quit()


if __name__ == '__main__':main()
