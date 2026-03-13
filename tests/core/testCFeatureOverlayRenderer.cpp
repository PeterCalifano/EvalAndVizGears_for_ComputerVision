/// @file
/// @brief Catch2 coverage for viztools::CFeatureOverlayRenderer.

#include <catch2/catch_test_macros.hpp>
#include "core/CFeatureOverlayRenderer.h"

using namespace viztools;

/// @brief Creates a blank RGB image used as a drawing target in overlay tests.
/// @param rows Image height in pixels.
/// @param cols Image width in pixels.
/// @return Zero-initialized color image.
static cv::Mat makeTestImage(int rows = 200, int cols = 300)
{
    return cv::Mat::zeros(rows, cols, CV_8UC3);
}

TEST_CASE("CFeatureOverlayRenderer default construction", "[core][overlay]")
{
    CFeatureOverlayRenderer renderer;
    REQUIRE(renderer.config().marker_shape == EMarkerShape::CIRCLE);
    REQUIRE(renderer.config().marker_radius == 4);
}

TEST_CASE("CFeatureOverlayRenderer draw circles on image", "[core][overlay]")
{
    CFeatureOverlayRenderer renderer;
    cv::Mat image = makeTestImage();

    std::vector<cv::Point2f> pts = {{50.0f, 50.0f}, {150.0f, 100.0f}};
    renderer.draw(image, pts);

    // The image should no longer be fully black
    REQUIRE(cv::countNonZero(image.reshape(1)) > 0);
}

TEST_CASE("CFeatureOverlayRenderer draw crosses", "[core][overlay]")
{
    SOverlayConfig cfg;
    cfg.marker_shape = EMarkerShape::CROSS;
    CFeatureOverlayRenderer renderer(cfg);
    cv::Mat image = makeTestImage();

    std::vector<cv::Point2f> pts = {{100.0f, 100.0f}};
    renderer.draw(image, pts);

    REQUIRE(cv::countNonZero(image.reshape(1)) > 0);
}

TEST_CASE("CFeatureOverlayRenderer draw diamonds", "[core][overlay]")
{
    SOverlayConfig cfg;
    cfg.marker_shape = EMarkerShape::DIAMOND;
    CFeatureOverlayRenderer renderer(cfg);
    cv::Mat image = makeTestImage();

    std::vector<cv::Point2f> pts = {{100.0f, 100.0f}};
    renderer.draw(image, pts);

    REQUIRE(cv::countNonZero(image.reshape(1)) > 0);
}

TEST_CASE("CFeatureOverlayRenderer per-feature colors", "[core][overlay]")
{
    CFeatureOverlayRenderer renderer;
    cv::Mat image = makeTestImage();

    std::vector<cv::Point2f> pts = {{50.0f, 50.0f}, {150.0f, 100.0f}};
    std::vector<cv::Scalar> colors = {{255, 0, 0}, {0, 0, 255}};
    renderer.draw(image, pts, {}, colors);

    REQUIRE(cv::countNonZero(image.reshape(1)) > 0);
}

TEST_CASE("CFeatureOverlayRenderer draw with IDs", "[core][overlay]")
{
    SOverlayConfig cfg;
    cfg.show_ids = true;
    CFeatureOverlayRenderer renderer(cfg);
    cv::Mat image = makeTestImage();

    std::vector<cv::Point2f> pts = {{50.0f, 50.0f}};
    std::vector<int> ids = {42};
    renderer.draw(image, pts, ids);

    REQUIRE(cv::countNonZero(image.reshape(1)) > 0);
}

TEST_CASE("CFeatureOverlayRenderer empty points is no-op", "[core][overlay]")
{
    CFeatureOverlayRenderer renderer;
    cv::Mat image = makeTestImage();
    cv::Mat original = image.clone();

    renderer.draw(image, {});

    // Image should remain unchanged
    cv::Mat diff;
    cv::absdiff(image, original, diff);
    REQUIRE(cv::countNonZero(diff.reshape(1)) == 0);
}

TEST_CASE("CFeatureOverlayRenderer colorFromAge gradient", "[core][overlay]")
{
    cv::Scalar young = CFeatureOverlayRenderer::colorFromAge(0.0);
    cv::Scalar old_c = CFeatureOverlayRenderer::colorFromAge(1.0);

    // Young should be greenish (high G channel), old should be reddish (high R-ish / low G)
    // BGR format: green = (0,255,0), red = (0,0,255)
    REQUIRE(young[1] > young[2]); // Green > Red for young
    REQUIRE(old_c[2] > old_c[1]); // Red > Green for old
}
