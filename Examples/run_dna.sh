#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$script_dir/prempni.sh" \
  --complex-type dna \
  --sample-id 2KO0 \
  --protein-sequence MVQSCSAYGCKNRYDKDKPVSFHKFPLTRPSLCKEWEAAVRRKNFKPTKYSSICSEHFTPDSFKRESNNKLLKENAVPTIFLELVPR \
  --mutation A39T \
  --chain DNA_1=GCTTGTGTGGGCAGCG \
  --chain DNA_2=CGCTGCCCACACAAGC
