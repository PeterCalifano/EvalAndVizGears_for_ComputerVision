/// @file
/// @brief Catch2 coverage for viztools::CMatchVisualizer.

#include <catch2/catch_test_macros.hpp>
#include "core/CMatchVisualizer.h"

using namespace viztools;

/// @brief Creates a neutral test image that makes rendered matches visible.
/// @param rows Image height in pixels.
/// @param cols Image width in pixels.
/// @return Constant-color RGB test image.
static cv::Mat makeTestImage(int rows = 100, int cols = 150)
{
    // Create a non-black image so we can distinguish drawing
    cv::Mat img(rows, cols, CV_8UC3, cv::Scalar(50, 50, 50));
    return img;
}

TEST_CASE("CMatchVisualizer default construction", "[core][match]")
{
    CMatchVisualizer viz;
    REQUIRE(viz.config().vertical_layout == false);
    REQUIRE(viz.config().line_thickness == 1);
}

TEST_CASE("CMatchVisualizer horizontal layout dimensions", "[core][match]")
{
    CMatchVisualizer viz;
    cv::Mat img1 = makeTestImage(100, 150);
    cv::Mat img2 = makeTestImage(100, 150);

    std::vector<cv::Point2f> pts1 = {{50.0f, 50.0f}};
    std::vector<cv::Point2f> pts2 = {{60.0f, 55.0f}};

    cv::Mat result = viz.draw(img1, img2, pts1, pts2);

    REQUIRE(result.rows == 100);
    REQUIRE(result.cols == 300); // side-by-side
    REQUIRE(result.channels() == 3);
}

TEST_CASE("CMatchVisualizer vertical layout dimensions", "[core][match]")
{
    SMatchVizConfig cfg;
    cfg.vertical_layout = true;
    CMatchVisualizer viz(cfg);

    cv::Mat img1 = makeTestImage(100, 150);
    cv::Mat img2 = makeTestImage(100, 150);

    std::vector<cv::Point2f> pts1 = {{50.0f, 50.0f}};
    std::vector<cv::Point2f> pts2 = {{60.0f, 55.0f}};

    cv::Mat result = viz.draw(img1, img2, pts1, pts2);

    REQUIRE(result.rows == 200); // stacked
    REQUIRE(result.cols == 150);
}

TEST_CASE("CMatchVisualizer draws match lines", "[core][match]")
{
    CMatchVisualizer viz;
    cv::Mat img1 = cv::Mat::zeros(100, 150, CV_8UC3);
    cv::Mat img2 = cv::Mat::zeros(100, 150, CV_8UC3);

    std::vector<cv::Point2f> pts1 = {{50.0f, 50.0f}, {70.0f, 30.0f}};
    std::vector<cv::Point2f> pts2 = {{55.0f, 52.0f}, {75.0f, 35.0f}};

    cv::Mat result = viz.draw(img1, img2, pts1, pts2);

    REQUIRE(cv::countNonZero(result.reshape(1)) > 0);
}

TEST_CASE("CMatchVisualizer inlier/outlier coloring", "[core][match]")
{
    CMatchVisualizer viz;
    cv::Mat img1 = cv::Mat::zeros(100, 150, CV_8UC3);
    cv::Mat img2 = cv::Mat::zeros(100, 150, CV_8UC3);

    std::vector<cv::Point2f> pts1 = {{50.0f, 50.0f}, {70.0f, 30.0f}};
    std::vector<cv::Point2f> pts2 = {{55.0f, 52.0f}, {75.0f, 35.0f}};
    std::vector<bool> mask = {true, false};

    cv::Mat result = viz.draw(img1, img2, pts1, pts2, mask);

    REQUIRE(cv::countNonZero(result.reshape(1)) > 0);
}

TEST_CASE("CMatchVisualizer empty matches produces composite only", "[core][match]")
{
    CMatchVisualizer viz;
    cv::Mat img1 = makeTestImage(100, 150);
    cv::Mat img2 = makeTestImage(100, 150);

    cv::Mat result = viz.draw(img1, img2, {}, {});

    // Should still produce a composite image with correct dimensions
    REQUIRE(result.rows == 100);
    REQUIRE(result.cols == 300);
}

TEST_CASE("CMatchVisualizer grayscale input converted to BGR", "[core][match]")
{
    CMatchVisualizer viz;
    cv::Mat img1(100, 150, CV_8UC1, cv::Scalar(128));
    cv::Mat img2(100, 150, CV_8UC1, cv::Scalar(128));

    std::vector<cv::Point2f> pts1 = {{50.0f, 50.0f}};
    std::vector<cv::Point2f> pts2 = {{60.0f, 55.0f}};

    cv::Mat result = viz.draw(img1, img2, pts1, pts2);

    REQUIRE(result.channels() == 3);
}

TEST_CASE("CMatchVisualizer different-sized images", "[core][match]")
{
    CMatchVisualizer viz;
    cv::Mat img1 = cv::Mat::zeros(100, 150, CV_8UC3);
    cv::Mat img2 = cv::Mat::zeros(80, 120, CV_8UC3);

    std::vector<cv::Point2f> pts1 = {{50.0f, 50.0f}};
    std::vector<cv::Point2f> pts2 = {{60.0f, 40.0f}};

    cv::Mat result = viz.draw(img1, img2, pts1, pts2);

    // Horizontal: max rows, sum cols
    REQUIRE(result.rows == 100);
    REQUIRE(result.cols == 270);
}
