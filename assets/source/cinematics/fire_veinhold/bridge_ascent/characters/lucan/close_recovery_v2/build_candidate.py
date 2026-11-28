"""Temporary exact-compositor gate for bounded complete-image source revisions."""
from pathlib import Path
from hashlib import sha256
import sys,json,copy
import numpy as np
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent;S=HERE.parent;ROOT=S.parents[6];sys.path[:0]=[str(S),str(ROOT)]
import register_banks as banks
from register_close_recovery import export_rows,head_target
from register_cycle_repairs import apply as apply_far
from cinematic_bridge_ascent import actor_states_at,camera_signature
from tools.build_prologue_bridge_ascent import FigureCompositor,_figure_record


def main():
    production=ROOT/'assets/story/fire_veinhold_opening/shot08/characters/lucan/actorperformance.json';raw=production.read_bytes();data=json.loads(raw)
    output=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/lucan_close_v2_candidate');output.mkdir(exist_ok=True);banks.OUT=output
    observations=json.loads((HERE/'rigid_observations.json').read_text())
    rows=[dict(row,source=master['source'],uniform_scale=master['uniform_scale']) for master in observations['masters'] for row in master['rows']]
    
    if '--exposure' in sys.argv:
        by_index={row['index']:row for row in rows}
        for dest,source in ((36,37),(40,41),(44,45)):
            replacement=copy.deepcopy(by_index[source]);replacement.update(index=dest,source_pose_index=source)
            rows=[replacement if row['index']==dest else row for row in rows]
    repairs=export_rows(rows,output);replaced={r['index'] for r in repairs}
    current=json.loads((S/'bank_registration.json').read_text());records=[]
    for record in current:
        if record['kind']=='transition' and record['index'] in replaced:continue
        row=copy.deepcopy(record)
        if row['kind']=='transition' and 48<=row['index']<108:
            target=head_target(row['index']);old=row['guide_head_centre'];row['origin']=[row['origin'][a]+target[a]-old[a] for a in(0,1)];row['guide_head_centre']=target
            row['canonical_head_registration_note']='Adult cranium center calibrated from approved source35; same physical body convention as new36–47.'
            path=output/f"transition_{row['index']:03d}.png";banks.export(row).save(path);row['output_sha256']=sha256(path.read_bytes()).hexdigest()
        records.append(row)
    records+=repairs;far=apply_far();records=[r for r in records if r['kind']!='overhead' or r['index'] not in{q['index'] for q in far}]+far
    (output/'candidate_registration.json').write_text(json.dumps(records,indent=2)+'\n')
    for key,rows in [('transition_frames',data['transition_frames']),('overhead_cycle',data['overhead_cycle']['frames'])]:
        for row in rows:
            if key=='transition_frames' and '--exposure' in sys.argv and row['index'] in (36,40,44):row['source_pose_gait_frame']=row['index']+1;row['exposure']='Adjacent complete drawn recovery pose held for two samples'
            original=(production.parent/row['file']).resolve();candidate=output/original.name
            row['file']=str(candidate if candidate.exists() else original)
    data['source_sha256']={r['file']:sha256(Path(r['file']).read_bytes()).hexdigest() for r in data['transition_frames']+data['overhead_cycle']['frames']}
    profile=output/'actorperformance.json';profile.write_text(json.dumps(data,indent=2)+'\n');compositor=FigureCompositor();bindings=[]
    for index in range(181):
        state=actor_states_at(index/60);actor=state['runners'][0];row=data['transition_frames'][index] if index<133 else data['overhead_cycle']['frames'][actor['frame_index']];record={'id':'lucan','path':Path(row['file']),'cell':row.get('cell'),'anchor':row.get('anchor',data['anchor']),'art_pixels_per_metre':row.get('art_pixels_per_metre',data['art_pixels_per_metre'])}
        picture=compositor.compose(Image.new('RGB',(960,640),'#203040'),np.full((640,960),np.inf),state,[record],shadows=False);path=output/f'native_{index:03d}.png';picture.save(path)
        bindings.append({'index':index,'state':state,'source':row['file'],'source_sha256':sha256(record['path'].read_bytes()).hexdigest(),'output_sha256':sha256(path.read_bytes()).hexdigest()})
    samples=[34,35,*range(36,54),54,55,56,57,58,59,60,61,67,68,107,108,132,133]
    sheet=Image.new('RGB',(1920,((len(samples)+3)//4)*340),'#203040');d=ImageDraw.Draw(sheet)
    for n,index in enumerate(samples):
        im=Image.open(output/f'native_{index:03d}.png');im.thumbnail((480,320));x,y=n%4*480,n//4*340;sheet.paste(im,(x,y));d.text((x+5,y+322),f'{index:03d}',fill='white')
    sheet.save(output/'contact.jpg',quality=95)
    for sample in [[35,36,37,38,39,40],[43,44,45,46,47,48],[48,49,50,51,52,53],[54,55,56,57,58,59,60,61]]:
        strip=Image.new('RGB',(400*len(sample),640),'#203040');draw=ImageDraw.Draw(strip)
        for n,index in enumerate(sample):
            im=Image.open(output/f'native_{index:03d}.png');strip.paste(im.crop((280,0,680,640)),(n*400,0));draw.text((n*400+5,5),str(index),fill='white')
        strip.save(output/f'boundary_{sample[0]:03d}_{sample[-1]:03d}.jpg',quality=97)
    (output/'binding.json').write_text(json.dumps({'production_profile_sha256':sha256(raw).hexdigest(),'candidate_profile_sha256':sha256(profile.read_bytes()).hexdigest(),'registration_sha256':sha256((output/'candidate_registration.json').read_bytes()).hexdigest(),'rigid_observations_sha256':sha256((HERE/'rigid_observations.json').read_bytes()).hexdigest(),'camera_signature':camera_signature(),'renderer':'FigureCompositor.compose(shadows=False)','records':bindings},indent=2)+'\n')
    assert production.read_bytes()==raw
    print(json.dumps({'output':str(output),'binding_sha256':sha256((output/'binding.json').read_bytes()).hexdigest()}))
if __name__=='__main__':main()
