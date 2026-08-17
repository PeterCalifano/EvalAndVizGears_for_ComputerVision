#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEVCONTAINER_DIR="${ROOT_DIR}/.devcontainer"
DOCKERFILE="${DEVCONTAINER_DIR}/Dockerfile"
DEVCONTAINER_JSON="${DEVCONTAINER_DIR}/devcontainer.json"
JSON_WRITER="${DEVCONTAINER_DIR}/update_devcontainer_json.py"
BASE_OPTIONS=(ubuntu-24.04 ubuntu-22.04 ubuntu-20.04 debian-12)
GPU_RUNTIME_OPTIONS=(auto docker podman)
ROS_PROFILE_OPTIONS=(ros-base desktop)

usage() {
  cat <<'EOF'
Usage: ./configure_devcontainer.sh [options]

Options:
  --cuda               Enable the NVIDIA CUDA devcontainer feature.
  --no-cuda            Disable the CUDA feature and GPU run arguments.
  --cuda-version <v>   CUDA feature version (default: 12.9).
  --gpu-runtime <r>    GPU runtime: auto, docker, or podman (default: auto).
  --base <name>        Base: ubuntu-24.04, ubuntu-22.04, ubuntu-20.04, debian-12.
  --base-image <img>   Full base image reference; overrides --base.
  --ros2               Enable ROS 2 Jazzy in the image.
  --no-ros             Disable ROS in the image (default).
  --ros-profile <p>    ROS 2 profile: ros-base or desktop (default: ros-base).
  --non-interactive    Accepted for compatibility; this command is non-interactive.
  -h, --help           Show this help.

Examples:
  ./configure_devcontainer.sh --no-cuda --base ubuntu-24.04
  ./configure_devcontainer.sh --cuda --cuda-version 12.9 --gpu-runtime docker
  ./configure_devcontainer.sh --cuda --gpu-runtime podman
  ./configure_devcontainer.sh --ros2 --no-cuda --base ubuntu-24.04
EOF
}

contains_value() {
  local requested="$1"
  shift
  local candidate
  for candidate in "$@"; do
    [[ "${candidate}" == "${requested}" ]] && return 0
  done
  return 1
}

resolve_gpu_runtime() {
  if [[ "$1" != "auto" ]]; then
    printf '%s\n' "$1"
  elif command -v docker >/dev/null 2>&1; then
    printf 'docker\n'
  elif command -v podman >/dev/null 2>&1; then
    printf 'podman\n'
  else
    printf 'docker\n'
  fi
}

CUDA=off
CUDA_VERSION=12.9
GPU_RUNTIME=auto
BASE=ubuntu-24.04
BASE_IMAGE=""
ROS_MODE=none
ROS_DISTRO=""
ROS_PROFILE=ros-base

while (($# > 0)); do
  case "$1" in
    --cuda) CUDA=on ;;
    --no-cuda) CUDA=off ;;
    --cuda-version) shift; CUDA_VERSION="${1:-}" ;;
    --gpu-runtime) shift; GPU_RUNTIME="${1:-}" ;;
    --base) shift; BASE="${1:-}" ;;
    --base-image) shift; BASE_IMAGE="${1:-}" ;;
    --ros2) ROS_MODE=ros2; ROS_DISTRO=jazzy ;;
    --no-ros) ROS_MODE=none; ROS_DISTRO="" ;;
    --ros-profile) shift; ROS_PROFILE="${1:-}" ;;
    --non-interactive) ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
  shift
done

[[ -n "${CUDA_VERSION}" ]] || { echo "CUDA version cannot be empty" >&2; exit 2; }
contains_value "${GPU_RUNTIME}" "${GPU_RUNTIME_OPTIONS[@]}" || {
  echo "Unsupported GPU runtime: ${GPU_RUNTIME}" >&2
  exit 2
}
contains_value "${ROS_PROFILE}" "${ROS_PROFILE_OPTIONS[@]}" || {
  echo "Unsupported ROS profile: ${ROS_PROFILE}" >&2
  exit 2
}
if [[ -z "${BASE_IMAGE}" ]]; then
  contains_value "${BASE}" "${BASE_OPTIONS[@]}" || {
    echo "Unsupported base: ${BASE}" >&2
    exit 2
  }
  if [[ "${ROS_MODE}" == "ros2" && "${BASE}" != "ubuntu-24.04" ]]; then
    echo "ROS 2 Jazzy requires --base ubuntu-24.04" >&2
    exit 2
  fi
  BASE_IMAGE="mcr.microsoft.com/devcontainers/cpp:1-${BASE}"
fi

[[ -f "${DOCKERFILE}" ]] || { echo "Missing ${DOCKERFILE}" >&2; exit 1; }
[[ -f "${JSON_WRITER}" ]] || { echo "Missing ${JSON_WRITER}" >&2; exit 1; }

resolved_runtime="$(resolve_gpu_runtime "${GPU_RUNTIME}")"
dockerfile_tmp="$(mktemp)"
json_tmp="$(mktemp)"
trap 'rm -f "${dockerfile_tmp}" "${json_tmp}"' EXIT

awk -v replacement="FROM ${BASE_IMAGE}" '
  BEGIN { replaced = 0 }
  /^FROM[[:space:]]+/ && replaced == 0 { print replacement; replaced = 1; next }
  { print }
  END { if (replaced == 0) exit 1 }
' "${DOCKERFILE}" > "${dockerfile_tmp}"
chmod --reference="${DOCKERFILE}" "${dockerfile_tmp}"

CUDA="${CUDA}" CUDA_VERSION="${CUDA_VERSION}" \
DEVCONTAINER_GPU_RUNTIME="${resolved_runtime}" \
ROS_MODE="${ROS_MODE}" ROS_DISTRO="${ROS_DISTRO}" \
ROS_PROFILE="${ROS_PROFILE}" \
DEVCONTAINER_JSON_PATH="${DEVCONTAINER_JSON}" \
python3 "${JSON_WRITER}" > "${json_tmp}"
if [[ -f "${DEVCONTAINER_JSON}" ]]; then
  chmod --reference="${DEVCONTAINER_JSON}" "${json_tmp}"
else
  chmod 0644 "${json_tmp}"
fi

mv "${dockerfile_tmp}" "${DOCKERFILE}"
mv "${json_tmp}" "${DEVCONTAINER_JSON}"
trap - EXIT
echo "Updated devcontainer (${CUDA}, ${resolved_runtime}, ${ROS_MODE}, ${BASE_IMAGE})"
