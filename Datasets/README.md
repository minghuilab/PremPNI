# PremPNI datasets

These datasets cover amino acid substitutions in protein–DNA and protein–RNA interactions. Each record includes the experimental change in binding free energy (ΔΔG, kcal/mol).

Select a dataset name to access its workbook.

| Dataset | Interaction | Records | Type |
| :--- | :--- | ---: | :--- |
| [S1336](S1336.xlsx) | Protein–DNA | 1,336 | Structure-based |
| [S599](S599.xlsx) | Protein–RNA | 599 | Structure-based |
| [S1664](S1664.xlsx) | Protein–DNA | 1,664 | Sequence-based |
| [S1150](S1150.xlsx) | Protein–RNA | 1,150 | Sequence-based |

## Structure-based datasets

Each record includes a PDB ID, the protein and nucleic acid chain identifiers, the mutated chain, the amino acid substitution, and experimental ΔΔG.

- **S1336** marks membership in the leakage-controlled benchmark subset S441 and reports CatBoost and PremPDI2 predictions.
- **S599** marks membership in the leakage-controlled benchmark subset S260 and reports ExtraTrees and PremPRI2 predictions.

CatBoost and ExtraTrees predictions were obtained using leave-one-complex-out cross-validation (LOCOV).

## Sequence-based training datasets

Each record includes an amino acid substitution, the wild-type protein sequence, the corresponding DNA or RNA sequence(s), and experimental ΔΔG. S1664 and S1150 were used to train the sequence-based models.

See the `README` sheet in each workbook for details.
