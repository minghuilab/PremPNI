# Website-matched examples

| File | Purpose |
| --- | --- |
| `prempni_dna_example.json` | 2KO0, A39T; 87 aa and two 16 nt DNA chains |
| `prempni_rna_example.json` | 1AUD, K49A; 101 aa and one 30 nt RNA chain |
| `PremPNI_complexes_example.tsv` | Website multi-complex upload: one DNA and one RNA row |
| `run_dna.sh`, `run_rna.sh` | CPU-default commands for v0.2.1 |

The JSON and TSV were compared with the public website downloads on 2026-09-10. They are also bundled at `/opt/prempni/examples/` in the image. v0.2.1 accepts them directly with `--input-json` or `--input-tsv`. Both shell scripts use the same inputs and the image's CPU defaults.

The website TSV has five columns: sample_id, complex_type, protein_sequence, nucleic_acid_sequences and mutations. `|` separates nucleic-acid chains and independent mutations. The full TSV is validated before computation; sample IDs and mutations within each complex must be unique. Empty chain/mutation entries are rejected.

Mutations use positions numbered from 1 in the supplied sequence. PDB/literature numbering may require mapping. `--alanine-scan` produces one XnA output row per position, with synthetic zero for an existing alanine. For TXT/CSV/TSV mutation lists, use `--mutation-file`; comments beginning with # and mutation headers are supported.

[CPU validation](../docs/installation.md#model-continuity-and-cpu-baseline) records reference predictions for these inputs. `scripts/smoke_test.sh` checks the same website examples; it does not reuse expected values from unrelated historical examples.
