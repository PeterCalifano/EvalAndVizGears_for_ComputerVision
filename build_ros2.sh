#!/usr/bin/env bash
# Build the optional ROS 2 overlay without coupling ROS to the standalone build.

set -Eeuo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${SCRIPT_DIR}"
WORKSPACE_DIR="${ROOT_DIR}/ros2"
ROS_DISTRO_NAME="${ROS_DISTRO:-jazzy}"

build_type="RelWithDebInfo"
clean=false
enable_cuda=false
metadata_sync=true
packages_select=()
cmake_args=()
colcon_args=()

info() { printf '\033[34m[INFO]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[WARN]\033[0m %s\n' "$*" >&2; }
die() { printf '\033[31m[ERROR]\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage:
  ./build_ros2.sh [options]

Build the ROS 2 overlay under ros2/. The standalone C++ library continues to
use ./build_lib.sh and never requires ROS.

Options:
  --clean                    Remove ros2/build, ros2/install, and ros2/log first.
  --debug                    Use CMAKE_BUILD_TYPE=Debug.
  --release                  Use CMAKE_BUILD_TYPE=Release.
  --relwithdebinfo           Use CMAKE_BUILD_TYPE=RelWithDebInfo (default).
  --build-type <type>        Use an explicit CMake build type.
  --packages-select <pkg...> Build selected packages.
  --cuda                     Enable CUDA in the nested standalone core.
  --cmake-arg <arg>          Append one CMake argument. Repeatable.
  --colcon-arg <arg>         Append one colcon build argument. Repeatable.
  --no-version-sync          Do not synchronize ROS package metadata.
  -h, --help                 Show this help.

The overlay intentionally contains no ROS test phase. Source the install from
the pinned slam-primitives ROS overlay before invoking this helper.
EOF
}

parse_args() {
  while (($# > 0)); do
    case "$1" in
      --clean)
        clean=true
        shift
        ;;
      --debug)
        build_type="Debug"
        shift
        ;;
      --release)
        build_type="Release"
        shift
        ;;
      --relwithdebinfo)
        build_type="RelWithDebInfo"
        shift
        ;;
      --build-type)
        [[ $# -ge 2 ]] || die "--build-type requires a value"
        build_type="$2"
        shift 2
        ;;
      --packages-select)
        shift
        [[ $# -gt 0 && "$1" != --* ]] ||
          die "--packages-select requires at least one package"
        while [[ $# -gt 0 && "$1" != --* ]]; do
          packages_select+=("$1")
          shift
        done
        ;;
      --cuda)
        enable_cuda=true
        shift
        ;;
      --cmake-arg)
        [[ $# -ge 2 ]] || die "--cmake-arg requires a value"
        cmake_args+=("$2")
        shift 2
        ;;
      --colcon-arg)
        [[ $# -ge 2 ]] || die "--colcon-arg requires a value"
        colcon_args+=("$2")
        shift 2
        ;;
      --no-version-sync)
        metadata_sync=false
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown argument: $1"
        ;;
    esac
  done
}

source_ros_environment() {
  local setup_file_="/opt/ros/${ROS_DISTRO_NAME}/setup.bash"

  if [[ ! -f "${setup_file_}" ]]; then
    die "ROS setup file not found: ${setup_file_}. Use the ROS devcontainer or set ROS_DISTRO to an installed distro."
  fi

  set +u
  # shellcheck disable=SC1090
  source "${setup_file_}"
  set -u

  command -v colcon >/dev/null 2>&1 ||
    die "colcon was not found after sourcing ${setup_file_}"
}

sync_ros2_package_metadata() {
  [[ "${metadata_sync}" == true ]] || return 0

  if [[ ! -x "${ROOT_DIR}/generate_version.sh" ]]; then
    warn "generate_version.sh is missing or not executable; keeping existing package metadata"
    return
  fi

  "${ROOT_DIR}/generate_version.sh" --sync-ros2
}

clean_workspace_outputs() {
  [[ "${clean}" == true ]] || return 0

  local output_dir_
  for output_dir_ in build install log; do
    if [[ -e "${WORKSPACE_DIR}/${output_dir_}" ]]; then
      info "Removing ros2/${output_dir_}"
      rm -rf -- "${WORKSPACE_DIR:?}/${output_dir_}"
    fi
  done
}

run_colcon_build() {
  local cuda_flag_="OFF"
  local build_cmd_=(colcon build --symlink-install)

  [[ "${enable_cuda}" == true ]] && cuda_flag_="ON"

  if ((${#packages_select[@]} > 0)); then
    build_cmd_+=(--packages-select "${packages_select[@]}")
  fi
  if ((${#colcon_args[@]} > 0)); then
    build_cmd_+=("${colcon_args[@]}")
  fi
  build_cmd_+=(
    --cmake-args
    "-DCMAKE_BUILD_TYPE=${build_type}"
    "-DEVAL_AND_VIZ_GEARS_ENABLE_CUDA=${cuda_flag_}"
    "${cmake_args[@]}"
  )

  info "Workspace : ${WORKSPACE_DIR}"
  info "ROS distro: ${ROS_DISTRO_NAME}"
  info "Build type: ${build_type}"
  info "CUDA      : ${cuda_flag_}"

  (
    cd "${WORKSPACE_DIR}"
    "${build_cmd_[@]}"
  )
}

main() {
  parse_args "$@"

  [[ -d "${WORKSPACE_DIR}" ]] ||
    die "ROS 2 workspace directory not found: ${WORKSPACE_DIR}"
  source_ros_environment
  clean_workspace_outputs
  sync_ros2_package_metadata
  run_colcon_build
}

main "$@"
