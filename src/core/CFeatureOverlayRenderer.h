#pragma once
#include <cstdint>
#include <vector>

#include <opencv2/core.hpp>

namespace viztools
{

    /// @brief Marker shape for feature rendering.
    enum class EMarkerShape : uint8_t
    {
        CIRCLE,
        CROSS,
        DIAMOND
    };

    /// @brief Configuration for feature overlay rendering.
    struct SOverlayConfig
    {
        /// @brief Marker shape to draw at each feature location.
        EMarkerShape marker_shape{EMarkerShape::CIRCLE};

        /// @brief Marker radius in pixels.
        int marker_radius{4};

        /// @brief Line thickness for markers (-1 = filled for circles).
        int thickness{1};

        /// @brief Default marker color (BGR) when no per-feature color is given.
        cv::Scalar default_color{0, 255, 0};

        /// @brief If true, draw feature ID labels next to markers.
        bool show_ids{false};

        /// @brief Font scale for ID labels.
        double font_scale{0.35};

        /// @brief Opacity for the overlay (1.0 = fully opaque).
        double opacity{1.0};
    };

    /// @brief Renders feature markers on an image.
    ///
    /// Draws circles, crosses, or diamonds at given 2D locations. Supports
    /// per-feature coloring (e.g. by track age or custom scalar) and optional
    /// ID labels.
    class CFeatureOverlayRenderer
    {
      public:
        explicit CFeatureOverlayRenderer(SOverlayConfig config = {});

        /// @brief Draw feature markers on the image.
        /// @param image Image to draw on (modified in-place).
        /// @param points Feature locations in pixel coordinates.
        /// @param ids Optional per-feature IDs for labeling.
        /// @param colors Optional per-feature colors. If empty, default_color is used.
        void draw(cv::Mat &image,
                  const std::vector<cv::Point2f> &points,
                  const std::vector<int> &ids = {},
                  const std::vector<cv::Scalar> &colors = {}) const;

        /// @brief Generate a color based on a normalized age value [0, 1].
        /// Maps 0 (young) → green through yellow to 1 (old) → red.
        /// @param normalized_age Value in [0, 1].
        /// @return BGR color.
        static auto colorFromAge(double normalized_age) -> cv::Scalar;

        /// @brief Get mutable config reference.
        auto config() -> SOverlayConfig & { return config_; }

        /// @brief Get const config reference.
        auto config() const -> const SOverlayConfig & { return config_; }

      private:
        void drawCircle(cv::Mat &image, cv::Point2f pt, const cv::Scalar &color) const;
        void drawCross(cv::Mat &image, cv::Point2f pt, const cv::Scalar &color) const;
        void drawDiamond(cv::Mat &image, cv::Point2f pt, const cv::Scalar &color) const;

        SOverlayConfig config_;
    };

} // namespace viztools
