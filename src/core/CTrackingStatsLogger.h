#pragma once
#include <cstdint>
#include <fstream>
#include <string>
#include <vector>

namespace viztools
{

    /// @brief Per-frame tracking statistics entry.
    struct SFrameStats
    {
        int frame_id{0};
        uint32_t num_tracked{0};
        uint32_t num_lost{0};
        uint32_t num_new{0};
        bool is_keyframe{false};
        uint32_t cumulative_features{0};
    };

    /// @brief Accumulates per-frame tracking statistics and exports to CSV.
    ///
    /// Pure C++ class with no visualization dependency. Collects stats from
    /// each tracking step and writes them to a CSV file for analysis with
    /// external tools (Python, MATLAB, gnuplot).
    class CTrackingStatsLogger
    {
      public:
        CTrackingStatsLogger() = default;

        /// @brief Record statistics for one frame.
        /// @param stats Frame statistics entry.
        void record(const SFrameStats &stats);

        /// @brief Write all recorded statistics to a CSV file.
        /// @param path Output CSV file path.
        /// @return true on success, false if file could not be opened.
        auto writeCsv(const std::string &path) const -> bool;

        /// @brief Get the number of recorded entries.
        auto size() const -> size_t { return entries_.size(); }

        /// @brief Get all recorded entries.
        auto entries() const -> const std::vector<SFrameStats> & { return entries_; }

        /// @brief Clear all recorded entries.
        void clear() { entries_.clear(); }

      private:
        std::vector<SFrameStats> entries_;
    };

} // namespace viztools
