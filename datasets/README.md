# PremPNI datasets

Download the four datasets as Excel workbooks. Each workbook contains a `README` sheet and a data sheet named after the dataset.

| Dataset | Interaction | Records | Contents |
| --- | --- | ---: | --- |
| [S1336](S1336.xlsx) | Protein–DNA | 1,336 | Complex and mutation identifiers, S441 membership, experimental ΔΔG and model predictions |
| [S599](S599.xlsx) | Protein–RNA | 599 | Complex and mutation identifiers, S260 membership, experimental ΔΔG and model predictions |
| [S1664](S1664.xlsx) | Protein–DNA | 1,664 | Sequence-model training records: mutation, wild-type protein sequence, nucleic acid sequence and experimental ΔΔG |
| [S1150](S1150.xlsx) | Protein–RNA | 1,150 | Sequence-model training records: mutation, wild-type protein sequence, nucleic acid sequence and experimental ΔΔG |

ΔΔG values are in kcal/mol. Negative values are Stabilizing; zero and positive values are Destabilizing.

S1336 and S599 include PremPDI2/PremPRI2 predictions averaged over three forward-trained MLPs. Their separate structure-model predictions use leave-one-complex-out cross-validation (LOCOV), with CatBoost for DNA and ExtraTrees for RNA.

Mutation positions in S1336/S599 may require mapping to the supplied sequence. These research datasets differ from the [CLI input examples](../examples/README.md).
