"""The Ice Reaper rescue: a deterministic, perspective-projected pixel stage.

All actors, contacts, debris and the ground rune share one world.  The camera
moves around that world; authored scenic plates supply the distant landscape.
The caller owns the real-time clock, dialogue, music and playback lifecycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import math
from pathlib import Path

import pygame
import numpy as np

SIZE = (480, 320)
V3 = pygame.Vector3
TAU = math.tau


def clamp(value, low=0., high=1.):
    return max(low, min(high, value))


def smooth(value):
    value = clamp(value)
    return value*value*(3-2*value)


def phase(time, start, end):
    return clamp((time-start)/(end-start))


def lerp(a, b, amount):
    return V3(a).lerp(V3(b), clamp(amount))


@dataclass(frozen=True)
class PerspectiveCamera:
    position: tuple
    target: tuple
    focal: float = 245.
    center: tuple = (240., 158.)

    def basis(self):
        forward = (V3(self.target)-V3(self.position)).normalize()
        right = forward.cross(V3(0, 1, 0)).normalize()
        up = right.cross(forward).normalize()
        return right, up, forward

    def project(self, point):
        right, up, forward = self.basis()
        relative = V3(point)-V3(self.position)
        depth = relative.dot(forward)
        if depth <= .12:
            return None
        return (self.center[0]+relative.dot(right)*self.focal/depth,
                self.center[1]-relative.dot(up)*self.focal/depth, depth)


SHOTS = (
    (5., 7., 'reaper_launch'), (7., 7.5, 'rescue_dash'),
    (7.5, 9.5, 'slow_motion_rescue'), (9.5, 11., 'rescue_orbit'),
    (11., 12.8, 'mira_loading'), (12.8, 14.2, 'launcher_sight'),
    (14.2, 15.1, 'second_shard_intercept'), (15.1, 16.3, 'rhea_awakens'),
    (16.3, 16.95, 'prison_release'), (16.95, 19.25, 'rune_panorama'),
    (19.25, 20., 'rune_hold'))


class IceReaperActionStage:
    """Render 5–21 seconds over the preserved 20-second choreography clock."""

    def __init__(self, asset_root, *, strict=False):
        self.asset_root = Path(asset_root)
        self.repository = Path(__file__).resolve().parent
        self.opening = self.repository/'assets/story/ice_reaper_opening'
        self.continuity_root = self.asset_root.parent/'ice_reaper_continuity'
        self.images = {}
        self.actors = {}
        self.missing_assets = []
        self._scaled = {}
        self._load()
        if strict:
            self.validate_assets()

    def _read_image(self, path):
        path = Path(path)
        if path not in self.images:
            self.images[path] = pygame.image.load(str(path)).convert_alpha()
        return self.images[path]

    def _load(self):
        required = {
            'caelan': ('ready', 'dash', 'slash', 'land'),
            'lucan': ('dash', 'brace', 'impact'),
            'mira': ('raise', 'load', 'aim', 'fire'),
            'rhea': ('release',),
            'ice_reaper': ('aim', 'launch', 'recharge')}
        for actor, actions in required.items():
            folder = self.asset_root/'actors'/actor
            path = folder/'animation.json'
            if path.exists():
                manifest = json.loads(path.read_text())
                sequences = {}
                for key, entry in manifest['animations'].items():
                    frames = entry['frames'] if isinstance(entry, dict) else entry
                    sequences[key] = [(self._read_image(folder/frame['file']),
                                       frame.get('duration_ms', 100)/1000)
                                      for frame in frames]
                    if not sequences[key]:
                        raise ValueError(f'Empty rescue action: {actor}/{key}')
                anchor = tuple(manifest['anchor'])
                nominal = manifest.get('body_pixels', 155 if actor == 'ice_reaper' else 82)
                self.actors[actor] = dict(sequences=sequences, anchor=anchor,
                                          body_pixels=nominal, manifest=manifest)
                for action in actions:
                    if action not in sequences:
                        self.missing_assets.append(f'{actor}/{action}')
            else:
                self.missing_assets.append(f'{actor}/animation.json')
                if actor == 'ice_reaper':
                    source = self.opening/'actors/ice_reaper/charge.png'
                    image = self._read_image(source)
                    anchor = (image.get_width()/2, image.get_height()-8)
                else:
                    folder = self.repository/'assets/combat'/actor
                    manifest = json.loads((folder/'animation.json').read_text())
                    image = self._read_image(folder/'idle_01.png')
                    anchor = tuple(manifest['anchor'])
                self.actors[actor] = dict(sequences={key: [(image, .1)] for key in actions},
                                          anchor=anchor, body_pixels=image.get_bounding_rect().height,
                                          manifest={})
        # Angle-specific art augments action strips without altering their phase.
        # Retain the approved Reaper artwork before the directional overlay
        # replaces its ready views. The final shot reuses these exact images.
        self._approved_boss_sequences = self.actors['ice_reaper']['sequences'].copy()
        for actor, data in self.actors.items():
            folder = self.continuity_root/'actors'/actor
            path = folder/'animation.json'
            if not path.exists():
                self.missing_assets.append(f'continuity/actors/{actor}/animation.json')
                continue
            overlay = json.loads(path.read_text())
            if tuple(overlay['anchor']) != data['anchor'] or overlay['canvas'] != data['manifest']['canvas']:
                raise ValueError(f'Continuity views must preserve actor registration: {actor}')
            for key, entry in overlay['animations'].items():
                frames = entry['frames']
                data['sequences'][key] = [(self._read_image(folder/frame['file']),
                                          frame.get('duration_ms', 180)/1000) for frame in frames]
                data['manifest']['animations'][key] = entry
        environment = self.continuity_root/'environment'
        panorama_path = environment/'panorama.png'
        self.panorama = None
        self._panorama_cache = {}
        self._background_cache = {}
        self.landmark_images = {}
        if panorama_path.exists():
            self.panorama = pygame.surfarray.array3d(self._read_image(panorama_path))
            for name in ('castle', 'forest', 'ruins'):
                path = environment/f'{name}.png'
                if path.exists():
                    self.landmark_images[name] = self._read_image(path)
                else:
                    self.missing_assets.append(f'continuity/environment/{name}.png')
        else:
            self.missing_assets.append('continuity/environment/panorama.png')
        self.plates = {}
        for key in ('rescue', 'reverse', 'aerial'):
            path = self.asset_root/'environment'/f'{key}.png'
            if not path.exists():
                self.missing_assets.append(f'environment/{key}.png')
                path = self.opening/'environment.png'
            self.plates[key] = pygame.transform.scale(self._read_image(path), (640, 427))
        self.prison_back = self._read_image(self.opening/'ice_prison_back.png')
        self.prison_front = self._read_image(self.opening/'ice_prison_front.png')
        self.shard = self._read_image(self.opening/'glacial_shard.png')
        ground_path = self.asset_root/'environment/ground.png'
        self.ground_texture = pygame.surfarray.array3d(self._read_image(ground_path)) if ground_path.exists() else None
        self._screen_x = np.arange(480, dtype=np.float32)[:,None]
        self._screen_y = np.arange(320, dtype=np.float32)[None,:]
        self.scope = None
        for path in (self.asset_root/'props/launcher_scope.png',
                     self.asset_root/'launcher_scope.png'):
            if path.exists():
                self.scope = self._read_image(path)
                break
        from ice_reaper_rune import RuneSeal
        self.rune_seal = RuneSeal(self.asset_root.parent/'ice_reaper_rune/rune.png')
        # This front-quarter raising strip belongs only to Mira's pre-fire
        # loading shot. Keep the shared aim/fire art and its later mapping.
        folder = self.asset_root.parent/'mira_prefire_aim'
        prefire = json.loads((folder/'animation.json').read_text())
        mira = self.actors['mira']
        if prefire['canvas'] != mira['manifest']['canvas'] or tuple(prefire['anchor']) != mira['anchor']:
            raise ValueError('Mira pre-fire drawings must preserve scene registration')
        entry = prefire['animations']['prefire_raise']
        mira['sequences']['prefire_raise'] = [
            (self._read_image(folder/frame['file']), frame.get('duration_ms', 112.5)/1000)
            for frame in entry['frames']]
        if len(mira['sequences']['prefire_raise']) != 4:
            raise ValueError('Mira pre-fire raise requires four authored drawings')
        mira['manifest']['animations']['prefire_raise'] = entry
        from rhea_winter import RheaWinterSprites
        self.winter = RheaWinterSprites(self._read_image)
        from rhea_scene_awakening import RheaSceneAwakening
        self.awakening = RheaSceneAwakening(self)
        from ice_reaper_duel import IceReaperDuel
        self.duel = IceReaperDuel(self)
        self.last_draw_trace = []

    def validate_assets(self):
        if self.missing_assets:
            raise ValueError('Missing authored rescue assets: '+', '.join(self.missing_assets))
        required = {'caelan':('ready','dash','slash','land'), 'lucan':('dash','brace','impact'),
                    'mira':('raise','load','aim','fire'), 'rhea':('release',),
                    'ice_reaper':('aim','launch','recharge')}
        for actor, actions in required.items():
            for action in actions:
                count=len(self.actors[actor]['sequences'][action])
                if not 4 <= count <= 10:
                    raise ValueError(f'Rescue action requires 4–10 drawings: {actor}/{action}')

    def reset(self):
        # The entire visual state is a pure function of elapsed time.
        pass

    @staticmethod
    def story_time(elapsed):
        """Retain the early action's original choreography clock.

        The replacement awakening owns a local clock starting at 15.1 seconds;
        its camera and expression sequence do not use this legacy hold mapping.
        """
        if elapsed <= 15.1:
            return float(elapsed)
        if elapsed <= 16.1:
            return 15.1
        return float(elapsed)-1.

    @staticmethod
    def shot(time):
        return next((name for start, end, name in SHOTS if start <= time < end),
                    'rune_panorama' if time >= 20 else 'opening')

    @staticmethod
    def first_shard_release():
        """The first shard leaves the lowered hand, not the overhead charge."""
        return V3(3.6, 8.3, -8)

    @staticmethod
    def first_shard_target():
        """Rhea's upper body inside the prison is the attack's intended target."""
        return V3(-3, 1.1, 0)

    @classmethod
    def first_shard_shield_contact(cls):
        release, target = cls.first_shard_release(), cls.first_shard_target()
        # Contact is on the enemy side of the prison.  Its height and lateral
        # placement follow the attack ray, rather than aiming a new ray at Lucan.
        guard_depth = -.75
        return release.lerp(target, (guard_depth-release.z)/(target.z-release.z))

    @classmethod
    def lucan_guard_position(cls):
        contact = cls.first_shard_shield_contact()
        # In the rear-quarter overhead guard the shield is on the upper left
        # of the body.  Lucan plants farther toward the enemy and holds that
        # shield above/behind his left shoulder, leaving his kneeling silhouette
        # visible beside the prison while the shield itself covers Rhea's ray.
        return V3(contact.x+.215, 0, contact.z-.6)

    @classmethod
    def attack_geometry(cls):
        """Shared world geometry for rendering, telemetry and review overlays."""
        return dict(release=cls.first_shard_release(), target=cls.first_shard_target(),
                    shield=cls.first_shard_shield_contact(), lucan=cls.lucan_guard_position())

    @classmethod
    def first_shard_tip(cls, time):
        release, contact = cls.first_shard_release(), cls.first_shard_shield_contact()
        if time < 6.86:
            # The tip descends with her lowering arm before the forward launch.
            return lerp((3.6,12,-8), release, smooth(phase(time,6.45,6.86)))
        progress = (.68*phase(time,6.86,7.5) if time < 7.5 else
                    .68+.32*phase(time,7.5,9.0))
        return release.lerp(contact, progress)

    @classmethod
    def actor_positions(cls, time):
        dash = 1-(1-phase(time, 7.02, 7.5))**3
        slash = smooth(phase(time, 8.5, 9.25))
        caelan = lerp((4.7, 0, 8), (-1.5, 0, 1.25), dash)
        if time >= 7.5:
            caelan = lerp((-1.5, 0, 1.25), (-5.3, 0, -.7), slash)
        return {
            'rhea': V3(-3, 0, 0), 'caelan': caelan,
            'lucan': lerp((6.5, 0, 8), cls.lucan_guard_position(), dash),
            'mira': V3(7, 0, 10), 'ice_reaper': cls.reaper_position(time)}

    @staticmethod
    def reaper_position(time):
        """A brief rise and retreat bring her shoulders into the foreground."""
        original = V3(2, 6.6, -8)
        heading = V3(5, 0, -8).normalize()
        settled = original+heading*1.0
        settled.y = 9.0
        return original.lerp(settled, smooth(phase(time, 16.3, 16.95)))

    @classmethod
    def camera(cls, time, reduced_motion=False):
        shot = cls.shot(time)
        rescue_position = (7., 4.7, 15.)
        rescue_target = (-1.7, 1.9, .5)
        orbit_center = V3(-2, 1.7, 1)
        orbit_radius = V3(rescue_position)-orbit_center
        end_position = orbit_center+V3(-orbit_radius.x, orbit_radius.y, -orbit_radius.z)
        if shot == 'reaper_launch':
            return PerspectiveCamera((0, 8.6, 1.7), (2, 9.3, -8), 272)
        if shot in ('rescue_dash', 'slow_motion_rescue'):
            return PerspectiveCamera(rescue_position, rescue_target, 650)
        if shot == 'rescue_orbit':
            p = 1. if reduced_motion else smooth(phase(time, 9.5, 11))
            angle = p*math.pi
            x = orbit_radius.x*math.cos(angle)+orbit_radius.z*math.sin(angle)
            z = -orbit_radius.x*math.sin(angle)+orbit_radius.z*math.cos(angle)
            return PerspectiveCamera(tuple(orbit_center+V3(x, orbit_radius.y+math.sin(angle)*2, z)),
                                     tuple(lerp(rescue_target, (2.2, 1.7, 6), smooth(p))), 650-400*p)
        if shot == 'mira_loading':
            p = 1. if reduced_motion else smooth(phase(time, 11, 12.3))
            return PerspectiveCamera(tuple(lerp(end_position, (4.6, 2.5, 5.8), p)),
                                     tuple(lerp((2.2, 1.7, 6), (7, 1.45, 10), p)), 250+5*p)
        if shot in ('launcher_sight', 'second_shard_intercept'):
            p = 1. if reduced_motion else smooth(phase(time, 12.8, 14.05))
            angle = -2.62+p*math.pi
            position = V3(7+math.sin(angle)*4.2, 2.5, 10+math.cos(angle)*4.2)
            position = lerp((4.6, 2.5, 5.8), position, min(1, p*4))
            target = lerp((7, 1.45, 10), (2.1, 11.4, -8), 1. if reduced_motion else smooth(phase(time, 13, 14.05)))
            return PerspectiveCamera(tuple(position), tuple(target), 255+100*p, (240,158-33*p))
        # This utility accepts the canonical choreography clock. Production
        # playback passes actual elapsed time directly to the awakening helper.
        from rhea_scene_awakening import RheaSceneAwakening
        return RheaSceneAwakening.camera(time-14.1, reduced_motion)

    @classmethod
    def telemetry(cls, elapsed):
        if elapsed >= 21.-1e-10:
            from ice_reaper_duel import IceReaperDuel
            camera = IceReaperDuel.camera(elapsed)
            return dict(IceReaperDuel.state(elapsed), time=elapsed,
                        positions={key:list(value) for key,value in IceReaperDuel.actor_positions(elapsed).items()},
                        camera_position=list(camera.position), camera_target=list(camera.target),
                        focal=camera.focal, prison='shattered', rune=1., slow_motion=False)
        if elapsed >= 15.1-1e-10:
            from rhea_scene_awakening import RheaSceneAwakening
            local = RheaSceneAwakening.local_time(elapsed)
            time = RheaSceneAwakening.canonical_time(local)
            camera = RheaSceneAwakening.camera(local)
            return dict(RheaSceneAwakening.state(local), time=elapsed,
                        choreography_time=time,
                        positions={key:list(value) for key,value in cls.actor_positions(time).items()},
                        first_shard='intercepted', second_shard='destroyed',
                        rune=phase(time,16.3,17.6),
                        camera_position=list(camera.position),
                        camera_target=list(camera.target), focal=camera.focal,
                        slow_motion=False)
        time = cls.story_time(elapsed)
        if time < 8.5:
            prison = 'intact'
        elif time < 16.3:
            prison = 'cracked'
        else:
            prison = 'shattered'
        return dict(shot=cls.shot(time), time=elapsed, choreography_time=time,
                    positions={key: list(value) for key, value in cls.actor_positions(time).items()},
                    prison=prison,
                    first_shard='aimed' if time < 6.86 else 'flight' if time < 9.0 else 'intercepted',
                    second_shard='absent' if time < 12.65 else 'forming' if time < 14.7 else 'destroyed',
                    rune=phase(time, 16.3, 17.6),
                    camera_position=list(cls.camera(time).position),
                    camera_target=list(cls.camera(time).target),
                    slow_motion=7.5 <= time < 9.5)

    def _scale(self, image, width, height):
        width, height = max(1, round(width)), max(1, round(height))
        width, height = min(width, 1400), min(height, 1400)
        key = (id(image), width, height)
        if key not in self._scaled:
            if len(self._scaled) > 1800:
                self._scaled.clear()
            self._scaled[key] = pygame.transform.scale(image, (width, height))
        return self._scaled[key]

    @staticmethod
    def _flat_direction(vector, fallback=(0, 0, 1)):
        direction = V3(vector)
        direction.y = 0
        return direction.normalize() if direction.length_squared() > 1e-8 else V3(fallback)

    @classmethod
    def actor_heading(cls, actor, time):
        """A character's world direction is independent of the viewing camera."""
        positions = cls.actor_positions(time)
        if actor == 'caelan':
            if time < 7.5:
                vector = cls.actor_positions(7.5)[actor]-cls.actor_positions(7.02)[actor]
            else:
                # Continue facing through the strike and hold the landing.
                vector = cls.actor_positions(9.3)[actor]-cls.actor_positions(7.5)[actor]
        elif actor == 'lucan':
            if time < 7.5:
                vector = cls.actor_positions(7.5)[actor]-cls.actor_positions(7.02)[actor]
            else:
                release = cls.first_shard_release() if hasattr(cls, 'first_shard_release') else positions['ice_reaper']
                vector = V3(release)-positions[actor]
        elif actor == 'rhea':
            # Her original frozen pose faces the approaching party.  The ice
            # fixes that heading; she can turn toward her attacker only after
            # she breaks free, rather than changing sides inside the prison.
            intended = cls._flat_direction(positions['ice_reaper']-positions[actor])
            angle = math.atan2(intended.x, intended.z)*smooth(phase(time,16.32,16.92))
            return V3(math.sin(angle),0,math.cos(angle))
        elif actor == 'mira':
            vector = positions['ice_reaper']-positions[actor]
        else:
            vector = positions['rhea']-positions[actor]
        return cls._flat_direction(vector)

    @classmethod
    def view_angles(cls, actor, camera, position, time):
        """Signed azimuth and elevation of the viewer in the actor's frame.

        Zero azimuth sees the face, +90 sees the actor's right side, and
        +/-180 sees the back.  A signed angle preserves asymmetric equipment.
        """
        viewer = V3(camera.position)-V3(position)
        heading = cls.actor_heading(actor, time)
        right = V3(heading.z, 0, -heading.x)
        horizontal = cls._flat_direction(viewer, heading)
        azimuth = math.degrees(math.atan2(horizontal.dot(right), horizontal.dot(heading)))
        elevation = math.degrees(math.atan2(viewer.y, max(.0001, math.hypot(viewer.x, viewer.z))))
        return azimuth, elevation

    @staticmethod
    def _view_metadata(key, entry):
        if 'view_azimuth_deg' in entry:
            return float(entry['view_azimuth_deg']), float(entry.get('view_elevation_deg', 0.))
        suffixes = {'front_right':45., 'rear_right':135., 'rear_left':-135.,
                    'front_left':-45., 'right':90., 'left':-90., 'rear':180.,
                    'front':0., 'rear_threequarter':135., 'side':90.}
        for suffix, angle in suffixes.items():
            if key.endswith('_'+suffix):
                return angle, 0.
        return None

    def sequence_key(self, actor, action, local, duration, camera, position, time):
        """Choose a camera view without replacing an active action with a hold."""
        data = self.actors[actor]
        sequences = data['sequences']
        if actor == 'mira' and action == 'aim' and 12.35 <= time < 12.8:
            return 'prefire_raise'
        azimuth, elevation = self.view_angles(actor, camera, position, time)
        active = duration is not None and local < duration
        turning_release = actor == 'rhea' and action == 'release' and local >= .35
        settled_aim = actor == 'mira' and action == 'aim' and local >= .45
        base = sequences.get(action)
        families = [action]
        if not active:
            held = {'caelan':'ready', 'lucan':'hold_brace', 'mira':'aim',
                    'rhea':'frozen' if time < 16.3 else 'release', 'ice_reaper':'ready'}[actor]
            families = [held, action]
            if actor == 'rhea' and time >= 17.5:
                families.append('frozen')
        candidates = []
        entries = data['manifest'].get('animations', {})
        for key, sequence in sequences.items():
            if not any(key.startswith(family+'_') for family in families):
                continue
            # A one-drawing rear pose must never erase a six/eight/ten-drawing
            # dash, kneel or slash. Matching views retain the same phase index.
            if active and not (turning_release or settled_aim) and (base is None or len(sequence) != len(base)):
                continue
            view = self._view_metadata(key, entries.get(key, {}))
            if view is None:
                continue
            if actor == 'mira' and key.startswith('aim_') and time < 14.2:
                # These pre-fire aim turnarounds were authored with the view
                # sign opposite the stage basis. Correct their selection here
                # without mirroring her equipment or changing the firing shot.
                view = (-view[0], view[1])
            delta = abs((azimuth-view[0]+180)%360-180)
            score = delta+abs(elevation-view[1])*.25
            # Exact-action views win ties over a generic held-ready fallback.
            score += .01*next(i for i, family in enumerate(families) if key.startswith(family+'_'))
            candidates.append((score, key))
        if candidates:
            return min(candidates)[1]
        if action in sequences:
            return action
        return 'ready' if 'ready' in sequences else next(iter(sequences))

    def _approved_boss_frame(self, camera, position, time):
        """Original artwork, selected for the current view without changing it."""
        azimuth, _ = self.view_angles('ice_reaper', camera, position, time)
        sequences = self._approved_boss_sequences
        if abs(azimuth) >= 112.5:
            # The retained rear drawings depict left quarter, back and right
            # quarter views. Choose by angle, rather than rotating on a timer.
            # The first retained quarter drawing looks left; it belongs on
            # the right shoulder of this shot, facing inward toward Rhea.
            views = (145., 180., -145.)
            index = min(range(3), key=lambda i: abs((azimuth-views[i]+180)%360-180))
            image = sequences['ready_rear'][index][0]
        elif abs(azimuth) >= 45:
            # The approved side drawings all look left. On the opposite side
            # use the neutral approved back view instead of looking offstage.
            image = (sequences['ready_rear'][2][0] if azimuth < 0 else
                     sequences['ready_side'][min(2, int((abs(azimuth)-45)/30))][0])
        else:
            image = sequences['recharge'][-1][0]
        return image, self.actors['ice_reaper']

    def _sequence(self, actor, action, local, duration, camera, position, *, time=None):
        data = self.actors[actor]
        sequences = data['sequences']
        time = 8. if time is None else time
        if actor == 'rhea':
            azimuth, _ = self.view_angles(actor, camera, position, time)
            image, data, _ = self.winter.hold(azimuth, time)
            return image, data
        if actor == 'ice_reaper' and time >= 16.3:
            return self._approved_boss_frame(camera, position, time)
        key = self.sequence_key(actor, action, local, duration, camera, position, time)
        sequence = sequences[key]
        if actor == 'mira' and key == 'prefire_raise':
            duration = .45
        if duration:
            index = min(len(sequence)-1, int(phase(local, 0, duration)*len(sequence)))
        else:
            total = sum(item[1] for item in sequence)
            t = local % total
            index = 0
            for index, (_, length) in enumerate(sequence):
                if t < length:
                    break
                t -= length
        return sequence[index][0], data

    @staticmethod
    def _action(actor, time):
        if actor == 'caelan':
            if time < 7.02: return 'ready', time, None
            if time < 7.5: return 'dash', time-7.02, .48
            if time < 9.15: return 'slash', time-7.5, 1.65
            if time < 9.7: return 'land', time-9.15, .55
            return 'ready', time-9.7, None
        if actor == 'lucan':
            if time < 7.02: return 'ready', time, None
            if time < 7.5: return 'dash', time-7.02, .48
            if time < 9.0: return 'brace', time-7.5, 1.5
            if time < 9.7: return 'impact', time-9.0, .7
            return 'brace', 2, 1.65
        if actor == 'mira':
            # Her preparation begins offscreen during the rescue. When the
            # orbit reveals her, the settled aiming pose has matching views.
            if time < 9.1: return 'raise', 0., .4
            if time < 9.5: return 'raise', time-9.1, .4
            if time < 10.6: return 'aim', 1., .65
            if time < 12.35: return 'load', time-10.6, 1.75
            if time < 14.2: return 'aim', time-12.35, .65
            if time < 14.95: return 'fire', time-14.2, .75
            return 'aim', 1, .65
        if actor == 'rhea':
            return ('release', time-16.3, 1.2) if time >= 16.3 else ('ready', 0, None)
        if time < 6.65: return 'aim', time-5, 1.65
        if time < 7.3: return 'launch', time-6.65, .65
        if time < 11.7: return 'ready', time-7.3, None
        return 'recharge', time-11.7, 2.4

    def _billboard(self, canvas, actor, position, camera, time, *, alpha=255):
        projected = camera.project(position)
        if projected is None:
            return
        x, y, depth = projected
        action, local, duration = self._action(actor, time)
        image, data = self._sequence(actor, action, local, duration, camera, position, time=time)
        if actor == 'ice_reaper':
            self._projected_boss(canvas, image, data, position, camera, alpha=alpha)
            return
        height = 4.8 if actor == 'ice_reaper' else 1.85
        scale = camera.focal*height/depth/max(1, data['body_pixels'])
        if scale <= 0:
            return
        surface = self._scale(image, image.get_width()*scale, image.get_height()*scale)
        if alpha != 255:
            surface = surface.copy(); surface.set_alpha(alpha)
        ax, ay = data['anchor']
        canvas.blit(surface, (round(x-ax*scale), round(y-ay*scale)))
        if actor == 'caelan':
            self._fireblade(canvas, camera, position, time)

    def _projected_boss(self, canvas, image, data, position, camera, *, alpha=255):
        """Foreshorten the upright body and anchor it to projected head/feet.

        A fixed-height screen billboard incorrectly towers over the arena when
        the camera looks down from above the wings. A row shear follows the
        perspective head-to-foot axis without changing the authored anatomy.
        """
        foot = camera.project(position)
        head = camera.project(V3(position)+V3(0,4.8,0))
        if foot is None or head is None:
            return
        body = max(1, data['body_pixels'])
        height = max(1., foot[1]-head[1])
        scale_y = height/body
        scale_x = camera.focal*4.8/((foot[2]+head[2])*.5)/body
        # In the close foreground the head/shoulder plane is much nearer than
        # the feet. Use its actual world depth as she rises into that plane;
        # otherwise the old flat-card foreshortening exposes her whole body.
        # The projected head remains the anchor, and the lower body naturally
        # extends below the viewport rather than being masked or screen-pinned.
        proximity = smooth(phase(position.y, 6.6, 9.0))
        if proximity:
            head_scale = camera.focal*4.8/head[2]/body
            scale_x += (head_scale-scale_x)*proximity
            scale_y += (head_scale-scale_y)*proximity
            foot = (head[0]+(foot[0]-head[0])*(1-proximity),
                    head[1]+body*scale_y, foot[2])
            height = body*scale_y
        scaled = self._scale(image, image.get_width()*scale_x, image.get_height()*scale_y)
        ax, ay = data['anchor']
        foot_row = ay*scale_y
        shear = (head[0]-foot[0])/height
        shifts = [round((foot_row-row)*shear) for row in range(scaled.get_height())]
        low, high = min(shifts), max(shifts)
        projected = pygame.Surface((scaled.get_width()+high-low, scaled.get_height()),pygame.SRCALPHA)
        for row, shift in enumerate(shifts):
            projected.blit(scaled,(shift-low,row),(0,row,scaled.get_width(),1))
        if alpha != 255:
            projected.set_alpha(alpha)
        canvas.blit(projected,(round(foot[0]-ax*scale_x+low),round(foot[1]-foot_row)))

    @staticmethod
    def world_landmarks():
        # The city lies beyond the Reaper; the wooded approach is behind Mira.
        landmarks = [
            ('castle', (-14., 0., -70.), 22.),
            ('ruins', (-21., 0., 5.), 6.),
            ('ruins', (24., 0., -13.), 8.),
        ]
        # Overlapping groups form the same continuous wooded approach from
        # every view; they never move with the camera or the current shot.
        for index in range(-9, 10):
            landmarks.append(('forest', (index*4.8, 0., 38.+3*math.sin(index*1.8)),
                              10.+1.5*math.cos(index*2.1)))
        for side in (-1, 1):
            for index in range(9):
                landmarks.append(('forest', (side*(32.+2*math.sin(index*1.9)), 0., -8.+index*5.6),
                                  9.+1.8*math.cos(index*1.7)))
        return tuple(landmarks)

    def _panoramic_sky(self, canvas, camera):
        right, up, forward = camera.basis()
        key = tuple(round(v, 7) for vector in (right, up, forward) for v in vector)+(camera.focal, *camera.center)
        cached = self._panorama_cache.get(key)
        if cached is not None:
            canvas.blit(cached, (0, 0))
            return
        u = (self._screen_x-camera.center[0])/camera.focal
        v = (camera.center[1]-self._screen_y)/camera.focal
        ray_x = forward.x+right.x*u+up.x*v
        ray_y = forward.y+right.y*u+up.y*v
        ray_z = forward.z+right.z*u+up.z*v
        bearing = np.arctan2(ray_x, -ray_z)
        elevation = np.arctan2(ray_y, np.sqrt(ray_x*ray_x+ray_z*ray_z))
        width, height = self.panorama.shape[:2]
        px = ((.5+bearing/TAU)*width).astype(np.int32)%width
        py = np.clip((.66-elevation/math.radians(120))*height, 0, height-1).astype(np.int32)
        image = pygame.surfarray.make_surface(self.panorama[px, py])
        if len(self._panorama_cache) >= 16:
            self._panorama_cache.pop(next(iter(self._panorama_cache)))
        self._panorama_cache[key] = image
        canvas.blit(image, (0, 0))

    def _background(self, canvas, camera, time):
        # A camera pose always sees the same geography, regardless of shot ID.
        key = tuple(camera.position)+tuple(camera.target)+(camera.focal, *camera.center)
        cached = self._background_cache.get(key)
        if cached is not None:
            canvas.blit(cached, (0, 0))
            return
        if self.panorama is None:
            canvas.blit(self.plates['rescue'], (-80, -80))
            self._ground_plane(canvas, camera)
            return
        self._panoramic_sky(canvas, camera)
        self._ground_plane(canvas, camera)
        landmarks = []
        for name, position, height in self.world_landmarks():
            projected = camera.project(position)
            if projected is not None:
                landmarks.append((projected[2], name, position, height, projected))
        for depth, name, position, height, projected in sorted(landmarks, reverse=True):
            image = self.landmark_images.get(name)
            if image is None:
                continue
            scale = camera.focal*height/depth/image.get_height()
            surface = self._scale(image, image.get_width()*scale, image.get_height()*scale)
            canvas.blit(surface, (round(projected[0]-surface.get_width()/2),
                                  round(projected[1]-surface.get_height())))
        if len(self._background_cache) >= 16:
            self._background_cache.pop(next(iter(self._background_cache)))
        self._background_cache[key] = canvas.copy()

    def _ground_plane(self, canvas, camera):
        if self.ground_texture is None:
            return
        right, up, forward = camera.basis()
        u=(self._screen_x-camera.center[0])/camera.focal
        v=(camera.center[1]-self._screen_y)/camera.focal
        ray_y=forward.y+right.y*u+up.y*v
        distance=-camera.position[1]/np.minimum(ray_y,-.001)
        wx=camera.position[0]+distance*(forward.x+right.x*u+up.x*v)
        wz=camera.position[2]+distance*(forward.z+right.z*u+up.z*v)
        alpha=np.where(ray_y<-.015,np.clip((65-distance)/42,0,.45),0)
        # Mirror the authored snow patch at each edge so the moving ground
        # does not expose a checkerboard of hard texture-wrap seams.
        tw, th = self.ground_texture.shape[:2]
        tx=(wx*22).astype(np.int32)%(2*tw)
        tz=(wz*22).astype(np.int32)%(2*th)
        tx=np.minimum(tx,2*tw-1-tx)
        tz=np.minimum(tz,2*th-1-tz)
        texture=self.ground_texture[tx,tz].astype(np.float32)
        target=pygame.surfarray.pixels3d(canvas)
        target[:]=(target.astype(np.float32)*(1-alpha[:,:,None])+texture*alpha[:,:,None]).astype(np.uint8)
        del target

    @staticmethod
    def _line3(canvas, camera, color, points, width=1):
        projected = [camera.project(point) for point in points]
        if all(projected):
            pygame.draw.lines(canvas, color, False, [(round(p[0]),round(p[1])) for p in projected], width)

    def _shadow(self, canvas, camera, position, radius=.5):
        points = [camera.project((position.x+math.cos(a)*radius, .025,
                                  position.z+math.sin(a)*radius*.55))
                  for a in [i*TAU/16 for i in range(16)]]
        if all(points):
            pygame.draw.polygon(canvas, '#67869d', [(p[0],p[1]) for p in points])

    def _prison(self, canvas, camera, position, time, front):
        if time >= 16.45:
            return
        image = self.prison_front if front else self.prison_back
        p = camera.project(position)
        if p is None:
            return
        scale = camera.focal*2.55/p[2]/128
        surface = self._scale(image, image.get_width()*scale, image.get_height()*scale)
        if time >= 16.3:
            surface = surface.copy();surface.set_alpha(round(255*(1-phase(time,16.3,16.45))))
        canvas.blit(surface, (round(p[0]-44*scale), round(p[1]-130*scale)))
        if front and 8.5 <= time < 16.4:
            for i in range(7):
                start = V3(position)+V3(-.55+i*.17, .7+(i%3)*.4, -.08)
                points = [start, start+V3(.18,.25,0), start+V3(-.03,.45,0),start+V3(.15,.7,0)]
                self._line3(canvas,camera,'#f2ffff',points,2)
                self._line3(canvas,camera,'#3e7b9c',[p+V3(.025,0,0) for p in points],1)

    def _fireblade(self, canvas, camera, position, time):
        if not 8.45 < time < 9.0:
            return
        if time < 7.5:
            base = V3(position)+V3(-.2,1.0,.1); tip=base+V3(-1.0,.75,0)
        else:
            p = phase(time,7.5,9.15)
            angle = -1.7+p*3.7
            base=V3(position)+V3(-.25,1.05,0)
            tip=base+V3(math.sin(angle)*1.5, math.cos(angle)*1.5,0)
        # The blade itself is authored into every pose.  Only hot contact
        # sparks and a short arc are added here, so the weapon never detaches.
        contact = V3(-3, 1.15, .12)
        for i in range(14):
            angle = -1.4+phase(time,8.45,9.0)*2.7-i*.035
            point = contact+V3(math.cos(angle)*.6, math.sin(angle)*.8,0)
            q = camera.project(point)
            if q: pygame.draw.circle(canvas, '#ffd78c', q[:2], max(1,3-i//6))

    def _dash_snow(self, canvas, camera, positions, time, reduced):
        if not 7.02 <= time <= 10:return
        for actor in ('caelan','lucan'):
            origin=V3((4.7,0,8) if actor=='caelan' else (6.5,0,8))
            destination=positions[actor]
            for i in range(26 if not reduced else 8):
                birth=7.02+(i%9)/9*.44
                age=time-birth
                if age < 0 or age > 1.65:continue
                progress=(i%9)/9
                source=origin.lerp(destination,progress)
                source+=V3(math.sin(i*4.9)*age*.75, math.sin(min(1,age/1.4)*math.pi)*(.2+i%4*.12),math.cos(i*6.2)*age*.65)
                p=camera.project(source)
                if p:pygame.draw.circle(canvas,('#d8edfa','#edf8ff','#bcd9ec')[i%3],p[:2],max(1,round(camera.focal/p[2]*(.035+i%3*.025))))

    def _draw_shard(self, canvas, camera, point, target, *, size=2.8, alpha=255, tip=False):
        p=camera.project(point)
        direction=V3(target)-V3(point)
        q=camera.project(V3(point)+direction.normalize()*.5) if direction.length() else p
        if not p or not q:return
        length=max(6,camera.focal*size/p[2])
        image=self._scale(self.shard,self.shard.get_width()/self.shard.get_height()*length,length)
        angle=math.degrees(math.atan2(q[0]-p[0],q[1]-p[1]))
        image=pygame.transform.rotate(image,angle)
        if alpha!=255:image.set_alpha(alpha)
        center=pygame.Vector2(p[:2])
        if tip:
            projected_direction=pygame.Vector2(q[:2])-pygame.Vector2(p[:2])
            if projected_direction.length_squared():
                # Contact is defined at the pointed end.  Centering the whole
                # shard here would push half its length through the shield.
                center-=projected_direction.normalize()*length*.5
        canvas.blit(image,image.get_rect(center=(round(center.x),round(center.y))))

    def _fragments(self, canvas, camera, origin, time, birth, count, *, fire=False):
        age=time-birth
        if age < 0 or age > 2.5:return
        for i in range(count):
            angle=i*2.39996
            speed=1.3+(i%7)*.35
            point=V3(origin)+V3(math.cos(angle)*speed*age,
                               (1.3+i%5*.55)*age-2.4*age*age,
                               math.sin(angle)*speed*age)
            point.y=max(.03,point.y)
            p=camera.project(point)
            if not p:continue
            r=max(1,min(6,round(camera.focal/p[2]*(.03+i%4*.025))))
            color=('#fff0bd','#ffb14e','#e98042')[i%3] if fire else ('#e0f8ff','#8bc6ed','#d7edfc')[i%3]
            pygame.draw.polygon(canvas,color,[(p[0],p[1]-r*1.8),(p[0]+r,p[1]),(p[0],p[1]+r),(p[0]-r,p[1])])

    def _projectiles(self, canvas, camera, positions, time, reduced):
        start=self.first_shard_release()
        target=self.first_shard_target()
        shield=self.first_shard_shield_contact()
        if time < 6.86:
            self._draw_shard(canvas,camera,self.first_shard_tip(time),target,tip=True)
        elif time < 9.0:
            point=self.first_shard_tip(time)
            flight=(shield-start).normalize()
            self._line3(canvas,camera,'#b4e6fc',[point,point-flight*1.1],3)
            self._draw_shard(canvas,camera,point,target,tip=True)
        else:
            self._fragments(canvas,camera,shield,time,9.0,22 if not reduced else 8)
            if time<9.17:
                p=camera.project(shield)
                if p:pygame.draw.circle(canvas,'#f1faff',p[:2],max(1,round((1-phase(time,9.0,9.17))*17)),2)
        second=V3(2.1,11.4,-8)
        if 12.65 <= time < 14.7:
            grow=.2+.8*smooth(phase(time,12.65,14.2))
            self._draw_shard(canvas,camera,second,positions['mira'],size=2.8*grow)
        if 14.25 <= time < 14.7:
            muzzle=positions['mira']+V3(-.18,1.45,-.45)
            u=phase(time,14.25,14.7)
            point=muzzle.lerp(second,u)
            self._line3(canvas,camera,'#ffe9a9',[point,muzzle.lerp(second,max(0,u-.1))],4)
            q=camera.project(point)
            if q:pygame.draw.circle(canvas,'#fff5da',q[:2],3)
        if 14.7<=time<15.4:
            self._fragments(canvas,camera,second,time,14.7,32 if not reduced else 10)
            p=camera.project(second)
            if p:
                age=phase(time,14.7,15.25)
                pygame.draw.circle(canvas,'#d8f6ff',p[:2],max(1,round(age*42)),2)
                if time<14.86:pygame.draw.circle(canvas,'#fff2d2',p[:2],max(1,round((1-age)*18)))

    def _rune(self, canvas, camera, time, reduced):
        self.rune_seal.draw(canvas, camera, time, reduced)

    def _loading_insert(self, canvas, time):
        if not 11.4 <= time < 12.3:
            return
        sequence=self.actors['mira']['sequences'].get('loading_detail')
        if not sequence:
            return
        image=sequence[min(len(sequence)-1,int(phase(time,11.4,12.25)*len(sequence)))][0]
        p=smooth(phase(time,11.4,11.58))
        scale=3.85+.15*phase(time,11.4,12.3)
        surface=self._scale(image,image.get_width()*scale,image.get_height()*scale).copy()
        surface.set_alpha(round(255*p))
        canvas.blit(surface,surface.get_rect(center=(240,174)))

    def _foreground_boss(self, canvas, camera, time):
        # The foreground uses the same body, anchor, world position and camera
        # projection as every other shot. Its back becomes visible because the
        # camera passes behind her, never because of a timed pose or screen slide.
        position = self.actor_positions(time)['ice_reaper']
        projected = camera.project(position)
        if projected is None:
            return
        action, local, duration = self._action('ice_reaper', time)
        image, data = self._sequence('ice_reaper', action, local, duration, camera, position, time=time)
        self._projected_boss(canvas,image,data,position,camera)

    def _scope_overlay(self, canvas, time):
        if time < 13.65 or time >= 15.1:return
        opacity=smooth(phase(time,13.65,14.15))
        if self.scope is not None:
            image=self._scale(self.scope,*SIZE).copy();image.set_alpha(round(255*opacity));canvas.blit(image,(0,0))
        else:
            mask=pygame.Surface(SIZE,pygame.SRCALPHA);mask.fill((10,19,27,round(200*opacity)))
            pygame.draw.circle(mask,(0,0,0,0),(240,125),130)
            canvas.blit(mask,(0,0))
            pygame.draw.circle(canvas,'#647a86',(240,125),132,5)
            pygame.draw.circle(canvas,'#b4bfbd',(240,125),126,1)
        # Fine sight marks leave the shard and Reaper unobscured.
        for x in (-1,1):pygame.draw.line(canvas,'#dbba76',(240+x*48,125),(240+x*17,125),1)
        for y in (-1,1):pygame.draw.line(canvas,'#dbba76',(240,125+y*40),(240,125+y*15),1)
        pygame.draw.circle(canvas,'#d9bd7c',(240,125),3,1)

    def draw(self, canvas, elapsed, reduced_motion=False):
        actual_time=clamp(float(elapsed),5,32)
        if actual_time >= 21.-1e-10:
            self.duel.draw(canvas, actual_time, reduced_motion)
            self.last_draw_trace = self.duel.last_draw_trace
            return
        if actual_time >= 15.1-1e-10:
            self.awakening.draw(canvas, self.awakening.local_time(actual_time), reduced_motion)
            self.last_draw_trace = self.awakening.last_draw_trace
            return
        self.last_draw_trace = []
        time=clamp(self.story_time(actual_time),5,20)
        camera=self.camera(time,reduced_motion)
        self._background(canvas,camera,time)
        positions=self.actor_positions(time)
        for actor,position in positions.items():
            if actor!='ice_reaper':self._shadow(canvas,camera,position,.6 if actor=='rhea' else .45)
        # Emissive strokes illuminate the snow even underneath a cast shadow.
        self._rune(canvas,camera,time,reduced_motion)
        self._dash_snow(canvas,camera,positions,time,reduced_motion)
        visible=[]
        for actor,position in positions.items():
            if actor == 'mira' and 7 <= time < 9.5:
                continue
            if actor in ('caelan','lucan','rhea') and 13.65 <= time < 15.1:
                continue
            p=camera.project(position)
            if p:visible.append((p[2],actor,position))
        for _,actor,position in sorted(visible,reverse=True):
            if actor=='rhea':self._prison(canvas,camera,position,time,False)
            self._billboard(canvas,actor,position,camera,time)
            if actor=='rhea':self._prison(canvas,camera,position,time,True)
        self._projectiles(canvas,camera,positions,time,reduced_motion)
        self._loading_insert(canvas,time)
        self._scope_overlay(canvas,time)
