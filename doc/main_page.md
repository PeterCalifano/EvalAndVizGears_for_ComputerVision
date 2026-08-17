# EvalAndVizGears_for_ComputerVision {#mainpage}

This library provides reusable OpenCV-based primitives for annotating feature
tracks, visualizing matches, displaying frames, and recording tracking
statistics.

## Core Components

- `viztools::CFeatureOverlayRenderer` draws feature markers and IDs.
- `viztools::CTrackTrailRenderer` draws bounded track histories.
- `viztools::CFrameAnnotator` composes features, tracks, and HUD text.
- `viztools::CMatchVisualizer` compares feature correspondences.
- `viztools::CDisplayWindow` provides pause, step, and quit interaction.
- `viztools::CTrackingStatsLogger` exports algorithm statistics to CSV.
- `viztools::logging::CLogger` provides dependency-free diagnostic logging.

See the repository `README.md` for build, test, wrapper, package-consumer, and
versioning instructions.
