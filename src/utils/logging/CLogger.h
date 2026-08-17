/// @file
/// @brief Declares the dependency-free project logger and severity contracts.

#pragma once

#include <atomic>
#include <concepts>
#include <cstdint>
#include <iostream>
#include <optional>
#include <ostream>
#include <sstream>
#include <string>
#include <string_view>
#include <utility>

namespace viztools::logging
{
    /// @brief Configured logging threshold and message severity.
    enum class ELogLevel : std::uint8_t
    {
        Quiet = 0,    ///< Disable all logging.
        Critical = 1, ///< Emit only critical failures.
        Error = 2,    ///< Emit errors and critical failures.
        Warning = 3,  ///< Emit warnings and more severe messages.
        Info = 4,     ///< Emit ordinary runtime status and more severe messages.
        Debug = 5,    ///< Emit debugging details and more severe messages.
        Trace = 6     ///< Emit every supported message.
    };

    /// @brief Select whether emitted lines contain ANSI color escape sequences.
    enum class ELogColorMode : std::uint8_t
    {
        Disabled = 0, ///< Emit plain text.
        Enabled = 1   ///< Emit severity-specific ANSI colors.
    };

    /// @brief Constrains logger arguments to values accepted by an output stream.
    /// @tparam TValue Value type tested for stream insertion support.
    template <typename TValue>
    concept StreamInsertable = requires(std::ostream &objStream_, TValue &&value_) {
        objStream_ << std::forward<TValue>(value_);
    };

    /// @brief Thread-safe, dependency-free logger with explicit streams and colors.
    /// @details Each call is formatted before a process-wide output lock is taken,
    ///          so concurrent log calls are emitted as complete lines.
    class CLogger final
    {
      public:
        /// @brief Construct a logger with explicit identity, threshold, and streams.
        /// @param charComponentName Component label; an empty value uses the project identity.
        /// @param enumLevel Maximum verbosity to emit.
        /// @param enumColorMode Whether to add ANSI severity colors.
        /// @param objOutputStream Destination for info, debug, and trace messages.
        /// @param objDiagnosticStream Destination for warning, error, and critical messages.
        explicit CLogger(std::string charComponentName,
                         ELogLevel enumLevel = ELogLevel::Error,
                         ELogColorMode enumColorMode = ELogColorMode::Disabled,
                         std::ostream &objOutputStream = std::cout,
                         std::ostream &objDiagnosticStream = std::clog);

        CLogger(const CLogger &) = delete;
        CLogger &operator=(const CLogger &) = delete;
        CLogger(CLogger &&) = delete;
        CLogger &operator=(CLogger &&) = delete;
        ~CLogger() = default;

        /// @brief Set the maximum verbosity emitted by subsequent calls.
        /// @param enumLevel New logging threshold.
        void setLevel(ELogLevel enumLevel) noexcept;

        /// @brief Return the current logging threshold.
        /// @return Configured maximum verbosity.
        [[nodiscard]] ELogLevel getLevel() const noexcept;

        /// @brief Check whether a severity is enabled by the current threshold.
        /// @param enumSeverity Severity proposed for emission.
        /// @return True when the message should be written.
        [[nodiscard]] bool shouldLog(ELogLevel enumSeverity) const noexcept;

        /// @brief Parse a named or numeric logging threshold.
        /// @param charLevelText Case-insensitive name or a value from `0` through `6`.
        /// @return Parsed level, or `std::nullopt` when the text is unsupported.
        [[nodiscard]] static std::optional<ELogLevel> tryParseLevel(std::string_view charLevelText);

        /// @brief Update the threshold from an environment variable when valid.
        /// @param charVariableName Environment variable to read.
        /// @return True when a present value was parsed and applied.
        bool setLevelFromEnvironment(std::string_view charVariableName = "EVAL_AND_VIZ_LOG_LEVEL");

        /// @brief Emit a critical message when enabled.
        /// @tparam TArgs Stream-insertable argument types.
        /// @param args Values concatenated into one log line.
        template <StreamInsertable... TArgs>
        void critical(TArgs &&...args)
        {
            write_(ELogLevel::Critical, std::forward<TArgs>(args)...);
        }

        /// @brief Emit an error message when enabled.
        /// @tparam TArgs Stream-insertable argument types.
        /// @param args Values concatenated into one log line.
        template <StreamInsertable... TArgs>
        void error(TArgs &&...args)
        {
            write_(ELogLevel::Error, std::forward<TArgs>(args)...);
        }

        /// @brief Emit a warning message when enabled.
        /// @tparam TArgs Stream-insertable argument types.
        /// @param args Values concatenated into one log line.
        template <StreamInsertable... TArgs>
        void warning(TArgs &&...args)
        {
            write_(ELogLevel::Warning, std::forward<TArgs>(args)...);
        }

        /// @brief Emit an informational message when enabled.
        /// @tparam TArgs Stream-insertable argument types.
        /// @param args Values concatenated into one log line.
        template <StreamInsertable... TArgs>
        void info(TArgs &&...args)
        {
            write_(ELogLevel::Info, std::forward<TArgs>(args)...);
        }

        /// @brief Emit a debugging message when enabled.
        /// @tparam TArgs Stream-insertable argument types.
        /// @param args Values concatenated into one log line.
        template <StreamInsertable... TArgs>
        void debug(TArgs &&...args)
        {
            write_(ELogLevel::Debug, std::forward<TArgs>(args)...);
        }

        /// @brief Emit a trace message when enabled.
        /// @tparam TArgs Stream-insertable argument types.
        /// @param args Values concatenated into one log line.
        template <StreamInsertable... TArgs>
        void trace(TArgs &&...args)
        {
            write_(ELogLevel::Trace, std::forward<TArgs>(args)...);
        }

      private:
        template <StreamInsertable... TArgs>
        void write_(ELogLevel enumSeverity, TArgs &&...args)
        {
            if (!shouldLog(enumSeverity))
            {
                return;
            }

            std::ostringstream objMessageStream_;
            (objMessageStream_ << ... << std::forward<TArgs>(args));
            writeMessage_(enumSeverity, objMessageStream_.str());
        }

        void writeMessage_(ELogLevel enumSeverity, std::string_view charMessage);
        [[nodiscard]] std::ostream &selectStream_(ELogLevel enumSeverity) const noexcept;
        [[nodiscard]] static std::string_view getLevelLabel_(ELogLevel enumSeverity) noexcept;
        [[nodiscard]] static std::string_view getColorCode_(ELogLevel enumSeverity) noexcept;

      private:
        std::string charComponentName_;
        std::atomic<ELogLevel> enumLevel_;
        ELogColorMode enumColorMode_;
        std::ostream &objOutputStream_;
        std::ostream &objDiagnosticStream_;
    };
} // namespace viztools::logging
