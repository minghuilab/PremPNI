# Website-matched examples

| File | Purpose |
| --- | --- |
| `prempni_dna_example.json` | 2KO0, A39T; 87 aa and two 16 nt DNA chains |
| `prempni_rna_example.json` | 1AUD, K49A; 101 aa and one 30 nt RNA chain |
| `PremPNI_complexes_example.tsv` | Website multi-complex upload: one DNA and one RNA row |
| `run_dna.sh`, `run_rna.sh` | Bash commands for the published single-sample Docker entry point |

The JSON and TSV files were compared with the public website downloads on 2026-09-10. JSON is an input description: the Docker CLI does not accept a JSON filename as a positional argument. The shell scripts expand those values into supported CLI flags and write under the current directory's `output/`.

In the website TSV, `nucleic_acid_sequences` separates chains with `|`; `mutations` contains sequence-indexed substitutions. This is not the schema accepted by the historical research batch script. Mutations are numbered from 1 in the supplied protein sequence, not from PDB residue numbering.

Real CPU results for both examples are recorded in [CPU validation](../docs/installation.md#cpu-validation). The historical numeric fixtures in `scripts/smoke_test.sh` use different inputs.

Both example shell scripts select CPU for all three model stages. They do not request GPU access. Keep the explicit CPU options when copying commands from these scripts.
