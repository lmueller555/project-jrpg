"""Deterministic action accents and selectors for authored target reactions.

All points use the battle field's world coordinates, before its camera transform.
The caller owns action and impact clocks; drawing never starts a timer or alters
combat state. Enemy recoil uses the existing two distinct hurt drawings.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

import pygame


DART_RELEASE_AT = .75
IMPACT_FLASH_SECONDS = .08
REACTION_TIMINGS = {'bat': (.15, .37), 'ridgeback_tusker': (.18, .42),
                    'lithrusk': (.2, .5), 'veylume': (.2, .5)}


def _get(record, name, default=None):
    return record.get(name, default) if isinstance(record, Mapping) else getattr(record, name, default)


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f'{name} must be numeric')
    if not math.isfinite(value):raise ValueError(f'Invalid {name}')
    return float(value)


def _point(value):
    return (_number(value[0], 'effect point'), _number(value[1], 'effect point'))


def _clamp(value):return max(0., min(1., value))


def _xy(point):return round(point[0]), round(point[1])


def _color(color, opacity):return (*color, round(255*_clamp(opacity)))


def target_reaction(actor, age, *, direction=1, reduced_motion=False, guarded=False):
    """Select the enemy's hurt drawings from seconds since an impact event.

    ``direction`` points away from the attacker. Bat recoil folds its wings and
    opens them again; Tusker lifts its head then settles its shoulder. Their
    authored floor anchors stay at the same height. The small horizontal accent
    settles to zero before the drawings finish and is disabled in reduced motion.
    Caelan's ``guarded`` selector uses a 240 ms brace, or 360 ms hurt recovery.
    Living targets can return to idle when ``active`` becomes false. Lethal
    reactions remain the scene's defeat animation responsibility.
    """
    age = _number(age, 'reaction age')
    direction = _number(direction, 'reaction direction')
    first, duration = REACTION_TIMINGS.get(actor, (.16, .4))
    if actor in ('caelan', 'player'):
        first, duration = (.12, .24) if guarded else (.16, .36)
    active = 0 <= age < duration
    frame = 0 if age < first else 1
    kick = min(1., max(0., age)/.045) * _clamp((duration-age)/(duration-.065))
    distance = 4. if actor == 'bat' else 2. if actor == 'ridgeback_tusker' else 3.
    offset = (0., 0.) if reduced_motion or not active else (distance*direction*kick, 0.)
    state = ('guard_impact' if guarded else 'hurt_recover') if actor in ('caelan', 'player') else 'hurt'
    return {'active': active, 'state': state if active else 'idle',
            'time_ms': max(0., min(age, duration))*1000,
            'frame_index': frame if active else None, 'duration': duration,
            'offset': offset}


class BattleActionEffects:
    """Reusable, seekable casting, projectile, contact and ground dust layer.

    ``action`` accepts a BattleAction or mapping. ``elapsed`` optionally overrides
    its elapsed seconds. Pose ``anchors`` are already in world coordinates and
    may include ``cast_origin`` (or active_gem/guard/blade_tip), ``target_hit``,
    ``release_origin``, ``dash_origin``, ``landing``, ``dash_at`` and ``landing_at``.
    Supplying ``impact_age`` uses the authoritative impact event clock; otherwise
    the resolved action supplies it. Set ``show_impact=False`` when the scene draws
    its recorded impacts separately with :meth:`draw_impact`.
    """
    MAGIC = ((46, 95, 153), (111, 195, 238), (231, 250, 255))
    AETHER = ((98, 65, 149), (187, 151, 238), (255, 245, 255))
    CONTACT = ((136, 95, 58), (246, 199, 119), (255, 247, 214))
    DUST = ((105, 100, 67), (157, 145, 99), (198, 181, 126))
    ELECTRIC = ((37, 77, 113), (94, 215, 242), (255, 236, 153))
    FIRE = ((129, 41, 25), (246, 133, 58), (255, 238, 169))
    ICE = ((54, 99, 151), (155, 220, 250), (242, 255, 255))
    ELECTRIC_ACTIONS = frozenset(('veylume_static_spark', 'veylume_veinflash'))
    FIRE_ACTIONS = frozenset(('flame_edge', 'embravyr_emberwash', 'embravyr_furnace_lunge'))
    ICE_ACTIONS = frozenset(('ice_edge', 'nivareth_rime_needle', 'nivareth_glassfall',
                             'nivareth_frostspire_thrust'))

    def __init__(self):
        self._layer = None

    def _palette(self, name, kind='magical'):
        if name in self.ELECTRIC_ACTIONS:return self.ELECTRIC
        if name in self.FIRE_ACTIONS:return self.FIRE
        if name in self.ICE_ACTIONS:return self.ICE
        if name == 'aether_edge':return self.AETHER
        if name in ('aether_dart', 'aqua_edge') or kind == 'magical':return self.MAGIC
        return self.CONTACT

    @staticmethod
    def release_at(action):
        impact = _number(_get(action, 'impact_at', 1.1), 'impact time')
        default = DART_RELEASE_AT if _get(action, 'action', '') == 'aether_dart' else impact*.45
        release = _get(action, 'release_at')
        return max(0., min(impact, _number(default if release is None else release, 'release time')))

    def sample(self, actor_point, target_point, action, elapsed=None, anchors=None,
               reduced_motion=False):
        actor_point, target_point = _point(actor_point), _point(target_point)
        anchors = anchors or {}
        age = _number(_get(action, 'elapsed', 0.) if elapsed is None else elapsed, 'action age')
        impact = _number(_get(action, 'impact_at', 0.), 'impact time')
        duration = _number(_get(action, 'duration', max(impact, 1.)), 'action duration')
        if impact < 0 or duration < impact:raise ValueError('Invalid effects action timing')
        name, kind = _get(action, 'action', ''), _get(action, 'kind', '')
        direction = -1 if target_point[0] < actor_point[0] else 1
        fallback = (actor_point[0]+direction*25, actor_point[1]-40)
        origin = next((anchors[key] for key in ('cast_origin', 'active_gem', 'guard', 'blade_tip')
                       if key in anchors), fallback)
        origin = _point(origin)
        release_origin = _point(anchors.get('release_origin', origin))
        hit = _point(anchors.get('target_hit', (target_point[0], target_point[1]-35)))
        release = self.release_at(action)
        magical = kind == 'magical' or name == 'aether_dart'
        charge = 0.
        projectile = None
        if magical and 0 <= age < release:
            charge = _clamp(age/max(.001, release*.72))
            if not reduced_motion:charge *= .89+.11*math.sin(age*19)
        if magical and release <= age < impact and not _get(action, 'resolved', False):
            fraction = _clamp((age-release)/max(.001, impact-release))
            start, end = pygame.Vector2(release_origin), pygame.Vector2(hit)
            point = start.lerp(end, fraction)
            if not reduced_motion:point.y -= math.sin(math.pi*fraction)*4
            delta = end-start
            heading = delta.normalize() if delta.length_squared() else pygame.Vector2(direction, 0)
            projectile = {'point': tuple(point), 'direction': tuple(heading), 'fraction': fraction}
        impact_age = anchors.get('impact_age')
        if impact_age is None and _get(action, 'resolved', False):impact_age = age-impact
        if impact_age is not None:impact_age = _number(impact_age, 'impact age')
        strength = self.impact_strength(impact_age)
        if kind not in ('physical', 'magical', 'spellblade') or not anchors.get('show_impact', True):strength = 0.
        dust = []
        if not reduced_motion and kind in ('physical', 'spellblade'):
            for key, clock_key, lifetime in (('dash_origin', 'dash_at', .18), ('landing', 'landing_at', .22)):
                if key not in anchors or clock_key not in anchors:continue
                dust_age = age-_number(anchors[clock_key], 'dust time')
                if 0 <= dust_age < lifetime:
                    dust.append({'point': _point(anchors[key]), 'age': dust_age,
                                 'duration': lifetime, 'direction': -direction,
                                 'landing': key == 'landing'})
        return {'action': name, 'kind': kind, 'age': age, 'duration': duration,
                'origin': origin, 'target_hit': hit, 'charge': charge,
                'release_at': release, 'projectile': projectile,
                'impact_age': impact_age, 'impact_strength': strength,
                'dust': dust, 'reduced_motion': bool(reduced_motion)}

    @staticmethod
    def impact_strength(age):
        if age is None:return 0.
        age = _number(age, 'impact age')
        return 1-age/IMPACT_FLASH_SECONDS if 0 <= age < IMPACT_FLASH_SECONDS-1e-9 else 0.

    def _canvas_layer(self, canvas):
        if self._layer is None or self._layer.get_size() != canvas.get_size():
            self._layer = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        self._layer.fill((0, 0, 0, 0))
        return self._layer

    def _draw_charge(self, layer, sample):
        strength, point = sample['charge'], pygame.Vector2(sample['origin'])
        if strength <= 0:return
        dark, mid, light = self._palette(sample['action'])
        radius = 3+round(strength*3)
        pygame.draw.circle(layer, _color(dark, strength*.28), _xy(point), radius+3)
        pygame.draw.circle(layer, _color(mid, strength*.9), _xy(point), radius, 1)
        pygame.draw.circle(layer, _color(light, strength), _xy(point), 2)
        if sample['reduced_motion']:return
        for i in range(5):
            angle = i*math.tau/5-sample['age']*2
            ray = pygame.Vector2(math.cos(angle), math.sin(angle))
            start = point+ray*(radius+3+(1-strength)*5)
            pygame.draw.line(layer, _color(mid, strength*.7), _xy(start), _xy(start-ray*2), 1)

    def _draw_projectile(self, layer, sample):
        entry = sample['projectile']
        if entry is None:return
        point, heading = pygame.Vector2(entry['point']), pygame.Vector2(entry['direction'])
        dark, mid, light = self._palette(sample['action'])
        if sample['action'] in self.ICE_ACTIONS:
            normal = pygame.Vector2(-heading.y, heading.x)
            pygame.draw.polygon(layer, _color(mid, .9), [_xy(point+heading*6),
                _xy(point+normal*3), _xy(point-heading*5), _xy(point-normal*3)])
            pygame.draw.line(layer, _color(light, 1.), _xy(point-heading*3), _xy(point+heading*5), 1)
            return
        if sample['action'] in self.FIRE_ACTIONS:
            normal = pygame.Vector2(-heading.y, heading.x)
            pygame.draw.polygon(layer, _color(mid, .9), [_xy(point+heading*4),
                _xy(point+normal*3-heading*2), _xy(point-heading*10), _xy(point-normal*3)])
            pygame.draw.line(layer, _color(light, 1.), _xy(point-heading*4), _xy(point+heading*3), 2)
            return
        if sample['action'] in self.ELECTRIC_ACTIONS:
            normal = pygame.Vector2(-heading.y, heading.x)
            size = 15 if sample['action'] == 'veylume_veinflash' else 9
            points = [point-heading*size,
                      point-heading*(size*.67)+normal*3,
                      point-heading*(size*.42)-normal*2, point]
            pygame.draw.lines(layer, _color(mid, .9), False, [_xy(p) for p in points], 2)
            pygame.draw.lines(layer, _color(light, 1.), False, [_xy(p) for p in points], 1)
            pygame.draw.circle(layer, _color(light, .9), _xy(point), 2)
            return
        if not sample['reduced_motion']:
            normal = pygame.Vector2(-heading.y, heading.x)
            tail = point-heading*18
            pygame.draw.polygon(layer, _color(dark, .38),
                                [_xy(tail), _xy(point+normal*4), _xy(point-normal*4)])
            pygame.draw.line(layer, _color(mid, .78), _xy(point-heading*10), _xy(point), 3)
        pygame.draw.circle(layer, _color(mid, .95), _xy(point), 4 if not sample['reduced_motion'] else 3)
        pygame.draw.line(layer, _color(light, 1.), _xy(point-heading*2), _xy(point+heading*2), 2)

    def _draw_impact(self, layer, point, age, action, reduced_motion=False):
        strength = self.impact_strength(age)
        if not strength:return
        point = pygame.Vector2(point)
        name, kind = _get(action, 'action', action if isinstance(action, str) else ''), _get(action, 'kind', '')
        palette = self._palette(name, kind)
        _, mid, light = palette
        if reduced_motion:
            pygame.draw.circle(layer, _color(mid, strength*.65), _xy(point), 5, 1)
            pygame.draw.circle(layer, _color(light, strength*.8), _xy(point), 2)
            return
        expansion = _clamp(age/IMPACT_FLASH_SECONDS)
        pygame.draw.circle(layer, _color(mid, strength*.35), _xy(point), 7+round(expansion*5), 1)
        for i in range(6):
            angle = i*math.tau/6+.25
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            pygame.draw.line(layer, _color(mid, strength*.85), _xy(point+direction*(4+expansion*4)),
                             _xy(point+direction*(9+expansion*6)), 1)
        pygame.draw.line(layer, _color(light, strength), _xy(point+(-5, -2)), _xy(point+(5, 2)), 2)
        pygame.draw.line(layer, _color(light, strength), _xy(point+(-1, -5)), _xy(point+(1, 5)), 2)

    def _draw_dust(self, layer, point, age, direction, landing=False):
        duration = .22 if landing else .18
        if not 0 <= age < duration:return
        phase, point = age/duration, pygame.Vector2(point)
        for i in range(4):
            side = (-1 if i%2 else 1) if landing else direction
            distance = (2+i*2)*(1+phase*1.6)
            center = point+pygame.Vector2(side*distance, -1-math.sin(phase*math.pi)*(2+i%2))
            radius = max(1, round((2+i%2)*(1-phase*.6)))
            pygame.draw.ellipse(layer, _color(self.DUST[i%3], (1-phase)*.55),
                                (round(center.x-radius), round(center.y-1), radius*2, 2))

    def draw(self, canvas, actor_point, target_point, action, elapsed=None,
             anchors=None, reduced_motion=False):
        sample = self.sample(actor_point, target_point, action, elapsed, anchors, reduced_motion)
        layer = self._canvas_layer(canvas)
        self._draw_charge(layer, sample)
        self._draw_projectile(layer, sample)
        if sample['impact_strength']:
            self._draw_impact(layer, sample['target_hit'], sample['impact_age'], action, reduced_motion)
        for entry in sample['dust']:
            self._draw_dust(layer, entry['point'], entry['age'], entry['direction'], entry['landing'])
        canvas.blit(layer, (0, 0))
        return sample

    def draw_impact(self, canvas, point, age, action='', reduced_motion=False):
        """Draw one event-owned flash; it expires after exactly 80 ms."""
        point = _point(point)
        if not self.impact_strength(age):return
        layer = self._canvas_layer(canvas)
        self._draw_impact(layer, point, age, action, reduced_motion)
        canvas.blit(layer, (0, 0))

    def draw_dust(self, canvas, point, age, direction=1, *, landing=False, reduced_motion=False):
        """Draw departure/landing dust from an explicit choreography boundary."""
        point, age = _point(point), _number(age, 'dust age')
        direction = _number(direction, 'dust direction')
        if reduced_motion:return
        layer = self._canvas_layer(canvas)
        self._draw_dust(layer, point, age, direction, landing)
        canvas.blit(layer, (0, 0))

    def draw_electric_charge(self, canvas, point, elapsed, *, reduced_motion=False):
        """A small local, seekable charge cue; never a full-screen flash."""
        point = pygame.Vector2(_point(point))
        elapsed = _number(elapsed, 'charge age')
        layer = self._canvas_layer(canvas)
        _, mid, light = self.ELECTRIC
        phase = 0. if reduced_motion else elapsed*2.4
        pygame.draw.circle(layer, _color(mid, .55), _xy(point), 5, 1)
        pygame.draw.circle(layer, _color(light, .85), _xy(point), 2)
        if not reduced_motion:
            for index in range(3):
                angle = phase+index*math.tau/3
                direction = pygame.Vector2(math.cos(angle), math.sin(angle))
                normal = pygame.Vector2(-direction.y, direction.x)
                points = [point+direction*6, point+direction*9+normal*2,
                          point+direction*11-normal, point+direction*14]
                pygame.draw.lines(layer, _color(mid, .8), False, [_xy(p) for p in points], 1)
        canvas.blit(layer, (0, 0))
