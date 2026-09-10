# PremPNI

PremPNI predicts mutation-induced changes in protein–DNA and protein–RNA binding affinity from a wild-type protein sequence, nucleic-acid sequences and a single-site protein mutation. No three-dimensional complex structure is required. Predictions are ΔΔG values in kcal/mol.

Use the [PremPNI web server](https://lilab.jysw.suda.edu.cn/research/PremPNI/) or the standalone Docker workflow below.

## Website and model correspondence

| Interaction | Website result column | Protein embedding | Nucleic-acid embedding | Prediction |
| --- | --- | --- | --- | --- |
| Protein–DNA | PremPDI2 | ESM-DBP | HyenaDNA | Mean of three final MLP predictions |
| Protein–RNA | PremPRI2 | ESM-2 3B | RiNALMo | Mean of three final MLP predictions |

The public output reports the final ensemble value. Negative ΔΔG means **Stabilizing**; zero or positive ΔΔG means **Destabilizing**. Classification uses the unrounded value. The website displays and exports three decimal places; Docker JSON/CSV retains numeric precision and uses the labels `stabilizing mutation` / `destabilizing mutation`.

The website provides job tracking, mutation lists, alanine scanning and multi-complex submissions. This repository distributes standalone inference, not the website application. See [website parity and scope](docs/website-parity.md).

## Install

The documented image release is `v0.1.1`:

```bash
docker pull ghcr.io/minghuilab/prempni:v0.1.1
docker run --rm ghcr.io/minghuilab/prempni:v0.1.1 --help
```

The published image includes the runtime, embedding models and prediction weights. The project documents anonymous access to the image; no separate Hugging Face model download is needed. See [installation, model verification and troubleshooting](docs/installation.md) for CPU memory requirements and source-build limitations.

## Input

- Supply a wild-type protein sequence using the 20 standard amino acids.
- Use a **one-based position in that exact sequence**, for example `A39T`; the wild-type letter must match.
- DNA accepts A/C/G/T; RNA accepts A/C/G/U.
- Supply each nucleic-acid chain in the 5′→3′ direction; repeat `--chain` for multiple chains.
- Use a distinct sample ID for each run. Existing output is protected unless `--overwrite` is supplied.

The examples below match the website's Load example and downloadable files: **2KO0 / A39T** (87 aa, two 16 nt DNA chains) and **1AUD / K49A** (101 aa, one 30 nt RNA chain). They are input examples; no predicted values are fabricated.

## Run

Commands below run entirely on CPU using Bash on Linux (or a configured WSL2 Docker environment). No GPU, NVIDIA driver or NVIDIA Container Toolkit is required. Keep all three `--*-device cpu` options: the existing image defaults to CUDA for its embedding stages. The image includes CUDA libraries, but CPU execution does not require GPU hardware.

```bash
mkdir -p output
```

### Protein–DNA

```bash
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
```

### Protein–RNA

```bash
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
```

The same commands are available as `bash examples/run_dna.sh` and `bash examples/run_rna.sh` after cloning this repository. See [example formats](examples/README.md).

## Output

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

The final result contains `mean_ddg`, `classification`, input lengths and wall-clock timings for protein embedding, nucleic-acid embedding, MLP prediction and the total run. Timings include model loading. Website queue time and standalone runtime are different measurements.

## Datasets

Download the author-provided [PremPNI curated workbook](datasets/PremPNI_curated_datasets.xlsx), or use the lossless UTF-8 TSV exports below:

| Dataset | Interaction | Records | Contents |
| --- | --- | ---: | --- |
| [S1664](datasets/S1664.tsv) | Protein–DNA | 1,664 | Mutation, protein and DNA sequences, experimental DDG |
| [S1150](datasets/S1150.tsv) | Protein–RNA | 1,150 | Mutation, protein and RNA sequences, experimental DDG |
| [S1336](datasets/S1336.tsv) | Protein–DNA | 1,336 | PDB mutation identifier, experimental DDG, PremPDI2 prediction |
| [S599](datasets/S599.tsv) | Protein–RNA | 599 | PDB mutation identifier, experimental DDG, PremPRI2 prediction |

The four sheets contain 4,749 rows in total; this is not a claim that all rows are independent or non-overlapping. Experimental labels and supplied predictions are distinct columns. See the [dataset schema, provenance and reuse notes](datasets/README.md) and [checksums](datasets/manifest.json).

## Citation

The PremPNI article citation and DOI will be added after publication. Until then, acknowledge PremPNI and the Minghui Li Research Group in derived academic work.

## License

PremPNI is available for academic, non-commercial use only. See [LICENSE](LICENSE). Third-party components retain their original licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
