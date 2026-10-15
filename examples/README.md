# Usage and input formats

Run commands from the repository root. The launcher saves results in `output/` and mounts the local `input/` directory as `/input/` when present.

## Examples

| File | Purpose |
| --- | --- |
| [prempni_dna_example.json](prempni_dna_example.json) | 2KO0, A39T; 87 aa and two 16 nt DNA chains |
| [prempni_rna_example.json](prempni_rna_example.json) | 1AUD, K49A; 101 aa and one 30 nt RNA chain |
| [PremPNI_complexes_example.tsv](PremPNI_complexes_example.tsv) | One DNA and one RNA complex |
| [run_dna.sh](run_dna.sh), [run_rna.sh](run_rna.sh) | Runnable Docker commands |

```bash
bash examples/run_dna.sh
bash examples/run_rna.sh

bash software/scripts/prempni.sh --input-json /opt/prempni/examples/prempni_dna_example.json
bash software/scripts/prempni.sh --input-tsv /opt/prempni/examples/PremPNI_complexes_example.tsv
```

## Custom inputs

Adapt an example JSON or TSV, save it in `input/`, then run:

```bash
bash software/scripts/prempni.sh --input-json /input/request.json
# Or:
bash software/scripts/prempni.sh --input-tsv /input/complexes.tsv
```

Protein sequences use the 20 standard amino acids; DNA uses A/C/G/T and RNA uses A/C/G/U. Supply nucleic-acid chains in the 5′→3′ direction. Mutation positions start at 1 in the supplied wild-type protein sequence; PDB/literature numbering may require mapping.

Example input notation (`A2V`: alanine at position 2 replaced by valine):

```text
Protein sequence: MAGKRVLSDYEKLQNFDPATVREAIKQLGVEKDSNVRFYTPEEIRKALDAGADVVVT
Mutation:         A2V
DNA sequence:     ACGTACGT
```

The website TSV has five columns: sample_id, complex_type, protein_sequence, nucleic_acid_sequences and mutations. `|` separates nucleic-acid chains and independent mutations. The full TSV is validated before computation; sample IDs and mutations within each complex must be unique. Empty chain/mutation entries are rejected.

## Mutation lists and scanning

In the [DNA command](run_dna.sh), replace `--mutation A39T` with one of:

- `--mutations 'A39T|A39V'`: independent mutations in input order.
- `--mutation-file /input/mutations.txt`: TXT/CSV/TSV mutation list; comments beginning with `#` and mutation headers are supported.
- `--alanine-scan`: one XnA row per protein position. Existing alanines return `0.000`, Destabilizing, `computed=false`, without model computation.

## Output

```text
2KO0 A39T PremPDI2: 0.549 Destabilizing [completed]
```

ΔΔG is reported in kcal/mol. Results include `prempni_prediction.csv`, `prempni_prediction.json` and `job.json`:

- DNA example: `output/protein_dna/2KO0/prediction/`
- RNA example: `output/protein_rna/1AUD/prediction/`
- Multiple complexes: `output/collections/JOB_ID/`

[The smoke test](../software/scripts/smoke_test.sh) records and checks reference CPU predictions for these website examples. See the [installation check](../software/docs/installation.md#check-the-installation) for the command.
