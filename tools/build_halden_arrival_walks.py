"""Rebuild the miller's four walking directions from his established costume."""
from pathlib import Path
from PIL import Image
from build_halden_visit import miller
ROOT=Path(__file__).resolve().parents[1]

def shift(im,dy):
    out=Image.new('RGBA',im.size);out.alpha_composite(im,(0,dy));return out

def build():
    for direction in ('front','left','right','back'):
        for i in range(4):
            frame=Image.open(ROOT/f'assets/characters/npcs/male_01/walk_{direction}/frame_{i+1:02}.png').convert('RGBA')
            dy=-1 if i%2 else 0
            # Align the approved costume overlays at idle height, then bob together.
            posed=shift(miller(shift(frame,-dy),direction),dy)
            posed.save(ROOT/f'assets/story/halden/walk_{direction}_{i}.png')
if __name__=='__main__':build()
