# Repository Guidelines

## Scope And Ownership

This repository owns reusable C++ visualization, annotation, plotting, logging,
wrapper, package, and development-environment infrastructure for computer-vision
evaluation. Treat sibling repositories in the parent development workspace as
read-only references unless the user explicitly includes them in the implementation scope.
Edit the root owning repository, never a mirrored or nested checkout.

Before editing:

- confirm the repository root, branch, `HEAD`, and `git status --short`;
- read this file, `README.md`, and the applicable plan under
  `doc/developments/`;
- treat every pre-existing modification as user-owned;
- identify which repository owns each cross-repository contract.

For long-running work, keep durable state in the applicable document under
`doc/developments/`. Re-read this file and that plan after context compaction or
an interrupted session. Do not create donor-style `CONTEXT.md` or other ad hoc
root state files in this derived project.

Never revert, overwrite, stage, commit, or push user changes without explicit
authorization. Do not commit or push unless the user asks for that operation in
this repository.

## Architecture Boundaries

The standalone C++ library is the baseline and must remain independently
buildable. Keep algorithm and estimator ownership in their source repositories;
this project owns rendering, visualization-facing data adaptation, and analysis
utilities only when the contract is explicitly assigned here.

ROS 2 and external viewer consolidation is governed by
`doc/developments/ros2_online_visualization_plan.md`. Do not add middleware
packages, topics, viewers, or container dependencies ahead of the approved plan
stage. Preserve the existing MATLAB plotting path as a fallback until an
external path has semantic and performance evidence.

Maintain these distinctions:

- image/feature/track rendering versus front-end feature computation;
- diagnostics logging versus tracking-statistics/CSV output;
- actual/control/boresight quantities versus estimator knowledge quantities;
- source estimator values versus visualization-derived geometry;
- standalone library dependencies versus optional integration-layer
  dependencies.

Intentional feature removals recorded in the development plan remain absent
unless the user explicitly changes that policy. In particular, do not restore
OptiX, ZeroMQ, or spdlog while aligning with the parent template.

The current ROS 2 surface is the `ros2/eval_and_viz_gears/` colcon shim, the
target-owned `ros2/eval_and_viz_gears_ros/` bridge, and metadata tooling under
`ros2/tools/`. Root CMake remains ROS-independent. The donor's placeholder
interfaces, lifecycle example, spinup package, rollout helper, and ROS tests
remain absent. ROS 2 Jazzy container and workflow support are approved project
infrastructure.

## Project Layout

- `src/core/`: OpenCV rendering and visualization primitives.
- `src/utils/logging/`: dependency-free project diagnostics.
- `src/utils/wrap_adapters/`: public wrapper-facing type adapters.
- `src/wrap_interface.i`: gtwrap API declaration surface.
- `tests/core/`: tests for this repository's visualization, adaptation,
  statistics, and logging behavior.
- `doc/`: maintained public documentation.
- `doc/developments/`: internal plans and implementation evidence; excluded
  from generated public documentation.
- `.devcontainer/` and `.github/workflows/`: target-owned development and CI
  automation.

Do not commit generated builds, installs, wrappers, documentation output,
archives, caches, bytecode, IDE databases, or machine-local configuration.

## Build And Test Commands

Run commands from the repository root.

```bash
./build_lib.sh -B build --clean -N -DCPU_ENABLE_NATIVE_TUNING=OFF
ctest --test-dir build --output-on-failure
```

Applicable feature gates include:

```bash
./build_lib.sh -B build_cuda --clean -N \
  -DENABLE_CUDA=ON -DCPU_ENABLE_NATIVE_TUNING=OFF
cmake --preset docs -DDOC_WARN_AS_ERROR=ON
cmake --build --preset docs
./build_lib.sh -B build_wrap --clean -N -p \
  --gtwrap-root /path/to/wrap --no-wrap-update
```

Use `./generate_version.sh` before creating a canonical source archive. Ordinary
CMake configure must leave the source `VERSION` unchanged. Package or export
changes require both build-tree and install-tree consumer tests plus no-Git
source-archive validation.

Before handoff, run all applicable checks:

- complete CTest suite from a clean CPU build;
- focused CUDA, wrapper, documentation, container, and package gates when those
  surfaces changed;
- structured parsing for JSON, JSONC, YAML, XML, and TOML changes;
- `bash -n` for changed shell scripts;
- `git diff --check`;
- exact conflict-marker, stale-identity, machine-local-path, generated-artifact,
  executable-bit, and feature-policy scans.

Record unavailable external gates as partial or blocked. Do not describe an
unrun gate as passing, and compare failures and warnings with the recorded
baseline rather than reporting only a raw test count.

## C++ And CUDA Conventions

Use C++20 and the existing `viztools` namespace. Follow established target
naming: `C` for behavior-owning classes, `S` for data/configuration structures,
and `E` for enums. Prefer concepts over SFINAE when a compile-time constraint is
needed. Keep public headers under the existing install layout and use target-based
CMake dependencies so installed exports remain relocatable.

