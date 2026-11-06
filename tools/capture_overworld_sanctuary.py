"""Render the actual overworld shrine, its approach, and inert footprint.

Uses a disposable exploration journey, normal town exit, production movement,
and Game.draw. The context view streams small render requests; no replacement
scenery is painted and no reserve/dungeon fixture is created.
"""
from __future__ import annotations
import argparse
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pygame
from PIL import Image

from main import Game
from npc_routines import find_path
from overworld_travel import TOWN_EXIT, WORLD_ID

OUT = ROOT/'docs/reviews/overworld_sanctuary'
LANDMARK = 'ridge_sanctuary'
ROAD = 'sanctuary_approach'


def regional_path(world, start, goal, step=12):
    """A short full-foot route that avoids Eldenmere's automatic contact."""
    start = tuple(round(v/step)*step for v in start)
    goal = tuple(round(v/step)*step for v in goal)
    contact = world.town_entry_rect.inflate(28, 16)
    bounds = pygame.Rect(min(start[0],goal[0])-240, min(start[1],goal[1])-240,
                         abs(start[0]-goal[0])+480, abs(start[1]-goal[1])+480)
    pending = [(math.dist(start,goal),0,start)];costs = {start:0};parents = {}
    while pending:
        _,cost,point = heapq.heappop(pending)
        if point == goal:
            route = [point]
            while point in parents:point = parents[point];route.append(point)
            return list(reversed(route))
        if cost > costs[point]:continue
        for dx,dy in ((step,0),(-step,0),(0,step),(0,-step)):
            other = (point[0]+dx,point[1]+dy)
            if not bounds.collidepoint(other) or contact.collidepoint(other):continue
            middle = ((point[0]+other[0])/2,(point[1]+other[1])/2)
            if not world.can_stand(other) or not world.can_stand(middle):continue
            next_cost = cost+step
            if next_cost >= costs.get(other,math.inf):continue
            costs[other] = next_cost;parents[other] = point
            heapq.heappush(pending,(next_cost+math.dist(other,goal),next_cost,other))
    raise AssertionError(('No regional foot route',start,goal))


def walk(game, points, *, seconds=.05, sample=None):
    for target in points:
        target = pygame.Vector2(target)
        for _ in range(1200):
            delta = target-game.player.position
            if delta.length() < .6:break
            before = game.player.position.copy();tick = min(seconds,delta.length()/72)
            game.update(tick,delta,False)
            if sample is not None:sample(game,tick)
            if game.world.data['id'] != WORLD_ID:
                raise AssertionError(('Unexpected scene transfer',game.world.data['id']))
            if game.player.position == before:
                raise AssertionError(('Blocked regional walk',tuple(before),tuple(target)))
            assert game.world.can_stand(game.player.position),tuple(game.player.position)
        else:raise AssertionError(('Walk stalled',tuple(target)))


def frame(game):
    game.draw()
    return Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB'))


class Movie:
    def __init__(self, path):
        executable = shutil.which('ffmpeg')
        if executable is None:raise RuntimeError('FFmpeg is required for the review movie')
        self.fps = 15;self.frames = 0;self.elapsed = self.next_frame = 0.
        self.process = subprocess.Popen([executable,'-y','-loglevel','error','-f','rawvideo',
            '-pix_fmt','rgb24','-s','960x640','-r',str(self.fps),'-i','-','-an',
            '-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p',
            '-movflags','+faststart',str(path)],stdin=subprocess.PIPE)

    def sample(self, game, seconds):
        self.elapsed += seconds
        if self.elapsed+1e-6 < self.next_frame:return
        picture = frame(game)
        while self.next_frame <= self.elapsed+1e-6:
            self.process.stdin.write(picture.tobytes());self.frames += 1
            self.next_frame += 1/self.fps

    def hold(self, game, seconds):
        picture = frame(game)
        for _ in range(round(seconds*self.fps)):
            self.process.stdin.write(picture.tobytes());self.frames += 1

    def finish(self):
        self.process.stdin.close()
        if self.process.wait() != 0:raise RuntimeError('Review movie encoding failed')


