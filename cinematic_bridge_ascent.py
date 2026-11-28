"""Bridge-ascent camera and phase state; native pictures are baked offline.

Bridge-local +Y points toward the Veinhold, +X is the runners' right and +Z
is above the walking deck. Screen right remains -X throughout the crane.
"""
from __future__ import annotations

import math
import json
from hashlib import sha256
from pathlib import Path

ASCENT_SCENE = Path(__file__).resolve().parent/'assets/story/fire_veinhold_opening/shot08/scene.json'
DURATION = 8.0
FPS = 60
RENDER_SIZE = (960, 640)
PARTY_START = 54.26
PARTY_SPEED = 4.0
GATE = {'center_y':299.0,'near_y':293.0,'far_y':305.0,
        'roof_bottom_z':21.0,'roof_top_z':27.0,'clear_half_width':6.0}
ACTORS = (
    {'id':'lucan', 'lane_metres':0.0, 'offset_metres':0.0,
     'phase_offset_seconds':0.0, 'height_metres':1.85},
    {'id':'iselin', 'lane_metres':0.65, 'offset_metres':-0.5,
     'phase_offset_seconds':1/6, 'height_metres':1.72},
    {'id':'crown_soldier', 'lane_metres':-0.75, 'offset_metres':-3.048,
     'phase_offset_seconds':0.3, 'height_metres':1.80},
)
FROZEN_GUARDS = ((3.200023648856204,.6999962608476988),(-2.4999983073154417,1.6000028961451442),
                 (1.1999872491216284,3.0000127642188605),(-4.599979947232173,.5999836759026613))
REINFORCEMENTS = tuple(zip((-2.2,2.2,-2.2,2.2,-2.2,2.2,-.8,.8),
                          (236,236,242,242,248,248,316,320),
                          (0,.18,.42,.56,.28,.70,.08,.48)))
CAMERA = {
    'starting_party_metres':PARTY_START, 'speed_metres_per_second':PARTY_SPEED,
    'height_keys':[[0,1.55,0],[0.8,4,6],[2.2,22,22],[5.8,292,7],[8,300,2]],
    'focal_keys':[[0,900,0],[0.4,860,-200],[0.6,780,-500],[0.8,650,-100],
                  [1.2,620,-25],[2.2,600,-15],[5.8,550,0],[8,550,0]],
    'pitch_degree_keys':[[0,math.degrees(-.08),0],[0.4,-12,-35],[0.6,-25,-70],
                         [0.8,-40,-85],[1,-60,-75],[1.2,-70,-40],
                         [1.6,-82,-22],[2.2,-90,0],[8,-90,0]],
    'overhead_seconds':2.2, 'reframe_seconds':5.8,
    'screen_right':[-1,0,0], 'art_pixels_per_metre':500,
    'framing':'mainland_up_fortress_down',
}


def _clock(seconds):
    if type(seconds) not in (int,float) or not math.isfinite(seconds):
        raise ValueError('Invalid bridge ascent clock')
    return min(DURATION,max(0.0,float(seconds)))


def _smooth(value):
    value = min(1.0,max(0.0,value))
    return value**3*(10+value*(-15+6*value))


def _hermite(t, t0, p0, v0, t1, p1, v1):
    """Quintic interpolation with shared velocities and zero node acceleration."""
    dt = t1-t0
    u = min(1.0,max(0.0,(t-t0)/dt))
    delta = p1-p0
    a,b = v0*dt,v1*dt
    return p0+a*u+(10*delta-6*a-4*b)*u**3+(-15*delta+8*a+7*b)*u**4+(6*delta-3*a-3*b)*u**5


def _keys(t, keys):
    for first,second in zip(keys,keys[1:]):
        if t <= second[0]:
            return _hermite(t,first[0],first[1],first[2],second[0],second[1],second[2])
    return float(keys[-1][1])


