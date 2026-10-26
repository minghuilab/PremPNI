# Usage and input formats

Run commands from the repository root. The launcher mounts this repository's `Examples/` as `/examples/` (read-only), saves results in `output/`, and mounts a local `input/` directory as `/input/` when present.

## Examples

| File | Purpose |
| --- | --- |
| [prempni_dna_example.json](prempni_dna_example.json) | DNA M1A; 272 aa and two 14 nt DNA chains |
| [prempni_rna_example.json](prempni_rna_example.json) | RNA M1A; 282 aa and one 29 nt RNA chain |
| [PremPNI_complexes_example.tsv](PremPNI_complexes_example.tsv) | One DNA and one RNA complex, three independent mutations each |
| [PremPNI_upload_example_dna.txt](PremPNI_upload_example_dna.txt) | DNA mutation list: M1A, F3A, Y6A |
| [PremPNI_upload_example_rna.txt](PremPNI_upload_example_rna.txt) | RNA mutation list: M1A, P4A, R7A |
| [run_dna.sh](run_dna.sh), [run_rna.sh](run_rna.sh) | Runnable Docker commands |

```bash
bash Examples/run_dna.sh
bash Examples/run_rna.sh

bash Examples/prempni.sh --input-json /examples/prempni_dna_example.json
bash Examples/prempni.sh --input-json /examples/prempni_rna_example.json
bash Examples/prempni.sh --input-tsv /examples/PremPNI_complexes_example.tsv
```

## Custom inputs

Adapt an example JSON or TSV, save it in `input/`, then run:

```bash
bash Examples/prempni.sh --input-json /input/request.json
# Or:
bash Examples/prempni.sh --input-tsv /input/complexes.tsv
```

Protein sequences use the 20 standard amino acids; DNA uses A/C/G/T and RNA uses A/C/G/U. Supply nucleic-acid chains in the 5′→3′ direction. Mutation positions start at 1 in the supplied wild-type protein sequence; PDB/literature numbering may require mapping.

`M1A` replaces methionine at sequence position 1 with alanine.

For command-line input, `--sample-id` is optional and defaults to a unique generated name. Add `--sample-id my_sample` to choose a name. Reusing an explicit name requires `--overwrite` to replace its results.

The website TSV has five columns: sample_id, complex_type, protein_sequence, nucleic_acid_sequences and mutations. `|` separates nucleic-acid chains and independent mutations. The full TSV is validated before computation; sample IDs and mutations within each complex must be unique. Empty chain/mutation entries are rejected.

For JSON and TSV files, include a `sample_id` for each complex.

## Mutation lists and scanning

In the [DNA command](run_dna.sh), replace `--mutation M1A` with one of:

- `--mutations 'M1A|F3A|Y6A'`: independent mutations in input order.
- `--mutation-file /examples/PremPNI_upload_example_dna.txt`: TXT/CSV/TSV mutation list; comments beginning with `#` and mutation headers are supported.
- `--alanine-scan`: one XnA row per protein position. Existing alanines return `0.000`, Destabilizing, `computed=false`, without model computation.

For RNA, use `M1A|P4A|R7A` or `/examples/PremPNI_upload_example_rna.txt`.

## Output

```text
<sample_id> M1A PremPDI2: 0.329 Destabilizing [completed]
<sample_id> M1A PremPRI2: -0.541 Stabilizing [completed]
```

ΔΔG is reported in kcal/mol. Results include `prempni_prediction.csv`, `prempni_prediction.json` and `job.json`:

- Command-line DNA example: `output/protein_dna/<sample_id>/prediction/`
- Command-line RNA example: `output/protein_rna/<sample_id>/prediction/`
- JSON example: `<sample_id>` is the name specified in the JSON file.
- Multiple complexes: `output/collections/JOB_ID/`