def context(game, output):
    """Actual streamed northeastern region, reduced after each bounded request."""
    world = game.world;bounds = pygame.Rect(0,-96*24,128*24,104*24);scale = 2
    image = pygame.Surface((bounds.width//scale,bounds.height//scale))
    hidden = SimpleNamespace(position=pygame.Vector2(),story_visible=False)
    for y in range(bounds.top,bounds.bottom,384):
        for x in range(bounds.left,bounds.right,384):
            size = (min(384,bounds.right-x),min(384,bounds.bottom-y))
            tile = pygame.Surface(size)
            world.draw(tile,(x,y),hidden,game.elapsed_ms,include_ui=False)
            small = pygame.transform.scale(tile,(size[0]//scale,size[1]//scale))
            image.blit(small,((x-bounds.left)//scale,(y-bounds.top)//scale))
    pygame.image.save(image,output)
    return {'bounds_tiles':[0,-96,128,104],'scale':scale,'largest_render_request':[384,384]}


def key(game, code):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=code,repeat=False))
    game.handle_events()
    pygame.event.post(pygame.event.Event(pygame.KEYUP,key=code))
    game.handle_events()


def capture(output=OUT):
    output.mkdir(parents=True,exist_ok=True)
    region = ROOT/'assets/maps/overworld/elden_vale/region.json'
    geometry_hash = hashlib.sha256(region.read_bytes()).hexdigest()
    report = {'disposable_journey_and_settings':True,'quest_or_equipment_seeding':False,
              'normal_player_files_untouched':True,'region_sha256':geometry_hash,'views':{}}
    with tempfile.TemporaryDirectory(prefix='overworld-sanctuary-') as temporary:
        game = Game(window_size=(960,640),fullscreen=False,start_on_title=False,
            save_path=Path(temporary)/'journey.json',settings_path=Path(temporary)/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0;pygame.event.clear()
        # This is an ordinary exploration fixture, with no story quest changes.
        route = find_path(game.town,game.player.position,TOWN_EXIT,game.town.probe_size,None)
        assert route is not None,'Town exit is unreachable'
        for goal in route:
            for _ in range(600):
                if game.world.data['id']==WORLD_ID:break
                delta = pygame.Vector2(goal)-game.player.position
                if delta.length()<.6:break
                game.update(min(.05,delta.length()/72),delta,False)
            if game.world.data['id']==WORLD_ID:break
        if game.world is game.town:game.update(.01,(0,0),False)
        assert game.world.data['id']==WORLD_ID,'Normal town exit did not transfer'
        game.update(.4,(0,0),False)
        game.location_seconds = 0;game.quest_ui.current_notice = None;game.quest_ui.notices.clear()
        world = game.world
        site = next(p for p in world.region['landmarks'] if p['id']==LANDMARK)
        road = next(r for r in world.region['roads'] if r['id']==ROAD)
        baseline = (game.quests.to_dict(),game.inventory.to_dict(),set(game.social.flags),
                    game.music.desired_track,set(game.scenes))
        movie = Movie(output/'sanctuary_walk.mp4')
        movie.hold(game,1)
        walk(game,regional_path(world,game.player.position,world._tile_point(road['points'][0])),sample=movie.sample)
        frame(game).save(output/'path_junction.png')
        points = [world._tile_point(p) for p in road['points']]
        midpoint = max(1,len(points)*2//3)
        walk(game,points[:midpoint],sample=movie.sample)
        frame(game).save(output/'woodland_approach.png')
        walk(game,points[midpoint:],sample=movie.sample)
        game.update(.4,(0,0),False);movie.sample(game,.4)
        frame(game).save(output/'sanctuary_overworld.png')
        movie.hold(game,2)
        gif_frames = []
        def crossing_sample(g, seconds):
            movie.sample(g,seconds)
            if len(gif_frames)%2==0:gif_frames.append(frame(g).resize((480,320),Image.Resampling.NEAREST))
            else:gif_frames.append(None)
        walk(game,regional_path(world,game.player.position,world._tile_point((87,-66))),sample=movie.sample)
        crossing_before = tuple(game.player.position)
        walk(game,[world._tile_point((93,-66))],sample=crossing_sample)
        walk(game,[world._tile_point((87,-66))],sample=crossing_sample)
        movie.hold(game,1)
        assert (game.quests.to_dict(),game.inventory.to_dict(),set(game.social.flags),
                game.music.desired_track,set(game.scenes))==baseline
        assert game.world is world and not game.social.active and not game.combat.active
        frame(game).save(output/'miniature_crossing.png')
        report['crossing']={'start_pixel':list(crossing_before),
                            'far_edge_pixel':list(world._tile_point((93,-66))),
                            'end_pixel':list(game.player.position),
                            'scene_before':WORLD_ID,'scene_after':game.world.data['id'],
                            'quest_inventory_flags_music_and_scene_set_unchanged':True}
        pictures=[p for p in gif_frames if p is not None]
        indexed=[p.quantize(colors=192,dither=Image.Dither.NONE) for p in pictures]
        indexed[0].save(output/'miniature_crossing.gif',save_all=True,append_images=indexed[1:],
                         duration=100,loop=0,optimize=True)
        key(game,pygame.K_m);assert game.map_open
        ui=game.map_ui._regional();ui.fit();ui.select_landmark(LANDMARK)
        frame(game).save(output/'regional_atlas.png');movie.hold(game,3)
        key(game,pygame.K_m);assert not game.map_open
        movie.finish()
        report['movie']={'file':'sanctuary_walk.mp4','fps':movie.fps,'frames':movie.frames,
                         'seconds':movie.frames/movie.fps}
        report['context']=context(game,output/'region_context.png')
        report['scene']=game.world.data['id'];report['position_pixel']=list(game.player.position)
        report['landmark']=site;report['cache']=world.cache_stats
        assert game.save_progress() and game._read_saved_journey() is not None
        report['saved_journey_valid']=True
        assert hashlib.sha256(region.read_bytes()).hexdigest()==geometry_hash,'Geometry changed during capture'
        pygame.quit()
    names=['sanctuary_overworld.png','woodland_approach.png','miniature_crossing.png','regional_atlas.png']
    contact=Image.new('RGB',(960,640),'#18362b')
    for i,name in enumerate(names):
        with Image.open(output/name) as im:contact.paste(im.resize((480,320),Image.Resampling.NEAREST),((i%2)*480,(i//2)*320))
    contact.save(output/'scene_contact.png')
    for name in names+['path_junction.png','region_context.png','scene_contact.png']:
        with Image.open(output/name) as picture:
            report['views'][name]={'size':list(picture.size),'source':'production game renderer'}
    (output/'verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    (output/'README.md').write_text('''# Ridge Sanctuary — overworld geography

[Watch the approach and inert miniature crossing](sanctuary_walk.mp4)

![Actual game view](sanctuary_overworld.png)

![Regional context](region_context.png)

The preview uses the actual game renderer and ordinary movement from Eldenmere’s
existing southern exit. The exploration fixture changes no quest, equipment or
story flags. The new approach, grove, ridge and miniature are streamed normally.
Walking across the miniature loads no scene and changes no quest, inventory,
music or dialogue state. The detailed reserve and cave are future work.

[Regional atlas](regional_atlas.png) · [Crossing animation](miniature_crossing.gif)

[Verification](verification.json) records the unchanged gameplay state, valid
disposable save, geometry hash and bounded context-render requests. Player save
and settings files are untouched. Reproduce with
`python tools/capture_overworld_sanctuary.py`.
''')
    print(json.dumps({'output':str(output),'movie':report['movie'],'saved_journey_valid':True}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUT)
    capture(parser.parse_args().output)
