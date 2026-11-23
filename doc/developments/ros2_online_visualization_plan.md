# ROS 2 Online Visualization And Plot Management Plan

## Document Status

- Created: 2026-05-30
- Last reviewed: 2026-08-17
- Target repository: `/home/peterc/devDir/dev-tools/EvalAndVizGears_for_ComputerVision`
- Source-of-truth sibling repositories for investigation and import planning:
  - `/home/peterc/devDir/nav-backend`
  - `/home/peterc/devDir/nav-frontend`
  - `/home/peterc/devDir/nav-system`
  - `/home/peterc/devDir/projects-DART/cosmica-simulator`
  - `/home/peterc/devDir/dev-tools/cpp_cuda_template_project`
  - `/home/peterc/devDir/projects-DFKI/hyper_2`
- Rule for this plan: use the root repositories under `/home/peterc/devDir` as the implementation references. Nested or submodule copies, such as a backend checkout visible from `nav-system`, must be treated as integration wiring points only until their equivalence to the root checkout is verified.
- Stage 0 status: repository and cross-repository design audit completed for planning purposes. No fatal design conflict was found, but several implementation gates were identified and must be handled before code migration.
- Stage 0 review update: repeated the plan review, re-checked COSMICA path assumptions, completed the original standalone alignment from `cpp_cuda_template_project` tag `v1.11.1`, and incrementally rebased the current target onto stable tag `v1.11.3` at commit `f3fd6555c7c965eebc89d5aa40227b0f36ac5fde`.
- Stage 2 status: the prior v1.11.3 consolidation is being upgraded to signed
  `cpp_cuda_template_project` v2.0.1. The approved batch includes the adapted
  ROS colcon shim, ROS 2 Jazzy container/tooling, R2024b wrappers, and pinned
  `slam-primitives`; donor example interfaces, lifecycle behavior, spinup, and
  ROS tests remain excluded.
- Stage 2 validation summary: the original import passed its historical 52/52
  CPU/CUDA suite and broader template-infrastructure gates. After applying the
  stricter derivation boundary, the current target-owned suite contains 44
  runtime cases; all 44 pass together with both real examples, strict Doxygen
  HTML/XML, installation, and an external installed-package consumer.
- Stable donor rule: use the signed `v2.0.1` tag at
  `1d87153b2d060bf03c2c9adcd1df6c6d4f40ea09` for current alignment
  decisions. The prior tags remain historical baselines only.
- Donor working-tree note: the donor checkout was clean on `main` at the `v1.11.3` tag during the incremental review. Only committed tagged content was considered.
- Donor ownership rule: do not edit `cpp_cuda_template_project` during target alignment. Its package names, release version, template-only plans, optional four-package overlay shape, and retained OptiX support are donor-owned details, not derived-project defaults.
- Derived-project rule: apply v2.0.1 as a three-way semantic port. Preserve this
  repository's project identity, `viztools` API, OpenCV behavior,
  target-owned tests and recorder, and intentional feature removals.
- Current-pass ordering: keep root CMake independent from ROS while adding the
  explicitly approved colcon shim, build-only ROS workflow, and ROS-enabled
  devcontainer. Do not import the donor package quartet or placeholder runtime
  behavior.
- Explicit feature policy for the aligned target:
  - keep CUDA support where it is already relevant;
  - remove OptiX support and all advertised OptiX options;
  - remove ZeroMQ support rather than retaining a fallback transport;
  - remove the external spdlog dependency and legacy adapter;
  - keep Pangolin absent; its optional CMake discovery, linkage, compile
    definition and package export were removed, and the legacy prototype
    remains only as preserved history;
  - adapt the dependency-free `CLogger` from `v1.11.1` into `viztools::logging`;
  - keep the standalone non-ROS build as the Stage 2 acceptance baseline.

## Primary Goal

Move online plot management out of the MATLAB simulation thread where practical, while preserving the current MATLAB algorithms and plot semantics. The new path should publish visualization and analysis data from MATLAB through ROS 2 interfaces and render externally using C++/OpenCV, RViz, PlotJuggler, and optional Foxglove-compatible tooling.

The system must support:

- online image display at algorithm resolution;
- centroid overlays;
- extracted feature overlays;
- feature-track overlays with length-dependent color mapping;
- arbitrary track count;
- 3D visualization of estimated quantities, trajectories, target frame geometry, landmarks, ROIs, and covariance;
- online plots of estimation errors, residuals, covariance, empirical covariance, and additional state errors;
- local and remote visualization;
- low-blocking or non-blocking behavior when viewers are slow, missing, or disconnected;
- existing MATLAB plotting as a fallback until the ROS 2 path is validated.

## Stage 0 Findings

### Target Repository Snapshot

Target repository:

`/home/peterc/devDir/dev-tools/EvalAndVizGears_for_ComputerVision`

Observed current implementation:

- Existing C++ visualization primitives are already present and should be reused:
  - `src/core/CFrameAnnotator.h`
  - `src/core/CFrameAnnotator.cpp`
  - `src/core/CFeatureOverlayRenderer.h`
  - `src/core/CFeatureOverlayRenderer.cpp`
  - `src/core/CTrackTrailRenderer.h`
  - `src/core/CTrackTrailRenderer.cpp`
  - `src/core/CDisplayWindow.h`
  - `src/core/CDisplayWindow.cpp`
  - `src/core/CBasePlotter.h`
- Current rendering stack uses OpenCV:
  - images are converted to BGR for display;
  - feature overlays are drawn in OpenCV;
  - feature trails have bounded tail length and fade logic;
  - display currently uses HighGUI through `imshow`.
- The repository has CMake and template-derived infrastructure but no committed ROS 2 workspace, no committed ROS 2 message package, no committed PlotJuggler layouts, and no committed devcontainer directory.
- A `.vscode` workspace setting references ROS 2 Jazzy, but this is not yet a buildable ROS 2 package layout.
- `configure_devcontainer.sh` contains logic for ROS 2 setup, but the required `.devcontainer/Dockerfile` and `.devcontainer/update_devcontainer_json.py` are not present in this repository.
- `cmake/HandleZeroMQ.cmake` is present only as an untracked file. It is not part of the stable `v1.11.1` donor tree and is now an explicit removal rather than a fallback transport candidate.
- The target still carries tracked spdlog integration inherited from its last committed template alignment: `cmake/HandleSpdlog.cmake`, `src/utils/logging/SpdlogUtils.*`, root/source CMake wiring, template examples, and four registered logging tests.
- The existing build directory currently enumerates 41 CTest tests, of which tests 1-4 exercise the legacy spdlog adapter. These four tests must be replaced by target-adapted `CLogger` tests; a lower raw test count is not acceptable evidence by itself.
- The target still advertises OptiX in root CMake and carries `cmake/HandleOptiX.cmake`. This conflicts with the established derived-project feature policy and must be removed during the standalone alignment pass.
- `build_lib.sh` in the target repo is behind the current template with respect to newer Python-test configuration options.

Observed dirty target files at the time of Stage 0:

- `CMakeLists.txt`
- `build_lib.sh`
- several files under `cmake/`
- `generate_version.sh`
- `python/setup.py.in`
- `src/CMakeLists.txt`
- untracked `cmake/HandleZeroMQ.cmake`, which is scheduled for removal

Implication:

- Do not blindly overwrite template-derived files.
- Template update must be staged as a diff and tested independently.
- Existing C++ OpenCV renderer code should become the image/feature/track rendering backend instead of being bypassed.

### nav-frontend Snapshot

Root repository:

`/home/peterc/devDir/nav-frontend`

Relevant MATLAB plotting and data-production areas:

- `matlab/utils/simulation_programs/RunFrontEnd.m`
  - main front-end execution wrapper;
  - produces KLT and centroiding outputs;
  - stores centroid diagnostics in persistent data;
  - routes KLT, centroiding, feature matching, and optional output save behavior.
- `matlab/utils/simulation_programs/RunFrontEnd_KLT.m`
  - KLT extraction and diagnostics path;
  - calls track plotting;
  - contains image snapshot plotting/export logic;
  - currently couples diagnostic rendering to flags such as `bEnableOutputPlot`, `bSaveKltDiagnostics`, and Monte Carlo mode.
- `matlab/utils/SaveFrontEndUnifiedOutput.m`
  - creates unified hidden output figures;
  - draws image, KLT keypoints, and centroid markers;
  - uses `exportgraphics`.
- `matlab/track_builder/CTrackBuilder.m`
  - relevant to feature track ownership and track-history access.
- `matlab/datastructs/SFeatureTrack.m`
  - relevant to track representation.
- Dirty or untracked feature producer and extraction directories exist and must be considered as current root-repo implementation, not ignored:
  - `matlab/algorithms/coffee_keypoint/`
  - `matlab/algorithms/rot_state_features_based/`
  - `matlab/algorithms/rot_state_shape_bootstrap/`
  - `matlab/feature_producers/`
  - related tests under `matlab/tests/`.

Implication:

- The first MATLAB ROS publisher hook should be after the front-end step has produced the temporary algorithm outputs, not inside low-level extractor code.
- The plan must preserve active dirty work in the root repo.
- Optional extraction-specific fields must be supported through optional ROS messages or status fields rather than by hard-coding only one front-end algorithm.

### nav-backend Snapshot

Root repository:

`/home/peterc/devDir/nav-backend`

Relevant MATLAB plotting and analysis areas:

- `matlab/utils/PlotKeypointsTrack.m`
  - current online image, keypoint, and track-history overlay path;
  - uses image display, scatter/plot style overlays, track-history color mapping, and `drawnow`;
  - likely a high-priority replacement target for the ROS image overlay path.
- `matlab/utils/TestHarness_RunCentroiding.m`
  - centroiding visualization path;
  - overlays estimated centroid, projected centroid, center of brightness, status text, and legend;
  - uses figure drawing, optional export, and `drawnow`.
- `matlab/utils/VisualizeEstimationStateWith3dScene.m`
  - target-fixed 3D visualization;
  - includes shape model, trajectories, map points, ROI-related display, persistent camera state, and `drawnow`.
- `matlab/utils/Plot3dEstimatedTrajectories.m`
  - reference, online, smoothed, GTSAM estimate, map point, and covariance ellipsoid display.
- `matlab/utils/PlotEstimationErrorsFromPerfMonitor.m`
  - online position/velocity/additional-state error plots;
  - covariance and empirical covariance plots;
  - focused time-window behavior and y-limit computation.
- `matlab/utils/PlotSimCoreRunFromPerfMonitor.m`
  - higher-level plotting wrapper for error/covariance/additional-state views.
- Current untracked or modified online visualization utilities exist and should be treated as current implementation inputs:
  - `matlab/utils/BuildLatLonRoiCircle.m`
  - `matlab/utils/ComputeOnlineTrajectoryValidityMask.m`
  - `matlab/utils/ComputeOnlineVizFocusMask.m`
  - `matlab/utils/ComputeOnlineVizYLimits.m`
  - `matlab/utils/ConvertTargetFixedPointsToLatLon.m`
  - `matlab/utils/PlotOnlineLatLonRoiCoverageMap.m`
  - `matlab/tests/testOnlineVisualizationUtilities.m`
- An untracked development document exists in the root backend repo:
  - `doc/development/matlab/online_visualization_development_plan.md`
  - It already describes completed MATLAB-side improvements for 3D scene readability, focused online estimation-error plots, online map/ROI view, and a still-open streaming visualization contract stage.

Implication:

- The ROS 2 plan should not duplicate the current backend MATLAB refactor work.
- C++/ROS rendering should consume the same semantic outputs where possible.
- Scalar time-series plot computation should be formalized from the current perf-monitor plotting code, then published to PlotJuggler-compatible ROS topics.
- 3D covariance geometry should move toward C++ marker generation, while covariance values and frame ownership remain in the estimator/performance monitor source.

### nav-system Snapshot

Root repository:

`/home/peterc/devDir/nav-system`

Relevant integration areas:

- `src/SetupOptions_COSMICAsys.m`
  - current defaults include image plotting disabled by default and plot flags separately configurable;
  - Monte Carlo mode disables plotting.
- `src/navigation_programs/navigation_update.m`
  - calls `RunFrontEnd`;
  - passes image plot and output save flags to the front-end;
  - is a clean candidate to publish front-end visualization packets after the front-end update;
  - is also a clean candidate to publish backend/performance-monitor packets after estimator updates.
- `src/LoadNavSystemConfigFromYaml.m`
  - configuration loader will need explicit ROS 2 visualization options added.

Observed issue:

- `nav-system` shows a dirty `space-nav-backend` entry. This may be a submodule or nested checkout state.

Implication:

- Implementation must use the root `/home/peterc/devDir/nav-backend` and `/home/peterc/devDir/nav-frontend` repositories as source-of-truth for code import/review.
- During nav-system wiring, the nested backend reference must be checked for path resolution and version compatibility.
- If nav-system runtime loads nested backend files instead of the root sibling checkout, that must be reported before editing because it can create an integration conflict.

### COSMICA Simulator Snapshot

Root repository:

`/home/peterc/devDir/projects-DART/cosmica-simulator`

Relevant simulation-core plotting areas:

- `scripts/RunCosmicaSystemSimulation.m`
  - public manual-run entry point;
  - resolves root repos from `/home/peterc/devDir`;
  - sets `charNavSystemRoot = /home/peterc/devDir/nav-system`;
  - sets `charGuiSystemRoot = /home/peterc/devDir/projects-DART/gui-system`;
  - sets SPICE data root through `/home/peterc/devDir/nav-backend/data/SPICE_kernels`;
  - loads `input/run_configs/cosmica_manual_approach.yml`;
  - supports MATLAB `profile on/off` through `runner_options.bProfileRun`;
  - passes `bPlotSimRunResults` and `bEnableFinalPlots` to the shared simulation-core runner.
- `scripts/main_cosmica_system_simulation_core.m`
  - main simulation loop;
  - uses resolved visualization options;
  - calls evaluation plotting at a fixed in-core refresh cadence;
  - includes guidance and backend 3D visualization paths;
  - uses `drawnow limitrate` and optional `exportgraphics`.
- `scripts/main_cosmica_system_simulation_core_harnessed.m`
  - harnessed variant of the simulation loop with similar visualization concerns.
- `scripts/utils/MakeEvaluationPlotsFcn.m`
  - evaluation plotting entry point;
  - reuses figure handles through `strPlotState`;
  - plots inertial truth/estimate trajectory in MATLAB;
  - calls backend error plotting and 3D scene visualization.
- `scripts/utils/MakeEvaluationPlots.m`
  - legacy caller-workspace script mirror of `MakeEvaluationPlotsFcn.m`;
  - should be kept in sync or retired after the function path is confirmed as the only active path.
- `scripts/utils/ResolveCosmicaRunnerVisualizationOptions.m`
  - centralizes runtime visualization flags;
  - defaults live visualization, backend 3D export, guidance debug export, and preplan summary display to false;
  - forces those boolean visualization flags off for Monte Carlo trials;
  - validates backend scene camera mode as `target_fixed`, `camera_fixed`, or `sun_to_body`;
  - current live visualization defaults can be extended with ROS 2 publish options.
- `input/LoadCosmicaRunConfigFromYaml.m`
  - strictly validates `cosmica_run.runner_options`;
  - currently allows only existing profiling, plotting, output-folder, backend scene, guidance debug, preplan summary, and final plot flags;
  - rejects legacy `bEnableOnlinePlots` as an unknown runner option;
  - any ROS 2 visualization flags must be added here with tests.
- `input/run_configs/cosmica_manual_approach.yml`
  - current manual debug run has `bEnableLiveVisualization: false`;
  - current manual debug run has `bSaveBackend3dVisualization: true`;
  - current manual debug run has `bSaveGuidanceDebugFigures: true`;
  - current manual debug run has `charBackendSceneCameraViewMode: camera_fixed`.
- `src/approach_trajectory_design/SaveApproachPreplannedTrajectoryFigures.m`
  - exports setup-time approach trajectory summary figures;
  - calls `PlotApproachPreplannedTrajectorySummary`;
  - uses `drawnow limitrate` and `exportgraphics`.
- `src/approach_trajectory_design/PlotApproachPreplannedTrajectorySummary.m`
  - plots 3D preplanned approach trajectory, shell wireframes, insertion markers, shaping manoeuvre marker, and target marker;
  - plots compact scalar histories for range, speed, phase angle, apparent diameter or radial speed;
  - down-samples plotted trajectory samples for responsiveness.
- `src/monte_carlo_set/GenerateCosmicaMonteCarloSetSamples.m`
  - exports approach preplanned trajectory figures for generated MC samples when a sample output root is provided.
- `scripts/RunCosmicaMonteCarloSet.m`
  - builds Monte Carlo trial setups;
  - marks each trial as `bIsMonteCarloTrial = true`, which triggers visualization-disable behavior in `ResolveCosmicaRunnerVisualizationOptions`.
- `gui-system` plotting used from COSMICA:
  - `/home/peterc/devDir/projects-DART/gui-system/gui-goal-definition/PlotGoalDefinitionMap.m`;
  - `/home/peterc/devDir/projects-DART/gui-system/gui-goal-definition/CheckGoalStatus.m`;
  - `/home/peterc/devDir/projects-DART/gui-system/src/plots/plotGuidanceSolution.m`;
  - `/home/peterc/devDir/projects-DART/gui-system/src/plots/PlotHandleGroup.m`.

Implication:

- COSMICA should not own the visualization implementation.
- COSMICA should own only simulation-level enable/disable, refresh cadence, and destination configuration.
- COSMICA should publish through nav-system/nav-backend/nav-frontend adapter calls where possible, not directly serialize every plot type by itself.
- COSMICA must still publish or expose simulation-level context that is not owned by nav-system:
  - run name and trial id;
  - simulation timestamp and timestamp id;
  - Monte Carlo trial status;
  - current action id and guidance counter;
  - output folder and recording metadata if recording is enabled;
  - approach-preplan summary data if the viewer should replace setup-time figures.
- Guidance plots are not nav-backend plots. They come from `gui-system` and need either:
  - a separate GUI/guidance ROS message family;
  - or a deliberate decision to keep them as MATLAB/export-only for the first implementation.
- The strict run YAML loader means new ROS 2 options must be added to the allowed `runner_options` list and to tests before they are used in `cosmica_manual_approach.yml`.
- The current manual run saves backend 3D and guidance debug figures even though live visualization is off. A ROS path must preserve the distinction between live display, export/recording, and publish-only operation.
- Monte Carlo runs intentionally disable live/export visualization today. ROS publishing should keep that default unless a new explicit MC diagnostics override is added.
- The fixed in-core plot cadence `dPlotDeltaNumOfKeyframes = 5` should become a run option before ROS publishing is benchmarked.

### cpp_cuda_template_project Snapshot

Root repository:

`/home/peterc/devDir/dev-tools/cpp_cuda_template_project`

Relevant template observations:

- The reviewed production donor is the signed stable tag `v1.11.1` at commit `ed11d83`, released on 2026-07-19.
- The donor checkout is clean on `main` at `a9604ca`, one documentation-plan commit after `v1.11.1`. That post-tag commit is excluded from this alignment baseline.
- The previous plan used `5cf1ac1` (`v1.10.3-1-g5cf1ac1`) as its snapshot. The complete donor delta from that snapshot to `v1.11.1` changes 92 paths with 9,730 insertions and 908 deletions, so it cannot be represented as only a ROS overlay update.
- The target's last explicit committed template synchronization is `db58f13`, whose commit message records `cpp_cuda_template_project` v1.5.0. Current uncommitted target changes forward-port parts of later template behavior, so Stage 2 must use a three-way semantic comparison rather than assume either a clean v1.5.0 or v1.10.3 target.
- The target and the `5cf1ac1..v1.11.1` donor delta overlap on 18 tracked paths. Seven of those are already dirty in the target: `CMakeLists.txt`, `build_lib.sh`, `cmake/HandleCUDA.cmake`, `cmake/HandleOptiX.cmake`, `generate_version.sh`, `src/CMakeLists.txt`, and `.vscode/c_cpp_properties.json`.
- The donor's `doc/developments/derived_project_upgrade_agent_guidelines.md` requires a three-way semantic port, a tailoring-preservation ledger, per-delta Adopt/Adapt/Skip/Upstream-first/Blocked classification, and executable guards for intentionally absent features.
- The donor tailoring script is a template-maintainer tool, not target content. A scratch copy of the tagged donor may be tailored with `--project-namespace viztools --remove-ros2` to create a comparison oracle, but `tailor_template_cleanup.sh`, donor development plans, donor reports, and template-only validation workflows must not be copied into this instantiated project.
- `build_lib.sh` and the older pre-ROS CMake improvements still include Python-test controls, source-version side-effect controls, compiler-flag centralization, target naming controls, and build/install regression coverage relevant to this target.
- `v1.11.1` adds a dependency-free `CLogger`, CPack source-release support, nested header-install fixes, CUDA/PTX source classification fixes, generic workflow templates, and stronger behavioral tests.
- `v1.11.1` also retains a conditional legacy spdlog adapter during migration. This target will adapt the new `CLogger` but remove `ENABLE_SPDLOG`, `ENABLE_FETCH_SPDLOG`, `HandleSpdlog.cmake`, `SpdlogUtils.*`, spdlog compile definitions, spdlog export metadata, legacy examples, and legacy tests.
- The stable donor does not contain `cmake/HandleZeroMQ.cmake`; the target's untracked module is a local/earlier experiment and will be removed.
- The donor still supports OptiX. This target intentionally does not; OptiX files, flags, PTX embedding paths that are only required by OptiX, tests, documentation, workflow inputs, and later ROS facade options must remain absent.
- `v1.11.1` contains a complete optional ROS 2 overlay, rollout helpers, metadata synchronization, workflows, and tests. Those changes are classified as Later for the current pass. They will be reconsidered only after the standalone alignment exit gate is green.
- Broad directory comparisons also show generated or local artifacts such as `build`, `install`, cache, workspace databases, and backup files. Template alignment must ignore those and compare only source-controlled target surfaces.

