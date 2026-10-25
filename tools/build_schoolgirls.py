"""Native child girls posed with the shared four-phase walk and run rhythm."""
import hashlib
import json
from pathlib import Path
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
SIZE=(24,36);DIRECTIONS=('front','left','right','back')
SPECS={
 'tessa':{'name':'Tessa','age_years':10,'height':28,'home':'home_a','style':'braid','eyes':'#3f784b',
          'hair':['#4b2928','#854b39','#b6754e'],'dress':['#405b49','#6e9275','#a0b9a2'],
          'trim':['#bcae91','#ded1ae','#fbeed0'],'design':'Auburn braid, cream blouse and sage pinafore.'},
 'ada':{'name':'Ada','age_years':7,'height':24,'home':'home_b','style':'bob','eyes':'#356c9b',
        'hair':['#242027','#38343d','#55515b'],'dress':['#304f70','#4d77a0','#7da5c7'],
        'trim':['#bcae91','#ded1ae','#fbeed0'],'design':'Dark bob, blue dress and cream collar.'},
 'pippa':{'name':'Pippa','age_years':8,'height':26,'home':'home_c','style':'ponytail','eyes':'#98703a',
          'hair':['#88633b','#c79f5b','#ead197'],'dress':['#51364f','#805477','#ad80a0'],
          'trim':['#394955','#596e7d','#8197a5'],'design':'Sandy-blonde ponytail, plum dress and blue-gray ribbon.'},
}


