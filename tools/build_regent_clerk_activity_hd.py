from pathlib import Path
import sys,json,hashlib
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];ID='regent_clerk';SRC=ROOT/'assets/source/story/royal_activity_hd'/ID;OUT=ROOT/'assets/story/royal_activity_hd'/ID;REVIEW=ROOT/'docs/reviews/royal_activity_hd'/ID
sys.path.insert(0,str(SRC));from author_activity import draw
POSES={'regent_clerk':{'read':6,'read_attention':6,'read_resume':6,'seated':1},'regent_driver':{'seated':1},'regent_survivor':{'alarm_front':1,'rest_front':1}}[ID]
def build():
 OUT.mkdir(parents=True,exist_ok=True);REVIEW.mkdir(parents=True,exist_ok=True);manifest={'id':ID,'canvas':[48,72],'logical_size':[24,36],'artwork_pixels_per_world_pixel':2,'draw_anchor':[24,60],'foot_anchor':[24,68],'poses':{},'status':'candidate_pending_independent_review','runtime_integration':False}
 for pose,count in POSES.items():
  frames=[];sheet=Image.new('RGBA',(48*count,72));entries=[]
  for i in range(count):
   im=draw(pose,i);file=f'{pose}_{i:02}.png';im.save(OUT/file);frames.append(im);sheet.alpha_composite(im,(i*48,0));entries.append(dict(file=file,duration_ms=([140,110,100,140,180,200][i] if pose=='read' else 100)))
  sheet.save(SRC/(pose+'_native_master.png'));bg=Image.new('RGBA',sheet.size,'#58615a');bg.alpha_composite(sheet);bg.save(REVIEW/(pose+'_native.png'));bg.resize((bg.width*4,bg.height*4),Image.Resampling.NEAREST).save(REVIEW/(pose+'_4x.png'))
  if count>1:
   for name,duration in [('normal',100),('slow',200)]:
    ff=[]
    for im in frames:
     g=Image.new('RGBA',(48,72),'#58615a');g.alpha_composite(im);ff.append(g.convert('RGB').resize((192,288),Image.Resampling.NEAREST))
    ff[0].save(REVIEW/f'{pose}_{name}.gif',save_all=True,append_images=ff[1:],duration=[f['duration_ms']*(2 if duration==200 else 1) for f in entries],loop=0,disposal=2)
  manifest['poses'][pose]={'frames':entries,'loop':False,'facing':'left' if pose.startswith('read') else 'back' if ID=='regent_driver' else 'front'}
 (OUT/'animation.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (SRC/'provenance.json').write_text(json.dumps({'id':ID,'inputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC.glob('*.py')},'construction':'Complete new body/legs/activity arms and prop drawings. Own same-task native base head retained explicitly, not legacy enlarged pixels. Existing scene pose source references retained for footprint/projection.', 'separate_from_base':True},indent=2)+'\n')
 print(ID,POSES)
if __name__=='__main__':build()
