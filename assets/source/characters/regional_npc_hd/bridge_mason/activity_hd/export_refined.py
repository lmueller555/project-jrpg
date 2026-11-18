from pathlib import Path
import json, hashlib
from PIL import Image
source=Path(__file__).resolve().parent
plan=json.loads((source/'native_pose_plan.json').read_text())
master=source/'authored.png'
assert hashlib.sha256(master.read_bytes()).hexdigest()==plan['authored_sha256']
im=Image.open(master)
for item in plan['frames']:
 x,y,w,h=item['source_cell'];p=source/'refined_masters'/Path(item['file']).name
 im.crop((x,y,x+w,y+h)).save(p,optimize=True)
print('Exported',len(plan['frames']),'native complete drawings')
