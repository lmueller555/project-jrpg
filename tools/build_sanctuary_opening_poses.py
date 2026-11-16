"""Restore unchanged Tomas/prop exports and rebuild drawn HD Caelan poses."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
def build():
    source=ROOT/'assets/source/story/sanctuary_opening/retained_household'
    output=ROOT/'assets/story/sanctuary_opening/poses'
    for path in source.rglob('*'):
        if path.is_file():
            target=output/path.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
    try:from tools.export_caelan_scene_actions_hd import build as caelan
    except ModuleNotFoundError:from export_caelan_scene_actions_hd import build as caelan
    caelan()
if __name__=='__main__':build()
