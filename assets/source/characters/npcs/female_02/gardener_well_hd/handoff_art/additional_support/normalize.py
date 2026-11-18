"""Technical extraction of eight complete image-authored support poses."""
from pathlib import Path
from PIL import Image,ImageDraw
from hashlib import sha256
from collections import deque
import json
folder=Path(__file__).resolve().parent
source=folder/'support_master.png';raw=Image.open(source).convert('RGBA');W,H=raw.size
threshold=220;parts=[]
labels=['engage_start','engage_reach','engage_grip','brace_hold','secure_brake','disengage_release','disengage_recover','disengage_rest']
for i in range(8):
 c,r=i%4,i//4;cell=[round(c*W/4),round(r*H/2),round((c+1)*W/4),round((r+1)*H/2)]
 im=raw.crop(cell);a=im.getchannel('A').point(lambda v:255 if v>=threshold else 0);pix=a.load();seen=set();components=[]
 for y in range(a.height):
  for x in range(a.width):
   if not pix[x,y] or (x,y) in seen:continue
   q=deque([(x,y)]);seen.add((x,y));component=[]
   while q:
    p=q.popleft();component.append(p)
    for n in ((p[0]-1,p[1]),(p[0]+1,p[1]),(p[0],p[1]-1),(p[0],p[1]+1)):
     if 0<=n[0]<a.width and 0<=n[1]<a.height and n not in seen and pix[n[0],n[1]]:seen.add(n);q.append(n)
   components.append(component)
 component=max(components,key=len);mask=Image.new('L',im.size);mp=mask.load()
 for x,y in component:mp[x,y]=255
 im.putalpha(mask);box=im.getbbox();bottom=box[3];feet=[x for x,y in component if y>=bottom-6];footx=(min(feet)+max(feet)+1)/2
 parts.append((im,box,footx,bottom,cell))
scale=68/(parts[0][1][3]-parts[0][1][1]);records=[]
for i,(im,box,footx,bottom,cell) in enumerate(parts):
 cropped=im.crop(box);sz=[round(cropped.width*scale),round(cropped.height*scale)];pose=cropped.resize(sz,Image.Resampling.NEAREST);offset=[round(48-(footx-box[0])*scale),80-pose.height]
 canvas=Image.new('RGBA',(96,96));canvas.alpha_composite(pose,tuple(offset));target=folder/'native'/f'frame_{i:02}.png';target.parent.mkdir(parents=True,exist_ok=True);canvas.save(target)
 records.append({'group':'support_left','index':i,'label':labels[i],'source':'support_master.png','source_sha256':sha256(source.read_bytes()).hexdigest(),'grid':[4,2],'cell':i,'source_cell_rect':cell,'alpha_threshold':threshold,'source_bbox':list(box),'source_foot':[footx,bottom],'whole_frame_uniform_scale':scale,'native_crop_size':sz,'native_offset':offset,'canvas_artwork':[96,96],'logical_size':[48,48],'draw_anchor_logical':[24,36],'foot_anchor_artwork':[48,80],'native_file':str(target.relative_to(folder)),'native_sha256':sha256(target.read_bytes()).hexdigest()})
(folder/'extraction.json').write_text(json.dumps({'version':1,'method':'Complete image_gen-authored poses; technical component/cell isolation, hard alpha and uniform whole-frame normalization only.','records':records},indent=2)+'\n')
board=Image.new('RGB',(8*160,208),'#243c38');d=ImageDraw.Draw(board)
for i,record in enumerate(records):
 im=Image.open(folder/record['native_file']).convert('RGBA').resize((144,144),Image.Resampling.NEAREST);board.paste(im,(i*160+8,20),im);d.text((i*160+8,175),record['label'],fill='white')
board.save(folder/'inspection.png')
print('Eight complete support poses normalized; source retained unchanged.')
