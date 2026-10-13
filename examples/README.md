# Website-matched examples

| File | Purpose |
| --- | --- |
| `prempni_dna_example.json` | 2KO0, A39T; 87 aa and two 16 nt DNA chains |
| `prempni_rna_example.json` | 1AUD, K49A; 101 aa and one 30 nt RNA chain |
| `PremPNI_complexes_example.tsv` | Website multi-complex upload: one DNA and one RNA row |
| `run_dna.sh`, `run_rna.sh` | Runnable DNA and RNA examples using the Docker launcher |

The JSON and TSV are bundled at `/opt/prempni/examples/` in the image. Use them with `--input-json` or `--input-tsv`. Both shell scripts use the same inputs and save results in `output/` through `scripts/prempni.sh`.

The website TSV has five columns: sample_id, complex_type, protein_sequence, nucleic_acid_sequences and mutations. `|` separates nucleic-acid chains and independent mutations. The full TSV is validated before computation; sample IDs and mutations within each complex must be unique. Empty chain/mutation entries are rejected.

Mutations use positions numbered from 1 in the supplied sequence. PDB/literature numbering may require mapping. `--alanine-scan` produces one XnA output row per position, with synthetic zero for an existing alanine. For TXT/CSV/TSV mutation lists, use `--mutation-file`; comments beginning with # and mutation headers are supported.

[The smoke test](../scripts/smoke_test.sh) records and checks reference CPU predictions for these website examples. See the [installation check](../docs/installation.md#check-the-installation) for the command.
