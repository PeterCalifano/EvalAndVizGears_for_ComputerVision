/// @file
/// @brief Catch2 coverage for viztools::CFeatureTrackSnapshotAdapter.

#include "core/CFeatureTrackSnapshotAdapter.h"

#include <bit>
#include <cstdint>

#include <catch2/catch_test_macros.hpp>

using namespace viztools;

TEST_CASE("CFeatureTrackSnapshotAdapter reverses chronological observations", "[core][feature-track]")
{
    const slam_primitives::SFeatureTrackSnapshot snapshot{
        .track_id = slam_primitives::CFeatureTrackID{7},
        .observations = {
            {.frame_id = slam_primitives::CFrameID{10}, .location = {.u = 10.25, .v = 20.5}},
            {.frame_id = slam_primitives::CFrameID{11}, .location = {.u = 30.75, .v = 40.125}},
            {.frame_id = slam_primitives::CFrameID{12}, .location = {.u = 50.5, .v = 60.25}},
        },
        .is_terminated = false,
    };

    const auto trail = CFeatureTrackSnapshotAdapter::toNewestFirstTrail(snapshot);

    REQUIRE(trail.size() == 3);
    REQUIRE(trail[0] == cv::Point2f{50.5F, 60.25F});
    REQUIRE(trail[1] == cv::Point2f{30.75F, 40.125F});
    REQUIRE(trail[2] == cv::Point2f{10.25F, 20.5F});
}

TEST_CASE("CFeatureTrackSnapshotAdapter accepts empty snapshots", "[core][feature-track]")
{
    const slam_primitives::SFeatureTrackSnapshot snapshot{
        .track_id = slam_primitives::CFeatureTrackID{0},
    };

    const auto trail = CFeatureTrackSnapshotAdapter::toNewestFirstTrail(snapshot);

    REQUIRE(trail.empty());
}

TEST_CASE("CFeatureTrackSnapshotAdapter does not mutate the source snapshot", "[core][feature-track]")
{
    const slam_primitives::SFeatureTrackSnapshot snapshot{
        .track_id = slam_primitives::CFeatureTrackID{(std::uint64_t{1} << 53) + 42},
        .observations = {
            {.frame_id = slam_primitives::CFrameID{3}, .location = {.u = 1.0, .v = 2.0}},
            {.frame_id = slam_primitives::CFrameID{4}, .location = {.u = 3.0, .v = 4.0}},
        },
        .is_terminated = true,
    };

    static_cast<void>(CFeatureTrackSnapshotAdapter::toNewestFirstTrail(snapshot));

    REQUIRE(snapshot.track_id == slam_primitives::CFeatureTrackID{(std::uint64_t{1} << 53) + 42});
    REQUIRE(snapshot.is_terminated);
    REQUIRE(snapshot.observations.size() == 2);
    REQUIRE(snapshot.observations[0].frame_id == slam_primitives::CFrameID{3});
    REQUIRE(std::bit_cast<std::uint64_t>(snapshot.observations[0].location.u) ==
            std::bit_cast<std::uint64_t>(1.0));
    REQUIRE(std::bit_cast<std::uint64_t>(snapshot.observations[0].location.v) ==
            std::bit_cast<std::uint64_t>(2.0));
    REQUIRE(snapshot.observations[1].frame_id == slam_primitives::CFrameID{4});
    REQUIRE(std::bit_cast<std::uint64_t>(snapshot.observations[1].location.u) ==
            std::bit_cast<std::uint64_t>(3.0));
    REQUIRE(std::bit_cast<std::uint64_t>(snapshot.observations[1].location.v) ==
            std::bit_cast<std::uint64_t>(4.0));
}
