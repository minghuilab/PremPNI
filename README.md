# PremPNI

## About

PremPNI is a sequence-based predictor for mutation-induced changes in
protein-DNA and protein-RNA interactions. It requires only a wild-type
protein sequence, one or more nucleic-acid chains, and a single-site protein
mutation. No three-dimensional complex structure is required.

PremPNI predicts whether the mutation is **stabilizing** or **destabilizing**
and quantitatively estimates the resulting change in binding affinity,
reported as ΔΔG (kcal/mol). The Docker image includes the complete embedding
and prediction workflow so that users can run PremPNI directly from sequence
inputs.

## PremPNI Installation and Usage Instructions

### 1. Download the public Docker image

The PremPNI Docker image is publicly available from the GitHub Container
Registry. No GitHub account or access token is required to pull the image:

```bash
docker pull ghcr.io/minghuilab/prempni:v0.1.1
```

The image contains all embedding models and final prediction weights. No
additional model download or Hugging Face account is required.

### 2. Input

Each prediction requires:

- one wild-type protein sequence;
- one or more nucleic-acid chains;
- one single-site protein mutation in one-based notation, such as `A10V`.

Input rules:

- Protein sequences may contain only the 20 standard amino-acid letters.
- The reference residue in the mutation must match the protein sequence.
- DNA accepts `A`, `C`, `G`, and `T`.
- RNA accepts `A`, `C`, `G`, and `U`.
- Every nucleic-acid chain must be supplied in the 5-prime to 3-prime direction.
- Repeat `--chain` for multiple chains. For example, a two-chain DNA input
  uses `DNA_1=...` and `DNA_2=...`.

### 3. Run a prediction

Create a local directory for results:

```bash
mkdir -p output
```

#### Protein-DNA prediction

```bash
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

#### Protein-RNA prediction

```bash
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

The models are loaded sequentially, so one GPU can run both tasks.

### 4. Output

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

The prediction files contain the final ensemble ΔΔG value in kcal/mol, the
stability classification, input lengths, and wall-clock times for protein
embedding, nucleic-acid embedding, MLP prediction, and the complete run. A
non-negative ΔΔG is classified as **destabilizing mutation**; a negative ΔΔG
is classified as **stabilizing mutation**.

## Recommended System Requirements

- Linux x86_64
- Docker Engine ≥ 24
- NVIDIA driver compatible with CUDA 11.7
- NVIDIA Container Toolkit
- ≥ 30 GB free disk space
- ≥ 32 GB RAM (64 GB recommended for RNA prediction)
- NVIDIA GPU:
  - DNA: ≥ 8 GB VRAM
  - RNA: ≥ 16 GB VRAM

## Citation

The PremPNI article has not yet been published. Citation information and the
DOI will be added after publication. Until then, acknowledge PremPNI and the
Minghui Li Research Group in derived academic work.

## License

PremPNI is available for academic, non-commercial use only. See
[LICENSE](LICENSE). Third-party components retain their original licenses; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
