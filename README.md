# PremPNI

## About

PremPNI predicts the effects of single amino acid substitutions on protein–**DNA (PremPDI2)** and protein–**RNA (PremPRI2)** binding affinity. For each substitution, PremPNI predicts the change in binding free energy (ΔΔG, kcal/mol), classified as stabilizing (ΔΔG < 0) or destabilizing (ΔΔG ≥ 0).

Users only need to provide the wild-type protein and corresponding DNA or RNA sequence(s) and specify the amino acid substitution(s). No 3D structure is required.

## Scoring mutations with PremPNI

> [!TIP]
> We recommend that most users who just want to obtain PremPNI predictions use [PremPNI website](https://lilab.jysw.suda.edu.cn/research/PremPNI/) to obtain scores.

## PremPNI Installation and Usage Instructions

### 1. Pull Docker Image

Ensure [Docker](https://docs.docker.com/get-started/get-docker/) is installed, then download the image:

```bash
docker pull ghcr.io/minghuilab/prempni
```

**Image size:** 18.9 GB\
**Estimated download time:** ~20 min at 100 Mbps · ~2 min at 1 Gbps\
*Actual time depends on your network speed.*

### 2. Run the Docker Container

Run this command in a terminal on your computer:

```bash
docker run -it ghcr.io/minghuilab/prempni bash
```

### 3. Preparing Input Files

**Please specify an input folder name (`<folder_name>`) and prepare a tab-separated input file (`.tsv`) with the four columns shown below.**

Replace `<folder_name>` with your chosen folder name, then create the input directory inside the container:

```bash
mkdir -p "/data/<folder_name>"
```

Place your input file in `/data/<folder_name>/`. When running PremPNI, set `--input` to the full path of that file.

For the provided examples, `<folder_name>` is `PremPNI_input`, and the input directory is `/data/PremPNI_input/`.

Copy the provided protein-DNA and protein-RNA example files into this directory:

```bash
mkdir -p /data/PremPNI_input
cp /opt/prempni/examples/prempni_dna_example.tsv /data/PremPNI_input/
cp /opt/prempni/examples/prempni_rna_example.tsv /data/PremPNI_input/
```

The reference format for the input file is shown below:

```text
Type	Wild-type protein sequence	Nucleic acid sequence	Mutation
Protein-DNA	MNFFEYCISTYAKIFEETMNAVGDERVSQKKAIRDTMISAMREFPNVEAAEIWKAVYSAHMDRKSGIADPDIIQKVISAENSWKKSSGHAFEEMIKLLGNSSLEEYGMRILLQKDLNMMIENQEIANEPRDINWLKEQISSNVFDLYITVRNNDKEYVFGCIQSKTSIRDRVTRDREPSMKAMEAFFWSVAICLDGDFLKMPKFIAMVNGGTSNYRLNGWHGMYVFWDKPTIDRIYPIDINLELFVQHAREAAEDWLHRRQWFNYEWKAGQK	CTCGACCGGTCGAG&CTCGACCGGTCGAG	M1A
Protein-RNA	MAVPETRPNHTIYINNLNEKIKKDELKKSLYAIFSQFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFVERDRKREKRKPKSQETPATKKAVQGGGATPVVGAVQGPVPGMPPMTQAPRIMHHMPGQPPYMPPPGMIPPPGLAPGQIPPGAMPPQQLMPGQMPPAQPLSENPPNHILFLTNLPEETNELMLSMLFNQFPGFKEVRLVPGRHDIAFVEFDNEVQAGAARDALQGFKITQNNAMKISFAKK	GGCAGAUCUGAGCCUGGGAGCUCUCUGCC	M1A
```

**Note:**

- **Type:** `Protein-DNA` or `Protein-RNA`.

- **Wild-type protein sequence:** Use the one-letter codes for the 20 standard amino acids.

- **Nucleic acid sequence:** Multiple nucleic acid chains are separated by `&`.

- **Mutation:** one substitution per row, such as `M1A`.

### 4. Running PremPNI

Run the following Python commands **inside the container**.

`run_prempni.py` predicts the effects of one or more single amino acid substitutions, with each substitution entered on a separate row and predicted independently. `--input` specifies the input file, and `--output` specifies the results directory.

#### Protein-DNA example

```bash
python run_prempni.py \
  --input /data/PremPNI_input/prempni_dna_example.tsv \
  --output /data/output
```

#### Protein-RNA example

```bash
python run_prempni.py \
  --input /data/PremPNI_input/prempni_rna_example.tsv \
  --output /data/output
```

### 5. Understanding Output Files

The result file, [prempni_prediction.tsv](Example/prempni_prediction.tsv), is **Tab-separated**. It keeps the original four input columns and adds **Predicted ΔΔG (kcal/mol)** and **Predicted effect**. Click the filename to view the example output.

**Stabilizing:** ΔΔG < 0; **Destabilizing:** ΔΔG ≥ 0.

### 6. Recommended System Requirements

- **Operating system:** 64-bit Linux (Intel or AMD), with Docker installed.
- **CPU:** 10 CPU cores recommended; a GPU is not required.
- **RAM:** ≥64 GB recommended (longer sequences may require more memory).
