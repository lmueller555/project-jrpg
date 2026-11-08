"""Record the expanded dungeon pack using production feet, sprites and light.

All review stations are reached by ordinary movement. The viewer constructs no
Game, quest, journey or settings controller. The complete catalogue is a labelled
asset study; gameplay photographs use the ordinary world renderer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT/'docs/reviews/dungeon_pack'
BASELINE = '0f2bf0b2d0a406113becce3c4c2aba48f704745c'
CATALOG = ROOT/'assets/terrain/limestone_cave/catalog/catalog.json'
SOURCES = {
    'base':'assets/terrain/limestone_cave/assets.json',
    'wall_micro':'assets/terrain/limestone_cave/wall_gems/assets.json',
    'structure':'assets/terrain/limestone_cave/structure/assets.json',
    'water':'assets/terrain/limestone_cave/water/assets.json',
    'geology':'assets/terrain/limestone_cave/geology/assets.json',
    'micro_adapters':'assets/terrain/limestone_cave/micro_adapters/assets.json',
}
GUARD_ROOTS = (
    'main.py', 'sanctuary_cave.py', 'sanctuary_cave_world.py', 'party_travel.py',
    'inventory.py', 'save_game.py', 'overworld_travel.py', 'regent_emergency.py',
    'tools/build_limestone_cave_assets.py', 'tools/build_wall_gems.py',
    'tools/build_limestone_cave_chamber.py', 'tools/preview_limestone_cave.py',
    'assets/maps/eldenmere', 'assets/maps/elden_vale_sanctuary',
    'assets/maps/elden_vale_sanctuary_hall', 'assets/maps/sanctuary_cave',
    'assets/maps/limestone_cave_review', 'assets/terrain/limestone_cave',
    'assets/source/terrain/limestone_cave', 'assets/source/maps/limestone_cave_review',
)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def approved_hashes():
    """Freeze the approved files, even when additions share their parent folder."""
    result = subprocess.run(['git', 'ls-tree', '-r', BASELINE, '--', *GUARD_ROOTS],
                            cwd=ROOT, check=True, capture_output=True, text=True)
    hashes = {}
    for line in result.stdout.splitlines():
        metadata, name = line.split('\t', 1)
        expected = metadata.split()[2]
        data = (ROOT/name).read_bytes()
        actual = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        assert actual == expected, 'The approved production file changed: '+name
        hashes[name] = hashlib.sha256(data).hexdigest()
    return hashes


def source_hashes():
    names = {
        'main.py', 'sanctuary_cave_world.py', 'ui_style.py',
        'tools/preview_dungeon_pack.py', 'tools/capture_dungeon_pack.py',
        'tools/build_dungeon_review_scene.py', 'tools/build_dungeon_pack_catalog.py',
        'tools/build_dungeon_structure.py', 'tools/build_dungeon_water.py',
        'tools/build_dungeon_geology.py', 'tools/build_microcrystal_adapters.py',
        'tools/capture_sanctuary_reserve.py',
    }
    for folder in ('assets/terrain/limestone_cave', 'assets/source/terrain/limestone_cave',
                   'assets/maps/dungeon_pack_review', 'assets/source/maps/dungeon_pack_review',
                   'assets/characters/caelan'):
        names.update(path.relative_to(ROOT).as_posix()
                     for path in (ROOT/folder).rglob('*') if path.is_file())
    pending = [ROOT/name for name in names];seen = set()
    while pending:
        path = pending.pop()
        if path in seen or not path.is_file():continue
        seen.add(path)
        if path.suffix != '.json':continue
        def collect(value):
            if isinstance(value, dict):
                for key,item in value.items():collect(key);collect(item)
            elif isinstance(value, list):
                for item in value:collect(item)
            elif isinstance(value, str) and value.startswith('assets/'):
                referenced = ROOT/value
                if referenced.is_file() and referenced not in seen:pending.append(referenced)
        collect(json.loads(path.read_text()))
    return {path.relative_to(ROOT).as_posix():digest(path) for path in sorted(seen)}


def frame(demo):
    import pygame
    from PIL import Image
    demo.draw()
    return Image.frombytes('RGB', demo.window.get_size(), pygame.image.tobytes(demo.window, 'RGB'))


def native_frame(demo):
    import pygame
    from PIL import Image
    demo.draw()
    return Image.frombytes('RGB', demo.canvas.get_size(), pygame.image.tobytes(demo.canvas, 'RGB'))


class Movie:
    """Transit is sampled at three times speed; material holds use real time."""
    def __init__(self, path):
        binary = shutil.which('ffmpeg')
        if not binary:raise RuntimeError('ffmpeg is required to record the review')
        self.frames = 0;self.clock = 0.
        self.process = subprocess.Popen([
            binary, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
            '-s', '960x640', '-r', '20', '-i', '-', '-an', '-c:v', 'libx264',
            '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', str(path)], stdin=subprocess.PIPE)

    def add(self, image, count=1):
        for _ in range(count):
            self.process.stdin.write(image.tobytes());self.frames += 1

    def transit(self, image, seconds):
        self.clock += seconds
        while self.clock >= .15:
            self.add(image);self.clock -= .15

    def close(self):
        self.process.stdin.close()
        assert self.process.wait() == 0, 'Review video encoding failed'


def check(output=OUT):
    report = json.loads((output/'verification.json').read_text())
    assert report['source_sha256'] == source_hashes(), 'Source changed; recapture the pack.'
    assert report['approved_sha256'] == approved_hashes()
    for name, expected in report['artifact_sha256'].items():
        assert digest(output/name) == expected, 'Review changed: '+name
    assert report['ordinary_movement_only'] and report['no_save_or_settings_files']
    assert report['walking_seen'] and report['running_seen'] and report['all_stations_visited']
    assert report['reduced_motion_static'] and report['water']['animated']
    assert report['pulse']['max_mean'] > report['pulse']['min_mean']
    assert report['microcrystals']['colors'] == ['blue','green','orange','purple','red','white']
    assert report['microcrystals']['max_width'] <= 4 and report['microcrystals']['max_height'] <= 5
    assert report['catalog_entries'] > 0
    print('Dungeon pack catalogue, ordinary traversal, animation, lighting and isolation verified.')


def capture(output=OUT, movie_enabled=True):
    import pygame
    from PIL import Image, ImageDraw, ImageFont, ImageStat
    from tools.preview_dungeon_pack import DungeonPackDemo
    from tools.capture_sanctuary_reserve import path

    output.mkdir(parents=True, exist_ok=True)
    before = source_hashes();approved = approved_hashes()
    demo = DungeonPackDemo();demo.show_guide = False
    movie = Movie(output/'dungeon_pack_walkthrough.mp4') if movie_enabled else None
    report = {'source':'Production Player and SanctuaryCaveWorld in an isolated asset scene',
              'ordinary_movement_only':True, 'no_save_or_settings_files':True,
              'approved_sha256':approved, 'source_sha256':before,
              'walking_seen':False, 'running_seen':False, 'stations':[], 'depth_stations':[]}
    artifacts=[];views={}

    def step(seconds, direction=(0,0), running=False, record=True):
        demo.step(seconds, direction, running)
        assert demo.world.can_stand(demo.player.position), tuple(demo.player.position)
        report['walking_seen'] |= bool(demo.player.moving and not demo.player.running)
        report['running_seen'] |= bool(demo.player.moving and demo.player.running)
        image = frame(demo)
        if movie and record:movie.transit(image, seconds)
        return image

    def photograph(name, hold=8):
        image=frame(demo);filename=name+'.png';image.save(output/filename)
        artifacts.append(filename);views[name]=image
        if movie:movie.add(image,hold)
        report['stations'].append({'name':name,'position':list(demo.player.position),
                                  'camera':list(demo.camera),'file':filename,
                                  'source':'Production World.draw and unchanged native sprites'})
        return image

    def walk(goal, running=False):
        for waypoint in path(demo.world, demo.player.position, goal):
            target=pygame.Vector2(waypoint)
            for _ in range(1600):
                delta=target-demo.player.position
                if delta.length() < .45:break
                old=demo.player.position.copy();speed=108 if running else 72
                step(min(.05,delta.length()/speed),delta,running)
                assert demo.player.position.distance_to(old) > .001, ('Stalled',list(old),waypoint)
            else:raise AssertionError(('Walking budget exceeded',waypoint))

    try:
        points=demo.world.data['cave']['review_points'];photograph('review_entrance')
        for index,(name,point) in enumerate(points.items()):
            walk(point,running=index%2==1);step(.05);photograph(name)
        report['all_stations_visited']=set(points) <= {item['name'] for item in report['stations']}
        checks=demo.world.data['cave'].get('review_checks',{})
        for case in checks.get('depth_cases',[]):
            for suffix,key in (('rear','feet'),('front','visible_feet')):
                walk(case[key]);step(.05);photograph(case['id']+'_'+suffix)
                report['depth_stations'].append({'id':case['id'],'side':suffix,
                                                'position':list(demo.player.position)})

        hero=points.get('hero',points.get('wet_passage',points.get('pulse',next(iter(points.values())))))
        walk(hero);step(.05);photograph('hero_lit')
        demo.material_view=True;photograph('hero_materials');demo.material_view=False
        walk(points.get('pulse',checks.get('light_station',hero)));step(.05)
        low=high=None;frames=[]
        for _ in range(65):
            image=step(.1,record=False);native=native_frame(demo)
            mean=sum(ImageStat.Stat(native).mean)/3
            record=(mean,image,demo.elapsed_ms)
            if low is None or mean<low[0]:low=record
            if high is None or mean>high[0]:high=record
            frames.append(native)
            if movie:movie.add(image,2)
        low[1].save(output/'pulse_trough.png');high[1].save(output/'pulse_peak.png')
        artifacts.extend(('pulse_trough.png','pulse_peak.png'))
        frames[0].save(output/'microcrystal_pulse.gif',save_all=True,append_images=frames[1:],
                       duration=100,loop=0,optimize=False)
        artifacts.append('microcrystal_pulse.gif')
        report['pulse']={'min_mean':low[0],'max_mean':high[0],
                         'seconds':6.5,'crest_clock_ms':high[2]}
        views['pulse_trough']=low[1];views['pulse_peak']=high[1]

        water_station=points.get('water_animation',points.get('seepage_and_inlet',points.get('water',
                      points.get('pool_reflections',points.get('wet_grotto',points.get('pool',
                      next(reversed(points.values()))))))))
        walk(water_station);step(.05);photograph('water_detail')
        demo.pulse_mode=0;water_frames=[]
        for _ in range(25):
            image=step(.1,record=False);water_frames.append(native_frame(demo))
            if movie:movie.add(image,2)
        # Verify the visible water sprites themselves change. A changing light
        # field alone cannot satisfy the water-animation review requirement.
        viewport=pygame.Rect(demo.camera,(480,320));visible_water=[]
        for entity in demo.world.entities:
            if (entity['rect'].colliderect(viewport)
                    and '/water/' in entity['frames'][0] and len(entity['surfaces'])>1
                    and len({pygame.image.tobytes(image,'RGBA') for image in entity['surfaces']})>1):
                visible_water.append(entity['id'])
        report['water']={'animated':bool(visible_water),'visible_entities':visible_water,
                         'source':'Visible production animated water/seepage sprites'}
        water_frames[0].save(output/'water_animation.gif',save_all=True,
                             append_images=water_frames[1:],duration=100,loop=0,optimize=False)
        artifacts.append('water_animation.gif')

        demo.reduced_motion=True;step(.05,record=False);first=native_frame(demo)
        photograph('reduced_motion');demo.step(8.0)
        report['reduced_motion_static']=first.tobytes()==native_frame(demo).tobytes()
        assert report['reduced_motion_static'], 'Reduced motion animates scenery'
        demo.reduced_motion=False;demo.world.reduced_motion=False

        size=demo.world.size;whole=pygame.Surface(size)
        for y in range(0,size[1],320):
            for x in range(0,size[0],480):
                tile=pygame.Surface((480,320))
                demo.world.draw(tile,(x,y),demo.player,high[2],include_ui=False)
                whole.blit(tile,(x,y))
        whole_image=Image.frombytes('RGB',size,pygame.image.tobytes(whole,'RGB'))
        whole_image.resize((size[0]*2,size[1]*2),Image.Resampling.NEAREST).save(output/'whole_scene.png')
        artifacts.append('whole_scene.png')

        sizes=[];colors=set();count=0;module_manifests=[json.loads((ROOT/p).read_text()) for p in SOURCES.values()]
        for record in demo.world.data['entities']:
            name=record.get('source_module')
            if record.get('light_index') is None or not name:continue
            module=next((manifest['modules'][name] for manifest in module_manifests
                         if name in manifest.get('modules',{})),None)
            if module and module.get('core_components'):
                colors.add(module['gem_color']);sizes.extend(module['crystal_sizes']);count+=module['crystal_count']
        report['microcrystals']={'colors':sorted(colors),'count':count,
                                'max_width':max(size[0] for size in sizes),
                                'max_height':max(size[1] for size in sizes)}
        catalog=json.loads(CATALOG.read_text());report['catalog_entries']=len(catalog['entries'])
        report['catalog_pages']=len(catalog['pages'])
        selected=['hero_lit','hero_materials']
        selected += [name for name in points if name in views and name not in selected][:6]
        board=Image.new('RGB',(980,16+354*math.ceil(len(selected)/2)),'#202925')
        draw=ImageDraw.Draw(board);font=ImageFont.load_default(size=16)
        for index,name in enumerate(selected):
            x=8+index%2*488;y=8+index//2*354
            draw.text((x+8,y+6),name.replace('_',' ').title(),fill='#eee6cf',font=font)
            board.paste(views[name].resize((480,320),Image.Resampling.NEAREST),(x,y+27))
        board.save(output/'contact_sheet.png');artifacts.append('contact_sheet.png')
    finally:
        if movie:movie.close()
        demo.close()
    if movie:
        artifacts.append('dungeon_pack_walkthrough.mp4');report['movie_seconds']=movie.frames/20
        assert report['movie_seconds'] <= 100, 'Review video should stay under 100 seconds'
    assert approved==approved_hashes(), 'Review modified an approved asset'
    assert before==source_hashes(), 'Source changed during capture; wait for exports to freeze'
    report['artifact_sha256']={name:digest(output/name) for name in sorted(artifacts)}
    (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    check(output);return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUT)
    parser.add_argument('--check',action='store_true');parser.add_argument('--no-movie',action='store_true')
    args=parser.parse_args(argv)
    if args.check:check(args.output)
    else:capture(args.output,not args.no_movie)
    return 0


if __name__=='__main__':raise SystemExit(main())
