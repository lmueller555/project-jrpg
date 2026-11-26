"""Explicit retained-cave fixtures and real-input helpers for tests/reviews.

This is disposable combat/world setup, not a quest, party recruitment scene or
replacement opening. Only retained MQ01/MQ02 history is initialized.
"""
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import pygame

from main import VIEW_SIZE, camera_for
from halden_visit import town_path
from overworld_travel import WORLD_ID, RESERVE_ID
from tools.scenario_fixtures import make_game, seed_mill_completed
from tools.capture_overworld_sanctuary import regional_path
from tools.capture_sanctuary_reserve import path as clear_path

ROOT = Path(__file__).resolve().parents[1]


def seed_cave_combat(game, *, lesson_complete=True, enter=False):
    """Prepare a selectable Caelan/Mira pair and explicit earlier blade learning."""
    seed_mill_completed(game)
    if game.party.current_event_id:
        assert game.party.end_event(game.party.current_event_id)
    if 'mira' not in game.party.members:
        assert game.party.recruit('mira', temporary=True)
    assert game.party.set_available('mira', True)
    assert game.party.select(('caelan', 'mira'))
    if not game.character_abilities.has_weapon():
        assert game.character_abilities.acquire_weapon('caelan', 'caelan_gearblade')
    if lesson_complete:
        assert game.character_abilities.learn_ability('caelan', 'aqua_edge')
    assert game.cave_lesson.restore({'version': 1,
        'resonance_seen': lesson_complete, 'battle_cleared': lesson_complete,
        'deferred': False})
    from sanctuary_cave import RESERVE_ENTRY_APPROACH
    reserve = game._scene_by_id(RESERVE_ID)
    assert game.overworld_travel._commit(reserve, RESERVE_ENTRY_APPROACH, 'back',
                                       {'id': 'cave_scenario'})
    game.opening_fade = game.transfer_cooldown = 0
    game.social.cancel_script();game.social.blocked.clear()
    if enter:
        assert game.sanctuary_cave.interact()
        game.opening_fade = game.transfer_cooldown = 0
    game.party_travel.reset();game.party_travel.update(.001);game.camera.reset()
    assert game.save_progress()
    return game


def seed_cave_victory(game):
    """Set an explicit defeated-boss fixture without rescue or quest completion."""
    seed_cave_combat(game, enter=True)
    from post_battle import battle_reward_definition
    from sanctuary_boss import RECEIPT
    assert game.award_battle_rewards(RECEIPT, battle_reward_definition('cave_boss')['drops'])
    assert game.sanctuary_boss.restore({'version': 1, 'defeated': True,
                                      'intro_seen': True, 'pending': None})
    assert game.save_progress()
    return game


