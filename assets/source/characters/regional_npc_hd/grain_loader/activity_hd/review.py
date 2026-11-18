"""Reproducible native continuity sheets and source/registration checks."""
from pathlib import Path
from PIL import Image,ImageDraw
import json,hashlib,subprocess,sys,math
S=Path(__file__).parent;ROOT=S.parents[5]
meta=json.loads((ROOT/'assets/characters/regional_npc_hd/grain_loader/activity_hd/manifest.json').read_text())
recipe=json.loads((S/'recipe.json').read_text());out=S/'review';out.mkdir(exist_ok=True)
expected={f['file'] for seq in meta['sequences'].values() for f in seq['frames']}
assert set(recipe['refined_masters'])==expected
for file,ref in recipe['refined_masters'].items():
 p=S/ref['file'];im=Image.open(p);assert im.size==(96,104);assert set(im.getchannel('A').getdata())=={0,255};assert hashlib.sha256(p.read_bytes()).hexdigest()==ref['sha256']
board=Image.new('RGBA',(1000,1260),'#63715f');d=ImageDraw.Draw(board);d.text((10,5),'adult_man_02 identity | native complete activities | no runtime/prop claim',fill='white')
for row,(clip,seq) in enumerate(meta['sequences'].items()):
 y=25+row*72;d.text((0,y),clip,fill='white');face=clip.split('_')[-1];idle=Image.open(S/'identity'/f'idle_{face}.png');c=Image.new('RGBA',(96,104));c.alpha_composite(idle,(24,23));board.alpha_composite(c.crop((0,20,96,104)),(120,y-10))
 frames=[]
 for i,f in enumerate(seq['frames']):
  im=Image.open(S/recipe['refined_masters'][f['file']]['file']);board.alpha_composite(im.crop((0,20,96,104)),(240+i*115,y-10));bg=Image.new('RGBA',(96,104),'#63715f');bg.alpha_composite(im);frames.append(bg.convert('RGB').resize((288,312),Image.Resampling.NEAREST))
 for label,factor in [('normal',1),('half_speed',2)]:frames[0].save(out/f'{clip}_{label}.gif',save_all=True,append_images=frames[1:],duration=[f['duration_ms']*factor for f in seq['frames']],loop=0,disposal=2)
board.save(out/'all_frames_native.png')
board=Image.new('RGBA',(960,480),'#63715f')
for row,face in enumerate(['front','back','left','right']):
 c=Image.new('RGBA',(96,104));c.alpha_composite(Image.open(S/'identity'/f'idle_{face}.png'),(24,23));board.alpha_composite(c,(0,row*120))
 for i,name in enumerate([f'hold_{face}_0.png']+[f'carry_{face}_{n}.png' for n in range(4)]):board.alpha_composite(Image.open(S/'refined_masters'/name),(120+i*130,row*120))
board.save(out/'idle_hold_carry_native.png')
# Diagnostic only: metadata targets are unchanged, and actual prop reach/depth
# is a separate runtime acceptance gate. This does not claim pixel-perfect grip.
gaps=[]
for clip,seq in meta['sequences'].items():
 for f in seq['frames']:
  im=Image.open(S/recipe['refined_masters'][f['file']]['file'])
  skin=[(x,y) for y in range(104) for x in range(96) if im.getpixel((x,y))[:3] in ((232,196,157),(192,141,105)) and im.getpixel((x,y))[3]]
  for hand in f.get('hands',[]):
   target=(48+hand[0]*2,92+hand[1]*2);gap=min(math.dist(p,target) for p in skin)/2;gaps.append({'file':f['file'],'logical_target':hand,'nearest_drawn_skin_gap_logical':round(gap,3)})
(out/'checks.json').write_text(json.dumps({'frames':len(expected),'canvas':[96,104],'anchor':[48,92],'body_origin':[24,23],'hard_alpha':True,'all_source_hashes_match':True,'metadata':'Unchanged staged sequence contract; no export/runtime change in this package','hands_diagnostic':gaps,'runtime_acceptance':'PENDING coordinator actual-game snapshots with separately owned props'},indent=2)+'\n')
print('PASS',len(expected),'native contracts; largest skin-target diagnostic gap',max(g['nearest_drawn_skin_gap_logical'] for g in gaps))
