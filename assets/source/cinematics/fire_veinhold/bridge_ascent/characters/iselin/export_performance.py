"""Export complete ImageGen Iselin drawings by whole-image registration only.

Run with the repository Python. --check reconstructs every new PNG in memory,
checks the unchanged raw sources and their exact authoring inputs, and compares
the complete portable production profile. No mannequin pixels are exported.
"""
from pathlib import Path
from hashlib import sha256
from statistics import median
from io import BytesIO
import argparse,json,math,os,sys
from PIL import Image

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[6]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from cinematic_bridge_ascent import actor_states_at
OUTPUT=ROOT/'assets/story/fire_veinhold_opening/shot08/characters/iselin'
HIGH_NAMES=['transition_056_071_linked_view_bridge','transition_072_087_linked_occlusion_alpha',
            'transition_088_103_matched_phase','transition_104_119_matched_phase']
CYCLE_NAMES=['overhead_000_015_validated_chain','overhead_016_031_pose_retry','overhead_032_047_pose_retry']
CANVAS=(1024,1536)
ANCHOR=[512,960]
SOURCE_STATE='source_revision_prepared'
REVIEW_RECORD='docs/reviews/veinhold_bridge_ascent/README.md'


def digest(path):return sha256(path.read_bytes()).hexdigest()


def verify_master(folder):
    data=json.loads((folder/'generation.json').read_text())
    if digest(folder/'master.png')!=data['sha256']:
        raise ValueError(f'Changed raw ImageGen master: {folder.name}')
    if digest(folder/data['prompt'])!=data['prompt_sha256']:
        raise ValueError(f'Changed exact ImageGen prompt: {folder.name}')
    for ref in data['references']:
        reference=(ROOT if ref['path'].startswith('assets/') else BASE)/ref['path']
        if digest(reference)!=ref['sha256']:
            raise ValueError(f'Changed ImageGen reference: {ref["path"]}')
    return data


def registered_png(master,cell,scale,origin):
    figure=master.crop(tuple(cell)).convert('RGBA')
    figure.putalpha(figure.getchannel('A').point(lambda a:0 if a<=16 else a))
    size=tuple(max(1,round(v*scale)) for v in figure.size)
    figure=figure.convert('RGBa').resize(size,Image.Resampling.LANCZOS).convert('RGBA')
    canvas=Image.new('RGBA',CANVAS)
    canvas.alpha_composite(figure,tuple(round(v) for v in origin))
    stream=BytesIO();canvas.save(stream,format='PNG')
    return stream.getvalue()