class Driver:
    """Real input, movement and acknowledgment with disposable state."""
    def __init__(self, directory, *, initialize=True):
        self.directory = Path(directory)
        self.save = self.directory/'journey.json'
        self.settings = self.directory/'settings.json'
        self.game = self.new_game(False)
        self.observer = None
        self.transitions = [];self.dialogue = []
        if initialize:self.prepare_cave(lesson_complete=False)

    def new_game(self, title):
        game = make_game(self.directory, title=title, embedded=False)
        pygame.event.clear()
        return game

    def prepare_cave(self, *, lesson_complete=True, enter=False):
        return seed_cave_combat(self.game, lesson_complete=lesson_complete, enter=enter)

    def tick(self, seconds=.05, direction=(0, 0), running=False):
        before = self.game.world.data['id']
        self.game.update(seconds, direction, running)
        after = self.game.world.data['id']
        if before != after:self.transitions.append([before, after])
        if self.observer:self.observer(seconds)

    def until(self,predicate,seconds=80):
            for _ in range(round(seconds/.05)):
                if predicate():return
                self.tick()
            raise AssertionError(('Timed out',self.game.world.data['id'],self.game.social.script_identifier,
                self.game.world.data['id'],list(self.game.player.position)))

    def read_current(self,on_page=None):
            social=self.game.social;identifier=social.script_identifier
            assert social.active,('No dialogue',self.game.world.data['id'])
            seen=set()
            for _ in range(200):
                if not social.active or social.script_identifier!=identifier:return
                page=social.page
                assert not social.choosing,'This acknowledgment helper requires linear dialogue'
                key=page['source_line'],tuple(page['lines'])
                if key not in seen:
                    seen.add(key)
                    line=dict(social._source_lines[page['source_line']])
                    self.dialogue.append({'script':identifier,'line':page['source_line'],**line})
                    if on_page:on_page(identifier,line,page)
                social.advance()
            raise AssertionError(('Dialogue did not finish',identifier))

    def clear(self,world,desired):
            point=pygame.Vector2(desired)
            for radius in (0,6,12,18,24,30,36):
                for dx,dy in ((0,radius),(-radius,0),(radius,0),(0,-radius)):
                    candidate=point+(dx,dy)
                    if world.can_stand(candidate):return candidate
            raise AssertionError(('Blocked station',world.data['id'],list(point)))

    def walk(self,goal,*,transfer=None,running=False):
            world=self.game.world
            if world.data['id']==WORLD_ID:
                route=regional_path(world,self.game.player.position,goal)
            elif world is self.game.town and self.game.player.position.distance_to(goal)>180:
                route=town_path(world,self.game.player.position,goal,SimpleNamespace(probe_size=world.probe_size),None)
            else:route=clear_path(world,self.game.player.position,goal)
            assert route is not None,('No route',world.data['id'],list(self.game.player.position),list(goal))
            for corner in route:
                for _ in range(2400):
                    if self.game.world is not world:
                        assert self.game.world.data['id']==transfer,('Unexpected transfer',self.game.world.data['id'])
                        return
                    delta=pygame.Vector2(corner)-self.game.player.position
                    if delta.length()<.45:break
                    before=self.game.player.position.copy()
                    seconds=min(.04,delta.length()/(108 if running else 72))
                    self.tick(seconds,delta,running)
                    assert not self.game.combat.active,'The review route entered combat'
                    assert self.game.world is not world or self.game.world.can_stand(self.game.player.position)
                    if self.game.player.position==before:
                        # Door fades and a queued spoken scene can briefly own input.
                        if self.game.social.active or getattr(self.game, 'cinematic_active', False) or self.game.opening_fade:
                            raise AssertionError(('Movement owned during route',self.game.world.data['id'],self.game.social.script_identifier))
                        raise AssertionError(('Walking stalled',world.data['id'],list(before),list(corner)))
                else:raise AssertionError(('Walk budget',world.data['id'],corner))
            if transfer:
                door=next((door for door in world.doors
                           if pygame.Vector2(door.data['anchor']).distance_to(goal)<2),None)
                direction=(0,-1) if door and door.data['entry_side']=='north' else (0,1)
                for _ in range(50):
                    if self.game.world is not world:break
                    self.tick(.04,direction)
                assert self.game.world.data['id']==transfer,('Missing transfer',transfer)

    def travel(self,destination):
            if self.game.world is destination:return
            queue=deque([(self.game.world,[])]);seen={self.game.world.path};steps=None
            while queue:
                world,route=queue.popleft()
                if world is destination:steps=route;break
                for door in world.doors:
                    other=self.game._load_scene(ROOT/door.data['destination'])
                    if other.path not in seen:
                        seen.add(other.path);queue.append((other,route+[(door,other)]))
            assert steps is not None,('No room route',destination.data['id'])
            for door,other in steps:
                self.until(lambda:not self.game.opening_fade and not self.game.transfer_cooldown)
                self.walk(door.data['anchor'],transfer=other.data['id'])
                self.until(lambda:not self.game.opening_fade and not self.game.transfer_cooldown)

    def continue_saved(self,*,settle=True):
            assert self.game.save_progress()
            self.game=self.new_game(True)
            assert self.game.has_saved_journey,'Saved cave scenario rejected'
            assert self.game.begin_journey(True),'Continue failed'
            if settle:self.until(lambda:not self.game.opening_fade and not self.game.transfer_cooldown)
            return self.game


def cast_visibility(game):
    """Count actual visible pixels, toggling one actor only for comparison."""
    world=game.world
    companions=tuple(game.party_travel.actors())
    actors=[('caelan',game.player), *((actor.identifier,actor) for actor in companions)]
    def draw_to(surface):
        world.draw(surface,camera,game.player,game.elapsed_ms,False,party_actors=companions)
    camera=camera_for(game.player.position,world.size)
    result={}
    for identifier,actor in actors:
        shown=pygame.Surface(VIEW_SIZE);bare=shown.copy()
        draw_to(shown)
        existed=hasattr(actor,'story_visible');previous=getattr(actor,'story_visible',True)
        actor.story_visible=False
        try:draw_to(bare)
        finally:
            if existed:actor.story_visible=previous
            else:del actor.story_visible
        sprite=(game.player.sprite() if actor is game.player else
                getattr(actor,'story_sprite',None) or actor.sprite(game.elapsed_ms))
        mask=pygame.mask.from_surface(sprite)
        position=getattr(actor,'story_position',None) or actor.position
        anchor=(getattr(actor,'story_draw_anchor',None) or
                (world.data['player_draw_anchor'] if actor is game.player else actor.draw_anchor))
        origin=(round(position[0])-anchor[0]-camera[0],round(position[1])-anchor[1]-camera[1])
        opaque=visible=0
        for y in range(sprite.get_height()):
            for x in range(sprite.get_width()):
                if not mask.get_at((x,y)):continue
                point=int(origin[0])+x,int(origin[1])+y
                if not shown.get_rect().collidepoint(point):continue
                opaque+=1;visible+=shown.get_at(point)!=bare.get_at(point)
        result[identifier]={'opaque_pixels':opaque,'visible_pixels':visible}
    return result
