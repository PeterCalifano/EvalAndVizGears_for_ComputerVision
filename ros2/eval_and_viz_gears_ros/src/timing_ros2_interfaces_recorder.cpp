/// @file
/// @brief Runs the one-bundle ROS 2 timing and visualization recorder node.

#include <eval_and_viz_gears_ros/CBenchmarkBundleProcessor.h>

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>

#include <nav_msgs/msg/path.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <slam_primitives_interfaces/msg/feature_track_array.hpp>

namespace eval_and_viz_gears_ros
{
namespace
{

auto topicName(std::string root, const std::string& suffix) -> std::string
{
    while (root.size() > 1U && root.back() == '/')
    {
        root.pop_back();
    }
    if (root == "/")
    {
        root.clear();
    }
    return root + suffix;
}

class CTimingRos2InterfacesRecorder final : public rclcpp::Node
{
public:
    CTimingRos2InterfacesRecorder()
        : rclcpp::Node("timing_ros2_interfaces_recorder")
    {
        const auto output_dir = declare_parameter<std::string>("output_dir", "");
        const auto topic_root =
            declare_parameter<std::string>("topic_root", "/nav_viz/benchmark");
        const auto expected_path_length =
            declare_parameter<int64_t>("expected_path_length", 200);
        const auto expected_track_observations =
            declare_parameter<int64_t>("expected_track_observations", 3);
        const auto expected_track_id = declare_parameter<int64_t>("expected_track_id", 17);

        if (output_dir.empty())
        {
            throw std::invalid_argument("output_dir parameter is required and must be nonempty");
        }
        if (topic_root.empty())
        {
            throw std::invalid_argument("topic_root parameter must be nonempty");
        }
        if (expected_path_length <= 0 || expected_track_observations <= 0)
        {
            throw std::invalid_argument("expected bundle sizes must be positive");
        }
        if (expected_track_id < 0 ||
            expected_track_id >
                static_cast<int64_t>(std::numeric_limits<uint32_t>::max()))
        {
            throw std::invalid_argument("expected_track_id must fit uint32");
        }

        processor_ = std::make_unique<CBenchmarkBundleProcessor>(SRecorderConfig{
            .output_dir = output_dir,
            .topic_root = topic_root,
            .expected_path_length = static_cast<std::size_t>(expected_path_length),
            .expected_track_observations =
                static_cast<std::size_t>(expected_track_observations),
            .expected_track_id = static_cast<uint32_t>(expected_track_id),
        });

        const auto qos = rclcpp::QoS(rclcpp::KeepLast(1U)).reliable();
        image_subscription_ = create_subscription<sensor_msgs::msg::Image>(
            topicName(topic_root, "/frontend/image"),
            qos,
            [this](sensor_msgs::msg::Image::ConstSharedPtr message) {
                const auto callback_entry = std::chrono::steady_clock::now();
                bundle_.image = *message;
                has_image_ = true;
                ++callback_counts_.image;
                noteCallbackAndFinalize(callback_entry);
            });
        tracks_subscription_ =
            create_subscription<slam_primitives_interfaces::msg::FeatureTrackArray>(
                topicName(topic_root, "/frontend/tracks"),
                qos,
                [this](
                    slam_primitives_interfaces::msg::FeatureTrackArray::ConstSharedPtr message) {
                    const auto callback_entry = std::chrono::steady_clock::now();
                    bundle_.tracks = *message;
                    has_tracks_ = true;
                    ++callback_counts_.tracks;
                    noteCallbackAndFinalize(callback_entry);
                });
        reference_path_subscription_ = create_subscription<nav_msgs::msg::Path>(
            topicName(topic_root, "/trajectory/reference"),
            qos,
            [this](nav_msgs::msg::Path::ConstSharedPtr message) {
                const auto callback_entry = std::chrono::steady_clock::now();
                bundle_.reference_path = *message;
                has_reference_path_ = true;
                ++callback_counts_.reference_path;
                noteCallbackAndFinalize(callback_entry);
            });
        online_path_subscription_ = create_subscription<nav_msgs::msg::Path>(
            topicName(topic_root, "/trajectory/online"),
            qos,
            [this](nav_msgs::msg::Path::ConstSharedPtr message) {
                const auto callback_entry = std::chrono::steady_clock::now();
                bundle_.online_path = *message;
                has_online_path_ = true;
                ++callback_counts_.online_path;
                noteCallbackAndFinalize(callback_entry);
            });
        smoothed_path_subscription_ = create_subscription<nav_msgs::msg::Path>(
            topicName(topic_root, "/trajectory/smoothed"),
            qos,
            [this](nav_msgs::msg::Path::ConstSharedPtr message) {
                const auto callback_entry = std::chrono::steady_clock::now();
                bundle_.smoothed_path = *message;
                has_smoothed_path_ = true;
                ++callback_counts_.smoothed_path;
                noteCallbackAndFinalize(callback_entry);
            });

        // The marker is published only after every reliable subscription exists.
        processor_->writeReadyMarker();
        RCLCPP_INFO(get_logger(), "ready for benchmark topics below %s", topic_root.c_str());
    }

