# Reuse the verified runtime and immutable model layers; no model retraining.
FROM ghcr.io/minghuilab/prempni@sha256:befc7207e644c957fb79ff54e5c42ccac27ff53b5ff3f2353b85ee86043fce23

ARG PREMPNI_VERSION=0.2.0
LABEL org.opencontainers.image.title="PremPNI" \
      org.opencontainers.image.version="${PREMPNI_VERSION}" \
      org.opencontainers.image.description="CPU-first PremPNI with website-compatible inputs and results" \
      org.opencontainers.image.source="https://github.com/minghuilab/PremPNI"

ENV PREMPNI_PROTEIN_DEVICE=cpu \
    PREMPNI_NA_DEVICE=cpu \
    PREMPNI_MLP_DEVICE=cpu \
    OMP_NUM_THREADS=8 \
    MKL_NUM_THREADS=8

WORKDIR /opt/prempni
COPY src/ /opt/prempni/
COPY scripts/ /opt/prempni/scripts/
COPY examples/ /opt/prempni/examples/
COPY datasets/ /opt/prempni/datasets/
COPY docs/ /opt/prempni/docs/
COPY README.md LICENSE THIRD_PARTY_NOTICES.md MODEL_MANIFEST.sha256 /opt/prempni/
RUN python -m unittest discover -s tests -p test_web_contract.py
ENTRYPOINT ["python", "/opt/prempni/run_prempni.py"]
CMD ["--help"]
