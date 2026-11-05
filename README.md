# PremPNI

## About

**PremPNI** predicts changes in protein–nucleic acid binding affinity caused by single amino acid substitutions. **PremPDI2** is used for protein–DNA interactions and **PremPRI2** for protein–RNA interactions. Only the wild-type protein sequence, the binding DNA or RNA sequences, and the substitution to be tested are required; no three-dimensional structure is needed.

[Web server](https://lilab.jysw.suda.edu.cn/research/PremPNI/) · [Datasets](Datasets/README.md)

## PremPNI Installation and Usage Instructions

### 1. Download the Docker Image

Ensure [Docker](https://docs.docker.com/get-started/get-docker/) is installed, then download the image:

```bash
docker pull ghcr.io/minghuilab/prempni
```

- **Image size:** 18.9 GB (download: 14.7 GB)
- **Estimated download time (approximate):**

> 100 Mbps: ~20 min<br>
> 1 Gbps: ~2 min<br>
> (actual time depends on your network speed)

### 2. Start the Docker Container

The image includes `/data/input/` and `/data/output/`. Run this command from the folder where you want to keep your input files and results. PremPNI creates `input/` and `output/` there automatically when the container starts.

```bash
docker run -it --rm \
  --user "$(id -u):$(id -g)" \
  -v "$PWD:/data" \
  ghcr.io/minghuilab/prempni bash
```

This opens a terminal inside the container at `/opt/prempni/`. The local `input/` and `output/` folders are available as `/data/input/` and `/data/output/`. The `--user` option keeps new files owned by your current user. No environment activation is required. After startup, you can place your own file at `input/input.tsv` using your computer's file manager or another terminal. Existing files are preserved. `--rm` removes the container after you exit; the image and results in your local `output/` folder are retained.

### 3. Prepare Input Files

The image includes the program, trained models and example input files. The DNA and RNA examples are stored in `/opt/prempni/examples/` as `prempni_dna_example.tsv` and `prempni_rna_example.tsv`. The examples use **Tab** to separate these five columns:

```text
Job name	Type	Wild-type protein sequence	Nucleic acid sequence	Mutation
DNA_example	Protein-DNA	MNFFEYCISTYAKIFEETMNAVGDERVSQKKAIRDTMISAMREFPNVEAAEIWKAVYSAHMDRKSGIADPDIIQKVISAENSWKKSSGHAFEEMIKLLGNSSLEEYGMRILLQKDLNMMIENQEIANEPRDINWLKEQISSNVFDLYITVRNNDKEYVFGCIQSKTSIRDRVTRDREPSMKAMEAFFWSVAICLDGDFLKMPKFIAMVNGGTSNYRLNGWHGMYVFWDKPTIDRIYPIDINLELFVQHAREAAEDWLHRRQWFNYEWKAGQK	CTCGACCGGTCGAG&CTCGACCGGTCGAG	M1A
RNA_example	Protein-RNA	MAVPETRPNHTIYINNLNEKIKKDELKKSLYAIFSQFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFVERDRKREKRKPKSQETPATKKAVQGGGATPVVGAVQGPVPGMPPMTQAPRIMHHMPGQPPYMPPPGMIPPPGLAPGQIPPGAMPPQQLMPGQMPPAQPLSENPPNHILFLTNLPEETNELMLSMLFNQFPGFKEVRLVPGRHDIAFVEFDNEVQAGAARDALQGFKITQNNAMKISFAKK	GGCAGAUCUGAGCCUGGGAGCUCUCUGCC	M1A
```

- **Job name:** a unique name for each row; start with a letter or number and use letters, numbers, underscores, dots or hyphens.
- **Type:** `Protein-DNA` or `Protein-RNA`.
- **Wild-type protein sequence:** the complete protein sequence before mutation, using the 20 standard amino acids.
- **Nucleic acid sequence:** use `&` between chains; write each chain in the 5′→3′ direction (T for DNA, U for RNA).
- **Mutation:** one substitution per row, such as `M1A`; positions start at 1 in the supplied protein sequence.

The example files are:

| File | Contents |
| --- | --- |
| [prempni_dna_example.tsv](Examples/prempni_dna_example.tsv) | Protein-DNA M1A; 272 amino acids and two 14 nt DNA chains |
| [prempni_rna_example.tsv](Examples/prempni_rna_example.tsv) | Protein-RNA M1A; 282 amino acids and one 29 nt RNA chain |

Use the same format for your own data. To test several substitutions, put each one on a separate row with a unique Job name. Do not combine substitutions within a cell. Input order is preserved.

### 4. Run PremPNI

Run the following Python commands **inside the container**. `run_prempni.py` is the entry point for both single-row and multi-row input files. `--input` specifies the input file, and `--output` specifies the results directory.

**Protein-DNA example**

```bash
python run_prempni.py \
  --input /opt/prempni/examples/prempni_dna_example.tsv \
  --output /data/output
```

**Protein-RNA example**

```bash
python run_prempni.py \
  --input /opt/prempni/examples/prempni_rna_example.tsv \
  --output /data/output
```

### 5. Understand the Output Files

A Job ID identifies one prediction run. It is generated automatically from `PNI`, the UTC start time (`YYYYMMDD-HHMMSS`), and five random uppercase letters, e.g. `PNI-20261105-051102-MXGMG`.

Each run automatically creates a `<JOB_ID>/` subfolder in the directory selected with `--output`, containing only `prempni_prediction.tsv`. With the default folders, the result file is:

```text
output/<JOB_ID>/prempni_prediction.tsv
```

The output is **Tab-separated**. It keeps the original five input columns and adds two result columns. The [example output](Examples/PremPNI_prediction_example.tsv) is shown below; scroll horizontally to view all columns and the complete sequences.

| Job name | Type | Wild-type protein sequence | Nucleic acid sequence | Mutation | Predicted ΔΔG (kcal/mol) | Predicted effect |
| --- | --- | --- | --- | --- | --- | --- |
| DNA_example | Protein-DNA | `MNFFEYCISTYAKIFEETMNAVGDERVSQKKAIRDTMISAMREFPNVEAAEIWKAVYSAHMDRKSGIADPDIIQKVISAENSWKKSSGHAFEEMIKLLGNSSLEEYGMRILLQKDLNMMIENQEIANEPRDINWLKEQISSNVFDLYITVRNNDKEYVFGCIQSKTSIRDRVTRDREPSMKAMEAFFWSVAICLDGDFLKMPKFIAMVNGGTSNYRLNGWHGMYVFWDKPTIDRIYPIDINLELFVQHAREAAEDWLHRRQWFNYEWKAGQK` | `CTCGACCGGTCGAG&CTCGACCGGTCGAG` | M1A | 0.329 | Destabilizing |
| RNA_example | Protein-RNA | `MAVPETRPNHTIYINNLNEKIKKDELKKSLYAIFSQFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFVERDRKREKRKPKSQETPATKKAVQGGGATPVVGAVQGPVPGMPPMTQAPRIMHHMPGQPPYMPPPGMIPPPGLAPGQIPPGAMPPQQLMPGQMPPAQPLSENPPNHILFLTNLPEETNELMLSMLFNQFPGFKEVRLVPGRHDIAFVEFDNEVQAGAARDALQGFKITQNNAMKISFAKK` | `GGCAGAUCUGAGCCUGGGAGCUCUCUGCC` | M1A | -0.541 | Stabilizing |

**Stabilizing:** ΔΔG < 0. **Destabilizing:** ΔΔG ≥ 0.

### 6. Recommended System

We recommend **Linux on a 64-bit Intel or AMD computer**, with Docker installed. A GPU is not required.

| Resource | Recommendation |
| --- | --- |
| CPU | 10 CPU cores for runtimes similar to the example tests |
| Memory | 64 GB or more; longer sequences may require more memory |

Academic, non-commercial use only. [License](Examples/licenses/LICENSE) · [Third-party notices](Examples/licenses/THIRD_PARTY_NOTICES.md).
