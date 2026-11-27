"""Frontal bridge performance with shared camera projection and drawn figures.

The environment is baked from the same camera helpers used to place complete
character drawings. Source artwork owns faces, anatomy, equipment and gait;
runtime applies one uniform scale and translation per whole drawing.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import OrderedDict
from concurrent.futures import Future
import math
from pathlib import Path

import pygame

from cinematic_bridge_run import (CinematicBridgeRun, RENDER_SIZE, _animation,
                                  _number, _path, _read, _smooth)
from cinematic_perspective import CinematicPerspective

FACE_SCENE = Path(__file__).resolve().parent/'assets/story/fire_veinhold_opening/shot07/scene.json'
DEFAULT_CAMERA = {
    'focal_pixels':900., 'height_metres':1.55, 'ahead_metres':3.,
    'art_pixels_per_metre':500., 'speed_metres_per_second':11.42,
    'preceding_run_seconds':3., 'tilt_seconds':1.5,
    'pitch_start_radians':.48, 'pitch_end_radians':-.08,
    'reduced_motion_pitch_start_radians':.48,
}


def camera_at(seconds, reduced_motion=False, *, config=None):
    """Return the offline/runtime pinhole camera in bridge-local metres.

    +Y runs toward the fortress, +X is the runners' anatomical right, and +Z
    points upward. Looking back toward Merovar therefore maps +X to viewer left.
    Positive pitch looks upward. The camera tracks at exactly the party speed.
    """
    if not _number(seconds):
        raise ValueError('Invalid frontal camera clock')
    data = DEFAULT_CAMERA if config is None else config
    local = min(5., float(seconds))
    start = data['reduced_motion_pitch_start_radians'] if reduced_motion else data['pitch_start_radians']
    blend = _smooth(local/data['tilt_seconds'])
    pitch = start+(data['pitch_end_radians']-start)*blend
    travel = data['speed_metres_per_second']*(data['preceding_run_seconds']+local)
    position = [0., travel+data['ahead_metres'], data['height_metres']]
    forward = [0., -math.cos(pitch), math.sin(pitch)]
    return {'space':'local_bridge_frontal', 'position':position,
            'target':[position[i]+forward[i] for i in range(3)],
            'up':[0., math.sin(pitch), math.cos(pitch)],
            'focal_pixels':data['focal_pixels'], 'principal_point':[480., 320.],
            'fov_degrees':math.degrees(2*math.atan(320./data['focal_pixels'])),
            'fov_axis':'vertical', 'pitch_radians':pitch,
            'party_travel_metres':travel,
            'direction':'toward_mainland', 'tracking_direction':'toward_veinhold'}


def project_world(point, camera):
    """Project one fixed world point, returning x/y/depth or None behind lens."""
    if (not isinstance(point, (list, tuple)) or len(point) != 3
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in point)):
        raise ValueError('Invalid frontal world point')
    position = camera['position']
    along, vertical = position[1]-point[1], point[2]-position[2]
    pitch = camera['pitch_radians']
    depth = along*math.cos(pitch)+vertical*math.sin(pitch)
    if depth <= .05:
        return None
    image_vertical = vertical*math.cos(pitch)-along*math.sin(pitch)
    focal = camera['focal_pixels']
    return [480.+focal*(position[0]-point[0])/depth,
            320.-focal*image_vertical/depth, depth]


def _metadata(path, root, *, check_images):
    data = _read(path)
    if (data.get('version') != 1 or tuple(data.get('render_size', ())) != RENDER_SIZE
            or not _number(data.get('duration_seconds'), positive=True)
            or abs(data['duration_seconds']-5.) > 1e-8
            or not isinstance(data.get('actors'), list) or len(data['actors']) != 3):
        raise ValueError('Invalid frontal-reveal scene')
    camera = data.get('camera')
    positive = ('focal_pixels', 'height_metres', 'ahead_metres', 'art_pixels_per_metre',
                'speed_metres_per_second', 'tilt_seconds')
    if (not isinstance(camera, dict)
            or any(not _number(camera.get(key), positive=True) for key in positive)
            or not _number(camera.get('preceding_run_seconds'))
            or camera['tilt_seconds'] > data['duration_seconds']):
        raise ValueError('Invalid frontal-reveal camera')
    for key in ('pitch_start_radians', 'pitch_end_radians', 'reduced_motion_pitch_start_radians'):
        value = camera.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not -1. < value < 1.:
            raise ValueError('Invalid frontal-reveal camera pitch')
    actors, identifiers = [], set()
    for record in data['actors']:
        if (not isinstance(record, dict) or record.get('id') not in ('lucan', 'iselin', 'crown_soldier')
                or record['id'] in identifiers
                or not _number(record.get('phase_offset_seconds'))
                or not _number(record.get('offset_metres'), minimum=-100.)
                or record['offset_metres'] > 0
                or not _number(record.get('lane_metres'), minimum=-100.)):
            raise ValueError('Invalid frontal running formation')
        identifiers.add(record['id'])
        animation_path = _path(record.get('animation'), path.parent, root)
        animation = _animation(animation_path, root, check_images=check_images)
        actors.append({**record, 'animation':animation})
    by_id = {record['id']:record for record in actors}
    if (by_id['lucan']['offset_metres'] != 0 or by_id['lucan']['lane_metres'] != 0
            or abs(by_id['crown_soldier']['offset_metres']+3.048) > 1e-8
            or not by_id['iselin']['lane_metres'] > 0 > by_id['crown_soldier']['lane_metres']):
        raise ValueError('Frontal reveal must preserve the approved party formation')
    environment = _path(data.get('environment'), path.parent, root)
    segments = data.get('environment_segments')
    if (not isinstance(segments, dict) or set(segments) != {'normal', 'reduced_motion'}
            or any(not isinstance(value, str) or not value for value in segments.values())):
        raise ValueError('Invalid frontal environment segment selection')
    return {**data, 'actors':tuple(actors), 'layers':(), 'environment_path':environment}


def read_face_timing(manifest_path=FACE_SCENE):
    """Read actual authored contacts and offsets without decoding any artwork."""
    path = Path(manifest_path).resolve()
    data = _metadata(path, path.parent, check_images=False)
    return tuple({'id':actor['id'], 'cycle_seconds':actor['animation']['cycle_seconds'],
                  'phase_offset_seconds':actor['phase_offset_seconds'],
                  'contacts':[dict(contact) for contact in actor['animation']['contacts']]}
                 for actor in data['actors'])


class CinematicFaceReveal(CinematicBridgeRun):
    """Bounded full-drawing and environment caches, using one deterministic rig."""
    def __init__(self, manifest_path=FACE_SCENE, *, allowed_root=None, cache_size=72,
                 environment_cache_size=8):
        self.path = Path(manifest_path).resolve()
        root = self.path.parent if allowed_root is None else Path(allowed_root).resolve()
        if not self.path.is_relative_to(root):
            raise ValueError('Frontal-reveal manifest leaves its cinematic')
        if type(cache_size) is not int or not 3 <= cache_size <= 72:
            raise ValueError('Invalid frontal drawing cache size')
        self.data = _metadata(self.path, root, check_images=True)
        self.duration = self.data['duration_seconds']
        self.cache_size = cache_size
        self._cache = OrderedDict()
        self._backgrounds = {}
        self._sizes = {}
        for actor in self.data['actors']:
            self._sizes.update({frame['path']:actor['animation']['canvas']
                                for frame in actor['animation']['frames']})
        if len(self._sizes) > self.cache_size:
            raise ValueError('Complete frontal gait cycle exceeds its drawing cache bound')
        self._window = ()
        self._executor = None
        self._decodes = self._waits = 0
        self._wait_seconds = 0.
        self.environment = CinematicPerspective(self.data['environment_path'], allowed_root=root,
                                               cache_size=environment_cache_size)
        for mode, segment in self.data['environment_segments'].items():
            self.environment.validate_segment(segment, self.duration)
            if self.environment.segments[segment]['loop'] is not None:
                raise ValueError('Frontal camera bank must retain its inclusive endpoints')
            for index, sample in enumerate(self.environment.segments[segment]['metadata']):
                expected = camera_at(index/60, mode == 'reduced_motion', config=self.data['camera'])
                actual = sample.get('camera', {})
                for key in ('position', 'target', 'up'):
                    if key not in actual or any(abs(a-b) > 1e-6 for a,b in zip(actual[key], expected[key])):
                        raise ValueError('Frontal background camera differs from character staging')
                for key in ('fov_degrees', 'focal_pixels', 'pitch_radians'):
                    if (not _number(actual.get(key), minimum=-1.)
                            or abs(actual[key]-expected[key]) > 1e-6):
                        raise ValueError('Frontal background lens differs from character staging')

    def samples(self, seconds, reduced_motion=False):
        if not _number(seconds):
            raise ValueError('Invalid frontal-reveal clock')
        local = min(self.duration, float(seconds))
        camera = camera_at(local, reduced_motion, config=self.data['camera'])
        actors = []
        for actor in self.data['actors']:
            animation = actor['animation']
            phase = (local+actor['phase_offset_seconds']) % animation['cycle_seconds']
            if animation['cycle_seconds']-phase <= 1e-9:
                phase = 0.
            index = min(len(animation['frames'])-1,
                        bisect_right(animation['boundaries'], phase+1e-10))
            world = [actor['lane_metres'], camera['party_travel_metres']+actor['offset_metres'], 0.]
            foot = project_world(world, camera)
            body = project_world([world[0], world[1], .9], camera)
            if foot is None or body is None:
                raise ValueError('Frontal actor has moved behind the camera')
            scale = camera['focal_pixels']/body[2]/self.data['camera']['art_pixels_per_metre']
            position = [foot[0]-animation['anchor'][0]*scale,
                        foot[1]-animation['anchor'][1]*scale]
            bounds = pygame.Rect(round(position[0]), round(position[1]),
                                 round(animation['canvas'][0]*scale), round(animation['canvas'][1]*scale))
            actors.append({'id':actor['id'], 'frame_index':index, 'cycle_phase':phase,
                'phase_offset_seconds':actor['phase_offset_seconds'], 'scale':scale,
                'space':'local_bridge_frontal', 'world_position_metres':world,
                'draw_position':position, 'ground_anchor':foot[:2], 'depth_metres':body[2],
                'visible':bounds.colliderect(pygame.Rect((0, 0), RENDER_SIZE)),
                'draw_order':-body[2]})
        segment = self.data['environment_segments']['reduced_motion' if reduced_motion else 'normal']
        # Reduced Motion has a dedicated, geometrically registered camera bank;
        # generic dissolve sampling would detach the drawn actors from the deck.
        environment = self.environment.samples(segment, local, False)
        return {'local_time':local, 'phase':'face_reveal', 'reduced_motion':bool(reduced_motion),
                'camera':camera, 'runners':actors, 'environment':environment}

    def preload(self, seconds=0., *, reduced_motion=False, blocking=False):
        """Prepare one complete cycle without repeatedly decoding large poses.

        Full-film and standalone playback prepare the bounded cycle before
        their clocks start. Two software decoders fill the fixed reservations;
        nonblocking callers convert at most two completed poses per main-thread
        call rather than doing an unbounded display-conversion burst.
        """
        state = self.samples(seconds, reduced_motion)
        current = []
        for stage, actor in zip(state['runners'], self.data['actors']):
            current.append(actor['animation']['frames'][stage['frame_index']]['path'])
        self._window = tuple(dict.fromkeys((*current, *self._sizes)))
        for path in self._window:
            if path not in self._cache:
                self._queue(path)
        if blocking:
            for path in self._window:
                self._image(path, canvas=self._sizes[path])
        else:
            converted = 0
            for path in self._window:
                cached = self._cache[path]
                if isinstance(cached, Future) and cached.done():
                    self._image(path, canvas=self._sizes[path])
                    converted += 1
                    if converted == 2:
                        break
        self.environment.preload(state['environment']['segment'], seconds,
                                 reduced_motion=False, alarm_active=False,
                                 blocking=blocking, max_slots=self.environment.cache_size)
        return state

    def draw(self, target, state):
        if target.get_size() != RENDER_SIZE:
            raise ValueError('Frontal reveal requires native output dimensions')
        self.environment.draw(target, state['environment'], alarm_active=False, alarm_elapsed=0.)
        by_id = {actor['id']:actor for actor in self.data['actors']}
        for stage in sorted(state['runners'], key=lambda actor:actor['draw_order']):
            if stage['visible']:
                animation = by_id[stage['id']]['animation']
                record = animation['frames'][stage['frame_index']]
                image = self._image(record['path'], canvas=animation['canvas'])
                self._whole_drawing(target, image, stage['draw_position'], stage['scale'])

    @property
    def cache_info(self):
        actor = super().cache_info
        environment = self.environment.cache_info
        return {'surfaces':actor['surfaces']+environment['surfaces'],
                'bytes':actor['bytes']+environment['bytes'],
                'decoded_bytes':actor['decoded_bytes']+environment['decoded_bytes'],
                'pending_bytes':actor['pending_bytes']+environment['pending_bytes'],
                'capacity':actor['capacity']+environment['capacity'],
                'byte_capacity':self.cache_size*max(width*height*4 for width, height in self._sizes.values())
                                +self.environment.cache_size*960*640*4,
                'waits':actor['waits']+environment['waits'],
                'wait_seconds':actor['wait_seconds']+environment['wait_seconds'],
                'prepared_frames':sum(not isinstance(value, Future) for value in self._cache.values()),
                'expected_frames':len(self._sizes),
                'actor_cache':actor, 'environment_cache':environment}

    def close(self):
        super().close()
        self.environment.close()
