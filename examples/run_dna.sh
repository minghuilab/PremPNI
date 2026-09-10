#!/usr/bin/env bash
set -euo pipefail
mkdir -p output
docker run --rm --gpus all \
  -v "$PWD/output:/output" \
  ghcr.io/minghuilab/prempni:v0.1.1 \
  --complex-type dna \
  --sample-id 2KO0 \
  --protein-sequence MVQSCSAYGCKNRYDKDKPVSFHKFPLTRPSLCKEWEAAVRRKNFKPTKYSSICSEHFTPDSFKRESNNKLLKENAVPTIFLELVPR \
  --mutation A39T \
  --chain DNA_1=GCTTGTGTGGGCAGCG \
  --chain DNA_2=CGCTGCCCACACAAGC \
  --protein-device cuda:0 \
  --na-device cuda:0 \
  --mlp-device cuda:0
