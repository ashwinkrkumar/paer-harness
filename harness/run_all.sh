#!/usr/bin/env bash
# Usage: bash run_all.sh <reuters_dir> <results_dir> <figures_dir>
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
PKG=$(cd "$HERE/.." && pwd)
ROOT=${1:-$PKG/data/reuters}
RES=${2:-$PKG/results}
FIG=${3:-$PKG/figures}
mkdir -p "$RES" "$FIG"

echo "== Experiment A: mirrored synthetic benchmark"
python3 -c "
import json, sys
sys.path.insert(0, '$HERE')
from paer import synthetic
json.dump(synthetic.run(), open('$RES/expA_synthetic.json', 'w'), indent=2)
"
echo "== Experiments B and C: Reuters-21578, two retrievers, existence oracle"
python3 "$HERE/run_reuters.py" --root "$ROOT" --out "$RES"
echo "== Experiment D: revocation lag replay"
python3 "$HERE/run_revocation.py" --root "$ROOT" --out "$RES"
echo "== Experiment E: vector-index cost"
python3 "$HERE/run_latency.py" --root "$ROOT" --out "$RES"
echo "== Figures"
python3 "$HERE/make_figures.py" "$RES" "$FIG"
echo "done"
