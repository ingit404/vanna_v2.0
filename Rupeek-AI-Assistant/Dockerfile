FROM python:3.11-slim-bookworm


RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git git-lfs && \
    rm -rf /var/lib/apt/lists/*


COPY fortinet_root.pem /usr/local/share/ca-certificates/fortinet_root.crt
RUN update-ca-certificates

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt

RUN python -m pip install --upgrade pip


COPY requirements.txt .

RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.5.1"


RUN pip install --no-cache-dir -r requirements.txt

RUN pip install "vanna[postgres]"

ENV HF_HOME=/opt/huggingface \
    TRANSFORMERS_CACHE=/opt/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/opt/huggingface

RUN mkdir -p /opt/huggingface/models/intfloat/e5-large-v2 && chmod -R 777 /opt/huggingface

# DOWNLOAD MODEL DURING BUILD (NOT AT RUNTIME)
RUN python - <<'EOF'
from huggingface_hub import snapshot_download
print("📥 Downloading model: intfloat/e5-large-v2")
snapshot_download(
    "intfloat/e5-large-v2",
    local_dir="/opt/huggingface/models/intfloat/e5-large-v2",
    local_dir_use_symlinks=False
)
print("✅ Model download complete!")
EOF

WORKDIR /app

COPY src/ /app/src/
COPY config.yaml /app/config.yaml

ENV PYTHONPATH=/app/src

EXPOSE 5000


COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]