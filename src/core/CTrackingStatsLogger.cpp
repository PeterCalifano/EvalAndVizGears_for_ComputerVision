/// @file
/// @brief Implements CSV logging for per-frame tracking statistics.

#include "CTrackingStatsLogger.h"

namespace viztools
{

/// @copydoc viztools::CTrackingStatsLogger::record
void CTrackingStatsLogger::record(const SFrameStats &stats)
{
    entries_.push_back(stats);
}

/// @copydoc viztools::CTrackingStatsLogger::writeCsv
auto CTrackingStatsLogger::writeCsv(const std::string &path) const -> bool
{
    std::ofstream ofs(path);
    if (!ofs.is_open())
        return false;

    ofs << "frame_id,num_tracked,num_lost,num_new,is_keyframe,cumulative_features\n";
    for (const auto &e : entries_)
    {
        ofs << e.frame_id << ","
            << e.num_tracked << ","
            << e.num_lost << ","
            << e.num_new << ","
            << (e.is_keyframe ? 1 : 0) << ","
            << e.cumulative_features << "\n";
    }

    return true;
}

} // namespace viztools
