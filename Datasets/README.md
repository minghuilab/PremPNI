# PremPNI datasets

| Dataset | Interaction | Records | Type |
| :--- | :--- | ---: | :--- |
| [S1336](S1336.xlsx) | Protein–DNA | 1,336 | Structure-based |
| [S599](S599.xlsx) | Protein–RNA | 599 | Structure-based |
| [S1664](S1664.xlsx) | Protein–DNA | 1,664 | Sequence-based |
| [S1150](S1150.xlsx) | Protein–RNA | 1,150 | Sequence-based |

## Structure-based datasets

- **PDB ID:** The PDB identifier of the protein–nucleic acid complex.

- **Protein chains:** The protein chain identifiers in the complex.

- **Nucleic acid chains:** The DNA or RNA chain identifiers in the complex.

- **Mutated chain:** The protein chain in which the mutation occurs.

- **Mutation:** Amino acid substitution in one-letter code (e.g., M1A).

- `Included in leakage-controlled benchmark set (S441/S260)`: Indicates whether the entry is included in the leakage-controlled subset—`S441` for protein–DNA (`S1336`) or `S260` for protein–RNA (`S599`) (`Yes` / `No`).

- **Experimental ΔΔG (kcal/mol):** Experimentally determined ΔΔG value upon mutation.

- **CatBoost / ExtraTrees predicted ΔΔG (LOCOV, kcal/mol):** The ΔΔG value predicted by CatBoost (in S1336) or ExtraTrees (in S599), using leave-one-complex-out cross-validation (LOCOV).

- **PremPDI2 / PremPRI2 predicted ΔΔG (kcal/mol):** The ΔΔG value predicted by PremPDI2 (in S1336) or PremPRI2 (in S599).

## Sequence-based datasets

- **Mutation:** Amino acid substitution in one-letter code (e.g., M1A).

- **Wild-type protein sequence:** The protein sequence before mutation, using one-letter amino acid codes.

- **DNA sequence / RNA sequence:** The DNA sequence(s) in S1664 or RNA sequence(s) in S1150. Multiple sequences are separated by `&`.

- **Experimental ΔΔG (kcal/mol):** Experimentally determined ΔΔG value upon mutation.