#### v1.11.1 Donor Delta Classification

| Donor capability or path group | Stage 2 classification | Target treatment |
|---|---|---|
| Dependency-free `src/utils/logging/CLogger.*` and logger tests/docs | Adapt | Rename namespace to `viztools::logging`, use `EVAL_AND_VIZ_LOG_LEVEL`, preserve deterministic streams and concurrency behavior, and remove all legacy spdlog compatibility. |
| Legacy spdlog options, handler, adapter, examples, tests, and exports | Skip/remove | Delete from the target and add source-tree plus installed-package absence guards. Do not copy the donor's transitional compatibility layer. |
| `generate_version.sh` semantic-version handling | Adopt now | Preserve no-argument standalone behavior and prerelease/build metadata. Add the `--sync-ros2` interface only in a way that no-ops cleanly while no ROS overlay exists. |
| `ros2/tools/sync_package_metadata.py` and ROS package release metadata | Later | Do not import in Stage 2. Import/adapt with the ROS overlay stage and test against target package metadata then. |
| Root CMake metadata and CPack source-release contract | Adapt | Preserve target identity and dependencies; adopt source-release hygiene and no-Git VERSION fallback without adding ROS requirements. |
| Nested install-header and build/install consumer fixes | Adapt | Apply to the target's real `src/core`, `src/utils`, and wrapper layout; verify target headers rather than template placeholders. |
| CUDA/PTX source classification and compile graph fixes | Adapt | Keep reusable CUDA behavior, remove OptiX-only branches, and test at least configure/source classification when CUDA hardware or toolkit is unavailable. |
| OptiX handler, options, workflows, tests, and docs | Skip/remove | Remove all target support and add absence guards. Do not retain disabled facade options. |
| ZeroMQ support | Skip/remove | Remove untracked `cmake/HandleZeroMQ.cmake`; do not add options, packages, or fallback transport documentation. |
| Python-test, wrapper, compiler-flag, and target-option improvements predating the ROS overlay | Adapt | Port only behavior compatible with the target package/API; retain target wrapper names and OpenCV build contracts, and keep Pangolin absent. |
| Generic workflow templates (`*.yml.tpl`) and self-hosted CUDA guard | Adapt/optional | Materialize only workflows the target owns, preserve target runner policy, and never copy active donor template-validation workflows as project CI. |
| Pull-request template and generic documentation workflow improvements | Adopt/optional | Apply only after target policy review; exclude donor identity and internal campaign material. |
| `tailor_template_cleanup.sh`, template development plans/reports, template static tests | Source-only | Use as review evidence or scratch tooling only; do not import into the target. |
| ROS 2 overlay packages, `add_ros2_support.sh`, `build_ros2.sh`, COLCON markers, ROS workflows | Later | Keep in persistent Stages 3 and later. Adapt later to no OptiX/no spdlog and to a ROS-valid lowercase package prefix. |
| Donor `.vscode` files, deleted workspace file, `AGENTS.md`, `CLAUDE.md`, and `CONTEXT.md` history | Skip/manual | Preserve target-local IDE/instruction ownership; do not treat donor housekeeping as product functionality. |

Implication:

- The template update must be an explicit stage with a pinned source commit, per-file diff review, and tests.
- Do not update template files in the same stage as ROS 2 visualization implementation.
- Run the donor tailoring script only in a temporary scratch copy. It is a comparison and test oracle, not an overwrite mechanism.
- Import template functionality in dependency order. Do not copy the template root wholesale because this target has project-specific OpenCV, source, tests, wrappers, and install/export differences.
- Treat the target's absence of OptiX and ZeroMQ, and removal of spdlog, as post-update invariants with executable checks.
- If template changes conflict with target local modifications, stop and report the conflicting file list before applying.

### hyper_2 Reference Snapshot

Root repository:

`/home/peterc/devDir/projects-DFKI/hyper_2`

Relevant reference components:

- `ros2_ws/src/hyper_2_interfaces`
  - custom ROS 2 message package pattern;
  - uses `rosidl_generate_interfaces`.
- `ros2_ws/src/hyper_2_visualization`
  - C++ ROS 2 visualization package;
  - uses RViz visual tools, marker topics, TF, pose/twist display;
  - has Python plotting nodes for some scalar/time-series views.
- `ros2_ws/src/hyper_2_bringup`
  - launch and configuration conventions.
- Docker and devcontainer:
  - uses ROS 2 Jazzy;
  - installs PlotJuggler, PlotJuggler ROS plugin, Foxglove bridge, RViz visual tooling, and rqt packages;
  - uses host networking and X11 forwarding for visualization.

Implication:

- Use hyper_2 as the pattern for ROS 2 package layout, custom messages, launch/config separation, Docker/devcontainer setup, and QoS choices.
- Do not copy domain-specific robot/gait message semantics from hyper_2.
- Use PlotJuggler for scalar and covariance dashboards, not image overlays or rich 3D scene ownership.

## Design Conflict Audit

### No Fatal Conflict Found

The planned ROS 2 architecture is compatible with the current repositories if staged carefully:

- MATLAB can remain the algorithm owner.
- The target repo can own C++ visualization nodes and message definitions.
- nav-system can own runtime configuration and publisher lifecycle.
- nav-frontend and nav-backend can expose packet construction adapters without changing algorithm outputs.
- PlotJuggler can handle scalar dashboards.
- RViz/Foxglove can handle 3D scene and covariance markers.
- OpenCV/C++ can handle image, centroid, feature, and track overlay rendering.

### Mandatory Gates Before Implementation

- [ ] Verify that all implementation work references root repositories under `/home/peterc/devDir`, not stale nested mirrors.
- [ ] Snapshot dirty state in every participating repo before copying or refactoring code.
- [ ] Resolve whether nav-system runtime paths load root sibling repos or nested submodule paths.
- [ ] Use the stable template overlay layout under repository-local `ros2/`, with the standalone root CMake project included only through the colcon shim package.
- [ ] Update cpp_cuda_template_project-derived files in a dedicated stage before ROS package work.
- [ ] Create a devcontainer only after comparing the target missing `.devcontainer` state with the newest template and hyper_2.
- [ ] Generate MATLAB ROS 2 custom message bindings before relying on custom messages in MATLAB.
- [ ] Keep existing MATLAB plotting available until ROS 2 output is tested against it.

### Main Design Risks

- Dirty source repos can contain uncommitted APIs that differ from committed code.
- Large image messages from MATLAB can slow the simulation if published too frequently.
- MATLAB custom ROS 2 message generation can be fragile if package paths or environment setup are inconsistent.
- PlotJuggler is unsuitable for image overlays and complex 3D scenes.
- RViz marker generation can become cluttered if MATLAB publishes fully rendered geometry instead of compact semantic data.
- C++ rendering must preserve MATLAB image channel order and numeric type semantics.
- Existing target C++ renderer uses BGR/OpenCV conventions, while MATLAB image data may be grayscale, RGB, logical, integer, single, or double.
- Track-history publication can become expensive if full history is sent every refresh.
- Scalar error/covariance plots may currently compute display-specific limits and focused windows inside plotting functions; this computation must be separated from plotting.

## Recommended Architecture

### Data Flow

```text
MATLAB simulation / nav-system
  -> nav-frontend packet adapters
  -> nav-backend/perf-monitor packet adapters
  -> MATLAB ROS 2 publishers
  -> ROS 2 topics with best-effort / keep-last QoS where appropriate
  -> C++ visualization nodes in EvalAndVizGears_for_ComputerVision
       -> OpenCV image overlay viewer
       -> RViz marker publishers
       -> PlotJuggler scalar topic stream
       -> optional Foxglove bridge
```

### Ownership Boundaries

MATLAB remains responsible for:

- running simulation and algorithm steps;
- producing front-end outputs;
- producing back-end estimated states and covariance;
- producing performance-monitor errors and reference comparisons;
- selecting mission phase, active front-end stage, and refresh cadence;
- publishing compact semantic visualization messages;
- preserving existing plotting fallback;
- controlling whether publishing is enabled.

C++/ROS 2 target repo becomes responsible for:

- message definitions;
- ROS 2 subscriber and visualization nodes;
- image overlay rendering;
- track color mapping from length and status;
- conversion of compact semantic messages into OpenCV/RViz/PlotJuggler outputs;
- 3D marker generation for trajectories, points, axes, ROI geometry, covariance ellipsoids, and status annotations;
- bounded latest-frame behavior;
- launch files and layouts;
- Docker/devcontainer visualization environment.

PlotJuggler becomes responsible for:

- time-series dashboards for scalar/vector topics;
- errors and covariance streams;
- residuals;
- additional-state errors;
- optional latency and publish timing streams.

RViz/Foxglove-compatible tooling becomes responsible for:

- 3D spatial quantities;
- trajectories;
- landmarks/map points;
- target-fixed frames;
- ROI geometry;
- covariance ellipsoids;
- estimated vs reference transforms;
- optional shape-model markers if performance allows.

OpenCV viewer becomes responsible for:

- image display;
- centroid overlays;
- extracted features;
- feature tracks and tails;
- feature-track color by length;
- layer toggles for image overlays.

### Why ROS 2

ROS 2 is the recommended primary interface because:

- the user explicitly wants ROS 2 interfaces and MATLAB ROS 2 integration;
- MATLAB has ROS 2 publisher/subscriber support with generated custom messages;
- ROS 2 supports local and remote visualization through standard discovery and bridge tools;
- PlotJuggler, RViz, Foxglove, and rqt can consume ROS 2 topics;
- QoS policies support best-effort, keep-last, and frame dropping behavior;
- hyper_2 already provides a local reference for ROS 2 package layout, Docker, devcontainer, PlotJuggler, RViz visual tools, and launch organization.

### Why Not PlotJuggler As The Only Viewer

PlotJuggler is appropriate for:

- scalar time series;
- vector components split into scalar curves;
- covariance diagonal and selected off-diagonal terms;
- error norms;
- timing and latency;
- status counters.

PlotJuggler is not the primary tool for:

- image display at native resolution;
- feature overlay rendering;
- feature-track trails;
- arbitrary image-layer toggles;
- rich 3D scene display;
- covariance ellipsoid geometry.

Therefore PlotJuggler should be configured as one consumer of the ROS 2 stream, not the central renderer.

### Why Not MATLAB As The Renderer

A second MATLAB process could reduce blocking in the simulation process, but it keeps:

- MATLAB graphics overhead;
- MATLAB licensing/session dependency;
- awkward remote rendering;
- higher startup/setup burden for non-MATLAB users;
- limited interoperability with ROS visualization tools.

It may remain a fallback, but not the primary path.

### Why Not Raw TCP / WebSocket As Primary

Raw TCP or WebSocket can be lightweight and direct, but they would require custom schemas, custom discovery, custom tooling adapters, and custom viewer lifecycle handling. ROS 2 already solves most of this and directly connects to the requested ecosystem.

Raw TCP/WebSocket can remain a later fallback for deployments where MATLAB ROS 2 support is unavailable.

### Why ZeroMQ Is Removed

ZeroMQ is no longer a fallback in this plan. The only target artifact is an untracked `cmake/HandleZeroMQ.cmake`, and the stable `v1.11.1` donor does not include it. Retaining a second transport would add dependency discovery, schema ownership, lifecycle, testing, and remote-configuration work without improving the selected ROS 2/PlotJuggler/RViz/MATLAB integration. If a future deployment proves ROS 2 unusable, transport alternatives must be evaluated as a new design decision rather than keeping dormant ZeroMQ support.

## Plot Category Mapping

| Current MATLAB plot category | Current owning repo | Future transport | Future renderer |
| --- | --- | --- | --- |
| Raw algorithm image | nav-frontend / nav-system | `sensor_msgs/Image` or custom frame packet | OpenCV viewer |
| Centroid output | nav-backend / nav-frontend | custom `CentroidArray` | OpenCV viewer, optional RViz markers |
| Extracted features | nav-frontend | custom `FeatureArray` | OpenCV viewer |
| Feature tracks | nav-backend / nav-frontend | custom `FeatureTrackArray` | OpenCV viewer |
| Track length color map | MATLAB plotting today | C++ renderer computes from length | OpenCV viewer |
| Keyframe and lost-feature status | nav-frontend | custom status fields | OpenCV viewer, PlotJuggler counters |
| 3D estimated trajectory | nav-backend | `nav_msgs/Path` or custom trajectory | RViz/Foxglove |
| Reference trajectory | nav-backend/perf monitor | `nav_msgs/Path` or custom trajectory | RViz/Foxglove |
| Smoothed trajectory | nav-backend | `nav_msgs/Path` | RViz/Foxglove |
| GTSAM best estimate trajectory | nav-backend | `nav_msgs/Path` | RViz/Foxglove |
| Landmarks / map points | nav-backend | `visualization_msgs/MarkerArray` or custom points | RViz/Foxglove |
| Shape model | nav-backend | marker mesh/point cloud topic | RViz/Foxglove |
| ROI / lat-lon coverage | nav-backend | custom ROI topic plus marker geometry | RViz/Foxglove, PlotJuggler summary |
| Position error | nav-backend/perf monitor | scalar/vector time-series topics | PlotJuggler |
| Velocity error | nav-backend/perf monitor | scalar/vector time-series topics | PlotJuggler |
| Additional state errors | nav-backend/perf monitor | scalar/vector time-series topics | PlotJuggler |
| Covariance diagonal | nav-backend/perf monitor | scalar/vector time-series topics | PlotJuggler |
| Empirical covariance | nav-backend/perf monitor | scalar/vector time-series topics | PlotJuggler |
| Covariance ellipsoids | nav-backend values, C++ geometry | custom covariance topic | RViz/Foxglove |
| Plot timing / publish timing | nav-system / target viewer | scalar diagnostic topics | PlotJuggler |
| COSMICA run context | cosmica-simulator | custom run-context topic | all viewers / diagnostics |
| Guidance goal-definition map | gui-system through COSMICA | custom ROI/goal topic plus markers | RViz/Foxglove, optional PlotJuggler summary |
| Guidance status/visited goals | gui-system through COSMICA | custom guidance-status topic | RViz/Foxglove, PlotJuggler counters |
| Guidance planned trajectory and Delta-V | gui-system/COSMICA | custom guidance solution plus `nav_msgs/Path` | RViz/Foxglove, PlotJuggler scalar summaries |
| Approach preplanned trajectory | cosmica-simulator | custom approach-preplan topic plus path | RViz/Foxglove |
| Approach preplan range/speed/phase/apparent size | cosmica-simulator | scalar/vector time-series topics | PlotJuggler |

## MATLAB Versus C++ Compute Split

### Keep In MATLAB

- [ ] Algorithm outputs: centroids, features, descriptors, track associations, estimated states, covariance, residuals.
- [ ] Mission phase and active front-end stage.
- [ ] Reference truth and performance monitor values.
- [ ] Existing data structure interpretation.
- [ ] Refresh cadence decisions.
- [ ] Online visualization enable/disable state.
- [ ] Optional save-to-disk behavior until replaced by a separate recording tool.

### Move To C++ / ROS Visualization Nodes

- [ ] Image overlay drawing.
- [ ] Feature marker drawing.
- [ ] Track-tail truncation for display.
- [ ] Track color mapping based on length.
- [ ] Layer toggles.
- [ ] OpenCV window management.
- [ ] RViz marker creation for 3D trajectories, landmarks, axes, ROI geometry, covariance ellipsoids.
- [ ] PlotJuggler topic shaping where the MATLAB publisher would otherwise emit plot-specific structures.
- [ ] Viewer-side timing measurement.
- [ ] Frame dropping / latest-frame-wins behavior.

### Split And Formalize

- [ ] Current MATLAB y-limit and focus-window helpers should be separated into reusable analysis functions. The raw values should be published so PlotJuggler can own display range.
- [ ] Covariance ellipsoid generation should move to C++ marker generation, but MATLAB must publish covariance matrix, frame id, position, and confidence scale.
- [ ] Lat/lon ROI conversion may stay MATLAB initially because current utilities are in nav-backend; later C++ can take over if frame and shape-model contracts are formalized.
- [ ] Track-history compaction should be configurable. MATLAB should publish current point plus either bounded tail or incremental updates. C++ should not require full lifetime history for every refresh.

## ROS 2 Package Layout Proposal

I would avoid redesign the library around ros 2 only. plotjuggler can work also outside and so should the library do. ros 2 is just to be intended as the default communication protocol

Selected target layout, rebased onto applicable facilities from the stable `v1.11.3` optional overlay:

```text
EvalAndVizGears_for_ComputerVision/
  doc/
    developments/
      ros2_online_visualization_plan.md
  ros2/
    eval_and_viz_gears/
      CMakeLists.txt
      package.xml
    eval_and_viz_gears_interfaces/
      CMakeLists.txt
      package.xml
      msg/
      srv/
    eval_and_viz_gears_ros/
      CMakeLists.txt
      package.xml
      include/eval_and_viz_gears_ros/
      src/
      test/
    eval_and_viz_gears_spinup/
      CMakeLists.txt
      package.xml
      config/
      launch/
      plotjuggler/
      rviz/
    tools/
      sync_package_metadata.py
  tools/
    matlab_ros2/
      README.md
      matlab/
```

Decision:

- [ ] Keep `EvalAndVizGears_for_ComputerVision` as the standalone CMake project and installed CMake package identity.
- [ ] Use explicit ROS-valid package prefix `eval_and_viz_gears`.
- [ ] Use `ros2/eval_and_viz_gears` only as the plain-CMake colcon shim that includes the root project.
- [ ] Use `ros2/eval_and_viz_gears_interfaces` only for remaining
  Eval-and-Viz-owned domain messages and services. Feature-track messages are
  owned by `slam-primitives`; trajectory transport uses `nav_msgs/Path`.
- [ ] Use `ros2/eval_and_viz_gears_ros` for ROS adapters, image-overlay viewer nodes, 3D marker nodes, and conversion code.
- [ ] Use `ros2/eval_and_viz_gears_spinup` for launch, runtime configuration, PlotJuggler XML, and RViz configuration.
- [ ] Keep MATLAB binding generation/scripts outside the colcon package tree under `tools/matlab_ros2` unless MATLAB tooling proves it requires another generated-source location.
- [ ] Build the repository-local package tree by running `colcon` with repository root as the workspace base; do not require a committed outer `ros2_ws/src` wrapper.

Rationale:

- This matches the now-stable template overlay and retains the standalone library as the primary architecture.
- It avoids inventing a second workspace layout while still keeping ROS packages isolated below `ros2/`.
- It preserves hyper_2's useful interface/visualization/bringup separation through equivalent interfaces/ROS/spinup ownership.
- It gives `add_ros2_support.sh --ros-prefix eval_and_viz_gears` a supported, explicit rollout target despite the mixed-case CMake project name.

## ROS 2 Message Plan

Package:

`eval_and_viz_gears_interfaces`

Benchmark decision override (approved and validated 2026-07-22):

- The `TrackPoint`, `FeatureTrack`, and `FeatureTrackArray` proposals below are
  historical and superseded by
  `slam_primitives_interfaces/{FeatureObservation2D,FeatureTrack2D,FeatureTrackArray}`.
  Their ROS-neutral source contract is `slam_primitives::SFeatureTrackSnapshot`.
- The `TrajectorySample` and `Trajectory` proposals below are historical and
  superseded for camera-path visualization by three `nav_msgs/Path` topics:
  reference, online, and smoothed. Each sample is a real `PoseStamped` with a
  normalized orientation; no custom trajectory message is required for this
  benchmark slice.
- The remaining message proposals are not implemented by this benchmark and
  stay available for later roadmap decisions.

### Message Principles

- [ ] Use standard ROS messages where they fit.
- [ ] Use custom messages only where standard messages cannot express the semantic data cleanly.
- [ ] Keep MATLAB publishing simple.
- [ ] Keep image data separated from overlays so image publish rate can be throttled independently.
- [ ] Include schema/version fields in custom messages.
- [ ] Include frame index and simulation time in all visualization packets.
- [ ] Include source and mission phase strings or enums.
- [ ] Include optional fields through arrays and status flags rather than deeply nested structures.
- [ ] Avoid descriptors in the online display path unless explicitly needed.
- [ ] Avoid full track history unless configured.

### Standard Messages

- [ ] `std_msgs/Header`
  - time stamp;
  - frame id;
  - sequence association through custom fields if needed.
- [ ] `sensor_msgs/Image`
  - raw image display;
  - encoding must explicitly represent grayscale, RGB, or BGR.
- [ ] `sensor_msgs/CompressedImage`
  - optional compressed image path for remote visualization.
- [ ] `geometry_msgs/Point`
  - image-plane or 3D point fields where appropriate.
- [ ] `geometry_msgs/PointStamped`
  - selected centroid or debug points if useful.
- [ ] `geometry_msgs/PoseStamped`
  - estimated pose quantities.
