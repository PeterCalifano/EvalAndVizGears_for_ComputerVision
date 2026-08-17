# Build Script Reference

`build_lib.sh` provides one entry point for configuring, building, testing, and
optionally installing the project. Run `./build_lib.sh --help` for the canonical
option list.

## Common Workflows

Configure a portable CPU build with Ninja and run all tests:

```bash
./build_lib.sh -B build --clean -N -DCPU_ENABLE_NATIVE_TUNING=OFF
```

Configure a CUDA build:

```bash
./build_lib.sh -B build_cuda --clean -N \
  -DENABLE_CUDA=ON \
  -DCPU_ENABLE_NATIVE_TUNING=OFF
```

Build and install after tests pass:

```bash
./build_lib.sh -B build --clean -i
```

Rebuild an existing configured tree without rerunning CMake:

```bash
./build_lib.sh -B build --rebuild-only
```

## Build Selection

- `-B, --buildpath <dir>` selects the build directory.
- `-t, --type <type>` selects `Debug`, `Release`, `RelWithDebInfo`, or
  `MinSizeRel`.
- `-j, --jobs <count>` controls build and test parallelism.
- `-N, --ninja-build` selects Ninja.
- `--clean` removes the build tree before configuration.
- `-r, --rebuild-only` skips configuration.
- `-D, --define <name=value>` forwards a CMake cache definition and may be
  repeated.
- `-f, --flagsCXX <flags>` appends compiler flags.
- `--toolchain <file>` forwards `CMAKE_TOOLCHAIN_FILE`.

Tests are enabled by default. Use `--skip-tests` when a configure/build-only
iteration is intentional. `--ctest-extra-args` accepts a quoted,
whitespace-separated argument string that is appended to CTest.

Relative build paths resolve against the checkout containing `build_lib.sh`.
`--clean` accepts only a conventional build path inside that checkout and
refuses to remove a directory whose CMake cache belongs to another source tree.

## Python Tests

Python CTest entries use the configured Python interpreter by default. Exactly
one execution selector may be supplied:

```bash
./build_lib.sh --python-test-executable /usr/bin/python3
./build_lib.sh --python-test-conda-env navigation
./build_lib.sh --python-test-conda-prefix /opt/conda/envs/navigation
```

The CMake configuration rejects conflicting environment-name, environment-prefix,
or direct-interpreter selections.

## Wrappers

Use `-p` for the Python wrapper and `-m` for the MATLAB wrapper. A local gtwrap
checkout can be selected explicitly:

```bash
./build_lib.sh -p -m --gtwrap-root /path/to/wrap
```

The project wrapper interface is `src/wrap_interface.i`. Wrapper generation is
disabled when no valid interface or gtwrap installation is available.
Wrapper checkout updates and declared-submodule initialization are disabled by
default; request them explicitly with `--wrap-update` and
`--wrap-submodule-init`.

## Profiling

`--profile` enables profiling-friendly compiler flags and requests the CPU
profiler integration. Allocator replacement remains independent and disabled by
default because it is unsafe to impose on MATLAB MEX consumers.

The corresponding CMake options are:

- `ENABLE_PROFILING`
- `ENABLE_GPERFTOOLS`
- `ENABLE_TCMALLOC`

## Portability

Optimized builds enable host-native CPU tuning by default. Disable it for CI,
binary distribution, or cross-machine artifacts:

```bash
./build_lib.sh -DCPU_ENABLE_NATIVE_TUNING=OFF
```

The script uses CMake's generator-independent build and install commands and
CTest's `--test-dir` interface. It does not assume Makefiles.
