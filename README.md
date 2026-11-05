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

The image includes `/data/input/` and `/data/output/`. Run this command from the folder where you want to keep your input files and results. PremPNI creates `input/` and `output/` there automatically when the container starts.

```bash
docker run -it --rm \
  --user "$(id -u):$(id -g)" \
  -v "$PWD:/data" \
  ghcr.io/minghuilab/prempni bash
```

This opens a terminal inside the container at `/opt/prempni/`. The local `input/` and `output/` folders are available as `/data/input/` and `/data/output/`. The `--user` option keeps new files owned by your current user. No environment activation is required. After startup, you can place your own file at `input/input.tsv` using your computer's file manager or another terminal. Existing files are preserved. `--rm` removes the container after you exit; the image and results in your local `output/` folder are retained.

**Use your own folders (optional)**

You can choose separate input and output folders anywhere on your computer. Replace `/home/yourname/my_inputs` and `/home/yourname/my_results` below with the full paths to existing folders you want to use. Choose a writable folder for results.

```bash
docker run -it --rm \
  --user "$(id -u):$(id -g)" \
  --mount "type=bind,source=/home/yourname/my_inputs,target=/data/input,readonly" \
  --mount "type=bind,source=/home/yourname/my_results,target=/data/output" \
  ghcr.io/minghuilab/prempni bash
```

Inside the container, `/data/input/` refers to your chosen input folder and `/data/output/` refers to your chosen results folder. Input files are read-only; results are written to your chosen output folder and remain there after you exit. Use this startup command instead of the default command above.

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

**Your own input**

```bash
python run_prempni.py \
  --input /data/input/input.tsv \
  --output /data/output
```

**Choose a different input filename or result subfolder**

```bash
python run_prempni.py \
  --input /data/input/my_jobs.tsv \
  --output /data/output/project_A
```

`--input` accepts a file path, including its filename. `--output` accepts a directory path and creates missing subdirectories automatically. With the custom folders above, this example reads `/home/yourname/my_inputs/my_jobs.tsv` and saves results under `/home/yourname/my_results/project_A/`.

Each input row is predicted independently. All rows are validated before prediction starts. Results are saved in the selected output folder on your computer. You can run more predictions in the same container. When finished, type `exit` to return to your computer's terminal.

Reference CPU runtimes for one mutation are approximately **22 seconds for DNA** (272 amino acids) and **62 seconds for RNA** (282 amino acids), measured using 10 CPUs and a 64 GiB memory limit. Actual time varies with sequence length and hardware; image downloading is excluded.

### 5. Understand the Output Files

Each run creates a `collections/<JOB_ID>/` subfolder in the directory selected with `--output`. With the default folders, the main result file is:

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
| DNA_example | 0.329 | Destabilizing |
| RNA_example | -0.541 | Stabilizing |

**Stabilizing:** ΔΔG < 0. **Destabilizing:** ΔΔG ≥ 0. Predicted effect is assigned before rounding. Failed predictions retain their input row with the two result cells empty; details are recorded in `job.json`.

### 6. Recommended System

We recommend **Linux on a 64-bit Intel or AMD computer**, with Docker installed. A GPU is not required.

| Resource | Recommendation |
| --- | --- |
| CPU | 10 CPU cores for runtimes similar to the example tests |
| Memory | 64 GB or more; longer sequences may require more memory |

Academic, non-commercial use only. [License](Examples/licenses/LICENSE) · [Third-party notices](Examples/licenses/THIRD_PARTY_NOTICES.md).
