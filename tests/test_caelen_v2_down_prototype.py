from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

def test_downward_prototype_dimensions_and_alpha():
    path=ROOT/"assets/source/characters/caelen/v2/caelen_v2_down_prototype.png"
    im=Image.open(path)
    assert im.size==(160,48)
    assert im.mode=="RGBA"
    assert all(im.crop((i*32,0,(i+1)*32,48)).getbbox() for i in range(5))
    assert im.getpixel((0,0))[3]==0
