"""Reproducible native identity and literal complete-pose walk export.
Retained high-resolution identity source, not enlarged legacy game pixels.
"""
from pathlib import Path
from PIL import Image,ImageColor,ImageDraw
import argparse,json,hashlib,shutil
p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,required=True);p.add_argument('--legacy-input-root',type=Path);a=p.parse_args();R=a.repo_root.resolve();OLD=(a.legacy_input_root or R).resolve()
who='serene'
src=OLD/f'assets/source/characters/{who}';out=R/f'assets/characters/named_hd/{who}';out.mkdir(parents=True,exist_ok=True)
pal=json.loads((OLD/f'assets/characters/{who}/palette.json').read_text());front=json.loads((src/'export.json').read_text());turn=json.loads((src/'turnaround_export.json').read_text())
for face in ['front','left','right','back']:
 recipe=front if face=='front' else turn['views'][face];source=Image.open(src/(front['source'] if face=='front' else turn['source'])).convert('RGBA');im=Image.new('RGBA',(48,72));left,_,right,_=recipe['source_bounds'];ox=recipe['occupied_rect'][0]*2 if 'occupied_rect'in recipe else recipe['native_x']*2;width=recipe['occupied_rect'][2]*2 if 'occupied_rect'in recipe else recipe['native_width']*2
 for band in recipe['bands']:
  top,bottom=band['source_y'];first,last=[v*2 for v in band['native_y']];piece=source.crop((left,top,right,bottom)).resize((width,last-first),Image.Resampling.NEAREST)
  for y in range(piece.height):
   for x in range(piece.width):
    px=piece.getpixel((x,y))
    if px[3]<128:continue
    sx=left+(x+.5)*(right-left)/width;sy=top+(y+.5)*(bottom-top)/piece.height;materials=band['materials']
    for win in recipe['material_windows']:
     x0,y0,x1,y1=win['rect']
     if x0<=sx<x1 and y0<=sy<y1:materials=win['materials']
    colors=[ImageColor.getrgb(c) for mat in materials for c in pal['materials'][mat]];color=min(colors,key=lambda c:sum((a-b)**2 for a,b in zip(c,px[:3])));im.putpixel((ox+x,first+y),(*color,255))
 eyes=recipe['eyes']['top_pixels'] if isinstance(recipe['eyes'],dict) else recipe['eyes'];d=ImageDraw.Draw(im)
 for x,y in eyes:
  d.rectangle((x*2,y*2,x*2+1,y*2+1),fill=pal['eyes']['pupil']);d.point((x*2,y*2+2),fill=pal['eyes']['iris'])
 im.save(out/f'idle_{face}.png')
plans=json.loads((Path(__file__).parent/'walk_drawings.json').read_text())
for face,fs in plans.items():
 idle=Image.open(out/f'idle_{face}.png').convert('RGBA');frames=[]
 for i,f in enumerate(fs):
  im=Image.new('RGBA',(48,72));d=ImageDraw.Draw(im)
  for sh in f['shapes']:
   pts=list(map(tuple,sh['points']))
   if sh.get('line'):d.line(pts,fill=sh['fill'])
   else:d.polygon(pts,fill=sh['fill'],outline=sh.get('outline'))
  # Unwarped identity-bearing costume panel; no retained idle arms or legs.
  mask=Image.new('L',(48,72));ImageDraw.Draw(mask).polygon(list(map(tuple,f['costume_preservation_polygon'])),fill=255);panel=Image.new('RGBA',(48,72));panel.paste(idle,(0,0),mask);im.alpha_composite(panel,tuple(f['head_shift']));im.alpha_composite(idle.crop((0,0,48,f['head_cut'])),tuple(f['head_shift']))
  target=out/f'walk_{face}';target.mkdir(exist_ok=True);im.save(target/f'frame_{i+1:02}.png')
  frames.append(dict(file=f'frame_{i+1:02}.png',duration_ms=140,phase=f['phase']))
 m=dict(character=who,animation=f'walk.{face}',artwork_pixels_per_world_pixel=2,frame_size=[48,72],logical_size=[24,36],draw_anchor=[24,60],foot_anchor=[24,68],loop=True,cycle_ms=560,frames=frames)
 (target/'animation.json').write_text(json.dumps(m,indent=2)+'\n')
shutil.copyfile(OLD/f'assets/portraits/eldenmere/{who}_neutral.png',out/'portrait.png')
m=dict(id=who,display_name='Mother Serene' if who=='serene' else 'Tomas',artwork_pixels_per_world_pixel=2,logical_size=[24,36],draw_anchor=[12,30],foot_anchor=[12,34],frames={d:f'idle_{d}.png'for d in ('front','back','left','right')},portrait='portrait.png',portrait_sha256=hashlib.sha256((out/'portrait.png').read_bytes()).hexdigest(),status='candidate')
(out/'design.json').write_text(json.dumps(m,indent=2)+'\n')
h={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(out.rglob('*.png'))}
(out/'sha256.json').write_text(json.dumps(h,indent=2)+'\n')
print(who,len(h),'native outputs')
