#!/usr/bin/env bash
set -Eeo pipefail

ros_mode="${ROS_MODE:-none}"
ros_distro="${ROS_DISTRO:-}"
ros_profile="${ROS_PROFILE:-ros-base}"

if [[ "${ros_mode}" == "none" ]]; then
  exit 0
fi
if [[ "${ros_mode}" != "ros2" ]]; then
  echo "ros-setup.sh: only ROS_MODE=none or ROS_MODE=ros2 is supported" >&2
  exit 1
fi
if [[ "${ros_distro}" != "jazzy" ]]; then
  echo "ros-setup.sh: this project supports ROS 2 Jazzy" >&2
  exit 1
fi
case "${ros_profile}" in
  ros-base|desktop) ;;
  *)
    echo "ros-setup.sh: ROS_PROFILE must be ros-base or desktop" >&2
    exit 1
    ;;
esac

# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
  echo "ros-setup.sh: ROS 2 Jazzy requires Ubuntu 24.04" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  software-properties-common

keyring="/usr/share/keyrings/ros-archive-keyring.gpg"
curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  | gpg --dearmor -o "${keyring}"
architecture="$(dpkg --print-architecture)"
echo "deb [arch=${architecture} signed-by=${keyring}] http://packages.ros.org/ros2/ubuntu ${UBUNTU_CODENAME} main" \
  > /etc/apt/sources.list.d/ros2.list

apt-get update
apt-get install -y --no-install-recommends \
  "ros-${ros_distro}-${ros_profile}" \
  python3-colcon-common-extensions \
  python3-rosdep \
  ros-dev-tools

printf '\nsource /opt/ros/%s/setup.bash\n' "${ros_distro}" \
  >> /etc/bash.bashrc
rosdep init 2>/dev/null || true
rosdep update

apt-get clean
rm -rf /var/lib/apt/lists/*
