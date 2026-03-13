/// @file
/// @brief Catch2 coverage for viztools::CFrameAnnotator.

#include <catch2/catch_test_macros.hpp>
#include "core/CFrameAnnotator.h"

using namespace viztools;

/// @brief Creates a blank RGB image used as a drawing target in annotator tests.
/// @param rows Image height in pixels.
/// @param cols Image width in pixels.
/// @return Zero-initialized color image.
static cv::Mat makeTestImage(int rows = 200, int cols = 300)
{
    return cv::Mat::zeros(rows, cols, CV_8UC3);
}

TEST_CASE("CFrameAnnotator default construction", "[core][annotator]")
{
    CFrameAnnotator annotator;
    REQUIRE(annotator.hudConfig().enabled == true);
}

TEST_CASE("CFrameAnnotator annotates with features and HUD", "[core][annotator]")
{
    CFrameAnnotator annotator;
    cv::Mat image = makeTestImage();

    SFrameAnnotation ann;
    ann.frame_id = 42;
    ann.feature_points = {{50.0f, 50.0f}, {150.0f, 100.0f}};
    ann.feature_ids = {1, 2};
    ann.is_keyframe = false;
    ann.num_lost = 3;

    annotator.annotate(image, ann);

    REQUIRE(cv::countNonZero(image.reshape(1)) > 0);
}

TEST_CASE("CFrameAnnotator keyframe draws border", "[core][annotator]")
{
    CFrameAnnotator annotator;
    cv::Mat image_kf = makeTestImage();
    cv::Mat image_no_kf = makeTestImage();

    SFrameAnnotation ann;
    ann.frame_id = 1;
    ann.is_keyframe = true;
    annotator.annotate(image_kf, ann);

    ann.is_keyframe = false;
    annotator.annotate(image_no_kf, ann);

    // Keyframe image should have more drawn pixels due to the border
    int pixels_kf = cv::countNonZero(image_kf.reshape(1));
    int pixels_no_kf = cv::countNonZero(image_no_kf.reshape(1));
    REQUIRE(pixels_kf > pixels_no_kf);
}

TEST_CASE("CFrameAnnotator with trails", "[core][annotator]")
{
    CFrameAnnotator annotator;
    cv::Mat image = makeTestImage();

    SFrameAnnotation ann;
    ann.frame_id = 5;
    ann.feature_points = {{100.0f, 100.0f}};
    ann.trails = {{{100.0f, 100.0f}, {95.0f, 95.0f}, {90.0f, 90.0f}}};

    annotator.annotate(image, ann);

    REQUIRE(cv::countNonZero(image.reshape(1)) > 0);
}

TEST_CASE("CFrameAnnotator with extra info lines", "[core][annotator]")
{
    CFrameAnnotator annotator;
    cv::Mat image = makeTestImage();

    SFrameAnnotation ann;
    ann.frame_id = 10;
    ann.extra_info = {"FPS: 30.0", "Scale: 1.05"};

    annotator.annotate(image, ann);

    REQUIRE(cv::countNonZero(image.reshape(1)) > 0);
}

TEST_CASE("CFrameAnnotator grayscale input converted to BGR", "[core][annotator]")
{
    CFrameAnnotator annotator;
    cv::Mat gray_image = cv::Mat::zeros(200, 300, CV_8UC1);

    SFrameAnnotation ann;
    ann.frame_id = 1;
    ann.feature_points = {{50.0f, 50.0f}};

    annotator.annotate(gray_image, ann);

    // After annotation, image should be converted to BGR (3 channels)
    REQUIRE(gray_image.channels() == 3);
    REQUIRE(cv::countNonZero(gray_image.reshape(1)) > 0);
}

TEST_CASE("CFrameAnnotator HUD disabled produces less output", "[core][annotator]")
{
    SOverlayConfig overlay_cfg;
    STrailConfig trail_cfg;
    SHudConfig hud_cfg;
    hud_cfg.enabled = false;
    hud_cfg.highlight_keyframes = false;

    CFrameAnnotator annotator_no_hud(overlay_cfg, trail_cfg, hud_cfg);
    CFrameAnnotator annotator_with_hud;

    cv::Mat img1 = makeTestImage();
    cv::Mat img2 = makeTestImage();

    SFrameAnnotation ann;
    ann.frame_id = 1;
    ann.feature_points = {{50.0f, 50.0f}};

    annotator_no_hud.annotate(img1, ann);
    annotator_with_hud.annotate(img2, ann);

    int pixels_no_hud = cv::countNonZero(img1.reshape(1));
    int pixels_with_hud = cv::countNonZero(img2.reshape(1));

    REQUIRE(pixels_with_hud > pixels_no_hud);
}
