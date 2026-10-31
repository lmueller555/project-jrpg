"""Record interrupted mill diagnosis recovery with the production Game renderer.

Only MQ01 prerequisites use the existing fixture. MQ02 inspections, cancellation,
Continue, diagnosis, warning, north-road transfer and arrival pan use real input
and controller updates. The short route between the mill and final approach is
omitted from the video; no movement or quest facts are replaced for recording.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import pygame
from test_millrace_departure import MillraceDepartureTests
from test_mill_battle_gameplay import key

FPS = 20


class Capture:
    def __init__(self, output):
        self.output = output
        self.driver = MillraceDepartureTests('runTest')
        self.encoder = None
        self.recording = True
        self.frames = 0
        self.remainder = 0.0
        self.events = []
        self.screenshots = []
        self.pages = []

    @property
    def game(self):return self.driver.g

    @property
    def quest(self):return self.driver.c

    @property
    def seconds(self):return self.frames/FPS

    def mark(self, event, **values):
        self.events.append(dict(time=round(self.seconds, 3), event=event, **values))

    def observed_state(self):
        game, quest = self.game, self.quest
        return dict(scene=game.world.data['id'], player=list(game.player.position),
                    mira=list(quest.mira.position), stage=quest.stage,
                    inspected=sorted(quest.inspected), warned=quest.warned,
                    diagnose_completed=quest._done('diagnose_mill'),
                    warning_completed=quest._done('prepare_journey'),
                    encounter_cleared=quest.encounter_cleared,
                    intake_inspected='intake' in quest.inspected,
                    script=game.social.script_identifier,
                    cutscene_phase=quest.encounter_cutscene_phase)

    def snapshot(self, filename):
        self.game.draw()
        pygame.image.save(self.game.window, str(self.output/filename))
        self.screenshots.append(dict(file=filename, time=round(self.seconds, 3),
                                     state=self.observed_state()))

    def frame(self, game, seconds):
        if not self.recording:return
        self.remainder += max(0.0, seconds)
        while self.remainder+1e-9 >= 1/FPS:
            self.remainder -= 1/FPS
            game.draw()
            assert game.window.get_size() == self.size
            self.encoder.stdin.write(pygame.image.tobytes(game.window, 'RGB'))
            self.frames += 1

    def hold(self, seconds):
        for _ in range(round(seconds*FPS)):
            self.driver.tick(1/FPS)

    def until(self, predicate, label):
        for _ in range(20*FPS):
            if predicate():return
            self.driver.tick(1/FPS)
        raise AssertionError('Timed out: '+label)

    def read_departure_dialogues(self):
        seen = set()
        while self.game.social.active:
            social = self.game.social
            assert social.script_identifier in ('mill_diagnosis', 'mill_warning')
            identity = social.script_identifier, social.page_index
            assert identity not in seen, 'Departure dialogue failed to advance'
            seen.add(identity)
            text = ' '.join(social.page['lines'])
            duration = max(1.8, len(text.split())/3.0+.4)
            self.pages.append(dict(time=round(self.seconds, 3), script=identity[0],
                                   page=identity[1], text=text,
                                   hold_seconds=round(duration, 3)))
            if identity[0] == 'mill_warning' and identity[1] == 0:
                assert self.quest._done('diagnose_mill') and not self.quest.warned
                self.mark('warning_started')
                self.snapshot('warning.png')
            self.hold(duration)
            key(self.game, pygame.K_SPACE)

    def sequence(self):
        self.mark('directions_visible_before_final_acknowledgement', **self.observed_state())
        self.snapshot('directions.png')
        self.hold(max(2.4, len(' '.join(self.game.social.page['lines']).split())/3.0+.4))
        key(self.game, pygame.K_SPACE)
        assert self.game.social.page['source_line'] == len(self.quest.lines['diagnosis'])-1
        self.hold(1.8)
        # The ordinary walk cancels the unacknowledged directions. Omit its long
        # middle stretch, retaining the final approach and visible prompt change.
        self.recording = False
        self.driver.walk((720, 156))
        self.recording = True
        assert not self.game.social.locked
        assert self.quest.inspected == {'mechanism', 'race'}
        assert not self.quest._done('diagnose_mill')
        self.mark('cut_to_final_walking_approach', **self.observed_state())
        self.hold(.4)
        self.driver.north()
        assert self.quest.interaction_hint() == 'E: Discuss the mill with Mira'
        assert not self.game.travel_link(self.game.nearby_world_link())
        self.hold(.6)
        self.mark('north_prompt_recovers_pending_diagnosis', hint=self.quest.interaction_hint())
        self.snapshot('recovery_prompt.png')
        self.hold(1.6)

        saved = self.driver.continue_save()
        assert self.quest.to_dict() == saved['mill_quest']
        assert self.quest.interaction_hint() == 'E: Discuss the mill with Mira'
        self.mark('continue_preserved_pending_diagnosis', **self.observed_state())
        self.snapshot('continue_recovery.png')
        self.hold(1.2)
        key(self.game, pygame.K_e)
        assert self.game.social.script_identifier == 'mill_diagnosis'
        self.mark('north_e_resumed_diagnosis')
        self.read_departure_dialogues()
        assert self.quest.warned and self.quest._done('prepare_journey')
        assert self.quest.can_enter_upstream()
        assert self.quest.interaction_hint() == ''
        self.mark('departure_warning_acknowledged', **self.observed_state())
        self.snapshot('travel_prompt.png')
        self.hold(1.8)

        mira = self.quest.mira
        self.driver.enter()
        self.mark('north_e_entered_upstream', **self.observed_state())
        self.until(lambda: self.quest.encounter_cutscene_phase == 'noticing', 'Mira joining upstream')
        assert self.quest.mira is mira
        assert sum(mira in world.npcs for world in self.game.scenes.values()) == 1
        self.snapshot('upstream.png')
        self.until(lambda: self.quest.encounter_cutscene_phase == 'conversation', 'arrival pan')
        assert self.game.social.script_identifier == 'mill_encounter_intro'
        assert not self.quest.combat_unlocked and not self.game.combat.active
        assert 'intake' not in self.quest.inspected
        self.mark('arrival_pan_reached_encounter', **self.observed_state())
        self.snapshot('arrival_pan.png')
        self.hold(2.8)

    def write_metadata(self):
        sources = ('mill_quest.py', 'main.py', 'tests/test_millrace_departure.py',
                   'tests/test_mill_trigger_geometry.py', 'tools/capture_millrace_departure.py')
        metadata = dict(game_integration=True, renderer='Production Game.draw() and game.window',
                        source_base_commit=subprocess.check_output(
                            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                        source_sha256={name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                                       for name in sources},
                        video='millrace_departure.mp4', video_fps=FPS,
                        video_frames=self.frames, duration_seconds=self.seconds,
                        video_size=list(self.size), soundtrack='Silent; SDL dummy capture, no audio reconstruction.',
                        temporary_journey_and_settings=True, normal_player_files_untouched=True,
                        fixture='Existing geometry fixture completes MQ01 through public quest APIs. '
                                'MQ02 uses actual recruitment, inspections and dialogue callbacks. '
                                'The north approach, Continue, recovery and transfer use production input and movement.',
                        video_edit='One cut omits the middle walk from the mill to (720, 156); '
                                   'that walk still executes normally and cancels the unacknowledged diagnosis.',
                        events=self.events, dialogue_pages=self.pages,
                        screenshots=self.screenshots, final_state=self.observed_state())
        (self.output/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n')
        (self.output/'README.md').write_text('''# Millrace north-departure recovery

[Watch the actual-game recovery and upstream arrival](millrace_departure.mp4).

The recording first shows the diagnosis directions before their final
acknowledgement. Walking away cancels that unfinished dialogue. After one cut
that omits the middle of the walk, Caelan walks the final approach to the north
exit. The prompt offers to discuss the mill with Mira. A real title-menu Continue
preserves that pending diagnosis. E resumes the diagnosis; the complete diagnosis
and practical warning play at approximately three words per second. Once the
warning is acknowledged, E transfers to the upper millrace and the existing
arrival camera pans to the encounter.

![Recovery at the north prompt](recovery_prompt.png)
![Practical warning before departure](warning.png)
![Both actors arrive upstream](upstream.png)

All video frames and screenshots come from production `Game.draw()` at 960×640.
The 20 FPS video is silent. The disposable fixture completes only MQ01 through
public quest APIs; MQ02 progress comes from real interactions and callbacks.
No regular player save or settings files are used. The video stops before combat,
with the intake still uninspected and the encounter still uncleared.

The [verification record](verification.json) includes observed quest states,
dialogue timing, Continue results, source hashes and the source base commit.

Reproduce from the repository root with the project Python environment:

```sh
python tools/capture_millrace_departure.py --output docs/reviews/millrace_departure
```
''')

    def run(self):
        self.output.mkdir(parents=True, exist_ok=True)
        self.driver.setUp()
        try:
            # Stop one page earlier than diagnosis_directions() so the opening
            # screenshot shows the actual north-road instruction. Ordinary
            # Space input reaches the final acknowledgement during recording.
            self.driver.race_directions()
            while self.game.social.script_identifier != 'mill_diagnosis':
                key(self.game, pygame.K_SPACE)
            while self.game.social.page['source_line'] < len(self.quest.lines['diagnosis'])-2:
                key(self.game, pygame.K_SPACE)
            assert self.quest.inspected == {'mechanism', 'race'}
            assert not self.quest._done('diagnose_mill')
            self.size = self.game.window.get_size()
            self.encoder = subprocess.Popen([
                'ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                '-video_size', f'{self.size[0]}x{self.size[1]}', '-framerate', str(FPS),
                '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '26',
                '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                str(self.output/'millrace_departure.mp4')], stdin=subprocess.PIPE)
            game_type = type(self.game)
            original_update = game_type.update
            def update(game, seconds, *args, **kwargs):
                result = original_update(game, seconds, *args, **kwargs)
                self.frame(game, seconds)
                return result
            with patch.object(game_type, 'update', update):
                self.sequence()
            self.encoder.stdin.close()
            assert self.encoder.wait() == 0, 'Video encoding failed'
            self.write_metadata()
            print(json.dumps(dict(output=str(self.output), frames=self.frames,
                                  seconds=self.seconds,
                                  video_bytes=(self.output/'millrace_departure.mp4').stat().st_size)))
        finally:
            if self.encoder is not None and self.encoder.poll() is None:
                if not self.encoder.stdin.closed:self.encoder.stdin.close()
                self.encoder.wait()
            self.driver.doCleanups()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'docs/reviews/millrace_departure')
    Capture(parser.parse_args().output).run()
