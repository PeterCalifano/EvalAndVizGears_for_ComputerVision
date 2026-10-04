/// @file
/// @brief Implements ROS 2 benchmark validation and deterministic image artifacts.

#include <eval_and_viz_gears_ros/CBenchmarkBundleProcessor.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <utility>
#include <vector>

#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

#include <core/CFeatureTrackSnapshotAdapter.h>
#include <core/CFrameAnnotator.h>
#include <slam-primitives/feature_sets/feature_track_snapshot.h>

namespace eval_and_viz_gears_ros
{
namespace
{

using TStamp = builtin_interfaces::msg::Time;

auto stampsEqual(const TStamp& lhs, const TStamp& rhs) -> bool
{
    return lhs.sec == rhs.sec && lhs.nanosec == rhs.nanosec;
}

auto stampLess(const TStamp& lhs, const TStamp& rhs) -> bool
{
    return lhs.sec < rhs.sec || (lhs.sec == rhs.sec && lhs.nanosec < rhs.nanosec);
}

auto finite(double value) -> bool
{
    return std::isfinite(value);
}

void setFirstError(SBundleResult& result, std::string error)
{
    if (result.error.empty())
    {
        result.error = std::move(error);
    }
}

auto escapeJson(std::string_view value) -> std::string
{
    std::ostringstream escaped;
    for (const char character : value)
    {
        switch (character)
        {
        case '"':
            escaped << "\\\"";
            break;
        case '\\':
            escaped << "\\\\";
            break;
        case '\n':
            escaped << "\\n";
            break;
        case '\r':
            escaped << "\\r";
            break;
        case '\t':
            escaped << "\\t";
            break;
        default:
            escaped << character;
            break;
        }
    }
    return escaped.str();
}

void writeTextAtomic(const std::filesystem::path& path, const std::string& contents)
{
    const auto temporary_path = path.parent_path() / (path.filename().string() + ".tmp");
    {
        std::ofstream output(temporary_path, std::ios::binary | std::ios::trunc);
        if (!output)
        {
            throw std::runtime_error("unable to open temporary file " + temporary_path.string());
        }
        output << contents;
        output.flush();
        if (!output)
        {
            throw std::runtime_error("unable to write temporary file " + temporary_path.string());
        }
    }

    std::filesystem::rename(temporary_path, path);
}

void writePngAtomic(const std::filesystem::path& path, const cv::Mat& image)
{
    const auto temporary_path = path.parent_path() /
                                (path.stem().string() + ".tmp" + path.extension().string());
    if (!cv::imwrite(temporary_path.string(), image))
    {
        throw std::runtime_error("unable to encode PNG " + temporary_path.string());
    }
    std::filesystem::rename(temporary_path, path);
}

auto makeImage(const sensor_msgs::msg::Image& message) -> cv::Mat
{
    const auto row_step = static_cast<std::size_t>(message.step);
    // OpenCV receives a temporary read-only view; clone immediately owns the mono8 pixels.
    cv::Mat view(static_cast<int>(message.height),
                 static_cast<int>(message.width),
                 CV_8UC1,
                 const_cast<uint8_t*>(message.data.data()),
                 row_step);
    return view.clone();
}

auto makeSnapshot(const slam_primitives_interfaces::msg::FeatureTrack2D& message)
    -> slam_primitives::SFeatureTrackSnapshot
{
    slam_primitives::SFeatureTrackSnapshot snapshot{
        .track_id = slam_primitives::CFeatureTrackID{message.track_id},
        .is_terminated = message.is_terminated,
    };
    snapshot.observations.reserve(message.observations.size());
    for (const auto& observation : message.observations)
    {
        snapshot.observations.push_back({
            .frame_id = slam_primitives::CFrameID{observation.frame_id},
            .location = {
                .u = observation.u,
                .v = observation.v,
            },
        });
    }
    return snapshot;
}

auto renderAnnotatedImage(const SBenchmarkBundle& bundle) -> cv::Mat
{
    auto image = makeImage(bundle.image);
    const auto snapshot = makeSnapshot(bundle.tracks.tracks.front());

    viztools::SFrameAnnotation annotation;
    annotation.frame_id = snapshot.observations.back().frame_id.value();
    annotation.feature_points.reserve(snapshot.observations.size());
    for (const auto& observation : snapshot.observations)
    {
        annotation.feature_points.emplace_back(static_cast<float>(observation.location.u),
                                               static_cast<float>(observation.location.v));
    }
    annotation.trails.push_back(
        viztools::CFeatureTrackSnapshotAdapter::toNewestFirstTrail(snapshot));
    annotation.extra_info.push_back("Track: " + std::to_string(snapshot.track_id.value()));

    viztools::SOverlayConfig overlay_config;
    overlay_config.marker_radius = 5;
    overlay_config.thickness = 2;
    overlay_config.default_color = cv::Scalar(0, 255, 0);

    viztools::STrailConfig trail_config;
    trail_config.max_trail_length = static_cast<uint32_t>(snapshot.observations.size());
    trail_config.thickness = 2;
    trail_config.fade_older = false;
    trail_config.trail_color = cv::Scalar(0, 200, 255);
    trail_config.opacity = 1.0;

    viztools::CFrameAnnotator annotator(overlay_config, trail_config, {});
    annotator.annotate(image, annotation);
    return image;
}

auto orientationXAxis(const geometry_msgs::msg::Quaternion& quaternion) -> std::array<double, 3>
{
    const double x = quaternion.x;
    const double y = quaternion.y;
    const double z = quaternion.z;
    const double w = quaternion.w;
    return {
        1.0 - 2.0 * (y * y + z * z),
        2.0 * (x * y + w * z),
        2.0 * (x * z - w * y),
    };
}

auto positionCoordinates(const geometry_msgs::msg::Point& position) -> std::array<double, 3>
{
    return {position.x, position.y, position.z};
}

struct SProjection
{
    std::string label;
    std::size_t horizontal_axis;
    std::size_t vertical_axis;
};

struct SColoredPath
{
    const nav_msgs::msg::Path* path;
    std::string label;
    cv::Scalar color;
};

auto renderCameraPaths(const SBenchmarkBundle& bundle) -> cv::Mat
{
    constexpr int image_width = 1500;
    constexpr int image_height = 560;
    constexpr int panel_width = 470;
    constexpr int panel_top = 80;
    constexpr int panel_bottom = 535;
    constexpr int panel_margin = 25;
    constexpr int plot_padding = 38;

    cv::Mat canvas(image_height, image_width, CV_8UC3, cv::Scalar(250, 250, 250));
    const std::array<SProjection, 3> projections{{
        {"XY", 0U, 1U},
        {"XZ", 0U, 2U},
        {"YZ", 1U, 2U},
    }};
    const std::array<SColoredPath, 3> paths{{
        {&bundle.reference_path, "reference", cv::Scalar(30, 30, 220)},
        {&bundle.online_path, "online", cv::Scalar(30, 170, 30)},
        {&bundle.smoothed_path, "smoothed", cv::Scalar(220, 80, 30)},
    }};

    int legend_x = 35;
    for (const auto& colored_path : paths)
    {
        cv::line(canvas, {legend_x, 35}, {legend_x + 35, 35}, colored_path.color, 3, cv::LINE_AA);
        cv::putText(canvas,
                    colored_path.label,
                    {legend_x + 43, 42},
                    cv::FONT_HERSHEY_SIMPLEX,
                    0.6,
                    cv::Scalar(30, 30, 30),
                    1,
                    cv::LINE_AA);
        legend_x += 185;
    }

    for (std::size_t projection_index = 0U; projection_index < projections.size();
         ++projection_index)
    {
        const auto& projection = projections[projection_index];
        const int panel_left = panel_margin + static_cast<int>(projection_index) * panel_width;
        const int panel_right = panel_left + panel_width - panel_margin;
        const int plot_left = panel_left + plot_padding;
        const int plot_right = panel_right - plot_padding;
        const int plot_top = panel_top + plot_padding;
        const int plot_bottom = panel_bottom - plot_padding;

        double minimum_horizontal = std::numeric_limits<double>::infinity();
        double maximum_horizontal = -std::numeric_limits<double>::infinity();
        double minimum_vertical = std::numeric_limits<double>::infinity();
        double maximum_vertical = -std::numeric_limits<double>::infinity();
        for (const auto& colored_path : paths)
        {
            for (const auto& pose : colored_path.path->poses)
            {
                const auto position = positionCoordinates(pose.pose.position);
                minimum_horizontal = std::min(minimum_horizontal, position[projection.horizontal_axis]);
                maximum_horizontal = std::max(maximum_horizontal, position[projection.horizontal_axis]);
                minimum_vertical = std::min(minimum_vertical, position[projection.vertical_axis]);
                maximum_vertical = std::max(maximum_vertical, position[projection.vertical_axis]);
            }
        }

        const double horizontal_span = std::max(maximum_horizontal - minimum_horizontal, 1.0e-9);
        const double vertical_span = std::max(maximum_vertical - minimum_vertical, 1.0e-9);
        const auto project = [&](const std::array<double, 3>& coordinates) -> cv::Point {
            const double horizontal =
                (coordinates[projection.horizontal_axis] - minimum_horizontal) / horizontal_span;
            const double vertical =
                (coordinates[projection.vertical_axis] - minimum_vertical) / vertical_span;
            return {
                plot_left + static_cast<int>(std::lround(horizontal * (plot_right - plot_left))),
                plot_bottom - static_cast<int>(std::lround(vertical * (plot_bottom - plot_top))),
            };
        };

        cv::rectangle(canvas,
                      {panel_left, panel_top},
                      {panel_right, panel_bottom},
                      cv::Scalar(120, 120, 120),
                      1,
                      cv::LINE_AA);
        cv::putText(canvas,
                    projection.label + " projection",
                    {panel_left + 12, panel_top + 25},
                    cv::FONT_HERSHEY_SIMPLEX,
                    0.65,
                    cv::Scalar(20, 20, 20),
                    1,
                    cv::LINE_AA);

        for (const auto& colored_path : paths)
        {
            std::vector<cv::Point> projected_points;
            projected_points.reserve(colored_path.path->poses.size());
            for (const auto& pose : colored_path.path->poses)
            {
                projected_points.push_back(project(positionCoordinates(pose.pose.position)));
            }
            cv::polylines(canvas, projected_points, false, colored_path.color, 2, cv::LINE_AA);

            const std::size_t cue_stride = std::max<std::size_t>(
                1U, colored_path.path->poses.size() / 10U);
            for (std::size_t sample = 0U; sample < colored_path.path->poses.size();
                 sample += cue_stride)
            {
                const auto& pose = colored_path.path->poses[sample].pose;
                const auto direction = orientationXAxis(pose.orientation);
                const double cue_horizontal = direction[projection.horizontal_axis];
                const double cue_vertical = direction[projection.vertical_axis];
                const double cue_norm = std::hypot(cue_horizontal, cue_vertical);
                if (cue_norm <= 1.0e-12)
                {
                    continue;
                }
                const auto origin = project(positionCoordinates(pose.position));
                const cv::Point endpoint{
                    origin.x + static_cast<int>(std::lround(12.0 * cue_horizontal / cue_norm)),
                    origin.y - static_cast<int>(std::lround(12.0 * cue_vertical / cue_norm)),
                };
                cv::arrowedLine(canvas,
                                origin,
                                endpoint,
                                colored_path.color,
                                1,
                                cv::LINE_AA,
                                0,
                                0.25);
            }
        }
    }

    return canvas;
}

auto boolText(bool value) -> const char*
{
    return value ? "true" : "false";
}

auto makeReceipt(const SRecorderConfig& config,
                 const SBenchmarkBundle& bundle,
                 const SCallbackCounts& counts,
                 const SBundleResult& result,
                 double callback_to_artifact_milliseconds) -> std::string
{
    const bool has_track = bundle.tracks.tracks.size() == 1U;
    const uint64_t track_id = has_track ? bundle.tracks.tracks.front().track_id : 0U;
    const std::size_t observation_count =
        has_track ? bundle.tracks.tracks.front().observations.size() : 0U;

    std::ostringstream receipt;
    receipt << std::fixed << std::setprecision(6);
    receipt << "{\n"
            << "  \"status\": \"" << (result.ok ? "ok" : "error") << "\",\n"
            << "  \"topic_root\": \"" << escapeJson(config.topic_root) << "\",\n"
            << "  \"callback_counts\": {\n"
            << "    \"image\": " << counts.image << ",\n"
            << "    \"tracks\": " << counts.tracks << ",\n"
            << "    \"reference_path\": " << counts.reference_path << ",\n"
            << "    \"online_path\": " << counts.online_path << ",\n"
            << "    \"smoothed_path\": " << counts.smoothed_path << "\n"
            << "  },\n"
            << "  \"image\": {\"width\": " << bundle.image.width
            << ", \"height\": " << bundle.image.height
            << ", \"encoding\": \"" << escapeJson(bundle.image.encoding) << "\"},\n"
            << "  \"track_id\": " << track_id << ",\n"
            << "  \"observation_count\": " << observation_count << ",\n"
            << "  \"path_lengths\": {\n"
            << "    \"reference\": " << bundle.reference_path.poses.size() << ",\n"
            << "    \"online\": " << bundle.online_path.poses.size() << ",\n"
            << "    \"smoothed\": " << bundle.smoothed_path.poses.size() << "\n"
            << "  },\n"
            << "  \"frame_agreement\": " << boolText(result.frame_ids_agree) << ",\n"
            << "  \"timestamp_agreement\": " << boolText(result.timestamps_agree) << ",\n"
            << "  \"quaternion_validity\": " << boolText(result.quaternions_valid) << ",\n"
            << "  \"quaternion_norm_tolerance\": "
            << CBenchmarkBundleProcessor::kQuaternionNormTolerance << ",\n"
            << "  \"callback_to_artifact_milliseconds\": "
            << callback_to_artifact_milliseconds << ",\n"
            << "  \"render_milliseconds\": " << result.render_milliseconds << ",\n"
            << "  \"error\": \"" << escapeJson(result.error) << "\"\n"
            << "}\n";
    return receipt.str();
}

void validatePath(const nav_msgs::msg::Path& path,
                  std::string_view path_name,
                  const std::string& common_frame_id,
                  std::size_t expected_length,
                  SBundleResult& result)
{
    if (path.poses.size() != expected_length)
    {
        setFirstError(result, std::string(path_name) + " path length does not match expectation");
    }
    if (path.header.frame_id.empty() || path.header.frame_id != common_frame_id)
    {
        result.frame_ids_agree = false;
        setFirstError(result, std::string(path_name) + " path frame IDs do not agree");
    }

    TStamp previous_stamp{};
    bool has_previous_stamp = false;
    for (const auto& pose : path.poses)
    {
        if (pose.header.frame_id != common_frame_id)
        {
            result.frame_ids_agree = false;
            setFirstError(result, std::string(path_name) + " pose frame IDs do not agree");
        }
        if (has_previous_stamp && stampLess(pose.header.stamp, previous_stamp))
        {
            result.timestamps_agree = false;
            setFirstError(result, std::string(path_name) + " pose timestamps are not nondecreasing");
        }
        previous_stamp = pose.header.stamp;
        has_previous_stamp = true;

        const auto& position = pose.pose.position;
        const auto& quaternion = pose.pose.orientation;
        if (!finite(position.x) || !finite(position.y) || !finite(position.z) ||
            !finite(quaternion.x) || !finite(quaternion.y) || !finite(quaternion.z) ||
            !finite(quaternion.w))
        {
            setFirstError(result, std::string(path_name) + " contains nonfinite pose values");
        }

        const double norm = std::sqrt(quaternion.x * quaternion.x +
                                      quaternion.y * quaternion.y +
                                      quaternion.z * quaternion.z +
                                      quaternion.w * quaternion.w);
        if (!finite(norm) || std::abs(norm - 1.0) >
                                 CBenchmarkBundleProcessor::kQuaternionNormTolerance)
        {
            result.quaternions_valid = false;
            setFirstError(result, std::string(path_name) + " quaternion is not normalized");
        }
    }
}

} // namespace

CBenchmarkBundleProcessor::CBenchmarkBundleProcessor(SRecorderConfig config)
    : config_(std::move(config))
{
    if (config_.expected_path_length == 0U ||
        config_.expected_track_observations == 0U)
    {
        throw std::invalid_argument("expected bundle sizes must be positive");
    }
}

auto CBenchmarkBundleProcessor::isComplete(const SBenchmarkBundle& bundle) const -> bool
{
    const auto& stamp = bundle.image.header.stamp;
    return stampsEqual(stamp, bundle.tracks.header.stamp) &&
           stampsEqual(stamp, bundle.reference_path.header.stamp) &&
           stampsEqual(stamp, bundle.online_path.header.stamp) &&
           stampsEqual(stamp, bundle.smoothed_path.header.stamp) &&
           bundle.tracks.tracks.size() == 1U &&
           bundle.tracks.tracks.front().observations.size() ==
               config_.expected_track_observations &&
           bundle.reference_path.poses.size() == config_.expected_path_length &&
           bundle.online_path.poses.size() == config_.expected_path_length &&
           bundle.smoothed_path.poses.size() == config_.expected_path_length;
}

auto CBenchmarkBundleProcessor::validate(const SBenchmarkBundle& bundle) const -> SBundleResult
{
    SBundleResult result;

    if (bundle.image.encoding != "mono8")
    {
        setFirstError(result, "image encoding must be mono8");
    }
    if (bundle.image.width == 0U || bundle.image.height == 0U)
    {
        setFirstError(result, "image width and height must be nonzero");
    }
    if (bundle.image.step < bundle.image.width)
    {
        setFirstError(result, "image step is smaller than width");
    }
    const auto height = static_cast<std::size_t>(bundle.image.height);
    const auto step = static_cast<std::size_t>(bundle.image.step);
    if (height != 0U && step > std::numeric_limits<std::size_t>::max() / height)
    {
        setFirstError(result, "image data size calculation overflows");
    }
    else if (bundle.image.data.size() < step * height)
    {
        setFirstError(result, "image data does not cover step times height");
    }

    const auto& stamp = bundle.image.header.stamp;
    if (!stampsEqual(stamp, bundle.tracks.header.stamp) ||
        !stampsEqual(stamp, bundle.reference_path.header.stamp) ||
        !stampsEqual(stamp, bundle.online_path.header.stamp) ||
        !stampsEqual(stamp, bundle.smoothed_path.header.stamp))
    {
        result.timestamps_agree = false;
        setFirstError(result, "top-level bundle timestamps do not agree");
    }

    if (bundle.image.header.frame_id.empty() ||
        bundle.tracks.header.frame_id.empty() ||
        bundle.image.header.frame_id != bundle.tracks.header.frame_id)
    {
        result.frame_ids_agree = false;
        setFirstError(result, "image and feature-track frame IDs must be nonempty and agree");
    }

    if (bundle.tracks.tracks.size() != 1U)
    {
        setFirstError(result, "feature-track array must contain exactly one track");
    }
    else
    {
        const auto& track = bundle.tracks.tracks.front();
        if (track.track_id != config_.expected_track_id)
        {
            setFirstError(result, "feature track ID does not match expectation");
        }
        if (track.observations.size() != config_.expected_track_observations)
        {
            setFirstError(result, "feature track observation count does not match expectation");
        }
        for (std::size_t index = 0U; index < track.observations.size(); ++index)
        {
            const auto& observation = track.observations[index];
            if (!finite(observation.u) || !finite(observation.v))
            {
                setFirstError(result, "feature track contains nonfinite pixel coordinates");
            }
            if (index > 0U &&
                track.observations[index - 1U].frame_id >= observation.frame_id)
            {
                setFirstError(result, "feature track observations are not strictly chronological");
            }
        }
    }

    const std::string common_frame_id = bundle.reference_path.header.frame_id;
    if (common_frame_id.empty())
    {
        result.frame_ids_agree = false;
        setFirstError(result, "trajectory frame ID must be nonempty");
    }
    validatePath(bundle.reference_path,
                 "reference",
                 common_frame_id,
                 config_.expected_path_length,
                 result);
    validatePath(bundle.online_path,
                 "online",
                 common_frame_id,
                 config_.expected_path_length,
                 result);
    validatePath(bundle.smoothed_path,
                 "smoothed",
                 common_frame_id,
                 config_.expected_path_length,
                 result);

    result.ok = result.error.empty();
    return result;
}

void CBenchmarkBundleProcessor::writeReadyMarker() const
{
    if (config_.output_dir.empty())
    {
        throw std::invalid_argument("output_dir must be nonempty");
    }
    std::filesystem::create_directories(config_.output_dir);
    std::ostringstream marker;
    marker << "{\n"
           << "  \"status\": \"ready\",\n"
           << "  \"topic_root\": \"" << escapeJson(config_.topic_root) << "\"\n"
           << "}\n";
    writeTextAtomic(config_.output_dir / "ready.json", marker.str());
}

auto CBenchmarkBundleProcessor::writeArtifacts(
    const SBenchmarkBundle& bundle,
    const SCallbackCounts& callback_counts,
    double callback_to_processing_entry_milliseconds) const -> SBundleResult
{
    const auto processing_entry = std::chrono::steady_clock::now();
    if (config_.output_dir.empty())
    {
        return {
            .ok = false,
            .error = "output_dir must be nonempty",
        };
    }
    std::filesystem::create_directories(config_.output_dir);

    auto result = validate(bundle);
    if (result.ok)
    {
        const auto render_start = std::chrono::steady_clock::now();
        try
        {
            writePngAtomic(config_.output_dir / "annotated_image.png",
                           renderAnnotatedImage(bundle));
            writePngAtomic(config_.output_dir / "camera_paths.png",
                           renderCameraPaths(bundle));
        }
        catch (const std::exception& exception)
        {
            result.ok = false;
            result.error = exception.what();
        }
        const auto render_stop = std::chrono::steady_clock::now();
        result.render_milliseconds =
            std::chrono::duration<double, std::milli>(render_stop - render_start).count();
    }

    const auto artifact_completion = std::chrono::steady_clock::now();
    const double processing_to_artifact_milliseconds =
        std::chrono::duration<double, std::milli>(artifact_completion - processing_entry).count();
    const double callback_to_artifact_milliseconds =
        callback_to_processing_entry_milliseconds + processing_to_artifact_milliseconds;
    try
    {
        writeTextAtomic(config_.output_dir / "receipt.json",
                        makeReceipt(config_,
                                    bundle,
                                    callback_counts,
                                    result,
                                    callback_to_artifact_milliseconds));
    }
    catch (const std::exception& exception)
    {
        result.ok = false;
        result.error = exception.what();
    }
    return result;
}

} // namespace eval_and_viz_gears_ros
