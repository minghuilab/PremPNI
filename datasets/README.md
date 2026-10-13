# PremPNI datasets and supplementary data

The seven Excel workbooks below are the author-approved final files, copied without modification. Each includes a `README` worksheet. SHA-256 checksums, worksheet names, row counts and exact column names are recorded in [manifest.json](manifest.json).

## Datasets

| Dataset | Interaction | Records | Files | Contents |
| --- | --- | ---: | --- | --- |
| S1336 | Protein–DNA | 1,336 | [Excel](S1336.xlsx), [TSV](S1336.tsv) | Complex and mutation identifiers, S441 membership, 20 handcrafted features, experimental ΔΔG, PremPDI2 and structure-model predictions |
| S599 | Protein–RNA | 599 | [Excel](S599.xlsx), [TSV](S599.tsv) | Complex and mutation identifiers, S260 membership, 13 handcrafted features, experimental ΔΔG, PremPRI2 and structure-model predictions |
| S1664 | Protein–DNA | 1,664 | [Excel](S1664.xlsx), [TSV](S1664.tsv) | Sequence-model training records: mutation, wild-type protein sequence, nucleic acid sequence and experimental ΔΔG |
| S1150 | Protein–RNA | 1,150 | [Excel](S1150.xlsx), [TSV](S1150.tsv) | Sequence-model training records: mutation, wild-type protein sequence, nucleic acid sequence and experimental ΔΔG |

Each TSV is an unmodified value export of the identically named worksheet in its Excel file, preserving column names and row order. The current files replace the earlier combined workbook and TSV schemas. S1150 contains four columns; it has no `Record ID` or `Mutant protein sequence` column.

## Supplementary data

| File | Data worksheets | Contents |
| --- | --- | --- |
| [Supplementary Data S1](Supplementary_Data_S1_10.10.xlsx) | `Revised_records`, `Excluded_records` | 232 revised records (184 DNA, 48 RNA) and 14 excluded records (9 DNA, 5 RNA), with reasons and publication references |
| [Supplementary Data S2](Supplementary_Data_S2_10.10.xlsx) | `S1336`, `S599` | Curated experimental records, chains, mutations, sequences, publication PMIDs, methods, structural resolution and S441/S260 comparison-subset membership |
| [Supplementary Data S3](Supplementary_Data_S3_10.10.xlsx) | `DNA selected features`, `RNA selected features` | Definitions and sources for the 20 DNA and 13 RNA handcrafted features |

## Reading the data

- ΔΔG values are in kcal/mol. Negative values are Stabilizing; zero and positive values are Destabilizing.
- PremPDI2/PremPRI2 columns contain the mean predictions of three forward-trained MLPs. The separate structure-model column contains leave-one-complex-out cross-validation (LOCOV) predictions from forward-trained CatBoost (DNA) or ExtraTrees (RNA).
- S1336/S599 mutation labels use the supplied structural identifiers; mapping may be needed before using a position in a sequence-based input. S1664/S1150 provide the corresponding wild-type protein sequences.
- Sequence separators are preserved exactly as supplied: S1664 uses `&` for multiple nucleic-acid chains; Supplementary Data S2 uses `|`. These research tables are not the five-column CLI input format; see [input examples](../examples/README.md).

## Reproduce the TSV exports

With `openpyxl` installed, run from the repository root:

```bash
python scripts/export_datasets.py
```

The script verifies all seven Excel checksums before exporting the four dataset sheets and regenerating the manifest. It does not modify the Excel workbooks.
