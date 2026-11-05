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

### 2. Input Files

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

### 3. Start the Docker Container

Run these commands on your computer. Create separate folders for your input files and prediction results:

```bash
mkdir -p input
mkdir -p output
```

For your own data, place the Tab-separated file at `input/input.tsv`. Then open the PremPNI environment:

```bash
docker run -it --rm \
  -v "$PWD/input:/input:ro" \
  -v "$PWD/output:/output" \
  --entrypoint bash \
  ghcr.io/minghuilab/prempni
```

This opens a terminal inside the container at `/opt/prempni/`. The local `input/` and `output/` folders are available as `/input/` and `/output/`. No environment activation is required. `--rm` removes the container after you exit; the image and results saved in your local `output/` folder are retained.

### 4. Run PremPNI

Run the following Python commands **inside the container**. `--input` specifies the input file, and `--output` specifies the results directory.

**Protein-DNA example**

```bash
python run_prempni.py \
  --input /opt/prempni/examples/prempni_dna_example.tsv \
  --output /output
```

**Protein-RNA example**

```bash
python run_prempni.py \
  --input /opt/prempni/examples/prempni_rna_example.tsv \
  --output /output
```

**Your own input**

```bash
python run_prempni.py \
  --input /input/input.tsv \
  --output /output
```

Each input row is predicted independently. All rows are validated before prediction starts. Results are saved in the local `output/` folder on your computer. You can run more predictions in the same container. When finished, type `exit` to return to your computer's terminal.

Reference CPU runtimes for one mutation are approximately **22 seconds for DNA** (272 amino acids) and **62 seconds for RNA** (282 amino acids), measured using 10 CPUs and a 64 GiB memory limit. Actual time varies with sequence length and hardware; image downloading is excluded.

### 5. Understand the Output Files

The main result file is saved under a folder created for each run:

```text
output/collections/<JOB_ID>/prempni_prediction.tsv
```

The output is **Tab-separated**. It keeps the original five input columns and adds two result columns:

```text
Job name	Type	Wild-type protein sequence	Nucleic acid sequence	Mutation	Predicted ΔΔG (kcal/mol)	Predicted effect
```

Reference values for the [complete example output](Examples/PremPNI_prediction_example.tsv):

| Job name | Predicted ΔΔG (kcal/mol) | Predicted effect |
| --- | ---: | --- |
| DNA_example | 0.329 | Des |
| RNA_example | -0.541 | Stab |

**Stab:** ΔΔG < 0. **Des:** ΔΔG ≥ 0. Predicted effect is assigned before rounding. Failed predictions retain their input row with the two result cells empty; details are recorded in `job.json`.

### 6. Recommended System

We recommend **Linux on a 64-bit Intel or AMD computer**, with Docker installed. A GPU is not required.

| Resource | Recommendation |
| --- | --- |
| CPU | 10 CPU cores for runtimes similar to the example tests |
| Memory | 64 GB or more; longer sequences may require more memory |

Academic, non-commercial use only. [License](Examples/licenses/LICENSE) · [Third-party notices](Examples/licenses/THIRD_PARTY_NOTICES.md).
