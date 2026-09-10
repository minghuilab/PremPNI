#!/usr/bin/env bash
set -euo pipefail
mkdir -p output
docker run --rm \
  -e OMP_NUM_THREADS=8 -e MKL_NUM_THREADS=8 \
  -v "$PWD/output:/output" \
  ghcr.io/minghuilab/prempni:v0.1.1 \
  --complex-type rna \
  --sample-id 1AUD \
  --protein-sequence AVPETRPNHTIYINNLNEKIKKDELKKSLHAIFSRFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFV \
  --mutation K49A \
  --chain RNA_1=GGCAGAGUCCUUCGGGACAUUGCACCUGCC \
  --protein-device cpu \
  --na-device cpu \
  --mlp-device cpu
