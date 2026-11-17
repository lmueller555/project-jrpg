#!/usr/bin/env python3
"""Stage regional-density exports from retained drawings; never activate maps."""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import colorsys
from io import BytesIO
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_overworld_art as base
import build_overworld_polish_art as polish
import build_overworld_composition_art as composition
OUT = ROOT / 'assets/terrain/overworld/elden_vale/hd'
SOURCE = ROOT / 'assets/source/terrain/overworld/elden_vale/hd'
REVIEW = ROOT / 'docs/reviews/elden_vale_hd_foundation'

def encoded(image):
    buffer = BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()

def json_bytes(data):
    return (json.dumps(data, indent=2) + '\n').encode()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build(check=False):
    products, images, inventory, dependencies = {}, {}, [], {}
    def depend(path):
        dependencies[path.relative_to(ROOT).as_posix()] = digest(path)
    def emit(path, image):
        if not image.getbbox():
            raise ValueError(f'Empty export: {path}')
        if set(image.getchannel('A').tobytes()) - {0,255}:
            raise ValueError(f'Soft alpha: {path}')
        products[path] = encoded(image)
    depend(Path(__file__))
    manifest = {'id':'elden_vale.hd.foundation', 'artwork_pixels_per_world_pixel':2,
                'integration_status':'not_integrated', 'visual_approval':'not_reviewed_by_user',
                'path_space':'repository_relative', 'anchor_space':'logical',
                'tiles':{}, 'props':{}, 'vegetation':[], 'reuse':{}}
    # Resolve runtime overrides first; excluded IDs are actors/effects with their own owners.
    selected = {}
    for module in (base, polish, composition):
        recipe = json.loads((module.SOURCE/'recipe.json').read_text())
        depend(module.SOURCE/'recipe.json')
        depend(Path(module.__file__))
        for record in recipe['source_records']:
            path=ROOT/record['file']
            if digest(path)!=record['sha256']:
                raise ValueError(f'Altered source: {path}')
            depend(path)
        for kind in ('tiles','props'):
            for key,spec in recipe.get(kind,{}).items():
                selected[kind,key]=(module,recipe,spec)
    excluded={'guard_front','guard_back','bird_1','bird_2','butterfly_1','butterfly_2',
              'sheep_1','sheep_2','smoke_1','smoke_2','broken_bridge'}
    for (kind,key),(module,recipe,original) in selected.items():
        if key in excluded: continue
        spec=deepcopy(original)
        spec['size']=[n*2 for n in spec['size']]
        if module is composition:
            if 'uniform_resize' in spec:
                spec['uniform_resize']=[n*2 for n in spec['uniform_resize']]
                for item in spec.get('components',[]):
                    item['crop']=[n*2 for n in item['crop']]
                    item['position']=[n*2 for n in item['position']]
            image=module.export(spec,recipe)
        elif module is polish:
            image=module.native_image(spec,recipe,prop=kind=='props')
        else:
            image=module.export_image(spec,recipe,prop=kind=='props')
        # One-artwork-pixel external contour, preserving original color pixels.
        if kind=='props':
            alpha=image.getchannel('A')
            outlined=Image.new('RGBA',image.size,(0,0,0,0))
            outlined.putalpha(alpha.filter(ImageFilter.MaxFilter(3)))
            outlined.alpha_composite(image)
            image=outlined
        if key in ('grass','grass_lush','grass_meadow','pasture','orchard_grass','forest_floor','leaf_litter') or kind=='props':
            pixels=[]
            for r,g,b,a in zip(*[iter(image.tobytes())]*4):
                if g > r and g > b*1.12:
                    h,saturation,value=colorsys.rgb_to_hsv(r/255,g/255,b/255)
                    r,g,b=[round(c*255) for c in colorsys.hsv_to_rgb((h+146/360)/2,max(saturation,.32),value)]
                pixels.append((r,g,b,a))
            image.putdata(pixels)
        if key=='broken_bridge_wide':
            gap=original['central_gap_x_px']
            image.paste((0,0,0,0),(gap[0]*2,0,gap[1]*2,image.height))
        if key=='eldenmere':
            business_path=ROOT/'assets/terrain/eldenmere/business_exteriors_hd/manifest.json'
            depend(business_path)
            businesses=json.loads(business_path.read_text())['buildings']
            for business_id,position in [('inn_maintained',(98,184)),('item_shop_maintained',(148,184))]:
                building=next(item for item in businesses if item['id']==business_id)
                donor=business_path.parent/building['closed'];depend(donor)
                icon=Image.open(donor).convert('RGBA')
                ratio=min(42/icon.width,50/icon.height)
                icon=icon.resize((round(icon.width*ratio),round(icon.height*ratio)),Image.Resampling.NEAREST)
                image.alpha_composite(icon,position)
        path=OUT/kind/f'{key}.png'
        emit(path,image)
        logical=original['size']
        entry={'image':path.relative_to(ROOT).as_posix(),'logical_size':logical,
               'artwork_pixels_per_world_pixel':2,'source_recipe':str((module.SOURCE/'recipe.json').relative_to(ROOT)),
               'collision':'unregistered; preserve consumer geometry independently'}
        if kind=='props':
            entry['foot_anchor']=original['foot_anchor']
            entry['depth_baseline_logical']=original['foot_anchor'][1]
        if key=='broken_bridge_wide':
            entry.update({k:v for k,v in original.items() if k.startswith('deck_') or k=='central_gap_x_px'})
            entry['geometry_space']='logical; artwork values are twice these measurements'
        manifest[kind][key]=entry
        images[key]=image
        inventory.append({'id':key,'kind':kind,'legacy_image':str((module.OUTPUT/kind/(key+'.png')).relative_to(ROOT)),
                          'logical_size':logical,'method':'retained_master_export','entry':entry})
    # Authored material interiors supply coherent alternates; crop-row orientations
    # are independent flat ground exports, never rotations of elevated structures.
    manifest['material_variants']={}
    for key in ('grain','vegetables','furrows','leaf_litter','gravel','cart_earth','scorched'):
        module,recipe,original=selected['tiles',key]
        variants=[]
        with Image.open(module.SOURCE/original['source']) as master:
            crop=master.convert('RGBA').crop(original['crop'])
        for index in range(3):
            margin=index*max(1,crop.width//12)
            image=crop.crop((margin,margin,crop.width-margin,crop.height-margin)).resize((48,48),Image.Resampling.NEAREST)
            image=base.binary_alpha(base.palette_reduce(image,32),128)
            path=OUT/'materials'/f'{key}_{index}.png';emit(path,image)
            variants.append({'image':str(path.relative_to(ROOT)),'logical_size':[24,24],
                             'usage':'coherent patches; regional painter must blend contacts'})
        manifest['material_variants'][key]=variants
        if key in ('grain','vegetables','furrows'):
            for direction,angle in [('east_west',0),('north_south',90)]:
                image=images[key].rotate(angle)
                path=OUT/'materials'/f'{key}_{direction}.png';emit(path,image)
                manifest['material_variants'][key].append({'image':str(path.relative_to(ROOT)),
                    'logical_size':[24,24],'row_orientation':direction})
    # Reuse material packs by explicit reference, not copies with lost connection metadata.
    for name,relative in {
        'grass_dirt':'assets/terrain/eldenmere/grass_dirt_hd/tileset.json',
        'paving':'assets/terrain/eldenmere/stone_paving_hd/tileset.json',
        'water':'assets/terrain/water_hd/tileset.json',
        'masonry':'assets/terrain/eldenmere/terraces_hd/tileset.json',
        'waterworks':'assets/terrain/eldenmere/waterworks_hd/tileset.json'}.items():
        depend(ROOT/relative)
        manifest['reuse'][name]={'manifest':relative,'preserve':'phase, mask, connection and animation metadata',
                                 'activation':'staged regional consumer only'}
    plant_path=ROOT/'assets/terrain/vegetation_hd/plants.json'
    depend(plant_path)
    plants=json.loads(plant_path.read_text())
    for plant in plants['plants']:
        factor=.5 if plant['family'] in ('broadleaf','woodland','orchard','conifer') else 1
        size=[round(n*factor) for n in plant['logical_size']]
        entry={k:deepcopy(plant[k]) for k in ('id','family','variant','animated','allowed_surfaces')}
        entry.update(logical_size=size,artwork_size=[n*2 for n in size],artwork_pixels_per_world_pixel=2,
                     draw_anchor_logical=[n*factor for n in plant['draw_anchor_logical']],
                     ground_rect_logical=[n*factor for n in plant['ground_rect_logical']],
                     depth_baseline_logical=plant['depth_baseline_logical']*factor,
                     collision='not_registered',interaction_cues=False,frames=[],
                     source_manifest=str(plant_path.relative_to(ROOT)),
                     reduced_motion='idle; no contacts or progress',animation_kind=plant.get('animation_kind','static'))
        for frame in [{'file':plant['idle'],'duration_ms':0}]+plant['frames']:
            source=plant_path.parent/frame['file'];depend(source)
            image=Image.open(source).convert('RGBA').resize(tuple(entry['artwork_size']),Image.Resampling.NEAREST)
            path=OUT/'vegetation'/plant['id']/Path(frame['file']).name
            emit(path,image)
            if frame['duration_ms']==0:
                entry['idle']=str(path.relative_to(ROOT));images[plant['id']]=image
            else:entry['frames'].append({'file':str(path.relative_to(ROOT)),'duration_ms':frame['duration_ms']})
        for layer in ('fixed','backing'):
            if plant.get(layer):
                source=plant_path.parent/plant[layer];depend(source)
                image=Image.open(source).convert('RGBA').resize(tuple(entry['artwork_size']),Image.Resampling.NEAREST)
                path=OUT/'vegetation'/plant['id']/f'{layer}.png';emit(path,image)
                entry[layer]=str(path.relative_to(ROOT))
        manifest['vegetation'].append(entry)
    # Composition diagrams use only exported/referenced artwork. No gameplay capture claim.
    board=Image.new('RGBA',(1536,((len(images)+7)//8)*190),'#d7d9cb')
    draw=ImageDraw.Draw(board)
    for i,(key,image) in enumerate(images.items()):
        x,y=i%8*192,i//8*190
        factor=min(1,180/image.width,145/image.height)
        shown=image.resize((round(image.width*factor),round(image.height*factor)),Image.Resampling.NEAREST)
        board.alpha_composite(shown,(x+(192-shown.width)//2,y+150-shown.height))
        draw.text((x+4,y+157),key,fill='black')
    products[REVIEW/'asset_board.png']=encoded(board)
    grass=Image.open(ROOT/'assets/terrain/eldenmere/grass_dirt_hd/materials/lawn_00.png').convert('RGBA')
    scene=Image.new('RGBA',(960,640))
    for y in range(0,640,48):
        for x in range(0,960,48):scene.paste(grass,(x,y))
    depend(ROOT/'assets/terrain/eldenmere/grass_dirt_hd/materials/lawn_00.png')
    # Simple dirt approach framed by farm/woodland/shore donor examples.
    dirt=images['dirt']
    for y in range(0,640,48):
        for x in range(432,576,48):scene.paste(dirt,(x,y))
    for key,position in [('farm_house',(150,170)),('barn',(650,190)),('fence_h',(130,290)),
                         ('cart',(620,330)),('oak_a',(30,380)),('orchard_tree',(700,430)),('reeds',(30,130))]:
        scene.alpha_composite(images[key],position)
    for y in range(0,640,48):
        for x in range(816,960,48):scene.paste(images['water'],(x,y))
    actor_bank=ROOT/'assets/characters/caelan/animation.json';depend(actor_bank)
    actor=ROOT/json.loads(actor_bank.read_text())['idles']['front']['file']
    # Character reference resolved from the approved bank, never a substitute body.
    depend(actor)
    scene.alpha_composite(Image.open(actor).convert('RGBA'),(480,340))
    # Blend a connected bank strip over the water/grass meeting for shore review.
    water_manifest=ROOT/'assets/terrain/water_hd/tileset.json'
    water_bank=json.loads(water_manifest.read_text())
    shore=next(item for item in water_bank['bank_tiles'] if item['family']=='grass' and item['mask']==31 and item['arrangement']==0)
    bank_path=water_manifest.parent/shore['file'];depend(bank_path)
    bank=Image.open(bank_path).convert('RGBA')
    for y in range(0,640,48):scene.alpha_composite(bank,(816,y))
    ImageDraw.Draw(scene).text((16,16),'OFFLINE SCALE STUDY - regional canvases / 2x artwork; not gameplay',fill='white')
    products[REVIEW/'scale_scene.png']=encoded(scene)
    for title,keys in {
        'woodland':['broadleaf_full','woodland_paired','fern_curled','exposed_roots_twisted'],
        'riverbank':['tall_reeds_cattails','bank_flowers_white','boulder_mossy','fallen_log_weathered'],
        'bridge':['broken_bridge_wide','bridge_rubble','wall_segment_worn','scorched']}.items():
        study=Image.new('RGBA',(960,640))
        for y in range(0,640,48):
            for x in range(0,960,48):study.paste(grass,(x,y))
        if title in ('riverbank','bridge'):
            for y in range(0,640,48):
                for x in range(384,672,48):study.paste(images['water'],(x,y))
        if title=='woodland':
            floor=images['leaf_litter']
            for y in range(80,600,48):
                for x in list(range(0,336,48))+list(range(624,960,48)):
                    study.paste(floor,(x,y))
            for index,(x,y) in enumerate([(20,50),(145,95),(30,240),(190,290),(0,435),
                                           (650,50),(790,95),(680,250),(830,310),(750,440)]):
                study.alpha_composite(images[['broadleaf_full','broadleaf_spreading','woodland_paired'][index%3]],(x,y))
        if title=='riverbank':
            for mask,x in [(31,384),(241,624)]:
                record=next(item for item in water_bank['bank_tiles'] if item['family']=='grass' and item['mask']==mask and item['arrangement']==0)
                path=water_manifest.parent/record['file'];depend(path)
                edge=Image.open(path).convert('RGBA')
                for y in range(0,640,48):study.alpha_composite(edge,(x,y))
            for index,(x,y) in enumerate([(300,30),(315,210),(290,380),(690,90),(700,285),(705,450)]):
                study.alpha_composite(images[['tall_reeds_cattails','bank_flowers_white','rushes_splayed'][index%3]],(x,y))
        for index,key in enumerate(keys):
            image=images[key]
            position=(min(900-image.width,50+index*210),160+(index%2)*220)
            if title=='bridge':
                position={'broken_bridge_wide':(240,140),'bridge_rubble':(240,430),
                          'wall_segment_worn':(60,80),'scorched':(140,380)}[key]
            study.alpha_composite(image,position)
        study.alpha_composite(Image.open(actor).convert('RGBA'),(440,480))
        ImageDraw.Draw(study).text((16,16),'OFFLINE '+title.upper()+' / asset composition, not gameplay',fill='white')
        products[REVIEW/f'{title}_scene.png']=encoded(study)
    region=ROOT/'assets/maps/overworld/elden_vale/region.json';depend(region)
    layout=json.loads(region.read_text())
    plan={'status':'preliminary; no map edits or new collision',
          'coordinate_space':'existing logical tile coordinates',
          'protected':{k:layout[k] for k in ('roads','gates','town','bridge','landmarks','safe_clearings','clearance_paths')},
          'constraints':['Bases/skull only in already inaccessible northeastern ridge ground.',
                         'Overhead spans have no ground collision; protect all routes and story stations.',
                         'Reserve court, hall/relief doors, cave apron and NPC work stations retain clearance.',
                         'No crossing of boundary rivers, walls, gates or destroyed bridge.',
                         'PR2 must locate supports and sightlines against detailed scene geometry before final art.'],
          'views':['Eldenmere roof/tree gaps','woodland approach openings','Sanctuary forecourt','optional skull viewpoint'],
          'support_coordinates':'not finalized; require detailed scene clearance review'}
    products[SOURCE/'layout_blockout.json']=json_bytes(plan)
    diagram=Image.new('RGB',(1000,700),'#e1e4d4');d=ImageDraw.Draw(diagram)
    def project(p):return (int((p[0]+256)*1.75+40),int((p[1]+192)*1.55+30))
    for river in layout['terrain']['rivers']:
        d.line([project(p) for p in river['points']],fill='#497f92',width=14)
    for wall in layout['walls']:
        d.line([project([wall['x0'],wall['y']]),project([wall['x1'],wall['y']])],fill='#55534b',width=4)
    for landmark in [layout['town']]+layout['landmarks']+layout['gates']:
        if 'tile_position' in landmark:
            x,y=project(landmark['tile_position'])
            d.ellipse((x-4,y-4,x+4,y+4),fill='#993d39')
            d.text((x+6,y),landmark.get('name',landmark.get('id','station')),fill='black')
    for road in layout['roads']:
        if 'points' in road:d.line([project(p) for p in road['points']],fill='#a17a4b',width=5)
    d.rectangle((*project([70,-90]),*project([115,-70])),outline='#765b89',width=3)
    d.text(project([40,-120]),'Candidate ridge study: confirm ground contacts in PR2',fill='black')
    d.line([project([95,-80]),project([65,-55]),project([40,-45])],fill='#765b89',width=3)
    d.text(project([10,-35]),'Overhead envelope: no ground collision',fill='black')
    d.text((30,650),'PRELIMINARY PLAN / existing routes; spans illustrative; no committed support coordinates',fill='black')
    products[REVIEW/'antler_blockout.png']=encoded(diagram)
    products[SOURCE/'replacement_inventory.json']=json_bytes(inventory)
    products[SOURCE/'recipe.json']=json_bytes({'id':manifest['id'],'density':2,'method':'retained source crops plus regional HD vegetation exports',
        'sources':dependencies,'palette':'green-dominant source pixels mapped halfway toward emerald hue 146 degrees; existing earth/stone/wood retained; shared emerald grass donors',
        'geometry':'unchanged; staged only','excluded_actor_or_overridden_ids':sorted(excluded),
        'lighting':'retained upper-left source lighting','review':'docs/reviews/elden_vale_hd_foundation',
        'scope':'ordinary regional foundations; Sanctuary miniature and signatures in PR2; weather in PR3'})
    products[OUT/'art.json']=json_bytes(manifest)
    stale=[]
    for path,data in products.items():
        if check:
            if not path.exists() or path.read_bytes()!=data:stale.append(str(path.relative_to(ROOT)))
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    if stale:raise SystemExit('Stale outputs: '+', '.join(stale))
    print(f'{"Verified" if check else "Exported"} {len(products)} products; {len(inventory)} regional assets; {len(plants["plants"])} vegetation designs')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
