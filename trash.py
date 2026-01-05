# FROM python:3.11-slim-bookworm

# RUN apt-get update && apt-get install -y --no-install-recommends \
#     ca-certificates curl git git-lfs && \
#     rm -rf /var/lib/apt/lists/*

# COPY fortinet_root.pem /usr/local/share/ca-certificates/fortinet_root.crt
# RUN update-ca-certificates

# ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
#     REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
#     PIP_CERT=/etc/ssl/certs/ca-certificates.crt

# RUN python -m pip install --upgrade pip

# # ------------------------------
# # (1) Verify SSL trust store
# RUN python - <<'PY'
# import ssl, os
# print("SSL_CERT_FILE =", os.environ.get("SSL_CERT_FILE"))
# ctx = ssl.create_default_context()
# print("CA Certificates Loaded =", len(ctx.get_ca_certs()))
# PY

# # (2) Verify PyTorch CPU index is reachable
# RUN python - <<'PY'
# import urllib.request
# urllib.request.urlopen("https://download.pytorch.org/whl/cpu/").read(20)
# print("✅ PyTorch index reachable")
# PY
# # ------------------------------

# COPY requirements.txt .

# # Install Torch (test with known-good version first)
# RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.5.1"

# RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install "vanna[postgres]"

# ENV HF_HOME=/opt/huggingface \
#     TRANSFORMERS_CACHE=/opt/huggingface \
#     SENTENCE_TRANSFORMERS_HOME=/opt/huggingface
# RUN mkdir -p /opt/huggingface && chmod -R 777 /opt/huggingface

# WORKDIR /app
# COPY src/ /app/src/
# COPY config.yaml /app/config.yaml
# ENV PYTHONPATH=/app/src

# EXPOSE 5000

# COPY start.sh /app/start.sh
# RUN chmod +x /app/start.sh

# CMD ["/app/start.sh"]


#trial docker file