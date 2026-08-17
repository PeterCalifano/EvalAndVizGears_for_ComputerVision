FROM mcr.microsoft.com/devcontainers/cpp:1-ubuntu-24.04

ARG REINSTALL_CMAKE_VERSION_FROM_SOURCE="none"
ARG ROS_MODE="none"
ARG ROS_DISTRO=""
ARG ROS_PROFILE="ros-base"

COPY ./reinstall-cmake.sh /tmp/reinstall-cmake.sh
RUN if [ "${REINSTALL_CMAKE_VERSION_FROM_SOURCE}" != "none" ]; then \
      chmod +x /tmp/reinstall-cmake.sh \
      && /tmp/reinstall-cmake.sh "${REINSTALL_CMAKE_VERSION_FROM_SOURCE}"; \
    fi \
    && rm -f /tmp/reinstall-cmake.sh

ARG INSTALL_VALGRIND="off"
ARG VALGRIND_VERSION="3.27.1"
COPY ./custom-setup.sh /tmp/custom-setup.sh
RUN chmod +x /tmp/custom-setup.sh \
    && INSTALL_VALGRIND="${INSTALL_VALGRIND}" VALGRIND_VERSION="${VALGRIND_VERSION}" /tmp/custom-setup.sh \
    && rm -f /tmp/custom-setup.sh

# ROS 2 remains an explicit image layer selected by configure_devcontainer.sh
# or run_in_container.sh --ros2.
COPY ./ros-setup.sh /tmp/ros-setup.sh
RUN chmod +x /tmp/ros-setup.sh \
    && ROS_MODE="${ROS_MODE}" ROS_DISTRO="${ROS_DISTRO}" \
       ROS_PROFILE="${ROS_PROFILE}" /tmp/ros-setup.sh \
    && rm -f /tmp/ros-setup.sh

ARG SLAM_PRIMITIVES_REVISION="05a9c72be25692c965cf688511ac45107bfd382f"
COPY ./project-dependencies.sh /tmp/project-dependencies.sh
RUN chmod +x /tmp/project-dependencies.sh \
    && ROS_MODE="${ROS_MODE}" ROS_DISTRO="${ROS_DISTRO}" \
       SLAM_PRIMITIVES_REVISION="${SLAM_PRIMITIVES_REVISION}" \
       /tmp/project-dependencies.sh \
    && rm -f /tmp/project-dependencies.sh

# Standalone image builds can install CUDA through build arguments. VS Code
# devcontainers use the NVIDIA feature configured in devcontainer.json.
ARG INSTALL_CUDA="off"
ARG CUDA_VERSION="12.9"
COPY ./cuda-setup.sh /tmp/cuda-setup.sh
RUN chmod +x /tmp/cuda-setup.sh \
    && INSTALL_CUDA="${INSTALL_CUDA}" CUDA_VERSION="${CUDA_VERSION}" /tmp/cuda-setup.sh \
    && rm -f /tmp/cuda-setup.sh

ENV CUDA_HOME=/usr/local/cuda
ENV PATH=/usr/local/cuda/bin:${PATH}
ENV SLAM_PRIMITIVES_ROOT=/opt/slam-primitives-src
ENV CMAKE_PREFIX_PATH=/opt/slam-primitives-src/ros2/install:/opt/slam-primitives
ENV AMENT_PREFIX_PATH=/opt/slam-primitives-src/ros2/install
ENV LD_LIBRARY_PATH=/opt/slam-primitives-src/ros2/install/lib:/usr/local/cuda/lib64
ENV PYTHONPATH=/opt/slam-primitives-src/ros2/install/local/lib/python3.12/dist-packages

RUN echo "export GPG_TTY=\$(tty)" >> /etc/bash.bashrc