- [ ] `geometry_msgs/Vector3Stamped`
  - velocity, acceleration, and error vectors where useful.
- [ ] `nav_msgs/Path`
  - trajectories.
- [ ] `visualization_msgs/Marker`
  - RViz marker primitives.
- [ ] `visualization_msgs/MarkerArray`
  - covariance ellipsoids, landmarks, ROI, shape model markers.
- [ ] `diagnostic_msgs/DiagnosticArray`
  - publisher/viewer health if useful.

### Custom Messages

Implement these only if really necessary because compounding existing ros 2 messages is not viable

#### `VizFrameHeader.msg`

Purpose:

Common metadata attached to all custom visualization messages.

Fields:

```text
std_msgs/Header header
uint32 schema_version
uint64 frame_index
float64 sim_time_sec
string mission_phase
string frontend_stage
string source
string algorithm
```

Tests:

- [ ] MATLAB can construct and publish the message.
- [ ] C++ node can receive and log the metadata.
- [ ] Message generation works in Docker/devcontainer.

#### `ImageMetadata.msg`

Purpose:

Preserve MATLAB image semantics when `sensor_msgs/Image` alone is ambiguous.

Fields:

```text
uint32 width
uint32 height
uint32 channels
string matlab_class
string color_order
string ros_encoding
bool normalized_float
float64 min_value
float64 max_value
```

Tests:

- [ ] Grayscale `uint8` images round-trip without color conversion.
- [ ] RGB `uint8` images display correctly in OpenCV after explicit conversion.
- [ ] `double` images preserve scale metadata and display with intentional normalization.

#### `ImageFrame.msg`

Purpose:

Optional combined image metadata packet if `sensor_msgs/Image` is insufficient for MATLAB publishing.

Fields:

```text
VizFrameHeader viz_header
ImageMetadata metadata
sensor_msgs/Image image
```

Tests:

- [ ] C++ viewer displays image at original resolution.
- [ ] Viewer reports mismatch if metadata dimensions differ from image dimensions.

#### `Centroid.msg`

Purpose:

One centroiding output point.

Fields:

```text
uint64 id
float32 x
float32 y
float32 uncertainty_x
float32 uncertainty_y
float32 intensity
float32 score
int32 status
string label
```

Tests:

- [ ] Empty centroid arrays are accepted.
- [ ] Missing uncertainty is represented by NaN or zero plus status convention.
- [ ] C++ viewer toggles centroid layer.

#### `CentroidArray.msg`

Purpose:

All centroid outputs for a frame.

Fields:

```text
VizFrameHeader viz_header
Centroid[] centroids
```

Tests:

- [ ] MATLAB publishes zero, one, and many centroids.
- [ ] C++ viewer overlays centroids without resizing the image.

#### `FeaturePoint.msg`

Note that KLT is just the algorithm running now. Source may change in the future.

Purpose:

One extracted feature in image coordinates.

Fields:

```text
uint64 id
float32 x
float32 y
float32 score
float32 scale
float32 orientation
int32 status
string source
```

Tests:

- [ ] KLT keypoints publish with ID and image coordinates.
- [ ] Coffee/keypoint extractor outputs can be mapped without algorithm changes.
- [ ] Optional fields can be NaN when unavailable.

#### `FeatureArray.msg`

Purpose:

All extracted features for a frame.

Fields:

```text
VizFrameHeader viz_header
FeaturePoint[] features
```

Tests:

- [ ] C++ viewer handles arbitrary feature count.
- [ ] Feature layer can be disabled without affecting track rendering.

#### `TrackPoint.msg`

Purpose:

One historical point in a feature track.

Fields:

```text
float32 x
float32 y
uint64 frame_index
float64 sim_time_sec
```

Tests:

- [ ] Viewer renders tails in frame order.
- [ ] Missing time values do not break rendering.

#### `FeatureTrack.msg`

Purpose:

One feature track.

Fields:

```text
uint64 id
TrackPoint current
TrackPoint[] tail
uint32 length
uint32 age
int32 status
float32 quality
string source
```

Tests:

- [ ] Tail length can be bounded from MATLAB.
- [ ] Viewer color depends on `length`.
- [ ] Viewer handles tracks with only current point and no tail.

#### `FeatureTrackArray.msg`

Purpose:

All tracks for a frame.

Fields:

```text
VizFrameHeader viz_header
FeatureTrack[] tracks
uint32 max_tail_length
```

Tests:

- [ ] Arbitrary number of tracks renders.
- [ ] Empty track array is accepted.
- [ ] Track color mapping remains stable across refreshes.

#### `FrontendFrame.msg`

Purpose:

Optional aggregate front-end packet for synchronized overlay updates.

Fields:

```text
VizFrameHeader viz_header
ImageMetadata image_metadata
Centroid[] centroids
FeaturePoint[] features
FeatureTrack[] tracks
bool has_image
bool has_centroids
bool has_features
bool has_tracks
```

Decision:

- [ ] Prefer separate topics for image, centroids, features, and tracks in first implementation.
- [ ] Add aggregate packet only if synchronization complexity becomes significant.

#### `StateEstimate.msg`

Purpose:

Estimated navigation state for 3D visualization.

Fields:

```text
VizFrameHeader viz_header
string estimate_frame
geometry_msgs/Pose pose
geometry_msgs/Vector3 velocity
geometry_msgs/Vector3 acceleration
float64[] covariance
uint32 covariance_rows
uint32 covariance_cols
string status
```

Tests:

- [ ] MATLAB publishes current estimate.
- [ ] C++ node validates covariance dimensions.
- [ ] RViz pose marker appears in the correct frame.

#### `TrajectorySample.msg`

Purpose:

Seems unnecessarily redundant.

One trajectory sample with optional covariance.

Fields:

```text
float64 sim_time_sec
geometry_msgs/Pose pose
geometry_msgs/Vector3 velocity
float64[] covariance
uint32 covariance_rows
uint32 covariance_cols
int32 status
```

Tests:

- [ ] Trajectory arrays can include or omit covariance.
- [ ] C++ marker node rejects malformed covariance without crashing.

#### `Trajectory.msg`

Purpose:

Named trajectory stream for estimated, reference, smoothed, or GTSAM output.

Fields:

```text
VizFrameHeader viz_header
string trajectory_name
string coordinate_frame
TrajectorySample[] samples
uint32 max_samples
```

Tests:

- [ ] Estimated and reference trajectories can be published as separate topics.
- [ ] Viewer can render only latest bounded history.

#### `Landmark.msg`

Purpose:
Seems unnecessarily redundant.

One 3D map point or landmark.

Fields:

```text
uint64 id
geometry_msgs/Point position
float32 quality
int32 status
string source
```

Tests:

- [ ] Viewer renders landmarks as RViz points or spheres.
- [ ] Status controls color or visibility.

#### `LandmarkArray.msg`

Purpose:

All current landmarks/map points.

Fields:

```text
VizFrameHeader viz_header
string coordinate_frame
Landmark[] landmarks
```

Tests:

- [ ] Empty map is accepted.
- [ ] Large map can be throttled or downsampled.

#### `CovarianceEllipsoid.msg`

Purpose:

Compact covariance visualization request.

Fields:

```text
uint64 id
geometry_msgs/Pose center
float64[] covariance_3x3
float32 confidence_scale
int32 status
string label
```

Tests:

- [ ] C++ node computes ellipsoid axes from covariance.
- [ ] Negative or non-finite covariance values are rejected safely.

#### `CovarianceEllipsoidArray.msg`

Purpose:

All ellipsoids for the current 3D scene.

Fields:

```text
VizFrameHeader viz_header
string coordinate_frame
CovarianceEllipsoid[] ellipsoids
```

Tests:

- [ ] RViz marker array updates without accumulating stale markers.
- [ ] Confidence scale changes marker size predictably.

#### `RoiRegion.msg`

Purpose:

Target ROI or lat/lon coverage region.

Fields:

```text
uint64 id
string roi_type
geometry_msgs/Point[] boundary_points
float32 score
int32 status
string label
```

Tests:

- [ ] ROI boundary renders as line strip marker.
- [ ] Lat/lon-derived target-fixed points render in expected frame.

#### `RoiRegionArray.msg`

Purpose:

All ROI/coverage regions.

Fields:

```text
VizFrameHeader viz_header
string coordinate_frame
RoiRegion[] regions
```

Tests:

- [ ] Empty ROI list is accepted.
- [ ] Multiple ROI types can coexist.

#### `CosmicaRunContext.msg`

Too tied to cosmica. should be both more general and not strictly related to that but useful for generai simulations

Purpose:

COSMICA-owned run and loop context that is not an algorithm output but is needed to align online viewers, recordings, and dashboards.

Fields:

```text
VizFrameHeader viz_header
string trial_name
int32 trial_id
bool is_monte_carlo_trial
uint32 timestamp_id
uint32 action_id
uint32 guidance_counter
string output_root
string run_config_file
string nav_system_config_file
string nav_backend_config_file
string gui_system_config_file
```

Tests:

- [ ] MATLAB publishes run context without requiring nav-system output.
- [ ] Monte Carlo context marks `is_monte_carlo_trial` true.
- [ ] Viewer/recorder can use the context without depending on COSMICA classes.

#### `GuidanceStatus.msg`

Purpose:

Compact status for guidance goals and visited/remaining ROI counts, sourced from GUI-system/COSMICA data without forcing MATLAB figure generation.

Fields:

```text
VizFrameHeader viz_header
uint32 num_goals_total
uint32 num_goals_remaining
uint32 num_goals_visited
uint32 guidance_counter
uint32 action_id
bool has_active_solution
float64 total_nominal_delta_v_km_s
float64 last_manoeuvre_time_sec
```

Tests:

- [ ] Empty goal sets publish valid zero counts.
- [ ] Guidance counters update only when COSMICA has guidance data.
- [ ] PlotJuggler can display goal counts and total Delta-V.

#### `GuidanceSolution.msg`

Purpose:

Online guidance solution summary replacing `plotGuidanceSolution` for remote viewing.

Fields:

```text
VizFrameHeader viz_header
uint32 guidance_counter
float64[] guidance_time_sec
geometry_msgs/Point[] planned_position
geometry_msgs/Vector3[] planned_velocity
geometry_msgs/Vector3[] delta_v_km_s
float64[] manoeuvre_time_sec
string coordinate_frame
```

Tests:

- [ ] Empty or absent guidance solution does not publish misleading geometry.
- [ ] C++ marker node renders planned trajectory and manoeuvre markers.
- [ ] PlotJuggler receives Delta-V norms and guidance timing summaries.

#### `ApproachPreplanSummary.msg`

Purpose:

Setup-time approach-preplan visualization data currently rendered by `PlotApproachPreplannedTrajectorySummary`.

Fields:

```text
VizFrameHeader viz_header
string candidate_mode
string coordinate_frame
float64 insertion_time_sec
geometry_msgs/Point[] trajectory_position
geometry_msgs/Vector3[] trajectory_velocity
geometry_msgs/Point initial_position
geometry_msgs/Point insertion_position
geometry_msgs/Point shaping_manoeuvre_position
bool has_shaping_manoeuvre
float64[] trajectory_time_sec
float64[] range_km
float64[] speed_m_s
float64[] phase_angle_deg
float64[] apparent_diameter_px
float64[] radial_speed_m_s
```

Tests:

- [ ] Setup-time publisher can emit summary without opening MATLAB figures.
- [ ] RViz marker path renders trajectory, shell limits, and manoeuvre markers.
- [ ] PlotJuggler layout displays range, speed, phase angle, and apparent size.

#### `ScalarSeriesPoint.msg`

Purpose:

Generic scalar time-series value for PlotJuggler.

Fields:

```text
VizFrameHeader viz_header
string name
float64 value
string unit
int32 status
```

Decision:

- [ ] Prefer named scalar topics with standard numeric messages when PlotJuggler layout simplicity is more important than one generic message.
- [ ] Use this generic message only if topic count becomes unmanageable.

## ROS 2 Topic Plan

Do not make topics just for visualization nav_viz --> nav_system. This will become later on interfaces for the algorithms themselves and to interact with other algorithms (e.g. hyper2 for state estimation). Make sure to distinguish what comes from algorithms and what gets published by the simulation for this reason.

### COSMICA Run And Guidance Topics

- [ ] `/nav_viz/cosmica/run_context`
  - Type: `eval_and_viz_gears_interfaces/CosmicaRunContext`
  - QoS: reliable or transient local if late-joining viewers need the current run metadata
  - Publisher: MATLAB COSMICA/nav-system visualization coordinator
  - Consumer: C++ viewers, PlotJuggler diagnostics, recorder
  - Test: run context is available before first frame publish.

- [ ] `/nav_viz/cosmica/guidance/status`
  - Type: `eval_and_viz_gears_interfaces/GuidanceStatus`
  - QoS: best effort, keep last 1
  - Publisher: MATLAB COSMICA guidance adapter
  - Consumer: PlotJuggler, RViz marker node
  - Test: goal counters and Delta-V summary update without MATLAB figures.

- [ ] `/nav_viz/cosmica/guidance/solution`
  - Type: `eval_and_viz_gears_interfaces/GuidanceSolution`
  - QoS: best effort, keep last 1
  - Publisher: MATLAB COSMICA guidance adapter
  - Consumer: RViz/Foxglove marker node, PlotJuggler scalar adapter
  - Test: new guidance solution renders planned trajectory and manoeuvre markers.

- [ ] `/nav_viz/cosmica/approach_preplan`
  - Type: `eval_and_viz_gears_interfaces/ApproachPreplanSummary`
  - QoS: reliable or transient local because this is setup-time data
  - Publisher: MATLAB COSMICA setup adapter
  - Consumer: RViz/Foxglove marker node, PlotJuggler scalar adapter
  - Test: setup-time approach trajectory and scalar histories render without calling MATLAB plotting.

### Front-End Topics

- [ ] `/nav_viz/frontend/image`
  - Type: `sensor_msgs/Image` or `eval_and_viz_gears_interfaces/ImageFrame`
  - QoS: best effort, keep last 1
  - Publisher: MATLAB nav-system/front-end adapter
  - Consumer: C++ OpenCV viewer
  - Test: viewer displays image at native resolution.

- [ ] `/nav_viz/frontend/image_metadata`
  - Type: `eval_and_viz_gears_interfaces/ImageMetadata`
  - QoS: best effort, keep last 1
  - Publisher: MATLAB adapter
  - Consumer: C++ OpenCV viewer
  - Test: channel order and class are displayed in viewer diagnostics.

- [ ] `/nav_viz/frontend/centroids`
  - Type: `eval_and_viz_gears_interfaces/CentroidArray`
  - QoS: best effort, keep last 1
  - Publisher: MATLAB adapter
  - Consumer: C++ OpenCV viewer
  - Test: centroid layer toggles on/off.

- [ ] `/nav_viz/frontend/features`
  - Type: `eval_and_viz_gears_interfaces/FeatureArray`
  - QoS: best effort, keep last 1
  - Publisher: MATLAB adapter
  - Consumer: C++ OpenCV viewer
  - Test: feature layer toggles on/off.

- [ ] `/nav_viz/frontend/tracks`
  - Type: `eval_and_viz_gears_interfaces/FeatureTrackArray`
  - QoS: best effort, keep last 1
  - Publisher: MATLAB adapter
  - Consumer: C++ OpenCV viewer
  - Test: track layer toggles on/off and length color mapping matches MATLAB baseline.

- [ ] `/nav_viz/frontend/status`
  - Type: `diagnostic_msgs/DiagnosticArray` or custom status
  - QoS: reliable or best effort depending on use
  - Publisher: MATLAB adapter and C++ viewer
  - Consumer: rqt/PlotJuggler/logs
  - Test: missing viewer does not block publisher.

### 3D Topics

- [ ] `/nav_viz/state/current_estimate`
  - Type: `eval_and_viz_gears_interfaces/StateEstimate`
  - QoS: best effort, keep last 1
  - Consumer: C++ RViz marker node
  - Test: pose marker appears in RViz.

- [ ] `/nav_viz/trajectory/estimated`
  - Type: `eval_and_viz_gears_interfaces/Trajectory` or `nav_msgs/Path`
  - QoS: best effort, keep last 1
  - Consumer: RViz/Foxglove
  - Test: trajectory updates online.

- [ ] `/nav_viz/trajectory/reference`
  - Type: `eval_and_viz_gears_interfaces/Trajectory` or `nav_msgs/Path`
  - QoS: best effort, keep last 1
  - Consumer: RViz/Foxglove
  - Test: reference and estimate use distinct colors/namespaces.

- [ ] `/nav_viz/trajectory/smoothed`
  - Type: `eval_and_viz_gears_interfaces/Trajectory` or `nav_msgs/Path`
  - QoS: best effort, keep last 1
  - Consumer: RViz/Foxglove
  - Test: optional topic can be absent without warnings.

- [ ] `/nav_viz/trajectory/gtsam_best`
  - Type: `eval_and_viz_gears_interfaces/Trajectory` or `nav_msgs/Path`
  - QoS: best effort, keep last 1
  - Consumer: RViz/Foxglove
  - Test: optional topic can be absent without warnings.

- [ ] `/nav_viz/map/landmarks`
  - Type: `eval_and_viz_gears_interfaces/LandmarkArray`
  - QoS: best effort, keep last 1
  - Consumer: RViz marker node
  - Test: large point set update is bounded or throttled.

- [ ] `/nav_viz/map/roi`
  - Type: `eval_and_viz_gears_interfaces/RoiRegionArray`
  - QoS: best effort, keep last 1
  - Consumer: RViz marker node
  - Test: ROI boundary renders and stale markers are deleted.

- [ ] `/nav_viz/covariance/ellipsoids`
  - Type: `eval_and_viz_gears_interfaces/CovarianceEllipsoidArray`
  - QoS: best effort, keep last 1
  - Consumer: RViz marker node
  - Test: ellipsoid geometry matches MATLAB baseline within tolerance.

- [ ] `/nav_viz/markers`
  - Type: `visualization_msgs/MarkerArray`
  - QoS: best effort, keep last 1
  - Publisher: C++ marker node
  - Consumer: RViz/Foxglove
  - Test: RViz receives marker array without stale marker growth.

### PlotJuggler Scalar Topics

Use standard numeric message topics when practical because they are easiest to configure in PlotJuggler.

Examples:

- [ ] `/nav_viz/errors/position/x`
- [ ] `/nav_viz/errors/position/y`
- [ ] `/nav_viz/errors/position/z`
- [ ] `/nav_viz/errors/position/norm`
- [ ] `/nav_viz/errors/velocity/x`
- [ ] `/nav_viz/errors/velocity/y`
- [ ] `/nav_viz/errors/velocity/z`
- [ ] `/nav_viz/errors/velocity/norm`
- [ ] `/nav_viz/covariance/position/xx`
- [ ] `/nav_viz/covariance/position/yy`
- [ ] `/nav_viz/covariance/position/zz`
- [ ] `/nav_viz/covariance/velocity/xx`
- [ ] `/nav_viz/covariance/velocity/yy`
- [ ] `/nav_viz/covariance/velocity/zz`
- [ ] `/nav_viz/empirical_covariance/position/xx`
- [ ] `/nav_viz/empirical_covariance/position/yy`
- [ ] `/nav_viz/empirical_covariance/position/zz`
- [ ] `/nav_viz/additional_state_error/<state_name>`
- [ ] `/nav_viz/additional_state_covariance/<state_name>`
- [ ] `/nav_viz/frontend/num_features`
- [ ] `/nav_viz/frontend/num_tracks`
- [ ] `/nav_viz/frontend/num_lost`
- [ ] `/nav_viz/performance/matlab_publish_ms`
- [ ] `/nav_viz/performance/viewer_render_ms`

Test:

- [ ] PlotJuggler layout loads and displays every expected topic.
- [ ] Missing optional topics do not break the layout.
- [ ] Time axes align with simulation time or ROS time by documented convention.

## QoS Policy

### Default Visualization QoS

- [ ] Use best effort for image, centroids, features, tracks, trajectories, markers, and high-rate scalars.
- [ ] Use keep last 1 for image and overlay topics.
- [ ] Use keep last N for scalar topics only when PlotJuggler needs short buffering.
- [ ] Avoid reliable QoS for high-rate image or overlay messages unless debugging message loss.
- [ ] Use reliable QoS for configuration/status only if required.

### Frame Dropping Policy

- [ ] MATLAB should publish only on configured visualization refresh frames.
- [ ] MATLAB should skip publish if visualization is disabled.
- [ ] C++ viewer should process the latest complete frame and drop stale overlay packets when falling behind.
- [ ] Viewer should not require every simulation frame.
- [ ] Publisher should continue when no subscriber exists.

## Configuration Plan

### MATLAB nav-system Configuration

Add settings under nav-system, preferably through YAML and `SetupOptions_COSMICAsys.m`.

Proposed fields:

```yaml
visualization:
  enable_matlab_plots: false
  enable_matlab_image_plots: false
  enable_ros2_publish: false
  ros2_domain_id: 42
  namespace: /nav_viz
  publish_rate_divider: 5
  publish_image: true
  publish_centroids: true
  publish_features: true
  publish_tracks: true
  publish_3d: true
  publish_errors: true
  publish_covariance: true
  publish_roi: true
  track_tail_length: 50
  image_transport: raw
  image_encoding_policy: preserve
  scalar_topic_mode: split
```

Tests:

