"""Capture one actual MQ02 Bolt Shot after playing New Game and its lesson.

No quest/stat/unlock seeding, elapsed assignment, or preview battle. Production
inputs drive the existing opening walkthrough, then precise update deltas sample
one ordinary Mira Attack. Separate invocations capture normal and Reduced Motion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
from contextlib import nullcontext
from types import ModuleType
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
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
import pygame
from PIL import Image, ImageDraw
import numpy as np
from battle_action_audio import BattleActionAudio
import test_opening_dialogue_pass as opening
from test_mill_battle_gameplay import key, click

SAMPLES = (0., .10, .20, .279, .28, .295, .31, .325, .34, .355, .37, .385,
           .399, .4, .416, .44, .456, .49, .55, .6, .65, .72, .8, .88, .95, 1.05)


class Captured(Exception):pass


def capture(output, reduced_motion=False, baseline_ref=None):
    output.mkdir(parents=True, exist_ok=True)
    driver = opening.OpeningDialogueDriver()
    game = driver.g
    game.audio.set_reduced_motion(reduced_motion)
    records, video, sounds, review_cues = [], [], [], []
    lesson = {}
    baseline_commit = None
    baseline_patch = nullcontext()
    if baseline_ref:
        import world_encounters
        baseline_commit = subprocess.check_output(['git', 'rev-parse', baseline_ref], cwd=ROOT, text=True).strip()
        source = subprocess.check_output(['git', 'show', f'{baseline_commit}:battle_scene.py'], cwd=ROOT)
        module = ModuleType('_bolt_impact_baseline_scene')
        module.__file__ = str(ROOT/'battle_scene.py')
        exec(compile(source, module.__file__, 'exec'), module.__dict__)
        baseline_patch = patch.object(world_encounters, 'BattleScene', module.BattleScene)
    source_files = ('battle_scene.py', 'mira_combat_art.py', 'bolt_shot_fx.py',
                    'assets/combat/mira/animation.json', 'assets/combat/ridgeback_tusker/animation.json',
                    'assets/combat/actions.json', 'battle_model.py', 'battle_action_audio.py',
                    'assets/audio/sfx/mira_bolt_shot/bolt_impact.wav', 'tools/capture_mira_bolt_impact.py')
    hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
              for name in source_files if (ROOT/name).exists()}
    if baseline_ref:hashes['battle_scene.py'] = hashlib.sha256(source).hexdigest()

    def shot(scene):
        action = scene.model.current_action
        lesson.update(stage=scene.model.spellblade_stage,
                      aether_edge_discovered=scene.model.aether_edge_discovered)
        assert lesson == dict(stage='complete', aether_edge_discovered=True)
        before_hp = scene.model.enemy.hp
        cue_start = len(sounds)
        world = game.elapsed_ms, tuple(game.player.position), tuple(game.mill_quest.mira.position)
        last = 0.
        sample_clocks = {round(t, 6) for t in SAMPLES}
        video_clocks = {round(frame/60, 6) for frame in range(64)}
        for time in sorted(sample_clocks | video_clocks):
            game.update(time-last, (0, 0), False);last = time
            game.draw()
            if round(time, 6) in video_clocks:
                video.append(Image.frombytes('RGB', game.ui_surface.get_size(),
                                              pygame.image.tobytes(game.ui_surface, 'RGB')))
            if time not in sample_clocks:continue
            filename = f'{round(time*1000):03d}ms.png'
            pygame.image.save(game.ui_surface, str(output/filename))
            geometry = scene._mira_shot()
            record = scene._reactions.get('enemy')
            positions = scene._ground_positions()
            records.append(dict(file=filename, elapsed=time, actual_elapsed=action.elapsed,
                resolved=action.resolved, enemy_hp=scene.model.enemy.hp,
                projectile=geometry['projectile'] if geometry else None,
                origin=geometry['origin'] if geometry else None,
                target=geometry['target'] if geometry else None,
                enemy_floor=list(positions['enemy']), mira_floor=list(positions['mira']),
                enemy_pose=list(scene._pose('enemy')), camera=scene._camera(),
                observed_reduced_motion=scene.reduced_motion,
                reaction=record.copy() if record else None))
        assert (action.action, action.impact_at, action.duration) == ('bolt_shot', .4, .8)
        assert all(r['enemy_hp'] == before_hp for r in records if r['elapsed'] < .4)
        impacted = [r for r in records if r['elapsed'] >= .4]
        assert impacted[0]['resolved'] and impacted[0]['enemy_hp'] < before_hp
        assert len({r['enemy_hp'] for r in impacted}) == 1
        assert all(r['projectile'] is None for r in impacted)
        assert world == (game.elapsed_ms, tuple(game.player.position), tuple(game.mill_quest.mira.position))
        review_cues.extend(cue for cue in sounds[cue_start:] if cue['action'] == 'bolt_shot')
        raise Captured()

    def battle(game, *args, **kwargs):
        scene, model = game.combat.scene, game.combat.model
        assert game.combat.kind == 'mill' and model.enemy_id == 'ridgeback_tusker'
        assert [m.name for m in model.party] == ['Caelan', 'Mira']
        game.audio.set_reduced_motion(reduced_motion)
        assert scene.reduced_motion == reduced_motion
        model.rng = random.Random(7)
        original_play = scene.action_audio.play
        def play(cue):
            action = model.current_action
            sounds.append(dict(cue=cue, elapsed=action.elapsed if action else None,
                               action=action.action if action else None))
            original_play(cue)
        scene.action_audio.play = play
        for _ in range(8000):
            if game.combat.transitioning:game.update(.05, (0, 0), False);continue
            if scene.tutorial_active:key(game, pygame.K_SPACE)
            elif model.ended:raise AssertionError('MQ02 ended before an ordinary Mira Attack')
            elif model.waiting_for_player:
                game.draw()
                if model.spellblade_stage in ('opening', 'guard', 'charge'):
                    click(game, scene.command_rects['guard'].center)
                elif model.spellblade_stage == 'first_edge':
                    click(game, scene.command_rects['skills'].center);game.draw()
                    click(game, scene.command_rects['aqua_edge'].center)
                elif model.ready_actor == 'mira':
                    click(game, scene.command_rects['attack'].center)
                    assert model.current_action.action == 'bolt_shot'
                    return shot(scene)
                elif model.telegraphed_target == model.ready_actor:
                    click(game, scene.command_rects['guard'].center)
                elif not model.action_reason('aether_edge'):
                    click(game, scene.command_rects['skills'].center);game.draw()
                    click(game, scene.command_rects['aether_edge'].center)
                else:click(game, scene.command_rects['attack'].center)
            else:game.update(.01, (0, 0), False)
        raise AssertionError('MQ02 did not reach Mira Bolt Shot')

    try:
        with baseline_patch, patch.object(opening, 'finish_mill_battle', battle):
            try:driver.run()
            except Captured:pass
        assert records and video
        assert all(r['observed_reduced_motion'] == reduced_motion for r in records)
        # Keep native runtime pixels in PNGs. Pillow only arranges rendered
        # screenshots and quantizes an unretimed 60 fps clip for review.
        # Reconstruct only the observed action's SFX through the production
        # cue loader at unity effects setting. No soundtrack or invented cue.
        # The journey itself stays muted for deterministic headless execution.
        with tempfile.TemporaryDirectory(prefix='bolt-impact-audio-') as folder:
            from types import SimpleNamespace
            player = BattleActionAudio(SimpleNamespace(audio=SimpleNamespace(effects_volume=1.)))
            if not pygame.mixer.get_init():pygame.mixer.init(frequency=44100, size=-16, channels=2)
            rate, sample_format, channels = pygame.mixer.get_init()
            assert sample_format == -16
            mix = np.zeros((round(len(video)/60*rate), channels), dtype=np.float64)
            for cue in review_cues:
                player.play(cue['cue'])
                sound = player._sounds[cue['cue']]
                pcm = np.frombuffer(sound.get_raw(), dtype='<i2').reshape((-1, channels))
                start = round(cue['elapsed']*rate)
                count = min(len(pcm), len(mix)-start)
                if count > 0:mix[start:start+count] += pcm[:count]*sound.get_volume()
            player.stop()
            assert np.max(np.abs(mix)) < 32767
            path = Path(folder)/'effects.wav'
            with wave.open(str(path), 'wb') as wav:
                wav.setparams((channels, 2, rate, 0, 'NONE', 'not compressed'))
                wav.writeframes(np.rint(mix).astype('<i2').tobytes())
            process = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                '-s', f'{video[0].width}x{video[0].height}', '-r', '60', '-i', '-', '-i', str(path),
                '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k',
                '-shortest', '-movflags', '+faststart', str(output/'bolt_shot.mp4')], stdin=subprocess.PIPE)
            for frame in video:process.stdin.write(frame.tobytes())
            process.stdin.close()
            if process.wait():raise AssertionError('Video encode failed')
        # Alternating 10/20 ms delays preserve total speed in centisecond GIF.
        small = [im.resize((480, 320), Image.Resampling.NEAREST) for im in video]
        palette = small[len(small)//2].quantize(colors=256, dither=Image.Dither.NONE)
        small = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in small]
        delays = [10*(round((i+1)*100/60)-round(i*100/60)) for i in range(len(small))]
        small[0].save(output/'bolt_shot.gif', save_all=True, append_images=small[1:],
                      duration=delays, loop=0, disposal=1, optimize=False)
        small[0].save(output/'bolt_shot_slow.gif', save_all=True, append_images=small[1:],
                      duration=[delay*2 for delay in delays], loop=0, disposal=1, optimize=False)
        chosen = (.279, .28, .34, .399, .4, .44, .49, .6, .95)
        sheet = Image.new('RGB', (480*3, 344*3), '#172b2b');draw = ImageDraw.Draw(sheet)
        for i, time in enumerate(chosen):
            x,y = i%3*480, i//3*344
            draw.text((x+6,y+5), f'{time:.3f}s', fill='white')
            im = Image.open(output/f'{round(time*1000):03d}ms.png').convert('RGB')
            sheet.paste(im.resize((480,320),Image.Resampling.NEAREST),(x,y+24))
        sheet.save(output/'contact.png')
        (output/'verification.json').write_text(json.dumps(dict(
            unseeded_new_game=True, production_mq02=True, normal_player_files_untouched=True,
            reduced_motion=reduced_motion, baseline_scene_commit=baseline_commit, git_commit=subprocess.check_output(
                ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), runtime_hashes=hashes,
            source_dialogue_pages=len(driver.pages), lesson=lesson, cues=sounds, review_cues=review_cues,
            preview_audio="Observed production SFX at unity effects volume; no music",
            samples=records, fps=60, frames=len(video)), indent=2)+'\n')
    finally:driver.close()
    print(json.dumps({'output':str(output),'samples':len(records),'reduced_motion':reduced_motion}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reduced-motion', action='store_true')
    parser.add_argument('--baseline-ref', help='Render actual encounter with BattleScene from this committed base')
    args=parser.parse_args();capture(args.output,args.reduced_motion,args.baseline_ref)
