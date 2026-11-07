# PremPNI

## About

PremPNI predicts the effects of single amino acid substitutions on protein–**DNA (PremPDI2)** and protein–**RNA (PremPRI2)** binding affinity. For each substitution, PremPNI predicts the change in binding free energy (ΔΔG, kcal/mol), classified as stabilizing (ΔΔG < 0) or destabilizing (ΔΔG ≥ 0).

Users only need to provide the wild-type protein and corresponding DNA or RNA sequence(s) and specify the amino acid substitution(s). No 3D structure is required.

## Scoring mutations with PremPNI

> [!TIP]
> We recommend that most users who just want to obtain PremPNI predictions use [PremPNI website](https://lilab.jysw.suda.edu.cn/research/PremPNI/) to obtain scores.

## PremPNI Installation and Usage Instructions

### 1. Pull Docker Image

Ensure Docker is installed:\
Docker Installation Guide ([https://docs.docker.com/get-started/get-docker/](https://docs.docker.com/get-started/get-docker/))

```bash
docker pull ghcr.io/minghuilab/prempni
```

• Image size: 16.4 GB\
• Estimated download time (approximate):

> 100 Mbps: ~20 min\
> 1 Gbps: ~2 min\
> (actual time depends on network speed)

### 2. Run the Docker Container and Activate Environment

```bash
docker run -it ghcr.io/minghuilab/prempni bash
```

### 3. Preparing Input files and Dictionaries

Please create a folder to store input files:

```bash
mkdir -p /prempni/folder_name
```

Alternatively, use the predefined directory: `/prempni/prempni_input/` for input file storage.

This directory already contains the example files `prempni_dna_example_input.tsv` and `prempni_rna_example_input.tsv`.

The reference format for the input file is shown below:

```text
Type	Wild-type protein sequence	Nucleic acid sequence	Mutation
Protein-DNA	MNFFEYCISTYAKIFEETMNAVGDERVSQKKAIRDTMISAMREFPNVEAAEIWKAVYSAHMDRKSGIADPDIIQKVISAENSWKKSSGHAFEEMIKLLGNSSLEEYGMRILLQKDLNMMIENQEIANEPRDINWLKEQISSNVFDLYITVRNNDKEYVFGCIQSKTSIRDRVTRDREPSMKAMEAFFWSVAICLDGDFLKMPKFIAMVNGGTSNYRLNGWHGMYVFWDKPTIDRIYPIDINLELFVQHAREAAEDWLHRRQWFNYEWKAGQK	CTCGACCGGTCGAG&CTCGACCGGTCGAG	M1A
Protein-RNA	MAVPETRPNHTIYINNLNEKIKKDELKKSLYAIFSQFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFVERDRKREKRKPKSQETPATKKAVQGGGATPVVGAVQGPVPGMPPMTQAPRIMHHMPGQPPYMPPPGMIPPPGLAPGQIPPGAMPPQQLMPGQMPPAQPLSENPPNHILFLTNLPEETNELMLSMLFNQFPGFKEVRLVPGRHDIAFVEFDNEVQAGAARDALQGFKITQNNAMKISFAKK	GGCAGAUCUGAGCCUGGGAGCUCUCUGCC	M1A
```

**Note：**

- **Type:** Interaction type: `Protein-DNA` or `Protein-RNA`.

- **Wild-type protein sequence:** Amino acid sequence using the one-letter codes for the 20 standard amino acids.

- **Nucleic acid sequence:** DNA or RNA sequence; separate multiple chains with `&`.

- **Mutation:** One amino acid substitution per row, such as `M1A`.

- Different columns in the table are separated by tabs.

### 4. Running PremPNI

`run_prempni.py` predicts the effects of one or more single amino acid substitutions, with each substitution entered on a separate row and predicted independently. `--input` specifies the input file, and `--output` specifies the results directory.

#### Protein-DNA example

```bash
python run_prempni.py \
  --input /prempni/prempni_input/prempni_dna_example_input.tsv \
  --output /prempni/prempni_output
```

#### Protein-RNA example

```bash
python run_prempni.py \
  --input /prempni/prempni_input/prempni_rna_example_input.tsv \
  --output /prempni/prempni_output
```

### 5. Understanding Output Files

After running PremPNI, a tab-separated result file named `prempni_prediction.tsv` will be generated under the specified output directory.

The outputs for `prempni_dna_example_input.tsv` and `prempni_rna_example_input.tsv` are provided in [prempni_dna_example_output.tsv](Example/prempni_dna_example_output.tsv) and [prempni_rna_example_output.tsv](Example/prempni_rna_example_output.tsv), respectively. The meaning of each column can be referred to in the [README.md](Example/README.md) file within the corresponding folder.

### 6. Recommended System Requirements

• **RAM:** ≥64 GB recommended (≥50 GB minimal requirement).

• **Disk Space:** ≥50 GB (Docker image: ~16.4 GB + additional space for data and output).
