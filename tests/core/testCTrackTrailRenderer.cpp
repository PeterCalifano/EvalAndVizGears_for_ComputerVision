/// @file
/// @brief Catch2 coverage for viztools::CTrackTrailRenderer.

#include <catch2/catch_test_macros.hpp>
#include "core/CTrackTrailRenderer.h"

using namespace viztools;

/// @brief Creates a blank RGB image used as a drawing target in trail tests.
/// @param rows Image height in pixels.
/// @param cols Image width in pixels.
/// @return Zero-initialized color image.
static cv::Mat makeTestImage(int rows = 200, int cols = 300)
{
    return cv::Mat::zeros(rows, cols, CV_8UC3);
}

TEST_CASE("CTrackTrailRenderer default construction", "[core][trail]")
{
    CTrackTrailRenderer renderer;
    REQUIRE(renderer.config().max_trail_length == 20);
    REQUIRE(renderer.config().fade_older == true);
}

TEST_CASE("CTrackTrailRenderer draws trail lines", "[core][trail]")
{
    CTrackTrailRenderer renderer;
    cv::Mat image = makeTestImage();

    std::vector<std::vector<cv::Point2f>> trails = {
        {{100.0f, 100.0f}, {90.0f, 95.0f}, {80.0f, 90.0f}, {70.0f, 85.0f}}
    };

    renderer.draw(image, trails);

    REQUIRE(cv::countNonZero(image.reshape(1)) > 0);
}

TEST_CASE("CTrackTrailRenderer empty trails is no-op", "[core][trail]")
{
    CTrackTrailRenderer renderer;
    cv::Mat image = makeTestImage();
    cv::Mat original = image.clone();

    renderer.draw(image, {});

    cv::Mat diff;
    cv::absdiff(image, original, diff);
    REQUIRE(cv::countNonZero(diff.reshape(1)) == 0);
}

TEST_CASE("CTrackTrailRenderer single-point trail is no-op", "[core][trail]")
{
    CTrackTrailRenderer renderer;
    cv::Mat image = makeTestImage();
    cv::Mat original = image.clone();

    // A trail with only one point has no line segments to draw
    std::vector<std::vector<cv::Point2f>> trails = {
        {{100.0f, 100.0f}}
    };

    renderer.draw(image, trails);

    cv::Mat diff;
    cv::absdiff(image, original, diff);
    REQUIRE(cv::countNonZero(diff.reshape(1)) == 0);
}

TEST_CASE("CTrackTrailRenderer respects max_trail_length", "[core][trail]")
{
    STrailConfig cfg;
    cfg.max_trail_length = 3;
    cfg.fade_older = false;
    CTrackTrailRenderer renderer(cfg);

    cv::Mat image_short = makeTestImage();
    cv::Mat image_long = makeTestImage();

    // Trail with 3 points (2 segments)
    std::vector<std::vector<cv::Point2f>> short_trail = {
        {{100.0f, 100.0f}, {90.0f, 90.0f}, {80.0f, 80.0f}}
    };

    // Trail with 10 points, but should be clamped to max_trail_length=3
    std::vector<std::vector<cv::Point2f>> long_trail = {
        {{100.0f, 100.0f}, {90.0f, 90.0f}, {80.0f, 80.0f},
         {70.0f, 70.0f}, {60.0f, 60.0f}, {50.0f, 50.0f},
         {40.0f, 40.0f}, {30.0f, 30.0f}, {20.0f, 20.0f}, {10.0f, 10.0f}}
    };

    renderer.draw(image_short, short_trail);
    renderer.draw(image_long, long_trail);

    int pixels_short = cv::countNonZero(image_short.reshape(1));
    int pixels_long = cv::countNonZero(image_long.reshape(1));

    // Both should draw similar pixel count since long trail is clamped
    REQUIRE(pixels_short > 0);
    REQUIRE(pixels_long > 0);
    // Long trail should have same or similar drawn pixels as short trail
    // (they draw the same first 3 points worth of segments)
    REQUIRE(pixels_long == pixels_short);
}

TEST_CASE("CTrackTrailRenderer with per-feature colors", "[core][trail]")
{
    CTrackTrailRenderer renderer;
    cv::Mat image = makeTestImage();

    std::vector<std::vector<cv::Point2f>> trails = {
        {{100.0f, 100.0f}, {90.0f, 90.0f}},
        {{200.0f, 50.0f}, {190.0f, 45.0f}}
    };
    std::vector<cv::Scalar> colors = {{255, 0, 0}, {0, 0, 255}};

    renderer.draw(image, trails, colors);

    REQUIRE(cv::countNonZero(image.reshape(1)) > 0);
}
