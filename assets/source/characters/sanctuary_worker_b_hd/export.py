"""Technical, uniform sampling of complete authored drawings; no body transforms."""
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[4]
SOURCE=Path(__file__).parent
OUT=ROOT/'assets/characters/named_hd/sanctuary_worker_b'

def export(include_activity=False):
    im=Image.open(SOURCE/'master.png').convert('RGBA')
    # Five separated authored drawings; remove generation's partial-alpha fringe.
    alpha=im.getchannel('A').point(lambda a:255 if a>=190 else 0)
    im.putalpha(alpha)
    ranges=[(0,350),(350,750),(750,1150),(1150,1530),(1530,im.width)]
    crops=[im.crop((a,0,b,im.height)) for a,b in ranges]
    crops=[p.crop(p.getbbox()) for p in crops]
    factor=60/crops[0].height
    OUT.mkdir(parents=True,exist_ok=True)
    for name,p in zip(['idle_front','idle_back','idle_left','idle_right','injured'],crops):
        if name=='injured' and not include_activity:continue
        p=p.resize((round(p.width*factor),round(p.height*factor)),Image.Resampling.NEAREST)
        canvas=Image.new('RGBA',(64 if name=='injured' else 48,72))
        canvas.alpha_composite(p,((canvas.width-p.width)//2,68-p.height))
        canvas.save(OUT/f'{name}.png')
if __name__=='__main__':
    import sys
    export('--activity' in sys.argv)
