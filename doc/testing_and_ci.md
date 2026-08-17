# Testing

CTest is the single test entry point for target-owned Catch2 C++ tests and
pytest files:

```bash
./build_lib.sh --clean
ctest --test-dir build --output-on-failure
```

Python tests can run through the detected interpreter, an explicit executable,
or a conda environment/prefix. Select these through `build_lib.sh` or the
`PYTHON_TEST_*` CMake cache variables. Environment and prefix selectors are
mutually exclusive.

The target-owned test suite covers this repository's runtime code: logging,
image annotations, feature overlays, tracks, matches, feature-track snapshot
adaptation, and CSV statistics. Template-conformance tests for compiler flags,
version scripts, source releases, workflow templates, devcontainers, and
tailoring belong to `cpp_cuda_template_project` and its testfield; they are not
copied into this derived repository.

Infrastructure changes are still validated through their real entry points:
clean configure/build/install commands, wrapper generation, documentation
generation, structured-file parsing, shell syntax, and active CI runs as
applicable.

CUDA CI must remain opt-in on an explicitly enabled runner. CPU CI must not
require a CUDA toolkit or GPU.

CPU, CUDA, ROS, and container paths pin `slam-primitives` revision
`05a9c72be25692c965cf688511ac45107bfd382f`. The optional ROS overlay is
build-only: it contains no registered ROS tests and CI does not invoke
`colcon test`. Existing standalone target-owned CTest coverage remains the
runtime regression gate.
