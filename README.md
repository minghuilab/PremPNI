# PremPNI

PremPNI predicts binding ΔΔG (kcal/mol) for single-site protein mutations: **PremPDI2** for DNA and **PremPRI2** for RNA. Inputs are protein and nucleic acid sequences plus mutations; no 3D structure is required. Mutations are evaluated independently.

[Web server](https://lilab.jysw.suda.edu.cn/research/PremPNI/) · [Installation](#install) · [Usage and input formats](examples/README.md)

## Install

Linux x86_64 or WSL2 with Docker. The image includes the runtime and model weights.

GHCR package access is currently required; authenticate with an authorized account via `docker login ghcr.io`.

```bash
git clone https://github.com/minghuilab/PremPNI.git
cd PremPNI
docker pull ghcr.io/minghuilab/prempni
bash examples/prempni.sh --help
```

## Run a prediction

Run the following commands from the `PremPNI` directory. Predictions use CPU by default.

### Protein–DNA

```bash
bash examples/prempni.sh \
  --complex-type dna \
  --sample-id 2KO0 \
  --protein-sequence MVQSCSAYGCKNRYDKDKPVSFHKFPLTRPSLCKEWEAAVRRKNFKPTKYSSICSEHFTPDSFKRESNNKLLKENAVPTIFLELVPR \
  --mutation A39T \
  --chain DNA_1=GCTTGTGTGGGCAGCG \
  --chain DNA_2=CGCTGCCCACACAAGC
```

### Protein–RNA

```bash
bash examples/prempni.sh \
  --complex-type rna \
  --sample-id 1AUD \
  --protein-sequence AVPETRPNHTIYINNLNEKIKKDELKKSLHAIFSRFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFV \
  --mutation K49A \
  --chain RNA_1=GGCAGAGUCCUUCGGGACAUUGCACCUGCC
```

For your own data, replace the sample ID, wild-type protein sequence, mutation and nucleic-acid sequences. `A39T` replaces alanine at position 39 with threonine; positions start at 1 in the supplied protein sequence. Use one `--chain NAME=SEQUENCE` per nucleic-acid chain, written in the 5′→3′ direction (T for DNA, U for RNA).

Choose a new `--sample-id` for each run, or add `--overwrite` to replace an existing result. See the [usage guide](examples/README.md) for JSON/TSV inputs, mutation lists and alanine scanning.

## Output

The DNA example prints:

```text
2KO0 A39T PremPDI2: 0.549 Destabilizing [completed]
```

The predicted ΔΔG is **0.549 kcal/mol**. Negative values indicate stabilizing mutations; positive values indicate destabilizing mutations.

Results are saved automatically:

```text
output/protein_dna/2KO0/prediction/
├── prempni_prediction.csv
└── prempni_prediction.json
```

RNA results use `output/protein_rna/1AUD/prediction/`.

## Datasets

| Excel | Interaction | Records | Contents |
| --- | --- | ---: | --- |
| [S1664](datasets/S1664.xlsx) | Protein–DNA | 1,664 | Training sequences and experimental ΔΔG |
| [S1150](datasets/S1150.xlsx) | Protein–RNA | 1,150 | Training sequences and experimental ΔΔG |
| [S1336](datasets/S1336.xlsx) | Protein–DNA | 1,336 | Experimental ΔΔG and model predictions |
| [S599](datasets/S599.xlsx) | Protein–RNA | 599 | Experimental ΔΔG and model predictions |

See the [data guide](datasets/README.md) for contents.

## License

Academic, non-commercial use only. [License](LICENSE) · [Third-party notices](licenses/THIRD_PARTY_NOTICES.md).