- [ ] Defaults preserve current behavior.
- [ ] Monte Carlo mode disables ROS publish unless explicitly overridden.
- [ ] Existing MATLAB plotting can still be enabled independently.
- [ ] ROS 2 publish can be enabled while MATLAB plotting remains disabled.

### C++ Viewer Configuration

Proposed YAML:

```yaml
frontend_viewer:
  image_topic: /nav_viz/frontend/image
  metadata_topic: /nav_viz/frontend/image_metadata
  centroids_topic: /nav_viz/frontend/centroids
  features_topic: /nav_viz/frontend/features
  tracks_topic: /nav_viz/frontend/tracks
  show_centroids: true
  show_features: true
  show_tracks: true
  max_track_tail_length: 50
  track_colormap: turbo
  window_name: nav_frontend
  use_highgui: true
```

Tests:

- [ ] Viewer starts with default config.
- [ ] Layer flags can disable centroids/features/tracks.
- [ ] Missing metadata topic produces warning but not crash.

### PlotJuggler Layouts

Proposed files:

```text
ros2/eval_and_viz_gears_spinup/plotjuggler/
  frontend_tracks.xml
  estimation_errors.xml
  covariance.xml
  additional_states.xml
  performance.xml
```

Tests:

- [ ] Each XML opens in PlotJuggler.
- [ ] Each layout references topics from the topic plan.
- [ ] Layouts tolerate missing optional topics.

## Stage Plan

### Stage 0 - Audit, Plan, And Conflict Detection

Objective:

Establish current root-repo state, identify implementation inputs, avoid design conflicts, and create this plan.

Tasks:

- [x] Inspect target repository structure.
- [x] Inspect target C++ visualization primitives.
- [x] Inspect nav-backend plotting and online analysis functions.
- [x] Inspect nav-frontend plotting and temporary output generation functions.
- [x] Inspect nav-system integration points and configuration surface.
- [x] Inspect COSMICA simulation plotting entry points.
- [x] Re-run COSMICA search against `/home/peterc/devDir/projects-DART/cosmica-simulator` after the initial path correction.
- [x] Add COSMICA guidance, approach-preplan, run-context, YAML-loader, Monte Carlo, and legacy evaluation-script findings.
- [x] Inspect hyper_2 ROS 2, Docker, devcontainer, PlotJuggler, and RViz patterns.
- [x] Inspect cpp_cuda_template_project update relevance.
- [x] Re-review stable `cpp_cuda_template_project` tag `v1.11.1` at `ed11d83`.
- [x] Read `doc/developments/derived_project_upgrade_agent_guidelines.md` and apply its semantic-port/tailoring-preservation model to this plan.
- [x] Audit the complete `5cf1ac1..v1.11.1` donor delta by commits, changed paths, and functional groups.
- [x] Confirm target last committed template alignment is recorded as v1.5.0 in `db58f13` and identify current dirty overlap with the donor delta.
- [x] Confirm the stable donor includes the dependency-free `CLogger` but retains transitional spdlog compatibility.
- [x] Reclassify OptiX, ZeroMQ, and spdlog as explicit target removals with testable absence guards.
- [x] Select repository-local `ros2/` four-package layout from the stable overlay for the later ROS pass.
- [x] Identify root repositories under `/home/peterc/devDir` as source-of-truth references.
- [x] Identify design conflicts and mandatory gates.
- [ ] Review this plan with the user and update it iteratively before implementation.

Tests/checks:

- [x] Confirm plan is written under target repository documentation area.
- [ ] User review confirms source-of-truth repo roots and package layout.

Exit criteria:

- [ ] User approves Stage 1 start.
- [ ] No unresolved source-root ambiguity remains.

### Stage 1 - Freeze Baselines And Protect Dirty Work

Objective:

Record enough state to safely import/refactor across dirty root repositories.

Tasks:

- [ ] Capture `git status --short` for target, nav-backend, nav-frontend, nav-system, COSMICA, cpp_cuda_template_project, and hyper_2.
- [ ] Capture current HEAD commit for each root repo.
- [ ] Capture relevant diff stats for plotting/config/template files.
- [ ] Identify files that are modified in both template and target.
- [ ] Identify untracked MATLAB plotting utilities in nav-backend that are part of the current design.
- [ ] Identify untracked nav-frontend algorithms and feature producer code that must be supported by optional fields.
- [ ] Determine whether nav-system runtime uses root sibling repos or nested/submodule paths.
- [ ] Write a short baseline section into this document after the snapshot.

Tests/checks:

- [ ] `git status --short` output is saved or summarized in this document.
- [ ] No implementation files are edited in this stage.
- [ ] Any ambiguous repo path is reported before proceeding.

Exit criteria:

- [ ] All source roots are known.
- [ ] All dirty-state risks are documented.
- [ ] No accidental edit to sibling repos has occurred.

### Stage 2 - Stable v1.11.1 Standalone Template Alignment

Objective:

Semantically port the applicable `cpp_cuda_template_project` `v1.11.1` implementation into this repository while preserving target behavior and completing the target-specific removal of OptiX, ZeroMQ, and spdlog. This stage deliberately excludes ROS 2 packages, ROS 2 build helpers, ROS workflows, PlotJuggler, and ROS-enabled container configuration.

#### Stage 2.0 - Establish The Tagged Donor Contract

Tasks:

- [ ] Record the donor root as `/home/peterc/devDir/dev-tools/cpp_cuda_template_project`.
- [ ] Verify `git -C /home/peterc/devDir/dev-tools/cpp_cuda_template_project rev-parse v1.11.1^{commit}` returns `ed11d83`.
- [ ] Verify the donor worktree is clean and record that `main` is at `a9604ca`, one planning-only commit ahead of the selected tag.
- [ ] Record the previous reviewed donor snapshot `5cf1ac1` and the target's last explicit committed template alignment `db58f13` (`v1.5.0`).
- [ ] Save the `5cf1ac1..v1.11.1` commit list, file list, and functional classification in this document's implementation-status section.
- [ ] Create a temporary comparison tree with `mktemp -d` and `git archive v1.11.1`; do not switch or edit the donor checkout.
- [ ] In the temporary tree, run `./tailor_template_cleanup.sh --list --project-namespace viztools --remove-ros2` and review the reported removals before applying it there.
- [ ] In the temporary tree only, run `./tailor_template_cleanup.sh --apply --project-namespace viztools --remove-ros2 --yes` to create a derived-project comparison oracle.
- [ ] Record the additional manual tailoring that the donor script does not perform:
  - [ ] remove OptiX options, handlers, tests, examples, documentation, and workflow inputs;
  - [ ] remove the transitional spdlog adapter and all dependency/export wiring;
  - [ ] retain and rename the dependency-free logger to `viztools::logging`;
  - [ ] use `EVAL_AND_VIZ_LOG_LEVEL` instead of `TEMPLATE_PROJECT_LOG_LEVEL`;
  - [ ] retain CUDA independently from OptiX;
  - [ ] verify that ZeroMQ is absent from the tagged donor and remove the target's untracked module.
- [ ] Delete the temporary comparison tree after its inventory has been summarized; do not preserve generated build or install artifacts from it.

Tests/checks:

- [ ] `git -C /home/peterc/devDir/dev-tools/cpp_cuda_template_project diff --name-only v1.11.1..a9604ca` reports only `doc/developments/template_v2_test_ownership_plan.md`; no post-tag implementation file is admitted to Stage 2.
- [ ] `bash -n` passes for the donor `tailor_template_cleanup.sh` before the scratch run.
- [ ] The scratch-tailored tree contains no `ros2/`, `build_ros2.sh`, `add_ros2_support.sh`, ROS workflow, or COLCON marker.
- [ ] The scratch run leaves the donor checkout unchanged.
- [ ] Every donor delta group is classified as Adopt, Adapt, Skip/remove, Source-only, Later, or Blocked.

Exit criteria:

- [ ] The donor revision and derived-project comparison oracle are reproducible.
- [ ] No target file has been edited in Stage 2.0.
- [ ] No unclassified donor file group remains.

#### Stage 2.1 - Baseline The Target And Freeze Tailoring

Tasks:

- [ ] Record target branch, `HEAD`, upstream relation, staged state, unstaged state, untracked files, and ignored generated directories.
- [ ] Record the seven dirty paths that overlap the donor delta and treat their current contents as user-owned:
  - [ ] `.vscode/c_cpp_properties.json`;
  - [ ] `CMakeLists.txt`;
  - [ ] `build_lib.sh`;
  - [ ] `cmake/HandleCUDA.cmake`;
  - [ ] `cmake/HandleOptiX.cmake`;
  - [ ] `generate_version.sh`;
  - [ ] `src/CMakeLists.txt`.
- [ ] Exclude `.vscode/c_cpp_properties.json` from automatic template alignment; inspect it only for build include-path regressions.
- [ ] Exclude generated/local artifacts from comparisons and staging:
  - [ ] `build*`;
  - [ ] `install`;
  - [ ] `*.egg-info`;
  - [ ] `__pycache__`;
  - [ ] `.pytest_cache`;
  - [ ] `.mypy_cache`;
  - [ ] `.bak.*`;
  - [ ] `.vscode/browse.vc.db` and other workspace databases.
- [ ] Create a tailoring-preservation ledger covering:
  - [ ] CMake project and package identity `EvalAndVizGears_for_ComputerVision`;
  - [ ] public C++ namespace `viztools`;
  - [ ] OpenCV rendering and image color-order contracts;
  - [ ] Pangolin absent;
  - [ ] CUDA retained independently from OptiX;
  - [ ] OptiX absent;
  - [ ] ZeroMQ absent;
  - [ ] spdlog absent after replacement;
  - [ ] ROS 2 absent during Stage 2;
  - [ ] wrapper and Python package identity;
  - [ ] standalone CMake package export and installed-consumer behavior;
  - [ ] target-owned CI runner and release policy.
- [ ] Capture the current configured test inventory. The existing build currently enumerates 41 tests, including four legacy spdlog tests.
- [ ] Run the current applicable baseline tests before implementation and record exact pass/fail totals and warnings.
- [ ] Record whether CPU clean configure/build, existing build-tree tests, install-tree consumer tests, Python tests, CUDA configure/build, and docs are available in the local environment.

Tests/checks:

- [ ] `ctest --test-dir build -N` output is summarized in this document.
- [ ] `ctest --test-dir build --output-on-failure` establishes the pre-change behavioral baseline.
- [ ] `./build_lib.sh --help` and `./configure_devcontainer.sh --help` are captured before alignment.
- [ ] No existing dirty file is replaced wholesale.
- [ ] Any pre-existing red gate is reported and approved before implementation continues.

Exit criteria:

- [ ] The target baseline and tailoring ledger are recorded.
- [ ] Every dirty overlap has an explicit merge strategy.
- [ ] The validation environment and unavailable gates are known.

#### Stage 2.2 - Add Tailoring Regression Guards First

Tasks:

- [ ] Add a target-owned CMake regression test, for example `tests/cmake/VerifyDerivedFeaturePolicy.cmake`, before removing features.
- [ ] Make the guard fail while any of these source paths exist:
  - [ ] `cmake/HandleOptiX.cmake`;
  - [ ] `cmake/HandleSpdlog.cmake`;
  - [ ] `cmake/HandleZeroMQ.cmake`;
  - [ ] `src/utils/logging/SpdlogUtils.h`;
  - [ ] `src/utils/logging/SpdlogUtils.cpp`;
  - [ ] `tests/template_test/testLogging.cpp`.
- [ ] Make the guard scan tracked build/runtime/package files, excluding historical development plans, for stale feature identifiers:
  - [ ] `ENABLE_OPTIX`, `OPTIX_COMPILE_TARGET`, `USE_SYS_OPTIX_SDK`, and `__OPTIX_ENABLED__`;
  - [ ] `ENABLE_ZEROMQ`, `ENABLE_FETCH_CPPZMQ`, `CPPZMQ`, and `__ZEROMQ_ENABLED__`;
  - [ ] `ENABLE_SPDLOG`, `ENABLE_FETCH_SPDLOG`, `SPDLOG_COMPILE_TARGET`, `SPDLOG_UTILS_ENABLED`, `SpdlogUtils`, and `find_dependency(spdlog)`.
- [ ] Make the guard verify that no ROS 2 overlay path or root ROS build helper is introduced in Stage 2.
- [ ] Add target-adapted logger tests based on `v1.11.1` `testProjectLogger.cpp` for:
  - [ ] severity threshold filtering;
  - [ ] stdout versus diagnostic-stream routing;
  - [ ] case-insensitive and numeric level parsing;
  - [ ] `EVAL_AND_VIZ_LOG_LEVEL` behavior;
  - [ ] invalid environment input leaving the level unchanged;
  - [ ] deterministic color-disabled output;
  - [ ] explicit ANSI color output;
  - [ ] complete-line serialization under concurrent writers;
  - [ ] namespace and default-component identity.
- [ ] Register the new policy and logger tests through the target's existing CTest conventions.

Tests/checks:

- [ ] The feature-policy guard initially fails for the known OptiX, ZeroMQ, and spdlog remnants.
- [ ] The new logger test initially fails because `viztools::logging::CLogger` does not yet exist.
- [ ] Existing non-logging tests remain runnable while the red guards are present.

Exit criteria:

- [ ] The intended removals and logger replacement are executable contracts, not only checklist prose.
- [ ] Failures point to exact stale paths or identifiers.

#### Stage 2.3 - Remove Unsupported Features And Adopt CLogger

Tasks:

- [ ] Remove ZeroMQ completely:
  - [ ] delete untracked `cmake/HandleZeroMQ.cmake`;
  - [ ] verify no tracked CMake option, source include, package dependency, build-script flag, documentation promise, or test advertises ZeroMQ;
  - [ ] remove the former fallback recommendation from user-facing architecture documentation.
- [ ] Remove OptiX completely while preserving CUDA:
  - [ ] remove `ENABLE_OPTIX` and `USE_SYS_OPTIX_SDK` options;
  - [ ] remove automatic `ENABLE_CUDA` mutation from OptiX;
  - [ ] remove C-language enablement that exists only for OptiX PTX embedding;
  - [ ] remove `OPTIX_COMPILE_TARGET`;
  - [ ] remove `cmake/HandleOptiX.cmake` and all includes/calls;
  - [ ] remove OptiX compile definitions, include paths, package exports, tests, workflow inputs, build-script flags, and documentation;
  - [ ] retain generic CUDA compilation and reusable PTX source classification only where a non-OptiX target uses it;
  - [ ] verify the ordinary CPU build does not probe an OptiX SDK.
- [ ] Remove spdlog completely:
  - [ ] remove `ENABLE_SPDLOG` and `ENABLE_FETCH_SPDLOG`;
  - [ ] remove `SPDLOG_COMPILE_TARGET`, `HandleSpdlog.cmake`, and `handle_spdlog()`;
  - [ ] remove spdlog from `EXPORT_TARGET_DEPS` and installed package dependency expansion;
  - [ ] remove `SPDLOG_UTILS_ENABLED` compile definitions and conditional links from root/source/example/test CMake;
  - [ ] remove `SpdlogUtils.h`, `SpdlogUtils.cpp`, and `testLogging.cpp`;
  - [ ] update or remove inherited example code that includes spdlog;
  - [ ] verify no network fetch or system package discovery for spdlog remains.
- [ ] Adapt the `v1.11.1` dependency-free logger:
  - [ ] add `src/utils/logging/CLogger.h` and `CLogger.cpp` using the donor implementation as the behavioral source;
  - [ ] use namespace `viztools::logging`;
  - [ ] use default component name `eval_and_viz_gears` when the caller supplies an empty name;
  - [ ] use `EVAL_AND_VIZ_LOG_LEVEL` as the default environment variable;
  - [ ] keep color output disabled by default;
  - [ ] keep caller-owned output streams and complete-line cross-instance synchronization;
  - [ ] always compile/install `CLogger` without a feature option;
  - [ ] update target examples to demonstrate `CLogger` rather than spdlog.
- [ ] Keep `CTrackingStatsLogger` separate from diagnostic logging; it remains the project-specific frame-statistics/CSV component and must not be renamed or conflated with `CLogger`.

Tests/checks:

- [ ] Run the new logger test group after each coherent logger edit.
- [ ] Run the feature-policy guard after ZeroMQ removal, after OptiX removal, and after spdlog removal so each removal is independently reviewable.
- [ ] Configure and build the CPU-only library with network access unavailable or dependency fetching disabled; no spdlog lookup occurs.
- [ ] Inspect the generated package config and exported targets after a clean install; neither `spdlog` nor OptiX appears.
- [ ] Run all existing OpenCV renderer and `CTrackingStatsLogger` tests to prove the logging replacement did not change visualization/statistics behavior.

Exit criteria:

- [ ] OptiX, ZeroMQ, and spdlog are absent from source/build/package contracts.
- [ ] `viztools::logging::CLogger` passes its focused tests without third-party dependencies.
- [ ] CUDA remains independently configurable.
- [ ] No ROS 2 content has been introduced.

#### Stage 2.4 - Align Generic Build, Version, Wrapper, And Test Infrastructure

Tasks:

- [ ] Align `build_lib.sh` through a semantic merge, preserving target flags and adding applicable v1.11.1-era controls:
  - [ ] `--python-test-conda-env`;
  - [ ] `--python-test-conda-prefix`;
  - [ ] `--python-test-executable`;
  - [ ] `--ctest-extra-args`;
  - [ ] corresponding CMake definitions;
  - [ ] no `--optix`, ZeroMQ, spdlog, or ROS option.
- [ ] Preserve existing build-script behavior:
  - [ ] default build path;
  - [ ] clean behavior;
  - [ ] wrapper toggles;
  - [ ] install/test defaults;
  - [ ] target-specific CUDA and OpenCV behavior.
- [ ] Align root CMake versioning behavior:
  - [ ] preserve prerelease and build metadata from `git describe`;
  - [ ] add `WRITE_SOURCE_VERSION_FILE` defaulting `OFF`;
  - [ ] always write the build-tree `VERSION`;
  - [ ] install the build-tree `VERSION`;
  - [ ] keep a no-Git source/archive fallback;
  - [ ] ensure ordinary configure does not dirty the source tree.
- [ ] Rebase `generate_version.sh` onto the complete `v1.11.1` implementation:
  - [ ] retain no-argument VERSION generation;
  - [ ] retain `--help` and unknown-argument failure;
  - [ ] retain `--sync-ros2` as a future-compatible no-op that reports the absent overlay and exits successfully during Stage 2;
  - [ ] do not import `ros2/tools/sync_package_metadata.py` until the ROS stage;
  - [ ] verify the generated core, prerelease, metadata, and full-version fields match CMake.
- [ ] Align reusable CPack source-release behavior without adding ROS release requirements:
  - [ ] define canonical TGZ source packaging;
  - [ ] exclude build/install/cache/generated artifacts;
  - [ ] include the generated VERSION metadata needed by a no-Git archive;
  - [ ] keep project identity and release naming target-specific.
- [ ] Align target naming controls:
  - [ ] add `LIB_TARGET_NAME` with `LIB_TARGET_NAME_OVERRIDE` if still applicable in `v1.11.1`;
  - [ ] add `${LIB_NAMESPACE}_BUILD_PROGRAMS`;
  - [ ] add `${LIB_NAMESPACE}_BUILD_EXAMPLES`;
  - [ ] preserve CMake project identity, installed namespace, Python package identity, and `viztools` API.
- [ ] Align compiler flag handling:
  - [ ] import/adapt `cmake/HandleCompilerFlags.cmake` from the applicable stable donor history;
  - [ ] remove duplicated inline compiler-flag logic only after equivalent target behavior is covered;
  - [ ] call the target-adapted compiler flag functions with C++20;
  - [ ] preserve `NO_OPTIMIZATION`, sanitizer, user extra flags, CUDA flags, and profiler-friendly behavior.
- [ ] Align Python pytest CTest support:
  - [ ] `ENABLE_PYTHON_TESTS`;
  - [ ] `PYTHON_TEST_RUNNER`;
  - [ ] `PYTHON_TEST_EXECUTABLE`;
  - [ ] `PYTHON_TEST_CONDA_ENV`;
  - [ ] `PYTHON_TEST_CONDA_PREFIX`;
  - [ ] `PYTHON_TEST_CONDA_EXECUTABLE`;
  - [ ] target-specific smoke coverage for `python/EvalAndVizGears_for_ComputerVision`.
- [ ] Align Catch2 registration controls:
  - [ ] `CATCH2_TEST_REPORTER`;
  - [ ] `CATCH2_TEST_PROPERTIES`;
  - [ ] target-adapted `add_tests()` property handling;
  - [ ] existing `tests/core` discovery and labels.
- [ ] Align wrapper support only after the standalone C++ baseline is green:
  - [ ] compare `cmake/HandleWrapper.cmake` semantically;
  - [ ] compare `python/setup.py.in` and `python/pyproject.toml.in` semantically;
  - [ ] preserve target wrapper interfaces and package name;
  - [ ] verify both wrapper-disabled and supported wrapper-enabled configuration paths.

Tests/checks:

