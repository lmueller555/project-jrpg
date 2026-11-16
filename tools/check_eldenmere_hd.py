"""Run the town migration's asset, gameplay, quest and save regression checks.

Scene fixtures own substantial native surfaces. Collect between cases so a full
review run does not retain discarded Game cycles until Python's later generation.
"""
import argparse
import gc
import json
import os
from pathlib import Path
import sys
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
MODULES=('test_eldenmere_hd_integration','test_rendering','test_interactive_grass',
         'test_world_grass','test_eldenmere_grass','test_upstream_grass','test_doors',
         'test_school','test_game','test_map_ui','test_world_map_viewer','test_school_world_map',
         'test_sanctuary_courtyard_hd','test_sanctuary_home_hd','test_sanctuary_dining_hd',
         'test_gardener','test_well_drawing','test_halden_visit','test_elira_visit',
         'test_venn_visit','test_mill_quest','test_lantern_quest','test_lantern_rest',
         'test_lantern_finish','test_lantern_village','test_liam_blocks',
         'test_daisy_routines','test_bed_rest','test_caelan_scene_actions_hd',
         'test_caelan_pickup_continuity','test_save_system_gameplay','test_save_game',
         'test_save_library')
class ReviewResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.passed=[]
    def addSuccess(self,test):super().addSuccess(test);self.passed.append(test.id())
    def stopTest(self,test):super().stopTest(test);gc.collect()
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('modules',nargs='*');parser.add_argument('--report',type=Path);args=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromNames(args.modules or MODULES)
    result=unittest.TextTestRunner(verbosity=2,resultclass=ReviewResult).run(suite)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps({'tests_run':result.testsRun,'passed':result.passed,'failures':[{'test':test.id(),'traceback':trace} for test,trace in result.failures],'errors':[{'test':test.id(),'traceback':trace} for test,trace in result.errors],'skipped':[{'test':test.id(),'reason':reason} for test,reason in result.skipped]},indent=2)+'\n')
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
