# PremPNI

## About

**PremPNI** predicts changes in protein–nucleic acid binding affinity caused by single amino acid substitutions. **PremPDI2** is used for protein–DNA interactions and **PremPRI2** for protein–RNA interactions. Only the wild-type protein sequence, the binding DNA or RNA sequences, and the substitution to be tested are required; no three-dimensional structure is needed.

[Web server](https://lilab.jysw.suda.edu.cn/research/PremPNI/) · [Datasets](Datasets/README.md)

## PremPNI Installation and Usage Instructions

### 1. Download the Docker Image

Install [Docker](https://docs.docker.com/get-started/get-docker/), then download PremPNI and its Docker image:

```bash
git clone https://github.com/minghuilab/PremPNI.git
cd PremPNI
docker pull ghcr.io/minghuilab/prempni
```

The image includes the software and trained models. The download is approximately **14.7 GB**, and the extracted image occupies about **18.9 GB**. We recommend **50 GB of free disk space** for downloading, installation and example results.

Download time depends on your connection. At 100 Mbps, the transfer alone would take about **20 minutes**; extraction requires additional time.

### 2. Run the Docker Container

Check that the container can start and display the available options:

```bash
docker run --rm ghcr.io/minghuilab/prempni --help
```

The prediction commands below start and stop the container automatically. Run them from the `PremPNI` directory.

### 3. Prepare the Input File

Copy the [DNA example](Examples/prempni_dna_example.json) to an `input/` folder, then edit `input/request.json` for your own data:

```bash
mkdir -p input
cp Examples/prempni_dna_example.json input/request.json
```

The input file has the following format:

```json
{
  "sample_id": "S1664_C_61_AlaScan_001",
  "complex_type": "dna",
  "protein_sequence": "MNFFEYCISTYAKIFEETMNAVGDERVSQKKAIRDTMISAMREFPNVEAAEIWKAVYSAHMDRKSGIADPDIIQKVISAENSWKKSSGHAFEEMIKLLGNSSLEEYGMRILLQKDLNMMIENQEIANEPRDINWLKEQISSNVFDLYITVRNNDKEYVFGCIQSKTSIRDRVTRDREPSMKAMEAFFWSVAICLDGDFLKMPKFIAMVNGGTSNYRLNGWHGMYVFWDKPTIDRIYPIDINLELFVQHAREAAEDWLHRRQWFNYEWKAGQK",
  "mutation": "M1A",
  "chains": [
    {"chain_id": "DNA_1", "sequence": "CTCGACCGGTCGAG"},
    {"chain_id": "DNA_2", "sequence": "CTCGACCGGTCGAG"}
  ]
}
```

Use a unique `sample_id` to name the result folder. `M1A` means replacing methionine at position 1 with alanine; positions start at 1 in the supplied wild-type protein sequence.

Provide one entry per nucleic acid chain, written in the 5′→3′ direction. DNA uses A/C/G/T. For RNA, use `"complex_type": "rna"` and A/C/G/U sequences, as shown in the [RNA example](Examples/prempni_rna_example.json).

### 4. Run PremPNI

Run your prepared input file:

```bash
bash Examples/prempni.sh --input-json /input/request.json
```

Here, `/input/request.json` refers to the local `input/request.json` file inside Docker.

To run the two supplied examples directly:

```bash
# Protein–DNA: 272 amino acids
bash Examples/run_dna.sh

# Protein–RNA: 282 amino acids
bash Examples/run_rna.sh
```

In CPU-only tests using 10 CPUs and a 64 GiB memory limit, these single-mutation examples took approximately **22 seconds for DNA** and **62 seconds for RNA**. Runtime varies with sequence length and hardware; these timings exclude downloading the image.

See [additional input formats](Examples/README.md) for multiple complexes, mutation lists and alanine scanning. Mutations are evaluated independently.

### 5. Understand the Output Files

Results are saved in the local `output/` folder:

```text
output/protein_dna/<sample_id>/prediction/
├── prempni_prediction.csv
├── prempni_prediction.json
└── job.json
```

RNA results use `output/protein_rna/<sample_id>/prediction/`. The CSV contains the input and predictions; the JSON files also record the run status. For the supplied example scripts, the generated folder name is printed when the run starts.

The main result columns and reference values for the two M1A examples are:

| mutation | predictor | prediction_kcal_per_mol | predicted_effect |
| --- | --- | ---: | --- |
| M1A | PremPDI2 | 0.329 | Destabilizing |
| M1A | PremPRI2 | -0.541 | Stabilizing |

`prediction_kcal_per_mol` is the predicted binding affinity change (ΔΔG, kcal/mol). Negative values indicate stabilizing substitutions; zero and positive values are classified as destabilizing.

### 6. Recommended System

We recommend **Linux on a 64-bit Intel or AMD computer**, with Docker and Bash installed. A GPU is not required.

| Resource | Recommendation |
| --- | --- |
| CPU | 10 CPU cores for runtimes similar to the example tests |
| Memory | 64 GB or more; longer sequences may require more memory |
| Free disk space | 50 GB or more for installation and example results |

Academic, non-commercial use only. [License](Examples/licenses/LICENSE) · [Third-party notices](Examples/licenses/THIRD_PARTY_NOTICES.md).