Use OpenCV's BGR convention explicitly at rendering boundaries. Never introduce
an implicit RGB/BGR conversion. Preserve native image resolution unless a
display-only scale is explicitly configured.

CUDA is optional and independent of the CPU build. Keep ordinary `.cu`
translation units distinct from dedicated `*.ptx.cu` inputs. Never expose local
toolkit paths through installed targets.

Add short comments only for non-obvious ownership, synchronization, color-space,
or lifetime behavior. Prefer a direct local change over a helper that is used
once and does not simplify the contract.

## Python And MATLAB Conventions

Use Python 3.12 or newer for repository tooling. Follow this target's established
snake_case function and method naming even where the donor template uses a
different Python convention. Require type hints on every new callable and use
Google-style module, class, method, and function docstrings. Prefer dataclasses
over unstructured dictionaries and enums over multi-value literal sets.

Use matplotlib for ordinary plots, Pillow or OpenCV for image processing, and
seaborn for statistical plots when those dependencies are justified by the
feature. Use PyTorch with scikit-learn support for machine-learning work and
preserve ONNX export compatibility when a model is intended for deployment. Do
not introduce any of these as unconditional dependencies merely because the
parent guidance mentions them. New public Python functionality should include a
runnable example and expected output. Do not commit generated wrapper modules.

For MATLAB code added to an approved integration stage, follow the owning MATLAB
repository's conventions and preserve host-only plotting versus code-generated
algorithm boundaries. Evaluate whether state is genuinely required before
introducing a class; functions are preferred for stateless computation. Use
`self` for methods and do not nest function definitions.

MATLAB names use PascalCase and established type prefixes: `d` for double, `f`
for single, `b` for logical, `char` for text, `str` for structures, `ui8`/`i8`
and corresponding widths for integers, `obj` for objects, `cell` for cell arrays,
`table` for tables, and `bus_` for Simulink buses. Function and static-method
names start with a capital letter; file-local functions end with `_`. Names must
describe purpose, and short temporary names are acceptable only in a genuinely
local scope. Algorithmic MATLAB code must remain code-generation safe where
required and keep identifiers within the 31-character code-generation limit.

Public MATLAB functions and methods require `arguments` and `arguments (Output)`
blocks plus the repository's `SIGNATURE`, `DESCRIPTION`, `INPUT`, `OUTPUT`,
`CHANGELOG`, and `DEPENDENCIES` sections. Scripts require an opening sectioned
description, and class files require class help text. Do not move estimator or
front-end computation into this visualization repository merely to simplify
plotting.

## Testing And Review

Use Catch2 for C++ runtime behavior owned by this repository. Do not import or
recreate tests whose subject is `cpp_cuda_template_project` infrastructure;
template-conformance belongs to the parent template and its testfield. Add
focused semantic regressions for this repository's code before or with behavior
changes. For cross-repository seams, test the actual consumer path rather than a
substitute fixture whenever the environment permits.

The consolidation workflow is staged review: stage one coherent functional
batch, inspect the complete index with `git diff --cached`, and hand it to the
user with a proposed commit title and bullet description. Do not commit or push.
This workflow does not authorize staging `.vscode/`, generated artifacts, or
unrelated user changes.

For every new or substantially changed source file:

- keep module/file documentation and public API documentation accurate;
- organize code into coherent blocks with one immediate objective each;
- comment non-obvious ownership, invariant, synchronization, and failure-policy
  decisions rather than narrating individual statements;
- preserve useful existing comments unless the changed behavior invalidates
  them;
- review the resulting whole file in target context, not only edited lines.

Use Doxygen for C++/CUDA public APIs, Google-style docstrings for Python public
callables, and the repository's sectioned function/class documentation for
MATLAB. Keep this cleanup within the intended change scope and summarize any
documentation or readability work during handoff.

For C++ and CUDA, use Doxygen file-level documentation and public API
documentation. Group related statements into visually separated blocks with one
immediate objective. Introduce non-obvious blocks with concise comments about
purpose, ownership, invariants, synchronization, color order, lifetime, or
failure policy; do not translate individual statements into prose.

Treat template upgrades as a three-way semantic port:

```text
updated target = current target + applicable donor intent
```

Never replace the target with the newest donor tree. Follow this authority order:
the current user request, target instructions and plans, target architecture and
tests, campaign plan, derivation guidance, then donor implementation. Preserve
project identity, public APIs, option defaults, dependency policy, CI ownership,
and intentional absences. A donor path absent from the target remains absent
until repository history or the user establishes that it belongs here.

Classify donor deltas as adopted, adapted, deferred, source-only, rejected, or
blocked and document the reason. Stop and report when a donor improvement would
change target architecture, dependency ownership, public API, or established
tailoring instead of presenting that change as routine alignment.

Inspect every changed file in target context before handoff. Keep the persistent
development plan current with commands, exact totals, warnings, residual risks,
and proposed functional commit groups. Do not create ad hoc root context files;
use the existing plan for durable implementation state.
