# Input File Format

For Docker setup and the prediction command, see the [installation and usage instructions](../README.md#prempni-installation-and-usage-instructions).

## Example Files

Save an example as `input/input.tsv` in your local `prempni` working folder.

| File | Contents |
| --- | --- |
| [PremPNI_complexes_example.tsv](PremPNI_complexes_example.tsv) | One DNA and one RNA prediction |
| [prempni_dna_example.tsv](prempni_dna_example.tsv) | DNA M1A; 272 amino acids and two 14 nt DNA chains |
| [prempni_rna_example.tsv](prempni_rna_example.tsv) | RNA M1A; 282 amino acids and one 29 nt RNA chain |
| [PremPNI_prediction_example.tsv](PremPNI_prediction_example.tsv) | Reference output for the combined DNA/RNA example |

## Five-Column Format

The first line contains the column names. Separate columns with a **Tab**, and use `&` between nucleic acid chains.

```text
Job Name	Type	Wild-Type Protein Sequence	Nucleic Acid Sequence	Mutation
DNA_example	DNA	MNFFEYCISTYAKIFEETMNAVGDERVSQKKAIRDTMISAMREFPNVEAAEIWKAVYSAHMDRKSGIADPDIIQKVISAENSWKKSSGHAFEEMIKLLGNSSLEEYGMRILLQKDLNMMIENQEIANEPRDINWLKEQISSNVFDLYITVRNNDKEYVFGCIQSKTSIRDRVTRDREPSMKAMEAFFWSVAICLDGDFLKMPKFIAMVNGGTSNYRLNGWHGMYVFWDKPTIDRIYPIDINLELFVQHAREAAEDWLHRRQWFNYEWKAGQK	CTCGACCGGTCGAG&CTCGACCGGTCGAG	M1A
RNA_example	RNA	MAVPETRPNHTIYINNLNEKIKKDELKKSLYAIFSQFGQILDILVSRSLKMRGQAFVIFKEVSSATNALRSMQGFPFYDKPMRIQYAKTDSDIIAKMKGTFVERDRKREKRKPKSQETPATKKAVQGGGATPVVGAVQGPVPGMPPMTQAPRIMHHMPGQPPYMPPPGMIPPPGLAPGQIPPGAMPPQQLMPGQMPPAQPLSENPPNHILFLTNLPEETNELMLSMLFNQFPGFKEVRLVPGRHDIAFVEFDNEVQAGAARDALQGFKITQNNAMKISFAKK	GGCAGAUCUGAGCCUGGGAGCUCUCUGCC	M1A
```

| Column | Description |
| --- | --- |
| Job Name | Unique row name; start with a letter or number and use letters, numbers, dots, underscores or hyphens |
| Type | DNA or RNA |
| Wild-Type Protein Sequence | Complete wild-type protein sequence using the 20 standard amino acids |
| Nucleic Acid Sequence | DNA: A/C/G/T; RNA: A/C/G/U; write each chain in the 5′→3′ direction |
| Mutation | One substitution, such as M1A; numbering starts at 1 in the supplied protein sequence |

To test several substitutions, put each one on a separate row and give each row a different Job Name. Do not combine substitutions within a cell. Input order is preserved.

## Run the File

```bash
docker run --rm \
  -v "$PWD/input:/input:ro" \
  -v "$PWD/output:/output" \
  ghcr.io/minghuilab/prempni \
  --input-tsv /input/input.tsv
```

All rows are checked before prediction starts. Empty chains, invalid sequences, duplicate Job Names and mutations that do not match the wild-type sequence are rejected.

## Output

The main result file is `output/collections/JOB_ID/prempni_prediction.tsv`. It is Tab-separated and preserves the original five input columns, including `&` between nucleic acid chains, in the original row order. Two result columns are appended:

| Added Column | Meaning |
| --- | --- |
| Predicted ΔΔG (kcal/mol) | Predicted binding affinity change, displayed to three decimal places |
| Predicted effect | Stab: ΔΔG < 0; Des: ΔΔG ≥ 0, using the value before rounding |

See the [complete reference output](PremPNI_prediction_example.tsv). Failed predictions keep their input row with the two result cells empty; details are recorded in `job.json`.
