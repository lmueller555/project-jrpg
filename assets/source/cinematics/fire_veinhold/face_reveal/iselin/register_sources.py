"""Record source-cell landmarks and whole-figure registration; no anatomy edits.

Run from the repository root. Template matching measures actual neck, belt and
face features. One common whole-body density per four-pose source master and
documented complete-figure placement preserve the generated drawings.
"""
from pathlib import Path
from hashlib import sha256
import json

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image, ImageDraw

FOLDER = Path(__file__).resolve().parent
REFERENCE = Image.open(FOLDER/'key_00_reference.png').convert('RGB')
FEATURES = {'neck': ((260,116,304,148),(282,132)),
            'belt': ((270,260,306,288),(288,274)),
            'face': ((260,57,306,106),(283,81.5))}


def measure(image, name):
    rectangle, point = FEATURES[name]
    x0,y0,x1,y1 = rectangle
    search = {'neck':(.33,.11,.72,.27),'belt':(.32,.27,.72,.47),
              'face':(.32,.025,.72,.19)}[name]
    width,height=image.size
    box=tuple(round(value*(width if i%2==0 else height)) for i,value in enumerate(search))
    region=image.crop(box).convert('L')
    region=region.resize((max(1,region.width//3),max(1,region.height//3)),Image.Resampling.BILINEAR)
    source=np.asarray(region,dtype=np.float32)
    best=(-2,None,None)
    for factor in np.linspace(.76,1.24,17):
        scale=height/724*factor
        patch=REFERENCE.crop(rectangle).convert('L')
        shape=(max(3,round(patch.width*scale/3)),max(3,round(patch.height*scale/3)))
        patch=np.asarray(patch.resize(shape,Image.Resampling.BILINEAR),dtype=np.float32)
        if patch.shape[0]>source.shape[0] or patch.shape[1]>source.shape[1]:continue
        windows=sliding_window_view(source,patch.shape)
        centered=patch-patch.mean()
        count=patch.size
        denominator=np.sqrt(np.maximum(0,(windows*windows).sum(axis=(-2,-1))-windows.sum(axis=(-2,-1))**2/count)*float((centered*centered).sum()))
        numerator=np.einsum('ijkl,kl->ij',windows,centered,optimize=False)
        scores=np.divide(numerator,denominator,out=np.full_like(numerator,-1),where=denominator>1e-5)
        iy,ix=np.unravel_index(np.argmax(scores),scores.shape)
        score=float(scores[iy,ix])
        if score>best[0]:
            location=[box[0]+ix*region.width/source.shape[1]*3+(point[0]-x0)*scale,
                      box[1]+iy*region.height/source.shape[0]*3+(point[1]-y0)*scale]
            # region/source dimensions coincide; the sampling factor is three.
            best=(score,location,scale)
    return {'score':round(best[0],4),'point':[round(v,3) for v in best[1]],'template_scale':round(best[2],5)}


def main():
    drawings=[]
    hashes={}
    # Small complete-body recoil/rise follows stance/flight, with no head paste.
    body_y=[0,2,4,3,1,-2,-4,-3,-2,-1,0,1,0,2,4,3,1,-2,-4,-3,-2,-1,0,1]
    for start in range(0,24,4):
        filename=f'batch_{start:02d}_{start+3:02d}.png'
        master=Image.open(FOLDER/filename).convert('RGBA')
        hashes[filename]=sha256((FOLDER/filename).read_bytes()).hexdigest()
        width,height=master.size
        cells=((0,0,width//2,height//2),(width//2,0,width,height//2),
               (0,height//2,width//2,height),(width//2,height//2,width,height))
        records=[]
        for j,cell in enumerate(cells):
            crop=master.crop(cell)
            found={name:measure(crop,name) for name in FEATURES}
            records.append((j,cell,crop,found))
        spans=[found['belt']['point'][1]-found['neck']['point'][1] for _,_,_,found in records]
        scale=180/float(np.median(spans))
        for j,cell,crop,found in records:
            index=start+j
            nx,ny=found['neck']['point']
            origin=[384-nx*scale,200+body_y[index]-ny*scale]
            drawings.append({'source':filename,'cell':list(cell),'scale':scale,'origin':origin,
                'landmarks':{name:record['point'] for name,record in found.items()},
                'landmark_match_scores':{name:record['score'] for name,record in found.items()},
                'notes':'Complete image-authored drawing. Uniform density uses median neck-to-belt span of this four-pose source, not occupied bounds. Whole-body registration includes restrained authored stance/flight recoil; no independent head or limb transformation.',
                'phase':'right_contact' if index==0 else 'left_contact' if index==12 else 'flight' if index in (6,18) else 'transition'})
    # Six individual complete-figure repairs bridge the arm exchange and retain
    # a tucked recovery boot during the passing poses instead of an early kick.
    # Preserve every RGB sample; only nearly transparent generator fringe in
    # frame02 is discarded by the explicitly recorded alpha export.
    raw=Image.open(FOLDER/'repairs/frame_02.png').convert('RGBA')
    cleaned=np.array(raw)
    cleaned[:,:,3][cleaned[:,:,3]<16]=0
    Image.fromarray(cleaned).save(FOLDER/'repairs/frame_02_alpha_clean.png')
    for index in (1,2,3,13,14,15):
        filename=f'repairs/frame_{index:02d}'+('_alpha_clean.png' if index==2 else '.png')
        crop=Image.open(FOLDER/filename).convert('RGBA')
        found={name:measure(crop,name) for name in FEATURES}
        span=found['belt']['point'][1]-found['neck']['point'][1]
        scale=180/span
        nx,ny=found['neck']['point']
        origin=[384-nx*scale,200+body_y[index]-ny*scale]
        drawings[index]={'source':filename,'cell':[0,0,*crop.size],'scale':scale,'origin':origin,
            'landmarks':{name:record['point'] for name,record in found.items()},
            'landmark_match_scores':{name:record['score'] for name,record in found.items()},
            'notes':'Complete individual figure redrawn by ImageGen to bridge the arm exchange gradually. Uniform whole-figure density from measured neck-to-belt span; no separate head, hand or limb manipulation.',
            'phase':'early_stance'}
        hashes[filename]=sha256((FOLDER/filename).read_bytes()).hexdigest()
    data={'version':1,'actor':'iselin','canvas':[768,1024],'anchor':[384,960],
        'cycle_ms':400,'facing':'front','near':'anatomical_right','far':'anatomical_left',
        'contacts':[{'frame':0,'foot':'near'},{'frame':12,'foot':'far'}],
        'construction':'Twenty-four complete image-authored frontal running poses. No detached limbs, head pastes, idle warps or pixel-interpolated anatomy.',
        'registration':'Measured neck, belt and face source-cell landmarks; uniform whole-figure sampling. Four-pose master median torso density and restrained complete-body recoil.',
        'source_sha256':hashes,'frames':drawings}
    (FOLDER/'source_art_24.json').write_text(json.dumps(data,indent=2)+'\n')
    report=[]
    proof=Image.new('RGB',(1536,1056),'#182338');painter=ImageDraw.Draw(proof)
    for index,record in enumerate(drawings):
        master=Image.open(FOLDER/record['source']).convert('RGBA');crop=master.crop(record['cell'])
        size=tuple(round(value*record['scale']) for value in crop.size)
        sampled=crop.convert('RGBa').resize(size,Image.Resampling.LANCZOS).convert('RGBA')
        frame=Image.new('RGBA',(768,1024));frame.alpha_composite(sampled,tuple(round(v) for v in record['origin']))
        frame.thumbnail((256,256));x=(index%6)*256;y=(index//6)*264;proof.paste(frame,(x,y),frame)
        painter.text((x+5,y+245),str(index),fill='white')
        report.append({'frame':index,'scale':record['scale'],'origin':record['origin'],'landmarks':record['landmarks'],'scores':record['landmark_match_scores']})
    proof.save('/tmp/iselin_frontal_registered24_contact.jpg',quality=94)
    (FOLDER/'registration_measurements.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
