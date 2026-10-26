#!/usr/bin/env bash
# Run from your working directory; results are saved in ./output.
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p output
output_dir="$(cd output && pwd)"
mounts=(-v "$output_dir:/output" -v "$script_dir:/examples:ro")
if [[ -d input ]]; then
  input_dir="$(cd input && pwd)"
  mounts+=(-v "$input_dir:/input:ro")
fi
exec docker run --rm "${mounts[@]}" ghcr.io/minghuilab/prempni "$@"
