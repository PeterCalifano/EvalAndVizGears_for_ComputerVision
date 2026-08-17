/// @file
/// @brief Standalone example rendering synthetic feature locations.

#include <core/CFeatureOverlayRenderer.h>
#include <utils/logging/CLogger.h>

#include <opencv2/core.hpp>

#include <vector>

/// @brief Renders three synthetic features into a BGR image.
/// @return Process exit status compatible with the hosting shell.
int main()
{
    viztools::logging::CLogger objLogger_("example_feature_overlay",
                                         viztools::logging::ELogLevel::Info);
    objLogger_.setLevelFromEnvironment();
    objLogger_.info("Rendering synthetic features in OpenCV BGR order.");

    cv::Mat objImage_ = cv::Mat::zeros(120, 160, CV_8UC3);
    const std::vector<cv::Point2f> objFeatureLocations_{{40.0F, 40.0F},
                                                       {80.0F, 60.0F},
                                                       {120.0F, 80.0F}};
    viztools::CFeatureOverlayRenderer objRenderer_;
    objRenderer_.draw(objImage_, objFeatureLocations_);

    return cv::countNonZero(objImage_.reshape(1)) > 0 ? 0 : 1;
}
