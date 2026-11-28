"""Retain one unchanged ImageGen master and its exact authoring inputs."""
from pathlib import Path
from hashlib import sha256
from PIL import Image
import json,shutil,sys
base=Path(__file__).resolve().parent
name,generation_id=sys.argv[1:3];p=base/'batches'/name
original=Path('/workspace/generated_images')/(generation_id+'.png');dest=p/'master.png'
if dest.exists() and dest.read_bytes()!=original.read_bytes():raise ValueError('Refuse to overwrite existing generated master')
shutil.copyfile(original,dest)
refs=[p/'camera_pose_guide.png',p/'approved_phase_reference.png']
extra=p/'angle_model_reference.png'
if extra.exists():refs.append(extra)
record={'generation_id':generation_id,'original_generation_path':str(original),'master':'master.png','sha256':sha256(dest.read_bytes()).hexdigest(),'size':list(Image.open(dest).size),'prompt':'prompt.txt','prompt_sha256':sha256((p/'prompt.txt').read_bytes()).hexdigest(),'references':[{'path':str(x.relative_to(base)),'sha256':sha256(x.read_bytes()).hexdigest()} for x in refs],'status':'candidate_complete_drawings','samples':[r['sample_index'] for r in json.loads((p/'reference_manifest.json').read_text())],'guide_pixels_used_in_export':False}
(p/'generation.json').write_text(json.dumps(record,indent=2)+'\n');print(name,record['size'])
