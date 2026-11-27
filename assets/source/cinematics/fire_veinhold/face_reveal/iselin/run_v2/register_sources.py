"""Measure image-authored complete run frames; write reproducible registration.

This does not construct a limb, deform a drawing or blend frames. Pose-plan guides
were references for ImageGen only. A uniform density per complete master, calibrated by actual face detail and
checked against neck/belt proportions, registers the selected drawings.
"""
from pathlib import Path
from hashlib import sha256
from math import sin,pi
import json
import numpy as np

from PIL import Image,ImageDraw
P=Path(__file__).resolve().parent
ACTOR=P.parent
ROOT=ACTOR.parents[5]
REFERENCE=Image.open(P/'appearance_reference.png').convert('RGB')
FEATURES={'neck':((355,181,410,221),(384,200)),
          'belt':((352,355,417,401),(384,379)),
          'face':((347,95,426,182),(386,138))}
SEARCH={'neck':(.3,.10,.79,.30),'belt':(.30,.28,.79,.50),'face':(.3,.035,.79,.21)}

def measure(image,name):
    rect,point=FEATURES[name]
    w,h=image.size
    box=tuple(round(v*(w if i%2==0 else h)) for i,v in enumerate(SEARCH[name]))
    region=image.crop(box).convert('L');sm=2
    arr=np.asarray(region.resize((max(1,region.width//sm),max(1,region.height//sm)),Image.Resampling.BILINEAR),dtype=np.float32)
    best=(-2,None,None)
    patch0=REFERENCE.crop(rect).convert('L')
    # Templates sample features, never determine pose from silhouette dimensions.
    for factor in np.linspace(.72,1.18,24):
      scale=h/1024*factor
      patch=np.asarray(patch0.resize((max(3,round(patch0.width*scale/sm)),max(3,round(patch0.height*scale/sm))),Image.Resampling.BILINEAR),dtype=np.float32)
      if min(arr.shape[i]-patch.shape[i] for i in (0,1))<0:continue
      c=patch-patch.mean();n=patch.size
      ph,pw=patch.shape;ah,aw=arr.shape
      fh=1<<(ah+ph-2).bit_length();fw=1<<(aw+pw-2).bit_length()
      corr=np.fft.irfft2(np.fft.rfft2(arr,s=(fh,fw))*np.fft.rfft2(c[::-1,::-1],s=(fh,fw)),s=(fh,fw))
      num=corr[ph-1:ah,pw-1:aw]
      def sums(a):
        v=np.pad(a.astype(np.float64),((1,0),(1,0))).cumsum(0).cumsum(1)
        return v[ph:,pw:]-v[:-ph,pw:]-v[ph:,:-pw]+v[:-ph,:-pw]
      total=sums(arr);var=np.maximum(0,sums(arr*arr)-total*total/n)
      den=np.sqrt(var*float((c*c).sum()))
      scores=np.divide(num,den,out=np.full_like(num,-1),where=den>1e-5)
      iy,ix=np.unravel_index(np.argmax(scores),scores.shape);score=float(scores[iy,ix])
      if score>best[0]:
        pt=[box[0]+ix*region.width/arr.shape[1]+(point[0]-rect[0])*scale,
            box[1]+iy*region.height/arr.shape[0]+(point[1]-rect[1])*scale]
        best=(score,pt,scale)
    return {'point':[round(v,3) for v in best[1]],'score':round(best[0],4),'template_scale':round(best[2],5)}

def main():
    records=[]
    overrides=json.loads((P/'manual_landmark_overrides.json').read_text()) if (P/'manual_landmark_overrides.json').exists() else {}
    generations=json.loads((P/'generation_records.json').read_text())
    cached={v['frame']:v for v in json.loads((P/'measured_features.json').read_text())} if (P/'measured_features.json').exists() else {}
    for i in range(48):
      path=P/generations.get(str(i),{}).get('source_master',f'frame_{i:02d}.png')
      if not path.is_file():raise ValueError(f'Missing complete authored drawing {i}')
      im=Image.open(path).convert('RGBA')
      found=cached[i]['features'] if i in cached and cached[i]['sha256']==sha256(path.read_bytes()).hexdigest() else {name:measure(im,name) for name in FEATURES}
      override=overrides.get(path.relative_to(P).as_posix())
      if override and override['source_sha256']==sha256(path.read_bytes()).hexdigest():
        for name,point in override['landmarks'].items():found[name]['point']=point
      records.append((i,path,im.size,found))
    spans=[(v['belt']['point'][1]-v['neck']['point'][1])*1448/size[1] for _,_,size,v in records]
    density=180/float(np.median(spans))
    frames=[];hashes={};report=[]
    proof=Image.new('RGB',(2048,1536),'#182338');d=ImageDraw.Draw(proof)
    for i,path,size,found in records:
      scale=1/found['face']['template_scale']
      nx,ny=found['neck']['point'];bob=round(4*sin(4*pi*i/48),3)
      origin=[512-nx*scale,200+bob-ny*scale]
      record={'source':'run_v2/'+path.relative_to(P).as_posix(),'cell':[0,0,*size],'scale':scale,'origin':origin,
              'landmarks':{name:v['point'] for name,v in found.items()},
              'landmark_match_scores':{name:v['score'] for name,v in found.items()},
              'authored_weight_offset_y':bob,
              'generation_id':generations.get(str(i),{}).get('generation_id','imagegen'),
              'phase':'right_contact' if i==0 else 'left_contact' if i==24 else 'passing_flight' if i in (12,36) else 'transition',
              'notes':'Complete ImageGen-authored unified drawing. Measured whole-master face/model density and neck translation retain deliberate phase-specific complete-body weight offset. Face/neck/belt agreement is inspected; source anatomy is not changed. No detached limbs, warps, head paste, interpolation or per-pose silhouette fitting.'}
      frames.append(record);hashes[record['source']]=sha256(path.read_bytes()).hexdigest()
      scaled={name:[round(v['point'][0]*scale+origin[0],3),round(v['point'][1]*scale+origin[1],3)] for name,v in found.items()}
      report.append({'frame':i,'scale':scale,'origin':origin,'canonical_landmarks':scaled,'source_landmarks':record['landmarks'],'match_scores':record['landmark_match_scores']})
      im=Image.open(path).convert('RGBA');im.putalpha(im.getchannel('A').point(lambda a:0 if a<=16 else a))
      im=im.convert('RGBa').resize(tuple(round(v*scale) for v in size),Image.Resampling.LANCZOS).convert('RGBA')
      out=Image.new('RGBA',(1024,1024));out.alpha_composite(im,tuple(round(v) for v in origin));out.thumbnail((256,256))
      proof.paste(out,((i%8)*256,(i//8)*256),out);d.text(((i%8)*256+5,(i//8)*256+235),str(i),fill='white')
    for name in ['run_v2/generation_records.json','run_v2/appearance_reference.png','run_v2/manual_landmark_overrides.json']:
      hashes[name]=sha256((ACTOR/name).read_bytes()).hexdigest()
    for row in generations.values():
      name='run_v2/'+row['prompt_file']
      if (ACTOR/name).is_file():hashes[name]=sha256((ACTOR/name).read_bytes()).hexdigest()
    data={'version':1,'actor':'iselin','canvas':[1024,1024],'anchor':[512,960],'cycle_ms':800,'alpha_floor':16,
          'facing':'front','near':'anatomical_right','far':'anatomical_left',
          'contacts':[{'frame':0,'foot':'near'},{'frame':24,'foot':'far'}],
          'approval_state':'implemented_for_ingame_review',
          'construction':'Forty-eight complete individually image-authored frontal running drawings. Verified whole-frame female-model keys and hierarchical midpoint subdivision establish phase and continuous limb/cloth/hair paths. Initial authoring diagrams remain planning history; no guide pixels, detached limbs, idle warps, head pastes or pixel-interpolated anatomy enter production.',
          'registration':'Each complete master has a measured uniform model density calibrated by face detail, checked against neck/belt proportions; whole drawing uniformly sampled and translated only. Extra transparent canvas width preserves flowing hair/mantle at the existing body size.',
          'source_sha256':hashes,'frames':frames}
    (ACTOR/'source_art_48.json').write_text(json.dumps(data,indent=2)+'\n')
    (P/'registration_measurements.json').write_text(json.dumps({'calibration_method':'Uniform per-master face/model density, checked by actual neck/belt proportions; no occupied-bounds fitting','normalized_master_height':1448,'normalized_torso_spans':spans,'median_torso_reference_density':density,'frames':report},indent=2)+'\n')
    proof.save('/tmp/iselin_run_v2_contact.jpg',quality=95)
    print(json.dumps({'median_torso_reference_density':density,'torso_span_range':[min(spans),max(spans)],'count':len(frames)},indent=2))
if __name__=='__main__':main()
