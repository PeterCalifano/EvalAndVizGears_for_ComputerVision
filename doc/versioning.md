# Versioning And Source Releases

Version resolution uses the first available source:

1. A semantic Git tag and `git describe` distance/hash.
2. An existing `VERSION` file, including prerelease and build metadata fields.
3. The hardcoded CMake fallback.

Ordinary configure writes `${PROJECT_BINARY_DIR}/VERSION` and leaves the source
tree unchanged. Run `./generate_version.sh` to update the source `VERSION`, or
configure with `WRITE_SOURCE_VERSION_FILE=ON` when that side effect is explicit.

When `ros2/tools/sync_package_metadata.py` is present, the default
`./generate_version.sh` invocation also synchronizes immediate
`ros2/*/package.xml` manifests from root CMake metadata. Use
`--no-sync-ros2` when only `VERSION` should change; `--sync-ros2` explicitly
requests synchronization and reports a missing overlay or helper.

ROS synchronization uses only the strict `X.Y.Z` core version. It updates the
version, project-derived description, maintainer, license, and website while
preserving package names, dependencies, non-website URLs, and file modes. A
hardcoded fallback version is never propagated into package manifests.

`package_source` creates a TGZ source archive named
`EvalAndVizGears_for_ComputerVision-<version>-source.tar.gz`. Build, install,
wrapper, ROS workspace, cache, and Python bytecode directories are excluded.
No-Git consumers resolve the packaged `VERSION` file through
`PROJECT_METADATA_ONLY=ON` without configuring a compiler.
