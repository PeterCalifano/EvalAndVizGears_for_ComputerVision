/// @file
/// @brief Adapts shared feature-track snapshots to OpenCV rendering order.

#pragma once

#include <vector>

#include <opencv2/core.hpp>

#include <slam-primitives/feature_sets/SFeatureTrackSnapshot.h>

namespace viztools
{

/// @brief Adapts chronological feature-track snapshots to renderer trail order.
/// @details Keeps the shared tracking representation ROS- and OpenCV-independent;
///          conversion occurs only at this repository's rendering boundary.
class CFeatureTrackSnapshotAdapter
{
public:
    /// @brief Convert a chronological source snapshot into a newest-first OpenCV trail.
    /// @param snapshot ROS-independent source snapshot; it is never modified.
    /// @return Pixel locations in the newest-first order required by CTrackTrailRenderer.
    [[nodiscard]] static auto toNewestFirstTrail(
        const slam_primitives::SFeatureTrackSnapshot& snapshot) -> std::vector<cv::Point2f>
    {
        std::vector<cv::Point2f> trail;
        trail.reserve(snapshot.observations.size());

        for (auto observation = snapshot.observations.rbegin();
             observation != snapshot.observations.rend();
             ++observation)
        {
            trail.emplace_back(static_cast<float>(observation->location.u),
                               static_cast<float>(observation->location.v));
        }

        return trail;
    }
};

} // namespace viztools
