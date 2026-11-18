"""Reproduce/validate these literal native worker drawings (source-only, no Game).

Use --repo-root PATH to select the repository containing approved adult_man_03.
--check validates SHA, all original palm cues, exact directional head pixels,
sole bounds, hard alpha, and complete sequence coverage without writing.
"""
import argparse,hashlib,json,io
from pathlib import Path
from PIL import Image,ImageDraw
SOURCE=Path(__file__).resolve().parent

def draw(plan,base):
 im=Image.new('RGBA',(96,104));ox,oy=plan['origin']
 if plan['native_leg_source']:
  with Image.open(base/plan['native_leg_source']) as raw:im.alpha_composite(raw.convert('RGBA').crop((0,44,48,72)),(ox,oy+44))
 d=ImageDraw.Draw(im)
 for s in plan['shapes']:
  points=[(x+ox,y+oy) for x,y in s['points']]
  if s.get('line'):d.line(points,fill=s['fill'])
  else:d.polygon(points,fill=s['fill'],outline=s.get('outline'))
 with Image.open(base/f"idle_{plan['face']}.png") as raw:head=raw.convert('RGBA').crop((0,0,48,28))
 dx,dy=plan['head_shift'];im.alpha_composite(head,(ox+dx,oy+dy));return im

def run(root,check=True):
 data=json.loads((SOURCE/'recipe.json').read_text());base=root/'assets/characters/npc_roster_hd/adult_man_03'
 records=data['refinement']['sequence_frame_contract'];expected={f['file']:f for seq in records.values() for f in seq['frames']}
 assert set(data['refined_masters'])==set(expected)==set(data['native_drawings'])
 for filename,sha in data['refinement']['approved_source_sha256'].items():assert hashlib.sha256((base/filename).read_bytes()).hexdigest()==sha,filename
 for name,r in data['refined_masters'].items():
  im=draw(data['native_drawings'][name],base);path=SOURCE/r['file'];buffer=io.BytesIO();im.save(buffer,format='PNG');raw=buffer.getvalue()
  assert hashlib.sha256(raw).hexdigest()==r['sha256'],('source recipe differs',name)
  if check:assert path.read_bytes()==raw,('master differs',name)
  else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
  assert im.size==(96,104);assert set(im.getchannel('A').tobytes())=={0,255}
  for x,y in expected[name].get('hands',[]):assert im.getpixel((48+x*2,92+y*2))[:3] in ((232,196,157),(237,175,120)),('palm',name,x,y)
  plan=data['native_drawings'][name];dx,dy=plan['head_shift'];crop=im.crop((24+dx,23+dy,72+dx,51+dy))
  with Image.open(base/f"idle_{plan['face']}.png") as img:head=img.convert('RGBA').crop((0,0,48,28))
  a=head.tobytes();b=crop.tobytes();assert all(a[i:i+4]==b[i:i+4] for i in range(0,len(a),4) if a[i+3]),('head',name)
  assert im.getbbox()[3]<=93,('sole',name)
 print(f"Verified {len(expected)} exact native source bodies, directional heads and original hand cues; no Game initialized.")
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo-root',type=Path,required=True);p.add_argument('--check',action='store_true');args=p.parse_args();run(args.repo_root,args.check)
