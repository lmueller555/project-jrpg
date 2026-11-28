"""Retain an unchanged ImageGen whole-sheet edit and exact ordered inputs."""
from pathlib import Path
from hashlib import sha256
from PIL import Image
import json,shutil,sys
base=Path(__file__).resolve().parent
name,generation_id=sys.argv[1:3];p=base/'batches'/name
original=Path('/workspace/generated_images')/(generation_id+'.png')
destination=p/'master.png'
if destination.exists() and destination.read_bytes()!=original.read_bytes():
    raise ValueError('Refuse to overwrite a different ImageGen master')
shutil.copyfile(original,destination)
reference_names=(json.loads((p/'edit_references.json').read_text())
                 if (p/'edit_references.json').exists() else ['edit_reference.png'])
data={'generation_id':generation_id,'original_generation_path':str(original),
      'master':'master.png','sha256':sha256(destination.read_bytes()).hexdigest(),
      'size':list(Image.open(destination).size),'prompt':'prompt.txt',
      'prompt_sha256':sha256((p/'prompt.txt').read_bytes()).hexdigest(),
      'references':[{'path':str((p/filename).relative_to(base)),
                     'sha256':sha256((p/filename).read_bytes()).hexdigest()}
                    for filename in reference_names],
      'status':('ImageGen complete-figure correction; native review pending'
                if len(reference_names)>1 else 'ImageGen whole-sheet transparency edit; native review pending'),
      'samples':[r['sample_index'] for r in json.loads((p/'reference_manifest.json').read_text())],
      'guide_pixels_used_in_export':False}
(p/'generation.json').write_text(json.dumps(data,indent=2)+'\n')
print(name,data['size'])
