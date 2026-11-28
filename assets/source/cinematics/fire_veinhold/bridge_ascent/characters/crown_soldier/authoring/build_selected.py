"""Rebuild the selected Crown whole-figure actor inputs, or verify the export."""
from pathlib import Path
import argparse,subprocess,sys
HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check',action='store_true')
args=parser.parse_args()
def run(script,*options):
 subprocess.run([sys.executable,str(HERE/script),*options],check=True)
if not args.check:
 run('extract_register_atlases.py','--names','transition_00_modelv2',
     *[f'transition_{n:02d}' for n in range(1,7)],
     *[f'overhead_{n:02d}' for n in range(3)])
 run('register_minimal_repairs.py')
 run('export_actorperformance.py')
run('export_actorperformance.py','--check')
run('verify_provenance.py')

