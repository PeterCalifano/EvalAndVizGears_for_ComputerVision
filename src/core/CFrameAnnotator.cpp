/// @file
/// @brief Implements composite frame annotation helpers.

#include "CFrameAnnotator.h"
#include <opencv2/imgproc.hpp>

namespace viztools
{

/// @brief Builds an annotator with default overlay, trail, and HUD settings.
CFrameAnnotator::CFrameAnnotator() = default;

/// @brief Builds an annotator with caller-provided renderer and HUD settings.
/// @param overlay_config Feature overlay configuration.
/// @param trail_config Track trail configuration.
/// @param hud_config Heads-up-display configuration.
CFrameAnnotator::CFrameAnnotator(SOverlayConfig overlay_config,
                                 STrailConfig trail_config,
                                 SHudConfig hud_config)
    : overlay_(std::move(overlay_config)),
      trail_(std::move(trail_config)),
      hud_config_(std::move(hud_config))
{
}

/// @copydoc viztools::CFrameAnnotator::annotate
void CFrameAnnotator::annotate(cv::Mat &image,
                               const SFrameAnnotation &annotation) const
{
    // Convert grayscale to BGR if needed
    if (image.channels() == 1)
    {
        cv::cvtColor(image, image, cv::COLOR_GRAY2BGR);
    }

    // Draw trails first (underneath features)
    if (!annotation.trails.empty())
    {
        trail_.draw(image, annotation.trails, annotation.trail_colors);
    }

    // Draw feature markers
    if (!annotation.feature_points.empty())
    {
        overlay_.draw(image, annotation.feature_points,
                      annotation.feature_ids, annotation.feature_colors);
    }

    // Draw HUD
    if (hud_config_.enabled)
    {
        drawHud(image, annotation);
    }

    // Draw keyframe border
    if (hud_config_.highlight_keyframes && annotation.is_keyframe)
    {
        cv::rectangle(image, cv::Point(0, 0),
                      cv::Point(image.cols - 1, image.rows - 1),
                      hud_config_.keyframe_border_color,
                      hud_config_.keyframe_border_thickness);
    }
}

/// @brief Draws the textual HUD summarizing the current frame annotation.
/// @param image Image receiving the HUD overlay.
/// @param annotation Data used to assemble the HUD text lines.
void CFrameAnnotator::drawHud(cv::Mat &image,
                              const SFrameAnnotation &annotation) const
{
    std::vector<std::string> lines;
    lines.push_back("Frame: " + std::to_string(annotation.frame_id));
    lines.push_back("Features: " +
                    std::to_string(annotation.feature_points.size()));
    if (annotation.num_lost > 0)
    {
        lines.push_back("Lost: " + std::to_string(annotation.num_lost));
    }
    if (annotation.is_keyframe)
    {
        lines.push_back("[KEYFRAME]");
    }
    for (const auto &extra : annotation.extra_info)
    {
        lines.push_back(extra);
    }

    // Compute HUD background rectangle
    int font_face = cv::FONT_HERSHEY_SIMPLEX;
    int baseline = 0;
    int line_height = 0;
    int max_width = 0;

    for (const auto &line : lines)
    {
        cv::Size text_size = cv::getTextSize(line, font_face,
                                              hud_config_.font_scale, 1,
                                              &baseline);
        line_height = std::max(line_height, text_size.height + baseline + 4);
        max_width = std::max(max_width, text_size.width);
    }

    int padding = 6;
    int bg_height = static_cast<int>(lines.size()) * line_height + padding * 2;
    int bg_width = max_width + padding * 2;

    // Draw semi-transparent background
    cv::Mat roi = image(cv::Rect(0, 0,
                                  std::min(bg_width, image.cols),
                                  std::min(bg_height, image.rows)));
    cv::Mat bg_overlay;
    roi.copyTo(bg_overlay);
    bg_overlay.setTo(hud_config_.bg_color);
    cv::addWeighted(bg_overlay, hud_config_.bg_opacity, roi,
                    1.0 - hud_config_.bg_opacity, 0.0, roi);

    // Draw text lines
    int y = padding + line_height - baseline - 2;
    for (const auto &line : lines)
    {
        cv::putText(image, line, cv::Point(padding, y),
                    font_face, hud_config_.font_scale,
                    hud_config_.text_color, 1, cv::LINE_AA);
        y += line_height;
    }
}

} // namespace viztools
