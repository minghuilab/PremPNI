# PremPNI curated datasets

The author-designated release source is [PremPNI_curated_datasets.xlsx](PremPNI_curated_datasets.xlsx), provided on 2026-09-10 from the author's 2026-09-09 curated-data directory. The workbook is distributed byte-for-byte without edits. Four TSV files reproduce every source cell and the original row order.

| Sheet / TSV | Interaction | Rows | Columns |
| --- | --- | ---: | --- |
| [S1664](S1664.tsv) | Protein–DNA | 1,664 | `Mutation`, `Protein_sequence`, `Nucleic_acid_sequence`, `DDG` |
| [S1150](S1150.tsv) | Protein–RNA | 1,150 | `Mutation`, `Protein_sequence`, `Nucleic_acid_sequence`, `DDG` |
| [S1336](S1336.tsv) | Protein–DNA | 1,336 | `PDB_mutation`, `DDG`, `PremPDI2_prediction` |
| [S599](S599.tsv) | Protein–RNA | 599 | `PDB_mutation`, `DDG`, `PremPRI2_prediction` |

Source SHA256: `23efe7455ea7085d9d913f66cae6df04a292398dea1a53991b482ad4e7791248`. The [manifest](manifest.json) records the source hash, TSV hashes, row counts and exact schemas. The total of 4,749 rows is a sum across sheets, not a count of unique experimental observations across datasets.

## Meaning of the columns

- `DDG` is the experimental ΔΔG label, in kcal/mol. Negative means Stabilizing; zero or positive means Destabilizing. Preserve numeric precision when deriving classes.
- `PremPDI2_prediction` and `PremPRI2_prediction` are the author-supplied model prediction columns, also in kcal/mol. They are not experimental labels and were not recomputed for this release. The workbook does not specify their per-row training/test fold provenance or establish that they are fresh web-server results.
- `Mutation` describes a single protein substitution, such as `R355A`. For all 1,664 DNA and 1,150 RNA sequence records, the wild-type residue matches the stated one-based position in `Protein_sequence`.
- `Protein_sequence` contains the supplied wild-type sequence, using the 20 standard amino acids.
- `Nucleic_acid_sequence` contains DNA A/C/G/T or RNA A/C/G/U; `|` separates chains. Supply each chain separately to the CLI, in its supplied order. The website expects each chain in the 5′→3′ direction.
- `PDB_mutation` retains the author's compound identifier, for example `1LMB*3*A49D`. Treat it as text and preserve PDB and chain identifiers. These benchmark sheets do not contain sequences or a verified mapping from PDB/literature numbering to sequence indices.

The provided workbook has no missing/nonfinite DDG or prediction values. Mutation identifiers are unique within S1336 and S599. These validation results do not imply independence of records or remove the need for grouped evaluation.

## Relationship to the website and models

S1664/S1150 provide sequence-and-label records for research reuse. S1336/S599 provide experimental labels and supplied PremPDI2/PremPRI2 predictions. The file has no explicit split assignments, training configurations or checkpoint identifiers; do not infer exact checkpoint training membership from dataset names alone. Publishing this curated workbook does not retrain or replace the deployed models.

These TSVs preserve the workbook schemas. They are not the website's multi-complex upload schema or direct inputs for the historical `run_prempni_batch.py`. For inference, map the sequence columns to CLI flags or the website input fields. For S1336/S599, obtain and verify the corresponding wild-type sequence and residue mapping first. See [website-matched examples](../examples/README.md).

No labels are rounded, imputed or recalculated; no forward/reverse augmentation or row filtering is applied. These exports supersede the uncommitted supplementary-data draft prepared before the author designated this workbook for publication.

## Reproduce and verify

In a separate Python environment with `openpyxl` installed, run from the repository root:

```bash
python scripts/export_datasets.py
```

The script uses the bundled workbook by default. Use `--source /path/to/PremPNI_curated_datasets.xlsx` to select a byte-identical copy, or `--output /path/to/export` to write elsewhere. It rejects unexpected source hashes, sheet schemas, row counts, nonfinite labels/predictions, invalid sequence alphabets and sequence-position mismatches before exporting. Future curated revisions require an explicit update of the pinned source hash and associated documentation.

Repository use terms are in [LICENSE](../LICENSE). The original workbook remains the authoritative source for the values in this release.