- [ ] `bash -n build_lib.sh generate_version.sh configure_devcontainer.sh` passes after each script group.
- [ ] `./build_lib.sh --help` lists only supported target options.
- [ ] Default configure leaves source VERSION state unchanged.
- [ ] `WRITE_SOURCE_VERSION_FILE=ON` changes source VERSION only when explicitly requested.
- [ ] `./generate_version.sh` and CMake resolve matching version fields from the same Git state.
- [ ] `./generate_version.sh --sync-ros2` succeeds with an explicit “overlay absent” path and creates no ROS files.
- [ ] Invalid `generate_version.sh` arguments fail without changing project files.
- [ ] Python-test option conflict tests pass with Python tests enabled and are ignored when disabled.
- [ ] Existing C++ tests remain discoverable through CTest after registration changes.

Exit criteria:

- [ ] Generic build/version/wrapper/test improvements are aligned without unsupported feature flags.
- [ ] Version generation is consistent across script, CMake, package metadata, and source archive.
- [ ] The target's project and package identities remain unchanged.

#### Stage 2.5 - Align CUDA, Install, Export, And Consumer Behavior

Tasks:

- [ ] Port the reusable `v1.11.1` CUDA source-classification fix from `cmake/HandleCUDA.cmake` and affected source CMake files.
- [ ] Distinguish ordinary `.cu` translation units from dedicated `*.ptx.cu` inputs without reintroducing OptiX ownership.
- [ ] Remove target branches that exist solely to generate/embed OptiX PTX while preserving generic CUDA compilation used by the project.
- [ ] Adapt the nested-header install fix to real target directories:
  - [ ] `src/core`;
  - [ ] `src/utils`;
  - [ ] `src/utils/logging`;
  - [ ] `src/utils/wrap_adapters`;
  - [ ] any current project-specific nested public header directory.
- [ ] Align build-tree and install-tree package config behavior while preserving target dependencies `Eigen3`, OpenCV, optional CUDA, and any currently supported TBB/OpenGL choices, with Pangolin absent.
- [ ] Ensure optional dependencies are exported only when actually enabled and required by the public interface.
- [ ] Adapt the donor's source-release and nested-consumer tests to target headers and targets rather than template placeholder paths.

Tests/checks:

- [ ] Clean CPU configure/build/test/install passes.
- [ ] A minimal external consumer can `find_package(EvalAndVizGears_for_ComputerVision CONFIG REQUIRED)` against both build-tree and install-tree packages and link a real target header/API.
- [ ] Installed headers include the target-adapted `utils/logging/CLogger.h` and required nested visualization headers.
- [ ] Installed package files contain no absolute source/build paths and no spdlog, OptiX, ZeroMQ, or ROS dependency.
- [ ] CUDA-enabled configure and build pass when the local toolkit is available.
- [ ] When CUDA execution hardware is unavailable, configure/source-inventory/compile-database checks still prove ordinary `.cu` and `*.ptx.cu` classification without claiming a runtime pass.
- [ ] CPU-only configuration does not require CUDA or an OptiX SDK.

Exit criteria:

- [ ] Build-tree and install-tree consumption are verified.
- [ ] CUDA behavior is retained without OptiX.
- [ ] Installed exports reflect only enabled target dependencies.

#### Stage 2.6 - Align Generic Documentation, CI, And Devcontainer Baseline

Tasks:

- [ ] Align target-owned generic documentation where it describes behavior adopted in Stage 2:
  - [ ] build and test entry points;
  - [ ] versioning and CPack source releases;
  - [ ] dependency-free logging;
  - [ ] wrappers;
  - [ ] documentation workflow;
  - [ ] CUDA support and explicit absence of OptiX;
  - [ ] explicit absence of ZeroMQ and spdlog.
- [x] Do not copy donor development plans, reports, `CLAUDE.md`, `CONTEXT.md`, or deleted workspace-file history.
- [x] Import and tailor applicable parent-workspace and donor `AGENTS.md` guidance as the final Stage 2 review step; preserve target ownership, commands, namespace, image color-order contract, and standalone-versus-ROS stage boundaries rather than copying donor instructions verbatim.
- [ ] Review generic workflow templates from `v1.11.1` as derived-project inputs:
  - [ ] preserve target runner labels, branches, permissions, and secrets policy;
  - [ ] retain the self-hosted CUDA opt-in guard when a CUDA workflow is owned by the target;
  - [ ] materialize only target-owned generic workflows;
  - [ ] do not copy active donor template-validation workflows;
  - [ ] do not add the ROS overlay workflow in Stage 2.
- [ ] Review the pull-request template as optional repository policy, separately from build alignment.
- [ ] Align the generic devcontainer assets needed for the standalone project:
  - [ ] `.devcontainer/Dockerfile`;
  - [ ] `.devcontainer/devcontainer.json`;
  - [ ] `.devcontainer/update_devcontainer_json.py`;
  - [ ] `.devcontainer/cuda-setup.sh`;
  - [ ] `.devcontainer/custom-setup.sh`;
  - [ ] `.devcontainer/reinstall-cmake.sh` only if the selected base requires it;
  - [ ] `configure_devcontainer.sh` CUDA-version and Docker/Podman GPU-runtime selection.
- [ ] Defer `.devcontainer/ros-setup.sh`, ROS packages, PlotJuggler installation, ROS environment variables, and ROS networking to Stage 3.
- [ ] Keep this development plan in `doc/developments/`; do not expose it through generated public Doxygen output.

Tests/checks:

- [ ] Parse every changed workflow and JSON file with a structured parser.
- [ ] Run target-owned static workflow tests against materialized generic workflows.
- [ ] `./configure_devcontainer.sh --help` advertises only the standalone Stage 2 capabilities.
- [ ] Devcontainer JSON generation is deterministic for CPU, Docker GPU, and Podman CDI selections.
- [ ] Build the standalone devcontainer when Docker/Podman is available; otherwise record syntax/static validation as partial.
- [ ] Search active CI and container files to confirm no ROS, PlotJuggler, OptiX, ZeroMQ, or spdlog dependency is introduced.

Exit criteria:

- [ ] Documentation and automation describe the implemented standalone feature set exactly.
- [ ] Generic devcontainer support is aligned without enabling ROS.
- [ ] Workflow ownership remains target-specific.

#### Stage 2.7 - Full Alignment Validation And Review Gate

Tasks:

- [ ] Run a clean standalone CPU build from the documented entry point.
- [ ] Run the complete CTest suite and compare failures against the Stage 2.1 baseline.
- [ ] Run Python tests when enabled.
- [ ] Run build-tree and install-tree consumer tests.
- [ ] Run source-release generation and no-Git archive validation.
- [ ] Run CUDA gates available on the current machine and label unavailable runtime gates explicitly.
- [ ] Run documentation configure/build and inspect generated output for internal-plan leakage.
- [ ] Run generic devcontainer tests available in the environment.
- [ ] Run hygiene checks:
  - [ ] `git diff --check`;
  - [ ] conflict-marker scan;
  - [ ] stale donor identity scan;
  - [ ] machine-local absolute-path scan over added lines;
  - [ ] generated-artifact and bytecode scan;
  - [ ] executable-bit check for scripts;
  - [ ] feature-policy absence guard;
  - [ ] ROS-overlay absence guard.
- [ ] Inspect every changed file in target context and verify that no user-owned dirty change was overwritten.
- [ ] Update this document with:
  - [ ] imported/adapted donor capabilities;
  - [ ] skipped/source-only/later donor capabilities;
  - [ ] exact validation commands and totals;
  - [ ] warnings and unavailable gates;
  - [ ] residual risks;
  - [ ] proposed functional commit groups without creating commits.

Tests/checks:

- [ ] `./build_lib.sh --clean` passes with target defaults.
- [ ] `ctest --test-dir build --output-on-failure` passes with the new CLogger tests replacing the four legacy spdlog tests.
- [ ] The policy guard proves OptiX, ZeroMQ, spdlog, and ROS are absent from active source/build/package surfaces.
- [ ] Clean install and external consumer tests pass.
- [ ] `./generate_version.sh`, CMake version resolution, and CPack source archive agree.
- [ ] No new warning or failure is hidden by comparing only raw test totals.

Exit criteria:

- [ ] The target is aligned to applicable `v1.11.1` behavior as a derived project.
- [ ] The standalone build is green before any ROS 2 integration starts.
- [ ] OptiX, ZeroMQ, and spdlog removal is verified in source and installed outputs.
- [ ] All skipped and deferred donor deltas are documented.
- [ ] Stage 3 remains blocked until the user reviews the Stage 2 evidence and explicitly starts the ROS 2 pass.

#### Stage 2.8 - Implementation Evidence And Consolidation Handoff

Status:

- [x] Stage 2 implementation is complete for the standalone target baseline.
- [x] The final review was performed after adding the target-owned root `AGENTS.md`.
- [x] No commit was created; the working tree remains available for user review and consolidation.
- [x] ROS 2, PlotJuggler, RViz/Foxglove, and MATLAB ROS publishing were not introduced in this pass.

Pinned source and ownership evidence:

- [x] The donor source was pinned to `cpp_cuda_template_project` tag `v1.11.1`, commit `ed11d837fc9e107f00ca462fefd47e7da73c5d2a`.
- [x] The target baseline was branch `feature/add_base_implementation_ocv` at commit `651f2d5` before Stage 2 edits.
- [x] The target's previous explicit template-alignment reference was `db58f13` (`v1.5.0`).
- [x] The stable-tag implementation was ported semantically rather than by replacing target files wholesale.
- [x] The pre-existing user edit to `.vscode/c_cpp_properties.json` was inspected but not modified or reverted by this pass.
- [x] No sibling repository was edited by this pass.
- [x] The donor checkout was dirty during the original v1.11.1 pass, so uncommitted files were excluded; the v1.11.3 incremental review later confirmed a clean tagged donor checkout.

Tailoring and dependency evidence:

- [x] Removed active OptiX options, handlers, PTX embedding helper, build paths, tests, package wiring, and documentation promises while retaining generic CUDA support.
- [x] Removed ZeroMQ support and guarded against its reintroduction in active build/runtime/automation surfaces.
- [x] Removed spdlog options, discovery/fetch/export wiring, adapter sources, and legacy tests.
- [x] Added the dependency-free `viztools::logging::CLogger` with `EVAL_AND_VIZ_LOG_LEVEL`, deterministic color control, target identity, caller-owned streams, and synchronized complete-line output.
- [x] Kept `CTrackingStatsLogger` as the independent frame-statistics and CSV facility.
- [x] Added `tests/cmake/VerifyDerivedFeaturePolicy.cmake` to enforce the target's removals and the Stage 2 no-ROS boundary.
- [x] Added six focused CLogger test cases covering filtering/routing, level parsing, environment configuration, target identity, color behavior, and concurrent complete-line serialization.

Generic template-alignment evidence:

- [x] Aligned C++20 compiler-flag management through `cmake/HandleCompilerFlags.cmake` while preserving no-optimization and user-extra-flag behavior.
- [x] Aligned source-side-effect-free Git version resolution, build-tree `VERSION` generation, explicit source synchronization, prerelease/build metadata, and no-Git fallback behavior.
- [x] Rebased `generate_version.sh` with help, unknown-argument failure, and a Stage 2-safe `--sync-ros2` no-op when no overlay exists.
- [x] Added canonical source TGZ packaging and a regression that configures a generated no-Git source release.
- [x] Fixed source-package exclusion anchoring so a checkout located below a parent directory named `build*` is not excluded wholesale.
- [x] Aligned target naming, program/example gates, Python-test controls, Catch2 registration controls, wrapper controls, profiling options, install exports, and build/install consumer behavior.
- [x] Corrected nested public-header install roots and validated installed consumers.
- [x] Classified ordinary `.cu` and dedicated `*.ptx.cu` sources without OptiX ownership.
- [x] Updated wrapper packaging templates and ignored generated wrapper metadata files.
- [x] Built a Python wrapper artifact using the local `wrap` checkout with automatic donor updates disabled.
- [x] Built a MATLAB R2023b `.mexa64` wrapper artifact using an isolated copy of `gtwrap`, leaving the sibling wrapper checkout unchanged.
- [ ] Populate `src/wrap_interface.i` with the target API selected during consolidation; Stage 2 proves wrapper infrastructure only because the current namespace block exposes no classes.
- [ ] Decide whether warnings emitted from generated/third-party wrapper code should be suppressed at the external-project boundary; target-owned sources build without those warnings.

Documentation, automation, and policy evidence:

- [x] Rewrote the README and build-script reference for the target's implemented standalone behavior.
- [x] Added focused logging, versioning, testing, and CI documentation.
- [x] Added Doxygen HTML/XML generation with strict warning support and kept internal development plans outside public output.
- [x] Replaced inherited template workflow variants with target-owned CPU and guarded self-hosted CUDA workflows.
- [x] Added a standalone CPU/CUDA devcontainer, deterministic JSON updater, setup scripts, and container launcher without ROS 2 middleware.
- [x] Added target-owned Python smoke and devcontainer JSON tests.
- [x] Added root `AGENTS.md` last, after reviewing parent-workspace guidance, donor guidance, and derived-project tailoring rules.
- [x] Tailored `AGENTS.md` to target ownership, dirty-tree safety, no-commit policy, exact build/test commands, standalone/ROS boundaries, C++20 and `viztools` conventions, OpenCV BGR handling, CUDA, wrappers, and semantic three-way ports.

Validation evidence recorded on 2026-07-22:

- [x] Pre-change baseline: the existing standalone CTest inventory passed 41/41 tests, including four legacy spdlog tests that were subsequently replaced.
- [x] Final clean CPU command: `./build_lib.sh -B build_stage2_clean --clean -N -DCPU_ENABLE_NATIVE_TUNING=OFF`.
- [x] Final clean CPU result: configure, compile, and 52/52 CTest tests passed; total test wall time was 14.15 seconds.
- [x] CUDA command used the local CUDA 12.9 toolkit, detected architecture `sm_120`, compiled successfully, and passed 52/52 CTest tests.
- [x] Package-consumer regression validated top-level build-tree, install-tree, and nested `add_subdirectory` consumption.
- [x] Source-release regression generated/extracted the TGZ archive, verified required metadata and excluded artifacts, and configured the archive with Git discovery blocked.
- [x] Strict documentation configuration/build completed without Doxygen warnings and generated HTML, XML, and a tag file.
- [x] Python tests passed through CTest; an additional direct source-layout invocation with `PYTHONPATH=python` passed 4/4 tests.
- [x] Python and MATLAB wrapper generation/linking passed; no wrapper API behavior is claimed while `wrap_interface.i` is empty.
- [x] Workflow YAML, devcontainer JSON, CMake presets JSON, and Python packaging TOML parsed with structured parsers.
- [x] Changed Python files parsed as valid AST; changed shell scripts passed `bash -n` and `shellcheck`.
- [x] Standalone CPU Docker image built without Dockerfile warnings and passed runtime checks for CMake 3.28.3, GCC 13.3, pytest 7.4.4, OpenCV 4.6, and Eigen headers.
- [x] `git diff --check`, conflict-marker scan, active stale-feature scan, source-path scan, executable-bit review, and derived-feature policy passed before cleanup.
- [x] Removed only Stage 2-generated build trees, wrapper-generated source metadata/cache files, and the `evalandviz-stage2-cpu` image after preserving the evidence in this section.
- [x] Removed approximately 446 MB of named Stage 2 build trees and the 3,240,573,597-byte Docker image reference; Docker-wide pruning was deliberately not used because shared layers and unrelated caches are outside this task's ownership.
- [x] Preserved the pre-existing root `build/` directory and the separately created `build_stage0_ros2_timing/` directory.
- [x] Re-ran the derived-feature policy, structured parsers, `bash -n`, full `shellcheck`, `git diff --check`, image-absence check, and exact artifact-absence check after cleanup; all passed.

Residual risks and deferred work:

- [x] Re-reviewed the donor after its changes were committed and tagged as v1.11.3; no uncommitted donor content was admitted.
- [ ] Consolidate the currently empty wrapper interface against the public visualization DTO/API selected for the ROS-independent core.
- [ ] Re-run MATLAB wrapper behavior tests after real classes are exposed.
- [ ] Establish the ROS 2 package/interface ownership and MATLAB-compatible generated-message workflow in Stage 3 and later.
- [ ] Install and configure PlotJuggler only after scalar topic contracts and ROS 2 environment ownership are fixed.
- [ ] Preserve the standalone build/test/package lane after ROS support is introduced.

Proposed functional commit groups, without creating commits:

- [ ] Commit group 1: target tailoring guard, OptiX/ZeroMQ/spdlog removal, dependency-free CLogger, and focused logger tests.
- [ ] Commit group 2: generic CMake/build/version/package/install/CUDA/wrapper alignment and regression tests.
- [ ] Commit group 3: target documentation, CI workflows, standalone devcontainer, and Python smoke/configuration tests.
- [ ] Commit group 4: target `AGENTS.md` policy and this persistent implementation-evidence update.

#### Stage 2.9 - Incremental v1.11.3 Template Alignment

Historical note: the validation inventory below records the state before the
full derivation-boundary review in Stage 2.10. Template-conformance tests listed
here were subsequently removed from this derived repository at the user's
direction; their historical pass results remain evidence for the original port,
not the current target-owned test inventory.

Status and source:

- [x] Pinned donor tag `v1.11.3` to commit `f3fd6555c7c965eebc89d5aa40227b0f36ac5fde`.
- [x] Confirmed the donor checkout was clean on `main` at the tagged commit.
- [x] Preserved the target's uncommitted v1.11.1 alignment and concurrent ROS timing-benchmark changes through a semantic three-way port.
- [x] Did not edit any sibling repository and did not create a commit.

Donor delta classification from `v1.11.1..v1.11.3`:

- [x] `a9604ca` template-v2 planning document: source-only donor planning; not imported.
- [x] `6202cb1` complete spdlog removal: already implemented and more strictly guarded in this target; no dependency was restored.
- [x] `e6ba9df` expanded agent guidance: applicable changed-file review guidance was adapted into target `AGENTS.md`; donor `CONTEXT.md` and template-specific instructions were rejected.
- [x] `a467fd2` automatic ROS package metadata synchronization: adopted and adapted for the target's single `_ros` package rather than the donor's four-package overlay quartet.
- [x] `f3fd655` donor package release versions: classified source-only; target package identity and version remain `eval_and_viz_gears_ros` and `0.2.0`.
- [x] Donor `add_ros2_support.sh`, `build_ros2.sh`, package quartet, ROS workflow, and overlay documentation: deferred or rejected because the current target owns one isolated benchmark package and keeps root CMake ROS-independent.
- [x] Donor OptiX support: rejected under the target's established feature policy.
- [x] Donor ZeroMQ and legacy spdlog compatibility: remain absent.

Implemented alignment:

- [x] Completed the existing `generate_version.sh` automatic/default, explicit `--sync-ros2`, and `--no-sync-ros2` interface with v1.11.3 safeguards for hardcoded fallback versions, strict core versions, missing helpers, and unavailable Python.
- [x] Added `ros2/tools/sync_package_metadata.py` using root metadata-only CMake configuration as the source of truth.
- [x] Adapted package-role inference by suffix so a standalone `_ros` package is supported without fabricating the donor's shim/interfaces/bridge/spinup quartet.
- [x] Synchronization updates strict core version, project-derived description, maintainer, license, and website while preserving package names, dependencies, non-website URLs, and file modes.
- [x] Synchronized `ros2/eval_and_viz_gears_ros/package.xml`; repeated default generation is byte-idempotent.
- [x] Added five focused pytest cases for default synchronization, idempotence, opt-out behavior, hardcoded-fallback safety, mismatch-before-mutation behavior, and repository manifest consistency.
- [x] Expanded the derived-feature policy narrowly to admit only `ros2/tools/sync_package_metadata.py`; unapproved ROS children and ad-hoc tools remain rejected by self-fixtures.
- [x] Added root and nested colcon output ignores and excluded root `log/`, `output_data/`, and nested ROS build/install/log trees from CPack source archives.
- [x] Extended the source-release regression to require the ROS package/helper and reject generated ROS/benchmark output sentinels.
- [x] Documented default ROS metadata synchronization and the opt-out path in `doc/versioning.md`.
- [x] Added the applicable v1.11.3 changed-file review guidance to target `AGENTS.md` without authorizing staging or unrelated cleanup.

RED/GREEN and validation evidence:

- [x] Pre-change clean baseline passed 55/55 CTest tests using `CMAKE_PREFIX_PATH=/tmp/codex-sdd-019f895c/slam-primitives-install`.
- [x] Initial metadata regression failed 4/4 cases because the helper was absent and the repository manifest was not synchronized.
- [x] After adding the helper, isolated behavior passed while repository consistency remained RED; running the canonical generator synchronized one manifest.
- [x] Hardcoded-fallback regression reproduced a nonzero metadata mismatch before the v1.11.3 script safeguard was ported.
- [x] Source-release sentinel regression reproduced generated root `log/` leakage before CPack exclusions were added.
- [x] Focused metadata suite passed 5/5 after implementation.
- [x] Derived-feature policy and source-release regression passed after the narrow tool allowlist and generated-output exclusions.
- [x] Final clean standalone build passed 56/56 CTest tests; total test wall time was 15.55 seconds.
- [x] Strict Doxygen HTML/XML generation passed without warnings.
- [x] Python AST/bytecode compilation, package XML parsing, `bash -n`, `shellcheck`, removed-dependency scan, manifest idempotence, and `git diff --check` passed.
- [x] `ruff` was unavailable in the host environment and is not claimed as run.
- [x] CUDA, wrappers, and container images were not rebuilt because the `v1.11.1..v1.11.3` applicable delta did not change those surfaces; their prior Stage 2 evidence remains unchanged.
- [x] Removed approximately 323 MB of v1.11.3 alignment build, policy, documentation, pytest, and bytecode artifacts after recording the evidence.
- [x] Preserved the pre-existing root `build/`, concurrent `build_stage0_ros2_timing/`, ROS benchmark logs, and all user/concurrent source changes.
- [x] Re-ran source-only policy, Python/XML parsing, `bash -n`, `shellcheck`, artifact-absence, and `git diff --check` gates after cleanup; all passed.

