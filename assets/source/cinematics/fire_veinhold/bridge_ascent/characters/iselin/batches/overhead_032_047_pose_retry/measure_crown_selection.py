"""Measure candidate crowns; outputs require fresh manual overlay review."""
from pathlib import Path
from PIL import Image,ImageDraw
from hashlib import sha256
from statistics import median
import cv2,numpy as np,json
P=Path(__file__).resolve().parent;B=P.parents[1]
template_path=B/'keys/true_overhead_model_v2.png';template_box=[505,700,758,931];template=Image.open(template_path).crop(tuple(template_box)).convert('L');t=np.asarray(template);selected=json.loads((P/'selection.json').read_text())['frames'];rows=[]
sheet=Image.new('RGB',(2048,820),'#25374b');pen=ImageDraw.Draw(sheet)
for n,source in enumerate(selected):
 path=P/source['source'];digest=sha256(path.read_bytes()).hexdigest()
 if digest!=source['source_sha256']:raise ValueError('Changed selected master')
 sample=Image.open(path).crop(tuple(source['cell'])).convert('RGBA');a=np.asarray(sample.convert('L'));best=(-1,None);small=sample.width<400
 low,high=(.18,.50) if small else (.40,1.10)
 for scale in np.arange(low,high,.005):
  tt=cv2.resize(t,None,fx=scale,fy=scale);tw,th=tt.shape[1],tt.shape[0]
  x0=round(sample.width*.25);y0=round(sample.height*.25);x1=round(sample.width*.88);y1=round(sample.height*.82);roi=a[y0:y1,x0:x1]
  if roi.shape[0]<th or roi.shape[1]<tw:continue
  result=cv2.matchTemplate(roi,tt,cv2.TM_CCOEFF_NORMED);_,score,_,loc=cv2.minMaxLoc(result);point=[x0+loc[0]+tw/2,y0+loc[1]+th/2]
  if point[1]<sample.height*.43:continue
  if score>best[0]:best=(score,{'point':point,'template_scale':float(scale),'template_box':[x0+loc[0],y0+loc[1],x0+loc[0]+tw,y0+loc[1]+th]})
 if best[1] is None:raise ValueError('No crown candidate')
 row={**source,**best[1],'score':best[0],'actual_cell':source['cell'],'feature':'Actual visible white cranium crown NCC, not occupied body bounds','review_state':'pending actual overlay inspection'};rows.append(row)
 vis=Image.new('RGB',sample.size,'#25374b');vis.paste(sample,(0,0),sample);d=ImageDraw.Draw(vis);d.rectangle(row['template_box'],outline='yellow',width=2);x,y=row['point'];d.ellipse((x-3,y-3,x+3,y+3),fill='red');vis.thumbnail((256,384));sheet.paste(vis,(n%8*256,n//8*410));pen.text((n%8*256+5,n//8*410+388),f'{source["phase"]}: {best[0]:.2f} / scale{row["template_scale"]:.3f}',fill='white')
(P/'crown_selection_observations.json').write_text(json.dumps({'version':1,'status':'candidate NCC awaiting actual overlay review','template':{'path':str(template_path.relative_to(B)),'source_sha256':sha256(template_path.read_bytes()).hexdigest(),'cell':template_box,'size':[253,231]},'coordinate_space':'Local source-cell pixels, before any export scale or origin','observations':rows},indent=2)+'\n');sheet.save(P/'crown_observation_overlay.png')
print([(r['phase'],r['point'],round(r['score'],3),round(r['template_scale'],3)) for r in rows])
