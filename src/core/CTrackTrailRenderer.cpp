/// @file
/// @brief Implements motion trail rendering for tracked feature histories.

#include "CTrackTrailRenderer.h"
#include <algorithm>
#include <opencv2/imgproc.hpp>

namespace viztools
{

    /// @brief Stores the trail rendering configuration used for draw calls.
    /// @param config Trail styling and history truncation configuration.
    CTrackTrailRenderer::CTrackTrailRenderer(STrailConfig config)
        : config_(std::move(config))
    {
    }

    /// @copydoc viztools::CTrackTrailRenderer::draw
    void CTrackTrailRenderer::draw(cv::Mat &image,
                                   const std::vector<std::vector<cv::Point2f>> &trails,
                                   const std::vector<cv::Scalar> &colors) const
    {
        cv::Mat overlay;
        if (config_.opacity < 1.0)
        {
            overlay = image.clone();
        }
        cv::Mat &canvas = (config_.opacity < 1.0) ? overlay : image;

        for (size_t t = 0; t < trails.size(); ++t)
        {
            const auto &trail = trails[t];
            if (trail.size() < 2)
                continue;

            const cv::Scalar &base_color = (!colors.empty() && t < colors.size())
                                               ? colors[t]
                                               : config_.trail_color;

            uint32_t len = std::min(static_cast<uint32_t>(trail.size()),
                                    config_.max_trail_length);

            for (uint32_t i = 0; i + 1 < len; ++i)
            {
                cv::Scalar seg_color = base_color;
                if (config_.fade_older && len > 1)
                {
                    double fade = 1.0 - static_cast<double>(i) /
                                            static_cast<double>(len - 1);
                    seg_color = base_color * fade;
                }

                cv::Point p1(static_cast<int>(trail[i].x),
                             static_cast<int>(trail[i].y));
                cv::Point p2(static_cast<int>(trail[i + 1].x),
                             static_cast<int>(trail[i + 1].y));
                cv::line(canvas, p1, p2, seg_color, config_.thickness, cv::LINE_AA);
            }
        }

        if (config_.opacity < 1.0)
        {
            cv::addWeighted(overlay, config_.opacity, image, 1.0 - config_.opacity,
                            0.0, image);
        }
    }

} // namespace viztools