def blank():return Image.new('RGBA',SIZE)
def write(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n')
def move(im,dx=0,dy=0):
 out=blank();out.alpha_composite(im,(dx,dy));return out


def head(spec,direction,phase=0,motion='idle'):
 t=35-spec['height'];layers={'hair_back':blank(),'face_and_hair':blank(),'hair_accessory':blank()}
 hb=ImageDraw.Draw(layers['hair_back']);d=ImageDraw.Draw(layers['face_and_hair']);a=ImageDraw.Draw(layers['hair_accessory'])
 h0,h1,h2=spec['hair'];edge='#1a0e16';skin='#e8c49d';shade='#eda052';style=spec['style']
 if direction in ('front','back'):
  silhouette=[(9,t),(14,t),(16,t+2),(17,t+5),(16,t+9),(14,t+11),(10,t+11),(8,t+9),(7,t+4),(8,t+1)]
  d.polygon(silhouette,fill=edge);d.polygon([(9,t+1),(14,t+1),(16,t+3),(16,t+8),(14,t+10),(10,t+10),(8,t+8),(8,t+3)],fill=h1)
  d.line((9,t+2,13,t+1),fill=h2);d.point((15,t+3),fill=h2)
  if direction=='front':
   d.polygon([(10,t+4),(14,t+4),(15,t+5),(15,t+9),(13,t+11),(11,t+11),(9,t+9),(9,t+6)],fill=skin)
   d.line((14,t+5,14,t+8),fill=shade)
   d.polygon([(8,t+3),(13,t+2),(16,t+4),(14,t+5),(12,t+4),(10,t+5),(8,t+6)],fill=h1)
   d.line((10,t+3,13,t+3),fill=h2)
   for x in (10,14):
    d.point((x,t+6),fill=edge);d.point((x,t+7),fill=spec['eyes'])
   d.point((12,t+9),fill=shade)
   # A warm skin-tone lip avoids the old black open-mouth illusion.
   d.point((12,t+10),fill=shade)
   d.rectangle((11,t+11,13,t+12),fill=skin)
   if style=='bob':
    d.line((8,t+5,8,t+10),fill=h0);d.line((16,t+5,16,t+10),fill=h0)
    d.point((9,t+10),fill=h2);d.point((15,t+10),fill=h2)
  else:
   d.line((9,t+4,9,t+9),fill=h0);d.line((11,t+3,11,t+9),fill=h2);d.line((14,t+4,14,t+10),fill=h0)
   if style=='bob':d.line((9,t+11,15,t+11),fill=h0)
  if style=='braid':
   bx=16 if direction=='front' else 12;lag=(0,1,0,-1)[phase] if motion!='idle' else 0
   points=[(bx+(lag if yy>=t+14 else 0),yy) for yy in range(t+7,t+19)]
   a.line(points,fill=edge,width=3)
   for yy in range(t+8,t+18,2):
    xx=bx+(lag if yy>=t+14 else 0);a.line((xx-1,yy,xx+1,yy+1),fill=h1);a.point((xx,yy),fill=h2)
   a.line((bx+lag-1,t+18,bx+lag+1,t+18),fill=spec['dress'][0])
  if style=='ponytail':
   bx=17 if direction=='front' else 14;lag=(0,1,0,-1)[phase] if motion!='idle' else 0
   hb.polygon([(bx,t+3),(bx+2,t+4),(bx+3,t+8+lag),(bx+1,t+13+lag),(bx-1,t+12),(bx,t+8)],fill=edge)
   hb.line((bx+1,t+5,bx+1,t+11+lag),fill=h1,width=2);hb.point((bx+1,t+7),fill=h2)
   a.line((bx-1,t+4,bx+1,t+4),fill=spec['trim'][2]);a.point((bx+2,t+3),fill=spec['trim'][1])
 else:
  # Author a left profile, then turn this identity's own silhouette to the right.
  d.polygon([(10,t),(14,t),(16,t+2),(16,t+8),(14,t+11),(10,t+11),(9,t+9),(7,t+8),(7,t+6),(8,t+5),(8,t+2)],fill=edge)
  d.polygon([(10,t+1),(14,t+1),(15,t+3),(15,t+8),(13,t+10),(10,t+10),(9,t+8),(8,t+8),(8,t+6),(9,t+5),(9,t+3)],fill=h1)
  d.line((11,t+2,14,t+2),fill=h2)
  d.polygon([(9,t+4),(12,t+4),(13,t+6),(12,t+9),(11,t+11),(9,t+10),(8,t+8),(7,t+8),(8,t+6)],fill=skin)
  d.point((10,t+6),fill=edge);d.point((10,t+7),fill=spec['eyes']);d.point((8,t+9),fill=shade)
  d.line((12,t+5,12,t+8),fill=shade)
  d.polygon([(9,t+2),(13,t+2),(13,t+5),(11,t+4),(9,t+5),(8,t+5)],fill=h1)
  d.rectangle((11,t+11,13,t+12),fill=skin)
  if style=='bob':d.line((14,t+5,14,t+10),fill=h0,width=2);d.point((13,t+10),fill=h2)
  if style=='braid':
   lag=(0,1,0,-1)[phase] if motion!='idle' else 0
   a.line([(15,t+6),(16,t+12),(16+lag,t+16),(16+lag,t+18)],fill=edge,width=3)
   for yy in range(t+7,t+18,2):
    xx=16+(lag if yy>=t+14 else 0);a.line((xx-1,yy,xx+1,yy+1),fill=h1);a.point((xx,yy),fill=h2)
   a.line((15+lag,t+18,17+lag,t+18),fill=spec['dress'][0])
  if style=='ponytail':
   lag=(0,1,0,-1)[phase] if motion!='idle' else 0
   hb.polygon([(15,t+3),(18,t+3),(20,t+6+lag),(18,t+13+lag),(16,t+12),(17,t+7)],fill=edge)
   hb.line((17,t+5,18,t+8+lag,17,t+11+lag),fill=h1,width=2);hb.point((18,t+6),fill=h2)
   a.line((15,t+4,18,t+4),fill=spec['trim'][2]);a.point((19,t+3),fill=spec['trim'][1])
  if direction=='right':layers={key:im.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for key,im in layers.items()}
 return layers


def legs(spec,direction,motion,phase,dy):
 out=blank();d=ImageDraw.Draw(out);edge='#1a0e16';skin='#e8c49d';shadow='#eda052'
 run=motion=='run';idle=motion=='idle'
 if direction in ('front','back'):
  toes=[(9,34),(15,34)] if idle else ([(7,34),(16,31)] if run and phase==0 else [(10,31),(15,30)] if run and phase==1 else [(8,31),(17,34)] if run and phase==2 else [(9,30),(14,31)] if run else [(9,34),(15,32)] if phase==0 else [(10,33),(14,34)] if phase==1 else [(9,32),(15,34)] if phase==2 else [(9,34),(14,33)])
  roots=[(10,27+dy),(14,27+dy)]
 else:
  if idle:toes=[(10,34),(14,34)]
  elif run:toes=([(6,34),(17,30)],[(16,31),(9,30)],[(17,30),(6,34)],[(9,30),(16,31)])[phase]
  else:toes=([(8,34),(16,33)],[(11,32),(14,34)],[(16,33),(8,34)],[(14,34),(11,32)])[phase]
  roots=[(11,27+dy),(13,27+dy)]
 for i,((rx,ry),(tx,ty)) in enumerate(zip(roots,toes)):
  knee=(round((rx+tx)/2),min(ty-2,30+dy))
  d.line((rx,ry,*knee,tx,ty-2),fill=shadow if i==0 else skin,width=2)
  d.polygon([(tx-1,ty-3),(tx+1,ty-3),(tx+1,ty),(tx-2,ty),(tx-2,ty-1)],fill=edge)
  d.line((tx,ty-2,tx,ty-1),fill='#84512e' if i else '#3d2118')
  d.point((tx-1,ty-1),fill='#9d6238' if i else '#84512e')
 if direction=='right':out=out.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 return out


def torso(spec,direction,motion,phase,dy):
 top=35-spec['height']+12;out=blank();d=ImageDraw.Draw(out);m0,m1,m2=spec['dress'];edge='#1a0e16'
 profile=direction in ('left','right');left,right=(10,15) if profile else (8,16)
 d.polygon([(left,top),(right,top),(right-1,27+dy),(left+1,27+dy)],fill=edge)
 d.polygon([(left+1,top),(right-1,top),(right-1,27+dy),(left+1,27+dy)],fill=m1)
 d.line((left+1,top+1,left+1,26+dy),fill=m2)
 # Cream blouse visible above Tessa's pinafore; Ada's small collar stays cream.
 if spec['style']=='braid':
  d.rectangle((left+1,top,right-1,min(top+3,26+dy)),fill=spec['trim'][1])
  d.line((left+1,top,left+1,min(top+4,27+dy)),fill=m0)
  d.line((right-1,top,right-1,min(top+4,27+dy)),fill=m0)
 elif direction!='back':
  d.line((left+1,top,right-1,top),fill=spec['trim'][2]);d.point((12,top+1),fill=spec['trim'][1])
 if direction=='right':out=out.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 return out


def skirt(spec,direction,motion,phase,dy):
 out=blank();d=ImageDraw.Draw(out);m0,m1,m2=spec['dress'];edge='#1a0e16'
 run=motion=='run';passing=motion!='idle' and phase%2
 hem=29 if run and passing else 30 if run else 30 if passing else 31
 sway=(0,1,0,-1)[phase] if motion!='idle' else 0
 if direction in ('left','right'):
  poly=[(10,26+dy),(15,26+dy),(17+sway,hem),(8+sway,hem)]
 else:poly=[(9,26+dy),(15,26+dy),(18+sway,hem),(6+sway,hem)]
 d.polygon(poly,fill=edge)
 inner=[(poly[0][0]+1,poly[0][1]),(poly[1][0]-1,poly[1][1]),(poly[2][0]-1,hem-1),(poly[3][0]+1,hem-1)]
 d.polygon(inner,fill=m1);d.line((11,27+dy,10+sway,hem-1),fill=m2);d.line((14,27+dy,15+sway,hem-1),fill=m0)
 if spec['style']=='braid':
  # A narrower pinafore panel over cream sleeves, rather than an adult apron.
  d.line((11,27+dy,11+sway,hem-1),fill=m2,width=2)
 d.line((poly[3][0]+1,hem-1,poly[2][0]-1,hem-1),fill=m0)
 if direction=='right':out=out.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 return out


def arms(spec,direction,motion,phase,dy):
 top=35-spec['height']+12;out=blank();d=ImageDraw.Draw(out);profile=direction in ('left','right')
 edge='#1a0e16';cloth=spec['trim'][1] if spec['style']=='braid' else spec['dress'][1];light=spec['trim'][2] if spec['style']=='braid' else spec['dress'][2]
 if motion=='idle':
  joints=[((8,top+1),(7,top+4),(6,27)),((16,top+1),(17,top+4),(18,27))] if not profile else [((12,top+1),(12,top+4),(11,28))]
 elif motion=='walk':
  swing=(2,0,-2,0)[phase]
  joints=[((8,top+dy+1),(7,top+dy+4),(6,27+swing//2)),((16,top+dy+1),(17,top+dy+4),(18,27-swing//2))] if not profile else [((12,top+dy+1),(12+swing,top+dy+4),(11+swing,28+dy))]
 else:
  swing=(2,-1,-2,1)[phase]
  joints=[((8,top+dy+1),(5,top+dy+4),(7+swing,top+dy+2)),((16,top+dy+1),(19,top+dy+4),(17-swing,top+dy+2))] if not profile else [((12,top+dy+1),(15+swing,top+dy+4),(13+swing,top+dy+2)),((11,top+dy+1),(8-swing,top+dy+4),(6-swing,top+dy+2))]
 for shoulder,elbow,hand in joints:
  d.line((*shoulder,*elbow,*hand),fill=edge,width=3)
  d.line((*shoulder,*elbow,*hand),fill=cloth,width=2)
  d.point(elbow,fill=light);d.point(hand,fill='#e8c49d');d.point((hand[0],hand[1]+1),fill='#eda052')
 if direction=='right':out=out.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 return out


def pose(spec,direction,motion='idle',phase=0):
 dy=0 if motion=='idle' else -(phase%2)*(2 if motion=='run' else 1)
 lean=(-1 if direction=='left' else 1 if direction=='right' else 0) if motion=='run' else 0
 heads=head(spec,direction,phase,motion)
 layers={'hair_back':move(heads['hair_back'],lean,dy),'legs_and_boots':legs(spec,direction,motion,phase,dy),
         'dress_body':move(torso(spec,direction,motion,phase,0),lean,dy),
         'skirt':skirt(spec,direction,motion,phase,dy),'arms':move(arms(spec,direction,motion,phase,dy),lean,0),
         'head':move(heads['face_and_hair'],lean,dy),'hair_accessory':move(heads['hair_accessory'],lean,dy)}
 im=blank()
 for layer in layers.values():im.alpha_composite(layer)
 return im,layers,dy,lean


def export(root,source,direction,motion,frames):
 status=json.loads((root/'character.json').read_text())['status']
 records=[];unique=set()
 for i,(im,layers,dy,lean) in enumerate(frames,1):
  name=f'frame_{i:02}.png' if motion!='idle' else f'idle_{direction}.png'
  directory=root/f'{motion}_{direction}' if motion!='idle' else root
  directory.mkdir(parents=True,exist_ok=True);im.save(directory/name)
  paths=[];rebuilt=blank()
  for key,layer in layers.items():
   path=source/f'{motion}_{direction}'/f'frame_{i:02}_{key}.png';path.parent.mkdir(parents=True,exist_ok=True);layer.save(path);paths.append(path.relative_to(ROOT).as_posix());rebuilt.alpha_composite(layer)
  assert rebuilt.tobytes()==im.tobytes()
  assert set(im.getchannel('A').tobytes())=={0,255}
  box=im.getbbox();assert box and box[0]>0 and box[2]<24 and box[1]>=0 and box[3]<=35,(direction,motion,i,box)
  unique.add(im.tobytes())
  top=35-SPECS[root.name]['height'];eyes=[]
  if direction=='front':eyes=[[10+lean,top+6+dy],[14+lean,top+6+dy]]
  elif direction=='left':eyes=[[10+lean,top+6+dy]]
  elif direction=='right':eyes=[[13+lean,top+6+dy]]
  records.append({'file':name,'duration_ms':140 if motion=='walk' else 100,'layers_from_repo_root':paths,
                  'upper_body_offset':[lean,dy],'shoulder_offset':[lean,dy],'eyes':eyes,
                  'phase':('contact_near','passing_near','contact_far','passing_far')[i-1] if motion=='walk' else ('contact_near','flight_near','contact_far','flight_far')[i-1]})
 if motion!='idle':
  assert len(unique)==4,(root.name,motion,direction)
  meta={'character':root.name,'status':status,'animation':f'{motion}.{direction}','frame_size':[24,36],
        'frame_count':4,'draw_anchor':[12,30],'foot_anchor':[12,34],'frames':records,'loop':True}
  write(directory/'animation.json',meta)
  strip=Image.new('RGBA',(96,36))
  for i,(im,*_) in enumerate(frames):strip.alpha_composite(im,(24*i,0))
  strip.save(directory/'spritesheet.png')
 else:
  spec=SPECS[root.name]
  write(root/f'idle_{direction}.json',{'character':root.name,'status':status,'animation':f'idle.{direction}',
       'image':f'idle_{direction}.png','frame_size':[24,36],'draw_anchor':[12,30],'foot_anchor':[12,34],
       'visible_height_px':spec['height'],'eyes':{'top_pixels':records[0]['eyes'],'height':2,'iris_offset_y':1},
       'layers_from_repo_root':records[0]['layers_from_repo_root']})
 return records


def reviews(root):
 from PIL import ImageFont
 from build_liam_family_front_walks import save_gif
 f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
 board=Image.new('RGB',(960,960),'#e8edf2');d=ImageDraw.Draw(board);d.fontmode='1'
 for row,motion in enumerate(('idle','walk','run')):
  for col,direction in enumerate(DIRECTIONS):
   path=root/f'idle_{direction}.png' if motion=='idle' else root/f'{motion}_{direction}/frame_01.png'
   im=Image.open(path).convert('RGBA').resize((192,288),Image.Resampling.NEAREST)
   board.paste(im,(col*240,row*320+25),im);d.text((col*240+5,row*320),motion+' '+direction,font=f,fill='#26343e')
 board.save(root/'direction_review.png')
 for motion,ms in (('walk',140),('run',100)):
  frames=[]
  for index in range(4):
   im=Image.new('RGB',(640,260),'#e8edf2');draw=ImageDraw.Draw(im);draw.fontmode='1'
   for col,direction in enumerate(DIRECTIONS):
    sprite=Image.open(root/f'{motion}_{direction}/frame_{index+1:02}.png').convert('RGBA').resize((144,216),Image.Resampling.NEAREST)
    im.paste(sprite,(col*160,24),sprite);draw.text((col*160+5,0),direction,font=f,fill='#26343e')
   frames.append(im)
  save_gif(root/f'{motion}_review.gif',frames,ms)
  save_gif(root/f'{motion}_slow_review.gif',frames,ms*3)


def build():
 protected={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for who in ('liam','liam_mother','liam_father') for p in (ROOT/'assets/characters'/who).rglob('*.png')}
 for identity,spec in SPECS.items():
  root=ROOT/'assets/characters'/identity;source=ROOT/'assets/source/characters'/identity
  status=json.loads((root/'character.json').read_text())['status'] if (root/'character.json').exists() else 'review'
  palette={'status':status,'materials':{'outline':['#1a0e16'],'skin':['#e8c49d','#eda052'],'hair':spec['hair'],
          'dress':spec['dress'],'trim':spec['trim'],'leather':['#3d2118','#84512e','#9d6238']},'eyes':{'pupil':'#1a0e16','iris':spec['eyes']}}
  write(root/'palette.json',palette)
  write(root/'character.json',{'id':identity,'name':spec['name'],'age_years':spec['age_years'],'visible_height_px':spec['height'],
                             'frame_size':[24,36],'draw_anchor':[12,30],'foot_anchor':[12,34],'home':spec['home'],
                             'status':status,'design':spec['design'],'approved_reference_png_sha256':protected})
  write(source/'recipe.json',{**spec,'frame_size':[24,36],'draw_anchor':[12,30],'foot_anchor':[12,34],
                             'shared_motion':'Four phases, 140ms walk / 100ms run; native coordinated head/shoulder translation.',
                             'builder':'tools/build_schoolgirls.py'})
  for direction in DIRECTIONS:
   export(root,source,direction,'idle',[pose(spec,direction)])
   for motion in ('walk','run'):export(root,source,direction,motion,[pose(spec,direction,motion,i) for i in range(4)])
  write(root/'idle_all.json',{'character':identity,'status':status,'directions':list(DIRECTIONS),'frame_size':[24,36]})
  strip=Image.new('RGBA',(96,36))
  for i,direction in enumerate(DIRECTIONS):strip.alpha_composite(Image.open(root/f'idle_{direction}.png').convert('RGBA'),(i*24,0))
  strip.save(root/'idle_all.png')
  reviews(root)
  (root/'README.md').write_text(f"# {spec['name']} — child sprite pack\n\nAge {spec['age_years']}; {spec['design']} Home: `{spec['home']}`.\n\nFour directional idles, walks (4×140ms) and runs (4×100ms) use 24×36 frames\nwith foot anchor [12,34] and draw anchor [12,30]. Visible idle height: {spec['height']} px.\nOriginal cast remains unchanged. Source layers/recipe retain every export.\nRun poses use a forward lean, compact bent arms, alternating support/flight\nand a lifted skirt; walks use the established one-pixel head/shoulder bob.\n\nRebuild with `python tools/build_schoolgirls.py`.\n")
 assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in protected.items())
 print('Built Tessa, Ada and Pippa: four idles, four-frame walks and runs in every direction.')


if __name__=='__main__':build()
