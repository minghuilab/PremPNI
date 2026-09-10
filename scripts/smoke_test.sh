#!/usr/bin/env bash
set -euo pipefail
image="${1:-ghcr.io/minghuilab/prempni:v0.2.0}"
output_dir="${2:-$PWD/output}"
mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd)"
run_dir="$(mktemp -d "$output_dir/smoke.XXXXXX")"
docker run --rm --network none -v "$run_dir:/output" "$image" \
  --input-tsv /opt/prempni/examples/PremPNI_complexes_example.tsv
python - "$run_dir" <<'PY'
import csv
import json
import math
import sys
from pathlib import Path
paths = list(Path(sys.argv[1]).glob("collections/*/prempni_prediction.json"))
assert len(paths) == 1, paths
payload = json.loads(paths[0].read_text(encoding="utf-8"))
assert payload["status"] == "completed"
expected = {"2KO0": ("PremPDI2", 0.5487042168776194), "1AUD": ("PremPRI2", 0.9141754706700643)}
assert len(payload["results"]) == 2
for item in payload["results"]:
    model, target = expected[item["sample_id"]]
    row = item["predictions"][0]
    assert item["predictor"] == model
    assert math.isclose(row["mean_ddg"], target, abs_tol=1e-5, rel_tol=0)
    assert row["classification"] == "Destabilizing"
    assert "model_predictions" not in item
with paths[0].with_suffix(".csv").open(encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))
assert [r["ddg_kcal_mol"] for r in rows] == ["0.549", "0.914"]
print("CPU website-example regression passed.")
PY
