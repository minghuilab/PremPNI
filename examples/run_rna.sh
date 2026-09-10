#!/usr/bin/env bash
set -euo pipefail
mkdir -p output
docker run --rm --gpus all \
  -v "$PWD/output:/output" \
  ghcr.io/minghuilab/prempni:v0.1.1 \
  --complex-type rna \
  --sample-id 1AUD \
  --protein-sequence AVPETRPNHTIYINNLNEKIKKDELKKSLHAIFSRFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFV \
  --mutation K49A \
  --chain RNA_1=GGCAGAGUCCUUCGGGACAUUGCACCUGCC \
  --protein-device cuda:0 \
  --na-device cuda:0 \
  --mlp-device cuda:0
