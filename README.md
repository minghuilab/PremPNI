# PremPNI

PremPNI predicts binding ΔΔG (kcal/mol) for single-site protein mutations: **PremPDI2** for DNA and **PremPRI2** for RNA. Inputs are protein and nucleic acid sequences plus mutations; no 3D structure is required. Mutations are evaluated independently.

[Web server](https://lilab.jysw.suda.edu.cn/research/PremPNI/) · [Installation](software/docs/installation.md) · [Usage and input formats](examples/README.md)

## Quick start

Linux x86_64 or WSL2 with Docker. The image includes the runtime and model weights.

GHCR package access is currently required; authenticate with an authorized account via `docker login ghcr.io`.

```bash
git clone https://github.com/minghuilab/PremPNI.git
cd PremPNI
docker pull ghcr.io/minghuilab/prempni
bash software/scripts/prempni.sh --help

bash examples/run_dna.sh  # 2KO0 / A39T
bash examples/run_rna.sh  # 1AUD / K49A
```

CSV/JSON results are saved under `output/`. Expected DNA example output:

```text
2KO0 A39T PremPDI2: 0.549 Destabilizing [completed]
```

## Datasets

| Excel | Interaction | Records |
| --- | --- | ---: |
| [S1664](datasets/S1664.xlsx) | Protein–DNA | 1,664 |
| [S1150](datasets/S1150.xlsx) | Protein–RNA | 1,150 |
| [S1336](datasets/S1336.xlsx) | Protein–DNA | 1,336 |
| [S599](datasets/S599.xlsx) | Protein–RNA | 599 |

See the [data guide](datasets/README.md) for contents.

## License

Academic, non-commercial use only. [License](LICENSE) · [Third-party notices](software/licenses/THIRD_PARTY_NOTICES.md).
