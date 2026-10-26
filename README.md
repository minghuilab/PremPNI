# PremPNI

**PremPNI** predicts changes in protein–nucleic acid binding affinity caused by single amino acid substitutions. PremPDI2 is used for protein–DNA interactions and PremPRI2 for protein–RNA interactions. Only the wild-type protein sequence, the binding DNA or RNA sequences, and the substitution to be tested are required; no three-dimensional structure is needed.

[Web server](https://lilab.jysw.suda.edu.cn/research/PremPNI/) · [Installation](#install) · [Usage and input formats](Examples/README.md)

## Install

Install [Docker](https://docs.docker.com/get-started/get-docker/), then run:

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
  --protein-sequence MNFFEYCISTYAKIFEETMNAVGDERVSQKKAIRDTMISAMREFPNVEAAEIWKAVYSAHMDRKSGIADPDIIQKVISAENSWKKSSGHAFEEMIKLLGNSSLEEYGMRILLQKDLNMMIENQEIANEPRDINWLKEQISSNVFDLYITVRNNDKEYVFGCIQSKTSIRDRVTRDREPSMKAMEAFFWSVAICLDGDFLKMPKFIAMVNGGTSNYRLNGWHGMYVFWDKPTIDRIYPIDINLELFVQHAREAAEDWLHRRQWFNYEWKAGQK \
  --mutation M1A \
  --chain DNA_1=CTCGACCGGTCGAG \
  --chain DNA_2=CTCGACCGGTCGAG
```

### Protein–RNA

```bash
bash Examples/prempni.sh \
  --complex-type rna \
  --protein-sequence MAVPETRPNHTIYINNLNEKIKKDELKKSLYAIFSQFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFVERDRKREKRKPKSQETPATKKAVQGGGATPVVGAVQGPVPGMPPMTQAPRIMHHMPGQPPYMPPPGMIPPPGLAPGQIPPGAMPPQQLMPGQMPPAQPLSENPPNHILFLTNLPEETNELMLSMLFNQFPGFKEVRLVPGRHDIAFVEFDNEVQAGAARDALQGFKITQNNAMKISFAKK \
  --mutation M1A \
  --chain RNA_1=GGCAGAUCUGAGCCUGGGAGCUCUCUGCC
```

For your own data, replace the wild-type protein sequence, mutation and nucleic-acid sequences. `M1A` replaces methionine at position 1 with alanine; positions start at 1 in the supplied protein sequence. Use one `--chain NAME=SEQUENCE` per nucleic-acid chain, written in the 5′→3′ direction (T for DNA, U for RNA).

`--sample-id` is optional. A unique name is generated automatically; add `--sample-id my_sample` to choose your own. See the [usage guide](Examples/README.md) for JSON/TSV inputs, mutation lists and alanine scanning.

## Output

Reference output for the two M1A examples:

```text
<sample_id> M1A PremPDI2: 0.329 Destabilizing [completed]
<sample_id> M1A PremPRI2: -0.541 Stabilizing [completed]
```

The reference ΔΔG values are **0.329 kcal/mol** for DNA and **-0.541 kcal/mol** for RNA. Negative values indicate stabilizing mutations; positive values indicate destabilizing mutations.

Results are saved automatically:

```text
output/protein_dna/<sample_id>/prediction/
├── prempni_prediction.csv
└── prempni_prediction.json
```

RNA results use `output/protein_rna/<sample_id>/prediction/`. The automatically generated name is printed when the run starts.

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
