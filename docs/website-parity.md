# Website and Docker

Docker implements the website's scientific input and result conventions described below.

| Behavior | Shared contract |
| --- | --- |
| DNA / RNA models | PremPDI2 / PremPRI2; final mean of three MLPs |
| Classification | Negative: Stabilizing; zero or positive: Destabilizing, determined before rounding |
| Display and CSV | Three decimals, including exact halfway rounding consistent with JavaScript toFixed |
| JSON | Raw numeric prediction retained; Docker also provides prediction_display |
| Sequences | Wild-type protein, one or more 5′→3′ chains, one-based sequence mutation position |
| Input validation | 20 standard amino acids; DNA A/C/G/T; RNA A/C/G/U; valid and unique chain/sample identifiers; matching wild-type residue |
| Lengths | Up to 5,000 protein residues, 32 nucleic-acid chains and 10,000 total nucleotides, matching current web configuration |
| Examples | 2KO0 A39T and 1AUD K49A, bundled inside the image |
| Mutation lists | Ordered independent single-site substitutions; duplicates rejected |
| Alanine scanning | One row per protein position; A-to-A rows are synthetic zero, Destabilizing, computed=false |
| Multiple complexes | The same five-column website TSV; DNA/RNA can be mixed |
| Failure output | No numeric prediction and no stability classification; retain error and input |
| Downloads | Full inputs, final ensemble predictions and timing; no individual submodel predictions in public result files |

The six final MLP checkpoint hashes were verified against the website inference pipeline. All 13 assets in the base image passed the manifest check; the Dockerfile inherits these immutable model layers. CPU and GPU arithmetic can differ slightly. The smoke test checks the bundled examples against reference CPU predictions.

Docker now defaults to CPU, records local Job IDs, submission/start/completion timestamps and progress in `job.json`, and preserves results in the mounted output directory. Jobs run sequentially within that invocation. The website supplies a shared queue, public result lookup and email notifications; these hosted-service functions are not installed or configured by the local CLI. Local Job IDs are not public website Job IDs. Docker's total processing time includes subprocess startup and local model loading, so it need not match server job latency.

The website batches model calculations; Docker isolates independent mutations in subprocesses for predictable memory lifetime. Both implement the same mutation semantics, while throughput and job scheduling differ. CSV failure status is recorded per mutation in Docker collections so successful rows remain usable even when another mutation fails.
