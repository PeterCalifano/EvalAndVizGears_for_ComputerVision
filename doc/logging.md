# Project Logging

`viztools::logging::CLogger` is compiled into the core library and installed as
`utils/logging/CLogger.h`. It uses only the C++ standard library.

The logger supports severity filtering, separate output and diagnostic streams,
optional ANSI colors, case-insensitive level parsing, and complete-line
synchronization across concurrent logger instances. Colors are disabled by
default so redirected output remains deterministic.

The default environment variable is `EVAL_AND_VIZ_LOG_LEVEL`. Accepted values
are `quiet`, `critical`, `error`, `warning`, `info`, `debug`, `trace`, and the
numeric values `0` through `6`.

`CTrackingStatsLogger` has a different responsibility: it records structured
per-frame algorithm statistics and exports CSV. It is not a diagnostic logger.
