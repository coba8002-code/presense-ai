#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3.12 -m venv .venv-audio
.venv-audio/bin/python -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu
.venv-audio/bin/python -m pip install -r requirements-audio-model.txt -r local_pc/requirements-preprocess.txt
.venv-audio/bin/python -m pip check
