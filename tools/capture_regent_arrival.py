"""Capture the production MQ02 report, Aldric's arrival and the MQ03 handoff.

Only earlier quest work and the initial clear mill-report station are seeded.
The final report, cinematic, persistence and subsequent visit use production
Game input/update/draw. SDL dummy has no audio loopback: the review soundtrack
is reconstructed from exact OGGs and observed mixer commands, with effects muted.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests'), str(ROOT/'tools')]

import numpy as np
import pygame
from PIL import Image
from main import Game
from npc_routines import find_path
from quests import OPENING_QUEST, MILL_QUEST, REGENT_QUEST
from capture_battle_music_transition import MixerTrace, FPS, RATE
from capture_mill_quest import save_gif
from quest_capture_navigation import travel_to


class Capture:
    def __init__(self, output):
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='regent-arrival-review-')
        self.path = Path(self.temp.name)/'journey.json'
        self.trace = MixerTrace()
        self.trace.install()
        self.g = Game(window_size=(960, 640), fullscreen=False,
                      start_on_title=False, save_path=self.path,
                      settings_path=Path(self.temp.name)/'settings.json')
        self.g.audio.set_music(.65)
        self.g.audio.set_effects(0)
        self.frames = 0
        self.encoder = None
        self.events = []
        self.screenshots = []
        self.dialogue = []
        self.room_transitions = []
        self.gif_frames = []
        self.gif_durations = []
        self.freeze_checks = 0
        self.last_identity = None
        self.last_shot = None
        self._still_phases = set()
        self.quest_frames = []
        self.cart_frames = []
        self.admission_frames = []
        self.pause_check = False
        self.frozen = None
        self._seed_report()

    @property
    def seconds(self):
        return self.frames/FPS

    @property
    def c(self):
        return self.g.regent_arrival

    def mark(self, event, **values):
        self.events.append({'time':round(self.seconds, 6), 'event':event, **values})

    def world_signature(self):
        return {'world':self.g.world.data['id'],
                'player':list(self.g.player.position),
                'elapsed_ms':self.g.elapsed_ms,
                'actors':[(world.data['id'], actor.data['id'], list(actor.position))
                          for world in self.g.scenes.values() for actor in world.npcs]}

    def _seed_report(self):
        """Earlier work is a fixture; the report is left unread and uncommitted."""
        g = self.g
        assert g.accept_quest(OPENING_QUEST)
        for objective in ('halden', 'elira', 'venn'):
            assert g.quests.complete_objective(OPENING_QUEST, objective)
        g._sync_inventory()
        g.halden_visit.restore();g.elira_visit.restore();g.venn_visit.restore()
        assert g.quests.turn_in(OPENING_QUEST, 'mother_serene')
        assert g.quests.unlock(MILL_QUEST)
        g.opening_conclusion.restore({'version':1, 'stage':'done'})
        g.opening.restore({'version':1, 'stage':'disabled'})
        assert g.accept_quest(MILL_QUEST)
        for objective in g.quests.definitions[MILL_QUEST]['objectives']:
            if objective['id'] == 'report':break
            assert g.quests.complete_objective(MILL_QUEST, objective['id'])
        assert g.mill_quest.restore({'version':1,
            'inspected':['mechanism', 'race', 'intake'],
            'prepared':True, 'spell_done':True, 'encouraged':True,
            'restored':True, 'verified':True, 'resolved':False})
        # The legacy repair fixture records no invented victory or battle reward.
        assert g.mill_quest.legacy_bypass and not g.mill_quest.encounter_cleared
        g.world = g.town
        near = pygame.Vector2(g.mill_quest.halden.position)
        station = next(near+offset for offset in ((-24,24), (0,32), (24,24), (-32,0))
                       if g.town.can_stand(near+offset))
        g.player.position.update(station)
        g.player.facing = 'back'
        g.mill_quest._place_mira(g.town, station+(28,0))
        g.opening_fade = g.transfer_cooldown = 0
        g.social.blocked.clear();g.quests.drain_events();g.quest_ui.reset();g.camera.reset()
        assert g.quests.status(MILL_QUEST) == 'active'
        assert g.quests.status(REGENT_QUEST) == 'locked'
        assert g.mill_quest.stage == 'report'
        assert g.save_progress()
        self.start_station = list(g.player.position)
        self.prior_inventory = g.inventory.to_dict()
        self.fixture = {'MQ01':'completed through public quest APIs',
            'MQ02':'repair and verification complete; report remains active/unread',
            'encounter':'legitimate legacy-bypass snapshot; no victory or rewards invented',
            'initial_player_station':self.start_station,
            'later_actor_relocation':False,
            'cinematic_progress_assigned':False}

    def post_key(self, value):
        for kind in (pygame.KEYDOWN, pygame.KEYUP):
            pygame.event.post(pygame.event.Event(kind, key=value, repeat=False))

    def key(self, value):
        self.post_key(value)
        assert self.g.handle_events()

    def snapshot(self, filename):
        self.g.draw()
        pygame.image.save(self.g.window, str(self.output/filename))
        if filename not in self.screenshots:self.screenshots.append(filename)

    def frame(self, *, direction=(0,0), recording=True):
        before = self.world_signature() if self.c.active else None
        active_before = self.c.active
        assert self.g.handle_events()
        self.g.update(1/FPS, direction, False)
        if before is not None and self.c.active:
            assert self.world_signature() == before, 'Exploration advanced during cinematic'
            self.freeze_checks += 1
        self.g.draw()
        if recording:
            self.encoder.stdin.write(pygame.image.tobytes(self.g.window, 'RGB'))
            self.trace.advance(1/FPS)
            if self.frames % FPS == 0:
                image = Image.frombytes('RGB', self.g.window.get_size(),
                    pygame.image.tobytes(self.g.window, 'RGB'))
                self.gif_frames.append(image.resize((480,320), Image.Resampling.NEAREST))
                self.gif_durations.append(1000)
            if self.c.active and self.c.shot == 'gate_admission' and self.frames % 3 == 0:
                self.admission_frames.append(Image.frombytes('RGB',self.g.window.get_size(),
                    pygame.image.tobytes(self.g.window,'RGB')).resize((480,320),Image.Resampling.NEAREST))
            self.frames += 1
        if active_before and not self.c.active:
            self.mark('cinematic_finished', state=self.c.state,
                player=list(self.g.player.position), world=self.g.world.data['id'])

    def tick(self, seconds=1/30, direction=(0,0), record=True):
        # Door-navigation compatibility; live world movement is sampled at30fps.
        self.frame(direction=direction, recording=record)

    def hold(self, seconds, *, recording=True):
        for _ in range(round(seconds*FPS)):self.frame(recording=recording)

    def until(self, predicate, label, *, seconds=90, recording=True):
        for _ in range(round(seconds*FPS)):
            if predicate():return
            self.frame(recording=recording)
        raise AssertionError(('Timed out', label, self.g.world.data['id']))

    def walk(self, goal, seconds=180, next_scene=None):
        """Use production movement, collision and door transfers after the scene."""
        world = self.g.world
        goal = pygame.Vector2(goal)
        route = []
        stalled = 0
        for _ in range(round(seconds*FPS)):
            if self.g.world is not world:
                assert self.g.world.data['id'] == next_scene
                return
            if self.g.social.active:
                identifier = self.g.social.script_identifier
                if identifier in {'regent_'+kind for kind in ('preparations','arrival','dispute','welcome','discussion','aftermath')}:return
                self.read_social(identifier,recording=False)
            if self.g.player.position.distance_to(goal) < 1.5:
                if next_scene is None:return
                door = next(d for d in world.doors
                    if pygame.Vector2(d.data['anchor']).distance_to(goal) < 3)
                self.frame(direction=(0,-1 if door.data['entry_side']=='north' else 1), recording=False)
                continue
            if not route or stalled >= 20:
                found = find_path(world, self.g.player.position, goal, world.probe_size, None)
                assert found is not None, ('No route', world.data['id'], list(self.g.player.position), list(goal))
                route = list(found);stalled = 0
            if not route:return
            delta = pygame.Vector2(route[0])-self.g.player.position
            if delta.length() < 1.5:
                route.pop(0);continue
            before = self.g.player.position.copy()
            # Unit direction has realGame speed; clamp final step to avoid oscillation.
            self.g.update(min(1/FPS,delta.length()/72), delta, False)
            stalled = stalled+1 if self.g.player.position == before else 0
        raise AssertionError(('Walking stalled', world.data['id'], list(self.g.player.position), list(goal)))

    def read_social(self, expected, *, recording=True):
        pages = 0
        while self.g.social.active:
            assert self.g.social.script_identifier == expected, self.g.social.script_identifier
            pages += 1
            assert pages < 120, expected
            self.hold(1.4 if recording else .15, recording=recording)
            page = self.g.social.page
            self.dialogue.append({'script':expected, 'speaker':page.get('speaker'),
                'text':page.get('text'), 'world':self.g.world.data['id']})
            if isinstance(expected,str) and expected.startswith('regent_'):
                self.quest_frames.append(Image.frombytes('RGB', self.g.window.get_size(),
                    pygame.image.tobytes(self.g.window, 'RGB')).resize((480,320), Image.Resampling.NEAREST))
                name = expected.removeprefix('regent_')+'.png'
                if name not in self.screenshots:self.snapshot(name)
            self.key(pygame.K_SPACE)
            if self.c.active:return

    def accessibility_snapshot(self, filename, size=(480,320), scale=1.5):
        old_size = self.g.window.get_size()
        old_scale = self.g.audio.text_scale
        try:
            self.g.window = pygame.display.set_mode(size, pygame.RESIZABLE)
            self.g.audio.set_text_scale(scale)
            self.snapshot(filename)
            layout = self.c.caption_layout
            assert layout is not None
            assert pygame.Rect(0,0,480,320).contains(layout.panel)
            assert layout.panel.contains(layout.portrait)
            assert not layout.panel.colliderect(self.c.skip_rect)
            painter = self.g.ui.painter(self.g.ui_surface)
            for index,line in enumerate(self.c.caption_lines):
                width,height = painter.font().size(line)
                rect = pygame.Rect(layout.text_origin[0],layout.text_origin[1]+index*layout.line_height,width,height)
                assert layout.panel.contains(rect), (filename,line,list(rect),list(layout.panel))
            assert ' '.join(line for page in self.c.caption_pages for line in page).split() == self.c.dialogue['text'].split()
            return {'window':list(size), 'text_scale':scale, 'panel':list(layout.panel),
                    'pages':len(self.c.caption_pages), 'portrait_inside':True, 'prose_inside':True,
                    'skip_clear':True, 'complete_source_text':True}
        finally:
            self.g.window = pygame.display.set_mode(old_size, pygame.RESIZABLE)
            self.g.audio.set_text_scale(old_scale)
            self.g.draw()

    def _finish_video(self):
        self.encoder.stdin.close()
        assert self.encoder.wait() == 0
        self.encoder = None
        audio = np.concatenate(self.trace.blocks)
        assert len(audio) == self.frames*(RATE//FPS)
        assert np.max(np.abs(audio)) < 1
        with wave.open(str(self.output/'soundtrack.wav'), 'wb') as target:
            target.setparams((2,2,RATE,0,'NONE','not compressed'))
            target.writeframes(np.round(audio*32767).astype('<i2').tobytes())
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(self.output/'silent.mp4'),
            '-i',str(self.output/'soundtrack.wav'),'-c:v','copy','-c:a','aac','-b:a','160k',
            '-movflags','+faststart','-shortest',str(self.output/'regent_arrival.mp4')], check=True)
        self.output.joinpath('silent.mp4').unlink()
        self.output.joinpath('soundtrack.wav').unlink()
        save_gif(self.output/'regent_arrival.gif', self.gif_frames, self.gif_durations, 112)
        save_gif(self.output/'gate_admission.gif',self.admission_frames,[100]*len(self.admission_frames),112)
        self.music_evidence = {'initial':self.trace.initial, 'events':list(self.trace.events),
            'source_files':{str(Path(path).relative_to(ROOT)):hashlib.sha256(Path(path).read_bytes()).hexdigest()
                            for path in self.trace.samples},
            'soundtrack':'Reconstructed from exact runtime OGGs and observed production mixer calls; not hardware loopback. Effects muted.'}

    def _pause_focus_proof(self):
        before = (self.c.elapsed, self.c.phase_time, self.c.dialogue_index, self.c.page_index)
        self.key(pygame.K_ESCAPE)
        assert self.c.paused
        self.hold(.7)
        assert before == (self.c.elapsed, self.c.phase_time, self.c.dialogue_index, self.c.page_index)
        self.snapshot('paused.png')
        self.key(pygame.K_ESCAPE)
        assert not self.c.paused
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        assert self.g.handle_events()
        before = (self.c.elapsed, self.c.phase_time, self.c.dialogue_index, self.c.page_index)
        self.hold(.5)
        assert before == (self.c.elapsed, self.c.phase_time, self.c.dialogue_index, self.c.page_index)
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        assert self.g.handle_events()
        self.pause_check = True
        self.mark('pause_and_focus_freeze_verified')

    def _cinematic(self):
        """Hold each real page long enough to read, then send an ordinary key."""
        last_page = None
        due = 0
        self.accessibility = {}
        for _ in range(24000):
            if not self.c.active:return
            phase = self.c.shot
            if phase != self.last_shot:
                self.mark('shot', id=phase, scene=self.c.phase['scene'])
                self.last_shot = phase
            dialogue = self.c.dialogue
            identity = (self.c.phase_index, self.c.dialogue_index, self.c.page_index)
            if dialogue is not None and identity != last_page:
                self.g.draw()
                self.dialogue.append({'shot':phase, 'speaker':dialogue['speaker'],
                    'text':dialogue['text'], 'page':self.c.page_index})
                last_page = identity
                words = len(' '.join(self.c.caption_lines).split())
                due = self.seconds+max(1.7, words*.28)
            if phase not in self._still_phases and self.c.phase_time >= (1.0 if dialogue is None else .3):
                self.snapshot(phase+'.png')
                self._still_phases.add(phase)
                if phase == 'gate_greeting' and not self.pause_check:
                    self.pending_bytes = self.path.read_bytes()
                    self.pending_inventory = self.g.inventory.to_dict()
                    self._pause_focus_proof()
                if phase in ('locals','bridge_damage','serene_window'):
                    self.accessibility[phase] = self.accessibility_snapshot(phase+'_large_text.png')
                if phase == 'relief':
                    self.accessibility['letterboxed'] = self.accessibility_snapshot('letterboxed.png',(1000,740),1.5)
            if dialogue is not None and self.seconds >= due:
                self.key(pygame.K_SPACE)
                # A min shot hold may reject an early advance; retry only through
                # ordinary input, without moving a clock or controller checkpoint.
                if identity == (self.c.phase_index,self.c.dialogue_index,self.c.page_index):
                    due = self.seconds+.25
            self.frame()
        raise AssertionError('Cinematic did not finish through player input')

    def _snapshot_quest_frame(self):
        self.g.draw()
        self.quest_frames.append(Image.frombytes('RGB', self.g.window.get_size(),
            pygame.image.tobytes(self.g.window,'RGB')).resize((480,320),Image.Resampling.NEAREST))

    def _at_regent(self, key):
        quest = self.g.regent_quest
        travel_to(self, quest.world_for_station(key))
        point = pygame.Vector2(quest.points[key])
        if key == 'road':point += (-20,40)
        station = None
        for radius in (0,8,16,24,32):
            for offset in ((0,radius),(-radius,0),(radius,0),(0,-radius)):
                p = point+offset
                if self.g.world.can_stand(p):station = p;break
            if station is not None:break
        assert station is not None, ('No clear MQ03 station',key)
        core = {'regent_'+kind for kind in ('preparations','arrival','dispute','welcome','discussion','aftermath')}
        for _ in range(12):
            self.walk(station)
            if not self.g.social.active or self.g.social.script_identifier in core:break
            self.read_social(self.g.social.script_identifier,recording=False)
        else:raise AssertionError(('Repeated optional conversations',key))
        self.g.transfer_cooldown = 0

    def _regent_interact(self, kind):
        if not self.g.social.active:self.key(pygame.K_e)
        assert self.g.social.script_identifier == 'regent_'+kind, (
            kind,self.g.social.script_identifier,self.g.regent_quest.stage)
        self.read_social('regent_'+kind,recording=False)

    def _quest(self):
        """Walk and play every revised MQ03 scene after the real arrival."""
        q = self.g.regent_quest
        self.until(lambda:q._preps_ready,'interior preparations',recording=False)
        self._at_regent('arrival')
        assert self.g.quests.status(REGENT_QUEST) == 'available' and q.stage == 'idle'
        assert not self.g.social.active
        self.until(lambda:self.g.quest_ui.current_notice is None and not self.g.quest_ui.notices,
                   'quest notice settles',recording=False,seconds=30)
        self.snapshot('caravan_waiting.png')
        self._at_regent('preparations');self._regent_interact('preparations')
        assert q.stage == 'assigned' and self.g.quests.status(REGENT_QUEST) == 'active'
        self._at_regent('arrival')
        self.snapshot('greeting_station.png')
        self._regent_interact('arrival')
        assert q.stage == 'met'
        self._at_regent('road')
        self.until(lambda:q.stage=='dispute' and q._group_ready,'road crew',recording=False)
        self._regent_interact('dispute')
        assert q.stage == 'releasing'
        old_cart = list(q.cart['position'])
        for step in range(3600):
            if q.stage == 'escorting':break
            self.frame(recording=False)
            if step % 6 == 0:
                self.cart_frames.append(Image.frombytes('RGB',self.g.window.get_size(),
                    pygame.image.tobytes(self.g.window,'RGB')).resize((480,320),Image.Resampling.NEAREST))
        assert q.stage == 'escorting'
        assert old_cart != list(q.cart['position'])
        self.snapshot('cart_released.png')
        self._at_regent('courtyard')
        self.until(lambda:q.stage=='welcome' and q._group_ready,'dining arrival',recording=False)
        self._regent_interact('welcome')
        assert q.stage == 'hosted'
        self.until(lambda:q._group_ready,'meal finished',recording=False)
        self._regent_interact('discussion')
        assert q.stage == 'discussion'
        self.until(lambda:q._aside_ready,'Aldric steps aside',recording=False)
        self._at_regent('aftermath');self._regent_interact('aftermath')
        assert q.stage == 'done' and self.g.quests.status(REGENT_QUEST) == 'completed'
        assert self.g.quests.status('CH01_MQ04') == 'available'
        assert self.g.mill_quest.mill_restored and not self.g.opening_conclusion.mill_stopped
        assert not any('AUTHORIZ' in flag.upper() or 'EXCAVATION_STARTED' in flag.upper()
                       for flag in self.g.social.flags)
        self.snapshot('mq03_complete.png')
        self.until(lambda:q._delivery_done,'cart delivery',recording=False)
        assert pygame.Vector2(q.cart['position']).distance_to(q.points['cart_end']) < 1
        expected = {'regent_'+kind for kind in ('preparations','arrival','dispute','welcome','discussion','aftermath')}
        actual = {row.get('script') for row in self.dialogue}
        assert expected <= actual
        for kind in ('preparations','arrival','dispute','welcome','discussion','aftermath'):
            expected_pages = len(self.g.social._make_pages(q.lines[kind]))
            actual_pages = sum(row.get('script') == 'regent_'+kind for row in self.dialogue)
            assert expected_pages == actual_pages, (kind,expected_pages,actual_pages)
        save_gif(self.output/'mq03.gif',self.quest_frames,[700]*len(self.quest_frames),80)
        save_gif(self.output/'cart_release.gif',self.cart_frames,[200]*len(self.cart_frames),112)
        return {'status':'completed','stage':q.stage,
            'objectives':self.g.quests.states[REGENT_QUEST]['completed_objectives'],
            'main_dialogue_pages':sum(row.get('script') in expected for row in self.dialogue),
            'optional_dialogue_pages':sum(str(row.get('script','')).startswith('regent_') and row.get('script') not in expected for row in self.dialogue),
            'room_transitions':self.room_transitions,
            'final_party_rooms':[q._world(actor).data['id'] for actor in q.party],
            'cart_visible_release':True,'cart_delivery_finished':True,
            'mq04_available':True,'excavation_authorized':False,
            'player_role':'guide and host; witness to adult decisions'}

    def _persistence(self):
        """Probe saved files on separate temporary journeys, not the filmed run."""
        pending = json.loads(self.pending_bytes)
        result = {}
        original_window = self.g.window.get_size()
        settings = Path(self.temp.name)/'probe_settings.json'
        path = Path(self.temp.name)/'pending_probe.json'
        path.write_bytes(self.pending_bytes)
        probe = Game(fullscreen=False,start_on_title=True,save_path=path,settings_path=settings)
        assert probe.begin_journey(True)
        probe.update(.05,(0,0),False)
        assert probe.regent_arrival.active and probe.regent_arrival.state == 'pending'
        assert probe.inventory.to_dict() == self.pending_inventory
        assert probe.quests.status(MILL_QUEST) == 'completed'
        assert probe.quests.status(REGENT_QUEST) == 'available'
        before = probe.inventory.to_dict()
        probe.draw()
        logical = probe.regent_arrival.skip_rect.center
        width,height = probe.window.get_size()
        scale = min(width//480,height//320)
        point = ((width-480*scale)//2+logical[0]*scale,
                 (height-320*scale)//2+logical[1]*scale)
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=point))
        for key in (pygame.K_m,pygame.K_e):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=key,repeat=False))
            pygame.event.post(pygame.event.Event(pygame.KEYUP,key=key,repeat=False))
        assert probe.handle_events()
        assert probe.regent_arrival.state == 'seen' and not probe.regent_arrival.active
        assert probe.inventory.to_dict() == before
        assert not probe.map_open and not probe.social.active
        assert probe.quests.status(REGENT_QUEST) == 'available'
        assert not probe.regent_quest.active
        result.update(pending_resumes=True,skip_commits_seen=True,
                      queued_input_isolated=True,resources_not_duplicated=True)
        assert probe.save_progress()
        seen = Game(fullscreen=False,start_on_title=True,save_path=path,settings_path=settings)
        assert seen.begin_journey(True)
        seen.update(.05,(0,0),False)
        assert seen.regent_arrival.state == 'seen' and not seen.regent_arrival.active
        legacy = dict(pending)
        legacy.pop('regent_arrival')
        path = Path(self.temp.name)/'legacy_probe.json'
        path.write_text(json.dumps(legacy))
        old = Game(fullscreen=False,start_on_title=True,save_path=path,settings_path=settings)
        assert old.begin_journey(True)
        old.update(.05,(0,0),False)
        assert old.regent_arrival.state == 'seen' and not old.regent_arrival.active
        result.update(seen_does_not_replay=True,legacy_completed_mill_does_not_replay=True)
        self.g.window = pygame.display.set_mode(original_window,pygame.RESIZABLE)
        self.g.draw()
        return result

    def record(self):
        self.trace.begin()
        self.encoder = subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo',
            '-pixel_format','rgb24','-video_size','960x640','-framerate',str(FPS),'-i','-',
            '-an','-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p',
            str(self.output/'silent.mp4')],stdin=subprocess.PIPE)
        self.snapshot('mill_before_report.png')
        self.hold(.8)
        self.key(pygame.K_e)
        assert self.g.social.script_identifier == 'mill_resolution'
        self.read_social('mill_resolution')
        self.until(lambda:self.c.active,'arrival after MQ02 report')
        assert self.g.quests.status(MILL_QUEST) == 'completed'
        assert self.g.quests.status(REGENT_QUEST) == 'available'
        self.frozen = self.world_signature()
        self._cinematic()
        assert self.c.state == 'seen'
        assert self.g.quests.status(REGENT_QUEST) == 'available'
        assert self.g.regent_quest.stage == 'idle'
        assert list(self.g.player.position) == self.start_station
        assert self.g.world is self.g.town
        self.hold(.6)
        self.snapshot('return_to_mill.png')
        assert self.g.inventory.to_dict() == self.pending_inventory
        self._finish_video()
        party_before_accept = [{'actor':actor.data['id'],'position':list(actor.position),
            'world':self.g.regent_quest._world(actor).data['id'],
            'visible':actor in self.g.town.npcs} for actor in self.g.regent_quest.party]
        assert all(row['visible'] for row in party_before_accept)
        quest = self._quest()
        persistence = self._persistence()
        inputs = [ROOT/name for name in ('main.py','mill_quest.py','regent_quest.py',
            'regent_arrival.py','speech_bubble.py','social.py','ui_style.py','tools/capture_regent_arrival.py',
            'assets/story/regent/scene.json','assets/story/regent/layout.json','assets/story/regent/art.json')]
        inputs += sorted((ROOT/'assets/story/regent_arrival').rglob('*'))
        hashes = {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in inputs if path.is_file()}
        report = {'actual_renderer':True,'capture_stage':'final' if self.output == ROOT/'docs/reviews/regent_arrival' else 'diagnostic',
            'started_at_utc':self.started_at,'finished_at_utc':datetime.now(timezone.utc).isoformat(),'fixture':self.fixture,
            'video':{'file':'regent_arrival.mp4','frames':self.frames,'fps':FPS,'seconds':self.seconds},
            'events':self.events,'screenshots':self.screenshots,'dialogue':self.dialogue,
            'world_freeze_checks':self.freeze_checks,'pause_and_focus_verified':self.pause_check,
            'accessibility':self.accessibility,'mq02_completed':True,'mq03_available_after_cinematic':True,
            'caelan_restored_to_report_station':True,'report_station':self.start_station,
            'caravan_visible_before_acceptance':party_before_accept,'mq03':quest,
            'persistence':persistence,'music':self.music_evidence,'render_input_sha256':hashes,
            'captures':{path.name:hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in sorted(self.output.iterdir()) if path.suffix in ('.png','.gif','.mp4')}}
        self.output.joinpath('capture_report.json').write_text(json.dumps(report,indent=2)+'\n')
        self.output.joinpath('README.md').write_text("""# Aldric's arrival and revised MQ03

