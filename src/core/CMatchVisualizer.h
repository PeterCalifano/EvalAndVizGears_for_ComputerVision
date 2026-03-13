#pragma once
#include <cstdint>
#include <vector>

#include <opencv2/core.hpp>

namespace viztools
{

    /// @brief Configuration for match visualization.
    struct SMatchVizConfig
    {
        /// @brief Color for inlier match lines.
        cv::Scalar inlier_color{0, 255, 0};

        /// @brief Color for outlier match lines.
        cv::Scalar outlier_color{0, 0, 255};

        /// @brief Line thickness for match lines.
        int line_thickness{1};

        /// @brief Marker radius for matched keypoints.
        int marker_radius{3};

        /// @brief If true, stack images vertically; otherwise side-by-side.
        bool vertical_layout{false};
    };

    /// @brief Visualizes feature matches between two frames.
    ///
    /// Draws matched keypoint pairs connected by lines. Supports inlier/outlier
    /// coloring via an optional mask. Output is a side-by-side (or stacked)
    /// composite image.
    class CMatchVisualizer
    {
      public:
        explicit CMatchVisualizer(SMatchVizConfig config = {});

        /// @brief Draw matches between two images.
        /// @param img1 First image (left / top).
        /// @param img2 Second image (right / bottom).
        /// @param pts1 Matched points in img1.
        /// @param pts2 Matched points in img2 (same order as pts1).
        /// @param inlier_mask Optional per-match mask (true = inlier). If empty,
        ///        all matches are drawn as inliers.
        /// @return Composite image with matches drawn.
        auto draw(const cv::Mat &img1, const cv::Mat &img2,
                  const std::vector<cv::Point2f> &pts1,
                  const std::vector<cv::Point2f> &pts2,
                  const std::vector<bool> &inlier_mask = {}) const -> cv::Mat;

        /// @brief Get mutable config reference.
        auto config() -> SMatchVizConfig & { return config_; }

        /// @brief Get const config reference.
        auto config() const -> const SMatchVizConfig & { return config_; }

      private:
        SMatchVizConfig config_;
    };

} // namespace viztools
