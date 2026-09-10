#!/usr/bin/env bash
set -euo pipefail
mkdir -p output
docker run --rm \
  -e OMP_NUM_THREADS=8 -e MKL_NUM_THREADS=8 \
  -v "$PWD/output:/output" \
  ghcr.io/minghuilab/prempni:v0.1.1 \
  --complex-type dna \
  --sample-id 2KO0 \
  --protein-sequence MVQSCSAYGCKNRYDKDKPVSFHKFPLTRPSLCKEWEAAVRRKNFKPTKYSSICSEHFTPDSFKRESNNKLLKENAVPTIFLELVPR \
  --mutation A39T \
  --chain DNA_1=GCTTGTGTGGGCAGCG \
  --chain DNA_2=CGCTGCCCACACAAGC \
  --protein-device cpu \
  --na-device cpu \
  --mlp-device cpu
