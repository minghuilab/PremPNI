# Installation and operation

## Published image

Local release inspection on 2026-09-10 confirmed PyTorch `2.0.1+cu117` (CUDA 11.7) and verified all 13 model assets against the bundled manifest. The inspected `v0.1.1` and `latest` tags shared digest `sha256:befc7207e644c957fb79ff54e5c42ccac27ff53b5ff3f2353b85ee86043fce23`. This was a local-image inspection, not a fresh registry pull or GPU prediction test.

Use `ghcr.io/minghuilab/prempni:v0.1.1`. The README commands run one prediction per container. Both embedding stages and the MLP can use `cuda:0`; two GPUs are not required.

The existing release guidance recommends Linux x86_64, Docker Engine 24 or newer, NVIDIA Container Toolkit, a driver supporting the packaged CUDA runtime, at least 30 GB free disk and 32 GB RAM (64 GB recommended for RNA). Its suggested GPU memory is 8 GB for DNA and 16 GB for RNA. These are starting recommendations, not guaranteed limits for every sequence length. The local image occupies about 18.9 GB; allow additional space for image extraction, embeddings and outputs.

Before prediction:

```bash
nvidia-smi
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

## Source checkout and builds

```bash
git clone https://github.com/minghuilab/PremPNI.git
cd PremPNI
```

The checkout contains inference source, examples, experimental datasets and a model checksum manifest. It does **not** contain the large `models/` directory or `runtime-env.tar.gz`. The Dockerfile copies those assets from its build context. Therefore `docker build .` from a fresh checkout is not a complete installation procedure, and `pip install -r requirements.txt` alone does not install model weights or recreate the packed environment. Use the published image for the documented end-to-end workflow.

For a maintainer rebuild, provide the release's packed runtime and all model files at the paths listed in `MODEL_MANIFEST.sha256` before building. Do not substitute unrelated checkpoints. The Docker base is CUDA 11.6.1; the packed Python/PyTorch runtime is a separate layer, so the base tag alone does not establish its CUDA requirements.

## Troubleshooting

- Docker daemon connection failure: confirm Docker is running and your account can access it.
- GPU unavailable: check the host NVIDIA driver and NVIDIA Container Toolkit configuration. `--gpus all` requires GPU-enabled Docker.
- Out of memory: GPU/RAM requirements vary with input length; use a less occupied GPU or more memory.
- Mutation validation failure: index the exact supplied sequence from 1 and verify its wild-type residue. A PDB/literature residue number may require mapping.
- Existing output: choose a new `--sample-id`, or use `--overwrite` only when replacing that result is intended.
- A repeated sample ID must not be used as a cache key for changed sequences. Prefer a fresh ID/output directory.

## Regression fixtures and batch scope

`scripts/smoke_test.sh` is a historical numeric regression fixture with its own DNA/RNA inputs and expected values. It uses `cuda:1` for the RNA nucleic-acid stage and therefore assumes at least two visible GPUs as written. Those fixtures differ from the website examples; their expected values must not be assigned to 2KO0 or 1AUD.

`src/run_prempni_batch.py` references research-stage scripts (including `run_esm_dbp_s1345.py` and `run_rinalmo_s604.py`) that are absent from this checkout. Its complete batch pipeline is not a supported fresh-checkout quick start. Use independent single-sample commands or the website's batch interface. The supplementary datasets and website upload TSV use different schemas from that research runner.
