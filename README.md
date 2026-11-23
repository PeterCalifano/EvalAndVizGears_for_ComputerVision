# EvalAndVizGears_for_ComputerVision

C++20 components for feature-track visualization, image annotation, match
inspection, and tracking-statistics export. The library is the standalone
rendering/evaluation base that will be consolidated with navigation plotting
work before online middleware integration is added.

## Current Capabilities

- OpenCV feature markers with configurable shapes, colors, opacity, and IDs.
- Track trails with bounded history and optional age fading.
- Composite frame annotation with a tracking HUD and keyframe highlighting.
- Side-by-side or stacked feature-match visualization.
- Interactive OpenCV display windows with pause, step, and quit actions.
- Per-frame tracking statistics with CSV export.
- Dependency-free, thread-safe project logging through
  `viztools::logging::CLogger`.
- Optional CUDA compilation, OpenGL, oneTBB, Python wrappers, and
  MATLAB wrappers.
- Optional ROS 2 Jazzy colcon overlay and reproducible ROS-enabled devcontainer.

The current library provides 2D visualization primitives. Three-dimensional
state visualization, online error/covariance plots, and live navigation data
interfaces remain in the staged development plan under
`doc/developments/ros2_online_visualization_plan.md`.

## Documentation Map

- [`doc/build_script_doc.md`](doc/build_script_doc.md): build helper and feature options.
- [`doc/wrappers.md`](doc/wrappers.md): Python/MATLAB wrapper configuration and ownership.
- [`doc/versioning.md`](doc/versioning.md): semantic version and source-release metadata.
- [`doc/logging.md`](doc/logging.md): dependency-free diagnostics.
- [`doc/documentation_workflow.md`](doc/documentation_workflow.md): Doxygen and Pages flow.
- [`doc/testing_and_ci.md`](doc/testing_and_ci.md): target-owned test and CI boundaries.
- [`doc/ros2_overlay.md`](doc/ros2_overlay.md): ROS 2 and container build workflow.

## Requirements

| Dependency | Requirement | Purpose |
|---|---:|---|
| CMake | 3.15 or newer | Configure and package |
| C++ compiler | C++20 | Library and tests |
| Eigen3 | 3.4 or newer | Public math dependency |
| OpenCV | core, imgproc, highgui, imgcodecs | Rendering and display |
| slam-primitives | snapshot API revision | Public feature-track snapshot types |
| Catch2 | 3.x | C++ tests; optional when tests are disabled |
| Python | 3.12 by default | Python tests and wrapper tooling |
| CUDA Toolkit | 12.0 or newer | Optional CUDA builds |

## Build And Test

Install `slam-primitives` revision
`05a9c72be25692c965cf688511ac45107bfd382f` first and make its CMake package
discoverable:

```bash
cmake -S /path/to/slam-primitives -B /tmp/slam-primitives-build \
  -DCMAKE_INSTALL_PREFIX=/tmp/slam-primitives-install \
  -DENABLE_TESTS=OFF \
  -Dslam-primitives_BUILD_PROGRAMS=OFF \
  -Dslam-primitives_BUILD_EXAMPLES=OFF
cmake --build /tmp/slam-primitives-build --target install --parallel 4

export CMAKE_PREFIX_PATH=/tmp/slam-primitives-install${CMAKE_PREFIX_PATH:+:${CMAKE_PREFIX_PATH}}
```

The default command configures a `RelWithDebInfo` build and runs CTest:

```bash
./build_lib.sh
```

Common variants:

```bash
# Clean debug build with Ninja.
./build_lib.sh --clean -t debug -N

# Portable release build and install into ./install.
./build_lib.sh --clean -t release -i \
  -D CPU_ENABLE_NATIVE_TUNING=OFF

# CUDA build.
./build_lib.sh --clean -D ENABLE_CUDA=ON

# Run one test group after configuring.
ctest --test-dir build --output-on-failure -R logger
```

Optimized native builds enable `-march=native -mtune=native` by default.
Disable `CPU_ENABLE_NATIVE_TUNING` for distributable binaries or when cross
compiling.

`NO_OPTIMIZATION=ON` uses `-O0 -g3`, keeps assertions enabled, preserves frame
pointers, and disables inlining/tail-call optimization for profiler-friendly
debugging.

## Build Options