[Watch the arrival cinematic with music](regent_arrival.mp4) · [Animated preview](regent_arrival.gif)

These are production Game renders and ordinary event-driven quest/cinematic input.
A temporary fixture completes MQ01 and MQ02's earlier mill repair/verification,
leaving the report unread. It uses a legitimate legacy repair bypass, without
inventing battle victory or rewards. The final mill report, arrival, all six
revised MQ03 scenes, NPC movement, cart release and door transfers are played.
No cinematic clock or progression checkpoint is assigned during capture.

| Arrival at the southern land gate | Aldric listens to locals |
| --- | --- |
| ![Checkpoint greeting](gate_greeting.png) | ![Local consequences](locals.png) |

| Ruined western bridge | Serene inside the sanctuary |
| --- | --- |
| ![Bridge damage](bridge_damage.png) | ![Serene watches the approach](serene_window.png) |

| Caravan approaching Eldenmere | Correct town waiting station |
| --- | --- |
| ![Town approach](town_approach.png) | ![Town caravan](caravan_waiting.png) |

[150% local dialogue](locals_large_text.png) · [150% Serene dialogue](serene_window_large_text.png) · [Letterboxed view](letterboxed.png) · [Paused](paused.png)

[Gate admission motion](gate_admission.gif) · [All six revised MQ03 conversations](mq03.gif) · [Actual cart release](cart_release.gif)

The arrival freezes exploration and preserves Caelan's mill station. MQ03 stays
available until Serene's dining preparations are acknowledged. Separate saved
journey probes verify pending playback recovery, skip, queued-input isolation,
no duplicate resources and no replay for already-seen or legacy completed saves.
The bridge remains ruined and no excavation is authorized. The preserved town
music in the MP4 is reconstructed from exact runtime OGGs and observed mixer
commands because SDL dummy provides no loopback; effects are muted.

[Capture measurements and source hashes](capture_report.json).
""")
        print(json.dumps({'video_seconds':self.seconds,'frames':self.frames,
            'freeze_checks':self.freeze_checks,'mq03':quest,'persistence':persistence,
            'source_hashes':len(hashes),'captures':len(report['captures'])}))

    def close(self):
        if self.encoder is not None:
            self.encoder.stdin.close()
            self.encoder.wait()
        self.trace.close()
        self.temp.cleanup()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/reviews/regent_arrival')
    args = parser.parse_args()
    capture = Capture(args.output)
    try:capture.record()
    finally:capture.close()


if __name__ == '__main__':
    main()
