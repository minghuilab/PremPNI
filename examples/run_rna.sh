#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$script_dir/../software/scripts/prempni.sh" \
  --complex-type rna \
  --sample-id 1AUD \
  --protein-sequence AVPETRPNHTIYINNLNEKIKKDELKKSLHAIFSRFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFV \
  --mutation K49A \
  --chain RNA_1=GGCAGAGUCCUUCGGGACAUUGCACCUGCC