| CMake option | Default | Meaning |
|---|---:|---|
| `ENABLE_TESTS` | `ON` | Register target-owned C++ runtime tests and optional Python tests |
| `ENABLE_PYTHON_TESTS` | `ON` | Register `test*.py` through CTest |
| `ENABLE_CUDA` | `OFF` | Enable the CUDA language and toolkit interface |
| `ENABLE_OPENGL` | `OFF` | Enable the OpenGL interface |
| `ENABLE_TBB` | `OFF` | Enable oneTBB |
| `ENABLE_PROFILING` | `OFF` | Add profiler-friendly flags and annotations |
| `ENABLE_GPERFTOOLS` | profiling setting | Link the CPU profiler |
| `ENABLE_TCMALLOC` | `OFF` | Link allocator replacement explicitly |
| `SANITIZE_BUILD` | `OFF` | Enable configured sanitizers |
| `NO_OPTIMIZATION` | `OFF` | Force profiler-friendly non-optimized flags |
| `WRITE_SOURCE_VERSION_FILE` | `OFF` | Permit configure to update source `VERSION` |
| `EvalAndVizGears_for_ComputerVision_ENABLE_CUDA` | `OFF` | Canonical CUDA option for nested builds |
| `EvalAndVizGears_for_ComputerVision_BUILD_PROGRAMS` | `ON` | Build in-tree programs |
| `EvalAndVizGears_for_ComputerVision_BUILD_EXAMPLES` | `ON` | Build examples |

Run `./build_lib.sh --help` for script options, including Python-test conda
selection and additional CTest arguments.

## Logging

`CLogger` is always built and has no external logging dependency:

```cpp
#include <utils/logging/CLogger.h>

viztools::logging::CLogger logger(
    "tracker", viztools::logging::ELogLevel::Info);
logger.setLevelFromEnvironment();
logger.info("active tracks: ", active_tracks);
```

Set `EVAL_AND_VIZ_LOG_LEVEL` to `quiet`, `critical`, `error`, `warning`,
`info`, `debug`, `trace`, or the numeric values `0` through `6`. ANSI colors
are disabled unless explicitly selected by the caller.

## Package Consumption

Install the project and consume the exported CMake package:

```cmake
find_package(EvalAndVizGears_for_ComputerVision CONFIG REQUIRED)

target_link_libraries(my_target PRIVATE
  EvalAndVizGears_for_ComputerVision::EvalAndVizGears_for_ComputerVision)
```

Public headers are installed below
`include/EvalAndVizGears_for_ComputerVision`. The same package target is
available from a configured build tree by setting
`EvalAndVizGears_for_ComputerVision_DIR` to the build directory.

## Python And MATLAB Wrappers

Wrapper support uses `gtwrap` from an installed package or a local checkout:

```bash
./build_lib.sh -p
./build_lib.sh -p -m --gtwrap-root /path/to/wrap
```

The project-specific wrapper interface is `src/wrap_interface.i`. Generated
Python packaging uses `python/pyproject.toml.in` and `python/setup.py.in`.
MATLAB wrapper discovery targets R2024b. Generated Python and MATLAB outputs
remain under the build tree and install prefix.

## ROS 2 And Containers

The ROS 2 Jazzy overlay is optional and does not affect the standalone build.
After sourcing the pinned `slam-primitives` ROS install:

```bash
./build_ros2.sh --clean
```

The overlay contains the `eval_and_viz_gears` colcon shim and the existing
`eval_and_viz_gears_ros` recorder bridge. It intentionally imports no donor
example messages, lifecycle nodes, spinup package, or ROS tests.

The checked-in devcontainer uses ROS 2 Jazzy. Regenerate another supported
variant or run a one-shot container command with:

```bash
./configure_devcontainer.sh --ros2 --no-cuda --base ubuntu-24.04
./run_in_container.sh --ros2 --build -- ./build_ros2.sh --clean
./run_in_container.sh --matlab-root /path/to/MATLAB/R2024b -- bash
```

## Versioning And Releases

Version resolution follows Git tags, then an existing `VERSION` file, then the
hardcoded CMake fallback. Tags may carry semantic prerelease and build metadata.

```bash
./generate_version.sh
cmake --build build --target package_source
```

Ordinary CMake configure writes `VERSION` only to the build tree. Source-tree
generation is explicit through `generate_version.sh` or
`WRITE_SOURCE_VERSION_FILE=ON`.

## Documentation

When Doxygen is available, configure and build the `doc` target:

```bash
cmake -S . -B build_docs \
  -DENABLE_TESTS=OFF \
  -DEvalAndVizGears_for_ComputerVision_BUILD_PROGRAMS=OFF \
  -DEvalAndVizGears_for_ComputerVision_BUILD_EXAMPLES=OFF
cmake --build build_docs --target doc
```

Development plans under `doc/developments/` are intentionally excluded from
published API documentation.

## Development Status

The build, wrapper, package, ROS overlay, and container infrastructure is
aligned semantically with signed `cpp_cuda_template_project` v2.0.1 and tailored
to this repository's identity and feature policy. CI and container builds pin
the reviewed `slam-primitives` snapshot. Broader online visualization work
continues through the staged development plan.
