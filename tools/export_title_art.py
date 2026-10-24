"""Export the generated dawn illustration to the title renderer's canvas."""
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def build():
    source=ROOT/'assets/source/ui/title/eldenmere_dawn.png'
    image=Image.open(source).convert('RGB')
    width,height=image.size
    if width/height>16/9:
        extent=round(height*16/9);left=(width-extent)//2
        image=image.crop((left,0,left+extent,height))
    else:
        extent=round(width*9/16);top=(height-extent)//2
        image=image.crop((0,top,width,top+extent))
    output=ROOT/'assets/ui/title/eldenmere_dawn.png'
    output.parent.mkdir(parents=True,exist_ok=True)
    image.resize((640,360),Image.Resampling.NEAREST).save(output)
    print('Exported',output.relative_to(ROOT))


if __name__=='__main__':build()
