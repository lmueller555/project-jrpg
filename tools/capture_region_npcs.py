"""Record regional NPC work and guard conversations in the production Game.

Only earlier quest completion, the mill-restored fact and clear player/camera
stations are fixtures. Every work phase, sack transfer, conversation and pose
clock proceeds through normal Game input/update/draw. No actor positions,
animation clocks or farm milestones are assigned during the recordings.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageChops, ImageSequence

from main import Game
from grain_farm import MILL_FLAG, SOURCE, SCENE_ID
from quests import OPENING_QUEST, MILL_QUEST
from tools.capture_lantern_quest import seed_previous_quests

FPS = 30
VIDEO_FPS = 15
DEFAULT_OUTPUT = ROOT/'docs/reviews/region_npcs'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def surface_digest(image):
    return hashlib.sha256(pygame.image.tobytes(image, 'RGBA')).hexdigest()


def png(game, path):
    game.draw()
    pygame.image.save(game.window, str(path))


def save_gif(path, frames, fps=10):
    if not frames:
        raise AssertionError('No frames for '+str(path))
    # One shared palette permits faithful delta-frame encoding instead of a
    # full, independently paletted background on every captured sprite step.
    sample_count = min(64,len(frames))
    atlas = Image.new('RGB',(768,768))
    for index in range(sample_count):
        frame = frames[round(index*(len(frames)-1)/max(1,sample_count-1))]
        atlas.paste(frame.resize((96,96),Image.Resampling.NEAREST),
                    ((index%8)*96,(index//8)*96))
    palette = atlas.quantize(colors=256)
    intended = [frame.quantize(palette=palette,dither=Image.Dither.NONE)
                for frame in frames]
    duration = round(1000/fps)
    intended[0].save(path,save_all=True,append_images=intended[1:],
        duration=duration,loop=0,disposal=1,optimize=False,
        palette=palette.getpalette())
    # Identical consecutive frames may be merged by GIF. Verify the entire
    # decoded pixel/timing sequence against its intended quantized captures.
    source_index = 0
    total_ms = 0
    with Image.open(path) as encoded:
        encoded_frames = encoded.n_frames
        for frame in ImageSequence.Iterator(encoded):
            hold = frame.info.get('duration',duration)
            assert hold%duration == 0
            decoded = frame.convert('RGB')
            for _ in range(hold//duration):
                assert source_index < len(intended)
                assert not ImageChops.difference(decoded,intended[source_index].convert('RGB')).getbbox()
                source_index += 1
            total_ms += hold
    assert source_index == len(intended) and total_ms == len(intended)*duration
    return {'file':Path(path).name,'captured_frames':len(frames),
            'encoded_frames':encoded_frames,'milliseconds':total_ms,
            'decoded_pixels_verified':True,'timing_verified':True}


class Recorder:
    def __init__(self, game, output, name, *, close_crop=None, controller='grain_farm'):
        self.game = game
        self.output = Path(output)
        self.name = name
        self.controller = controller
        self.ticks = 0
        self.frames = 0
        self.detail_gifs = {}
        self.close_crop = pygame.Rect(close_crop) if close_crop else None
        self.stages = []
        self.contacts = []
        self._contact_identity = None
        self._identity = None
        self.sack_checks = 0
        self.foot_checks = 0
        self.encoder = subprocess.Popen([
            'ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo',
            '-pixel_format', 'rgb24', '-video_size', '960x640',
            '-framerate', str(VIDEO_FPS), '-i', '-', '-an', '-c:v',
            'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt',
            'yuv420p', '-movflags', '+faststart',
            str(self.output/(name+'.mp4'))], stdin=subprocess.PIPE)

    @property
    def seconds(self):
        return self.ticks/FPS

    def key(self, key):
        for kind in (pygame.KEYDOWN, pygame.KEYUP):
            pygame.event.post(pygame.event.Event(kind, key=key, repeat=False))
        assert self.game.handle_events()

    def actor_record(self, actor):
        result = {'id':actor.data['id'], 'position':list(actor.position),
                  'facing':actor.facing, 'moving':actor.moving,
                  'pose':actor.pose, 'clock':round(actor.clock, 5)}
        for field in ('animation_key', 'pose_key', 'action_key', 'frame_index'):
            value = getattr(actor, field, None)
            if value is not None:result[field] = value
        attachment = getattr(actor, 'attachment', None)
        if isinstance(attachment,dict):result['attachment'] = attachment
        hands = getattr(actor, 'hand_positions', None)
        if hands is not None:result['world_hands'] = [list(point) for point in hands]
        return result

    def step(self, direction=(0,0), *, record=True):
        assert self.game.handle_events()
        self.game.update(1/FPS, direction, False)
        self.ticks += 1
        farm = getattr(self.game.world,self.controller)
        props = farm.props()
        assert not farm.actors[0].blocker.colliderect(farm.actors[1].blocker)
        self.foot_checks += 1
        if self.controller == 'grain_farm':
            assert len(props) == 3, 'A sack was lost or duplicated'
        else:
            assert len(props) == 13
            assert sum(image is farm.art['stone'] for _,_,image,_ in props) == 4
            assert sum(image is farm.art['cup'] for _,_,image,_ in props) == 1
            assert sum(image is farm.art['tool'] for _,_,image,_ in props) == 1
        self.sack_checks += 1
        progress_key = 'loaded' if self.controller == 'grain_farm' else 'sorted'
        identity = (farm.stage,tuple(farm.state.get(k) for k in ('loaded','sorted','tea_beat')),
                    tuple((a.pose, a.facing, a.moving) for a in farm.actors))
        if identity != self._identity:
            self.stages.append({'seconds':round(self.seconds, 5),
                'stage':farm.stage,progress_key:farm.state[progress_key],
                'tea_beat':farm.state.get('tea_beat'),
                'actors':[self.actor_record(a) for a in farm.actors]})
            self._identity = identity
        if self.ticks % 3 == 0:
            records = [self.actor_record(a) for a in farm.actors]
            contact_identity = tuple((r['id'],r.get('animation_key'),r.get('frame_index'),
                                      json.dumps(r.get('attachment',{}),sort_keys=True))
                                     for r in records)
            if contact_identity != self._contact_identity:
                sacks = []
                for sort_y,_,image,point in props:
                    item = 'sack' if self.controller == 'grain_farm' else next(
                        (key for key in ('stone','cup','tool') if image is farm.art[key]),None)
                    if item:sacks.append({'item':item,
                        'lower_center':[point[0]+image.get_width()/2,point[1]+image.get_height()],
                        'sort_y':sort_y})
                self.contacts.append({'seconds':round(self.seconds,5),
                    'stage':farm.stage,progress_key:farm.state[progress_key],
                    'tea_beat':farm.state.get('tea_beat'),
                    'actors':records,'props':sacks})
                self._contact_identity = contact_identity
        if record and self.ticks % 2 == 0:
            self.game.draw()
            assert self.game.window.get_size() == (960,640)
            self.encoder.stdin.write(pygame.image.tobytes(self.game.window,'RGB'))
            self.frames += 1
        if record and self.ticks % 3 == 0 and self.close_crop:
            self.game.draw()
            image = self.game.canvas.subsurface(self.close_crop)
            frame = Image.frombytes('RGB', image.get_size(),
                            pygame.image.tobytes(image, 'RGB')).resize(
                            (image.get_width()*3, image.get_height()*3),
                            Image.Resampling.NEAREST)
            detail = None
            if self.name == 'grain_loading_and_shared_lift':
                detail = ('shared_lowering' if farm.stage.startswith('help_') else
                          'placing_'+str(farm.state['loaded']+1) if farm.stage == 'place' else
                          'carry_front' if farm.stage == 'carry' and farm.state['loaded'] == 0 else
                          'return_back' if farm.stage == 'return' and farm.state['loaded'] == 1 else
                          'rope_work' if farm.stage == 'check' else None)
            elif self.name == 'bridge_work_and_tea':
                detail = ('stone_carry_right' if farm.stage == 'carry' and farm.state['sorted'] == 0 else
                          'stone_return_left' if farm.stage == 'return' and farm.state['sorted'] == 1 else
                          'stone_placement' if farm.stage == 'place' and farm.state['sorted'] == 0 else
                          'cup_walk_left' if farm.stage == 'tea_across' else
                          'cup_walk_front' if farm.stage == 'tea_down' else
                          'cup_walk_right' if farm.stage == 'tray_return' else
                          'cup_walk_back' if farm.stage == 'tray_up' else
                          'tea_handoff' if farm.stage in ('wobble','reach','exchange','cup_return') else
                          'seating_and_drinking' if farm.stage in ('sit_down','sit','stand_up','rise') else None)
            if detail:self.detail_gifs.setdefault(detail,[]).append(frame)

    def run(self, seconds, direction=(0,0), **kwargs):
        for _ in range(round(seconds*FPS)):
            self.step(direction, **kwargs)

    def until(self, predicate, *, limit=90):
        for _ in range(round(limit*FPS)):
            if predicate():return
            self.step()
        f = getattr(self.game.world,self.controller)
        raise AssertionError(('Timed out',f.stage,f.to_dict(),
                              [list(a.position) for a in f.actors]))

    def still(self, name):
        png(self.game, self.output/(name+'.png'))

    def read(self, *, hold=1.25, screenshot_prefix=None):
        seen = []
        for index in range(160):
            if not self.game.social.active:return seen
            page = dict(self.game.social.page)
            seen.append(page)
            self.run(hold)
            if screenshot_prefix:self.still(screenshot_prefix+'_'+str(index))
            self.key(pygame.K_SPACE)
        raise AssertionError('Dialogue did not finish')

    def close(self):
        self.encoder.stdin.close()
        assert self.encoder.wait() == 0
        gif_validation = []
        for key,frames in self.detail_gifs.items():
            gif_validation.append(save_gif(self.output/(self.name+'_'+key+'.gif'),frames))
        return {'video':self.name+'.mp4', 'frames':self.frames,
                'fps':VIDEO_FPS, 'seconds':self.frames/VIDEO_FPS,
                'controller':self.controller,
                'sack_ownership_checks':self.sack_checks if self.controller=='grain_farm' else 0,
                'bridge_prop_ownership_checks':self.sack_checks if self.controller=='bridge_crew' else 0,
                'worker_foot_overlap_checks':self.foot_checks,
                'stages':self.stages,'contact_samples':self.contacts,
                'gif_validation':gif_validation}


def make_game(root, *, repaired=False, title=False):
    game = Game(window_size=(960,640), fullscreen=False, start_on_title=title,
                save_path=Path(root)/'journey.json',
                settings_path=Path(root)/'settings.json')
    game.audio.set_music(0);game.audio.set_effects(0)
    if not title:
        if repaired:
            seed_previous_quests(game)
            game.social.flags.add(MILL_FLAG)
        else:
            assert game.accept_quest(OPENING_QUEST)
            for key in ('halden','elira','venn'):
                assert game.quests.complete_objective(OPENING_QUEST,key)
            game._sync_inventory()
            game.halden_visit.restore();game.elira_visit.restore();game.venn_visit.restore()
            assert game.quests.turn_in(OPENING_QUEST,'mother_serene')
            assert game.quests.unlock(MILL_QUEST)
            game.opening_conclusion.restore({'version':1,'stage':'done'})
            game.opening.restore({'version':1,'stage':'disabled'})
        game.world = game.overworld_world
        game.player.position.update(-876,232)
        game.opening_fade = game.transfer_cooldown = 0
        game.location_seconds = 0
        game.camera.reset();game.camera.focus((-830,212), duration=0)
        game.quest_ui.reset();pygame.event.clear()
    return game


def farm_sequence(output, root, *, repaired):
    game = make_game(root, repaired=repaired)
    farm = game.world.grain_farm
    if repaired:
        # Let the ordinary covering loop establish its own visible cloth and
        # resting pose before introducing the repaired-mill prerequisite.
        # This is a prerequisite fixture, never an assigned farm milestone or
        # animation clock, and makes uncovering part of the recorded sequence.
        game.social.flags.discard(MILL_FLAG)
        for _ in range(20*FPS):
            game.update(1/FPS,(0,0),False)
            if farm.covered and farm.stage == 'rest':break
        else:raise AssertionError('The ordinary pre-repair cover did not settle')
        game.social.flags.add(MILL_FLAG)
    name = 'grain_loading_and_shared_lift' if repaired else 'grain_before_repair'
    recorder = Recorder(game, output, name, close_crop=(195,95,120,125))
    snapshots = set()
    if not repaired:
        for _ in range(18*FPS):
            recorder.step()
            if farm.stage not in snapshots:
                recorder.still('before_'+farm.stage);snapshots.add(farm.stage)
        assert farm.state['loaded'] == 0
        recorder.still('before_repair')
        return recorder.close()
    for _ in range(70*FPS):
        recorder.step()
        if farm.stage not in snapshots:
            recorder.still('loading_'+farm.stage);snapshots.add(farm.stage)
        if farm.stage == 'ready' and farm.coworker_stop == 6:break
    else:raise AssertionError('Workers never reached their shared-lift exchange')
    recorder.still('loaded_cart')
    # A nearby clear player station starts the real optional exchange. No
    # worker or phase is moved, and the loader continues owning the spare sack.
    game.player.position.update(-870,203)
    recorder.key(pygame.K_e)
    assert game.social.script_identifier == SCENE_ID
    before = (farm.timer, [tuple(a.position) for a in farm.actors])
    recorder.run(1)
    assert before == (farm.timer, [tuple(a.position) for a in farm.actors])
    dialogue = recorder.read(hold=1.5, screenshot_prefix='worker_dialogue')
    for _ in range(60*FPS):
        recorder.step()
        if farm.stage not in snapshots:
            recorder.still('shared_'+farm.stage);snapshots.add(farm.stage)
        if farm.stage == 'help_place' and farm.timer >= 1.3 and 'lowered' not in snapshots:
            recorder.still('shared_lowered');snapshots.add('lowered')
        if farm.state['scene_done'] and farm.stage == 'rest':break
    else:raise AssertionError('Shared lift did not reach its physical payoff')
    recorder.run(5)
    recorder.still('workers_finished')
    assert farm.state['loaded'] == 2 and farm.state['exchange_read']
    assert farm.state['scene_done'] and len(farm.props()) == 3
    result = recorder.close()
    result.update(dialogue=dialogue, final_state=farm.to_dict(),
                  dialogue_freezes_work=True,
                  repair_handoff_fixture='ordinary cover loop advanced with repair prerequisite withheld; repaired fact enabled before recording')
    return result


def blocked_and_continue(output, root):
    game = make_game(root, repaired=True)
    farm = game.world.grain_farm
    recorder = Recorder(game, output, 'blocked_carry_and_continue',
                        close_crop=(195,95,120,125))
    recorder.until(lambda:farm.stage == 'carry')
    # The player steps into the lane fixture; subsequent yielding, recovery
    # and movement use real Game.update collision and movement.
    game.player.position.update(-824,210)
    recorder.run(2)
    stopped = tuple(farm.loader.position)
    image = surface_digest(farm.loader.sprite(game.elapsed_ms))
    recorder.run(1.5)
    assert tuple(farm.loader.position) == stopped
    assert not farm.loader.moving
    assert surface_digest(farm.loader.sprite(game.elapsed_ms)) == image
    assert farm.state['loaded'] == 0
    recorder.still('blocked_carry')
    recorder.run(.7, (-1,0));recorder.run(.7, (0,1))
    recorder.until(lambda:farm.state['loaded'] == 1 and farm.stage == 'carry')
    assert game.save_progress()
    recorder.still('before_continue')
    before = farm.to_dict()
    game.on_title = True
    assert game.begin_journey(True)
    farm = game.world.grain_farm
    assert farm.state['loaded'] == before['loaded'] == 1
    assert tuple(farm.loader.position) == SOURCE
    assert len(farm.props()) == 3
    assert sum(a.data['id'] == 'grain_loader' for a in game.world.npcs) == 1
    game.opening_fade = game.transfer_cooldown = 0
    game.camera.focus((-830,212), duration=0);game.location_seconds = 0
    recorder.run(1)
    recorder.still('after_continue')
    recorder.until(lambda:farm.stage == 'ready' and farm.coworker_stop == 6)
    assert farm.state['loaded'] == 2 and len(farm.props()) == 3
    before_pause = (farm.timer, [a.clock for a in farm.actors],
                    [tuple(a.position) for a in farm.actors])
    crop = recorder.close_crop
    recorder.close_crop = None
    recorder.key(pygame.K_m);recorder.run(1)
    assert before_pause == (farm.timer, [a.clock for a in farm.actors],
                            [tuple(a.position) for a in farm.actors])
    recorder.key(pygame.K_m);recorder.run(.1)
    recorder.close_crop = crop
    result = recorder.close()
    result.update(blocked_body_holds=True, sack_count_preserved=True,
                  loaded_preserved_on_continue=True, unplaced_sack_returns_to_storage=True,
                  singleton_workers=True, map_freezes_routines=True,
                  final_state=farm.to_dict())
    return result


def clear_guard_station(game, actor, offset):
    direction = pygame.Vector2(offset).normalize()
    tangent = pygame.Vector2(-direction.y,direction.x)
    # A checkpoint post can occupy the pure cardinal axis. Keep the intended
    # direction dominant while finding an actual clear player foot station.
    for distance in (30,28,26,24,22,20,18,34,38,42):
        for lateral in (0,-8,8,-12,12,-16,16,-20,20):
            if abs(lateral) >= distance:continue
            position = actor.position+direction*distance+tangent*lateral
            if game.world.can_stand(position):return position
    raise AssertionError(('No clear guard approach', actor.data['id'], offset))


def guard_conversations(output, root):
    game = make_game(root)
    guards = [a for a in game.world.npcs if a.data['id'].startswith('road_guard:')]
    assert len(guards) == 4
    recorder = Recorder(game, output, 'checkpoint_guards')
    approaches = [('front',(0,1)),('back',(0,-1)),('left',(-1,0)),('right',(1,0))]
    rows = []
    for number, actor in enumerate(guards):
        watch = actor.facing
        images = set()
        for expected, offset in approaches:
            game.player.position.update(clear_guard_station(game, actor, offset))
            game.camera.reset();game.camera.focus(actor.position, duration=0)
            game.location_seconds = 0
            recorder.run(.15)
            recorder.key(pygame.K_e)
            assert game.social.active
            profile = game.social.data['speakers']['road_guard']
            assert profile.get('actor_id') == actor.data['id']
            assert profile['portrait'] == 'road_guard'
            recorder.run(.25)
            assert actor.facing == expected, (actor.data['id'], expected, actor.facing)
            sprite_sha = surface_digest(actor.sprite(game.elapsed_ms))
            images.add(sprite_sha)
            recorder.still(f'guard_{number}_{expected}')
            if number == 2 and expected == 'front':
                game.audio.set_text_scale(1.5)
                game.camera.focus(actor.position,duration=0,anchor=(.5,.6))
                recorder.still('guard_large_text')
                game.audio.set_text_scale(1.)
                game.camera.focus(actor.position,duration=0)
            pages = recorder.read(hold=.85)
            recorder.run(.35)
            assert actor.facing == watch, (actor.data['id'], watch, actor.facing)
            rows.append({'actor':actor.data['id'], 'position':list(actor.position),
                         'approach':expected, 'watch_facing':watch,
                         'portrait':profile['portrait'], 'sprite_sha256':sprite_sha,
                         'dialogue':pages, 'watch_restored':True})
        assert len(images) == 4, 'Guard still has repeated/front-only direction art'
    # Walking away cancels ordinary live prose and releases the guard's pose.
    actor = guards[0]
    game.player.position.update(clear_guard_station(game, actor, (0,1)))
    game.camera.reset();game.camera.focus(actor.position, duration=0)
    recorder.key(pygame.K_e)
    assert game.social.active
    recorder.run(2.1, (0,1))
    assert not game.social.active and actor.facing == 'front'
    recorder.still('guard_walkaway')
    result = recorder.close()
    result.update(guards=rows, four_guards=True,
                  all_four_facings_distinct=True, watch_restores_on_walkaway=True,
                  gates_still_closed=all(not game.world._gate_open(g) for g in game.world.gates))
    assert result['gates_still_closed']
    return result


def game_at_bridge(root):
    game = make_game(root,repaired=True)
    game.player.position.update(-2376,642)
    game.camera.reset();game.camera.focus((-2376,616),duration=0)
    game.location_seconds = 0
    assert len(game.world.npcs) == 8
    return game


def bridge_dialogue(recorder, *, prefix=None):
    recorder.key(pygame.K_e)
    assert recorder.game.social.script_identifier == 'bridge_crew_tea'
    return recorder.read(hold=1.4,screenshot_prefix=prefix)


def bridge_sequence(output, root):
    game = game_at_bridge(root)
    crew = game.world.bridge_crew
    flags = set(game.social.flags)
    quests = game.quests.to_dict()
    recorder = Recorder(game,output,'bridge_work_and_tea',
                        close_crop=(195,80,140,145),controller='bridge_crew')
    snapshots = set()
    for _ in range(90*FPS):
        recorder.step()
        if crew.stage not in snapshots:
            recorder.still('bridge_work_'+crew.stage);snapshots.add(crew.stage)
        if crew.stage == 'ready':break
    else:raise AssertionError('Bridge sorting did not finish')
    assert crew.state['sorted'] == 3 and crew.state['tea_beat'] == 0
    recorder.still('bridge_sorted_stones')
    recorder.key(pygame.K_e)
    assert crew.state['tea_beat'] == 1
    recorder.until(lambda:crew.stage == 'request')
    recorder.still('bridge_tea_arrives')
    dialogue = bridge_dialogue(recorder,prefix='bridge_request')
    assert crew.state.get('request_read')
    recorder.until(lambda:crew.stage == 'wobble')
    recorder.run(1.)
    recorder.still('bridge_steady_surface')
    recorder.until(lambda:crew.stage == 'reach')
    recorder.run(.5)
    recorder.still('bridge_reaching_cup')
    recorder.until(lambda:crew.stage == 'exchange')
    recorder.still('bridge_cup_handoff')
    dialogue += bridge_dialogue(recorder,prefix='bridge_exchange')
    recorder.until(lambda:crew.stage == 'sit')
    recorder.run(1.4)
    recorder.still('bridge_seated_drinking')
    recorder.until(lambda:crew.state['tea_beat'] == 5)
    recorder.run(2.)
    recorder.still('bridge_tea_finished')
    assert crew.state['sorted'] == 3
    assert flags == game.social.flags and quests == game.quests.to_dict()
    result = recorder.close()
    result.update(final_state=crew.to_dict(),dialogue=dialogue,
        finite_three_stones=True,one_cup=True,one_tool=True,
        no_story_mutation=True,all_eight_npcs_present=True)
    return result


def bridge_blocked_and_continue(output, root):
    from bridge_crew import SOURCE as BRIDGE_SOURCE
    game = game_at_bridge(root)
    crew = game.world.bridge_crew
    recorder = Recorder(game,output,'bridge_blocked_and_continue',
                        controller='bridge_crew')
    recorder.until(lambda:crew.stage == 'carry')
    game.player.position.update(-2352,616)
    recorder.run(2.)
    stopped = tuple(crew.mason.position)
    image = surface_digest(crew.mason.sprite(game.elapsed_ms))
    recorder.run(1.5)
    assert tuple(crew.mason.position) == stopped and not crew.mason.moving
    assert image == surface_digest(crew.mason.sprite(game.elapsed_ms))
    assert crew.state['sorted'] == 0
    recorder.still('bridge_blocked_stone')
    recorder.run(.6,(0,1));recorder.run(.5,(-1,0))
    recorder.until(lambda:crew.state['sorted'] == 1 and crew.stage == 'carry')
    assert game.save_progress()
    recorder.still('bridge_before_continue')
    game.on_title = True
    assert game.begin_journey(True)
    crew = game.world.bridge_crew
    assert crew.state['sorted'] == 1
    assert tuple(crew.mason.position) == BRIDGE_SOURCE
    assert len([a for a in game.world.npcs if a.data['id'].startswith('bridge_')]) == 2
    game.opening_fade = game.transfer_cooldown = 0
    game.camera.focus((-2376,616),duration=0);game.location_seconds = 0
    recorder.run(.5)
    recorder.still('bridge_after_continue')
    recorder.until(lambda:crew.stage == 'ready')
    assert crew.state['sorted'] == 3 and crew.state['tea_beat'] == 0
    result = recorder.close()
    result.update(blocked_body_holds=True,sorted_preserved_on_continue=True,
        unplaced_stone_returns_to_source=True,singleton_workers=True,
        finite_three_stones=True,final_state=crew.to_dict())
    return result


def bridge_tea_continue(output, root):
    game = game_at_bridge(root)
    crew = game.world.bridge_crew
    # Earn the sorted checkpoint by ordinary simulation, rather than assigning
    # a completed crew record solely to start the tea recovery probes.
    for _ in range(90*FPS):
        if crew.stage == 'ready':break
        game.update(1/FPS,(0,0),False)
    else:raise AssertionError('Sorting setup did not finish')
    recorder = Recorder(game,output,'bridge_tea_continue',controller='bridge_crew')

    def resume():
        assert game.save_progress()
        game.on_title = True
        assert game.begin_journey(True)
        game.opening_fade = game.transfer_cooldown = 0
        game.camera.focus((-2376,616),duration=0);game.location_seconds = 0
        return game.world.bridge_crew

    recorder.key(pygame.K_e)
    recorder.until(lambda:crew.stage == 'request')
    bridge_dialogue(recorder)
    assert crew.state['request_read'] and crew.state['tea_beat'] == 1
    recorder.still('bridge_request_before_continue')
    crew = resume()
    assert crew.stage == 'wobble' and not game.social.active
    recorder.run(.3)
    recorder.still('bridge_request_after_continue')
    recorder.until(lambda:crew.stage == 'reach')
    recorder.run(.7)
    recorder.still('bridge_cup_before_continue')
    crew = resume()
    assert crew.state['tea_beat'] == 2 and not game.social.active
    recorder.until(lambda:crew.stage == 'exchange')
    bridge_dialogue(recorder)
    recorder.until(lambda:crew.stage == 'sit')
    recorder.run(.8)
    recorder.still('bridge_sit_before_continue')
    crew = resume()
    assert crew.state['tea_beat'] == 4 and not game.social.active
    recorder.until(lambda:crew.state['tea_beat'] == 5)
    recorder.run(1.)
    recorder.still('bridge_sit_after_continue')
    result = recorder.close()
    result.update(read_request_not_replayed=True,cup_checkpoint_resumed=True,
        sitting_checkpoint_resumed=True,one_cup=True,one_tool=True,
        completed_tea_once=True,final_state=crew.to_dict())
    return result


def inputs():
    paths = {ROOT/'main.py', ROOT/'grain_farm.py', ROOT/'overworld_world.py',
             ROOT/'regional_audio.py',ROOT/'audio_settings.py',
             ROOT/'bridge_crew.py',ROOT/'overworld_travel.py', ROOT/'social.py', ROOT/'speech_bubble.py',
             ROOT/'assets/dialogue/eldenmere.json',
             ROOT/'assets/portraits/eldenmere/portraits.json',
             ROOT/'assets/maps/overworld/elden_vale/region.json', Path(__file__).resolve()}
    for folder in ('assets/characters/grain_workers', 'assets/characters/road_guards',
                   'assets/characters/bridge_workers','assets/characters/npcs/male_01',
                   'assets/characters/npcs/male_02', 'assets/characters/npcs/male_03'):
        paths.update(path for path in (ROOT/folder).rglob('*') if path.is_file())
    portrait_data = json.loads((ROOT/'assets/portraits/eldenmere/portraits.json').read_text())
    profiles = json.loads((ROOT/'assets/dialogue/eldenmere.json').read_text())['speakers']
    for name in ('road_guard','grain_loader','grain_coworker','bridge_mason','bridge_tender'):
        key = profiles[name]['portrait']
        if key in portrait_data['portraits']:
            paths.add(ROOT/'assets/portraits/eldenmere'/portrait_data['portraits'][key]['file'])
    return {path.relative_to(ROOT).as_posix():digest(path) for path in sorted(paths)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--diagnostic', action='store_true')
    parser.add_argument('--only', choices=('farm','guards','bridge'))
    args = parser.parse_args()
    output = args.output.resolve();output.mkdir(parents=True, exist_ok=True)
    old_report = output/'capture_report.json'
    if old_report.exists():
        for name in json.loads(old_report.read_text()).get('captures',{}):
            if (Path(name).name == name and Path(name).suffix in ('.png','.gif','.mp4')
                    and (output/name).exists()):
                (output/name).unlink()
    started = datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory(prefix='region-npc-review-') as tmp:
        root = Path(tmp)
        cases = {}
        for name in ('before', 'loading', 'blocked', 'guards','bridge','bridge_blocked','bridge_continue'):
            (root/name).mkdir()
        if args.only in (None,'farm'):
            cases['before_repair'] = farm_sequence(output, root/'before', repaired=False)
            cases['loading_and_shared_lift'] = farm_sequence(output, root/'loading', repaired=True)
            cases['blocked_and_continue'] = blocked_and_continue(output, root/'blocked')
        if args.only in (None,'guards'):cases['guards'] = guard_conversations(output, root/'guards')
        if args.only in (None,'bridge'):
            cases['bridge_work_and_tea'] = bridge_sequence(output,root/'bridge')
            cases['bridge_blocked_and_continue'] = bridge_blocked_and_continue(output,root/'bridge_blocked')
            cases['bridge_tea_continue'] = bridge_tea_continue(output,root/'bridge_continue')
    roster = {actor['id'] for case in cases.values() for sample in case['contact_samples']
              for actor in sample['actors']}
    roster.update(row['actor'] for row in cases.get('guards',{}).get('guards',[]))
    if args.only is None:assert len(roster) == 8, roster
    report = {'actual_renderer':True,
        'capture_stage':'diagnostic' if args.diagnostic else 'final',
        'started_at_utc':started, 'finished_at_utc':datetime.now(timezone.utc).isoformat(),
        'fixture':{'earlier_quests':'before-repair and guards: MQ01 completed/MQ02 available; repaired cases: earlier quests completed through public APIs',
                   'mill_repaired':'physical repair flag only in repaired cases',
                   'player_station':'clear camera and player approach stations; blocked carry lane',
                   'actor_relocation':False, 'animation_clock_assignment':False,
                   'farm_progress_assignment':False},
        'npc_roster_exercised':sorted(roster),
        'cases':cases, 'render_input_sha256':inputs(),
        'captures':{path.name:digest(path) for path in sorted(output.iterdir())
                    if path.suffix in ('.png','.gif','.mp4')}}
    (output/'capture_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'cases':list(cases),'inputs':len(report['render_input_sha256']),
                      'captures':len(report['captures'])}))
    pygame.quit()


if __name__ == '__main__':
    main()
