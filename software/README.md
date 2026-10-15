# PremPNI software

| Directory | Contents |
| --- | --- |
| [src](src/) | Prediction code and tests |
| [scripts](scripts/) | Docker launcher and validation utilities |
| [docs](docs/installation.md) | Installation and usage details |
| [docker](docker/) | Docker build files and model asset manifest |
| [licenses](licenses/THIRD_PARTY_NOTICES.md) | Third-party notices and license texts |

See the root [README](../README.md) for runnable examples. Build from the repository root with:

```bash
docker build -f software/docker/Dockerfile -t prempni:local .
```
