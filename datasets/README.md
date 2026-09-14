# PremPNI curated datasets

Download the [PremPNI workbook](PremPNI_curated_datasets.xlsx), or use the individual TSV files below.

| Dataset | Interaction | Records | Contents |
| --- | --- | ---: | --- |
| [S1664](S1664.tsv) | Protein–DNA | 1,664 | Mutations, protein and DNA sequences, experimental DDG |
| [S1150](S1150.tsv) | Protein–RNA | 1,150 | Mutations, protein and RNA sequences, experimental DDG |
| [S1336](S1336.tsv) | Protein–DNA | 1,336 | PDB mutation identifiers, experimental DDG, PremPDI2 predictions |
| [S599](S599.tsv) | Protein–RNA | 599 | PDB mutation identifiers, experimental DDG, PremPRI2 predictions |

## Meaning of the columns

| Column | Meaning |
| --- | --- |
| `DDG` | Experimental ΔΔG in kcal/mol; negative: Stabilizing, zero or positive: Destabilizing. |
| `PremPDI2_prediction`, `PremPRI2_prediction` | Predicted ΔΔG in kcal/mol. |
| `Mutation` | Protein substitution, e.g. `R355A`: arginine at sequence position 355 replaced by alanine. |
| `Protein_sequence` | Wild-type protein sequence. |
| `Nucleic_acid_sequence` | DNA or RNA sequence; `\|` separates chains. |
| `PDB_mutation` | PDB mutation identifier, e.g. `1LMB*3*A49D`. |
