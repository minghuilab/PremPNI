FROM nvidia/cuda:11.6.1-base-ubuntu20.04

ARG PREMPNI_VERSION=0.1.1

LABEL org.opencontainers.image.title="PremPNI" \
      org.opencontainers.image.description="Sequence-based prediction of mutation effects on protein-DNA and protein-RNA interactions" \
      org.opencontainers.image.version="${PREMPNI_VERSION}" \
      org.opencontainers.image.authors="Weikang Sun <20204021010@stu.suda.edu.cn>" \
      org.opencontainers.image.source="https://github.com/minghuilab/PremPNI" \
      org.opencontainers.image.licenses="LicenseRef-PremPNI-Academic-NonCommercial"

COPY runtime-env.tar.gz /tmp/runtime-env.tar.gz
RUN mkdir -p /opt/conda \
    && tar -xzf /tmp/runtime-env.tar.gz -C /opt/conda \
    && rm /tmp/runtime-env.tar.gz \
    && PATH="/opt/conda/bin:${PATH}" /opt/conda/bin/conda-unpack

ENV PATH="/opt/conda/bin:${PATH}" \
    PREMPNI_HOME="/opt/prempni" \
    PREMPNI_MODEL_ROOT="/opt/prempni/models" \
    PREMPNI_OUTPUT_ROOT="/output" \
    TORCH_HOME="/opt/prempni/models/torch" \
    TRANSFORMERS_NO_TF="1" \
    TF_CPP_MIN_LOG_LEVEL="3" \
    PYTHONUNBUFFERED="1"

WORKDIR /opt/prempni

COPY src/ /opt/prempni/
COPY LICENSE THIRD_PARTY_NOTICES.md MODEL_MANIFEST.sha256 /opt/prempni/
COPY third_party_licenses/ /opt/prempni/third_party_licenses/
COPY scripts/ /opt/prempni/scripts/

# Separate model groups into independent OCI layers. This keeps every layer
# below common registry limits and makes model updates less expensive.
COPY models/esm_dbp/ /opt/prempni/models/esm_dbp/
COPY models/hyenadna/ /opt/prempni/models/hyenadna/
COPY models/esm2/ /opt/prempni/models/esm2/
COPY models/rinalmo/ /opt/prempni/models/rinalmo/
COPY models/mlp/ /opt/prempni/models/mlp/

RUN python /opt/prempni/scripts/verify_models.py \
    --root /opt/prempni/models \
    --manifest /opt/prempni/MODEL_MANIFEST.sha256 \
    && mkdir -p /output

VOLUME ["/output"]

ENTRYPOINT ["python", "/opt/prempni/run_prempni_single.py"]
CMD ["--help"]
