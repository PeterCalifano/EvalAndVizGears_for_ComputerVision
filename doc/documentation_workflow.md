# Documentation Workflow

Public API documentation is generated from `README.md`, `src/`, and the public
pages directly under `doc/`. Internal plans under `doc/developments/`, reports,
dependency sources, and build trees are excluded.

## Local Build

Configure HTML and XML output from the repository root:

```bash
cmake --preset docs -DDOC_WARN_AS_ERROR=ON
cmake --build --preset docs
```

The generic `doc` target depends on the namespaced
`EvalAndVizGears_for_ComputerVision_doc` target. Generated output is written to
`build_docs/doc/html` and `build_docs/doc/xml`. Use `doc_clean` to remove all
generated documentation formats.

The XML directory is exported through the
`EvalAndVizGears_for_ComputerVision_DOXYGEN_XML_DIR` CMake cache entry so gtwrap
can use Doxygen comments for generated Python docstrings when XML output and
`GTWRAP_ADD_DOCSTRINGS` are enabled.

## Publication

The v1.11.3 parent template provides a GitHub Pages workflow using the current
Pages artifact and deployment actions. This repository must adapt that workflow
to provision its public `slam-primitives` dependency before configuration. The
workflow is intentionally not activated until the required snapshot API exists
at a committed, remotely resolvable revision.

When activated, pull requests build and upload the documentation artifact but do
not deploy it. Deployment is restricted to the default branch or an explicit
manual request. The workflow must verify both `html/index.html` and `xml/` before
publishing.
