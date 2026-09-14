# PremPNI

PremPNI predicts mutation-induced changes in protein–DNA and protein–RNA binding affinity from a wild-type protein sequence, nucleic-acid sequences and a single-site protein mutation. No three-dimensional complex structure is required. Predictions are ΔΔG values in kcal/mol.

Use the [PremPNI web server](https://lilab.jysw.suda.edu.cn/research/PremPNI/) or the standalone Docker workflow below.

## Install

The documented image release is `v0.2.1`:

```bash
docker pull ghcr.io/minghuilab/prempni:v0.2.1
docker run --rm ghcr.io/minghuilab/prempni:v0.2.1 --help
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

The v0.2.1 image runs all stages on CPU with 10 CPU threads by default. Commands below use Bash on Linux (or a configured WSL2 Docker environment). Set `OMP_NUM_THREADS` and `MKL_NUM_THREADS` only when you need a different thread count.

The commands below save results in `/home/user/prempni/output`. Replace this example path with your own absolute output path.

```bash
mkdir -p /home/user/prempni/output
```

### Protein–DNA

```bash
docker run --rm \
  -e OMP_NUM_THREADS=10 -e MKL_NUM_THREADS=10 \
  -v /home/user/prempni/output:/output \
  ghcr.io/minghuilab/prempni:v0.2.1 \
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
  -e OMP_NUM_THREADS=10 -e MKL_NUM_THREADS=10 \
  -v /home/user/prempni/output:/output \
  ghcr.io/minghuilab/prempni:v0.2.1 \
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
docker run --rm -v /home/user/prempni/output:/output \
  ghcr.io/minghuilab/prempni:v0.2.1 \
  --input-tsv /opt/prempni/examples/PremPNI_complexes_example.tsv

docker run --rm -v /home/user/prempni/output:/output \
  ghcr.io/minghuilab/prempni:v0.2.1 \
  --input-json /opt/prempni/examples/prempni_dna_example.json
```

For your own TSV file, replace the example input and output paths below with your local directories:

```bash
docker run --rm \
  -v /home/user/prempni/input:/input:ro \
  -v /home/user/prempni/output:/output \
  ghcr.io/minghuilab/prempni:v0.2.1 \
  --input-tsv /input/complexes.tsv
```

For JSON input, replace the last line with `--input-json /input/request.json`.

## Output

The DNA example prints:

```text
2KO0 A39T PremPDI2: 0.549 Destabilizing [completed]
```

Here, the predicted ΔΔG is **0.549 kcal/mol**, indicating a destabilizing mutation. Results are saved as:

```text
/home/user/prempni/output/protein_dna/2KO0/prediction/
├── prempni_prediction.csv     # results table
├── prempni_prediction.json    # full results
└── job.json                   # job status
```

RNA results use `output/protein_rna/1AUD/prediction/`; multi-complex results use `output/collections/JOB_ID/`.

## Datasets

The [PremPNI workbook](datasets/PremPNI_curated_datasets.xlsx) contains four datasets, also available separately as TSV files:

| Dataset | Interaction | Records | Contents |
| --- | --- | ---: | --- |
| [S1664](datasets/S1664.tsv) | Protein–DNA | 1,664 | Mutation, protein and DNA sequences, experimental DDG |
| [S1150](datasets/S1150.tsv) | Protein–RNA | 1,150 | Mutation, protein and RNA sequences, experimental DDG |
| [S1336](datasets/S1336.tsv) | Protein–DNA | 1,336 | PDB mutation identifier, experimental DDG, PremPDI2 prediction |
| [S599](datasets/S599.tsv) | Protein–RNA | 599 | PDB mutation identifier, experimental DDG, PremPRI2 prediction |

## Citation

The PremPNI article citation and DOI will be added after publication. Until then, acknowledge PremPNI and the Minghui Li Research Group in derived academic work.

## License

PremPNI is available for academic, non-commercial use only. See [LICENSE](LICENSE). Third-party components retain their original licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
