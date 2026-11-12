"""Small, registered visual beats for the portrait-led regent visit.

The quest owns progress and movement. This view owns only temporary approved
body drawings, attention and table props; reading is always player paced.
"""
import math

import pygame
from prop_presentation import personal_prop_visible

from social import facing_toward


class RegentActions:
    DURATIONS = {'caelan_scabbard': .85, 'meal_settle': .8,
                 'pass_bread': 1., 'tomas_eat': 1.45, 'lucan_watch': 1.2,
                 'open_survey': .9, 'clear_plates': .9,
                 'open_plan': .9, 'open_account': .75,
                 'survivor_alarm': 1.15, 'lucan_disbelief': 1.25,
                 'survivor_aid': 1.35}

    def __init__(self, owner):
        self.owner = owner;self.game = owner.game;self.dining = owner.dining
        self._images = {}
        self._poses = {}
        self._sword = None
        self.reset()

    def _image(self, path):
        if path not in self._images:self._images[path] = self.dining.image(path)
        return self._images[path]

    def _hand_pose(self, direction):
        image = self._image('assets/story/elira/give_right.png')
        return pygame.transform.flip(image, True, False) if direction == 'left' else image

    def _actors(self):
        result = {'caelan': self.game.player, 'serene': self.owner.serene,
                  'mother_serene': self.owner.serene,
                  'tomas': self.owner.tomas, 'aldric': self.owner.aldric,
                  'regent_clerk': self.owner.clerk, 'regent_driver': self.owner.driver}
        lucan = getattr(self.owner, 'lucan', None)
        if lucan is not None:result['lucan'] = lucan
        survivor = getattr(self.owner, 'survivor', None)
        if survivor is not None:result['regent_survivor'] = survivor
        return result

    def _owned_actor(self, actor):
        return actor is self.game.player or not self.owner._handed_off(actor)

    def _pose(self, actor, image, anchor, *, position=None, sort_y=None):
        if not self._owned_actor(actor):return
        previous = self._poses.setdefault(actor, {})
        values = [('story_sprite', image), ('story_draw_anchor', tuple(anchor))]
        if position is not None:values.append(('story_position', tuple(position)))
        if sort_y is not None:values.append(('story_sort_y', sort_y))
        for key, value in values:
            if key not in previous:previous[key] = (hasattr(actor, key), getattr(actor, key, None), value)
            else:previous[key] = (*previous[key][:2], value)
            setattr(actor, key, value)

    def _release_actor_pose(self, actor):
        """Release one drawing without disturbing another actor's active beat."""
        for key, (existed, before, ours) in self._poses.pop(actor, {}).items():
            if getattr(actor, key, None) is not ours and getattr(actor, key, None) != ours:continue
            if existed:setattr(actor, key, before)
            elif hasattr(actor, key):delattr(actor, key)

    def release(self):
        """Clear only drawings belonging to this view, leaving other owners alone."""
        for actor in tuple(self._poses):self._release_actor_pose(actor)
        self.active_cue = None;self.clock = 0.;self._script = None;self._seen = set()
        self._seated = False

    def reset(self):
        self.release()
        self._map_open = self._account_open = False
        self._meal_clock = 0.

    def _line(self):
        social = self.game.social
        if not social.active or not self.owner.dialogue:return None
        if social.script_identifier != 'regent_'+self.owner.dialogue:return None
        if social.page is None:return None
        index = social.page.get('source_line', 0)
        lines = getattr(self.owner, '_dialogue_lines', None) or self.owner.lines.get(self.owner.dialogue, ())
        return (index, lines[index]) if 0 <= index < len(lines) else None

    def _seating_enabled(self):
        return (self.owner.stage in ('welcome', 'hosted')
                and bool(getattr(self.owner, '_meal_ready', False)))

    def _seat_records(self):
        return self.owner.points.get('meal_seats', {})

    def _apply_seating(self):
        if not self._seating_enabled():return
        actors = self._actors()
        for identifier, record in self._seat_records().items():
            actor = actors.get(identifier)
            if (actor is None or not self._owned_actor(actor)
                    or self.owner._world(actor) is not self.dining):continue
            image = self._image(record['image'])
            if record.get('flip_x'):image = pygame.transform.flip(image, True, False)
            actor.facing = record['facing'];actor.moving = False
            if self._meal_clock < .35:
                fraction = min(1., self._meal_clock/.35)
                fraction = fraction*fraction*(3-2*fraction)
                position = pygame.Vector2(record['approach']).lerp(record['position'], fraction)
                frames = actor.walks[record['facing']]
                frame = frames[int(self._meal_clock/.12) % len(frames)]
                image = frame[0] if isinstance(frame, tuple) else frame
                self._pose(actor, image, actor.draw_anchor, position=position,
                           sort_y=position.y+actor.probe_size[1]/2)
            else:
                self._pose(actor, image, record['anchor'], position=record['position'],
                           sort_y=record['sort_y'])
            self._seated = True

    def _attention(self, line):
        actors = self._actors();speaker = actors.get(line.get('speaker'))
        if speaker is None:return
        focus = speaker.position
        if self.owner.dialogue == 'discussion' and self.active_cue in ('open_survey', 'open_plan', 'open_account'):
            focus = pygame.Vector2(168, 184)
        for actor in actors.values():
            if actor is speaker or actor is self.game.player or not self._owned_actor(actor):continue
            if self.owner._world(actor) is not self.game.world:continue
            # Seated bodies keep their chair-facing orientation. In particular,
            # Lucan's north-side place already gives him sight of the entrance.
            if self._seating_enabled() and actor.data['id'] in self._seat_records():continue
            direction = facing_toward(focus-actor.position)
            if actor is getattr(self.owner, 'lucan', None) and self.active_cue == 'lucan_watch':direction = 'front'
            actor.facing = direction
            if actor is self.owner.serene or actor is self.owner.tomas:
                actor.story_sprite = actor.idles[direction]

    def _apply_survivor_rest(self):
        """The injured man stays on the existing bench while the party leaves."""
        survivor = getattr(self.owner, 'survivor', None)
        record = self.owner.points.get('survivor_seat')
        if survivor is None:return
        resting = getattr(self.owner,'survivor_resting',False)
        if (not record or not getattr(survivor,'story_visible',False) or not resting
                or self.owner._world(survivor) is not self.dining
                or survivor.position.distance_to(record['approach']) > 2):
            # A safe landing can move the worker around a player occupying the
            # bench approach. Never keep a prior drawing pinned over that player.
            self._release_actor_pose(survivor)
            return
        self._pose(survivor, self._image(record['image']), record['anchor'],
                   position=record['position'],sort_y=record['sort_y'])

    def update(self, seconds):
        if (not getattr(self.game, '_music_focused', True) or self.game.pause.is_open
                or self.game.inventory_ui.is_open or self.game.map_open
                or self.game.quest_ui.journal_open):return
        seating = self._seating_enabled()
        if self._seated and not seating:self.release()
        self._meal_clock = self._meal_clock+max(0., seconds) if seating else 0.
        current = self._line()
        if current is None:
            if self._script is not None:self.release()
            self._apply_seating()
            self._apply_survivor_rest()
            return
        index, line = current;script = self.game.social.script_identifier
        if script != self._script:
            self.release();self._script = script
        key = (index, line.get('cue'))
        if line.get('cue') in self.DURATIONS and key not in self._seen:
            self._clear_beat();self.active_cue = line['cue'];self.clock = 0.;self._seen.add(key)
            if self.active_cue in ('open_survey', 'open_plan'):self._map_open = True
            if self.active_cue == 'open_account':self._account_open = True
        self.clock += max(0., seconds)
        if self.active_cue and self.clock >= self.DURATIONS[self.active_cue]:self._clear_beat()
        self._attention(line)
        self._apply_seating()
        self._apply_survivor_rest()
        player = self.game.player
        if self.active_cue in ('caelan_scabbard', 'pass_bread', 'clear_plates'):
            direction = 'left' if player.facing == 'left' else 'right'
            anchor = self.game.world.data['player_draw_anchor']
            self._pose(player, self._hand_pose(direction), (anchor[0]+8, anchor[1]+24))
        elif self.active_cue == 'tomas_eat' and self._owned_actor(self.owner.tomas):
            actor = self.owner.tomas
            record = self._seat_records().get('tomas') if self._seating_enabled() else None
            if record and self._meal_clock >= .35:
                frame = min(3, int(self.clock/.25))
                image = self._image(f'assets/story/sanctuary_opening/poses/tomas_eat/frame_{frame+1:02}.png')
                if record.get('flip_x'):image = pygame.transform.flip(image, True, False)
                self._pose(actor, image, record['anchor'], position=record['position'],
                           sort_y=record['sort_y'])
            elif not record:
                actor.facing = facing_toward(pygame.Vector2(168, 184)-actor.position)
                actor.story_sprite = actor.idles[actor.facing]
        elif self.active_cue == 'survivor_alarm':
            actor = getattr(self.owner,'survivor',None)
            if actor is not None and self.owner._world(actor) is self.game.world:
                self._pose(actor,self._image('assets/story/regent_emergency/poses/alarm_front.png'),
                           actor.draw_anchor)
        elif self.active_cue == 'lucan_disbelief':
            actor = getattr(self.owner,'lucan',None)
            if actor is not None and self.owner._world(actor) is self.game.world:
                direction = facing_toward(self.owner.aldric.position-actor.position)
                actor.facing = direction;actor.moving = False
                self._pose(actor,actor.idles[direction],actor.draw_anchor)
        elif self.active_cue == 'survivor_aid' and self._owned_actor(self.owner.serene):
            self._pose(self.owner.serene,
                       self._image('assets/story/regent_emergency/poses/serene_aid_left.png'),
                       (12,30))

    def _clear_beat(self):
        script = self._script;seen = self._seen
        self.release();self._script = script;self._seen = seen

    def _weapon(self):
        if self._sword is None:
            original = self._image('assets/story/mill_gift/blade.png')
            self._sword = pygame.transform.rotate(pygame.transform.scale(original, (9, 24)), 180)
            # Cover the blade with a fitted sheath. The approved gear and gems
            # remain visible above it; the steel is never drawn bare in town.
            pygame.draw.polygon(self._sword, '#31383b', ((2, 13), (6, 13), (5, 23), (3, 23)))
            pygame.draw.lines(self._sword, '#8c7451', False, ((2, 13), (3, 23), (5, 23), (6, 13)))
        return self._sword

    def draw_world(self, canvas, camera):
        if not self.owner.eligible:return
        player = self.game.player
        inventory = getattr(self.game, 'inventory', None)
        if personal_prop_visible(player, self.active_cue == 'caelan_scabbard') and inventory is not None and inventory.quantity('caelan_gearblade') > 0:
            sword = self._weapon()
            x = player.position.x+(4 if player.facing in ('front', 'right') else -10)
            y = player.position.y-20
            if self.active_cue == 'caelan_scabbard':x += round(math.sin(min(1., self.clock/.85)*math.pi)*2)
            canvas.blit(sword, (round(x)-camera[0], round(y)-camera[1]))
        if self.game.world is not self.dining:return
        if self._map_open or self.owner.stage in ('discussion', 'done'):
            paper = self._image('assets/story/lantern/rest_props/paper_clean.png')
            fraction = min(1., self.clock/.55) if self.active_cue in ('open_survey', 'open_plan') else 1.
            width = max(2, round(paper.get_width()*fraction))
            sheet = pygame.transform.scale(paper, (width, paper.get_height()))
            canvas.blit(sheet, (168-width//2-camera[0], 177-camera[1]))
        if self._account_open:
            paper = self._image('assets/story/lantern/rest_props/paper_clean.png')
            sheet = pygame.transform.scale(paper, (11, 10))
            canvas.blit(sheet, (182-camera[0], 180-camera[1]))
        if self.active_cue in ('pass_bread', 'clear_plates'):
            plate = self._image('assets/story/sanctuary_opening/poses/plate.png')
            sign = -1 if player.facing == 'left' else 1
            hand = player.position+pygame.Vector2(sign*8, -6)
            canvas.blit(plate, (round(hand.x)-4-camera[0], round(hand.y)-2-camera[1]))
            if self.active_cue == 'pass_bread':
                pygame.draw.rect(canvas, '#ba8b4b', (round(hand.x)-2-camera[0], round(hand.y)-3-camera[1], 4, 2))