    [[nodiscard]] auto exitCode() const -> int
    {
        return exit_code_;
    }

private:
    void noteCallbackAndFinalize(std::chrono::steady_clock::time_point callback_entry)
    {
        if (finalized_ || !has_image_ || !has_tracks_ || !has_reference_path_ ||
            !has_online_path_ || !has_smoothed_path_ || !processor_->isComplete(bundle_))
        {
            return;
        }

        finalized_ = true;
        const double callback_to_processing_entry_milliseconds =
            std::chrono::duration<double, std::milli>(
                std::chrono::steady_clock::now() - callback_entry)
                .count();
        const auto result = processor_->writeArtifacts(
            bundle_, callback_counts_, callback_to_processing_entry_milliseconds);
        exit_code_ = result.ok ? 0 : 1;
        if (result.ok)
        {
            RCLCPP_INFO(get_logger(), "wrote complete benchmark artifacts");
        }
        else
        {
            RCLCPP_ERROR(get_logger(), "benchmark bundle rejected: %s", result.error.c_str());
        }
        rclcpp::shutdown();
    }

    std::unique_ptr<CBenchmarkBundleProcessor> processor_;
    SBenchmarkBundle bundle_;
    SCallbackCounts callback_counts_;
    bool has_image_{false};
    bool has_tracks_{false};
    bool has_reference_path_{false};
    bool has_online_path_{false};
    bool has_smoothed_path_{false};
    bool finalized_{false};
    int exit_code_{1};

    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr image_subscription_;
    rclcpp::Subscription<slam_primitives_interfaces::msg::FeatureTrackArray>::SharedPtr
        tracks_subscription_;
    rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr reference_path_subscription_;
    rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr online_path_subscription_;
    rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr smoothed_path_subscription_;
};

auto helpRequested(int argc, char* argv[]) -> bool
{
    for (int argument = 1; argument < argc; ++argument)
    {
        const std::string value(argv[argument]);
        if (value == "--help" || value == "-h")
        {
            return true;
        }
    }
    return false;
}

} // namespace
} // namespace eval_and_viz_gears_ros

auto main(int argc, char* argv[]) -> int
{
    if (eval_and_viz_gears_ros::helpRequested(argc, argv))
    {
        std::puts("timing_ros2_interfaces_recorder parameters:\n"
                  "  output_dir (required)\n"
                  "  topic_root (default /nav_viz/benchmark)\n"
                  "  expected_path_length (default 200)\n"
                  "  expected_track_observations (default 3)\n"
                  "  expected_track_id (default 17)");
        return 0;
    }

    rclcpp::init(argc, argv);
    try
    {
        const auto node =
            std::make_shared<eval_and_viz_gears_ros::CTimingRos2InterfacesRecorder>();
        rclcpp::spin(node);
        const int exit_code = node->exitCode();
        if (rclcpp::ok())
        {
            rclcpp::shutdown();
        }
        return exit_code;
    }
    catch (const std::exception& exception)
    {
        std::fprintf(stderr, "timing_ros2_interfaces_recorder: %s\n", exception.what());
        if (rclcpp::ok())
        {
            rclcpp::shutdown();
        }
        return 1;
    }
}
