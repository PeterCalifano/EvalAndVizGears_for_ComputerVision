#pragma once
#include "CFeatureOverlayRenderer.h"
#include "CTrackTrailRenderer.h"

#include <string>
#include <vector>

#include <opencv2/core.hpp>

namespace viztools
{

    /// @brief Per-frame annotation data passed to CFrameAnnotator.
    struct SFrameAnnotation
    {
        /// @brief Current frame index / identifier.
        int frame_id{0};

        /// @brief Feature locations in pixel coordinates.
        std::vector<cv::Point2f> feature_points;

        /// @brief Feature IDs (same order as feature_points).
        std::vector<int> feature_ids;

        /// @brief Per-feature colors (optional; same order as feature_points).
        std::vector<cv::Scalar> feature_colors;

        /// @brief Per-feature trail histories (optional; newest position first).
        std::vector<std::vector<cv::Point2f>> trails;

        /// @brief Per-trail colors (optional).
        std::vector<cv::Scalar> trail_colors;

        /// @brief Whether this frame is a keyframe.
        bool is_keyframe{false};

        /// @brief Number of features lost this frame (for HUD display).
        uint32_t num_lost{0};

        /// @brief Optional extra text lines for the HUD.
        std::vector<std::string> extra_info;
    };

    /// @brief Configuration for the HUD text overlay.
    struct SHudConfig
    {
        /// @brief Show HUD text overlay.
        bool enabled{true};

        /// @brief Font scale for HUD text.
        double font_scale{0.5};

        /// @brief HUD text color (BGR).
        cv::Scalar text_color{255, 255, 255};

        /// @brief HUD background color (BGR).
        cv::Scalar bg_color{0, 0, 0};

        /// @brief Background opacity (0 = transparent, 1 = opaque).
        double bg_opacity{0.5};

        /// @brief Draw colored border on keyframes.
        bool highlight_keyframes{true};

        /// @brief Keyframe border color (BGR).
        cv::Scalar keyframe_border_color{0, 255, 255};

        /// @brief Keyframe border thickness.
        int keyframe_border_thickness{3};
    };

    /// @brief Composite frame annotator combining feature overlay, trails, and HUD.
    ///
    /// Composes CFeatureOverlayRenderer and CTrackTrailRenderer with a text
    /// HUD showing frame ID, feature count, lost count, and keyframe status.
    /// Designed as the main entry point for producing annotated frames.
    class CFrameAnnotator
    {
      public:
        /// @brief Construct annotator with default configs.
        CFrameAnnotator();

        /// @brief Construct annotator with explicit configs.
        CFrameAnnotator(SOverlayConfig overlay_config,
                        STrailConfig trail_config,
                        SHudConfig hud_config);

        /// @brief Annotate a frame with features, trails, and HUD.
        /// @param image Image to annotate (modified in-place). If single-channel,
        ///        it is converted to BGR first.
        /// @param annotation Frame annotation data.
        void annotate(cv::Mat &image,
                      const SFrameAnnotation &annotation) const;

        /// @brief Get mutable overlay renderer.
        auto overlayRenderer() -> CFeatureOverlayRenderer & { return overlay_; }

        /// @brief Get mutable trail renderer.
        auto trailRenderer() -> CTrackTrailRenderer & { return trail_; }

        /// @brief Get mutable HUD config.
        auto hudConfig() -> SHudConfig & { return hud_config_; }

      private:
        void drawHud(cv::Mat &image,
                     const SFrameAnnotation &annotation) const;

        CFeatureOverlayRenderer overlay_;
        CTrackTrailRenderer trail_;
        SHudConfig hud_config_;
    };

} // namespace viztools
