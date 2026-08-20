# PremPNI

PremPNI predicts mutation-induced binding-affinity changes for protein-DNA and
protein-RNA interactions directly from sequence. The input consists of a
wild-type protein sequence, one or more nucleic-acid chains, and a single-site
protein mutation. No three-dimensional complex structure is required.

This private repository accompanies the complete GPU-enabled Docker image. The
image contains the embedding models and the two final PremPNI ensembles:

- PremPDI2: three Protein-DNA MLP predictors combined by arithmetic mean;
- PremPRI2: three Protein-RNA MLP predictors combined by arithmetic mean.

## Requirements

- Linux x86_64;
- Docker Engine 24 or newer;
- NVIDIA driver compatible with CUDA 11.7;
- NVIDIA Container Toolkit;
- at least 30 GB free disk space for the image and outputs;
- at least 32 GB system RAM; 64 GB is recommended for Protein-RNA prediction;
- an NVIDIA GPU with at least 8 GB VRAM for DNA prediction. A GPU with at
  least 16 GB VRAM is recommended for RNA prediction; otherwise the ESM-2 3B
  protein stage automatically falls back to CPU and runs more slowly.

The models are loaded sequentially, so one GPU can run both tasks. Two GPUs may
be selected independently with `--protein-device` and `--na-device`.

## Obtain the private image

Ask the repository owner for access to the private repository and package.
Create a GitHub token with `read:packages`, then authenticate without placing
the token directly in shell history:

```bash
export CR_PAT='YOUR_GITHUB_TOKEN'
echo "$CR_PAT" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
unset CR_PAT
docker pull ghcr.io/minghuilab/prempni:v0.1.1
```

## Protein-DNA example

```bash
mkdir -p output
docker run --rm --gpus all \
  -v "$PWD/output:/output" \
  ghcr.io/minghuilab/prempni:v0.1.1 \
  --complex-type dna \
  --sample-id DNA_demo \
  --protein-sequence MKTAYIAKQRQISFVKSHFSRQDILDLIC \
  --mutation M1V \
  --chain DNA_1=ACGTACGT \
  --chain DNA_2=TGCATGCA \
  --protein-device cuda:0 \
  --na-device cuda:0 \
  --mlp-device cuda:0
```

## Protein-RNA example

```bash
mkdir -p output
docker run --rm --gpus all \
  -v "$PWD/output:/output" \
  ghcr.io/minghuilab/prempni:v0.1.1 \
  --complex-type rna \
  --sample-id RNA_demo \
  --protein-sequence MKTAYIAKQRQISFVKSHFSRQDILDLIC \
  --mutation M1V \
  --chain RNA_1=AAGAAC \
  --protein-device cuda:0 \
  --na-device cuda:0 \
  --mlp-device cuda:0
```

For a two-GPU system, set `--na-device cuda:1` to place the nucleic-acid model
on the second GPU. Repeat `--chain` for every nucleic-acid chain. Every chain
must be supplied in the 5-prime to 3-prime direction.

## Input rules

- Protein sequences may contain only the 20 standard amino-acid letters.
- Mutations use one-based notation such as `A10V`; the reference residue must
  match the input protein sequence.
- DNA accepts A, C, G, and T.
- RNA accepts A, C, G, and U.
- Sample and chain identifiers may contain letters, digits, `.`, `_`, and `-`.

## Output

Results are written beneath the mounted `/output` directory:

```text
output/
  protein_dna/ or protein_rna/
    SAMPLE_ID/
      embeddings/
      protein_metadata.json
      dna_metadata.json or rna_metadata.json
      prediction/
        prempni_prediction.json
        prempni_prediction.csv
```

The prediction files contain the ensemble DDG value in kcal/mol, stability
classification, input lengths, and wall-clock times for protein embedding,
nucleic-acid embedding, MLP prediction, and the complete run. A non-negative
DDG is classified as destabilizing; a negative DDG is classified as
stabilizing.

## Citation

The PremPNI article has not yet been published. Citation information and the
DOI will be added after publication. Until then, acknowledge PremPNI, Weikang
Sun, and the Minghui Li Research Group in derived academic work.

## License

PremPNI is available for academic, non-commercial use only. See [LICENSE](LICENSE).
Third-party components retain their original licenses; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Maintainer build notes

The Git repository intentionally excludes `models/` and
`runtime-env.tar.gz`, because GitHub rejects files larger than 100 MB. The
private GHCR image contains these assets. Before building, an authorized
maintainer stages the verified model tree and packed Python runtime beside the
Dockerfile, generates `MODEL_MANIFEST.sha256`, and runs:

```bash
docker build \
  --build-arg PREMPNI_VERSION=0.1.1 \
  -t ghcr.io/minghuilab/prempni:v0.1.1 \
  -t ghcr.io/minghuilab/prempni:latest .
```

Every release must pass one Protein-DNA and one Protein-RNA end-to-end smoke
test before it is pushed.
