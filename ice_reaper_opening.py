"""The thirty-two-second Ice Reaper rescue and duel cinematic."""
from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import pygame

from opening_cinematic import OpeningCinematic, VIEW_SIZE, _smooth


SCENE = Path(__file__).resolve().parent/'assets/story/ice_reaper_opening/scene.json'
ACTION_ASSETS = SCENE.parent.parent/'ice_reaper_rescue'


class IceReaperOpening(OpeningCinematic):
    def __init__(self, game, *, scene_path=SCENE):
        super().__init__(game, scene_path=scene_path)

    def _load(self):
        super()._load()
        if getattr(self, 'action_stage', None) is None:
            from ice_reaper_action import IceReaperActionStage
            from ice_reaper_audio import IceReaperActionAudio
            self.action_stage = IceReaperActionStage(ACTION_ASSETS, strict=True)
            self.action_audio = IceReaperActionAudio(self.game)

    def reset(self):
        if getattr(self, 'action_audio', None) is not None:
            self.action_audio.reset()
        if getattr(self, 'action_stage', None) is not None:
            self.action_stage.reset()
        super().reset()

    def _finish(self, reason):
        if getattr(self, 'action_audio', None) is not None:
            self.action_audio.stop()
        super()._finish(reason)

    def update(self, seconds):
        previous = self.elapsed
        playing = (self.active and not self.paused and self.focused
                   and getattr(self.game, '_music_focused', True))
        super().update(seconds)
        if getattr(self, 'action_audio', None) is not None and self.active:
            self.action_audio.update(previous, self.elapsed, playing=playing)

    def handle_event(self, event):
        super().handle_event(event)
        if getattr(self, 'action_audio', None) is not None:
            if (not self.active or self.paused or not self.focused
                    or not getattr(self.game, '_music_focused', True)):
                self.action_audio.pause()
            else:
                self.action_audio.resume()

    def _layout(self, painter):
        super()._layout(painter)
        if self.elapsed >= 5.0 and self.caption_layout is not None:
            # The new shot shows the boss high in frame. Keep Lucan's offscreen
            # line below the action rather than using the old party's bounds.
            layout = self.caption_layout
            dy = self.skip_rect.top-9-layout.panel.bottom
            self.caption_rect = layout.panel.move(0, dy)
            self.caption_layout = replace(
                layout, panel=self.caption_rect,
                portrait=layout.portrait.move(0, dy) if layout.portrait else None,
                text_origin=(layout.text_origin[0], layout.text_origin[1]+dy),
                anchor=(layout.anchor[0], layout.anchor[1]+dy))

    def _validate(self):
        required = {'version', 'id', 'duration', 'canvas', 'viewport', 'actors',
                    'layers', 'acting', 'shots', 'dialogue', 'dynamic_props',
                    'brush', 'camera_shake', 'hover', 'camera_bounds'}
        if not isinstance(self.data, dict) or not required <= self.data.keys():
            raise ValueError('Incomplete Ice Reaper opening scene')
        if any(not isinstance(self.data[name], dict) for name in
               ('brush', 'camera_shake', 'hover', 'dynamic_props', 'acting')):
            raise ValueError('Invalid Ice Reaper scene metadata')
        super()._validate()
        data = self.data
        if data['id'] != 'ice_reaper_opening' or data['duration'] != 32.0:
            raise ValueError('The Ice Reaper cinematic must last thirty-two seconds')
        actors = [record['id'] for record in data['actors']]
        if len(actors) != 5 or set(actors) != {'caelan', 'mira', 'rhea', 'lucan', 'ice_reaper'}:
            raise ValueError('Ice Reaper opening has an incorrect cast')
        for actor in data['actors']:
            if type(actor.get('pixel_scale', 1)) is not int or actor.get('pixel_scale', 1) not in (1, 2):
                raise ValueError('Invalid Ice Reaper actor pixel scale')
        for key in ('brush', 'camera_shake'):
            cue = data[key]
            if (not {'start', 'end'} <= cue.keys()
                    or any(type(cue[name]) not in (int, float)
                           or not math.isfinite(cue[name]) for name in ('start', 'end'))
                    or not 0 <= cue['start'] < cue['end'] <= data['duration']):
                raise ValueError(f'Invalid Ice Reaper {key} timing')
        for cue, key, low, high in ((data['brush'], 'travel', 1, 960),
                                    (data['camera_shake'], 'strength', 0, 2),
                                    (data['hover'], 'amplitude', 0, 3),
                                    (data['hover'], 'period', .1, 10)):
            value = cue.get(key)
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or not low <= value <= high):
                raise ValueError(f'Invalid Ice Reaper {key}')
        brush_layers = [record for record in data['layers'] if 'brush_direction' in record]
        if (len(brush_layers) != 2
                or any(type(record['brush_direction']) is not int
                       or not record.get('foreground') for record in brush_layers)
                or {record['brush_direction'] for record in brush_layers} != {-1, 1}):
            raise ValueError('Ice Reaper brush needs two opposing foreground layers')
        if not {'ice_prison_back', 'ice_prison_front', 'glacial_shard'} <= data['dynamic_props'].keys():
            raise ValueError('Ice Reaper opening is missing a required ice prop')
        if 'rhea' in data.get('position_tracks', {}):
            raise ValueError('Frozen Rhea cannot walk during the opening')
        expected = [('Caelan', 'Rhea! No!'), ('Lucan', "Cael, go! I'll cover!"),
                    ('Rhea', 'Thanks guys, now leave her to me...'),
                    ('Caelan', 'Rhea...are you su-')]
        if [(cue['speaker'], cue['text']) for cue in data['dialogue']] != expected:
            raise ValueError('Ice Reaper cinematic must preserve its four authored dialogue cues')
        if data['dialogue'][-1]['end'] != 24.:
            raise ValueError('Caelan must be interrupted by the staff sweep at 24 seconds')

    @property
    def brush_progress(self):
        cue = self.data['brush']
        return _smooth((self.elapsed-cue['start'])/(cue['end']-cue['start']))

    @property
    def camera_position(self):
        point = super().camera_position
        cue = self.data['camera_shake']
        if not self.reduced_motion and cue['start'] <= self.elapsed < cue['end']:
            envelope = min(1., (self.elapsed-cue['start'])/.06,
                           (cue['end']-self.elapsed)/.06)
            point += pygame.Vector2(math.sin(self.elapsed*51+.7),
                                    math.sin(self.elapsed*69+.21)*.65)*cue['strength']*envelope
            bounds = self.data['camera_bounds']
            point.x = max(bounds[0], min(bounds[2], point.x))
            point.y = max(bounds[1], min(bounds[3], point.y))
        return point

    @property
    def camera_zoom(self):
        if self.elapsed >= 5.0:
            return 1.0
        if self.reduced_motion:
            return self.shot_record.get('zoom', (1., 1.))[-1]
        return super().camera_zoom

    @property
    def fade_alpha(self):
        return round(255*max(0.,min(1.,(self.elapsed-31.1)/.9)))

    def _hover_offset(self):
        if self.reduced_motion:
            return pygame.Vector2()
        cue = self.data['hover']
        return pygame.Vector2(0, math.sin(self.elapsed*math.tau/cue['period'])*cue['amplitude'])

    def actor_position(self, actor):
        point = super().actor_position(actor)
        return point+self._hover_offset() if actor == 'ice_reaper' else point

    def _draw_actors(self, canvas, camera):
        self._draw_prop(canvas, 'ice_prison_back', camera)
        for record, anchor, frames, transitions in sorted(self.actors,
                key=lambda actor: self.actor_position(actor[0]['id']).y):
            image = self._actor_frame(record['id'], frames, transitions)
            scale = record.get('pixel_scale', 1)
            if scale != 1:
                image = pygame.transform.scale(image, (image.get_width()*scale, image.get_height()*scale))
            point = self.actor_position(record['id'])-camera
            canvas.blit(image, (round(point.x-anchor[0]*scale), round(point.y-anchor[1]*scale)))
        self._draw_prop(canvas, 'ice_prison_front', camera)

    def _brush_layer(self, canvas, record, image, camera):
        progress = self.brush_progress
        if progress >= 1:
            return
        if self.reduced_motion:
            image.set_alpha(round(255*(1-progress)))
            canvas.blit(image, (-round(camera.x), -round(camera.y)))
            image.set_alpha(255)
        else:
            x = record['brush_direction']*self.data['brush']['travel']*progress-camera.x
            canvas.blit(image, (round(x), -round(camera.y)))

    def _charge(self, canvas, camera):
        record = self.data['dynamic_props']['glacial_shard']
        point = pygame.Vector2(record['position'])-camera+self._hover_offset()
        point.y -= record['anchor'][1]/2
        layer = pygame.Surface(VIEW_SIZE, pygame.SRCALPHA)
        time = 0 if self.reduced_motion else self.elapsed
        for radius, alpha in ((36, 8), (24, 12), (13, 17)):
            pygame.draw.circle(layer, (106, 192, 251, alpha),
                               (round(point.x), round(point.y)), radius)
        for index in range(10):
            angle = index*math.tau/10+time*1.7
            radius = 20+7*math.sin(time*2.3+index)
            center = point+pygame.Vector2(math.cos(angle)*radius, math.sin(angle)*radius*.8)
            x, y = round(center.x), round(center.y)
            pygame.draw.polygon(layer, (197, 240, 255, 145),
                                [(x,y-2),(x+1,y),(x,y+2),(x-1,y)])
        canvas.blit(layer, (0, 0))

    def _ground_shadows(self, canvas, camera):
        layer = pygame.Surface(VIEW_SIZE, pygame.SRCALPHA)
        for record in self.data['actors']:
            if record['id'] == 'ice_reaper':
                continue
            point = self.actor_position(record['id'])-camera
            width = 44 if record['id'] == 'rhea' else 24
            pygame.draw.ellipse(layer, (38, 73, 103, 55),
                                (round(point.x-width/2), round(point.y)-2, width, 5))
        canvas.blit(layer, (0, 0))

    def _snow(self, canvas, camera):
        if self.reduced_motion:
            return
        layer = pygame.Surface(VIEW_SIZE, pygame.SRCALPHA)
        for index in range(17):
            x = (index*109+self.elapsed*(3+index%4)-camera.x*.3)%VIEW_SIZE[0]
            y = (index*61+self.elapsed*(7+index%3)-camera.y*.3)%VIEW_SIZE[1]
            pygame.draw.line(layer, (200, 235, 250, 85),
                             (round(x),round(y)), (round(x),round(y)+1))
        canvas.blit(layer, (0, 0))

    def _draw_scene(self, canvas, camera):
        if self.elapsed >= 5.0:
            self.action_stage.draw(canvas, self.elapsed, self.reduced_motion)
            return
        assert self.layers is not None
        canvas.fill('#101e34')
        for record, image in self.layers:
            if not record.get('foreground'):
                self._draw_layer(canvas, record, image, camera)
        self._ground_shadows(canvas, camera)
        self._charge(canvas, camera)
        self._draw_prop(canvas, 'glacial_shard', camera-self._hover_offset())
        self._draw_actors(canvas, camera)
        self._snow(canvas, camera)
        for record, image in self.layers:
            if record.get('foreground'):
                if 'brush_direction' in record:
                    self._brush_layer(canvas, record, image, camera)
                else:
                    self._draw_layer(canvas, record, image, camera)
