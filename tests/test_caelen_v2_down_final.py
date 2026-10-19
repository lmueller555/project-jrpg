from pathlib import Path
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
ASSET=ROOT/"assets/atlases/characters/caelen_v2_down.png"

def test_production_strip_geometry_alpha_and_clean_bounds():
    image=Image.open(ASSET)
    assert image.format=="PNG"
    assert image.mode=="RGBA" and image.size==(160,48)
    for frame in range(5):
        tile=image.crop((32*frame,0,32*(frame+1),48))
        bounds=tile.getchannel("A").getbbox()
        assert bounds is not None and bounds[0]>0 and bounds[2]<32
        assert bounds[1]>0 and bounds[3]<=47
        assert tile.getpixel((0,0))[3]==0

def test_distinct_walk_poses_and_consistent_foot_baseline():
    image=Image.open(ASSET)
    frames=[image.crop((i*32,0,(i+1)*32,48)) for i in range(5)]
    assert all(ImageChops.difference(frames[i].convert('RGB'),frames[j].convert('RGB')).getbbox()
               for i in range(5) for j in range(i+1,5))
    assert all(tile.getchannel("A").getbbox()[3]==47 for tile in frames)
