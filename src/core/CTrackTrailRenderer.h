#pragma once
#include <cstdint>
#include <vector>

#include <opencv2/core.hpp>

namespace viztools
{

    /// @brief Configuration for track trail rendering.
    struct STrailConfig
    {
        /// @brief Maximum number of past positions to draw per trail.
        uint32_t max_trail_length{20};

        /// @brief Line thickness for trails.
        int thickness{1};

        /// @brief If true, color fades from current (bright) to oldest (dim).
        bool fade_older{true};

        /// @brief Base trail color (BGR). Used when fade_older is false.
        cv::Scalar trail_color{0, 200, 200};

        /// @brief Opacity for the trail overlay (1.0 = fully opaque).
        double opacity{0.7};
    };

    /// @brief Renders feature track trails (polylines) on an image.
    ///
    /// Each trail is a sequence of past 2D positions for a single feature.
    /// Older segments can be drawn with fading intensity to show motion history.
    class CTrackTrailRenderer
    {
      public:
        explicit CTrackTrailRenderer(STrailConfig config = {});

        /// @brief Draw track trails on the image.
        /// @param image Image to draw on (modified in-place).
        /// @param trails Per-feature trail histories (outer: features, inner: positions newest-first).
        /// @param colors Optional per-feature trail colors. If empty, trail_color is used.
        void draw(cv::Mat &image,
                  const std::vector<std::vector<cv::Point2f>> &trails,
                  const std::vector<cv::Scalar> &colors = {}) const;

        /// @brief Get mutable config reference.
        auto config() -> STrailConfig & { return config_; }

        /// @brief Get const config reference.
        auto config() const -> const STrailConfig & { return config_; }

      private:
        STrailConfig config_;
    };

} // namespace viztools
