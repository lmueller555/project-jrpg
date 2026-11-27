"""Register complete authored candidates without changing the active profile."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,sys
from PIL import Image
P=Path(__file__).resolve().parent;A=P.parent
spec=importlib.util.spec_from_file_location('previous_registration',A/'run_v2/register_sources.py')
model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)

def export_frame(record):
    im=Image.open(A/record['source']).convert('RGBA').crop(tuple(record['cell']))
    im.putalpha(im.getchannel('A').point(lambda a:0 if a<=16 else a))
    im=im.convert('RGBa').resize(tuple(max(1,round(v*record['scale'])) for v in im.size),Image.Resampling.LANCZOS).convert('RGBA')
    out=Image.new('RGBA',(1024,1024));out.alpha_composite(im,tuple(round(v) for v in record['origin']));return out

def main():
    profile=json.loads((P/'baseline_source_art_48.json').read_text());candidate=json.loads((P/'candidate_records.json').read_text())
    report=[]
    observations_path=P/'manual_landmark_observations.json'
    observations=json.loads(observations_path.read_text())['observations'] if observations_path.exists() else {}
    for key,row in candidate.items():
      i=int(key);image=Image.open(A/row['source']).convert('RGBA')
      found={k:model.measure(image,k) for k in ('face','neck','belt')}
      observed=observations.get(row['source'])
      if observed:
          if sha256((A/row['source']).read_bytes()).hexdigest()!=observed['source_sha256']:
              raise ValueError('Reviewed landmark source changed: '+row['source'])
          for label,value in observed.items():
              if label!='source_sha256':
                  found[label]['point']=value['point']
                  found[label]['score']=None
      scale=1/found['face']['template_scale']
      baseline=profile['frames'][i];oldneck=baseline['landmarks']['neck'];target=[oldneck[j]*baseline['scale']+baseline['origin'][j] for j in (0,1)]
      origin=[target[j]-found['neck']['point'][j]*scale for j in (0,1)]
      rec={'source':row['source'],'cell':[0,0,*image.size],'scale':scale,'origin':origin,
           'landmarks':{k:v['point'] for k,v in found.items()},'landmark_match_scores':{k:v['score'] for k,v in found.items()},
           'generation_id':row['generation_id'], 'prompt_file':row['prompt_file'],
           'prompt_sha256':sha256((A/row['prompt_file']).read_bytes()).hexdigest(),
           'authored_weight_offset_y':baseline.get('authored_weight_offset_y',0),
           'phase':baseline.get('phase','run_inbetween'),
           'notes':'Complete image-authored continuity repair. Whole-frame uniform model density and measured neck registration only; no detached parts, warps, blends or duplicated endpoint.'}
      if row.get('selection_notes'):
          rec['notes'] += ' ' + row['selection_notes']
      if observed:
          rec['reviewed_landmarks']='run_v3/manual_landmark_observations.json'
      profile['frames'][i]=rec;profile['source_sha256'][row['source']]=sha256((A/row['source']).read_bytes()).hexdigest()
      report.append({'frame':i,'canonical_landmarks':{k:[round(v['point'][j]*scale+origin[j],3) for j in (0,1)] for k,v in found.items()},'scale':scale,'origin':origin,'scores':rec['landmark_match_scores']})
    out=Path('/tmp/iselin_v3_candidates');out.mkdir(exist_ok=True)
    for i,rec in enumerate(profile['frames']):export_frame(rec).save(out/f'frame_{i:02d}.png')
    (P/'candidate_source_art_48.json').write_text(json.dumps(profile,indent=2)+'\n')
    (P/'candidate_registration_measurements.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
