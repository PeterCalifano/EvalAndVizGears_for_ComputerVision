# ROS 2 Overlay

The ROS 2 Jazzy overlay is layered on the standalone C++ library. Root CMake
does not discover ROS and `build_lib.sh` remains the baseline build entry point.

## Packages

The overlay contains two packages:

| Package | Role |
|---|---|
| `eval_and_viz_gears` | Plain-CMake colcon shim around the root library. |
| `eval_and_viz_gears_ros` | Target-owned benchmark recorder and ROS adaptation package. |

The generic donor messages, service, lifecycle node, component, spinup package,
and ROS tests are intentionally excluded. `slam_primitives` owns the shared
feature-track interfaces consumed by the recorder.

## Dependency Setup

Use `slam-primitives` revision
`05a9c72be25692c965cf688511ac45107bfd382f`. Build its ROS overlay without
tests, then source it before this project:

```bash
git clone https://github.com/PeterCalifano/slam-primitives.git /tmp/slam-primitives
git -C /tmp/slam-primitives checkout --detach \
  05a9c72be25692c965cf688511ac45107bfd382f
/tmp/slam-primitives/build_ros2.sh --clean --skip-tests --no-version-sync
source /tmp/slam-primitives/ros2/install/setup.bash
```

## Build

```bash
./build_ros2.sh --clean
./build_ros2.sh --packages-select eval_and_viz_gears_ros
./build_ros2.sh --cuda
```

The helper sources `/opt/ros/${ROS_DISTRO:-jazzy}/setup.bash`, synchronizes
package metadata unless `--no-version-sync` is supplied, and runs only
`colcon build`. It never invokes `colcon test`.

Generated colcon output is confined to `ros2/build`, `ros2/install`, and
`ros2/log`. Root `COLCON_IGNORE` markers keep standalone directories outside
package discovery.

## Devcontainer And Standalone Container

The checked-in devcontainer installs ROS 2 Jazzy, the pinned dependency, and
the normal C++ toolchain. Regenerate it deterministically with:

```bash
./configure_devcontainer.sh --ros2 --no-cuda --base ubuntu-24.04
./configure_devcontainer.sh --ros2 --cuda --gpu-runtime docker
```

The same Dockerfile supports one-shot commands and a persistent VS Code
attachment container:

```bash
./run_in_container.sh --ros2 --build -- ./build_ros2.sh --clean
./run_in_container.sh --ros2 --vscode
./run_in_container.sh --matlab-root /path/to/MATLAB/R2024b -- bash
```

MATLAB is mounted read-only only when explicitly requested. No machine-local
MATLAB path is stored in the repository.
