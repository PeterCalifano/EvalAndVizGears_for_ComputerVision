/// @file
/// @brief Implements feature marker rendering utilities.

#include "CFeatureOverlayRenderer.h"
#include <algorithm>
#include <opencv2/imgproc.hpp>

namespace viztools
{

    /// @brief Stores the rendering configuration used for subsequent draw calls.
    /// @param config Marker styling and overlay configuration.
    CFeatureOverlayRenderer::CFeatureOverlayRenderer(SOverlayConfig config)
        : config_(std::move(config))
    {
    }

    /// @copydoc viztools::CFeatureOverlayRenderer::draw
    void CFeatureOverlayRenderer::draw(cv::Mat &image,
                                       const std::vector<cv::Point2f> &points,
                                       const std::vector<int> &ids,
                                       const std::vector<cv::Scalar> &colors) const
    {
        cv::Mat overlay;
        if (config_.opacity < 1.0)
        {
            overlay = image.clone();
        }

        cv::Mat &canvas = (config_.opacity < 1.0) ? overlay : image;

        for (size_t i = 0; i < points.size(); ++i)
        {
            const cv::Scalar &color = (!colors.empty() && i < colors.size())
                                          ? colors[i]
                                          : config_.default_color;

            switch (config_.marker_shape)
            {
            case EMarkerShape::CIRCLE:
                drawCircle(canvas, points[i], color);
                break;
            case EMarkerShape::CROSS:
                drawCross(canvas, points[i], color);
                break;
            case EMarkerShape::DIAMOND:
                drawDiamond(canvas, points[i], color);
                break;
            }

            if (config_.show_ids && !ids.empty() && i < ids.size())
            {
                cv::putText(canvas, std::to_string(ids[i]),
                            cv::Point(static_cast<int>(points[i].x) + config_.marker_radius + 2,
                                      static_cast<int>(points[i].y) - 2),
                            cv::FONT_HERSHEY_SIMPLEX, config_.font_scale,
                            color, 1, cv::LINE_AA);
            }
        }

        if (config_.opacity < 1.0)
        {
            cv::addWeighted(overlay, config_.opacity, image, 1.0 - config_.opacity,
                            0.0, image);
        }
    }

    /// @copydoc viztools::CFeatureOverlayRenderer::colorFromAge
    auto CFeatureOverlayRenderer::colorFromAge(double normalized_age) -> cv::Scalar
    {
        double t = std::clamp(normalized_age, 0.0, 1.0);
        // Green (0,255,0) → Yellow (0,255,255) → Red (0,0,255) in BGR
        int r, g;
        if (t < 0.5)
        {
            r = static_cast<int>(255.0 * (t * 2.0));
            g = 255;
        }
        else
        {
            r = 255;
            g = static_cast<int>(255.0 * (1.0 - (t - 0.5) * 2.0));
        }
        return {0.0, static_cast<double>(g), static_cast<double>(r)};
    }

    /// @brief Draws a circular marker at a feature location.
    /// @param image Image receiving the marker.
    /// @param pt Feature position in pixel coordinates.
    /// @param color Marker color in BGR order.
    void CFeatureOverlayRenderer::drawCircle(
        cv::Mat &image, cv::Point2f pt, const cv::Scalar &color) const
    {
        cv::circle(image, cv::Point(static_cast<int>(pt.x), static_cast<int>(pt.y)),
                   config_.marker_radius, color, config_.thickness, cv::LINE_AA);
    }

    /// @brief Draws a cross marker centered on a feature location.
    /// @param image Image receiving the marker.
    /// @param pt Feature position in pixel coordinates.
    /// @param color Marker color in BGR order.
    void CFeatureOverlayRenderer::drawCross(
        cv::Mat &image, cv::Point2f pt, const cv::Scalar &color) const
    {
        int r = config_.marker_radius;
        cv::Point center(static_cast<int>(pt.x), static_cast<int>(pt.y));
        cv::line(image, center - cv::Point(r, 0), center + cv::Point(r, 0),
                 color, config_.thickness, cv::LINE_AA);
        cv::line(image, center - cv::Point(0, r), center + cv::Point(0, r),
                 color, config_.thickness, cv::LINE_AA);
    }

    /// @brief Draws a diamond marker centered on a feature location.
    /// @param image Image receiving the marker.
    /// @param pt Feature position in pixel coordinates.
    /// @param color Marker color in BGR order.
    void CFeatureOverlayRenderer::drawDiamond(
        cv::Mat &image, cv::Point2f pt, const cv::Scalar &color) const
    {
        int r = config_.marker_radius;
        cv::Point center(static_cast<int>(pt.x), static_cast<int>(pt.y));
        std::vector<cv::Point> diamond = {
            center + cv::Point(0, -r),
            center + cv::Point(r, 0),
            center + cv::Point(0, r),
            center + cv::Point(-r, 0)};
        cv::polylines(image, diamond, true, color, config_.thickness, cv::LINE_AA);
    }

} // namespace viztools
