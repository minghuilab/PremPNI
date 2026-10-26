# PremPNI

PremPNI predicts binding ΔΔG (kcal/mol) for single-site protein mutations: **PremPDI2** for DNA and **PremPRI2** for RNA. Inputs are protein and nucleic acid sequences plus mutations; no 3D structure is required. Mutations are evaluated independently.

[Web server](https://lilab.jysw.suda.edu.cn/research/PremPNI/) · [Installation](#install) · [Usage and input formats](Examples/README.md)

## Install

Linux x86_64 or WSL2 with Docker. The image includes the runtime and model weights.

GHCR package access is currently required; authenticate with an authorized account via `docker login ghcr.io`.

```bash
git clone https://github.com/minghuilab/PremPNI.git
cd PremPNI
docker pull ghcr.io/minghuilab/prempni
bash Examples/prempni.sh --help
```

## Run a prediction

Run the following commands from the `PremPNI` directory. Predictions use CPU by default.

### Protein–DNA

```bash
bash Examples/prempni.sh \
  --complex-type dna \
  --sample-id S1664_C_61_AlaScan_001 \
  --protein-sequence MNFFEYCISTYAKIFEETMNAVGDERVSQKKAIRDTMISAMREFPNVEAAEIWKAVYSAHMDRKSGIADPDIIQKVISAENSWKKSSGHAFEEMIKLLGNSSLEEYGMRILLQKDLNMMIENQEIANEPRDINWLKEQISSNVFDLYITVRNNDKEYVFGCIQSKTSIRDRVTRDREPSMKAMEAFFWSVAICLDGDFLKMPKFIAMVNGGTSNYRLNGWHGMYVFWDKPTIDRIYPIDINLELFVQHAREAAEDWLHRRQWFNYEWKAGQK \
  --mutation M1A \
  --chain DNA_1=CTCGACCGGTCGAG \
  --chain DNA_2=CTCGACCGGTCGAG
```

### Protein–RNA

```bash
bash Examples/prempni.sh \
  --complex-type rna \
  --sample-id S1150_C_81_AlaScan_001 \
  --protein-sequence MAVPETRPNHTIYINNLNEKIKKDELKKSLYAIFSQFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFVERDRKREKRKPKSQETPATKKAVQGGGATPVVGAVQGPVPGMPPMTQAPRIMHHMPGQPPYMPPPGMIPPPGLAPGQIPPGAMPPQQLMPGQMPPAQPLSENPPNHILFLTNLPEETNELMLSMLFNQFPGFKEVRLVPGRHDIAFVEFDNEVQAGAARDALQGFKITQNNAMKISFAKK \
  --mutation M1A \
  --chain RNA_1=GGCAGAUCUGAGCCUGGGAGCUCUCUGCC
```

For your own data, replace the sample ID, wild-type protein sequence, mutation and nucleic-acid sequences. `M1A` replaces methionine at position 1 with alanine; positions start at 1 in the supplied protein sequence. Use one `--chain NAME=SEQUENCE` per nucleic-acid chain, written in the 5′→3′ direction (T for DNA, U for RNA).

Choose a new `--sample-id` for each run, or add `--overwrite` to replace an existing result. See the [usage guide](Examples/README.md) for JSON/TSV inputs, mutation lists and alanine scanning.

## Output

Reference output for the two M1A examples:

```text
S1664_C_61_AlaScan_001 M1A PremPDI2: 0.329 Destabilizing [completed]
S1150_C_81_AlaScan_001 M1A PremPRI2: -0.541 Stabilizing [completed]
```

The reference ΔΔG values are **0.329 kcal/mol** for DNA and **-0.541 kcal/mol** for RNA. Negative values indicate stabilizing mutations; positive values indicate destabilizing mutations.

Results are saved automatically:

```text
output/protein_dna/S1664_C_61_AlaScan_001/prediction/
├── prempni_prediction.csv
└── prempni_prediction.json
```

RNA results use `output/protein_rna/S1150_C_81_AlaScan_001/prediction/`.

## Datasets

| Excel | Interaction | Records | Contents |
| --- | --- | ---: | --- |
| [S1664](Datasets/S1664.xlsx) | Protein–DNA | 1,664 | Training sequences and experimental ΔΔG |
| [S1150](Datasets/S1150.xlsx) | Protein–RNA | 1,150 | Training sequences and experimental ΔΔG |
| [S1336](Datasets/S1336.xlsx) | Protein–DNA | 1,336 | Experimental ΔΔG and model predictions |
| [S599](Datasets/S599.xlsx) | Protein–RNA | 599 | Experimental ΔΔG and model predictions |

See the [data guide](Datasets/README.md) for contents.

## License

Academic, non-commercial use only. [License](Examples/licenses/LICENSE) · [Third-party notices](Examples/licenses/THIRD_PARTY_NOTICES.md).
