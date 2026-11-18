"""Review actual well feedback with disposable Game state and offline PCM.

The dummy SDL device cannot provide hardware loopback. Fake output-channel
leases expose the production WellAudio accepted start/gain/stop stream; this
helper mixes that stream using the same original PCM provider and sample rate.
It adds no cues, soundtrack, normalization, compression or limiting. Player
position changes used for distance/scene fixtures are labelled in the report;
the gardener always follows actual Game.update navigation and mechanism gates.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import wave
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pygame
from main import Game
from well_audio import WELL_POSITION, well_distance_gain
from well_audio_samples import DURATIONS, samples

OUTPUT = ROOT/'docs/reviews/well_feedback'
FPS = 30
DT = 1/FPS


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def document(value):
    return (json.dumps(value, indent=2, allow_nan=False)+'\n').encode()


class Channel:
    """Output-device stand-in; selection, lease identity and expiry stay live."""
    def __init__(self):
        self.sound = None

    def get_sound(self):return self.sound
    def get_busy(self):return self.sound is not None
    def set_volume(self, *levels):pass
    def play(self, sound, **kwargs):self.sound = sound
    def stop(self):self.sound = None


def signature(actor):
    return {'position':list(actor.position), 'state':actor.state,
            'state_ms':actor.state_ms, 'water_units':actor.water_units,
            'pail_location':actor.pail_location,
            'mechanism':actor.well_snapshot.to_dict(),
            'well_events':[event.to_dict() for event in actor.well_events]}


class Recorder:
    def __init__(self, game):
        self.game = game
        self.actor = next(a for a in game.town.npcs if a.data['id']=='sanctuary_gardener')
        spec = pygame.mixer.get_init()
        if not spec or spec[1] != -16:
            raise AssertionError('Review needs the supported signed-16-bit dummy mixer')
        self.mixer_spec = list(spec)
        self.rate = spec[0]
        self.blocks = []
        self.sample_count = 0
        self.frame = 0
        self.voices = {}
        self.pcm = {}
        self.events = []
        self.trace = []
        self.markers = []
        self.silent_intervals = []
        self.examinations = []
        self.game.well_audio.observer = self.event

    @property
    def time(self):return self.sample_count/self.rate

    def event(self, action, key, **data):
        if action == 'start':self.voices[key] = {**data, 'offset':0}
        elif action == 'stop':self.voices.pop(key, None)
        elif key in self.voices:self.voices[key]['gain'] = data['gain']
        if action != 'gain':
            self.events.append({'time':self.time, 'action':action, 'key':key, **data})

    def mark(self, label):
        self.markers.append({'time':self.time, 'label':label,
            'listener_world':list(self.game.player.position),
            'scene':self.game.world.data['id'],
            'actor_state':self.actor.state,
            'mechanism_phase':self.actor.well_snapshot.phase_id,
            'voices':{key:{'gain':self.game.well_audio._gain(value[0]),
                            'source_world':list(value[0].point()),
                            'sound':value[0].sound}
                      for key,value in self.game.well_audio.voices.items()}})

    def run(self, seconds, direction=(0, 0)):
        for _ in range(round(seconds*FPS)):
            self.game.update(DT, direction, False)
            self.trace.append({'time':self.time,
                'listener_world':list(self.game.player.position),
                'scene':self.game.world.data['id'],
                'mechanism_phase':self.actor.well_snapshot.phase_id,
                'voices':{key:{'sound':voice[0].sound,
                                'source_world':list(voice[0].point()),
                                'gain':self.game.well_audio._gain(voice[0])}
                          for key,voice in self.game.well_audio.voices.items()}})
            endpoint = round((self.frame+1)*self.rate/FPS)
            block = np.zeros(endpoint-self.sample_count, dtype=np.float64)
            for voice in self.voices.values():
                name = voice['sound']
                if name not in self.pcm:
                    self.pcm[name] = np.array(samples(name, self.rate, 1), dtype=np.float64)
                    actual = np.frombuffer(self.game.well_audio._sound(name).get_raw(), dtype=np.int16)
                    actual = actual.reshape((-1, self.mixer_spec[2]))[:, 0]
                    if not np.array_equal(self.pcm[name], actual):
                        raise AssertionError('Offline source differs from live Sound PCM: '+name)
                pcm = self.pcm[name]
                indices = np.arange(len(block))+voice['offset']
                valid = np.ones(len(block), dtype=bool) if voice['ambient'] else indices<len(pcm)
                block[valid] += pcm[indices[valid]%len(pcm)]*voice['gain']
                voice['offset'] += len(block)
            self.blocks.append(block)
            self.sample_count = endpoint
            self.frame += 1

    def until(self, predicate, limit=120):
        for _ in range(round(limit*FPS)):
            if predicate():return
            self.run(DT)
        raise AssertionError('Review timed out at '+self.actor.state)

    def silent(self, label, seconds):
        self.mark(label)
        start = self.sample_count
        self.run(seconds)
        self.silent_intervals.append({'label':label, 'first_sample':start,
                                      'last_sample_exclusive':self.sample_count})

    def inspect(self, output, label):
        game = self.game
        before = signature(self.actor)
        if not game.well_examination.interact():
            raise AssertionError('Well examination unavailable at '+str(game.player.position))
        identifier = game.social.script_identifier
        game.update(0, (0, 0), False)
        game.camera.reset()
        game.draw()
        pygame.image.save(game.window, str(output/(label+'.png')))
        self.silent(label+' reading', 1.)
        after = signature(self.actor)
        if before != after:
            raise AssertionError('Reading the examination advanced or mutated work')
        self.examinations.append({'label':label, 'identifier':identifier,
                                  'work_unchanged':True, 'state':before})
        while game.social.active:game.social.advance()
        game.update(0, (0, 0), False)

    def write(self, path):
        values = np.concatenate(self.blocks) if self.blocks else np.zeros(0)
        rounded = np.rint(values)
        peak = float(np.max(np.abs(rounded)))/32768 if len(rounded) else 0.
        if peak >= 1:raise AssertionError('Review PCM clipped')
        for interval in self.silent_intervals:
            if np.any(rounded[interval['first_sample']:interval['last_sample_exclusive']]):
                raise AssertionError('Expected exact silence: '+interval['label'])
        with wave.open(str(path), 'wb') as out:
            out.setparams((1, 2, self.rate, 0, 'NONE', 'not compressed'))
            out.writeframes(rounded.astype('<i2').tobytes())
        finite = [event['key'] for event in self.events
                  if event['action']=='start' and not event['ambient']]
        if len(finite) != len(set(finite)):
            raise AssertionError('A finite accepted cue replayed during review')
        return {'sample_rate':self.rate, 'mixer_spec':self.mixer_spec,
                'channels':1, 'samples':len(rounded), 'seconds':len(rounded)/self.rate,
                'peak':peak, 'peak_dbfs':20*math.log10(peak) if peak else None,
                'exact_silence_intervals':self.silent_intervals,
                'accepted_finite_cue_count':len(finite), 'finite_keys_unique':True}


def review(output=OUTPUT):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    source_paths = ['main.py', 'npc_routines.py', 'well_audio.py', 'well_audio_samples.py',
                    'well_examination.py', 'regional_audio.py',
                    'gardener_well_runtime.py', 'well_routine.py',
                    'assets/story/well/inspection.json', 'tools/review_well_feedback.py']
    source_before = {path:digest(ROOT/path) for path in source_paths}
    preserved_paths = ['assets/maps/eldenmere/playable/map.json',
                       'assets/maps/eldenmere/routines/gardener.json']
    town = json.loads((ROOT/preserved_paths[0]).read_text())
    preserved_paths.append(town['collision'])
    preserved_before = {path:digest(ROOT/path) for path in preserved_paths}
    with tempfile.TemporaryDirectory(prefix='well-feedback-review-') as temporary, \
            patch('pygame.mixer.find_channel', side_effect=Channel):
        temporary = Path(temporary)
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                    save_path=temporary/'save.json', settings_path=temporary/'settings.json')
        game.audio.set_music(0)
        game.audio.set_effects(1)
        game.opening.stage = 'disabled'
        game.opening_fade = game.transfer_cooldown = 0
        game.player.position.update(492, 864)
        game.player.facing = 'right'
        actor = next(a for a in game.town.npcs if a.data['id']=='sanctuary_gardener')
        actor._rng = random.Random(2026)
        actor.rest_duration_ms = actor._new_rest_duration()
        recorder = Recorder(game)
        recorder.inspect(output, 'examine_idle')
        # Skip only the long rest and quiet outbound trip, using actual updates.
        game.player.position.update(520, 520)
        game.update(actor.rest_remaining_ms/1000+DT, (0, 0), False)
        for _ in range(120*FPS):
            if actor.well_snapshot.phase_id == 'attach':break
            game.update(DT, (0, 0), False)
        else:raise AssertionError('The gardener never reached attachment')
        game.player.position.update(492, 864)
        game.player.facing = 'right'
        recorder.mark('Listener enters the close western rim: distance 36')
        recorder.until(lambda:actor.well_snapshot.phase_id=='guide_into_shaft', 15)
        recorder.inspect(output, 'examine_working')
        recorder.mark('Natural departure west across the steep hearing boundary')
        recorder.run(1.5, (-1, 0))
        recorder.silent('Outside the 80-unit hearing radius', 1.)
        recorder.mark('Natural return east into the short hearing radius')
        recorder.run(1.5, (1, 0))
        recorder.until(lambda:actor.well_snapshot.phase_id=='raise', 15)
        game.pause.is_open = True
        recorder.silent('Pause menu', 1.)
        game.pause.close()
        game._music_focused = False
        recorder.silent('Focus loss', 1.)
        game._music_focused = True
        recorder.run(.5)
        game.audio.set_effects(0)
        recorder.silent('Effects mute', 1.)
        game.audio.set_effects(1)
        recorder.mark('Unmute resumes current looping work only')
        recorder.until(lambda:actor.well_snapshot.completed, 15)
        recorder.run(.75)
        recorder.mark('Diagnostic home-door transition releases well voices')
        door = next(d for d in game.town.doors if d.data['id']=='home_a')
        if not game.enter(door):raise AssertionError('Diagnostic interior transfer failed')
        recorder.silent('Interior visit', 1.)
        if not game.enter(game.world.doors[0]):raise AssertionError('Diagnostic town return failed')
        game.player.position.update(492, 864)
        game.player.facing = 'right'
        recorder.silent('Town return after completed work has no stale impacts', .75)
        game.well_audio.stop()
        # Keep the gardening sound local to its carried pail. Omit ordinary
        # travel from this labelled excerpt, never from the actor simulation.
        game.well_audio.observer = None
        game.player.position.update(520, 520)
        garden_excerpt_start_ms = game.elapsed_ms
        for _ in range(120*FPS):
            if actor.state.startswith('water_'):break
            game.update(DT, (0, 0), False)
        else:raise AssertionError('The gardener never reached the first flower bed')
        candidates = [actor.position+delta for delta in ((0, 36), (0, -36), (-36, 0), (36, 0))]
        listener = next((p for p in candidates if game.world.can_stand(p)), None)
        if listener is None:raise AssertionError('No safe near-bed listener station')
        game.player.position.update(listener)
        game.well_audio.observer = recorder.event
        recorder.mark('Garden-pour excerpt: listener follows the pail locality; travel omitted')
        recorder.run(2.6)
        game.well_audio.stop()
        mix = recorder.write(output/'well_feedback.wav')
        mix['omitted_garden_travel_game_ms'] = game.elapsed_ms-garden_excerpt_start_ms-2600
        material_blocks = []
        materials = []
        cursor = 0
        for name in DURATIONS:
            pcm = np.array(samples(name, recorder.rate, 1), dtype=np.float64)
            gain = .34
            materials.append({'sound':name, 'first_sample':cursor,
                              'last_sample_exclusive':cursor+len(pcm), 'gain':gain})
            material_blocks.extend([pcm*gain, np.zeros(round(recorder.rate*.15))])
            cursor += len(pcm)+round(recorder.rate*.15)
        material_pcm = np.rint(np.concatenate(material_blocks)).astype('<i2')
        with wave.open(str(output/'materials.wav'), 'wb') as out:
            out.setparams((1, 2, recorder.rate, 0, 'NONE', 'not compressed'))
            out.writeframes(material_pcm.tobytes())
        events = deepcopy(recorder.events)
        markers = deepcopy(recorder.markers)
        examinations = deepcopy(recorder.examinations)
        trace = deepcopy(recorder.trace)
        well_events = [event.to_dict() for event in actor.well_events]
        game.music.stop()
        pygame.quit()
    for relative, expected in source_before.items():
        if digest(ROOT/relative) != expected:
            raise AssertionError('Source changed during review: '+relative)
    for relative, expected in preserved_before.items():
        if digest(ROOT/relative) != expected:
            raise AssertionError('Review changed authored map/routine/collision: '+relative)
    report = {'method':__doc__,
              'revision':subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'runtime_activation':True, 'simulation_fps':FPS,
              'listener_fixtures':'Initial placement and diagnostic door transfers are explicit; outward/return falloff uses actual Game movement. The gardener is never teleported or advanced outside Game.update.',
              'garden_excerpt':'The first garden pour follows the same actual routine. Ordinary travel between the well and garden is omitted from the audio montage; the listener is diagnostically placed near that pail.',
              'material_montage':{'scope':'Original source-bank diagnostic, not a Game mix; fixed gain .34 with 150ms silence separators.',
                                   'sample_rate':recorder.rate, 'clips':materials},
              'distance_curve':{'near_logical':32, 'far_logical':80,
                  'relative_gain':[{'distance_logical':d, 'gain':well_distance_gain(d)}
                                   for d in (0, 32, 36, 48, 56, 64, 72, 80, 96)]},
              'mix':mix, 'markers':markers, 'events':events, 'examinations':examinations,
              'trace':trace, 'mechanism_events':well_events,
              'source_sha256':source_before, 'preserved_sha256':preserved_before,
              'artifacts_sha256':{p.name:digest(p) for p in sorted(output.iterdir())
                                  if p.suffix in ('.wav', '.png')}}
    (output/'observations.json').write_bytes(document(report))
    print(f'Well feedback review: {mix["seconds"]:.3f}s; peak {mix["peak_dbfs"]:.2f}dBFS; '
          f'{mix["accepted_finite_cue_count"]} accepted finite cues; exact silence verified.')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', type=Path, default=OUTPUT)
    review(parser.parse_args().output)
