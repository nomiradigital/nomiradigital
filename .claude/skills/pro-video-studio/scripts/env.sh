# source this: sets paths for the pro video toolset
export PVS_PY=/opt/video-tools/pro/.venv/bin/python
export PATH=/opt/video-tools/pro/.venv/bin:$PATH
export HF_HOME=/opt/video-tools/models/hf HF_HUB_DISABLE_XET=1
export SSL_CERT_FILE=${SSL_CERT_FILE:-/root/.ccr/ca-bundle.crt} REQUESTS_CA_BUNDLE=${REQUESTS_CA_BUNDLE:-/root/.ccr/ca-bundle.crt}
export PVS_MODELS=/opt/video-tools/models PVS_RNNOISE=/opt/video-tools/rnnoise-models
export PVS=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
