"""Archive complete ImageGen masters and record reviewed replacements unchanged."""
from pathlib import Path
from hashlib import sha256
import json
import shutil
import sys
P=Path(__file__).resolve().parent

def main(request):
    rows=json.loads(Path(request).read_text())
    manifest=P/'repair_generation_records_outliers.json'
    chosen=json.loads(manifest.read_text()) if manifest.exists() else {}
    previous=json.loads((P/'generation_records.json').read_text())
    for row in rows:
      key=str(row['frame'])
      if not Path(row['source']).is_file() or key not in previous:raise ValueError('Missing reviewed master or frame record')
    for row in rows:
      key=str(row['frame']);n=int(key);old=chosen.get(key,previous[key])
      target=P/f'repairs/frame_{n:02d}.png';prompt=target.with_suffix('.txt')
      prior=Path('/workspace/generated_images')/(old['generation_id']+'.png')
      if not prior.is_file():prior=target
      history=P/f'repairs/history/frame_{n:02d}_{sha256(prior.read_bytes()).hexdigest()[:12]}.png'
      history.parent.mkdir(exist_ok=True);shutil.copy2(prior,history)
      if prompt.exists() and not history.with_suffix('.txt').exists():shutil.copy2(prompt,history.with_suffix('.txt'))
      shutil.copy2(row['source'],target);prompt.write_text(row['prompt'])
      chosen[key]={'generation_id':Path(row['source']).stem,'source_master':target.relative_to(P).as_posix(),
                   'prompt_file':prompt.relative_to(P).as_posix(),'history':[{**old,'archived_master':history.relative_to(P).as_posix()}]}
    manifest.write_text(json.dumps(chosen,indent=2)+'\n')
    print('Recorded',len(rows),'complete reviewed source replacements')
if __name__=='__main__':main(sys.argv[1])
