#!/usr/bin/env bash

set -euo pipefail

image="${1:-ghcr.io/minghuilab/prempni:latest}"
output_dir="${2:-$PWD/output}"
mkdir -p "$output_dir"

docker run --rm --gpus all \
  -v "$output_dir:/output" \
  "$image" \
  --complex-type dna \
  --sample-id DNA_demo \
  --protein-sequence MKTAYIAKQRQISFVKSHFSRQDILDLIC \
  --mutation M1V \
  --chain DNA_1=ACGTACGT \
  --chain DNA_2=TGCATGCA \
  --protein-device cuda:0 \
  --na-device cuda:0 \
  --mlp-device cuda:0 \
  --overwrite

test -s "$output_dir/protein_dna/DNA_demo/prediction/prempni_prediction.json"

docker run --rm --gpus all \
  -v "$output_dir:/output" \
  "$image" \
  --complex-type rna \
  --sample-id RNA_demo \
  --protein-sequence MGSSHHHHHHSSGLVPRGSHMASMTGGQQMGRGSRHVGNRANPDPNCCLGVFGLSLYTTERDLREVFSKYGPIADVSIVYDQQSRRSRGFAFVYFENVDDAKEAKERANGMELDGRRIRVDFSITKRPH \
  --mutation R119A \
  --chain RNA_1=AAGAAC \
  --protein-device cuda:0 \
  --na-device cuda:1 \
  --mlp-device cuda:0 \
  --overwrite

test -s "$output_dir/protein_rna/RNA_demo/prediction/prempni_prediction.json"

python - "$output_dir" <<'PY'
import json
import math
import sys
from pathlib import Path

root = Path(sys.argv[1])
expected = {
    root / "protein_dna/DNA_demo/prediction/prempni_prediction.json": 0.117677,
    root / "protein_rna/RNA_demo/prediction/prempni_prediction.json": 0.906902,
}
for path, target in expected.items():
    payload = json.loads(path.read_text(encoding="utf-8"))
    actual = float(payload["mean_ddg"])
    if not math.isclose(actual, target, rel_tol=0.0, abs_tol=1e-5):
        raise SystemExit(f"Unexpected prediction in {path}: {actual} != {target}")
    if "model_predictions" in payload:
        raise SystemExit(f"Single-model predictions must not be exposed: {path}")
print("PremPNI DNA and RNA predictions match the validated references.")
PY

echo "PremPNI Docker smoke tests passed."