#### Stage 2.10 - Full v1.11.3 Derivation-Boundary Audit

Objective:

Re-audit the complete stable `v1.11.3` tagged tree, not only the
`v1.11.1..v1.11.3` commit delta, and align every applicable improvement while
preserving this derived repository's product ownership and explicit removals.

Authoritative inputs:

- [x] Use donor tag `v1.11.3` at `f3fd6555c7c965eebc89d5aa40227b0f36ac5fde`.
- [x] Read `doc/developments/derived_project_upgrade_agent_guidelines.md` and
  apply its authority order, three-way semantic-port model, and rule that absent
  donor paths remain absent until target history or the user establishes ownership.
- [x] Read `doc/developments/template_v2_test_ownership_plan.md` specifically for
  the template-conformance versus derived-project runtime-test boundary.
- [x] Run `tailor_template_cleanup.sh` only in a disposable archived donor tree
  with `--project-namespace viztools --remove-ros2`; do not copy or retain the
  tailoring script in this repository.
- [x] Confirm that the donor retains issue forms, generic workflows, docs guides,
  CMake/build helpers, examples, toolchains, devcontainer assets, and starter
  tests after tailoring, but removes template-maintainer plans, reports,
  `VerifyTemplateProject*` tests, workflow-template tests, ROS static tests, and
  MATLAB template regressions.

Corrected test ownership:

- [x] Apply the user's stricter target tailoring: retain tests only for runtime
  code owned by this repository.
- [x] Remove imported CMake/compiler/version/source-release/package-consumer,
  devcontainer, metadata-sync, Python-import scaffold, and template-policy tests.
- [x] Remove the placeholder Catch2 test and its unused starter fixtures.
- [x] Remove the unused generated `config.h` starter scaffold rather than
  installing placeholder macros and unowned version helper functions as target API.
- [x] Remove the no-op `CBasePlotter` source and tautological test because neither
  represented behavior owned by this repository.
- [x] Retain and move dependency-free `CLogger` runtime tests into `tests/core/`
  because the logger is compiled, installed target code.
- [x] Retain visualization, feature-track adaptation, annotation, matching,
  logging, and tracking-statistics tests under `tests/core/`; do not claim
  HighGUI display coverage that is not registered.
- [x] Keep future tests scoped to this repository's runtime/API behavior; validate
  inherited template infrastructure through real configure/build/install/docs/
  wrapper/structured-file entry points rather than copied conformance suites.

Applicable donor improvements adopted or adapted:

- [x] Expand target `AGENTS.md` with the complete applicable v1.11.3 authority,
  staged-review, documentation, Python, MATLAB, CUDA, continuity, and ROS-boundary
  guidance while preserving target naming and the persistent-plan convention.
- [x] Preserve the target's explicit OptiX, ZeroMQ, and spdlog removals.
- [x] Remove residual unused PTX-source discovery left after the target's OptiX
  embedding path was deleted.
- [x] Restore robust standalone container option validation and forward `DISPLAY`
  for OpenCV/Pangolin visualization processes.
- [x] Harden devcontainer JSON merge handling without adding the deferred ROS
  configuration layer.
- [x] Preserve unmanaged devcontainer build arguments during regeneration and
  report malformed existing JSON as a concise command error.
- [x] Restore Python wrapper-target existence detection in `build_lib.sh`.
- [x] Restore optional Python-version/interpreter fallback and actionable pytest
  diagnostics in `cmake/cmake_utils.cmake` without adding template Python tests.
- [x] Add and adapt `cmake/HandleDoxygenDocs.cmake`; include README, source, and
  public docs; exclude internal plans/reports/build trees; expose HTML/XML output
  directories for wrapper docstrings; keep namespaced docs targets.
- [x] Replace generic Markdown issue templates with target-specific structured
  forms and add the reusable pull-request review template.
- [x] Mark active CPU and CUDA workflows as materialized generic project CI,
  preserving their target ownership without importing donor workflow tests.
- [x] Add target-specific wrapper and documentation-workflow guides and update
  test/CI documentation with the corrected ownership boundary.
- [x] Update README dependency, documentation-map, and stable-v1.11.3 status text.

Intentional exclusions and deferrals:

- [x] Do not import donor `CONTEXT.md`, `CLAUDE.md`, development plans/reports,
  template usage/bootstrap documents, template placeholders, or tailoring script.
- [x] Do not restore donor OptiX, ZeroMQ, PTX embedding, or legacy spdlog surfaces.
- [x] Do not import donor `.vscode` files or overwrite the pre-existing user edit
  in `.vscode/c_cpp_properties.json`.
- [x] Do not import donor profiling wrapper scripts; the existing CMake profiling
  options remain sufficient for the target.
- [x] Defer `.devcontainer/ros-setup.sh`, donor ROS package quartet,
  `add_ros2_support.sh`, `build_ros2.sh`, ROS workflow, and PlotJuggler setup to
  Stages 3 and later.
- [x] Treat `doc/bootstrap_prompts.md` and `doc/template_usage.md` as source-only
  template bootstrap material; this repository is already an instantiated,
  heavily tailored project.

Cross-repository design gate:

- [x] Confirm root CMake now exports a required `slam-primitives` dependency and
  `CFeatureTrackSnapshotAdapter` consumes
  `slam_primitives::SFeatureTrackSnapshot`.
- [x] Confirm the owning header is currently untracked in
  `slam-primitives` on branch `perf/review-impl-best-practices`; no remote branch
  or release tag contains it yet.
- [x] Confirm the current CPU/CUDA workflows and standalone container do not
  provision `slam-primitives`, so they cannot honestly be called runnable against
  the current target graph.
- [ ] Consolidate and publish/commit the `slam-primitives` snapshot contract first.
- [ ] Select a remotely resolvable commit SHA or release tag for CI rather than a
  moving branch.
- [ ] Adapt all target build workflows to checkout/build/install that revision and
  export its prefix before configuring this repository.
- [ ] Materialize the v1.11.3 Pages workflow only after the same dependency setup
  is available; do not activate a knowingly failing workflow.
- [ ] Decide the devcontainer dependency acquisition contract after the owning
  revision exists: explicit bootstrap command, pinned source build, or approved
  workspace composition. Do not add an implicit unpinned `FetchContent` fallback.

Validation and handoff tasks:

- [x] Run `bash -n` and `shellcheck` on every changed shell script.
- [x] Parse all active JSON, YAML, XML, and TOML files with structured parsers.
- [x] Configure a clean CPU build against the reviewed local `slam-primitives`
  install, build, and run only the target-owned runtime tests.
- [x] Build strict Doxygen HTML/XML and inspect generated inputs/exclusions.
- [x] Install the clean CPU build and configure, build, and run the standalone
  external consumer against that installation and the reviewed local
  `slam-primitives` installation.
- [x] Confirm 44/44 target-owned runtime cases pass, both target examples run,
  and removed `config.h` scaffolding is absent from the install tree.
- [x] Do not rerun CUDA, wrapper, or container gates solely to test inherited
  `cpp_cuda_template_project` functionality. Their historical Stage 2 evidence
  remains recorded; future runs must be triggered by target-owned code or an
  affected integration surface.
- [x] Run `git diff --check`, conflict-marker, stale-template-identity,
  machine-local-path, generated-artifact, and executable-bit scans.
- [x] Remove generated alignment build trees, Python caches, documentation output,
  ROS logs created by this pass, and alignment-owned Docker images after evidence
  is recorded. Preserve user-owned/pre-existing build trees and images.
- [x] Confirm this pass created no Docker image; leave unrelated pre-existing
  template/testfield images untouched.
- [x] Leave the Git index empty while the required `slam-primitives` contract is
  not remotely resolvable; a full staged batch would be non-runnable, while a
  path-only partial batch would conceal overlapping root-CMake ownership.
- [ ] Stage one coherent consolidation batch, inspect `git diff --cached`, and
  hand it to the user with a proposed title and bullet description; do not commit.

Final defect-review hardening (2026-07-22):

- [x] Re-read target `AGENTS.md`, the stable v1.11.3 donor guidance, and this
  plan before the final review; keep the index empty and preserve the user-owned
  `.vscode/c_cpp_properties.json` change.
- [x] Review target-owned renderer/logger/adapter code and the isolated ROS
  benchmark processor rather than limiting the pass to template-file parity.
- [x] Reject zero expected path/observation sizes in the processor constructor,
  closing direct-call paths that could reach empty observation `back()` and
  empty trajectory rendering.
- [x] Require nonempty, matching image and feature-track frame IDs separately
  from the common trajectory-frame contract.
- [x] Add focused processor regressions for both invalid size configurations and
  the front-end frame mismatch; the Jazzy package now passes seven cases and 32
  assertions with `BUILD_SHARED_LIBS=ON`.
- [x] Correct README/testing documentation so it names only target-owned runtime
  tests and does not claim deleted CMake-policy or absent HighGUI tests.
- [x] Validate `ccache` explicitly on self-hosted CPU CI because the workflow
  configures it as the compiler launcher.
- [x] Add required file/public-API documentation to the new logger, snapshot
  adapter, and ROS benchmark sources; strict Doxygen HTML/XML remains green.
- [x] Reproduce and fix devcontainer regeneration changing Dockerfile and JSON
  modes to `0600`; scratch regeneration now preserves both original `0664`
  modes, while first-time JSON generation uses `0644`.
- [x] Confirm a clean standalone Ninja build/install passes 44/44 runtime cases,
  both target examples run, and the external installed-package consumer builds
  and runs against the clean prefix.
- [x] Confirm a clean Jazzy colcon build of `eval_and_viz_gears_ros` succeeds,
  its focused test passes, and the installed recorder help path runs when the
  already-documented standalone-library directory is added to `LD_LIBRARY_PATH`.
- [x] Keep CUDA, wrappers, and container image builds unrun: no target-owned CUDA
  runtime, wrapper API, or image behavior changed, and this derived repository
  must not recreate donor-template test coverage.
- [ ] Do not call the consolidation ready to stage until the owning
  `slam-primitives` snapshot/interface changes are committed and a remotely
  resolvable revision allows CPU/CUDA CI and Pages dependency provisioning.

Staged review findings (2026-07-24):

- [x] Stage the complete consolidation candidate only after the user's explicit
  request to begin staged review; keep `.vscode/c_cpp_properties.json` and the
  user-owned root `.code-workspace` file outside the index.
- [x] Restore the v1.11.3 root `*.code-workspace` ignore rule that was missed
  during semantic alignment, and exclude those files from CPack source archives;
  replace escape-sensitive dot regexes so a fresh `package_source` run completes
  without CPack developer warnings and omits the workspace file.
- [x] Declare the ROS bridge's direct `libopencv-dev` rosdep key so a clean
  `rosdep install --from-paths ros2` provisions the OpenCV development package.
- [x] Independently reproduce that the staged CPU/CUDA workflows and
  devcontainer cannot configure because no remotely resolvable
  `slam-primitives` revision contains the required snapshot API.
- [x] Independently reproduce that sourcing the current ROS install does not
  make the separately installed standalone shared library discoverable; the
  benchmark-specific `TIMING_ROS2_EVAL_LIB_DIR` override remains a workaround,
  not a complete installed-package contract.
- [ ] Before commit, either keep the ROS benchmark outside the first alignment
  batch or implement a relocatable colcon-owned runtime dependency contract.
- [ ] Before commit, publish and pin the owning `slam-primitives` snapshot and
  interface revision, then provision it in CPU/CUDA CI and the development
  container.

### Stage 2.11 - Signed v2.0.1 CMake, Wrapper, ROS, And Container Alignment

Approved scope (2026-08-17):

- [x] Verify the signed donor tag and use only committed v2.0.1 content.
- [x] Adopt qualified metadata/CUDA options, exact VERSION output, distinct
  source-package naming, append-only CPack exclusions, and QUIET-preserving
  exported dependency lookup.
- [x] Replace the source-mutating wrapper monolith with the v2.0.1 split modules
  and set the target MATLAB release to R2024b.
- [x] Add the `eval_and_viz_gears` colcon shim around the existing
  `eval_and_viz_gears_ros` bridge without importing donor example behavior.
- [x] Exclude ROS tests from source, package metadata, build helpers, and CI.
- [x] Pin `slam-primitives` revision
  `05a9c72be25692c965cf688511ac45107bfd382f` in CPU, CUDA, ROS, and container
  dependency setup.
- [x] Extend the devcontainer and standalone launcher with explicit ROS 2 Jazzy,
  CUDA, R2024b mount, Docker/Podman, and VS Code attachment paths.
- [x] Complete CPU, wrapper, package/consumer, ROS, documentation, container,
  structured-file, and staged-index validation; record exact evidence below.
- [x] Stage the full consolidation as one allowlisted batch without staging
  `.vscode`, committing, or pushing.

Validation evidence (2026-08-17):

- The clean CPU Ninja build installed successfully, both target examples ran,
  and CTest passed 44/44. Build-tree and install-tree consumer projects both
  configured, built, and ran against the exact pinned `slam-primitives`
  revision.
- CUDA 12.9 configured through the qualified project option, built, installed,
  and passed the same 44/44 CTest cases.
- Python wrapper generation built and imported the build-owned package and
  produced the versioned CPython 3.12 wheel with its runtime shared library.
  MATLAB wrapper generation used R2024b (24.2), built the MEX target under the
  prefix-relative `matlab/` layout, and the build-owned
  `gtwrap_include_bridge/wrap/matlab.h` matched the installed gtwrap header
  byte-for-byte. The MATLAB gate retained only upstream gtwrap deprecated-policy
  and generated/upstream-header compiler warnings; source status was unchanged.
- CPack produced distinct binary and `-source` archives. The source archive
  contained a five-line VERSION with one terminal newline, excluded Git,
  editor, build/install, ROS output, cache, and generated wrapper artifacts, and
  configured/built with zero registered tests after extraction without Git.
  Build-tree and install-tree package consumers passed, and a QUIET consumer
  observed a missing transitive dependency as package-not-found without a
  fatal/noisy dependency diagnostic.
- The Jazzy overlay built `eval_and_viz_gears` and
  `eval_and_viz_gears_ros` against pinned `slam-primitives`, registered zero
  tests, and ran the installed recorder help path. Metadata synchronization was
  idempotent on its second run.
- The ROS-enabled Docker image built successfully as
  `sha256:9df008390d92fc3afdfc604af14cda2b903113a5516bfe36bf39677213a32f92`.
  An in-container build from a read-only checkout mount again built both target
  packages, registered zero tests, and ran the recorder help path.
- Strict Doxygen HTML/XML generation passed with
  `DOC_WARN_AS_ERROR=ON`. Final shell syntax/ShellCheck, Python compilation,
  JSON/XML/YAML parsing, conflict-marker, feature-policy, machine-local-path,
  executable-mode, and `git diff --check` gates passed.

### Stage 3 - Devcontainer And Docker ROS 2 Setup

Objective:

Extend the validated standalone v1.11.3-derived devcontainer into a reproducible ROS 2 Jazzy visualization environment. Use the stable template overlay for build conventions and hyper_2 for ROS visualization/runtime packages, display forwarding, and networking patterns.

Tasks:

- [ ] Confirm the Stage 2 standalone devcontainer and host build gates are green before adding ROS packages.
- [ ] Re-open `v1.11.3` `doc/ros2_overlay.md`, `build_ros2.sh`, and ROS workflow templates as the pinned ROS build reference.
- [ ] Re-open hyper_2 Docker/devcontainer dependencies as the visualization-tool reference; do not copy its domain packages or robot-specific configuration.
- [ ] Extend the existing `.devcontainer/Dockerfile`, `.devcontainer/devcontainer.json`, and generator instead of replacing the standalone variants.
- [ ] Add/adapt `.devcontainer/ros-setup.sh` as an explicit ROS-enabled layer selected by configuration.
- [ ] Use ROS 2 Jazzy base image, following hyper_2 where appropriate.
- [ ] Install core ROS 2 build tooling:
  - [ ] `colcon`
  - [ ] `rosdep`
  - [ ] `ament_cmake`
  - [ ] `rosidl_default_generators`
  - [ ] `rclcpp`
  - [ ] `sensor_msgs`
  - [ ] `geometry_msgs`
  - [ ] `nav_msgs`
  - [ ] `visualization_msgs`
  - [ ] `diagnostic_msgs`
- [ ] Install visualization tools:
  - [ ] PlotJuggler
  - [ ] PlotJuggler ROS plugin
  - [ ] RViz
  - [ ] Foxglove bridge if available in the selected base.
  - [ ] rqt tools.
- [ ] Configure X11 display passthrough for local OpenCV/RViz/PlotJuggler.
- [ ] Configure host networking or documented ROS 2 discovery alternatives.
- [ ] Configure `ROS_DOMAIN_ID` through devcontainer environment.
- [ ] Keep DDS implementation and discovery settings configurable for local, host-network, and remote hosts.
- [ ] Keep unsupported dependencies absent from the image and setup scripts:
  - [ ] no OptiX SDK;
  - [ ] no ZeroMQ/libzmq/cppzmq;
  - [ ] no spdlog package or fetch path.
- [ ] Add README notes for GPU/X11/remote usage if needed.
- [ ] Keep MATLAB out of the container unless explicitly required.

Tests/checks:

- [ ] Devcontainer builds.
- [ ] `ros2 --help` works inside container.
- [ ] `plotjuggler --help` or equivalent binary check works.
- [ ] `rviz2 --help` works.
- [ ] `ros2 topic list` works in an empty sourced workspace.
- [ ] Existing standalone target build still works outside the ROS workspace.
- [ ] Stage 2 feature-policy tests still pass in the ROS-enabled container.
- [ ] Container package inventory contains no OptiX, ZeroMQ, or spdlog dependency introduced by project setup.

Exit criteria:

- [ ] A developer can open the repo in the devcontainer and build ROS packages.
- [ ] Visualization tools are available.
- [ ] Environment setup is documented.

### Stage 4 - ROS 2 Workspace And Interface Package

Objective:

Roll out and tailor the stable `v1.11.3` ROS 2 overlay where its package structure remains applicable, then replace generic example interfaces with the navigation visualization message definitions.

Tasks:

- [ ] Confirm no `ros2/` directory or `build_ros2.sh` exists before using the additive rollout helper.
- [ ] Run the donor helper in list mode from the pinned donor checkout:
  - [ ] `./add_ros2_support.sh --list --root /home/peterc/devDir/dev-tools/EvalAndVizGears_for_ComputerVision --ros-prefix eval_and_viz_gears --no-ci`;
  - [ ] inspect every proposed path and derived identity;
  - [ ] verify core CMake references remain `EvalAndVizGears_for_ComputerVision` while ROS package names use `eval_and_viz_gears`.
- [ ] Apply the additive overlay only after the list output is approved:
  - [ ] use explicit `--ros-prefix eval_and_viz_gears`;
  - [ ] use `--no-ci` so the target workflow is reviewed separately;
  - [ ] use `--verify` for the standalone configure guard;
  - [ ] verify no pre-existing target file was edited by the helper.
- [ ] Immediately tailor the copied overlay to the Stage 2 feature policy before its first ROS build:
  - [ ] remove `--optix` from `build_ros2.sh`;
  - [ ] remove all `EVAL_AND_VIZ_GEARS_ENABLE_OPTIX`/renamed template OptiX cache options from all four packages;
  - [ ] keep the supported CUDA facade only;
  - [ ] remove spdlog build/documentation assumptions;
  - [ ] verify no ZeroMQ transport appears;
  - [ ] update copied ROS docs so unsupported flags are not advertised.
- [ ] Preserve the four-package ownership split:
  - [ ] `ros2/eval_and_viz_gears` for the plain-CMake colcon shim;
  - [ ] `ros2/eval_and_viz_gears_interfaces` for messages/services;
  - [ ] `ros2/eval_and_viz_gears_ros` for conversions and ROS nodes/components;
  - [ ] `ros2/eval_and_viz_gears_spinup` for launch/config/layout assets.
- [ ] Keep `ros2/eval_and_viz_gears_ros/src/conversions.cpp` as the project API adaptation seam and keep algorithm logic out of the lifecycle node.
- [ ] Remove donor example contracts `AlgorithmStatus.msg` and `RunAlgorithm.srv` unless a concrete target use case is approved.
- [ ] Add custom messages from the message plan to `eval_and_viz_gears_interfaces`.
- [ ] Add dependency declarations for standard ROS messages.
- [ ] Adapt `ros2/tools/sync_package_metadata.py` and `generate_version.sh --sync-ros2` to the target's root metadata contract and ROS package quartet.
- [ ] Add the target-owned ROS workflow only after materializing and tailoring the donor generic `.yml.tpl` workflow; preserve target runner policy.
- [ ] Run `rosdep` if needed.
- [ ] Build only the interface package first.
- [ ] Update this document with final message names and any deviations.

Tests/checks:

