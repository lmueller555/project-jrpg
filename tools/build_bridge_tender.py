"""Export whole authored bridge-surveyor poses and directional cup gait.

Crops/registers complete generated figures. It never paints, rotates, stretches
or substitutes individual limbs. Shared male_03 work/rest frames are copied
byte-for-byte from the already-authored grain coworker assets.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/characters/bridge_workers/tender'
OUT=ROOT/'assets/characters/bridge_workers/tender'
COWORKER=ROOT/'assets/characters/grain_workers/coworker'
SIZE=(40,44);ANCHOR=(20,38)
ROWS={'cup_walk':[(0,313),(313,585),(585,858),(858,1155)],
      'actions':[(0,314),(314,597),(597,865),(865,1155)]}
DIRECTIONS=('front','back','left','right')


def digest(data):return hashlib.sha256(data).hexdigest()
def png(im):
 s=io.BytesIO();im.save(s,format='PNG',optimize=True);return s.getvalue()
def dump(data):return (json.dumps(data,indent=2)+'\n').encode()


def source_cell(source,row,col,key):
 x0=round(source.width*col/4);x1=round(source.width*(col+1)/4);y0,y1=ROWS[key][row]
 im=source.crop((x0,y0,x1,y1)).convert('RGBA')
 im.putalpha(im.getchannel('A').point(lambda v:255 if v>=128 else 0))
 return im


def register(im,scale,head_aligned=False):
 im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.NEAREST)
 box=im.getbbox()
 if box is None:raise ValueError('Empty authored bridge tender frame')
 soles=im.getchannel('A').crop((0,box[3]-2,im.width,box[3])).getbbox()
 foot_x=round((soles[0]+soles[2]-1)/2)
 if head_aligned:
  # A stride changes the pair of shoe bounds. Anchor gait to the head/torso
  # axis instead, so foot extension never drags the entire body sideways.
  head=im.getchannel('A').crop((0,box[1],im.width,min(box[3],box[1]+12))).getbbox()
  foot_x=round((head[0]+head[2]-1)/2)
 origin=(ANCHOR[0]-foot_x,ANCHOR[1]+1-box[3])
 if origin[0]+box[0]<0 or origin[0]+box[2]>40 or origin[1]+box[1]<0 or origin[1]+box[3]>44:
  raise ValueError('Authored bridge tender leaves canvas')
 result=Image.new('RGBA',SIZE);result.alpha_composite(im,origin);return result


def build_payload():
 sources={key:Image.open(SOURCE/(key+'_generated.png')).convert('RGBA') for key in ROWS}
 if any(im.size!=(1362,1155) for im in sources.values()):raise ValueError('Unexpected source dimensions')
 payload={};images={};sequences={};registrations={};reused=[]
 def clip(name,cells,loop,duration,metadata=None):
  crops=[source_cell(sources[key],row,col,key) for key,row,col in cells]
  # One scale for an entire clip preserves the authored knee/hip bending.
  scale=33/max(im.getbbox()[3]-im.getbbox()[1] for im in crops)
  frames=[]
  for i,im in enumerate(crops):
   frame=register(im,scale,head_aligned=name.startswith('cup_'));filename=f'{name}_{i}.png';payload[OUT/filename]=png(frame);images[(name,i)]=frame
   record={'file':filename,'duration_ms':duration}
   if metadata:record.update(metadata[i] if isinstance(metadata,list) else metadata)
   frames.append(record)
  sequences[name]={'loop':loop,'frames':frames};registrations[name]={'scale':scale,'cells':cells}
 def reuse(name,files,loop,duration):
  frames=[]
  for i,filename in enumerate(files):
   path=COWORKER/filename;data=path.read_bytes();out=f'{name}_{i}.png'
   payload[OUT/out]=data;images[(name,i)]=Image.open(io.BytesIO(data)).convert('RGBA')
   reused.append({'file':str(path.relative_to(ROOT)),'sha256':digest(data)})
   record={'file':out,'duration_ms':duration}
   if name=='measure_left':
    authored=json.loads((COWORKER/'animation.json').read_text())['sequences']['work_left']['frames'][i]
    record.update({'hands':authored['hands'],'tool_offset':[-8,-10],'gripped':True})
   frames.append(record)
  sequences[name]={'loop':loop,'frames':frames}
 for row,direction in enumerate(DIRECTIONS):
  offset={'front':[-5,-14],'back':[6,-14],'left':[-6,-13],'right':[6,-14]}[direction]
  metadata=[{'cup_offset':offset,'cup_layer':'back' if direction=='back' else 'front','hands':[offset],'gripped':True}
            for _ in range(4)]
  if direction=='left':metadata[2]={**metadata[2],'hands':[[-5,-13]]}
  clip('cup_'+direction,[('cup_walk',row,col) for col in range(4)],True,180,metadata)
 for direction,(row,col) in {'front':(0,0),'back':(0,1),'left':(2,0),'right':(1,0)}.items():
  offset={'front':[-5,-14],'back':[6,-14],'left':[-6,-13],'right':[6,-14]}[direction]
  clip('cup_hold_'+direction,[('actions',row,col)],False,1000,
       {'cup_offset':offset,'cup_layer':'back' if direction=='back' else 'front','hands':[offset],'gripped':True})
 # The close pickup poses grasp the existing waist-high cup. The generated
 # far-reaching alternatives are retained in the source but not exported.
 clip('pickup_right',[('actions',1,col) for col in [0,0,3,3]],False,250,
      [{'cup_offset':[8,-11],'hands':[[7,-14]],'gripped':False},
       {'cup_offset':[8,-11],'hands':[[7,-14]],'gripped':True},
       {'cup_offset':[7,-12],'hands':[[6,-14]],'gripped':True},
       {'cup_offset':[6,-14],'hands':[[6,-14]],'gripped':True}])
 # Actual palms at a fixed, registered stance. Runtime docks four pixels
 # nearer the tray and positions its support under the final cup contact.
 clip('offer_left',[('actions',2,col) for col in [0,1,1,3]],False,500,
      [{'cup_offset':[-6,-13],'hands':[[-6,-13]],'gripped':True},
       {'cup_offset':[-12,-16],'hands':[[-12,-16]],'gripped':False},
       {'cup_offset':[-12,-16],'hands':[[-12,-16]],'gripped':True},
       {'cup_offset':[-7,-13],'hands':[[-7,-13]],'gripped':False}])
 clip('receive_left',[('actions',2,col) for col in [0,1,1,0]],False,250,
      [{'cup_offset':[-12,-14],'hands':[[-6,-13]],'gripped':False},
       {'cup_offset':[-12,-14],'hands':[[-12,-16]],'gripped':True},
       {'cup_offset':[-12,-15],'hands':[[-12,-16]],'gripped':True},
       {'cup_offset':[-6,-13],'hands':[[-6,-13]],'gripped':True}])
 clip('measure_right',[('actions',3,col) for col in [1,2,1,1]],True,400,
      [{'tool_offset':[8,-12],'hands':[[10,-14],[3,-13]],'gripped':True},
       {'tool_offset':[8,-12],'hands':[[10,-13],[5,-11]],'gripped':True},
       {'tool_offset':[8,-12],'hands':[[10,-14],[3,-13]],'gripped':True},
       {'tool_offset':[8,-12],'hands':[[10,-14],[3,-13]],'gripped':True}])
 clip('work_right',[('actions',3,col) for col in [1,2,1,1]],True,360,
      [{'tool_offset':[8,-12],'hands':[[10,-14],[3,-13]],'gripped':True},
       {'tool_offset':[8,-12],'hands':[[10,-13],[5,-11]],'gripped':True},
       {'tool_offset':[8,-12],'hands':[[10,-14],[3,-13]],'gripped':True},
       {'tool_offset':[8,-12],'hands':[[10,-14],[3,-13]],'gripped':True}])
 reuse('measure_left',[f'work_left_{i}.png' for i in range(4)],True,360)
 reuse('stretch_front',[f'stretch_front_{i}.png' for i in range(4)],False,550)
 manifest={'version':1,'canvas':list(SIZE),'anchor':list(ANCHOR),'sequences':sequences}
 payload[OUT/'animation.json']=dump(manifest)
 source_names=['cup_walk_generated.png','actions_generated.png','identity_reference.png','cup_walk_prompt.txt','actions_prompt.txt']
 provenance={'version':1,'exporter':'tools/build_bridge_tender.py',
  'sources':[{'file':str((SOURCE/name).relative_to(ROOT)),'sha256':digest((SOURCE/name).read_bytes())} for name in source_names],
  'reused_authored_frames':reused,
  'reused_authored_manifest':{'file':str((COWORKER/'animation.json').relative_to(ROOT)),'sha256':digest((COWORKER/'animation.json').read_bytes())},
  'registration':{'canvas':list(SIZE),'anchor':list(ANCHOR),'clips':registrations},
  'exports':[{'file':str(p.relative_to(ROOT)),'sha256':digest(data)} for p,data in payload.items()],
  'notes':['All frames are whole authored figures; no procedural limb paint/warp.',
           'Only bridge tender states used by the actual tea/measurement routine are exported; no seated/drinking tender poses.',
           'External cup/tool remain separate controller-owned props; no duplicate baked props.']}
 payload[OUT/'provenance.json']=dump(provenance)
 rows=list(sequences);review=Image.new('RGBA',(640,len(rows)*190),'#29413b');d=ImageDraw.Draw(review)
 for row,key in enumerate(rows):
  for col in range(4):
   i=min(col,len(sequences[key]['frames'])-1)
   review.alpha_composite(images[(key,i)].resize((160,176),Image.Resampling.NEAREST),(col*160,row*190))
   d.text((col*160+3,row*190+177),f'{key} {i}',fill='#dcd8c6')
 payload[SOURCE/'native_review.png']=png(review)
 previews=[]
 for index in range(4):
  im=Image.new('RGBA',(len(rows)*80,100),'#29413b')
  for col,key in enumerate(rows):
   i=min(index,len(sequences[key]['frames'])-1)
   im.alpha_composite(images[(key,i)].resize((80,88),Image.Resampling.NEAREST),(col*80,0))
  previews.append(im.convert('RGB'))
 s=io.BytesIO();previews[0].save(s,format='GIF',save_all=True,append_images=previews[1:],duration=260,loop=0,disposal=2)
 payload[SOURCE/'action_review.gif']=s.getvalue()
 cup=Image.open(ROOT/'assets/characters/bridge_workers/cup.png').convert('RGBA')
 alignment=Image.new('RGBA',(640,380),'#29413b');draw=ImageDraw.Draw(alignment)
 for row,prefix in enumerate(['cup_hold_','cup_']):
  for col,direction in enumerate(DIRECTIONS):
   key=prefix+direction;index=0 if row==0 else 2
   record=sequences[key]['frames'][index];body=images[(key,index)]
   pose=Image.new('RGBA',SIZE)
   offset=record['cup_offset'];point=(ANCHOR[0]+offset[0]-3,ANCHOR[1]+offset[1]-6)
   if record.get('cup_layer')=='back':pose.alpha_composite(cup,point)
   pose.alpha_composite(body)
   if record.get('cup_layer')!='back':pose.alpha_composite(cup,point)
   alignment.alpha_composite(pose.resize((160,176),Image.Resampling.NEAREST),(col*160,row*190))
   draw.text((col*160+3,row*190+177),key,fill='#dcd8c6')
 payload[SOURCE/'cup_alignment.png']=png(alignment)
 return payload


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
 payload=build_payload()
 if args.check:
  changed=[str(p.relative_to(ROOT)) for p,data in payload.items() if not p.exists() or p.read_bytes()!=data]
  if changed:raise SystemExit('Changed or missing bridge tender exports: '+', '.join(changed))
  print(f'Verified {len(payload)} bridge tender exports')
 else:
  for p,data in payload.items():p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  print(f'Exported {len(payload)} bridge tender files')

if __name__=='__main__':main()
