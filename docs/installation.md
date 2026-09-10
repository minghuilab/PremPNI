# Installation and operation

## Published image

Local release inspection on 2026-09-10 confirmed PyTorch `2.0.1+cu117` (CUDA 11.7) and verified all 13 model assets against the bundled manifest. The inspected `v0.1.1` and `latest` tags shared digest `sha256:befc7207e644c957fb79ff54e5c42ccac27ff53b5ff3f2353b85ee86043fce23`. This was a local-image inspection, not a fresh registry pull or GPU prediction test.

Use `ghcr.io/minghuilab/prempni:v0.1.1`. The README commands run one prediction per container, entirely on CPU. Pass `--protein-device cpu --na-device cpu --mlp-device cpu` and omit Docker GPU options. These explicit settings are required because this image defaults to CUDA for embedding. No NVIDIA driver or NVIDIA Container Toolkit is needed for this CPU workflow. The existing image still contains CUDA libraries; it is not a smaller CPU-only image build.

Use Linux x86_64 and Docker Engine 24 or newer. Plan for at least 30 GB free disk space and substantial host RAM; 64 GB RAM is a practical starting budget, especially for RNA with ESM-2 3B. Actual peak memory and runtime depend on sequence length and CPU resources, so this is not a guarantee for arbitrary inputs. The image occupies about 18.9 GB; allow additional space for extraction, embeddings and outputs. CPU inference can be substantially slower than GPU inference.

The examples set `OMP_NUM_THREADS=8` and `MKL_NUM_THREADS=8` to limit CPU thread oversubscription. Adjust these values for your machine and other workloads.

Before prediction:

```bash
docker pull ghcr.io/minghuilab/prempni:v0.1.1
docker run --rm ghcr.io/minghuilab/prempni:v0.1.1 --help
```

The help command checks the entry point without running model inference. Run the DNA/RNA examples in the root README to exercise actual inference.

To check packaged weights against the image manifest (reads all model assets and may take time):

```bash
docker run --rm --entrypoint python ghcr.io/minghuilab/prempni:v0.1.1 \
  /opt/prempni/scripts/verify_models.py \
  --root /opt/prempni/models \
  --manifest /opt/prempni/MODEL_MANIFEST.sha256
```

## CPU validation

On 2026-09-10, the published v0.1.1 image completed both website examples with all three devices set to `cpu`, no Docker GPU request, eight CPU threads, an eight-core container limit and a 64 GiB memory limit:

| Input | Final ΔΔG (kcal/mol) | Reported pipeline time |
| --- | ---: | ---: |
| 2KO0 A39T (DNA) | 0.5487042169 | 24.7 s |
| 1AUD K49A (RNA) | 0.9141754707 | 103.3 s |

These are real CPU-run results on a shared server, not performance guarantees for other machines or sequence lengths. Times are the pipeline's `timing_seconds.total`, not measured Docker startup-to-exit time. CPU/GPU floating-point results may differ slightly; this check did not run a paired GPU comparison. The 64 GiB setting was a container memory limit, not measured peak consumption.

## Source checkout and builds

```bash
git clone https://github.com/minghuilab/PremPNI.git
cd PremPNI
```

The checkout contains inference source, examples, experimental datasets and a model checksum manifest. It does **not** contain the large `models/` directory or `runtime-env.tar.gz`. The Dockerfile copies those assets from its build context. Therefore `docker build .` from a fresh checkout is not a complete installation procedure, and `pip install -r requirements.txt` alone does not install model weights or recreate the packed environment. Use the published image for the documented end-to-end workflow.

For a maintainer rebuild, provide the release's packed runtime and all model files at the paths listed in `MODEL_MANIFEST.sha256` before building. Do not substitute unrelated checkpoints. The Docker base is CUDA 11.6.1; the packed Python/PyTorch runtime is a separate layer, so the base tag alone does not establish its CUDA requirements.

## Troubleshooting

- Docker daemon connection failure: confirm Docker is running and your account can access it.
- CUDA requested/unavailable: confirm that all three device options are set to `cpu`; removing the Docker GPU option alone does not change the image defaults.
- Out of memory: host RAM requirements vary with input length; increase the memory available to Docker or use a machine with more RAM.
- Mutation validation failure: index the exact supplied sequence from 1 and verify its wild-type residue. A PDB/literature residue number may require mapping.
- Existing output: choose a new `--sample-id`, or use `--overwrite` only when replacing that result is intended.
- A repeated sample ID must not be used as a cache key for changed sequences. Prefer a fresh ID/output directory.

## Regression fixtures and batch scope

`scripts/smoke_test.sh` is a historical numeric regression fixture with its own DNA/RNA inputs and expected values. It uses `cuda:1` for the RNA nucleic-acid stage and therefore assumes at least two visible GPUs as written. Those fixtures differ from the website examples; their expected values must not be assigned to 2KO0 or 1AUD.

`src/run_prempni_batch.py` references research-stage scripts (including `run_esm_dbp_s1345.py` and `run_rinalmo_s604.py`) that are absent from this checkout. Its complete batch pipeline is not a supported fresh-checkout quick start. Use independent single-sample commands or the website's batch interface. The supplementary datasets and website upload TSV use different schemas from that research runner.
