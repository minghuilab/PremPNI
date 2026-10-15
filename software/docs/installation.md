# Installation and operation

## Run with Docker

```bash
git clone https://github.com/minghuilab/PremPNI.git
cd PremPNI
docker pull ghcr.io/minghuilab/prempni
bash software/scripts/prempni.sh --help
```

The image currently requires access to the GHCR package. If `docker pull` is denied, sign in with an authorized GitHub account using `docker login ghcr.io`.

The launcher uses the image's CPU defaults, saves results in `output/`, and makes files in the local `input/` directory available as `/input/` inside the container. See the [README](../../README.md) for DNA, RNA and batch-input commands.

Use Linux x86_64 with Docker Engine 24 or newer. Allow at least 30 GB free disk; 64 GB RAM is a practical starting point for RNA predictions.

## Build from source

```bash
docker build -f software/docker/Dockerfile -t prempni:local .
```

## Check the installation

After cloning, run the bundled DNA and RNA examples:

```bash
bash software/scripts/smoke_test.sh
```
