/// @file
/// @brief Declares deterministic ROS 2 benchmark validation and artifact output.

#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string>

#include <nav_msgs/msg/path.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <slam_primitives_interfaces/msg/feature_track_array.hpp>

namespace eval_and_viz_gears_ros
{

/// @brief Complete five-topic payload consumed by the timing recorder.
struct SBenchmarkBundle
{
    sensor_msgs::msg::Image image;
    slam_primitives_interfaces::msg::FeatureTrackArray tracks;
    nav_msgs::msg::Path reference_path;
    nav_msgs::msg::Path online_path;
    nav_msgs::msg::Path smoothed_path;
};

/// @brief Recorder validation and output configuration.
struct SRecorderConfig
{
    std::filesystem::path output_dir;
    std::string topic_root{"/nav_viz/benchmark"};
    std::size_t expected_path_length{200U};
    std::size_t expected_track_observations{3U};
    /// @brief Exact unsigned 64-bit track identity expected in the bundle.
    uint64_t expected_track_id{17U};
};

/// @brief Callback totals recorded when a synchronized bundle is finalized.
struct SCallbackCounts
{
    uint64_t image{0U};
    uint64_t tracks{0U};
    uint64_t reference_path{0U};
    uint64_t online_path{0U};
    uint64_t smoothed_path{0U};
};

/// @brief Validation and artifact-generation outcome.
struct SBundleResult
{
    bool ok{false};
    bool frame_ids_agree{true};
    bool timestamps_agree{true};
    bool quaternions_valid{true};
    double render_milliseconds{0.0};
    std::string error;
};

/// @brief Validates and renders one deterministic ROS 2 benchmark bundle.
class CBenchmarkBundleProcessor
{
public:
    /// Quaternion norms may differ from one only by this absolute tolerance.
    static constexpr double kQuaternionNormTolerance = 1.0e-6;

    /// @brief Construct a processor with fixed expected bundle sizes and identity.
    /// @param config Validation and artifact-output configuration.
    /// @throws std::invalid_argument When an expected bundle size is zero.
    explicit CBenchmarkBundleProcessor(SRecorderConfig config);

    /// @brief Check the synchronization and expected-size gate used by the node.
    [[nodiscard]] auto isComplete(const SBenchmarkBundle& bundle) const -> bool;

    /// @brief Validate image, feature-track, trajectory, frame, and time contracts.
    [[nodiscard]] auto validate(const SBenchmarkBundle& bundle) const -> SBundleResult;

    /// @brief Atomically write the recorder readiness marker.
    void writeReadyMarker() const;

    /// @brief Validate, render PNG artifacts, and atomically write a receipt.
    [[nodiscard]] auto writeArtifacts(
        const SBenchmarkBundle& bundle,
        const SCallbackCounts& callback_counts,
        double callback_to_processing_entry_milliseconds) const -> SBundleResult;

private:
    SRecorderConfig config_;
};

} // namespace eval_and_viz_gears_ros
