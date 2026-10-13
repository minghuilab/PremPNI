# PremPNI

PremPNI predicts mutation-induced changes in protein–DNA and protein–RNA binding affinity from a wild-type protein sequence, nucleic-acid sequences and a single-site protein mutation. No three-dimensional complex structure is required. Predictions are ΔΔG values in kcal/mol.

Use the [PremPNI web server](https://lilab.jysw.suda.edu.cn/research/PremPNI/) or the standalone Docker workflow below.

## Install

```bash
git clone https://github.com/minghuilab/PremPNI.git
cd PremPNI
docker pull ghcr.io/minghuilab/prempni
bash scripts/prempni.sh --help
```

The image includes the runtime, embedding models and prediction weights; no separate Hugging Face model download is needed. The GHCR package currently requires package access; use `docker login ghcr.io` with an authorized GitHub account if `docker pull` is denied. See the [installation guide](docs/installation.md) for system requirements and source builds.

## Input

Provide the wild-type protein sequence, a single-site mutation and the DNA or RNA sequence. A short example of the input format:

```text
Protein sequence: MAGKRVLSDYEKLQNFDPATVREAIKQLGVEKDSNVRFYTPEEIRKALDAGADVVVT
Mutation:         A2V
DNA sequence:     ACGTACGT
```

`A2V` replaces alanine (A) at position 2 with valine (V). Positions start at 1 in the supplied protein sequence. Use the 20 standard amino acids for protein, A/C/G/T for DNA and A/C/G/U for RNA; write nucleic-acid chains in the 5′→3′ direction.

The runnable examples below use the website's **2KO0 / A39T** DNA example and **1AUD / K49A** RNA example.

## Run

Run these Bash commands from the cloned repository on Linux or WSL2 with Docker. The launcher uses the image's CPU defaults and saves results in `output/` automatically.

### Protein–DNA

```bash
bash scripts/prempni.sh \
  --complex-type dna \
  --sample-id 2KO0 \
  --protein-sequence MVQSCSAYGCKNRYDKDKPVSFHKFPLTRPSLCKEWEAAVRRKNFKPTKYSSICSEHFTPDSFKRESNNKLLKENAVPTIFLELVPR \
  --mutation A39T \
  --chain DNA_1=GCTTGTGTGGGCAGCG \
  --chain DNA_2=CGCTGCCCACACAAGC
```

### Protein–RNA

```bash
bash scripts/prempni.sh \
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
- `--mutation-file /input/mutations.txt` for website-style TXT/CSV/TSV lists saved in the local `input/` directory;
- `--alanine-scan` for one XnA row at every protein position. Existing alanines produce `0.000`, Destabilizing, `computed=false`, without model computation.

Use the same downloadable JSON or five-column TSV as the website:

```bash
bash scripts/prempni.sh \
  --input-tsv /opt/prempni/examples/PremPNI_complexes_example.tsv

bash scripts/prempni.sh \
  --input-json /opt/prempni/examples/prempni_dna_example.json
```

For your own TSV file, save it as `input/complexes.tsv` inside the repository and run:

```bash
bash scripts/prempni.sh --input-tsv /input/complexes.tsv
```

For JSON input, save `input/request.json` and use `--input-json /input/request.json`.

## Output

The DNA example prints:

```text
2KO0 A39T PremPDI2: 0.549 Destabilizing [completed]
```

Here, the predicted ΔΔG is **0.549 kcal/mol**, indicating a destabilizing mutation. Results are saved as:

```text
output/protein_dna/2KO0/prediction/
├── prempni_prediction.csv     # results table
├── prempni_prediction.json    # full results
└── job.json                   # job status
```

RNA results use `output/protein_rna/1AUD/prediction/`; multi-complex results use `output/collections/JOB_ID/`.

## Datasets

Download the final Excel datasets below. Matching TSV exports, field descriptions and SHA-256 checksums are available in the [data directory](datasets/README.md).

| Dataset | Interaction | Records | Contents |
| --- | --- | ---: | --- |
| [S1664](datasets/S1664.xlsx) | Protein–DNA | 1,664 | Sequence-model training records: mutation, sequences and experimental ΔΔG |
| [S1150](datasets/S1150.xlsx) | Protein–RNA | 1,150 | Sequence-model training records: mutation, sequences and experimental ΔΔG |
| [S1336](datasets/S1336.xlsx) | Protein–DNA | 1,336 | Identifiers, S441 membership, 20 features, experimental ΔΔG, PremPDI2 and structure-model predictions |
| [S599](datasets/S599.xlsx) | Protein–RNA | 599 | Identifiers, S260 membership, 13 features, experimental ΔΔG, PremPRI2 and structure-model predictions |

Supplementary data: [S1 — revisions and exclusions](datasets/Supplementary_Data_S1_10.10.xlsx), [S2 — curated experimental records](datasets/Supplementary_Data_S2_10.10.xlsx), [S3 — handcrafted feature definitions](datasets/Supplementary_Data_S3_10.10.xlsx).

Download current data from this repository; the published Docker image has not been rebuilt with this data update.

## Citation

The PremPNI article citation and DOI will be added after publication. Until then, acknowledge PremPNI and the Minghui Li Research Group in derived academic work.

## License

PremPNI is available for academic, non-commercial use only. See [LICENSE](LICENSE). Third-party components retain their original licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
