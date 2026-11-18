from pathlib import Path
from PIL import Image,ImageDraw
from hashlib import sha256
from collections import deque
import json,statistics
root=Path(__file__).resolve().parents[7]
folder=Path(__file__).resolve().parent
threshold=220
sheets=[('transfer_pickup_master.png',['attach_back']*8+['pickup_left']*8),('ground_pour_master.png',['pour_ground_left']*8+['pour_ground_right']*8),('trough_pour_master.png',['pour_trough_left']*8+['pour_trough_right']*8)]
records=[]
for filename,groups in sheets:
 raw=Image.open(folder/filename).convert('RGBA'); W,H=raw.size
 crops=[]
 for i in range(16):
  col,row=i%4,i//4
  cell=[round(col*W/4),round(row*H/4),round((col+1)*W/4),round((row+1)*H/4)]
  im=raw.crop(tuple(cell)); mask=im.getchannel('A').point(lambda a:255 if a>=threshold else 0)
  pix=mask.load(); seen=set(); components=[]
  for y in range(mask.height):
   for x in range(mask.width):
    if not pix[x,y] or (x,y) in seen:continue
    q=deque([(x,y)]); seen.add((x,y)); comp=[]
    while q:
     p=q.popleft();comp.append(p)
     for n in ((p[0]-1,p[1]),(p[0]+1,p[1]),(p[0],p[1]-1),(p[0],p[1]+1)):
      if 0<=n[0]<mask.width and 0<=n[1]<mask.height and n not in seen and pix[n[0],n[1]]:seen.add(n);q.append(n)
    components.append(comp)
  component=max(components,key=len)
  cleaned=Image.new('L',im.size);cp=cleaned.load()
  for x,y in component:cp[x,y]=255
  im.putalpha(cleaned)
  box=im.getbbox();bottom=box[3]
  feet=[x for x,y in component if y>=bottom-6]
  footx=(min(feet)+max(feet)+1)/2
  crops.append((im,box,footx,bottom,cell,len(components),len(component)))
 # Upright first reference, same uniform whole-body scale across all16 cells.
 refheight=crops[0][1][3]-crops[0][1][1]
 scale=68/refheight
 for i,(im,box,footx,bottom,cell,ncomp,count) in enumerate(crops):
  group=groups[i];index=i%8
  cropped=im.crop(box);sz=(round(cropped.width*scale),round(cropped.height*scale)); native=cropped.resize(sz,Image.Resampling.NEAREST)
  offset=(round(48-(footx-box[0])*scale),80-native.height)
  canvas=Image.new('RGBA',(96,96));canvas.alpha_composite(native,offset)
  target=folder/'native'/group/f'frame_{index:02}.png';target.parent.mkdir(parents=True,exist_ok=True);canvas.save(target)
  records.append({'group':group,'index':index,'source':filename,'source_sha256':sha256((folder/filename).read_bytes()).hexdigest(),'grid':[4,4],'cell':i,'source_cell_rect':cell,'alpha_threshold':threshold,'source_component_policy':'Isolate the coherent complete full-body component after hard-alpha threshold; discard transparent generation fringe/noise only.','source_bbox':list(box),'source_foot':[footx,bottom],'whole_frame_uniform_scale':scale,'native_crop_size':list(sz),'native_offset':list(offset),'canvas_artwork':[96,96],'logical_size':[48,48],'draw_anchor_logical':[24,36],'foot_anchor_artwork':[48,80],'native_file':str(target.relative_to(folder)),'native_sha256':sha256(target.read_bytes()).hexdigest(),'discarded_fragment_components':ncomp-1})
meta={'version':1,'artwork_pixels_per_world_pixel':2,'status':'staged_authored_pose_sources','method':'New image_gen complete character drawings, technical cell extraction, hard alpha and uniform whole-frame normalization only. No limbs/body parts rotate or warp in export.','identity_reference':'assets/characters/npcs/female_02/idle_back.png','threshold':threshold,'records':records,'limits':'Static complete pose drawings. Grip/contact and joint mechanism timeline need final parent-level review. Attachment/retrieval can reverse authored reach/recover poses where motion remains natural.'}
(folder/'extraction.json').write_text(json.dumps(meta,indent=2)+'\n')
# Labelled technical inspection board, independent native exports are the reference.
board=Image.new('RGB',(8*180,6*205+64),'#243c38');d=ImageDraw.Draw(board);d.text((12,12),'GARDENER complete authored handoff / pickup / pouring frames — 2x inspection',fill='white')
for n,r in enumerate(records):
 im=Image.open(folder/r['native_file']).convert('RGBA').resize((144,144),Image.Resampling.NEAREST)
 x=(n%8)*180+18;y=(n//8)*205+48
 board.paste(im,(x,y),im);d.text((x,y+149),f"{r['group']} {r['index']+1}",fill='white')
board.save(folder/'inspection.png')
print(len(records),'authored native frames extracted; source files retained unchanged.')
