# PremPNI

PremPNI predicts mutation-induced changes in protein–DNA and protein–RNA binding affinity from a wild-type protein sequence, nucleic-acid sequences and a single-site protein mutation. No three-dimensional complex structure is required. Predictions are ΔΔG values in kcal/mol.

Use the [PremPNI web server](https://lilab.jysw.suda.edu.cn/research/PremPNI/) or the standalone Docker workflow below.

## Website and model correspondence

| Interaction | Website result column | Protein embedding | Nucleic-acid embedding | Prediction |
| --- | --- | --- | --- | --- |
| Protein–DNA | PremPDI2 | ESM-DBP | HyenaDNA | Mean of three final MLP predictions |
| Protein–RNA | PremPRI2 | ESM-2 3B | RiNALMo | Mean of three final MLP predictions |

The public output reports the final ensemble value under the model name **PremPDI2** or **PremPRI2**. Negative ΔΔG means **Stabilizing**; zero or positive ΔΔG means **Destabilizing**. The website and Docker console/CSV show three decimal places and classify the unrounded value. JSON retains raw `mean_ddg` and provides a three-decimal `prediction_display`.

Both interfaces support single mutations, mutation lists, alanine scanning and multi-complex input. Docker records local Job IDs, timestamps, progress and final results. See [website parity and scope](docs/website-parity.md).

## Install

The documented image release is `v0.2.0`:

```bash
docker pull ghcr.io/minghuilab/prempni:v0.2.0
docker run --rm ghcr.io/minghuilab/prempni:v0.2.0 --help
```

The image includes the runtime, embedding models and prediction weights; no separate Hugging Face model download is needed. The GHCR package is currently private pending administrator publication. Downloading it currently requires a GitHub account with package access and `docker login ghcr.io`. Anonymous downloads will be available only after the administrator makes the package public. See [installation, model verification and troubleshooting](docs/installation.md) for CPU memory requirements and source-build limitations.

## Input

- Supply a wild-type protein sequence using the 20 standard amino acids.
- Use a **one-based position in that exact sequence**, for example `A39T`; the wild-type letter must match.
- DNA accepts A/C/G/T; RNA accepts A/C/G/U.
- Supply each nucleic-acid chain in the 5′→3′ direction; repeat `--chain` for multiple chains.
- Use a distinct sample ID for each run. Existing output is protected unless `--overwrite` is supplied.

The examples below match the website's Load example and downloadable files: **2KO0 / A39T** (87 aa, two 16 nt DNA chains) and **1AUD / K49A** (101 aa, one 30 nt RNA chain). They are input examples; no predicted values are fabricated.

## Run

The v0.2.0 image defaults to CPU for all stages, with eight CPU threads. Commands below use Bash on Linux (or a configured WSL2 Docker environment). No GPU, NVIDIA driver or NVIDIA Container Toolkit is required; no device flags are needed. The image reuses the verified runtime, which includes CUDA libraries, but CPU execution does not require GPU hardware.

```bash
mkdir -p output
```

### Protein–DNA

```bash
docker run --rm \
  -e OMP_NUM_THREADS=8 -e MKL_NUM_THREADS=8 \
  -v "$PWD/output:/output" \
  ghcr.io/minghuilab/prempni:v0.2.0 \
  --complex-type dna \
  --sample-id 2KO0 \
  --protein-sequence MVQSCSAYGCKNRYDKDKPVSFHKFPLTRPSLCKEWEAAVRRKNFKPTKYSSICSEHFTPDSFKRESNNKLLKENAVPTIFLELVPR \
  --mutation A39T \
  --chain DNA_1=GCTTGTGTGGGCAGCG \
  --chain DNA_2=CGCTGCCCACACAAGC
```

### Protein–RNA

```bash
docker run --rm \
  -e OMP_NUM_THREADS=8 -e MKL_NUM_THREADS=8 \
  -v "$PWD/output:/output" \
  ghcr.io/minghuilab/prempni:v0.2.0 \
  --complex-type rna \
  --sample-id 1AUD \
  --protein-sequence AVPETRPNHTIYINNLNEKIKKDELKKSLHAIFSRFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFV \
  --mutation K49A \
  --chain RNA_1=GGCAGAGUCCUUCGGGACAUUGCACCUGCC
```

The same commands are available as `bash examples/run_dna.sh` and `bash examples/run_rna.sh` after cloning this repository. See [example formats](examples/README.md).

## Lists, scanning and file inputs

For one protein complex, replace `--mutation A39T` with **one** of:

- `--mutations 'A39T|A39V'` for independent mutations, preserving input order;
- `--mutation-file /input/mutations.txt` for website-style TXT/CSV/TSV lists (mount the containing directory as `/input`);
- `--alanine-scan` for one XnA row at every protein position. Existing alanines produce `0.000`, Destabilizing, `computed=false`, without model computation.

Use the same downloadable JSON or five-column TSV as the website:

```bash
docker run --rm -v "$PWD/output:/output" \
  ghcr.io/minghuilab/prempni:v0.2.0 \
  --input-tsv /opt/prempni/examples/PremPNI_complexes_example.tsv

docker run --rm -v "$PWD/output:/output" \
  ghcr.io/minghuilab/prempni:v0.2.0 \
  --input-json /opt/prempni/examples/prempni_dna_example.json
```

For your own files, mount `-v "$PWD/input:/input:ro"` and use `--input-tsv /input/complexes.tsv` or `--input-json /input/request.json`. JSON accepts a single website request, an array of requests, or `{ "samples": [...] }`. Input file modes cannot be mixed with individual sequence flags. Every input is validated before model computation starts.

## Output

Single-complex runs save under `output/protein_dna/SAMPLE_ID/prediction/` or `output/protein_rna/SAMPLE_ID/prediction/`. Collections save under `output/collections/JOB_ID/`. Each contains:

```text
job.json                    # local Job ID, status, timestamps and progress
prempni_prediction.json      # full input, raw final predictions and timings
prempni_prediction.csv       # website-compatible columns and three decimals
```

Single-complex CSV uses the website's result export columns, including predictor, full sequences, mutation, predicted effect, processing time and computed flag. Collection CSV uses the website's collection export columns. JSON retains full numeric precision; failures retain the input and error, with no prediction or classification. The process exits 0 on success, 1 for inference failures, or 2 for invalid inputs/output conflicts. A failed mutation does not erase completed rows.

Model stages run locally and mutations are processed sequentially in isolated subprocesses; this favors bounded memory and consistent results over the website worker's batch throughput. Large scans can take considerable time. Intermediate embeddings are temporary. Job IDs are local to the mounted output directory and cannot be looked up on the public website. A `.running` file prevents concurrent writes to the same sample; after an ungraceful termination, check that no process is using that output before removing a stale lock and rerunning.

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