- [ ] `bash -n build_ros2.sh` passes and its help contains no OptiX, ZeroMQ, or spdlog option.
- [ ] `colcon build --packages-select eval_and_viz_gears_interfaces`.
- [ ] `ros2 interface list | rg eval_and_viz`.
- [ ] `ros2 interface show eval_and_viz_gears_interfaces/msg/FeatureTrackArray`.
- [ ] Generated C++ headers are available.
- [ ] Generated Python modules are available.
- [ ] `./generate_version.sh --sync-ros2` updates all four package manifests atomically and preserves their package names.
- [ ] A repeated metadata synchronization is a no-op.
- [ ] Standalone `./build_lib.sh --clean` remains green after the overlay is added.
- [ ] The Stage 2 feature-policy guard is updated to allow the approved ROS paths while continuing to reject OptiX, ZeroMQ, and spdlog.

Exit criteria:

- [ ] Interface package builds cleanly.
- [ ] Message definitions are stable enough for MATLAB binding generation.

### Stage 5 - MATLAB ROS 2 Message Binding Smoke

Objective:

Validate MATLAB can publish standard and custom ROS 2 messages before algorithm wiring.

Tasks:

- [ ] Document MATLAB version and ROS 2 Toolbox availability.
- [ ] Document required ROS 2 environment variables.
- [ ] Generate MATLAB custom message support using `ros2genmsg` or the repository's chosen workflow.
- [ ] Add a minimal MATLAB smoke script in an appropriate target or bridge folder.
- [ ] Publish a standard `std_msgs/String`.
- [ ] Publish a standard `sensor_msgs/Image`.
- [ ] Publish a custom `VizFrameHeader`.
- [ ] Subscribe from `ros2 topic echo` or a tiny C++ listener.
- [ ] Document exact setup commands.

Tests/checks:

- [ ] MATLAB standard message publish works.
- [ ] MATLAB custom message publish works.
- [ ] `ros2 topic echo` sees custom message fields.
- [ ] Missing subscriber does not throw or block the MATLAB smoke script.
- [ ] Smoke script exits cleanly.

Exit criteria:

- [ ] MATLAB ROS 2 binding is proven in isolation.
- [ ] No algorithm code has been touched.

### Stage 6 - C++ Front-End Image Overlay Viewer Skeleton

Objective:

Create the first C++ ROS 2 viewer node and connect it to existing OpenCV rendering classes.

Tasks:

- [ ] Extend `ros2/eval_and_viz_gears_ros`; do not create a parallel visualization package.
- [ ] Add package dependencies for `rclcpp`, `sensor_msgs`, `cv_bridge` if used, OpenCV, and custom interfaces.
- [ ] Implement `frontend_overlay_viewer_node`.
- [ ] Subscribe to image topic.
- [ ] Convert ROS image to OpenCV matrix with explicit encoding handling.
- [ ] Use existing `CFrameAnnotator`, `CFeatureOverlayRenderer`, and `CTrackTrailRenderer` where possible.
- [ ] Add layer configuration flags.
- [ ] Add latest-frame state cache.
- [ ] Add missing-topic safe behavior.
- [ ] Add command-line or YAML config.

Tests/checks:

- [ ] `colcon build --packages-select eval_and_viz_gears_ros` builds the visualization package.
- [ ] Run node with no topics and confirm no crash.
- [ ] Publish synthetic image and display it.
- [ ] Confirm RGB/BGR test image colors are correct.
- [ ] Confirm grayscale image displays correctly.
- [ ] Confirm viewer exits cleanly.

Exit criteria:

- [ ] C++ viewer displays a ROS image without MATLAB.
- [ ] Existing target rendering code is reused or a reason is documented.

### Stage 7 - Synthetic Front-End Overlay Publisher

Objective:

Create a deterministic synthetic publisher to test centroids, features, tracks, and color mapping without MATLAB.

Tasks:

- [ ] Add a C++ or Python synthetic publisher under the visualization package.
- [ ] Publish dummy image at fixed resolution.
- [ ] Publish centroids.
- [ ] Publish extracted features.
- [ ] Publish tracks of different lengths.
- [ ] Publish tracks with bounded tails.
- [ ] Publish optional missing fields.
- [ ] Add launch file for synthetic demo.

Tests/checks:

- [ ] Synthetic demo starts with one command.
- [ ] Viewer renders image at native resolution.
- [ ] Centroid layer appears.
- [ ] Feature layer appears.
- [ ] Track layer appears.
- [ ] Track colors vary by track length.
- [ ] Layer toggles work.
- [ ] Viewer handles zero centroids/features/tracks.

Exit criteria:

- [ ] Front-end overlay renderer is validated without MATLAB dependency.

### Stage 8 - MATLAB Front-End Packet Construction

Objective:

Create MATLAB-side packet construction functions without changing algorithm outputs.

Candidate location:

- root source repo: `/home/peterc/devDir/nav-frontend`
- or nav-system adapter layer if ownership should stay out of nav-frontend.

Tasks:

- [ ] Identify exact fields from `RunFrontEnd.m`, `RunFrontEnd_KLT.m`, and track builder outputs needed for messages.
- [ ] Add packet construction function for image metadata.
- [ ] Add packet construction function for centroids.
- [ ] Add packet construction function for extracted features.
- [ ] Add packet construction function for feature tracks.
- [ ] Add configurable track-tail length.
- [ ] Ensure empty outputs produce valid empty messages.
- [ ] Do not call plotting functions from packet construction.
- [ ] Do not mutate front-end outputs.
- [ ] Add MATLAB unit tests with synthetic front-end structures.

Tests/checks:

- [ ] Packet construction from synthetic KLT output.
- [ ] Packet construction from centroid-only output.
- [ ] Packet construction with no features.
- [ ] Packet construction with long tracks and tail truncation.
- [ ] Packet construction preserves image dimensions and color metadata.
- [ ] Tests run in nav-frontend root checkout.

Exit criteria:

- [ ] MATLAB can construct front-end visualization messages from existing data structures.
- [ ] No ROS 2 publish side effects are required for the packet tests.

### Stage 9 - MATLAB Front-End ROS Publisher

Objective:

Publish front-end visualization packets from MATLAB through ROS 2 with low overhead.

Candidate location:

- nav-system should own lifecycle and enable/disable configuration.
- nav-frontend may expose packet construction only.

Tasks:

- [ ] Add publisher lifecycle object or struct.
- [ ] Initialize ROS 2 node only when publishing is enabled.
- [ ] Create publishers for image, metadata, centroids, features, and tracks.
- [ ] Publish only at configured visualization refresh cadence.
- [ ] Publish image only when enabled.
- [ ] Publish overlay topics independently from image when configured.
- [ ] Catch publisher errors and disable publishing safely if ROS 2 is unavailable.
- [ ] Track serialization/publish timing with optional profiling.
- [ ] Do not block simulation if no subscribers exist.
- [ ] Preserve current MATLAB plotting flags.

Tests/checks:

- [ ] Publisher disabled path has near-zero overhead in a smoke test.
- [ ] Publisher enabled with no subscriber does not throw.
- [ ] Publisher enabled with synthetic subscriber sends messages.
- [ ] Publish timing is recorded when profiling is enabled.
- [ ] Existing front-end tests still pass.

Exit criteria:

- [ ] MATLAB publishes front-end visualization messages in isolation.
- [ ] Viewer can render MATLAB-published synthetic or recorded front-end data.

### Stage 10 - nav-system Integration

Objective:

Wire ROS 2 visualization publishing into nav-system without changing algorithm behavior.

Tasks:

- [ ] Add visualization config fields to `SetupOptions_COSMICAsys.m`.
- [ ] Add YAML loading support in `LoadNavSystemConfigFromYaml.m`.
- [ ] Add publisher initialization at simulation setup time.
- [ ] Add front-end publish hook after `RunFrontEnd`.
- [ ] Add backend/perf-monitor publish hook after estimator update.
- [ ] Ensure Monte Carlo mode defaults remain non-visual.
- [ ] Ensure existing save/export flags do not accidentally enable online ROS rendering.
- [ ] Ensure ROS publish does not require MATLAB figure handles.
- [ ] Document exact flags to enable/disable publishing.

Tests/checks:

- [ ] Existing nav-system config tests pass.
- [ ] ROS publishing disabled preserves current behavior.
- [ ] MATLAB plotting enabled without ROS still works.
- [ ] ROS enabled without MATLAB plotting works.
- [ ] Missing ROS environment disables or reports publishing cleanly.

Exit criteria:

- [ ] nav-system can run with ROS 2 publish enabled and MATLAB plotting disabled.

### Stage 11 - Backend Error And Covariance Data Formalization

Objective:

Separate scalar error/covariance data extraction from MATLAB plotting routines and prepare PlotJuggler streams.

Source functions:

- `/home/peterc/devDir/nav-backend/matlab/utils/PlotEstimationErrorsFromPerfMonitor.m`
- `/home/peterc/devDir/nav-backend/matlab/utils/PlotSimCoreRunFromPerfMonitor.m`
- current online visualization utility functions in nav-backend root.

Tasks:

- [ ] Identify raw values currently plotted for position error.
- [ ] Identify raw values currently plotted for velocity error.
- [ ] Identify raw values currently plotted for additional state errors.
- [ ] Identify covariance and empirical covariance values.
- [ ] Identify current focus-window and y-limit computations.
- [ ] Create data extraction functions that return numeric series and metadata without drawing.
- [ ] Preserve existing plotting routines by letting them optionally consume the same extracted data.
- [ ] Add publish adapter for scalar topics.
- [ ] Add optional publish timing metrics.
- [ ] Avoid publishing display-only y-limits as algorithmic outputs unless useful as debug topics.

Tests/checks:

- [ ] Unit tests compare extracted values against existing plot input values.
- [ ] Empty or partial perf-monitor fields are handled.
- [ ] Additional state lists of different sizes are handled.
- [ ] Existing MATLAB error plots still render.
- [ ] PlotJuggler receives synthetic scalar topics.

Exit criteria:

- [ ] Error/covariance data can be published without creating MATLAB figures.

### Stage 12 - PlotJuggler Layouts

Objective:

Install and configure PlotJuggler layouts for current online MATLAB scalar plots.

Tasks:

- [ ] Create `plotjuggler/estimation_errors.xml`.
- [ ] Create `plotjuggler/covariance.xml`.
- [ ] Create `plotjuggler/additional_states.xml`.
- [ ] Create `plotjuggler/frontend_tracks.xml`.
- [ ] Create `plotjuggler/performance.xml`.
- [ ] Map topic names to current MATLAB plot groups.
- [ ] Add launch/config instructions.
- [ ] Document how to load each layout.
- [ ] Document optional/missing topics.

Tests/checks:

- [ ] PlotJuggler opens each XML.
- [ ] Synthetic scalar publisher populates curves.
- [ ] MATLAB publisher populates curves.
- [ ] Missing optional topics do not prevent layout loading.
- [ ] Topic naming matches this document.

Exit criteria:

- [ ] PlotJuggler provides replacement dashboards for online MATLAB error/covariance plots.

### Stage 13 - 3D State, Trajectory, ROI, And Covariance Marker Path

Objective:

Move 3D online visualization out of MATLAB plotting and into ROS 2/RViz-compatible markers.

Source functions:

- `/home/peterc/devDir/nav-backend/matlab/utils/VisualizeEstimationStateWith3dScene.m`
- `/home/peterc/devDir/nav-backend/matlab/utils/Plot3dEstimatedTrajectories.m`
- `/home/peterc/devDir/nav-backend/matlab/utils/PlotOnlineLatLonRoiCoverageMap.m`

Tasks:

- [ ] Identify coordinate frames currently used by MATLAB 3D plots.
- [ ] Identify target-fixed frame conventions.
- [ ] Identify reference, estimated, smoothed, and GTSAM trajectory sources.
- [ ] Identify map point and landmark sources.
- [ ] Identify ROI/lat-lon conversion ownership.
- [ ] Define frame ids for ROS 2:
  - [ ] world/inertial frame;
  - [ ] target-fixed frame;
  - [ ] camera/body frame;
  - [ ] image frame if needed.
- [ ] Add MATLAB packet construction for state estimate.
- [ ] Add MATLAB packet construction for trajectories.
- [ ] Add MATLAB packet construction for landmarks/map points.
- [ ] Add MATLAB packet construction for covariance ellipsoid requests.
- [ ] Add MATLAB packet construction for ROI regions.
- [ ] Implement C++ marker node.
- [ ] Generate trajectory line strip markers.
- [ ] Generate landmark markers.
- [ ] Generate covariance ellipsoid markers from covariance matrices.
- [ ] Generate ROI boundary markers.
- [ ] Add stale marker deletion logic.
- [ ] Add RViz config file.

Tests/checks:

- [ ] Synthetic 3D publisher renders known trajectory.
- [ ] Synthetic covariance ellipsoid has expected axis lengths.
- [ ] Marker node handles empty arrays.
- [ ] Marker node rejects malformed covariance safely.
- [ ] MATLAB-published state appears in RViz.
- [ ] Visual comparison against existing MATLAB 3D scene for a short scenario.

Exit criteria:

- [ ] RViz/Foxglove path covers the main 3D MATLAB online visualization categories.

### Stage 14 - COSMICA Simulation Hook And Profiling

Objective:

Enable the new ROS visualization path from the COSMICA simulation core and measure timing.

Tasks:

- [ ] Add or extend COSMICA visualization options in `ResolveCosmicaRunnerVisualizationOptions.m`.
- [ ] Add new ROS 2 visualization runner options to `input/LoadCosmicaRunConfigFromYaml.m` allowed fields before adding them to YAML.
- [ ] Add tests proving unknown legacy options still fail and new ROS 2 options load.
- [ ] Add simulation-level flags for ROS 2 publish.
- [ ] Add refresh cadence control.
- [ ] Replace the hard-coded online backend cadence `dPlotDeltaNumOfKeyframes = 5` with a resolved runner option while preserving the current default.
- [ ] Keep `bEnableLiveVisualization`, `bSaveBackend3dVisualization`, and ROS publishing as separate modes:
  - [ ] MATLAB live figures;
  - [ ] MATLAB export-only hidden figures;
  - [ ] ROS publish-only online visualization;
  - [ ] ROS recording/export without live viewer.
- [ ] Preserve Monte Carlo default behavior that disables visualization/export unless a new explicit MC diagnostics override is added.
- [ ] Publish COSMICA run context at setup time:
  - [ ] trial name;
  - [ ] trial id;
  - [ ] run config path;
  - [ ] nav-system config path;
  - [ ] backend config path;
  - [ ] GUI config path;
  - [ ] Monte Carlo flag.
- [ ] Add setup-time publish/export replacement path for approach preplanned trajectory summary:
  - [ ] trajectory arc;
  - [ ] insertion and shaping manoeuvre markers;
  - [ ] target shell limits;
  - [ ] range history;
  - [ ] speed history;
  - [ ] phase-angle history;
  - [ ] apparent-diameter or radial-speed history.
- [ ] Decide whether `SaveApproachPreplannedTrajectoryFigures` remains export-only in Stage 14 or gains a ROS publish path.
- [ ] Add COSMICA guidance adapter for GUI-system data:
  - [ ] goal-definition map;
  - [ ] visited/remaining goal status;
  - [ ] guidance planned trajectory;
  - [ ] manoeuvre times;
  - [ ] Delta-V vectors and norms.
- [ ] Keep GUI-system plotting functions as fallback:
  - [ ] `PlotGoalDefinitionMap`;
  - [ ] `CheckGoalStatus`;
  - [ ] `plotGuidanceSolution`;
  - [ ] `PlotHandleGroup`.
- [ ] Avoid making COSMICA depend directly on target-repo C++ code; the dependency should be ROS 2 messages and MATLAB publisher adapters only.
- [ ] Decide whether the legacy caller-workspace `scripts/utils/MakeEvaluationPlots.m` is retired, ignored, or kept in sync with `MakeEvaluationPlotsFcn.m`.
- [ ] Add profiling around algorithm/front-end computation.
- [ ] Add profiling around existing MATLAB plotting path.
- [ ] Add separate profiling around backend 3D export-only path.
- [ ] Add separate profiling around guidance debug export path.
- [ ] Add separate profiling around approach preplan figure export path.
- [ ] Add profiling around MATLAB ROS serialization/publish.
- [ ] Add optional viewer render timing topic.
- [ ] Ensure no noisy logging unless profiling is enabled.
- [ ] Run short scenario with plotting disabled.
- [ ] Run short scenario with existing MATLAB plotting enabled.
- [ ] Run short scenario with existing MATLAB export-only backend 3D enabled.
- [ ] Run short scenario with guidance debug export enabled.
- [ ] Run setup-only scenario with approach preplan summary enabled.
- [ ] Run short scenario with ROS publishing enabled and no viewers.
- [ ] Run short scenario with ROS publishing enabled and viewers running.

Tests/checks:

- [ ] `tests/testCosmicaRunConfigYaml.m` covers new ROS 2 runner options and preserves strict unknown-option rejection.
- [ ] `tests/testSimulatorInterfaceContractsAndDefaults.m` covers default-off behavior and Monte Carlo gating for new ROS publish/export flags.
- [ ] A setup-only smoke confirms COSMICA can publish run context and approach preplan summary without calling MATLAB plotting.
- [ ] A guidance-adapter unit test maps minimal GUI-system guidance data to ROS packet structs without figures.
- [ ] Simulation results are unchanged when visualization mode changes.
- [ ] Publishing disabled path matches baseline timing within noise.
- [ ] ROS publish with no subscribers does not block significantly.
- [ ] ROS publish with slow viewer drops frames or uses latest-frame behavior.
- [ ] MATLAB plotting remains available.
- [ ] Existing manual-run defaults in `input/run_configs/cosmica_manual_approach.yml` remain intentional or are explicitly changed with tests.

Exit criteria:

- [ ] Timing comparison is documented.
- [ ] The new path demonstrates lower simulation-thread visualization cost than direct MATLAB plotting, or limitations are explicitly reported.
- [ ] COSMICA-specific guidance, preplan, and run-context visualization gaps are either implemented or explicitly deferred.

### Stage 15 - Remote Visualization And Recording

Objective:

Support remote operation and later offline replay.

Tasks:

- [ ] Document local host-network setup.
- [ ] Document remote ROS 2 discovery assumptions.
- [ ] Document `ROS_DOMAIN_ID` usage.
- [ ] Add optional Foxglove bridge launch.
- [ ] Add rosbag2 recording instructions for visualization topics.
- [ ] Add replay instructions for front-end overlay viewer.
- [ ] Add bandwidth notes for raw vs compressed images.
- [ ] Add optional compressed image publishing plan.

Tests/checks:

- [ ] Viewer on same host receives topics.
- [ ] Viewer in devcontainer receives host MATLAB topics.
- [ ] Remote host test if environment is available.
- [ ] rosbag2 records selected topics.
- [ ] rosbag2 replay drives viewer and PlotJuggler.

Exit criteria:

- [ ] Local and remote visualization workflows are documented and tested where available.

### Stage 16 - Compatibility And Regression Tests

Objective:

Ensure algorithm behavior is unchanged and visualization code remains maintainable.

Tasks:

- [ ] Add C++ unit tests for message conversion into renderer data structures.
- [ ] Add C++ unit tests for track color mapping.
- [ ] Add C++ unit tests for tail truncation.
- [ ] Add C++ unit tests for image encoding conversion.
- [ ] Add C++ unit tests for covariance ellipsoid geometry.
- [ ] Add MATLAB tests for packet construction.
- [ ] Add MATLAB tests for disabled publisher overhead path.
- [ ] Add integration smoke test with synthetic publishers and viewers.
- [ ] Add CI-compatible tests that do not require GUI.
- [ ] Add optional manual GUI tests for OpenCV/RViz/PlotJuggler.

Tests/checks:

- [ ] `colcon test` passes for ROS packages.
- [ ] Existing target CTest passes.
- [ ] nav-frontend MATLAB tests pass.
- [ ] nav-backend MATLAB tests pass for affected utilities.
- [ ] nav-system config tests pass.
- [ ] GUI manual checklist passes when a display is available.

Exit criteria:

- [ ] Automated tests cover message conversion, packet construction, and non-GUI logic.
- [ ] Manual tests cover actual rendering.

### Stage 17 - Documentation And User Workflow

Objective:

Make the system usable by another developer.

Tasks:

- [ ] Update this document with actual implemented files and final status.
- [ ] Add target repo README section for ROS 2 visualization.
- [ ] Add MATLAB setup instructions.
- [ ] Add Docker/devcontainer instructions.
- [ ] Add viewer launch instructions.
- [ ] Add PlotJuggler layout loading instructions.
- [ ] Add RViz launch instructions.
- [ ] Add troubleshooting section:
  - [ ] missing MATLAB custom messages;
  - [ ] wrong ROS domain;
  - [ ] no subscribers;
  - [ ] wrong image colors;
  - [ ] X11/RViz display failure;
  - [ ] slow image publish;
  - [ ] missing optional topics.
- [ ] Add architecture diagram or ASCII flow.

Tests/checks:

- [ ] Follow docs from a clean shell.
- [ ] All commands are copy/paste executable after path adjustment.
- [ ] Documented paths use root repos under `/home/peterc/devDir`.

Exit criteria:

- [ ] Docs are sufficient to run the prototype without reading source code.

### Stage 18 - Cleanup, Review, And Migration Decision

Objective:

Decide how much MATLAB plotting can be retired or left as fallback.

Tasks:

