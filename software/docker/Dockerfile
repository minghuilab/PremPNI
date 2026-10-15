# Reuse the verified runtime and immutable model layers; no model retraining.
FROM ghcr.io/minghuilab/prempni@sha256:befc7207e644c957fb79ff54e5c42ccac27ff53b5ff3f2353b85ee86043fce23

LABEL org.opencontainers.image.title="PremPNI" \
      org.opencontainers.image.description="CPU-first PremPNI with website-compatible inputs and results" \
      org.opencontainers.image.source="https://github.com/minghuilab/PremPNI"

ENV PREMPNI_PROTEIN_DEVICE=cpu \
    PREMPNI_NA_DEVICE=cpu \
    PREMPNI_MLP_DEVICE=cpu \
    OMP_NUM_THREADS=10 \
    MKL_NUM_THREADS=10

WORKDIR /opt/prempni
COPY software/src/ /opt/prempni/
COPY software/scripts/ /opt/prempni/scripts/
COPY examples/ /opt/prempni/examples/
COPY datasets/ /opt/prempni/datasets/
COPY software/docs/ /opt/prempni/docs/
COPY README.md LICENSE /opt/prempni/
COPY software/licenses/ /opt/prempni/software/licenses/
COPY software/docker/MODEL_MANIFEST.sha256 /opt/prempni/MODEL_MANIFEST.sha256
COPY software/requirements.txt /opt/prempni/requirements.txt
RUN python -m unittest discover -s tests -p test_web_contract.py
ENTRYPOINT ["python", "/opt/prempni/run_prempni.py"]
CMD ["--help"]
