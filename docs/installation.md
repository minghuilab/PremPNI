# Installation and operation

## CPU-default image

The image has been uploaded, but the GHCR package currently remains private. An authorized account must first run `docker login ghcr.io`; an administrator will handle changing the package to public. Repository visibility and container-package visibility are separate.

```bash
docker pull ghcr.io/minghuilab/prempni:v0.2.0
docker run --rm ghcr.io/minghuilab/prempni:v0.2.0 --help
docker run --rm ghcr.io/minghuilab/prempni:v0.2.0 --version
```

All stages default to CPU, with `OMP_NUM_THREADS=8` and `MKL_NUM_THREADS=8`. No GPU device flags, NVIDIA driver or NVIDIA Container Toolkit are needed. Adjust the thread environment variables for your machine. The default entry point is `run_prempni.py`; it supports single mutations, lists, scans, website JSON and website multi-complex TSV. See the root [README](../README.md) for commands.

Use Linux x86_64 and Docker Engine 24 or newer. Allow at least 30 GB free disk and substantial RAM; 64 GB is a practical starting budget for RNA with ESM-2 3B, not a guarantee for arbitrary sequence lengths. The inherited runtime/model layers occupy about 18.9 GB. CPU inference can be slower than GPU inference, and large mutation scans require repeated calculations.

## Model continuity and CPU baseline

The image inherits the immutable v0.1.1 layers at digest `sha256:befc7207e644c957fb79ff54e5c42ccac27ff53b5ff3f2353b85ee86043fce23`. These contain PyTorch 2.0.1+cu117 (CUDA 11.7) and the same embedding and final MLP weights. Including CUDA libraries does not make GPU hardware necessary for CPU execution.

On 2026-09-10, v0.1.1 completed the website examples on CPU with eight threads, an eight-core container limit and a 64 GiB memory limit:

| Input | Final ΔΔG (kcal/mol) | Model-reported pipeline time |
| --- | ---: | ---: |
| 2KO0 A39T | 0.5487042169 | 24.7 s |
| 1AUD K49A | 0.9141754707 | 103.3 s |

These are reference predictions and timings on a shared server, not guarantees for other machines. v0.2.0 reports end-to-end local processing time, including worker startup. The memory limit was not a peak-memory measurement. CPU/GPU arithmetic may differ slightly.

Verify the inherited model assets:

```bash
docker run --rm --entrypoint python ghcr.io/minghuilab/prempni:v0.2.0 \
  /opt/prempni/scripts/verify_models.py \
  --root /opt/prempni/models --manifest /opt/prempni/MODEL_MANIFEST.sha256
```

## Rebuild from GitHub

```bash
git clone https://github.com/minghuilab/PremPNI.git
cd PremPNI
docker build -t prempni:local .
```

The v0.2.0 Dockerfile reuses the pinned public base image, then copies updated code, documentation, examples and curated datasets. A fresh checkout can therefore build this interface release without separately supplying `models/` or `runtime-env.tar.gz`. Network access to the base image is required unless cached. The scientific weights are not rebuilt or retrained. `requirements.txt` documents the inherited inference dependencies; installing it alone does not supply model weights.

## Verification and failures

Run the interface contract tests without loading models:

```bash
docker run --rm --entrypoint python ghcr.io/minghuilab/prempni:v0.2.0 \
  -m unittest discover -s tests -p test_web_contract.py
```

After cloning, `bash scripts/smoke_test.sh` runs the two bundled website examples on CPU and checks their predictions against the verified references. It writes a new smoke-test directory, so previous outputs are retained.

Invalid input is rejected before computation. Inference failures and timeouts preserve all requested rows and completed predictions; failed rows have a blank CSV value/classification and an error in JSON (also in collection CSV). Exit codes are 0 for success, 1 for inference failures, and 2 for invalid input/output conflicts. `--timeout` sets the per-mutation timeout in seconds (default 14,400).

If memory is exhausted, use a machine with more RAM or increase Docker's memory allowance. If an output already exists, use a new sample ID or explicitly request `--overwrite`. A `.running` lock prevents concurrent writes even with overwrite; after a forced termination, confirm no process is still using that output before removing a stale lock. A forced kill may leave a last-known running status or temporary embeddings; it is not a completed prediction.

The historical `run_prempni_batch.py` and research helper modules remain for provenance. The supported list/scanning/collection entry point is now `run_prempni.py`, which does not depend on the absent research-stage scripts.
