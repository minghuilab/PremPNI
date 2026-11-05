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
- **Recommended free disk space:** ≥50 GB
- **Estimated download time (approximate):**

> 100 Mbps: ~20 min<br>
> 1 Gbps: ~2 min<br>
> (actual time depends on your network speed)

### 2. Run the Docker Container

Check that the container can start:

```bash
docker run --rm ghcr.io/minghuilab/prempni --help
```

The image includes the program and trained models. Each command starts and stops the container automatically.

### 3. Prepare the Input File

Create a working folder:

```bash
mkdir -p prempni/input prempni/output
cd prempni
```

Save the [example file](Examples/PremPNI_complexes_example.tsv) as `input/input.tsv`, then edit it for your own data. Use **Tab** to separate these five columns:

```text
Job Name	Type	Wild-Type Protein Sequence	Nucleic Acid Sequence	Mutation
DNA_example	DNA	MNFFEYCISTYAKIFEETMNAVGDERVSQKKAIRDTMISAMREFPNVEAAEIWKAVYSAHMDRKSGIADPDIIQKVISAENSWKKSSGHAFEEMIKLLGNSSLEEYGMRILLQKDLNMMIENQEIANEPRDINWLKEQISSNVFDLYITVRNNDKEYVFGCIQSKTSIRDRVTRDREPSMKAMEAFFWSVAICLDGDFLKMPKFIAMVNGGTSNYRLNGWHGMYVFWDKPTIDRIYPIDINLELFVQHAREAAEDWLHRRQWFNYEWKAGQK	CTCGACCGGTCGAG&CTCGACCGGTCGAG	M1A
RNA_example	RNA	MAVPETRPNHTIYINNLNEKIKKDELKKSLYAIFSQFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFVERDRKREKRKPKSQETPATKKAVQGGGATPVVGAVQGPVPGMPPMTQAPRIMHHMPGQPPYMPPPGMIPPPGLAPGQIPPGAMPPQQLMPGQMPPAQPLSENPPNHILFLTNLPEETNELMLSMLFNQFPGFKEVRLVPGRHDIAFVEFDNEVQAGAARDALQGFKITQNNAMKISFAKK	GGCAGAUCUGAGCCUGGGAGCUCUCUGCC	M1A
```

- **Job Name:** a unique name for each row; use letters, numbers, underscores, dots or hyphens.
- **Type:** `DNA` or `RNA`.
- **Wild-Type Protein Sequence:** the complete protein sequence before mutation.
- **Nucleic Acid Sequence:** use `&` between chains; write each chain in the 5′→3′ direction (T for DNA, U for RNA).
- **Mutation:** one substitution per row, such as `M1A`; positions start at 1 in the supplied protein sequence.

See [more input examples](Examples/README.md) for separate DNA and RNA files.

### 4. Run PremPNI

Run this command from your `prempni` working folder:

```bash
docker run --rm \
  -v "$PWD/input:/input:ro" \
  -v "$PWD/output:/output" \
  ghcr.io/minghuilab/prempni \
  --input-tsv /input/input.tsv
```

Docker reads your local `input/input.tsv` and saves results in your local `output/` folder. Each row is predicted independently.

Reference CPU runtimes for one mutation are approximately **22 seconds for DNA** (272 amino acids) and **62 seconds for RNA** (282 amino acids), measured using 10 CPUs and a 64 GiB memory limit. Actual time varies with sequence length and hardware; image downloading is excluded.

### 5. Understand the Output Files

The main result file is saved under a folder created for each run:

```text
output/collections/<JOB_ID>/prempni_prediction.tsv
```

The output is **Tab-separated**. It keeps the original five input columns and adds two result columns:

```text
Job Name	Type	Wild-Type Protein Sequence	Nucleic Acid Sequence	Mutation	Predicted ΔΔG (kcal/mol)	Predicted effect
```

Reference values for the [complete example output](Examples/PremPNI_prediction_example.tsv):

| Job Name | Predicted ΔΔG (kcal/mol) | Predicted effect |
| --- | ---: | --- |
| DNA_example | 0.329 | Des |
| RNA_example | -0.541 | Stab |

**Stab:** ΔΔG < 0. **Des:** ΔΔG ≥ 0. Predicted effect is assigned before rounding.

### 6. Recommended System

We recommend **Linux on a 64-bit Intel or AMD computer**, with Docker installed. A GPU is not required.

| Resource | Recommendation |
| --- | --- |
| CPU | 10 CPU cores for runtimes similar to the example tests |
| Memory | 64 GB or more; longer sequences may require more memory |
| Free disk space | 50 GB or more for installation and example results |

Academic, non-commercial use only. [License](Examples/licenses/LICENSE) · [Third-party notices](Examples/licenses/THIRD_PARTY_NOTICES.md).
