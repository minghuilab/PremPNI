# Website and standalone inference

Checked against the website source and release records on 2026-09-10. Latest recorded frontend release: `20260910-readability-v6`; CSV precision release: `20260910-csv-precision-v5`.

| Behavior | Website | Standalone image |
| --- | --- | --- |
| DNA/RNA model names | PremPDI2 / PremPRI2 | `complex_type=dna/rna`, final `mean_ddg` |
| Scientific output | Final three-model ensemble ΔΔG, kcal/mol | Same ensemble design in source |
| Negative / non-negative | Stabilizing / Destabilizing | stabilizing mutation / destabilizing mutation |
| Rounding | Display and CSV: three decimals; classify before rounding | JSON/CSV retain numeric precision |
| Input | Wild-type protein, one or more 5′→3′ chains, sequence-indexed mutation | Same sequence contract via CLI flags |
| Examples | 2KO0 A39T and 1AUD K49A | Matching inputs under `examples/` |
| Job management | Queue, Job ID, result lookup and optional email | Local output directory |
| Lists/scanning/collections | Supported by web services | Default container entry point runs one mutation |

Website alanine scanning reports existing alanine positions as synthetic zero ΔΔG rows, classified as Destabilizing, without invoking the model for those rows. Do not interpret them as measured or inferred effects. Website failure rows without a prediction have no classification.

The website runs a separately deployed inference pipeline. Matching model names and source architecture alone do not prove that every deployed file or checkpoint is byte-identical to a Docker release. Use checkpoint hashes and matched-input inference to establish numerical equivalence. This documentation update does not rebuild the image, retrain models or deploy website changes.

Help illustrations are explicitly illustrative; they are not reference model predictions. Website status polling and typography releases do not change model identity.

On 2026-09-10, SHA256 checks of the six final MLP checkpoint files at the website inference pipeline's configured default model paths matched this repository's manifest (three DNA and three RNA). All 13 assets in the local v0.1.1 Docker image also passed its bundled manifest check. This confirms the checked final MLP weights; a full matched-input end-to-end prediction was not run during this documentation audit.
