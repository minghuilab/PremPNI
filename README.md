# PremPNI

## About

PremPNI predicts the effects of single amino acid substitutions on protein–**DNA (PremPDI2)** and protein–**RNA (PremPRI2)** binding affinity. For each substitution, PremPNI predicts the change in binding free energy (ΔΔG, kcal/mol), classified as stabilizing (ΔΔG < 0) or destabilizing (ΔΔG ≥ 0). Users only need to provide the wild-type protein and corresponding DNA or RNA sequence(s) and specify the amino acid substitution(s). No 3D structure is required.

## PremPNI Web Server

For online prediction without local installation, use the [PremPNI web server](https://lilab.jysw.suda.edu.cn/research/PremPNI/). Submit the wild-type protein sequence, the corresponding DNA or RNA sequence(s), and the amino acid substitution(s) through the web interface.

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

<table>
<thead>
<tr>
<th>Type</th>
<th>Wild-type protein sequence</th>
<th>Nucleic acid sequence</th>
<th>Mutation</th>
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
- **Wild-type protein sequence:** The wild-type protein sequence using the 20 standard amino acid one-letter codes.
- **Nucleic acid sequence:** Multiple nucleic acid chains are separated by `&`. Enter each chain in the 5′→3′ direction, using T for DNA and U for RNA.
- **Mutation:** one substitution per row, such as `M1A`; positions start at 1 in the supplied protein sequence.

### 4. Running PremPNI

Run the following Python commands **inside the container**. `run_prempni.py` predicts the effects of one or more single amino acid substitutions, with each substitution entered on a separate row and predicted independently. `--input` specifies the input file, and `--output` specifies the results directory.

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

<table>
<thead>
<tr>
<th>Type</th>
<th>Wild-type protein sequence</th>
<th>Nucleic acid sequence</th>
<th>Mutation</th>
<th>Predicted ΔΔG (kcal/mol)</th>
<th>Predicted effect</th>
</tr>
</thead>
<tbody>
<tr>
<td nowrap>Protein-DNA</td>
<td><code>MNFFEYCISTYAKIFEETMNAVGDERVSQKKAIRDTMISAMREFPNVEAAEIWKAVYSAHMDRKSGIADPDIIQKVISAENSWKKSSGHAFEEMIKLLGNSSLEEYGMRILLQKDLNMMIENQEIANEPRDINWLKEQISSNVFDLYITVRNNDKEYVFGCIQSKTSIRDRVTRDREPSMKAMEAFFWSVAICLDGDFLKMPKFIAMVNGGTSNYRLNGWHGMYVFWDKPTIDRIYPIDINLELFVQHAREAAEDWLHRRQWFNYEWKAGQK</code></td>
<td><code>CTCGACCGGTCGAG&amp;CTCGACCGGTCGAG</code></td>
<td>M1A</td>
<td>0.329</td>
<td>Destabilizing</td>
</tr>
<tr>
<td nowrap>Protein-RNA</td>
<td><code>MAVPETRPNHTIYINNLNEKIKKDELKKSLYAIFSQFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFVERDRKREKRKPKSQETPATKKAVQGGGATPVVGAVQGPVPGMPPMTQAPRIMHHMPGQPPYMPPPGMIPPPGLAPGQIPPGAMPPQQLMPGQMPPAQPLSENPPNHILFLTNLPEETNELMLSMLFNQFPGFKEVRLVPGRHDIAFVEFDNEVQAGAARDALQGFKITQNNAMKISFAKK</code></td>
<td><code>GGCAGAUCUGAGCCUGGGAGCUCUCUGCC</code></td>
<td>M1A</td>
<td>-0.541</td>
<td>Stabilizing</td>
</tr>
</tbody>
</table>

**Stabilizing:** ΔΔG < 0; **Destabilizing:** ΔΔG ≥ 0.

### 6. Recommended System Requirements

- **Operating system:** 64-bit Linux (Intel or AMD), with Docker installed.
- **CPU:** 10 CPU cores recommended; a GPU is not required.
- **RAM:** ≥64 GB recommended (longer sequences may require more memory).
