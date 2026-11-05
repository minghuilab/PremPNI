# PremPNI

## About

PremPNI predicts the effects of single amino acid substitutions on protein–**DNA (PremPDI2)** and protein–**RNA (PremPRI2)** binding affinity. For each substitution, PremPNI predicts the change in binding free energy (ΔΔG, kcal/mol), classified as stabilizing (ΔΔG < 0) or destabilizing (ΔΔG ≥ 0). Users only need to provide the wild-type protein and corresponding DNA or RNA sequence(s) and specify the amino acid substitution(s). No 3D structure is required.

[Web server](https://lilab.jysw.suda.edu.cn/research/PremPNI/) · [Datasets](Datasets/README.md)

## PremPNI Installation and Usage Instructions

### 1. Pull Docker Image

Ensure [Docker](https://docs.docker.com/get-started/get-docker/) is installed, then download the image:

```bash
docker pull ghcr.io/minghuilab/prempni
```

- **Image size:** 18.9 GB (download: 14.7 GB)
- **Estimated download time (approximate):**

> 100 Mbps: ~20 min<br>
> 1 Gbps: ~2 min<br>
> (actual time depends on your network speed)

### 2. Run the Docker Container

Run this command in a terminal on your computer:

```bash
docker run -it ghcr.io/minghuilab/prempni bash
```

The container includes `/data/input/` for input files and `/data/output/` for prediction results.

### 3. Preparing Input Files

The image includes the program, trained models and example input files. The DNA and RNA examples are stored in `/opt/prempni/examples/` as `prempni_dna_example.tsv` and `prempni_rna_example.tsv`. The examples use **Tab** to separate these four columns:

```text
Type	Wild-type protein sequence	Nucleic acid sequence	Mutation
Protein-DNA	MNFFEYCISTYAKIFEETMNAVGDERVSQKKAIRDTMISAMREFPNVEAAEIWKAVYSAHMDRKSGIADPDIIQKVISAENSWKKSSGHAFEEMIKLLGNSSLEEYGMRILLQKDLNMMIENQEIANEPRDINWLKEQISSNVFDLYITVRNNDKEYVFGCIQSKTSIRDRVTRDREPSMKAMEAFFWSVAICLDGDFLKMPKFIAMVNGGTSNYRLNGWHGMYVFWDKPTIDRIYPIDINLELFVQHAREAAEDWLHRRQWFNYEWKAGQK	CTCGACCGGTCGAG&CTCGACCGGTCGAG	M1A
Protein-RNA	MAVPETRPNHTIYINNLNEKIKKDELKKSLYAIFSQFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFVERDRKREKRKPKSQETPATKKAVQGGGATPVVGAVQGPVPGMPPMTQAPRIMHHMPGQPPYMPPPGMIPPPGLAPGQIPPGAMPPQQLMPGQMPPAQPLSENPPNHILFLTNLPEETNELMLSMLFNQFPGFKEVRLVPGRHDIAFVEFDNEVQAGAARDALQGFKITQNNAMKISFAKK	GGCAGAUCUGAGCCUGGGAGCUCUCUGCC	M1A
```

- **Type:** `Protein-DNA` or `Protein-RNA`.
- **Wild-type protein sequence:** the complete protein sequence before mutation, using the 20 standard amino acids.
- **Nucleic acid sequence:** use `&` between chains; write each chain in the 5′→3′ direction (T for DNA, U for RNA).
- **Mutation:** one substitution per row, such as `M1A`; positions start at 1 in the supplied protein sequence.

### 4. Running PremPNI

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

### 5. Understanding Output Files

A Run ID identifies one prediction run. It is generated automatically from `PNI`, the UTC start time (`YYYYMMDD-HHMMSS`), and five random uppercase letters, e.g. `PNI-20261105-051102-MXGMG` (illustrative; each run receives a new ID).

Each run automatically creates a `<RUN_ID>/` subfolder in the directory selected with `--output`, containing only `prempni_prediction.tsv`. The result file is saved inside the container at:

```text
/data/output/<RUN_ID>/prempni_prediction.tsv
```

The output is **Tab-separated**. It keeps the original four input columns and adds two result columns. The example output is shown below; scroll horizontally to view all six columns and the complete sequences.

| Type | Wild-type protein sequence | Nucleic acid sequence | Mutation | Predicted ΔΔG (kcal/mol) | Predicted effect |
| --- | --- | --- | --- | --- | --- |
| Protein-DNA | `MNFFEYCISTYAKIFEETMNAVGDERVSQKKAIRDTMISAMREFPNVEAAEIWKAVYSAHMDRKSGIADPDIIQKVISAENSWKKSSGHAFEEMIKLLGNSSLEEYGMRILLQKDLNMMIENQEIANEPRDINWLKEQISSNVFDLYITVRNNDKEYVFGCIQSKTSIRDRVTRDREPSMKAMEAFFWSVAICLDGDFLKMPKFIAMVNGGTSNYRLNGWHGMYVFWDKPTIDRIYPIDINLELFVQHAREAAEDWLHRRQWFNYEWKAGQK` | `CTCGACCGGTCGAG&CTCGACCGGTCGAG` | M1A | 0.329 | Destabilizing |
| Protein-RNA | `MAVPETRPNHTIYINNLNEKIKKDELKKSLYAIFSQFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFVERDRKREKRKPKSQETPATKKAVQGGGATPVVGAVQGPVPGMPPMTQAPRIMHHMPGQPPYMPPPGMIPPPGLAPGQIPPGAMPPQQLMPGQMPPAQPLSENPPNHILFLTNLPEETNELMLSMLFNQFPGFKEVRLVPGRHDIAFVEFDNEVQAGAARDALQGFKITQNNAMKISFAKK` | `GGCAGAUCUGAGCCUGGGAGCUCUCUGCC` | M1A | -0.541 | Stabilizing |

**Stabilizing:** ΔΔG < 0. **Destabilizing:** ΔΔG ≥ 0.

### 6. Recommended System Requirements

- **Operating system:** 64-bit Linux (Intel or AMD), with Docker installed.
- **CPU:** 10 CPU cores recommended; a GPU is not required.
- **RAM:** ≥64 GB recommended (longer sequences may require more memory).

Academic, non-commercial use only. [License](Examples/licenses/LICENSE) · [Third-party notices](Examples/licenses/THIRD_PARTY_NOTICES.md).
