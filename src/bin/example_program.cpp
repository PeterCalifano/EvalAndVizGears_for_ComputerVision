/// @file
/// @brief Minimal executable demonstrating library startup and optional logging.

#include <template_src/placeholder.h>

#ifndef SPDLOG_UTILS_ENABLED
#define SPDLOG_UTILS_ENABLED 0
#endif

#if SPDLOG_UTILS_ENABLED
#include <utils/logging/SpdlogUtils.h>
#endif

/// @brief Runs the example executable built from the main project tree.
/// @return Process exit status compatible with the hosting shell.
int main()
{
#if SPDLOG_UTILS_ENABLED
    if (!spdlog_utils::InitializeLogLevelFromEnvironment())
    {
        spdlog_utils::ConfigureDefaultLogging();
    }

    auto objLogger_ = spdlog_utils::GetLogger("example_program");
    objLogger_->info("Running template example program.");
#endif

    placeholder::placeholder_fcn();
    return 0;
}
