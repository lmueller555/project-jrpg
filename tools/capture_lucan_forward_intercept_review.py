"""Review Lucan's forward shield interception and approved held orbit.

Preserve the previous held artwork/metadata and all camera/other-actor staging,
while allowing Lucan's interception position to move onto the incoming ray.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]

import numpy as np
import pygame
from PIL import Image, ImageDraw

from main import Game
from tools import capture_mira_prefire_review as helpers
from tools.capture_rhea_winter_cinematic import assert_close

OUTPUT = ROOT/'docs/reviews/lucan_forward_intercept_review'
START, END, FPS = 7., 11.4, 60
SNAPSHOTS = (7.5, 7.9, 8.3, 8.7, 9., 9.3, 9.7, 10.4, 10.8, 11.)
MANIFEST = 'assets/story/ice_reaper_continuity/actors/lucan/animation.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_staging(scene, expected):
    for key, value in dict(shot=scene.shot, camera=list(scene.camera_position),
                           zoom=scene.camera_zoom, brush=scene.brush_progress).items():
        assert_close(value, expected[key], key)
    if 'action' not in expected:
        return
    action = scene.action_stage.telemetry(scene.elapsed)
    for key in ('shot', 'camera_position', 'camera_target', 'focal'):
        if key in expected['action']:
            assert_close(action[key], expected['action'][key], f'action.{key}')
    for actor, position in expected['action'].get('positions', {}).items():
        if actor != 'lucan':
            assert_close(action['positions'][actor], position, f'positions.{actor}')


def geometry_checks(stage, baseline, shield_native=None, tolerance=3.):
    release = stage.first_shard_release()
    target = stage.first_shard_target()
    contact = stage.first_shard_shield_contact()
    foot = stage.lucan_guard_position()
    ray = target-release
    offset = contact-release
    fraction = offset.dot(ray)/ray.length_squared()
    ray_error = offset.cross(ray).length()/ray.length()
    impact_error = stage.first_shard_tip(9.).distance_to(contact)
    forward = stage._flat_direction(release-foot)
    forward_distance = (contact-foot).dot(forward)
    if ray_error > 1e-8 or not 0 < fraction < 1 or impact_error > 1e-8:
        raise AssertionError('Shield interception does not lie on the attack aimed at Rhea')
    if forward_distance <= 0:
        raise AssertionError('Lucan shield contact is behind his body rather than toward the attacker')
    for helper in ('first_shard_release',):
        assert_close(list(getattr(stage, helper)()), list(getattr(baseline, helper)()), helper)
    rhea = stage.actor_positions(9.)['rhea']
    target_height = target.y-rhea.y
    if abs(target.x-rhea.x) > .35 or abs(target.z-rhea.z) > .35 or not .1 <= target_height <= 1.9:
        raise AssertionError('The adjusted intended target must remain inside Rhea and her ice prison')
    path_error = 0.
    for frame in range(round(6.86*FPS), 541):
        tip = stage.first_shard_tip(frame/FPS)
        path_error = max(path_error, (tip-release).cross(ray).length()/ray.length())
    if path_error > 1e-8:
        raise AssertionError('The shard bends away from its attack line aimed into Rhea\'s prison')
    camera = stage.camera(9.)
    result = dict(release=list(release), intended_rhea_target=list(target),
                shield_contact=list(contact), lucan_foot=list(foot),
                attack_ray_fraction=fraction, ray_error=ray_error,
                projectile_contact_error_at_impact=impact_error,
                original_release_unchanged=True,
                previous_rhea_target=list(baseline.first_shard_target()),
                intended_target_shift=target.distance_to(baseline.first_shard_target()),
                intended_target_height_within_rhea=target_height,
                intended_target_remains_inside_rhea_prison=True,
                previous_shield_contact=list(baseline.first_shard_shield_contact()),
                shield_contact_shift=contact.distance_to(baseline.first_shard_shield_contact()),
                moving_shard_attack_line_error=path_error,
                shield_forward_of_body=forward_distance,
                projected_contact=list(camera.project(contact)))
    if shield_native is not None:
        position = stage.actor_positions(9.)['lucan']
        action, local, duration = stage._action('lucan', 9.)
        image, data = stage._sequence('lucan', action, local, duration,
                                      camera, position, time=9.)
        x, y = map(round, shield_native)
        if image.get_at((x, y)).a == 0:
            raise AssertionError('Authored shield contact landmark is transparent')
        foot_projection = camera.project(position)
        scale = camera.focal*1.85/foot_projection[2]/data['body_pixels']
        projected = [foot_projection[index]+(shield_native[index]-data['anchor'][index])*scale
                     for index in (0, 1)]
        contact_projection = camera.project(contact)
        error = pygame.Vector2(projected).distance_to(contact_projection[:2])
        if error > tolerance:
            raise AssertionError(f'Projectile misses the authored shield landmark by {error:.3f} native pixels')
        result.update(authored_shield_landmark_native=list(shield_native),
                      projected_art_landmark=projected, projectile_to_shield_art_error_pixels=error,
                      art_landmark_error_tolerance_pixels=tolerance)
    return result


def capture(output=OUTPUT, *, baseline_ref='HEAD', protected_hashes=None,
            shield_contact_native=None, shield_contact_tolerance=3.):
    output.mkdir(parents=True, exist_ok=True)
    Baseline, commit, baseline_source_hash = helpers.committed_action_stage(baseline_ref)
    old_manifest_bytes = subprocess.check_output(['git', 'show', f'{commit}:{MANIFEST}'], cwd=ROOT)
    old_manifest = json.loads(old_manifest_bytes)
    original_holds = {key:entry for key,entry in old_manifest['animations'].items()
                      if key.startswith('hold_brace_')}
    current_manifest = json.loads((ROOT/MANIFEST).read_text())
    current_holds = {key:entry for key,entry in current_manifest['animations'].items()
                     if key.startswith('hold_brace_')}
    if current_holds != original_holds:
        raise AssertionError('Approved held orbit animation entries changed')
    protected = json.loads(Path(protected_hashes).read_text()) if protected_hashes else {}
    if protected != {name: digest(ROOT/name) for name in protected}:
        raise AssertionError('A protected asset changed before capture')
    source_names = ('ice_reaper_action.py', 'ice_reaper_opening.py', 'opening_cinematic.py',
                    'ice_reaper_audio.py', 'tools/capture_lucan_forward_intercept_review.py',
                    'tools/capture_mira_prefire_review.py', 'tools/build_lucan_guard_correction.py')
    sources = {name: digest(ROOT/name) for name in source_names}
    assets = {str(path.relative_to(ROOT)): digest(path)
              for folder in ('assets/story/ice_reaper_continuity/actors/lucan',
                             'assets/source/cinematics/lucan_forward_guard')
              for path in sorted((ROOT/folder).rglob('*')) if path.is_file()}
    manifest_hash = digest(ROOT/MANIFEST)
    reference_path = ROOT/'assets/source/cinematics/ice_reaper_continuity/staging_reference.json'
    reference = json.loads(reference_path.read_text())
    timeline, snapshots, sprite_snapshots = [], [], []
    sample_frames = {round((time-START)*FPS): time for time in SNAPSHOTS}
    frames = round((END-START)*FPS)

    with tempfile.TemporaryDirectory(prefix='lucan-forward-intercept-review-') as folder:
        folder = Path(folder)
        parent = Game(window_size=(960, 800), fullscreen=False, start_on_title=True,
                      save_path=folder/'journey.json', settings_path=folder/'settings.json')
        try:
            parent.audio.set_music(1.)
            parent.audio.set_effects(1.)
            parent.audio._save()
            settings = (folder/'settings.json').read_bytes()
            assert parent.open_gallery() and parent.launch_gallery_scene('ice_reaper_opening')
            child = parent.gallery_session.game
            scene = child.opening_cinematic
            scene.elapsed = START
            stage = scene.action_stage
            frozen = (child._progress_signature(), child.elapsed_ms, tuple(child.player.position))
            video = folder/'video.mp4'
            command = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                       '-s', '960x640', '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264',
                       '-preset', 'medium', '-crf', '20', '-threads', '2', '-pix_fmt', 'yuv420p', str(video)]
            with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
                for frame in range(frames):
                    time = START+frame/FPS
                    scene.elapsed = time
                    parent.draw()
                    encoder.stdin.write(pygame.image.tobytes(child.ui_surface, 'RGB'))
                    if frozen != (child._progress_signature(), child.elapsed_ms, tuple(child.player.position)):
                        raise AssertionError('Review changed the ordinary world')
                    story_time = stage.story_time(time)
                    camera = stage.camera(story_time)
                    position = stage.actor_positions(story_time)['lucan']
                    action, local, duration = stage._action('lucan', story_time)
                    key = stage.sequence_key('lucan', action, local, duration, camera, position, story_time)
                    image, _ = stage._sequence('lucan', action, local, duration, camera, position, time=story_time)
                    timeline.append(dict(frame=frame, time=time, shot=scene.shot,
                        dialogue=scene.dialogue['text'] if scene.dialogue else None,
                        lucan_action=action, lucan_view=key,
                        lucan_azimuth=stage.view_angles('lucan', camera, position, story_time)[0],
                        camera_position=list(camera.position), camera_target=list(camera.target), focal=camera.focal))
                    if frame in sample_frames:
                        label = f'{sample_frames[frame]:05.2f}'
                        name = f'{label}_scene.png'
                        pygame.image.save(child.ui_surface, str(output/name))
                        snapshots.append(name)
                        name = f'{label}_sprite.png'
                        pygame.image.save(image, str(output/name))
                        sprite_snapshots.append(name)
                encoder.stdin.close()
                if encoder.wait():
                    raise RuntimeError('Review encoding failed')
            music_gain = pygame.mixer.music.get_volume()
            effects_gain = child.audio.effects_volume
            # Reuse the exact audio reconstruction helper with this excerpt's
            # explicit boundaries. This is an isolated offline process.
            prior_start, prior_end = helpers.START, helpers.END
            try:
                helpers.START, helpers.END = START, END
                cues = helpers.audio_segment(video, output/'preview.mp4', music_gain, effects_gain)
            finally:
                helpers.START, helpers.END = prior_start, prior_end

            # The interception may intentionally move Lucan onto the incoming
            # ray. Every other actor and the full camera path remain fixed.
            for record in reference['timeline']:
                scene.elapsed = record['scene_time']
                validate_staging(scene, record)
            geometry = geometry_checks(stage, Baseline, shield_contact_native, shield_contact_tolerance)
            if (folder/'journey.json').exists() or (folder/'settings.json').read_bytes() != settings:
                raise AssertionError('Review changed save/settings files')
        finally:
            if parent.gallery_session is not None:
                parent.gallery_session.close(resume_music=False)
            parent.music.stop()
            pygame.quit()

    if sources != {name: digest(ROOT/name) for name in sources}:
        raise AssertionError('Runtime changed during capture')
    if manifest_hash != digest(ROOT/MANIFEST):
        raise AssertionError('Lucan directional metadata changed during capture')
    if protected != {name: digest(ROOT/name) for name in protected}:
        raise AssertionError('A protected asset changed during capture')
    if assets != {name: digest(ROOT/name) for name in assets}:
        raise AssertionError('Lucan art changed during capture')
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                       '-show_format', '-of', 'json', str(output/'preview.mp4')]))
    stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    if int(stream['nb_frames']) != frames or abs(float(stream['duration'])-(END-START)) > .001:
        raise AssertionError('Review excerpt has the wrong duration/frame count')
    audio = np.frombuffer(subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(output/'preview.mp4'),
                            '-vn', '-ar', '48000', '-ac', '2', '-f', 'f32le', '-']), dtype='<f4')
    if not np.isfinite(audio).all() or np.any(np.abs(audio) >= 1):
        raise AssertionError('Review audio is invalid or clipped')
    helpers.contact(output, snapshots, 'scene_contact.png')
    helpers.contact(output, sprite_snapshots, 'sprite_contact.png', sprites=True)
    drawings = ROOT/'docs/reviews/lucan_forward_guard/native_contact_sheet.png'
    if drawings.exists():
        shutil.copyfile(drawings, output/'native_drawings.png')
    if 'projected_art_landmark' in geometry:
        diagnostic = Image.open(output/'09.00_scene.png').convert('RGB')
        draw = ImageDraw.Draw(diagnostic)
        x, y = (value*2 for value in geometry['projected_art_landmark'])
        draw.ellipse((x-9, y-9, x+9, y+9), outline='#4dff8a', width=2)
        x, y = (value*2 for value in geometry['projected_contact'][:2])
        draw.line((x-7, y, x+7, y), fill='#ffd16b', width=2)
        draw.line((x, y-7, x, y+7), fill='#ffd16b', width=2)
        draw.rectangle((12, 12, 430, 36), fill='#14232c')
        draw.text((20, 18), 'Gold: projectile impact | Green: authored shield rim', fill='white')
        diagnostic.save(output/'impact_geometry.png', optimize=True)
    report = dict(version=1, segment=[START, END], fps=FPS, frames=frames,
        baseline_ref=commit, baseline_action_source_sha256=baseline_source_hash,
        baseline_lucan_manifest_sha256=hashlib.sha256(old_manifest_bytes).hexdigest(),
        current_lucan_manifest_sha256=manifest_hash,
        runtime_sources=sources, art_asset_hashes=assets, protected_asset_hashes=protected,
        save_and_settings_unchanged=True,
        full_scene_camera_and_blocking=dict(frames=1920, unchanged=True,
            reference=str(reference_path.relative_to(ROOT)), reference_sha256=digest(reference_path)),
        approved_held_orbit=dict(animation_entries_unchanged=True, views=original_holds),
        interception_geometry=geometry,
        music=dict(file=str(helpers.MUSIC.relative_to(ROOT)), sha256=digest(helpers.MUSIC),
                   rendered_gain=music_gain, segment=[START, END]),
        effects_settings_gain=effects_gain, effects=cues,
        audio_capture_method='Reconstructed runtime score/SFX; SDL dummy has no loopback',
        audio_peak=float(np.max(np.abs(audio))), audio_clipped_samples=0,
        snapshots=snapshots, sprite_snapshots=sprite_snapshots, timeline=timeline,
        preview_sha256=digest(output/'preview.mp4'))
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(segment=report['segment'], frames=frames, fps=FPS,
                         camera_frames_checked=1920, approved_held_views=len(original_holds),
                         video_bytes=(output/'preview.mp4').stat().st_size)))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--baseline-ref', default='HEAD', help='Commit before the forward interception correction')
    parser.add_argument('--protected-hashes', type=Path)
    parser.add_argument('--shield-contact-native', type=float, nargs=2,
                        help='Authored shield rim landmark on the first impact drawing')
    parser.add_argument('--shield-contact-tolerance', type=float, default=3.)
    args = parser.parse_args()
    capture(args.output.resolve(), baseline_ref=args.baseline_ref, protected_hashes=args.protected_hashes,
            shield_contact_native=args.shield_contact_native,
            shield_contact_tolerance=args.shield_contact_tolerance)
