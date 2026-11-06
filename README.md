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

The container includes `/data/input/` for input files and `/data/output/` for prediction results.

### 3. Preparing Input Files

The image includes the program, trained models and example input files. The examples are stored in `/opt/prempni/examples/`.

- **Protein-DNA:** `prempni_dna_example.tsv`
- **Protein-RNA:** `prempni_rna_example.tsv`

The examples use **Tab** to separate these four columns:

<table>
<thead>
<tr>
<th align="left" nowrap>Type</th>
<th align="left" nowrap>Wild-type protein sequence</th>
<th align="left" nowrap>Nucleic acid sequence</th>
<th align="left" nowrap>Mutation</th>
</tr>
</thead>
<tbody>
<tr>
<td nowrap>Protein-DNA</td>
<td><code>MNFFEYCISTYAKIFEETMNAVGDERVSQKKAIRDTMISAMREFPNVEAAEIWKAVYSAHMDRKSGIADPDIIQKVISAENSWKKSSGHAFEEMIKLLGNSSLEEYGMRILLQKDLNMMIENQEIANEPRDINWLKEQISSNVFDLYITVRNNDKEYVFGCIQSKTSIRDRVTRDREPSMKAMEAFFWSVAICLDGDFLKMPKFIAMVNGGTSNYRLNGWHGMYVFWDKPTIDRIYPIDINLELFVQHAREAAEDWLHRRQWFNYEWKAGQK</code></td>
<td><code>CTCGACCGGTCGAG&amp;CTCGACCGGTCGAG</code></td>
<td>M1A</td>
</tr>
<tr>
<td nowrap>Protein-RNA</td>
<td><code>MAVPETRPNHTIYINNLNEKIKKDELKKSLYAIFSQFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFVERDRKREKRKPKSQETPATKKAVQGGGATPVVGAVQGPVPGMPPMTQAPRIMHHMPGQPPYMPPPGMIPPPGLAPGQIPPGAMPPQQLMPGQMPPAQPLSENPPNHILFLTNLPEETNELMLSMLFNQFPGFKEVRLVPGRHDIAFVEFDNEVQAGAARDALQGFKITQNNAMKISFAKK</code></td>
<td><code>GGCAGAUCUGAGCCUGGGAGCUCUCUGCC</code></td>
<td>M1A</td>
</tr>
</tbody>
</table>

- **Type:** `Protein-DNA` or `Protein-RNA`.
- **Wild-type protein sequence:** Use the one-letter codes for the 20 standard amino acids.
- **Nucleic acid sequence:** Multiple nucleic acid chains are separated by `&`. Enter each chain in the 5′→3′ direction, using T for DNA and U for RNA.
- **Mutation:** one substitution per row, such as `M1A`.

### 4. Running PremPNI

Run the following Python commands **inside the container**.

`run_prempni.py` predicts the effects of one or more single amino acid substitutions, with each substitution entered on a separate row and predicted independently. `--input` specifies the input file, and `--output` specifies the results directory.

#### Protein-DNA example

```bash
python run_prempni.py \
  --input /opt/prempni/examples/prempni_dna_example.tsv \
  --output /data/output
```

#### Protein-RNA example

```bash
python run_prempni.py \
  --input /opt/prempni/examples/prempni_rna_example.tsv \
  --output /data/output
```

### 5. Understanding Output Files

PremPNI automatically generates a Run ID for each prediction run and uses it to name the results folder.

In `PNI-20261105-051102-MXGMG`, `PNI` is a fixed prefix, `20261105-051102` records the start time (5 November 2026 at 05:11:02 UTC), and `MXGMG` consists of five randomly chosen uppercase letters.

Each run automatically creates a `<RUN_ID>/` subfolder in the directory selected with `--output`, containing only `prempni_prediction.tsv`. The result file is saved inside the container at:

```text
/data/output/<RUN_ID>/prempni_prediction.tsv
```

The output is **Tab-separated**. It keeps the original four input columns and adds two result columns. The example output is shown below; scroll horizontally to view all six columns and the complete sequences.

<table>
<thead>
<tr>
<th align="left" nowrap>Type</th>
<th align="left" nowrap>Wild-type protein sequence</th>
<th align="left" nowrap>Nucleic acid sequence</th>
<th align="left" nowrap>Mutation</th>
<th align="right" nowrap>Predicted ΔΔG (kcal/mol)</th>
<th align="left" nowrap>Predicted effect</th>
</tr>
</thead>
<tbody>
<tr>
<td nowrap>Protein-DNA</td>
<td><code>MNFFEYCISTYAKIFEETMNAVGDERVSQKKAIRDTMISAMREFPNVEAAEIWKAVYSAHMDRKSGIADPDIIQKVISAENSWKKSSGHAFEEMIKLLGNSSLEEYGMRILLQKDLNMMIENQEIANEPRDINWLKEQISSNVFDLYITVRNNDKEYVFGCIQSKTSIRDRVTRDREPSMKAMEAFFWSVAICLDGDFLKMPKFIAMVNGGTSNYRLNGWHGMYVFWDKPTIDRIYPIDINLELFVQHAREAAEDWLHRRQWFNYEWKAGQK</code></td>
<td><code>CTCGACCGGTCGAG&amp;CTCGACCGGTCGAG</code></td>
<td>M1A</td>
<td align="right">0.329</td>
<td>Destabilizing</td>
</tr>
<tr>
<td nowrap>Protein-RNA</td>
<td><code>MAVPETRPNHTIYINNLNEKIKKDELKKSLYAIFSQFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFVERDRKREKRKPKSQETPATKKAVQGGGATPVVGAVQGPVPGMPPMTQAPRIMHHMPGQPPYMPPPGMIPPPGLAPGQIPPGAMPPQQLMPGQMPPAQPLSENPPNHILFLTNLPEETNELMLSMLFNQFPGFKEVRLVPGRHDIAFVEFDNEVQAGAARDALQGFKITQNNAMKISFAKK</code></td>
<td><code>GGCAGAUCUGAGCCUGGGAGCUCUCUGCC</code></td>
<td>M1A</td>
<td align="right">-0.541</td>
<td>Stabilizing</td>
</tr>
</tbody>
</table>

**Stabilizing:** ΔΔG < 0; **Destabilizing:** ΔΔG ≥ 0.

### 6. Recommended System Requirements

- **Operating system:** 64-bit Linux (Intel or AMD), with Docker installed.
- **CPU:** 10 CPU cores recommended; a GPU is not required.
- **RAM:** ≥64 GB recommended (longer sequences may require more memory).
