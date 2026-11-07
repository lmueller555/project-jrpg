"""Capture real party menus, story selection, exploration and three-member combat.

The disposable fresh journey explicitly recruits Mira, Lucan, Rhea and Edran
through Game's public story API. Their recruitment is a review fixture, not a
new story event. Authored quests, progression, skills and rewards are unchanged.
Inputs, simulation and rendering use production code; frames are never painted
or composited. Saves and settings live in a TemporaryDirectory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image

from main import Game

FPS = 30
SIZE = (960, 640)
OUTPUT = ROOT/'docs/reviews/party_system'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprints():
    paths = list(ROOT.glob('*.py'))+[Path(__file__).resolve()]
    paths += list((ROOT/'assets/characters').glob('*.json'))
    paths += list((ROOT/'assets/combat').glob('*.json'))
    for identifier in ('caelan', 'mira', 'lucan', 'rhea', 'edran', 'rivet', 'bat'):
        for directory in (ROOT/'assets/characters'/identifier, ROOT/'assets/combat'/identifier):
            paths += [p for p in directory.rglob('*') if p.is_file()]
    return {str(path.relative_to(ROOT)):digest(path) for path in sorted(set(paths))}


def write_json(path, value):path.write_text(json.dumps(value, indent=2)+'\n')


class Capture:
    def __init__(self, output):
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.frames = 0
        self.inputs, self.shots, self.checks, self.stages = [], [], {}, []
        self.menu_frames = []
        self.record_menu = False
        self.encoder = subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo',
            '-pixel_format','rgb24','-video_size','960x640','-framerate',str(FPS),'-i','-',
            '-an','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',
            str(output/'party_system_silent.mp4')], stdin=subprocess.PIPE)

    def key(self, game, key):
        self.inputs.append({'frame':self.frames, 'kind':'key', 'key':pygame.key.name(key)})
        assert game.handle_events([pygame.event.Event(pygame.KEYDOWN,key=key,repeat=False),
                                   pygame.event.Event(pygame.KEYUP,key=key)])

    def click(self, game, point):
        _, size, origin = game._ensure_ui_surface()
        physical = (round(origin[0]+point[0]*size[0]/480),
                    round(origin[1]+point[1]*size[1]/320))
        self.inputs.append({'frame':self.frames, 'kind':'click', 'logical':list(point),
                            'window':list(physical)})
        assert game.handle_events([pygame.event.Event(kind,button=1,pos=physical)
                                   for kind in (pygame.MOUSEBUTTONDOWN,pygame.MOUSEBUTTONUP)])

    def wheel(self, game, amount):
        self.inputs.append({'frame':self.frames,'kind':'wheel','amount':amount})
        assert game.handle_events([pygame.event.Event(pygame.MOUSEWHEEL,y=amount,x=0)])

    def frame(self, game, direction=(0,0)):
        assert game.handle_events()
        game.update(1/FPS,direction,False)
        game.draw()
        assert game.window.get_size() == SIZE
        self.encoder.stdin.write(pygame.image.tobytes(game.window,'RGB'))
        if self.record_menu and self.frames%5 == 0:
            self.menu_frames.append(Image.frombytes('RGB',SIZE,pygame.image.tobytes(game.window,'RGB')))
        self.frames += 1

    def hold(self, game, seconds, stage, direction=(0,0)):
        self.stages.append({'frame':self.frames,'stage':stage})
        for _ in range(math.ceil(seconds*FPS)):self.frame(game,direction)

    def shot(self, game, name):
        game.draw()
        pygame.image.save(game.window,str(self.output/name))
        self.shots.append({'file':name,'frame':self.frames,'window':list(game.window.get_size()),
            'text_scale':game.audio.text_scale,'active':list(game.party.active_ids),
            'draft':list(game.party_ui.formation) if game.party_ui.is_open else None,
            'event':game.party.current_event_id,
            'combatants':[member.identifier for member in game.combat.model.party]
                          if game.combat.active else [],
            'followers':[actor.identifier for actor in game.party_travel.actors()]})
        assert game.ui_surface.get_clip() == game.ui_surface.get_rect()

    def open_menu(self, game):
        self.key(game,pygame.K_ESCAPE)
        assert game.pause.is_open
        self.key(game,pygame.K_DOWN);self.key(game,pygame.K_DOWN)
        self.key(game,pygame.K_RETURN)
        assert game.party_ui.is_open and game.pause.overlay == 'party'
        game.draw()

    def close_pause(self, game):
        if game.party_ui.is_open:self.key(game,pygame.K_ESCAPE)
        if game.pause.is_open:self.key(game,pygame.K_ESCAPE)
        assert not game.pause.is_open and not game.party_ui.is_open

    def choose_looking_at(self, game, identifier):
        ui = game.party_ui
        if ui.focus != 'roster':self.key(game,pygame.K_RIGHT)
        while ui.roster[ui.selected_member] != identifier:self.key(game,pygame.K_DOWN)
        game.draw()

    def run(self):
        before = fingerprints()
        with tempfile.TemporaryDirectory(prefix='party-system-review-') as directory:
            directory = Path(directory)
            game = Game(window_size=SIZE,fullscreen=False,start_on_title=False,
                        save_path=directory/'journey.json',settings_path=directory/'settings.json')
            game.audio.set_music(0);game.audio.set_effects(0)
            pygame.event.clear()
            progression = game.lattice.to_dict()
            # Explicit public-API review fixtures. Future recruitment stays unimplemented.
            for identifier in ('mira','lucan','rhea','edran'):
                assert game.recruit_party_member(identifier)
                if game.party_ui.is_open:self.key(game,pygame.K_ESCAPE)
            assert game.set_party_member_available('rhea',False,
                'Resting at the sanctuary after the journey. Rhea will rejoin the travelling '
                'party once she has recovered and the group returns to town.')
            game.attributes.set_current(hp=103,mp=11)
            game.party.attributes('mira').set_current(hp=177,mp=13)
            game.party.attributes('lucan').set_current(hp=0,mp=4)
            game.party.attributes('edran').set_current(hp=81,mp=5)
            assert game.save_progress()
            resources = {key:(a.current_hp,a.current_mp) for key,a in game.party.characters.items()}
            self.checks['fixture_recruited'] = list(game.party.members)
            self.record_menu = True
            self.open_menu(game)
            self.hold(game,.8,'Five recruited; three active; existing resources shown')
            self.shot(game,'roster_normal.png')
            # Keyboard draft replaces KO Lucan with Edran, then Escape discards it.
            self.choose_looking_at(game,'edran')
            self.key(game,pygame.K_RETURN)
            assert game.party_ui.formation == ('caelan','mira','edran')
            assert game.party.active_ids == ('caelan','mira','lucan')
            self.hold(game,.65,'Keyboard replacement is a draft until confirmed')
            self.shot(game,'draft_before_cancel.png')
            self.close_pause(game)
            assert game.party.active_ids == ('caelan','mira','lucan')
            assert resources == {key:(a.current_hp,a.current_mp) for key,a in game.party.characters.items()}
            self.checks['cancel_keeps_formation_and_all_resources'] = True
            self.open_menu(game)
            self.choose_looking_at(game,'rhea')
            self.key(game,pygame.K_RETURN)
            assert game.party_ui.formation == ('caelan','mira','lucan')
            self.hold(game,1.0,'Unavailable companion remains inspectable with an authored reason')
            self.shot(game,'roster_unavailable.png')
            # Native minimum window; actual UI text scale, no resized screenshot.
            assert game.handle_events([pygame.event.Event(pygame.VIDEORESIZE,w=480,h=320)])
            game.audio.set_text_scale(1.5)
            self.shot(game,'roster_minimum_150.png')
            rect = game.party_ui.roster_rects['rhea'].clip(game.party_ui.roster_view)
            assert rect.height > 15
            self.click(game,rect.center)
            assert game.party_ui.formation == ('caelan','mira','lucan')
            self.key(game,pygame.K_END)
            self.shot(game,'roster_minimum_reason_end.png')
            self.checks['minimum_window_large_text_mouse_rejection_and_reason_scroll'] = True
            assert game.handle_events([pygame.event.Event(pygame.VIDEORESIZE,w=960,h=640)])
            game.audio.set_text_scale(1.0)
            # Mouse selects slot three, scrolls to Edran, selects and confirms.
            self.click(game,game.party_ui.slot_rects[2].center)
            self.wheel(game,-8)
            game.draw()
            rect = game.party_ui.roster_rects['edran'].clip(game.party_ui.roster_view)
            assert rect.height > 15
            self.click(game,rect.center)
            assert game.party_ui.formation == ('caelan','mira','edran')
            self.hold(game,.7,'Mouse selects a reserve in the third active slot')
            self.click(game,game.party_ui.confirm_rect.center)
            assert not game.party_ui.is_open
            self.close_pause(game)
            assert game.party.active_ids == ('caelan','mira','edran')
            assert resources == {key:(a.current_hp,a.current_mp) for key,a in game.party.characters.items()}
            self.checks['mouse_confirm_changes_formation_without_heal_or_revive'] = True
            self.record_menu = False
            callback = []
            assert game.request_party_selection('review_dungeon',required=('mira',),
                title='Choose dungeon party',reason='The party is fixed until the dungeon event ends.',
                lock_after=True,on_confirm=lambda:callback.append('confirmed'))
            assert not game.party_event_ready('review_dungeon')
            self.hold(game,.8,'Persistent selection gate requires Mira before the event')
            self.shot(game,'selection_gate.png')
            assert game._read_saved_journey() is not None
            loaded = Game(window_size=SIZE,fullscreen=False,start_on_title=True,
                save_path=directory/'journey.json',settings_path=directory/'settings.json')
            loaded.audio.set_music(0);loaded.audio.set_effects(0)
            assert loaded.has_saved_journey and loaded.begin_journey(True)
            game = loaded
            assert game.party_ui.is_open and game.party.pending_selection['event_id']=='review_dungeon'
            assert resources == {key:(a.current_hp,a.current_mp) for key,a in game.party.characters.items()}
            self.hold(game,.6,'Reload resumes the pending selection through its saved event ID')
            self.shot(game,'selection_after_reload.png')
            self.click(game,game.party_ui.confirm_rect.center)
            assert game.party.locked and game.party.pending_selection is None
            assert game.party_event_ready('review_dungeon')
            assert callback == []  # Runtime closures are intentionally not serialized.
            self.checks['selection_gate_resumes_after_reload_and_locks_on_confirm'] = True
            self.checks['runtime_callback_is_not_serialized'] = True
            self.open_menu(game)
            self.key(game,pygame.K_DELETE)
            self.hold(game,.8,'Confirmed event locks the formation with its reason')
            self.shot(game,'event_locked.png')
            self.close_pause(game)
            assert game.end_party_event('review_dungeon')
            # KO reserve stays KO. Restore this review actor explicitly for the reel.
            assert game.party.attributes('lucan').set_current(hp=97,mp=4)
            assert game.set_active_party(('caelan','mira','lucan'))
            self.checks['combat_fixture_explicitly_restores_lucan_hp'] = 97
            # Authored town route; player and followers move through normal updates.
            game.player.position.update(300,544);game.player.facing='right';game.camera.reset()
            game.party_travel.reset()
            assert all(game.world.can_stand((x,544)) for x in range(300,621))
            self.hold(game,1.8,'Three selected members follow the traversed town route',direction=(1,0))
            assert len(game.party_travel.actors()) == 2
            self.shot(game,'travel_trail.png')
            self.hold(game,.7,'Travelling party turns along its recorded route',direction=(1,0))
            self.checks['travel_followers'] = [actor.identifier for actor in game.party_travel.actors()]
            # Production contact encounter, including its transition and ATB clocks.
            game.player.position.update(game.combat.position+(0,24));game.player.facing='back'
            game.camera.reset()
            assert game.combat.interact(rng=random.Random(7))
            self.hold(game,1.3,'Live three-member encounter entry')
            self.shot(game,'three_member_battle.png')
            assert game.handle_events([pygame.event.Event(pygame.VIDEORESIZE,w=480,h=320)])
            game.audio.set_text_scale(1.5)
            self.shot(game,'three_member_battle_minimum_150.png')
            assert game.handle_events([pygame.event.Event(pygame.VIDEORESIZE,w=960,h=640)])
            game.audio.set_text_scale(1.0)
            model, acted, captured = game.combat.model, [], set()
            for _ in range(800):
                if model.waiting_for_player:
                    actor = model.ready_actor
                    action = 'attack' if actor == 'mira' else 'guard'
                    game.draw()
                    assert action in game.combat.scene.command_rects
                    self.click(game,game.combat.scene.command_rects[action].center)
                    assert model.current_action is not None
                    acted.append({'actor':actor,'action':model.current_action.action,'frame':self.frames})
                self.frame(game)
                action = model.current_action
                if action and action.actor == 'mira' and action.resolved and 'mira' not in captured:
                    self.shot(game,'mira_three_member_action.png');captured.add('mira')
                if len({entry['actor'] for entry in acted}) == 3 and not model.current_action:break
                if model.ended:raise AssertionError('Review battle ended before all three actors commanded')
            else:raise AssertionError('Three-member battle command loop timed out')
            self.checks['real_combat_actions'] = acted
            self.hold(game,.4,'Three active members have each received a command')
            assert game.lattice.to_dict() == progression
            self.checks['progression_unchanged'] = True
            game.opening_audio.reset();game.music.stop()
        self.encoder.stdin.close()
        assert self.encoder.wait() == 0
        assert self.menu_frames
        self.menu_frames[0].save(self.output/'party_menu.gif',save_all=True,
            append_images=self.menu_frames[1:],duration=round(5000/FPS),loop=0,optimize=True)
        after = fingerprints()
        write_json(self.output/'fingerprints.json',after)
        artifacts = {path.name:digest(path) for path in self.output.iterdir()
                     if path.suffix in ('.png','.gif','.mp4')}
        report = {'fixtures':__doc__,'fps':FPS,'video_frames':self.frames,
            'video_seconds':self.frames/FPS,'menu_native_size':list(SIZE),
            'source_changed_during_capture':before != after,
            'inputs':self.inputs,'stages':self.stages,'screenshots':self.shots,
            'checks':self.checks,'artifacts':artifacts}
        write_json(self.output/'verification.json',report)
        pygame.quit()
        print(json.dumps({'frames':self.frames,'seconds':round(self.frames/FPS,2),
                          'checks':len(self.checks),'source_changed':before!=after}))


def check(output):
    report = json.loads((output/'verification.json').read_text())
    recorded = json.loads((output/'fingerprints.json').read_text())
    assert recorded == fingerprints(), 'Sources changed; recapture before final review.'
    assert not report['source_changed_during_capture'], 'Sources changed during capture; recapture.'
    for filename,expected in report['artifacts'].items():assert digest(output/filename) == expected, filename
    probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',
                                               str(output/'party_system_silent.mp4')]))
    streams = probe['streams']
    assert len(streams)==1 and streams[0]['codec_type']=='video'
    assert (streams[0]['width'],streams[0]['height'])==SIZE
    assert int(streams[0]['nb_frames'])==report['video_frames']
    assert {action['actor'] for action in report['checks']['real_combat_actions']} >= {'player','mira','lucan'}
    print('Party review source fingerprints, artifacts, silent video and three actors verified.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    if args.check:check(args.output)
    else:
        capture = Capture(args.output)
        try:capture.run()
        finally:
            if capture.encoder.poll() is None:
                capture.encoder.stdin.close()
                capture.encoder.wait()
            pygame.quit()


if __name__ == '__main__':main()