def export(check=False,cycle_from=120):
    OUTPUT.mkdir(parents=True,exist_ok=True)
    profile={'version':1,'actor':'iselin','canvas':list(CANVAS),'anchor':ANCHOR,
             'art_pixels_per_metre':500,'cycle_seconds':.8,
             'approval_state':SOURCE_STATE,
             'registration':'Whole drawings only: crop, one uniform master density, translation, alpha floor16. No occupied-height fit, limb transforms, RGB repaint or pose blends.',
             'source_sha256':{},'transition_frames':[],
             'overhead_cycle':{'frames':[]}}
    if SOURCE_STATE=='source_revision_prepared':
        profile['source_review_record']=REVIEW_RECORD
    registrations=[];pending_pngs={}
    def record_file(record,content=None):
        path=(OUTPUT/record['file']).resolve()
        if content is None:
            actual=digest(path)
        else:
            # A later bounded selection may replace an earlier trial at the
            # same chronology index. Validate/materialize the FINAL bytes,
            # not an intermediate unselected drawing.
            pending_pngs[record['file']]=content
            actual=sha256(content).hexdigest()
        profile['source_sha256'][record['file']]=actual
        return record
    for index in range(20):
        state=next(a for a in actor_states_at(index/60)['runners'] if a['id']=='iselin')
        path=ROOT/f'assets/story/fire_veinhold_opening/shot07/characters/iselin/frame_{state["frame_index"]:02d}.png'
        record={'index':index,'file':os.path.relpath(path,OUTPUT),
                'canvas':[1024,1024],'anchor':[512,960],
                'art_pixels_per_metre':500,'gait_frame':state['frame_index'],
                'drawing':'unchanged approved front phase; small-angle entry reuse',
                'actual_elevation_degrees':state['view_elevation_degrees']}
        profile['transition_frames'].append(record_file(record))
    close=json.loads((BASE/'candidate_close_registration.json').read_text())['frames']
    if [r['index'] for r in close]!=list(range(20,56)):
        raise ValueError('Missing consecutive newly drawn close poses20–55')
    source_cache={}
    for source in close:
        raw=BASE/source['source'];folder=raw.parent
        if folder not in source_cache:
            source_cache[folder]=(verify_master(folder),Image.open(raw).convert('RGBA'))
        generation,master=source_cache[folder]
        if source['source_sha256']!=generation['sha256']:
            raise ValueError('Close drawing/source registration SHA mismatch')
        record={'index':source['index'],'file':f'transition/frame_{source["index"]:03d}.png',
                'gait_frame':source['gait_frame'],'actual_elevation_degrees':source['actual_elevation'],
                'drawing':'complete camera-specific ImageGen figure'}
        profile['transition_frames'].append(record_file(record,registered_png(master,source['cell'],source['scale'],source['origin'])))
        registrations.append({'kind':'transition',**{k:v for k,v in source.items() if k not in ('file','approval_state')}})
    for name in HIGH_NAMES:
        folder=BASE/'batches'/name;generation=verify_master(folder)
        master=Image.open(folder/'master.png').convert('RGBA')
        measured=json.loads((folder/'crown_template_observations.json').read_text())
        if measured['source_sha256']!=generation['sha256']:
            raise ValueError(f'Crown observation/master mismatch: {name}')
        rows=measured['observations']
        # Accepted overhead model's253px observed cranium region represents
        #130artpx at500px/m, consistent with the accepted adult close model.
        # Base density per master; measured framing overrides are recorded
        # separately. Never use occupied bounds or exposed face area here.
        density=(130/253)/median(r['template_scale'] for r in rows if r['use_for_density'])
        is_cycle=name.startswith('overhead_')
        for source in rows:
            index=source['sample_index'];phase=source['gait_frame']
            drawing_density=density
            if name=='transition_056_071_linked_view_bridge':
                calibration=measured['density_calibration']
                first,last=calibration['first'],calibration['last']
                amount=(index-first['index'])/(last['index']-first['index'])
                observed_framing=(first['motif_width_source_pixels']+
                    amount*(last['motif_width_source_pixels']-first['motif_width_source_pixels']))
                drawing_density=calibration['target_art_motif_width']/observed_framing
            elevation=90.0 if is_cycle else source['view_elevation']
            angle=math.radians(elevation)
            # Camera-plane white-crown feature calibration. Head/shoulder
            # width stays stable while the projected footprint shortens;
            # the ground/root anchor is internal, not occupied-bounds fitted.
            # The observed WHITE CROWN feature lies above the facial/neck
            # feature used by the frontal atlas. Its projection calibration
            # preserves the accepted55→56 feature join. This is a source
            # registration feature, not a claim that the adult skull is2.2m
            # tall. At overhead, feature height vanishes from projection.
            target=[512.0,960+500*(.22*math.sin(angle)-2.2*math.cos(angle))]
            origin=[target[j]-source['point'][j]*drawing_density for j in (0,1)]
            filename=(f'overhead/frame_{phase:02d}.png' if is_cycle else f'transition/frame_{index:03d}.png')
            record={'file':filename,'gait_frame':phase,
                    'authored_elevation_degrees':elevation,
                    'drawing':'complete ImageGen overhead figure' if is_cycle else 'complete camera-specific ImageGen figure'}
            if not is_cycle:record['index']=index
            rendered=registered_png(master,source['actual_cell'],drawing_density,origin)
            record_file(record,rendered)
            destination=profile['overhead_cycle']['frames'] if is_cycle else profile['transition_frames']
            destination.append(record)
            registrations.append({'index':index,'kind':'overhead' if is_cycle else 'transition',
                'source':str((folder/'master.png').relative_to(BASE)),
                'source_sha256':generation['sha256'],'generation_id':generation['generation_id'],
                'cell':source['actual_cell'],'crown_source':source['point'],
                'crown_observation':source,'density_scale':drawing_density,'origin':origin,
                'density_calibration':measured.get('density_calibration'),
                'target_crown':target,'canvas':list(CANVAS),'anchor':ANCHOR,
                'art_pixels_per_metre':500,'occupied_height_used':False})
    # Bounded full-figure material/gait bridges replace only the two failed
    # regime joins. Their visible beaded motif calibrates whole-image density;
    # the crown correlation is used for position, never its pattern-box width.
    for name in ('transition_072_079_material_bridge_legs','transition_080_087_material_bridge',
                 'transition_088_095_material_bridge_legs','transition_096_103_material_bridge'):
        folder=BASE/'batches'/name;generation=verify_master(folder)
        measured=json.loads((folder/'crown_template_observations.json').read_text())
        if measured['source_sha256']!=generation['sha256']:raise ValueError('Material bridge/source SHA mismatch')
        master=Image.open(folder/'master.png').convert('RGBA')
        density=measured['density_calibration']['uniform_scale']
        for row in measured['observations']:
            index=row['sample_index'];angle=math.radians(row['view_elevation'])
            target=[512.0,960+500*(.22*math.sin(angle)-2.2*math.cos(angle))]
            origin=[target[j]-row['point'][j]*density for j in (0,1)]
            record={'index':index,'file':f'transition/frame_{index:03d}.png',
                    'gait_frame':row['gait_frame'],'authored_elevation_degrees':row['view_elevation'],
                    'drawing':'complete ImageGen material/view bridge with linked folded-leg correction'}
            record_file(record,registered_png(master,row['actual_cell'],density,origin))
            profile['transition_frames']=[r for r in profile['transition_frames'] if r['index']!=index]
            profile['transition_frames'].append(record)
            registrations=[r for r in registrations if not (r.get('kind')=='transition' and r['index']==index)]
            registrations.append({'index':index,'kind':'transition',
                'source':(folder/'master.png').relative_to(BASE).as_posix(),
                'source_sha256':generation['sha256'],'generation_id':generation['generation_id'],
                'cell':row['actual_cell'],'crown_source':row['point'],
                'crown_observation':row,'density_calibration':measured['density_calibration'],
                'density_scale':density,'origin':origin,'target_crown':target,
                'canvas':list(CANVAS),'anchor':ANCHOR,'art_pixels_per_metre':500,'occupied_height_used':False})
    for name in CYCLE_NAMES:
        folder=BASE/'batches'/name
        observed=json.loads((folder/'crown_selection_observations.json').read_text())['observations']
        groups={}
        for row in observed:groups.setdefault(row['source'],[]).append(row)
        for relative,rows in groups.items():
            source_path=folder/relative;generation=verify_master(source_path.parent)
            if any(row['source_sha256']!=digest(source_path) for row in rows):
                raise ValueError('Selected cycle drawing/master SHA mismatch')
            master=Image.open(source_path).convert('RGBA')
            density=(130/253)/median(row['template_scale'] for row in rows if row['use_for_density'])
            for row in rows:
                phase=row['phase'];point=row['point'];target=[512.0,1070.0]
                origin=[target[j]-point[j]*density for j in (0,1)]
                record={'file':f'overhead/frame_{phase:02d}.png','gait_frame':phase,
                        'authored_elevation_degrees':90.0,
                        'drawing':'complete ImageGen overhead figure, validated knee/boot-chain construction'}
                record_file(record,registered_png(master,row['actual_cell'],density,origin))
                profile['overhead_cycle']['frames'].append(record)
                registrations.append({'index':phase,'kind':'overhead',
                    'source':source_path.relative_to(BASE).as_posix(),
                    'source_sha256':generation['sha256'],'generation_id':generation['generation_id'],
                    'cell':row['actual_cell'],'crown_source':point,'crown_observation':row,
                    'density_scale':density,'origin':origin,'target_crown':target,
                    'canvas':list(CANVAS),'anchor':ANCHOR,'art_pixels_per_metre':500,
                    'occupied_height_used':False})
    # A complete view-correct passing drawing replaces the two tiny late
    # exposures whose sixteen-cell trial had interpreted the knee as a shin.
    # The simulation phase keeps advancing; source32 is exposed for two ticks.
    folder=BASE/'batches/transition_118_passing';generation=verify_master(folder)
    measured=json.loads((folder/'registration.json').read_text())
    if measured['source_sha256']!=generation['sha256']:
        raise ValueError('Passing drawing/source measurement SHA mismatch')
    master=Image.open(folder/'master.png').convert('RGBA')
    registrations=[r for r in registrations if not (r.get('kind')=='transition' and r['index'] in (118,119))]
    for index in (118,119):
        state=next(a for a in actor_states_at(index/60)['runners'] if a['id']=='iselin')
        angle=math.radians(state['view_elevation_degrees'])
        target=[512.0,960+500*(.22*math.sin(angle)-2.2*math.cos(angle))]
        density=measured['density_scale'];origin=[target[j]-measured['point'][j]*density for j in (0,1)]
        # Separate uniformly registered exposures retain the actual root/camera
        # motion even though the complete authored body pose is held2ticks.
        record={'index':index,'file':f'transition/frame_{index:03d}.png',
                'gait_frame':32,'target_gait_frame':state['frame_index'],
                'authored_elevation_degrees':87.35,
                'actual_elevation_degrees':state['view_elevation_degrees'],
                'source_exposure':'one complete phase32 drawing exposed118–119; exact target gait/contact clock continues',
                'drawing':'complete ImageGen high-view folded passing figure'}
        record_file(record,registered_png(master,measured['cell'],density,origin))
        profile['transition_frames']=[r for r in profile['transition_frames'] if r['index']!=index]
        profile['transition_frames'].append(record)
        registrations.append({'index':index,'kind':'transition',
            'source':(folder/'master.png').relative_to(BASE).as_posix(),
            'source_sha256':generation['sha256'],'generation_id':generation['generation_id'],
            'cell':measured['cell'],'crown_source':measured['point'],
            'density_scale':density,'origin':origin,'target_crown':target,
            'canvas':list(CANVAS),'anchor':ANCHOR,'art_pixels_per_metre':500,
            'gait_frame':32,'target_gait_frame':state['frame_index'],'occupied_height_used':False})
    profile['overhead_cycle']['frames'].sort(key=lambda r:r['gait_frame'])
    cycle=profile['overhead_cycle']['frames']
    if [r['gait_frame'] for r in cycle]!=list(range(48)):
        raise ValueError('Incomplete48-drawing overhead cycle')
    if cycle_from<120:
        profile['transition_frames']=[r for r in profile['transition_frames'] if r['index']<cycle_from]
    for index in range(cycle_from,133):
        state=next(a for a in actor_states_at(index/60)['runners'] if a['id']=='iselin')
        profile['transition_frames'].append({**cycle[state['frame_index']],'index':index,
            'actual_elevation_degrees':state['view_elevation_degrees'],
            'drawing':'phase-matched new overhead cycle at tiny native size'})
    profile['transition_frames'].sort(key=lambda r:r['index'])
    if [r['index'] for r in profile['transition_frames']]!=list(range(133)):
        raise ValueError('Incomplete transition')
    encoded=json.dumps(profile,indent=2)+'\n';path=OUTPUT/'actorperformance.json'
    receipt_state=('source_revision_prepared' if SOURCE_STATE=='source_revision_prepared'
                   else 'candidate pending composed review')
    receipt=json.dumps({'version':1,'status':receipt_state,'frames':registrations},indent=2)+'\n'
    for relative,content in sorted(pending_pngs.items()):
        output=OUTPUT/relative
        if check:
            if not output.exists() or output.read_bytes()!=content:
                raise ValueError(f'Export differs: {relative}')
        else:
            output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(content)
    if check:
        if path.read_text()!=encoded:raise ValueError('Performance manifest differs')
        if (BASE/'export_registration.json').read_text()!=receipt:raise ValueError('Registration receipt differs')
    else:
        path.write_text(encoded)
        (BASE/'export_registration.json').write_text(receipt)
    print(('Checked' if check else 'Exported'),len(profile['transition_frames']),
          'transition records +',len(cycle),'complete overhead drawings;',len(profile['source_sha256']),'declared PNGs')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');parser.add_argument('--cycle-from',type=int,choices=(104,120),default=120)
    args=parser.parse_args();export(args.check,args.cycle_from)
