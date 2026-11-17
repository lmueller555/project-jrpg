"""Reproduce settlement build contracts without rebuilding or modifying the town."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.eldenmere_settlement import framework, MANIFEST, RECIPE


def build(check=False):
    town = json.loads((ROOT/'assets/maps/eldenmere/playable/map.json').read_text())
    source = json.loads((ROOT/'assets/source/maps/eldenmere/town_hd/recipe.json').read_text())
    report = framework(ROOT, town, source.get('settlement_recipe', RECIPE))
    raw = (json.dumps(report, indent=2)+'\n').encode()
    target = ROOT/MANIFEST
    if check:
        if not target.exists() or target.read_bytes() != raw:
            raise SystemExit('Stale settlement framework: '+MANIFEST)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    print(f'{"Verified" if check else "Built"} settlement framework: '
          f'{len(report["protected_spaces"])} protected spaces, '
          f'{len(report["inventory"]["assets"])} semantic asset records; '
          f'{report["active_ground_treatments"]} ground treatments, zero prop placements')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