def camera_at(seconds, reduced_motion=False, *, config=None):
    """C2 crane, retaining an explicit non-flipping basis through the zenith.

    Reduced motion uses this same deliberate path; it has no shake, roll,
    stochastic sway or lens pulse to remove.
    """
    t = _clock(seconds)
    data = CAMERA if config is None else config
    travel = data['starting_party_metres']+data['speed_metres_per_second']*t
    h = _keys(t,data['height_keys'])
    focal = _keys(t,data['focal_keys'])
    overhead = data['overhead_seconds']
    if t <= overhead:
        ahead = 3*(1-_smooth(t/overhead))
        y = travel+ahead
    else:
        if t <= data['reframe_seconds']:
            y = _hermite(t,overhead,PARTY_START+PARTY_SPEED*overhead,PARTY_SPEED,
                         data['reframe_seconds'],145,2)
        else:
            y = _hermite(t,data['reframe_seconds'],145,2,DURATION,150,2)
    pitch = math.radians(_keys(t,data['pitch_degree_keys']))
    forward = [0.0,-math.cos(pitch),math.sin(pitch)]
    position = [0.0,y,h]
    up = [0.0,forward[2],-forward[1]]
    return {'space':'local_bridge_ascent','position':position,
        'target':[position[i]+forward[i] for i in range(3)],
        'forward':forward,'right':[-1.0,0.0,0.0],'up':up,
        'focal_pixels':focal,'principal_point':[480.0,320.0],
        'fov_degrees':math.degrees(2*math.atan(320/focal)), 'fov_axis':'vertical',
        'pitch_radians':math.atan2(forward[2],-forward[1]),
        'party_travel_metres':travel,'direction':'toward_mainland_then_down',
        'tracking_direction':'toward_veinhold','framing':'mainland_up_fortress_down'}


def project_world(point,camera):
    if len(point)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in point):
        raise ValueError('Invalid ascent world point')
    delta=[point[i]-camera['position'][i] for i in range(3)]
    dot=lambda vector:sum(delta[i]*vector[i] for i in range(3))
    depth=dot(camera['forward'])
    if depth<=.05:return None
    f=camera['focal_pixels']
    return [480+f*dot(camera['right'])/depth,320-f*dot(camera['up'])/depth,depth]


def actor_states_at(seconds, reduced_motion=False):
    t=_clock(seconds);camera=camera_at(t,reduced_motion);actors=[]
    for record in ACTORS:
        phase=(t+record['phase_offset_seconds'])%.8
        if .8-phase<1e-9:phase=0.0
        frame=min(47,int(math.floor(phase*60+1e-8)))
        world=[record['lane_metres'],camera['party_travel_metres']+record['offset_metres'],0.0]
        body=[world[0],world[1],.9]
        relative=[camera['position'][i]-body[i] for i in range(3)]
        elevation=math.degrees(math.atan2(relative[2],math.hypot(relative[0],relative[1])))
        depth=project_world(body,camera)[2]
        actors.append({**record,'world_position_metres':world,'frame_index':frame,
            'cycle_phase':phase,'cycle_seconds':.8,'view_elevation_degrees':elevation,
            'view_azimuth_degrees':math.degrees(math.atan2(relative[0],relative[1])),
            'ground_anchor':project_world(world,camera)[:2],
            'pixels_per_metre':camera['focal_pixels']/depth,
            'scale':camera['focal_pixels']/depth/500,
            'depth_metres':depth})
    return {'local_time':t,'global_time':47+t,'phase':'bridge_ascent',
        'reduced_motion':bool(reduced_motion),'camera':camera,'runners':actors}


def read_ascent_timing():
    return tuple({'id':actor['id'],'cycle_seconds':.8,
        'phase_offset_seconds':actor['phase_offset_seconds'],
        'contacts':[{'frame':0,'foot':'near','time_seconds':0},
                    {'frame':24,'foot':'far','time_seconds':.4}]} for actor in ACTORS)


def guard_states_at(seconds,reduced_motion=False):
    t=_clock(seconds);camera=camera_at(t,reduced_motion);result=[]
    for index,(x,y) in enumerate(FROZEN_GUARDS):
        result.append({'id':f'carcovian_guard_{index+1}','kind':'frozen',
            'world_position_metres':[x,y,.1],'cycle_phase':0.0,'frame_index':0})
    for index,(x,y,phase) in enumerate(REINFORCEMENTS):
        cycle=(t+phase)%.8
        if .8-cycle<1e-9:cycle=0.0
        result.append({'id':f'carcovian_reinforcement_{index+1}','kind':'reinforcement',
            'world_position_metres':[x,y-4*t,0.0],'cycle_phase':cycle,
            'frame_index':min(15,int(math.floor(cycle*20+1e-8)))})
    for actor in result:
        world=actor['world_position_metres'];body=[world[0],world[1],world[2]+.9]
        point=project_world(body,camera)
        actor['depth_metres']=None if point is None else point[2]
        actor['ground_anchor']=project_world(world,camera)
        actor['pixels_per_metre']=None if point is None else camera['focal_pixels']/point[2]
        actor['view_elevation_degrees']=math.degrees(math.atan2(camera['position'][2]-body[2],
            math.hypot(camera['position'][0]-body[0],camera['position'][1]-body[1])))
    return result


