#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  build-essential \
  ccache \
  clang \
  cmake \
  curl \
  doxygen \
  gdb \
  git \
  graphviz \
  libeigen3-dev \
  libopencv-dev \
  libtbb-dev \
  ninja-build \
  pkg-config \
  python3 \
  python3-dev \
  python3-pip \
  python3-pytest \
  sudo

case "${INSTALL_VALGRIND:-off}" in
  on|true|1|yes)
    apt-get install -y --no-install-recommends valgrind
    ;;
esac

apt-get clean
rm -rf /var/lib/apt/lists/*