- [ ] Compare MATLAB plot output and ROS viewer output for representative scenarios.
- [ ] Compare timing across disabled, MATLAB-plotting, and ROS-publishing modes.
- [ ] Identify any MATLAB plots not yet represented externally.
- [ ] Decide which MATLAB plotting hooks remain primary fallback.
- [ ] Disable or de-emphasize expensive MATLAB plotting by default if validated.
- [ ] Remove dead prototype code.
- [ ] Keep implementation minimal and avoid unused helper layers.
- [ ] Update remaining work section.

Tests/checks:

- [ ] Representative scenario visual correctness checklist.
- [ ] Timing table included in this document.
- [ ] Existing algorithm outputs unchanged.
- [ ] No broken fallback MATLAB plotting path.

Exit criteria:

- [ ] The external online visualization path is ready for normal development use.

## Initial Implementation Order Recommendation

- [ ] Stage 1: freeze baselines.
- [x] Stage 2: semantically align the standalone target through stable `cpp_cuda_template_project` `v1.11.3`, remove OptiX/ZeroMQ/spdlog, and keep all standalone gates green.
- [ ] Stage 3: only after Stage 2 approval, extend the generic Docker/devcontainer setup with ROS 2 Jazzy and visualization tools.
- [ ] Stage 4: evaluate and tailor applicable `v1.11.3` ROS overlay facilities without forcing the donor's four-package shape, then replace generic example interfaces with visualization interfaces.
- [ ] Stage 5: validate MATLAB ROS 2 custom message publishing.
- [ ] Stage 6: build C++ OpenCV image viewer.
- [ ] Stage 7: validate with synthetic publisher.
- [ ] Stage 8: add MATLAB packet construction in nav-frontend/nav-system.
- [ ] Stage 9: add MATLAB front-end publisher.
- [ ] Stage 10: wire nav-system.
- [ ] Stage 11: formalize backend scalar plot data.
- [ ] Stage 12: add PlotJuggler layouts.
- [ ] Stage 13: add RViz marker path.
- [ ] Stage 14: integrate COSMICA and profile.

Rationale:

- Finish and review standalone template alignment before introducing ROS package or container dependencies.
- Prove environment and interfaces before touching algorithms.
- Prove renderer without MATLAB before MATLAB integration.
- Prove MATLAB publish without algorithm wiring before simulation integration.
- Move image overlay first because it is the most direct replacement for expensive per-frame MATLAB plotting.
- Move scalar errors/covariance to PlotJuggler after message and publisher plumbing is stable.
- Move 3D visualization after coordinate-frame contracts are explicit.

## Profiling Plan

Minimum timing groups:

- [ ] Simulation/front-end computation with all plotting and ROS publishing disabled.
- [ ] Existing MATLAB image/track/centroid plotting path.
- [ ] Existing MATLAB 3D scene plotting path.
- [ ] Existing MATLAB error/covariance plotting path.
- [ ] MATLAB packet construction time.
- [ ] MATLAB ROS publish time.
- [ ] C++ viewer receive-to-render time.
- [ ] PlotJuggler scalar publish/update observable behavior.
- [ ] RViz marker publish/update time.

Profiling tools:

- [ ] MATLAB `tic/toc` around selected hooks.
- [ ] MATLAB profiler for deeper investigation only when needed.
- [ ] C++ steady-clock timing around callback and render.
- [ ] ROS 2 topic statistics if enabled.
- [ ] Optional diagnostic topics for timing.

Rules:

- [ ] Timing logs must be disabled by default.
- [ ] Timing instrumentation must not create figure handles.
- [ ] Timing instrumentation must not alter algorithm outputs.
- [ ] Publish overhead must be measured with and without active subscribers.

## Acceptance Criteria

- [ ] Written development document exists under the target repo documentation area.
- [ ] Root repos under `/home/peterc/devDir` are used as implementation references.
- [x] The standalone target is semantically aligned through stable donor tag `v1.11.3` at `f3fd6555` while the isolated ROS package remains outside root CMake dependencies.
- [ ] OptiX, ZeroMQ, and spdlog are absent from active source, build, package-export, documentation, CI, and container surfaces.
- [ ] Dependency-free `viztools::logging::CLogger` replaces the legacy spdlog adapter and has focused tests.
- [ ] Current MATLAB plotting paths and hook points are identified.
- [ ] PlotJuggler is evaluated as part of a larger ROS 2 visualization architecture, not assumed to be sufficient alone.
- [ ] ROS 2 message interface is defined and buildable.
- [ ] MATLAB can publish standard and custom ROS 2 messages.
- [ ] C++ viewer can display image, centroids, features, and tracks.
- [ ] Track colors depend on track length.
- [ ] Arbitrary track count is supported.
- [ ] 3D quantities are available through RViz/Foxglove-compatible markers.
- [ ] Errors and covariance are available through PlotJuggler-compatible scalar topics.
- [ ] Missing viewer/subscriber does not block or crash MATLAB.
- [ ] Existing MATLAB plotting remains available as fallback.
- [ ] Tests exist at every implementation stage.
- [ ] Timing comparison is documented.
- [ ] Algorithm behavior is unchanged.

## Open Questions For Iteration

- [ ] Should MATLAB publish standard messages plus several custom overlay messages, or one aggregate front-end frame packet?
- [ ] Which exact MATLAB version and ROS 2 Toolbox version should be the supported baseline?
- [ ] Should raw images be published first, with compressed images as a later remote mode?
- [ ] Should track histories be sent as bounded tails every refresh or as incremental updates?
- [ ] Should ROI/lat-lon conversion stay MATLAB-only in the first implementation?
- [ ] Should covariance ellipsoid confidence scale match the existing MATLAB plotting convention exactly or be configurable?
- [ ] Should PlotJuggler topics be split scalar topics or generic named scalar messages?

## Current Conflict Report

No blocking design conflict was found during Stage 0.

Historical high-risk gates and current disposition:

- [x] Target repo had dirty template-derived files; Stage 2 preserved the pre-existing `.vscode/c_cpp_properties.json` edit and did not commit or revert user work.
- [x] Stable source template baseline advanced from `v1.11.1` at `ed11d83` to `v1.11.3` at `f3fd6555`; the latest donor checkout was clean and only tagged content was admitted.
- [x] The donor delta overlapped seven dirty target paths; the alignment used semantic merges and preserved target identity and user-owned changes.
- [x] The stable donor retained transitional spdlog compatibility and OptiX support; both were removed as explicit target tailoring and are enforced by a policy test.
- [x] The target's ZeroMQ module was removed and guarded against reintroduction.
- [x] The target had no committed devcontainer despite configuration scripts expecting one; Stage 2 added and validated the standalone container assets while deferring the ROS layer.
- [ ] nav-backend and nav-frontend root repos have uncommitted and untracked plotting/API work that must be included in the design.
- [ ] nav-system may reference nested backend content; runtime path ownership must be verified.
- [ ] COSMICA root path must be `/home/peterc/devDir/projects-DART/cosmica-simulator`; stale `/home/peterc/devDir/projects/cosmica-simulator` references are invalid in this workspace.
- [ ] COSMICA strict runner-option validation requires YAML-loader and test updates before new ROS 2 flags can be used.
- [ ] COSMICA guidance visualization depends on `gui-system` plotting/data contracts and is separate from nav-backend plotting.
- [ ] COSMICA approach-preplan and MC sample figure exports are setup/offline visualization surfaces, not nav-system online frame outputs.
- [ ] MATLAB custom ROS 2 message generation must be proven before algorithm integration.
- [ ] PlotJuggler cannot replace image overlays or 3D visualization by itself.

## Stage 0 Final Notes

The recommended path is a ROS 2 based visualization layer with multiple consumers:

- C++ OpenCV node for image/centroid/feature/track overlays.
- RViz/Foxglove-compatible marker node for 3D estimates, trajectories, landmarks, ROI, and covariance ellipsoids.
- PlotJuggler layouts for errors, covariance, residuals, additional states, counters, and timing.
- MATLAB publishes compact semantic data and remains the algorithm owner.

The plan should be iterated before implementation begins, especially around:

- repository layout;
- message granularity;
- MATLAB ROS 2 message generation workflow;
- Stage 2 implementation evidence after the completed `v1.11.3` semantic alignment;
- exact plot-topic mapping from nav-backend and nav-frontend current dirty implementations.

## MATLAB ROS 2 Interface Timing Benchmark - Approved Execution Plan

This benchmark is the first evidence-producing slice of the broader ROS 2
visualization roadmap. It does not replace the production publisher wiring.
It establishes the semantic interfaces, measures MATLAB-side cost, and proves
that the messages can be rendered after passing through ROS 2.

Binding decisions:

- MATLAB R2024b and ROS 2 Jazzy are the target runtime pair.
- The standalone entry point is
  `/home/peterc/devDir/nav-backend/matlab/tests/timing_ros2_interfaces.m`.
- `slam-primitives` owns the ROS-neutral feature-track snapshot and its ROS 2
  interface package. No `pyramidal_klt_interfaces/TrackerStepResult`
  dependency is permitted.
- `EvalAndVizGears_for_ComputerVision` depends on the exported header-only
  `slam-primitives` package and owns rendering plus ROS adaptation.
- `sensor_msgs/Image` carries the `mono8` image.
- `nav_msgs/Path` carries real camera poses. Three topics distinguish
  reference, online estimate, and smoothed trajectories.
- Each path pose represents `T_reference_from_camera`; its position and
  normalized quaternion come from real or deterministic synthetic pose data.
  Identity orientation must not be inserted merely to satisfy the message.
- The timed feature payload contains one track with exactly three
  chronological image observations.
- MATLAB is the manual test entry point. It launches the C++ recorder for the
  ROS round-trip mode; the benchmark is not an automatic CTest/CI job.
- Generated results and reviewable visualizations live below the ignored
  `output_data/timing_ros2_interfaces/<run-id>/` tree.

### Benchmark Stage 0 - Baseline And Runtime Gate

- [x] Record branches, HEADs, and dirty status for Eval-and-Viz,
  `slam-primitives`, and `nav-backend` before editing.
- [x] Confirm the existing Eval-and-Viz standalone alignment is green before
  adding ROS content: 52/52 tests passed on 2026-07-22.
- [x] Confirm the current `slam-primitives` baseline is green: 68/68 tests
  passed on 2026-07-22.
- [x] Confirm MATLAB R2024b starts with ROS Toolbox while the Jazzy environment
  is sourced and constructs `nav_msgs/Path`.
- [x] Add the ignored `output_data/` result root.

### Benchmark Stage 1 - Shared Feature-Track Primitive

- [x] Add ROS-independent observation and track-snapshot value types under
  `slam-primitives`, using the existing `FrameID`, `SFeatureLocation2D`, and
  feature-set identifier contracts.
- [x] Add a direct conversion from
  `CFeatureTrack<SFeatureLocation2D, MAX_LENGTH>` that preserves chronological
  observation order, track ID, and termination state.
- [x] Add focused Catch2 coverage and a self-contained public-header compile
  check.

Implementation evidence (2026-07-22): the conversion and four focused cases
pass in a fresh C++20 build; the complete `slam-primitives` suite is 72/72.

### Benchmark Stage 2 - Shared ROS 2 Interfaces

- [x] Add `ros2/slam_primitives_interfaces` in the `slam-primitives`
  repository.
- [x] Define `FeatureObservation2D`, `FeatureTrack2D`, and
  `FeatureTrackArray` messages using only `std_msgs` plus primitive ROS field
  types.
- [x] Build with colcon on Jazzy and generate MATLAB bindings with R2024b
  `ros2genmsg`.
- [x] Prove MATLAB constructs and populates all three generated message types.

Implementation evidence (2026-07-22): a fresh Jazzy build installed the
interface-only package, `ros2 interface show` matched all approved fields, and
fresh R2024b generation constructed one track with three chronological
observations. Generated bindings remained below `/tmp`.

### Benchmark Stage 3 - Eval-And-Viz Adapter And Recorder

- [x] Add `slam-primitives` as an exported dependency of the standalone
  Eval-and-Viz library.
- [x] Add a tested adapter that converts chronological snapshots to the
  existing renderer's newest-first trail contract at the rendering boundary.
- [x] Add an optional ROS 2 package and recorder executable that subscribe to
  the benchmark image, track, and three trajectory topics.
- [x] Validate image dimensions/encoding, observation order, track ID,
  timestamps, reference frames, path lengths, and quaternion normalization.
- [x] Write a readiness marker, annotated image, three-path visualization, and
  structured receipt into a caller-provided output directory; exit after one
  complete deterministic bundle.

Implementation evidence (Task 3a, 2026-07-22):

- [x] `CFeatureTrackSnapshotAdapter` preserves the ROS-free standalone target,
  accepts the chronological `slam_primitives::SFeatureTrackSnapshot`, explicitly
  converts `double` pixel coordinates to `cv::Point2f`, and reverses only the
  rendering-boundary copy.
- [x] Fresh CPU configuration used
  `CMAKE_PREFIX_PATH=/tmp/codex-sdd-019f895c/slam-primitives-install`; focused
  adapter coverage passed 3/3 and the complete suite passed 55/55, including
  build-tree, install-tree, and nested package consumers without a package
  registry.
- [x] Installed the validated standalone package to
  `/tmp/codex-sdd-019f895c/eval-and-viz-task-3a-install` for the next task.

Implementation evidence (Task 3b, 2026-07-22):

- [x] Added the isolated `ros2/eval_and_viz_gears_ros` ament package with the
  five reliable benchmark subscriptions, deterministic completeness gate,
  validation, atomic readiness/receipt files, and the installed
  `timing_ros2_interfaces_recorder` executable. The standalone root CMake target
  was not given a ROS dependency.
- [x] The required RED build reached the focused Catch2 source and failed on the
  missing `eval_and_viz_gears_ros/CBenchmarkBundleProcessor.h`; after the minimal
  implementation, a fresh Jazzy colcon build completed and all five processor
  cases passed. The review-hardened final suite passes 27 assertions, including
  rejection of a track ID that differs from the configured default ID 17.
- [x] The artifact case produced a 1024-by-1024 annotated image with the three
  chronological observations and trail plus a labeled 1500-by-560 XY/XZ/YZ
  three-path image with quaternion-derived orientation cues. The JSON receipt
  passed structured field/count validation. The final artifact test requires a
  unique nonexistent temporary directory, proves callback-to-artifact time
  starts at entry of the callback that completes the bundle, includes processor
  entry through successful PNG completion, keeps render time separate, and
  removes the directory after inspection. The obsolete first-warm-up callback
  state was removed so MATLAB warm-up and plotting time are excluded.
- [x] Added the `expected_track_id` recorder parameter and processor contract,
  defaulting to 17. Node construction rejects values outside the ROS message's
  `uint32` range, while focused Catch2 coverage rejects a complete bundle with
  the wrong single track ID.
- [x] Transitioned the Stage 2 derived-feature policy narrowly for Stage 3: only
  `ros2/eval_and_viz_gears_ros` plus the tightly constrained `ros2/tools`
  directory are allowed below `ros2/`; the latter permits only
  `sync_package_metadata.py`. The root ROS build helpers remain forbidden, and
  root CMake/modules plus `src` are scanned for ROS dependency identifiers. The
  single focused gate self-tests the approved children, an unapproved sibling,
  and direct `builtin_interfaces`, `rosbag2_cpp`, `rmw`, `rcutils`, and core
  `rcl` CMake/include leaks. The fresh standalone CPU suite passed 56/56 with
  the validated `slam-primitives` prefix.
- [x] Declared the package-internal bundle processor `STATIC`; a review RED
  reproduced the missing shared-library failure with `BUILD_SHARED_LIBS=ON`,
  while the final ON build linked a static archive, passed all five ROS tests
  with 27 assertions, and resolved `ros2 run ... --help` with exit code zero.

### Benchmark Stage 4 - Standalone MATLAB Timing Script

- [x] Implement `matlab/tests/timing_ros2_interfaces.m` as a script with only
  file-local helper functions and no nav-backend plotting dependencies.
- [x] Default to a 1024-by-1024 `mono8` image, one three-point feature trail,
  three growing 200-pose camera paths, 20 warm-up iterations, and 200 measured
  iterations.
- [x] Measure message construction, ROS send with an active recorder, figure
  and graphics-object creation, full replot with `drawnow`, graphics-handle
  update with `drawnow`, and `drawnow limitrate` as separate workloads.
- [x] Report mean, median, p95, standard deviation, and speed ratios without
  mixing MATLAB publisher time with C++ callback/render time.
- [x] Save CSV, JSON, and MAT results below the configured run directory.
- [x] Use cleanup guards for figures, ROS nodes, and the launched recorder.

Implementation evidence (2026-07-22): R2024b reports zero Code Analyzer
findings and zero parse errors. A function-scoped script driver owns the ROS
node and recorder process group; individual guards cover persistent and
per-iteration figures, while construction helpers close partially created
figures before rethrowing. A deliberate-error probe returned the figure count
from zero to zero, and the reduced live smoke left no recorder process.

### Benchmark Stage 5 - ROS Round-Trip Visualization

- [x] Let the manually invoked MATLAB script launch the recorder from the
  configured Jazzy overlay, wait for its ready marker, publish one deterministic
  bundle, and wait for its receipt.
- [x] Produce `annotated_image.png`, `camera_paths.png`, and `receipt.json`.
- [x] Verify the annotated image shows the three chronological feature points
  and trail.
- [x] Verify the trajectory artifact distinguishes reference, online, and
  smoothed camera paths and includes orientation cues.
- [x] Verify the receipt reports all five topics, one three-point track, three
  complete paths, valid timestamps/frames, and normalized quaternions.

Runtime evidence (R2024b/Jazzy, 2026-07-22): the default 20-warm-up,
200-measured run completed with five callback counts of 220. The receipt reports
one track with three observations, three 200-pose paths, matching frames and
timestamps, and normalized quaternions. Visual inspection confirmed all three
feature points and trail, three distinct paths in XY/XZ/YZ, and orientation
cues.

### Benchmark Stage 6 - Cross-Repository Validation

- [x] Run focused and full `slam-primitives` tests.
- [x] Build/test the Jazzy message overlay and regenerate MATLAB bindings from
  a clean generated-output directory.
- [x] Run focused recorder/adapter tests and the complete Eval-and-Viz CPU
  suite.
- [x] Inspect the already-run N=200 MATLAB R2024b benchmark and record its exact
  runtime evidence; Stage 6 did not rerun the benchmark.
- [x] Inspect the generated PNGs rather than using their existence alone as a
  correctness claim.

Fresh validation evidence (2026-07-22): `slam-primitives` passed 72/72;
Eval-and-Viz passed 56/56; the recorder passed 5/5 Catch2 cases with 27/27
assertions even with `BUILD_SHARED_LIBS=ON`; and fresh R2024b `ros2genmsg`
generation populated all three custom types. Stage 6 inspected the already-run
N=200 result rather than rerunning MATLAB within Stage 6. That run is:

`output_data/timing_ros2_interfaces/run_20260722T140655245_tp6b07c04a_c860_44ff_9aa6_0f7a784f8ff3`

| Workload | Mean ms | Median ms | P95 ms | Std ms |
| --- | ---: | ---: | ---: | ---: |
| Message construction | 16.554 | 15.413 | 27.746 | 5.874 |
| ROS five-topic send | 19.460 | 18.324 | 39.139 | 12.210 |
| Figure and object creation | 240.064 | 231.513 | 306.546 | 33.915 |
| Axes clear and full replot | 117.260 | 110.406 | 176.938 | 24.034 |
| Graphics-handle update | 33.820 | 31.600 | 51.466 | 8.084 |
| Handle update with `drawnow limitrate` | 1.140 | 1.190 | 1.757 | 0.363 |

Ordinary handle updates were 7.10x faster than recreating the figure and 3.47x
faster than clearing/replotting. The `limitrate` mode was 210.67x and 102.90x
faster respectively, but it is a coalesced-render policy and must remain a
separate result from fully rendered handle updates.

The corrected recorder receipt reports 24.447 ms from entry of the callback
that completed the synchronized bundle through PNG completion, with 24.414 ms
reported separately as rendering. This canonical run therefore excludes
MATLAB warm-up and plotting time from the C++ callback metric.

### Benchmark Stage 7 - Final Review And Roadmap Reconciliation

- [x] Review all three repository diffs without staging or committing user
  work.
- [x] Confirm no source, manifest, or transitive dependency mentions
  `pyramidal_klt_interfaces` or `TrackerStepResult`.
- [x] Remove or mark superseded the older Eval-owned feature-track and custom
  trajectory interface proposals in this document.
- [x] Record the timing table, commands, test totals, artifact paths, and any
  remaining runtime limitations here.
- [x] Keep the existing MATLAB plotting path available until the measured and
  visually checked ROS path supports a later migration decision.

Remaining runtime limitations:

- The standalone Eval-and-Viz shared library directory must be available to the
  recorder at runtime; the MATLAB launcher accepts `TIMING_ROS2_EVAL_LIB_DIR`
  and deliberately clears MATLAB's private `LD_LIBRARY_PATH` first.
- Headless R2024b used software OpenGL. This is suitable for the recorded
  benchmark comparison but should be called out when comparing against an
  interactive hardware-rendered session.
- `drawnow limitrate` coalesces rendering and therefore measures a different
  display-freshness policy than ordinary `drawnow`.
- Existing MATLAB plotting remains unchanged. This benchmark provides evidence
  for a later migration decision; it does not remove the current plotting path.