def reinforcement_states_at(seconds,reduced_motion=False):
    return [actor for actor in guard_states_at(seconds,reduced_motion)
            if actor['kind']=='reinforcement']


def acoustic_sources_at(seconds,reduced_motion=False):
    group=reinforcement_states_at(seconds,reduced_motion)
    return {'warning':[0.0,299.0819285747636,12.0],
            'machinery':[0.0,325.0,3.0],
            'reinforcements':[sum(actor['world_position_metres'][i] for actor in group)/len(group)
                              for i in range(3)]}


def camera_signature():
    return sha256(json.dumps({'camera':CAMERA,'actors':ACTORS,'duration':DURATION,
        'frozen_guards':FROZEN_GUARDS,'reinforcements':REINFORCEMENTS,'gate':GATE},
        sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _profile_records(data,kind):
    if kind=='party':
        transition=data.get('transition_frames');cycle=data.get('overhead_cycle',{}).get('frames')
        if (not isinstance(transition,list) or [row.get('index') for row in transition]!=list(range(133))
                or not isinstance(cycle,list) or len(cycle)!=48):
            raise ValueError('Ascent party needs its complete close transition and48-pose cycle')
        return [*transition,*cycle]
    frozen=data.get('frozen');live=data.get('live',{}).get('frames')
    if not isinstance(frozen,list) or len(frozen)!=4 or not isinstance(live,list) or len(live)!=16:
        raise ValueError('Ascent guard export lacks its four stasis poses or16-pose live cycle')
    return [*frozen,*live]


def performance_signature(manifest_path=ASCENT_SCENE,*,allowed_root=None):
    """Fingerprint portable art declarations without decoding source PNGs.

    The offline exporter/check additionally verifies these declared digests
    against the actual raw/export bytes. Runtime only owns native pictures.
    """
    path=Path(manifest_path).resolve()
    root=path.parent if allowed_root is None else Path(allowed_root).resolve()
    if not path.is_relative_to(root):raise ValueError('Ascent signature leaves cinematic root')
    scene=json.loads(path.read_text())
    parties=scene.get('party_performances',{})
    if set(parties)!={'lucan','iselin','crown_soldier'}:
        raise ValueError('Ascent signature requires all three portable party export manifests')
    sources={}
    for actor,relative in [*sorted(parties.items()),('guards',scene.get('guard_performance'))]:
        if not isinstance(relative,str) or Path(relative).is_absolute():
            raise ValueError('Invalid ascent art export manifest')
        profile=(path.parent/relative).resolve()
        if not profile.is_relative_to(root):raise ValueError('Ascent art manifest leaves cinematic root')
        data=json.loads(profile.read_text())
        hashes=data.get('source_sha256',{})
        records=_profile_records(data,'guards' if actor=='guards' else 'party')
        for record in records:
            filename=record.get('file',record.get('source'))
            digest=hashes.get(filename)
            if (not isinstance(filename,str) or not filename or Path(filename).is_absolute()
                    or not isinstance(digest,str) or len(digest)!=64
                    or any(c not in '0123456789abcdef' for c in digest)):
                raise ValueError('Ascent art export lacks a portable declared PNG hash')
        sources[actor]={'manifest':relative,'declarations':data}
    payload={'signature_version':1,'camera_signature':camera_signature(),
             'scene':scene,'art_exports':sources}
    return sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


class CinematicBridgeAscent:
    """Eight native-picture slots, with no decoded source-character bank."""
    def __init__(self, manifest_path=ASCENT_SCENE, *, allowed_root=None, cache_size=8):
        from cinematic_perspective import CinematicPerspective
        self.path=Path(manifest_path).resolve()
        root=self.path.parent if allowed_root is None else Path(allowed_root).resolve()
        if not self.path.is_relative_to(root):raise ValueError('Ascent scene leaves cinematic root')
        self.data=json.loads(self.path.read_text())
        if (self.data.get('version')!=1 or self.data.get('duration_seconds')!=DURATION
                or self.data.get('render_size')!=list(RENDER_SIZE)
                or self.data.get('camera')!=CAMERA or self.data.get('actors')!=list(ACTORS)
                or self.data.get('baked_characters') is not True):
            raise ValueError('Ascent scene does not match the shared camera/formation')
        if type(cache_size) is not int or cache_size!=8:
            raise ValueError('Ascent bank reserves exactly eight native picture slots')
        self.duration=DURATION;self.cache_size=cache_size
        relative=self.data.get('environment')
        if not isinstance(relative,str) or Path(relative).is_absolute():
            raise ValueError('Invalid ascent bank path')
        bank=(self.path.parent/relative).resolve()
        if not bank.is_relative_to(root):raise ValueError('Ascent bank leaves cinematic root')
        metadata=json.loads(bank.read_text())
        if (metadata.get('baked_characters') is not True or metadata.get('camera_signature')!=camera_signature()
                or metadata.get('performance_signature')!=performance_signature(self.path,allowed_root=root)):
            raise ValueError('Ascent baked performance is stale or lacks its complete cast')
        self.environment=CinematicPerspective(bank,allowed_root=root,cache_size=cache_size)
        try:
            self.segments=self.data.get('environment_segments',{})
            if self.segments!={'normal':'bridge_ascent','reduced_motion':'bridge_ascent_reduced'}:
                raise ValueError('Invalid ascent environment segments')
            if self.environment.fps!=60:raise ValueError('Ascent bank must run at60Hz')
            for name in self.segments.values():
                self.environment.validate_segment(name,DURATION)
                segment=self.environment.segments[name];rows=segment['metadata']
                if segment['loop'] is not None:
                    raise ValueError('Ascent camera segments must not loop')
                if len(segment['frames'])!=481 or len(rows)!=481 or len(segment['alarm_frames'])!=481:
                    raise ValueError('Ascent needs481 inclusive native camera samples')
                for index,row in enumerate(rows):
                    if abs(row.get('time_seconds',-1)-index/FPS)>1e-8:
                        raise ValueError('Ascent camera samples do not follow the60Hz clock')
                    expected=camera_at(index/FPS)
                    actual=row.get('camera',{})
                    for key in ('position','target','up','right','forward'):
                        if len(actual.get(key,[]))!=3 or any(abs(a-b)>1e-7 for a,b in zip(actual[key],expected[key])):
                            raise ValueError('Ascent picture camera differs from actor/audio staging')
                    if abs(actual.get('focal_pixels',0)-expected['focal_pixels'])>1e-7:
                        raise ValueError('Ascent picture lens differs from actor/audio staging')
        except BaseException:
            self.environment.close()
            raise

    def validate_duration(self,seconds):
        if type(seconds) not in (int,float) or not math.isfinite(seconds) or abs(seconds-DURATION)>1e-8:
            raise ValueError('Ascent scene and shot durations differ')

    def samples(self,seconds,reduced_motion=False):
        state=actor_states_at(seconds,reduced_motion)
        state['guards']=guard_states_at(seconds,reduced_motion)
        mode='reduced_motion' if reduced_motion else 'normal'
        # Generic representative-image dissolves would detach the moving cast.
        state['environment']=self.environment.samples(self.segments[mode],state['local_time'],False)
        return state

    def preload(self,seconds=0,*,reduced_motion=False,blocking=False,max_slots=None,priority='active'):
        state=self.samples(seconds,reduced_motion)
        self.environment.preload(state['environment']['segment'],state['local_time'],
            reduced_motion=False,alarm_active=False,blocking=blocking,
            max_slots=self.cache_size if max_slots is None else max_slots,priority=priority)
        return state

    def prepare(self,seconds=0,*,reduced_motion=False):
        return self.preload(seconds,reduced_motion=reduced_motion,blocking=True)

    def draw(self,target,state):
        if target.get_size()!=RENDER_SIZE:raise ValueError('Ascent requires the native picture size')
        self.environment.draw(target,state['environment'],alarm_active=False)

    @property
    def cache_info(self):
        data=dict(self.environment.cache_info)
        data.update({'byte_capacity':8*960*640*4,
            'actor_cache':{'surfaces':0,'bytes':0,'decoded_bytes':0,'pending_bytes':0},
            'environment_cache':dict(self.environment.cache_info)})
        return data

    def close(self):
        self.environment.close()
