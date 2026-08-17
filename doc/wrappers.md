# Python And MATLAB Wrappers

Wrapper generation uses gtwrap and the target-owned interface declaration in
`src/wrap_interface.i`. Generated wrappers are build artifacts and are not
committed.

## Configuration

Use an installed gtwrap package or select a local checkout explicitly:

```bash
./build_lib.sh -B build_python --clean -N -p \
  --gtwrap-root /path/to/wrap --no-wrap-update

./build_lib.sh -B build_matlab --clean -N -m \
  --gtwrap-root /path/to/wrap --no-wrap-update
```

`-p` enables the Python wrapper and `-m` enables the MATLAB wrapper. The build
helper resolves local gtwrap roots, installed packages, and declared submodules
according to the options documented by `./build_lib.sh --help`.
Updates and submodule initialization are opt-in maintenance actions.

## Python Packaging

Python metadata is generated from `python/pyproject.toml.in` and
`python/setup.py.in`. Python 3.12 is the default supported interpreter. A wrapper
build is only meaningful after `src/wrap_interface.i` exposes target-owned
visualization DTOs or classes; infrastructure-only generation does not prove API
coverage.

The configured package is staged under `${PROJECT_BINARY_DIR}/python`; wrapper
configuration never writes `setup.py`, `pyproject.toml`, generated modules, or
runtime libraries into the source `python/` directory.

## MATLAB Boundary

MATLAB wrappers must expose ROS-independent C++ data adaptation or rendering
APIs. ROS 2 message construction and publication belong to the integration
layer. Do not move estimator/front-end computation into this repository to make
it wrapper-accessible.

MATLAB discovery targets R2024b. The toolbox destination is the relative
install path `matlab`. Installed gtwrap layouts that expose
`include/gtwrap/matlab.h` are adapted through the build-owned
`gtwrap_include_bridge/wrap/matlab.h`; neither the gtwrap installation nor the
source tree is modified.

For MATLAB MEX consumers, keep allocator replacement disabled. Profiling flags
may be enabled explicitly, but `ENABLE_TCMALLOC` remains opt-in because imposing
an alternate allocator on MATLAB is unsafe.

## Docstrings

Enable `BUILD_DOC_XML` and `GTWRAP_ADD_DOCSTRINGS` together to feed Doxygen XML
into generated Python docstrings. The documentation build must complete before
wrapper generation consumes the XML directory.
