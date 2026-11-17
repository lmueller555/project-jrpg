"""Review the eastern growing plot against its clean pre-PR baseline.

Native initialized-Game views use disclosed clear-ground fixtures. Walking,
running, the Venn doorway and Continue use production code with
residents present. Only disposable save positions are changed for blocked-checkpoint
recovery fixtures; gameplay progress and production inputs remain untouched.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import capture_eldenmere_settlement_framework as framework
from tools.capture_eldenmere_streets import native_ground
from tools.capture_eldenmere_workyards import read, frame_paths

import numpy as np
from PIL import Image, ImageChops, ImageDraw
import pygame

from npc_routines import find_path

DEFAULT_OUTPUT = ROOT/'docs/reviews/eldenmere_growing'
PREFIX = 'settlement.growing.'
GROUND_PREFIX = 'assets/maps/eldenmere/town_hd/town/chunks/'
ALLOWED_FIELDS = {'entities','collision','ground_overlays','overview','settlement_growing'}
HOUSE_IDS = ('venn',)
ORIGINAL_PLOT_RECT = [1296,624,96,168]
PRIOR_LEDGERS = ('settlement_dressing','settlement_workyards','settlement_commons','settlement_households')
DETAILS = (
    ('venn_frontage',(1247.5,762),(1247.5,744)),
    ('upper_growing_terrace',(1368,576),(1344,564)),
    ('lower_growing_area',(1248,1008),(1272,1008)),
    ('irrigation_gate',(1404,684),(1428,648)),
    ('irrigation_channel',(1428,744),(1428,708)),
    ('growing_approach',(1176,864),(1200,840)),
    ('western_terrace_approach',(1080,912),(1128,912)),
)


def growing_entities(town):
    return [record for record in town['entities'] if record['id'].startswith(PREFIX)]


def parcel_rectangles(ledger):
    """The old source plot, not the larger eastern district, bounds review."""
    source=read(ROOT/'assets/maps/eldenmere/terrain_foundation/adapted_plan.json')
    plot=next(item for item in source['spaces'] if item['id']=='venn_plots')
    expected=[value*source['tile_size_px'] for value in plot['rect']]
    if (ledger['district']!='eastern_growing' or ledger['scope_rect']!=ORIGINAL_PLOT_RECT
            or expected!=ORIGINAL_PLOT_RECT):
        raise AssertionError(('Growing scope must equal the original source venn_plots',ledger['scope_rect'],expected))
    return {'venn_plots':expected}


def parcel_mask(size, parcels, camera=(0,0)):
    result=Image.new('L',size);painter=ImageDraw.Draw(result);cx,cy=camera
    for x,y,w,h in parcels.values():
        painter.rectangle((round((x-cx)*2),round((y-cy)*2),round((x+w-cx)*2)-1,round((y+h-cy)*2)-1),fill=255)
    return result


def contains(rect, other):
    x,y,w,h=rect;ox,oy,ow,oh=other
    return x<=ox and y<=oy and ox+ow<=x+w and oy+oh<=y+h


def growing_snapshot():
    town=read(framework.TOWN);files={}
    for path in sorted(set(framework.image_paths([town['settlement_growing']['ground_entities'],town['settlement_growing']['bed_contacts']]))):
        raw=(ROOT/path).read_bytes();files[path]={'sha256':framework.digest(raw),'bytes':len(raw)}
    return {'production':framework.production_snapshot(),'flat_source_files':files}


def bed_contacts(ledger):
    """Validate one authored native contact mask across each complete bed."""
    entries=ledger['bed_contacts']
    expected={f'bed_{index}':[1320,y,48,24] for index,y in enumerate((648,696,744),1)}
    if len(entries)!=3 or {item['id'] for item in entries}!=set(expected):
        raise AssertionError('Growing must declare exactly three source-owned bed contacts')
    all_assigned=[];result=[]
    for item in entries:
        if item['rect']!=expected[item['id']]:raise AssertionError(('Contact rectangle changed',item))
        x,y,w,h=item['rect'];path=item['mask']
        with Image.open(ROOT/path) as raw:
            if raw.mode!='L' or raw.size!=(96,48):raise AssertionError(('Bed contact must be native96x48L',path,raw.mode,raw.size))
            mask=raw.copy()
        if set(mask.tobytes())!={0,255}:raise AssertionError(('Bed contact requires binary notched coverage',path))
        if mask.crop((2,2,94,46)).getextrema()!=(255,255):
            raise AssertionError(('Contact notches exceed the two-art-pixel perimeter',path))
        tiles=[tile for tile in ledger['ground_entities'] if contains(item['rect'],[*tile['position'],*tile['logical_size']])]
        if (len(tiles)!=2 or {tuple(tile['position']) for tile in tiles}!={(x,y),(x+24,y)}
                or any(tile['logical_size']!=[24,24] for tile in tiles)):
            raise AssertionError(('Whole bed must own exactly two adjacent24x24tiles',item['id']))
        tiles.sort(key=lambda tile:tile['position'][0])
        if frame_paths(tiles[0])!=frame_paths(tiles[1]):raise AssertionError(('Bed source assets differ across its internal seam',item['id']))
        body=Image.new('RGBA',(96,48))
        for tile in tiles:
            paths=frame_paths(tile)
            if len(paths)!=1:raise AssertionError('Field source cadence must remain static')
            with Image.open(ROOT/paths[0]) as raw:picture=raw.convert('RGBA')
            if picture.size!=(48,48) or set(picture.getchannel('A').tobytes())-{0,255}:
                raise AssertionError('Field tile lost native density or hard source alpha')
            body.alpha_composite(picture,(round((tile['position'][0]-x)*2),0))
            all_assigned.append(tile['id'])
        result.append({'record':item,'mask':mask,'body':body,'tiles':tiles})
    if len(all_assigned)!=len(set(all_assigned)) or set(all_assigned)!={tile['id'] for tile in ledger['ground_entities']}:
        raise AssertionError('Each flat tile must belong to exactly one whole-bed contact')
    return result


def ground_coverage(town, ledger):
    """Only source alpha multiplied by the explicit whole-bed mask may change."""
    size=tuple(value*2 for value in town['size_pixels']);mask=Image.new('L',size)
    for entry in bed_contacts(ledger):
        x,y,_,_=entry['record']['rect']
        active=ImageChops.multiply(entry['mask'],entry['body'].getchannel('A'))
        layer=Image.new('L',size);layer.paste(active,(round(x*2),round(y*2)));mask=ImageChops.lighter(mask,layer)
    plot=parcel_mask(size,parcel_rectangles(ledger))
    if np.any((np.asarray(mask)!=0)&(np.asarray(plot)==0)):
        raise AssertionError('Field contact alpha leaves the original growing plot')
    return mask


def compare_baseline(baseline,folder):
    original,town=read(baseline/'town.json'),read(framework.TOWN);ledger=town['settlement_growing']
    parcels=parcel_rectangles(ledger);scope=ledger['scope_rect'];world=growing_entities(town);flat=ledger['ground_entities']
    if len(world)!=1 or len(flat)!=6 or world!=ledger['entities']:
        raise AssertionError('Growing must own exactly six flat field tiles and one live service crate')
    all_new=[*world,*flat];ids={item['id'] for item in all_new}
    if len(ids)!=len(all_new) or any(not item['id'].startswith(PREFIX) for item in all_new):
        raise AssertionError('Flat/world growing owners must be unique and explicit')
    if [item for item in town['entities'] if not item['id'].startswith(PREFIX)]!=original['entities']:
        raise AssertionError('Existing entity ownership changed')
    for key in (*PRIOR_LEDGERS,'grass','settlement_streets','cartography'):
        if town[key]!=original[key]:raise AssertionError(('Previous district/grass/street ownership changed',key))
    if ledger['ground_cells'] or ledger.get('retired_grass_ids') or ledger.get('retired_grass_records'):
        raise AssertionError('Growing cannot paint extra soil cells or retire existing grass')
    placements={item['id']:item for item in ledger['placements']}
    if len(placements)!=len(ledger['placements']) or set(placements)!=ids:
        raise AssertionError('Growing placement registry and flat/world owners differ')
    for entity in all_new:
        if (entity['artwork_pixels_per_world_pixel']!=2
                or not contains(scope,[*entity['position'],*entity['logical_size']])):
            raise AssertionError(('New artwork leaves the native source plot',entity['id']))
        for path in frame_paths(entity):
            with Image.open(ROOT/path) as raw:
                if raw.size!=tuple(round(value*2) for value in entity['logical_size']):
                    raise AssertionError(('Artwork lost native density',entity['id'],path))
    if any(item['logical_size']!=[24,24] for item in flat):
        raise AssertionError('Each flat field tile must retain its original24x24logicalsize')
    changed_fields=sorted(key for key in original.keys()|town.keys() if original.get(key)!=town.get(key))
    if set(changed_fields)-ALLOWED_FIELDS:raise AssertionError(('Unrelated map fields changed',changed_fields))
    previous=read(baseline/'observations.json')['production'];current=framework.production_snapshot()
    allowed={current['town_map'],town['collision'],town['overview'],original['overview']}
    images=set(framework.image_paths(all_new));old_files=previous['active_files'];new_files=current['active_files']
    changed_files=sorted(path for path in old_files.keys()|new_files.keys() if old_files.get(path)!=new_files.get(path))
    unexpected=[path for path in changed_files if path not in allowed and not path.startswith(GROUND_PREFIX)
                and not(path in images and path not in old_files)]
    if unexpected:raise AssertionError(('Existing non-ground artwork changed',unexpected))
    with Image.open(baseline/'collision.png') as raw:before_collision=raw.convert('L')
    expected=before_collision.copy();painter=ImageDraw.Draw(expected);supports=ledger['solid_footprints']
    if len(supports)!=1 or supports[0]['id']!=world[0]['id']:
        raise AssertionError('Only the explicit service crate may add collision')
    for support in supports:
        x,y,w,h=support['rect']
        if (any(type(value) is not int for value in (x,y,w,h)) or min(w,h)<=0
                or not contains(scope,support['rect'])):raise AssertionError(('Invalid crate support',support))
        painter.rectangle((x,y,x+w-1,y+h-1),fill=255)
    with Image.open(ROOT/town['collision']) as raw:collision=raw.convert('L')
    if collision.size!=expected.size or collision.tobytes()!=expected.tobytes():
        raise AssertionError('Collision is not exactly baseline union the service crate support')
    if (baseline/'navigation_allowed.png').read_bytes()!=(ROOT/town['navigation_allowed']).read_bytes():
        raise AssertionError('Navigation changed')
    contacts=bed_contacts(ledger);mask=ground_coverage(town,ledger);coverage=np.asarray(mask)!=0;x,y,w,h=scope
    mask.crop((x*2,y*2,(x+w)*2,(y+h)*2)).save(folder/'field_ground_coverage.png')
    phases=[];source_checks=[];contact_checks=[]
    (folder/'before_beds').mkdir(parents=True,exist_ok=True)
    before_beds={'source_revision':read(baseline/'baseline_revision.json')['git_commit'],
        'source':'Exact unscaled crop from original full native ground phase images before PR7 changes.',
        'beds':[{'id':entry['record']['id'],'rect':entry['record']['rect'],'phases':[]} for entry in contacts]}
    for phase in range(6):
        after=native_ground(town,phase*200)
        with Image.open(baseline/f'ground_phase_{phase}.png') as raw:before=raw.convert('RGBA')
        if before.size!=after.size:raise AssertionError('Native ground dimensions changed')
        changes=np.any(np.asarray(before)!=np.asarray(after),axis=2)
        item={'phase':phase,'elapsed_ms':phase*200,'changed_native_pixels':int(np.count_nonzero(changes)),
              'changed_outside_exact_flat_alpha':int(np.count_nonzero(changes&~coverage)),
              'before_rgba_sha256':framework.digest(before.tobytes()),'after_rgba_sha256':framework.digest(after.tobytes())}
        phases.append(item)
        if item['changed_outside_exact_flat_alpha']:raise AssertionError(('Ground changed outside exact field source alpha',item))
        for entity in flat:
            path=frame_paths(entity)[0]
            with Image.open(ROOT/path) as raw:source=raw.convert('RGBA')
            sx,sy=entity['position'];sw,sh=entity['logical_size']
            crop=after.crop((round(sx*2),round(sy*2),round((sx+sw)*2),round((sy+sh)*2)))
            pixels=np.asarray(source)
            contact=next(entry for entry in contacts if entity['id'] in {tile['id'] for tile in entry['tiles']})
            bx,by,_,_=contact['record']['rect']
            local=contact['mask'].crop((round((sx-bx)*2),round((sy-by)*2),round((sx+sw-bx)*2),round((sy+sh-by)*2)))
            opaque=(pixels[:,:,3]==255)&(np.asarray(local)==255)
            mismatches=int(np.count_nonzero(np.any(np.asarray(crop)!=pixels,axis=2)&opaque))
            check={'entity':entity['id'],'phase':phase,'source_image':path,'source_rgba_sha256':framework.digest(source.tobytes()),
                   'source_file_sha256':framework.digest((ROOT/path).read_bytes()),'contact_mask':contact['record']['mask'],
                   'source_opaque_pixels_before_contact':int(np.count_nonzero(pixels[:,:,3]==255)),
                   'opaque_source_pixels':int(np.count_nonzero(opaque)),
                   'opaque_source_pixel_mismatches':mismatches,'baked_crop_rgba_sha256':framework.digest(crop.tobytes())}
            source_checks.append(check)
            if mismatches:raise AssertionError(('Baked native field does not match its exact source pixels',check))
        for contact in contacts:
            item=contact['record'];bx,by,bw,bh=item['rect'];box=(bx*2,by*2,(bx+bw)*2,(by+bh)*2)
            first=before.crop(box);actual=after.crop(box);overlay=contact['body'].copy()
            before_path=folder/'before_beds'/f"{item['id']}_phase_{phase}.png"
            first.save(before_path)
            original_bed=next(bed for bed in before_beds['beds'] if bed['id']==item['id'])
            original_bed['phases'].append({'phase':phase,'elapsed_ms':phase*200,
                'image':before_path.relative_to(folder).as_posix(),
                'png_sha256':framework.digest(before_path.read_bytes()),'rgba_sha256':framework.digest(first.tobytes())})
            overlay.putalpha(ImageChops.multiply(overlay.getchannel('A'),contact['mask']))
            expected_bed=first.copy();expected_bed.alpha_composite(overlay)
            differences=np.any(np.asarray(actual)!=np.asarray(first),axis=2)
            outside=int(np.count_nonzero(differences&(np.asarray(contact['mask'])==0)))
            mismatches=int(np.count_nonzero(np.any(np.asarray(actual)!=np.asarray(expected_bed),axis=2)))
            check={'bed':item['id'],'phase':phase,'rect':item['rect'],'mask':item['mask'],
                   'mask_file_sha256':framework.digest((ROOT/item['mask']).read_bytes()),
                   'mask_native_size':list(contact['mask'].size),'mask_values':[0,255],
                   'interior_inset_art_pixels':2,'fully_opaque_interior':True,
                   'contact_zero_pixels':int(np.count_nonzero(np.asarray(contact['mask'])==0)),
                   'contact_zero_baseline_mismatches':outside,'whole_bed_composite_mismatches':mismatches,
                   'baseline_rgba_sha256':framework.digest(first.tobytes()),
                   'expected_rgba_sha256':framework.digest(expected_bed.tobytes()),
                   'actual_rgba_sha256':framework.digest(actual.tobytes())}
            contact_checks.append(check)
            if outside or mismatches:raise AssertionError(('Whole-bed contact failed baseline/source composition',check))
    (folder/'before_bed_ground.json').write_text(json.dumps(before_beds,indent=2)+'\n')
    for stale in folder.glob('before_*.png'):stale.unlink()
    for path in sorted(baseline.glob('*.png')):
        if path.name.startswith('ground_phase_') or path.name in {'collision.png','navigation_allowed.png','protection_plan_diagnostic.png'}:continue
        shutil.copyfile(path,folder/('before_'+path.name))
    for source,dest in (('observations.json','before_observations.json'),('town.json','before_town.json'),
                        ('baseline_revision.json','before_revision.json'),('growing_details.json','before_growing_details.json')):
        shutil.copyfile(baseline/source,folder/dest)
    return {'baseline_revision':read(baseline/'baseline_revision.json'),'changed_map_fields':changed_fields,'changed_active_files':changed_files,
            'scope_rect':scope,'existing_entities_unchanged':True,'all_four_prior_ledgers_unchanged':True,'grass_unchanged':True,
            'street_ledger_and_cartography_unchanged':True,'existing_non_ground_artwork_unchanged':True,
            'world_entity_ids':[item['id'] for item in world],'flat_field_ids':[item['id'] for item in flat],
            'solid_footprints':supports,'collision_exact_additive_delta':True,
            'collision_added_logical_pixels':int(np.count_nonzero(np.asarray(collision)!=np.asarray(before_collision))),
            'navigation_identical_bytes':True,'ground_coverage_native_pixels':int(np.count_nonzero(coverage)),
            'ground_phases':phases,'native_flat_source_checks':source_checks,'whole_bed_contact_checks':contact_checks}


def compare_view_scope(baseline,folder,capture):
    previous=read(baseline/'observations.json');parcels=parcel_rectangles(read(framework.TOWN)['settlement_growing']);results=[]
    for name,fixture in capture['views'].items():
        if fixture!=previous['views'][name]:raise AssertionError(('Production camera fixture changed',name))
        with Image.open(baseline/(name+'.png')) as raw:before=np.asarray(raw.convert('RGB'))
        with Image.open(folder/(name+'.png')) as raw:after=np.asarray(raw.convert('RGB'))
        mask=np.asarray(parcel_mask((after.shape[1],after.shape[0]),parcels,fixture['camera_logical']))!=0
        changes=np.any(before!=after,axis=2);item={'name':name,'changed_native_pixels':int(np.count_nonzero(changes)),
              'changed_outside_growing_plot':int(np.count_nonzero(changes&~mask))}
        results.append(item)
        if item['changed_outside_growing_plot']:raise AssertionError(('Native view changed outside original source plot',item))
    return results


def gameplay_capture(folder, *, baseline=None, movement=True):
    report = {'fixture':'Fresh production Game, opening disabled, disposable saves/settings, disclosed clear-ground starts. '
              'Residents and routines remain active; no quests, actors or scenery are replaced.',
              'routes':[],'details':[],'doorway_roundtrips':[],'ambient_conversations':[],
              'detail_view_comparison':[]}
    fixtures = DETAILS
    if baseline is not None:
        details = read(baseline/'growing_details.json')
        fixtures = tuple((name,tuple(item['actual_player_logical']),tuple(item['camera_focus_logical']))
                         for name,item in details['views'].items())
    with tempfile.TemporaryDirectory(prefix='eldenmere-growing-review-') as directory:
        temporary = Path(directory)
        options = dict(fullscreen=False,window_size=(960,640),start_on_title=True,
                       save_path=temporary/'journey.json',settings_path=temporary/'settings.json')
        game = framework.Game(**options)
        try:
            game.on_title=False;game.opening.restore({'version':1,'stage':'disabled'})
            game.opening_fade=game.transfer_cooldown=0
            game.audio.set_music(0);game.audio.set_effects(0);game.world=game.town
            initial = framework.canonical(framework.meaningful_state(game))

            def place(point, focus=None):
                if game.world is not game.town or not game.town.can_stand(point):
                    raise AssertionError(('Blocked growing fixture', point))
                game.player.position.update(point);game.player.moving=game.player.running=False
                game.player.walk_ms=0;game.location_label=None;game.location_seconds=0
                game.saves.notice_seconds=game.transfer_cooldown=0;game.camera.reset()
                if focus is not None:game.camera.focus(focus,duration=0)

            def choose(candidates, label, focus=None):
                for _ in range(30):
                    for point in candidates:
                        if game.town.can_stand(point):
                            place(point,focus)
                            return {'label':label,'candidates':[list(p) for p in candidates],'selected':list(point)}
                    game.update(.2,(0,0),False)
                raise AssertionError(('No clear growing fixture after waiting for actors', label))

            for name,point,focus in fixtures:
                px,py = point
                chosen = choose((point,(px+8,py),(px-8,py),(px,py+8),(px,py-8)),name,focus)
                game.player.facing='back'
                item = {'name':name,'start_fixture':chosen,'baseline_player_logical':list(point),
                        'player_logical':list(game.player.position),'focus_logical':list(focus),
                        'camera_logical':list(game.camera.position())}
                for reduced in (False,True):
                    game.audio.set_reduced_motion(reduced);game._update_grass(0)
                    pictures=[]
                    for elapsed in (0,600):
                        game.elapsed_ms=elapsed;game.draw()
                        if game.window.get_size() != (960,640):raise AssertionError('Non-native growing view')
                        pictures.append(Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB')))
                    name_out=name+('_reduced' if reduced else '')+'.png';pictures[0].save(folder/name_out)
                    changes=framework.changed_pixels(*pictures)
                    if reduced and changes:
                        raise AssertionError(('Reduced-motion growing view changed',name,changes))
                    item['reduced' if reduced else 'normal']={'image':name_out,'changed_pixels_at_600ms':changes,
                        'first_rgb_sha256':framework.digest(pictures[0].tobytes()),
                        'second_rgb_sha256':framework.digest(pictures[1].tobytes())}
                    if not reduced and baseline is not None:
                        prior=details['views'][name]
                        if (list(game.player.position)!=prior['actual_player_logical']
                                or list(game.camera.position())!=prior['camera_logical']):
                            raise AssertionError(('Protected baseline frontage fixture changed',name,chosen))
                        with Image.open(baseline/(name+'.png')) as raw:
                            first=np.asarray(raw.convert('RGB'))
                        after=np.asarray(pictures[0]);delta=np.any(first!=after,axis=2)
                        parcels=parcel_rectangles(game.town.data['settlement_growing'])
                        mask=np.asarray(parcel_mask(pictures[0].size,parcels,game.camera.position()))!=0
                        check={'name':name,'changed_native_pixels':int(np.count_nonzero(delta)),
                               'changed_outside_growing_plot':int(np.count_nonzero(delta&~mask))}
                        report['detail_view_comparison'].append(check)
                        if check['changed_outside_growing_plot']:
                            raise AssertionError(('Native detail changed outside the original growing plot',check))
                report['details'].append(item)
            game.audio.set_reduced_motion(False);game._update_grass(0)

            # Use Caelan's real registered sprite in the ordinary native Game
            # frame. Flat field alpha must actually overlap opaque body pixels,
            # and every opaque body texel must remain visible over the baked
            # field. No marker actor, hidden NPC or substitute scene is used.
            depth_fixture=choose(((1344,708),(1344,660),(1344,756)),
                                 'actual_player_on_field',(1344,708))
            game.player.facing='front';game.elapsed_ms=0;game.draw()
            pygame.image.save(game.window,str(folder/'field_player_depth.png'))
            sprite=game.player.sprite();native=getattr(sprite,'native',sprite)
            art=Image.frombytes('RGBA',native.get_size(),pygame.image.tobytes(native,'RGBA'))
            anchor=game.player.draw_anchor;cx,cy=game.camera.position()
            px,py=(round(value) for value in game.player.position)
            origin=(round((px-anchor[0]-cx)*2),round((py-anchor[1]-cy)*2))
            frame=Image.frombytes('RGB',game.window.get_size(),pygame.image.tobytes(game.window,'RGB'))
            actual=frame.crop((*origin,origin[0]+art.width,origin[1]+art.height))
            actual.save(folder/'field_player_native_crop.png')
            source=np.asarray(art);opaque=source[:,:,3]==255
            mismatches=int(np.count_nonzero(np.any(np.asarray(actual)!=source[:,:,:3],axis=2)&opaque))
            alpha=ground_coverage(game.town.data,game.town.data['settlement_growing'])
            wx,wy=round((px-anchor[0])*2),round((py-anchor[1])*2)
            field=np.asarray(alpha.crop((wx,wy,wx+art.width,wy+art.height)))!=0
            overlap=int(np.count_nonzero(field&opaque))
            if not overlap or mismatches:
                raise AssertionError(('Actual player is not correctly above native baked fields',overlap,mismatches))
            report['player_field_depth']={'fixture':depth_fixture,'actual_player_facing':'front',
                'native_sprite_size':list(art.size),'draw_anchor_logical':list(anchor),
                'camera_logical':[cx,cy],'native_sprite_origin':list(origin),
                'opaque_player_pixels':int(np.count_nonzero(opaque)),
                'opaque_player_pixels_overlapping_field_alpha':overlap,
                'opaque_player_pixel_mismatches':mismatches,'image':'field_player_depth.png',
                'native_crop':'field_player_native_crop.png','actual_sprite_rgba_sha256':framework.digest(art.tobytes())}

            def diagnostic(label):
                return {'label':label,'position':list(game.player.position),'scene':game.world.data['id'],
                        'social_script':game.social.script_identifier,
                        'nearby_actors':[(actor.data['id'],list(actor.position)) for actor in game.world.npcs
                                         if actor.position.distance_to(game.player.position)<80]}

            def drive(world, target, running, label):
                target=pygame.Vector2(target);trace=[list(game.player.position)];replans=0;waits=0
                for _ in range(30):
                    if game.world is not world:raise AssertionError(('Unexpected scene transfer',diagnostic(label)))
                    if game.player.position.distance_to(target)<.02:
                        return {'target':list(target),'trace':trace,'frames':len(trace)-1,'replans':replans,'wait_seconds':waits}
                    if game.social.scripted:raise AssertionError(('Scripted exchange entered',diagnostic(label)))
                    if game.social.actor is not None:
                        event={'actor':game.social.actor.data['id'],'conversation':(game.social.conversation or {}).get('id'),
                               'route':label,'player_position':list(game.player.position)}
                        if not any(item['actor']==event['actor'] and item['conversation']==event['conversation']
                                   for item in report['ambient_conversations']):
                            report['ambient_conversations'].append(event)
                    # The NPC planner is an even-unit lattice. Door anchors may
                    # be odd or half-unit; append a real-input exact approach.
                    gx,gy=round(target.x/2)*2,round(target.y/2)*2
                    candidates=sorted({(gx+dx,gy+dy) for dx in (-2,0,2) for dy in (-2,0,2)},
                                      key=lambda p:pygame.Vector2(p).distance_squared_to(target))
                    lattice=next((p for p in candidates if world.can_stand(p)),None)
                    path=None if lattice is None else find_path(world,game.player.position,lattice,world.probe_size,None)
                    if path is None:
                        replans+=1;waits+=.2;game.update(.2,(0,0),False);continue
                    if not path or pygame.Vector2(path[-1]).distance_to(target)>.01:path.append(tuple(target))
                    stalled=False
                    for waypoint in path:
                        goal=pygame.Vector2(waypoint)
                        for _ in range(3000):
                            delta=goal-game.player.position
                            if delta.length()<.01:break
                            before=game.player.position.copy()
                            game.update(min(1/30,delta.length()/(108 if running else 72)),delta,running)
                            if game.world is not world or not world.can_stand(game.player.position):
                                raise AssertionError(('Unsafe growing movement',diagnostic(label)))
                            trace.append([round(v,4) for v in game.player.position])
                            if before.distance_to(game.player.position)<.001:stalled=True;break
                        else:raise AssertionError(('Growing route frame budget',diagnostic(label)))
                        if stalled:break
                    if not stalled and game.player.position.distance_to(target)<.02:
                        return {'target':list(target),'trace':trace,'frames':len(trace)-1,'replans':replans,'wait_seconds':waits}
                    replans+=1;waits+=.2;game.update(.2,(0,0),False)
                raise AssertionError(('Growing route remained obstructed',list(target),diagnostic(label)))

            def follow(label, route, running):
                sx,sy=route[0]
                fixture=choose((route[0],(sx+8,sy),(sx-8,sy),(sx,sy+8),(sx,sy-8)),label)
                segments=[drive(game.town,target,running,label) for target in route[1:]]
                return {'label':label,'running':running,'goals':route,'start_fixture':fixture,
                        'segments':segments,'update_frames':sum(item['frames'] for item in segments),
                        'replans':sum(item['replans'] for item in segments),'passed':True}

            if movement:
                routes=(
                    ('upper_field_aisle',[[1380,636],[1380,684],[1332,684]]),
                    ('middle_field_aisle',[[1380,732],[1344,732]]),
                    ('lower_field_aisle',[[1380,780],[1344,780],[1320,780]]),
                    ('plot_approach',[[1248,816],[1380,816],[1380,780],[1368,732]]),
                    ('eastern_steps_west_lane',[[1172,912],[1172,864],[1172,816]]),
                    ('eastern_steps_east_lane',[[1180,912],[1180,864],[1180,816]]),
                    ('irrigation_contacts',[[1380,816],[1428,816],[1428,744],[1428,694],[1428,670]]),
                    ('venn_frontage',[[1248,816],[1247.5,762],[1247.5,738]]),
                )
                for name,route in routes:
                    for running in (False,True):
                        for reverse in (False,True):
                            label=name+('_run' if running else '_walk')+('_return' if reverse else '')
                            report['routes'].append(follow(label,list(reversed(route)) if reverse else route,running))
                            print('Passed route:',label,flush=True)
                for door_id in HOUSE_IDS:
                    for running in (False,True):
                        outer=next(door.data for door in game.town.doors if door.data['id']==door_id)
                        x,y=outer['anchor']
                        fixture=choose(((x,y+36),(x+24,y+36),(x-24,y+36),(x,y+54)),door_id+'_doorway')
                        approaches=[drive(game.town,(x,y+12),running,door_id+'_front_door')]
                        entry_frames=exit_frames=0
                        for _ in range(240):
                            game.update(1/60,(0,-1),running);entry_frames+=1
                            if game.world is not game.town:break
                        else:raise AssertionError(('Growing doorway did not enter',diagnostic(door_id)))
                        interior=game.world
                        if interior.data['id']!=door_id:raise AssertionError(('Doorway entered another scene',door_id,interior.data['id']))
                        back=next(door.data for door in interior.doors if door.data['id']=='courtyard')
                        bx,by=back['anchor']
                        # Select a disclosed clear interior rearm point and
                        # reach it by input; never reset the transition guard.
                        candidates=((bx,by-48),(bx,by-36),(bx,by-24),(bx-24,by-24),(bx+24,by-24))
                        clear=None
                        for _ in range(30):
                            clear=next((point for point in candidates if interior.can_stand(point)),None)
                            if clear is not None:break
                            game.update(.2,(0,0),False)
                        if clear is None:raise AssertionError(('No clear interior rearm fixture',door_id))
                        arrival_fixture={'requested':list(candidates[0]),'candidates':[list(p) for p in candidates],
                                         'selected':list(clear),'correction':clear!=candidates[0]}
                        approaches.append(drive(interior,clear,running,door_id+'_clear_arrival'))
                        game.update(.6,(0,0),False)
                        approaches.append(drive(interior,(bx,by-12),running,door_id+'_return_approach'))
                        for _ in range(240):
                            game.update(1/60,(0,1),running);exit_frames+=1
                            if game.world is game.town:break
                        else:raise AssertionError(('Growing doorway did not return',diagnostic(door_id)))
                        if not game.town.can_stand(game.player.position):raise AssertionError(('Blocked house return',door_id))
                        game.draw();name=door_id+'_roundtrip_'+('run' if running else 'walk')+'.png'
                        pygame.image.save(game.window,str(folder/name))
                        report['doorway_roundtrips'].append({'door':door_id,'running':running,'interior':interior.data['id'],
                            'start_fixture':fixture,'production_approaches':approaches,'entry_update_frames':entry_frames,
                            'clear_arrival_fixture':arrival_fixture,
                            'exit_update_frames':exit_frames,'return_position':list(game.player.position),'clear_ground':True,'image':name})
                        print('Passed doorway:',door_id,'run' if running else 'walk',flush=True)

                fixture=choose(((1368,732),(1380,780),(1247.5,762)),'save_start')
                if not game.save_progress():raise AssertionError(('Growing save failed',game.save_error))
                saved=deepcopy(game.saved_journey)
                saved_state=framework.canonical(framework.meaningful_state(game))
                expected_ledgers={key:deepcopy(game.town.data[key]) for key in
                                  (*PRIOR_LEDGERS,'settlement_growing')}
                entity_ids=[item['id'] for item in growing_entities(game.town.data)]

                def resume(name, payload):
                    if not game.save_store.write(payload):raise AssertionError('Disposable checkpoint write failed')
                    game.music.stop();restored=framework.Game(**options)
                    try:
                        restored.audio.set_music(0);restored.audio.set_effects(0)
                        if not restored.begin_journey(True):raise AssertionError(('Growing Continue failed',restored.save_error))
                        restored.opening_fade=restored.transfer_cooldown=0
                        ids=[item['id'] for item in growing_entities(restored.town.data)]
                        if ids!=entity_ids or len(ids)!=len(set(ids)):raise AssertionError('Continue lost/duplicated growing entities')
                        if any(restored.town.data[key]!=value for key,value in expected_ledgers.items()):
                            raise AssertionError('Continue changed an integrated district ledger')
                        if not restored.world.can_stand(restored.player.position):raise AssertionError('Continue restored blocked ground')
                        supports=restored.town.data['settlement_growing']['solid_footprints']
                        for support in supports:
                            sx,sy,sw,sh=support['rect']
                            if not all(restored.town.blocked.get_at((px,py))
                                       for py in range(sy,sy+sh) for px in range(sx,sx+sw)):
                                raise AssertionError(('Continue lost support',support['id']))
                        if framework.canonical(framework.meaningful_state(restored))!=saved_state:
                            raise AssertionError('Continue changed quest/party/inventory/flags')
                        if name=='continue_growing':
                            restored.draw();pygame.image.save(restored.window,str(folder/(name+'.png')))
                        return {'saved_position_fixture':payload['player']['position'],'restored_scene':restored.world.data['id'],
                                'position':list(restored.player.position),'clear_ground':True,'new_entity_ids':ids,
                                'flat_field_ids':[item['id'] for item in restored.town.data['settlement_growing']['ground_entities']],
                                'solid_supports_preserved':len(supports),'all_district_ledgers_unchanged':True,
                                'quest_party_inventory_flags_unchanged':True}
                    finally:restored.music.stop()
                report['save_continue']=resume('continue_growing',saved)
                report['save_continue']['start_fixture']=fixture
                recoveries=[]
                for support in expected_ledgers['settlement_growing']['solid_footprints']:
                    sx,sy,sw,sh=support['rect'];position=[sx+sw/2,sy+sh/2]
                    if game.town.can_stand(position):raise AssertionError(('Support checkpoint fixture is clear',support['id']))
                    if baseline is not None:
                        with Image.open(baseline/'collision.png') as raw:prior_collision=raw.convert('L')
                        px,py=(round(value) for value in position)
                        if prior_collision.crop((px-12,py-6,px+12,py+6)).getbbox():
                            raise AssertionError(('Older checkpoint fixture was not clear for baseline24x12probe',support['id'],position))
                    payload=deepcopy(saved);payload['player']['position']=position
                    result=resume(support['id'],payload)
                    if result['position']==position:raise AssertionError('Blocked checkpoint position did not recover')
                    recoveries.append({'support':support['id'],'baseline_24x12_collision_clear':True if baseline is not None else None,
                        'fixture':'Disposable older-checkpoint player coordinate inside new support; all progress fields unchanged.',**result})
                report['blocked_checkpoint_recoveries']=recoveries
            report['quest_party_inventory_flags_unchanged']=initial==framework.canonical(framework.meaningful_state(game))
            if not report['quest_party_inventory_flags_unchanged']:raise AssertionError('Growing review changed gameplay progress')
        finally:game.music.stop();pygame.quit()
    return report


def capture(folder, baseline=None, *, movement=True):
    folder.mkdir(parents=True,exist_ok=True)
    production=growing_snapshot()
    comparison=compare_baseline(baseline,folder) if baseline is not None else None
    framework.capture(folder)
    report=read(folder/'observations.json')
    report['scope']='Native production growing plot fixtures, exact source-alpha differences, input/doorway/Continue checks; no family quest playthrough.'
    report['baseline_comparison']=comparison
    if baseline is not None:report['native_view_comparison']=compare_view_scope(baseline,folder,report)
    report['gameplay']=gameplay_capture(folder,baseline=baseline,movement=movement)
    if growing_snapshot()!=production:raise AssertionError('Production or flat source artwork changed during growing capture')
    report['production_source_unchanged']=True
    report['flat_source_files']=production['flat_source_files']
    report['capture_png_sha256']={path.relative_to(folder).as_posix():framework.digest(path.read_bytes()) for path in sorted(folder.rglob('*.png'))}
    (folder/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"Growing review: {len(report['views'])} native views, {len(report['gameplay']['routes'])} movement checks; "
          f"baseline {'verified' if baseline is not None else 'not requested'}.")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',nargs='?',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--baseline-dir','--baseline',type=Path)
    parser.add_argument('--skip-movement',action='store_true',help='Only static views; omit movement/doorway/Continue checks')
    args=parser.parse_args()
    capture(args.output.resolve(),args.baseline_dir.resolve() if args.baseline_dir else None,movement=not args.skip_movement)
