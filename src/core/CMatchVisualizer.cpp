/// @file
/// @brief Implements feature match visualization helpers.

#include "CMatchVisualizer.h"
#include <opencv2/imgproc.hpp>

namespace viztools
{

    /// @brief Stores the layout and styling options for match visualizations.
    /// @param config Match drawing configuration.
    CMatchVisualizer::CMatchVisualizer(SMatchVizConfig config)
        : config_(std::move(config))
    {
    }

    auto CMatchVisualizer::draw(const cv::Mat &img1, const cv::Mat &img2,
                                const std::vector<cv::Point2f> &pts1,
                                const std::vector<cv::Point2f> &pts2,
                                const std::vector<bool> &inlier_mask) const -> cv::Mat
    {
        // Convert to BGR if grayscale
        cv::Mat c1, c2;
        if (img1.channels() == 1)
            cv::cvtColor(img1, c1, cv::COLOR_GRAY2BGR);
        else
            c1 = img1.clone();

        if (img2.channels() == 1)
            cv::cvtColor(img2, c2, cv::COLOR_GRAY2BGR);
        else
            c2 = img2.clone();

        // Build composite image
        cv::Mat composite;
        cv::Point2f offset;
        if (config_.vertical_layout)
        {
            int max_cols = std::max(c1.cols, c2.cols);
            composite = cv::Mat::zeros(c1.rows + c2.rows, max_cols, CV_8UC3);
            c1.copyTo(composite(cv::Rect(0, 0, c1.cols, c1.rows)));
            c2.copyTo(composite(cv::Rect(0, c1.rows, c2.cols, c2.rows)));
            offset = cv::Point2f(0.0f, static_cast<float>(c1.rows));
        }
        else
        {
            int max_rows = std::max(c1.rows, c2.rows);
            composite = cv::Mat::zeros(max_rows, c1.cols + c2.cols, CV_8UC3);
            c1.copyTo(composite(cv::Rect(0, 0, c1.cols, c1.rows)));
            c2.copyTo(composite(cv::Rect(c1.cols, 0, c2.cols, c2.rows)));
            offset = cv::Point2f(static_cast<float>(c1.cols), 0.0f);
        }

        // Draw matches
        size_t n = std::min(pts1.size(), pts2.size());
        for (size_t i = 0; i < n; ++i)
        {
            bool is_inlier = inlier_mask.empty() || (i < inlier_mask.size() && inlier_mask[i]);
            const cv::Scalar &color = is_inlier ? config_.inlier_color
                                                : config_.outlier_color;

            cv::Point p1(static_cast<int>(pts1[i].x),
                         static_cast<int>(pts1[i].y));
            cv::Point p2(static_cast<int>(pts2[i].x + offset.x),
                         static_cast<int>(pts2[i].y + offset.y));

            cv::circle(composite, p1, config_.marker_radius, color, -1, cv::LINE_AA);
            cv::circle(composite, p2, config_.marker_radius, color, -1, cv::LINE_AA);
            cv::line(composite, p1, p2, color, config_.line_thickness, cv::LINE_AA);
        }

        return composite;
    }

} // namespace viztools
