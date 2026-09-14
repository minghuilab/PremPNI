# Installation and operation

## Run with Docker

```bash
docker pull ghcr.io/minghuilab/prempni:v0.2.1
docker run --rm ghcr.io/minghuilab/prempni:v0.2.1 --help
```

The image currently requires access to the GHCR package. If `docker pull` is denied, sign in with an authorized GitHub account using `docker login ghcr.io`.

PremPNI runs on CPU with 10 threads by default. To use a different number of threads, set both `OMP_NUM_THREADS` and `MKL_NUM_THREADS` when starting the container. See the root [README](../README.md) for DNA, RNA and batch-input commands.

Use Linux x86_64 with Docker Engine 24 or newer. Allow at least 30 GB free disk; 64 GB RAM is a practical starting point for RNA predictions.

## Build from source

```bash
git clone https://github.com/minghuilab/PremPNI.git
cd PremPNI
docker build -t prempni:local .
```

## Check the installation

After cloning, run the bundled DNA and RNA examples:

```bash
bash scripts/smoke_test.sh
```
