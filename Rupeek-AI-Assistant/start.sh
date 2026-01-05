#!/usr/bin/env bash
set -e

echo "🔍 Checking model directory..."
if [ -d "/opt/huggingface/models/intfloat/e5-large-v2" ]; then
    echo "✅ Model is already baked into the Docker image."
else
    echo "❌ ERROR: Model missing inside container!"
    exit 1
fi

echo "Starting Vanna app..."
exec python -m src.main_vanna
