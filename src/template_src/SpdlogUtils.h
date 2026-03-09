#pragma once

#include <memory>
#include <optional>
#include <string_view>

#include <spdlog/common.h>
#include <spdlog/logger.h>

namespace spdlog_utils
{
    void ConfigureDefaultLogging(spdlog::level::level_enum level = spdlog::level::info);
    std::shared_ptr<spdlog::logger> GetLogger(std::string_view charComponentName);
    std::optional<spdlog::level::level_enum> TryParseLogLevel(std::string_view charLevelName);
    bool InitializeLogLevelFromEnvironment(std::string_view charEnvVarName = "SPDLOG_LEVEL");
} // namespace spdlog_utils
