#!/usr/bin/env bash
set -Eeuo pipefail

revision="${SLAM_PRIMITIVES_REVISION:-05a9c72be25692c965cf688511ac45107bfd382f}"
source_root="/opt/slam-primitives-src"
install_root="/opt/slam-primitives"
build_root="/tmp/slam-primitives-build"

git clone https://github.com/PeterCalifano/slam-primitives.git "${source_root}"
git -C "${source_root}" checkout --detach "${revision}"

cmake -S "${source_root}" -B "${build_root}" -GNinja \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_INSTALL_PREFIX="${install_root}" \
  -DENABLE_TESTS=OFF \
  -Dslam-primitives_BUILD_PROGRAMS=OFF \
  -Dslam-primitives_BUILD_EXAMPLES=OFF \
  -DCPU_ENABLE_NATIVE_TUNING=OFF
cmake --build "${build_root}" --target install --parallel 4
rm -rf "${build_root}"

if [[ "${ROS_MODE:-none}" == "ros2" ]]; then
  ros_distro="${ROS_DISTRO:-jazzy}"
  set +u
  # shellcheck disable=SC1090
  source "/opt/ros/${ros_distro}/setup.bash"
  set -u
  "${source_root}/build_ros2.sh" --clean --skip-tests --no-version-sync
  printf '\nsource %s/ros2/install/setup.bash\n' "${source_root}" \
    >> /etc/bash.bashrc
fi
