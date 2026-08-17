#!/usr/bin/env bash
set -euo pipefail

if [[ "${INSTALL_CUDA:-off}" != "on" ]]; then
  echo "CUDA toolkit installation disabled"
  exit 0
fi

# shellcheck disable=SC1091
source /etc/os-release
case "${ID:-}-${VERSION_ID:-}" in
  ubuntu-24.04) repo_tag="ubuntu2404" ;;
  ubuntu-22.04) repo_tag="ubuntu2204" ;;
  ubuntu-20.04) repo_tag="ubuntu2004" ;;
  debian-12) repo_tag="debian12" ;;
  *) echo "Unsupported CUDA base: ${ID:-unknown} ${VERSION_ID:-unknown}" >&2; exit 1 ;;
esac

case "$(dpkg --print-architecture)" in
  amd64) repo_arch="x86_64" ;;
  arm64) repo_arch="sbsa" ;;
  *) echo "Unsupported CUDA architecture" >&2; exit 1 ;;
esac

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg
curl -fsSL \
  "https://developer.download.nvidia.com/compute/cuda/repos/${repo_tag}/${repo_arch}/cuda-keyring_1.1-1_all.deb" \
  -o /tmp/cuda-keyring.deb
dpkg -i /tmp/cuda-keyring.deb
rm -f /tmp/cuda-keyring.deb
apt-get update
cuda_version="${CUDA_VERSION:-12.9}"
apt-get install -y --no-install-recommends "cuda-toolkit-${cuda_version//./-}"
apt-get clean
rm -rf /var/lib/apt/lists/*
