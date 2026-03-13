/// @file
/// @brief Catch2 coverage for viztools::CTrackingStatsLogger.

#include <catch2/catch_test_macros.hpp>
#include "core/CTrackingStatsLogger.h"

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

using namespace viztools;

TEST_CASE("CTrackingStatsLogger default is empty", "[core][stats]")
{
    CTrackingStatsLogger logger;
    REQUIRE(logger.size() == 0);
    REQUIRE(logger.entries().empty());
}

TEST_CASE("CTrackingStatsLogger record increases size", "[core][stats]")
{
    CTrackingStatsLogger logger;

    SFrameStats s1{.frame_id = 0, .num_tracked = 100, .num_lost = 5};
    SFrameStats s2{.frame_id = 1, .num_tracked = 95, .num_lost = 3};

    logger.record(s1);
    REQUIRE(logger.size() == 1);

    logger.record(s2);
    REQUIRE(logger.size() == 2);
}

TEST_CASE("CTrackingStatsLogger entries stored correctly", "[core][stats]")
{
    CTrackingStatsLogger logger;

    SFrameStats s{.frame_id = 42, .num_tracked = 200, .num_lost = 10,
                  .num_new = 5, .is_keyframe = true, .cumulative_features = 300};
    logger.record(s);

    const auto &entries = logger.entries();
    REQUIRE(entries.size() == 1);
    REQUIRE(entries[0].frame_id == 42);
    REQUIRE(entries[0].num_tracked == 200);
    REQUIRE(entries[0].num_lost == 10);
    REQUIRE(entries[0].num_new == 5);
    REQUIRE(entries[0].is_keyframe == true);
    REQUIRE(entries[0].cumulative_features == 300);
}

TEST_CASE("CTrackingStatsLogger clear empties entries", "[core][stats]")
{
    CTrackingStatsLogger logger;
    logger.record({.frame_id = 0});
    logger.record({.frame_id = 1});
    REQUIRE(logger.size() == 2);

    logger.clear();
    REQUIRE(logger.size() == 0);
    REQUIRE(logger.entries().empty());
}

TEST_CASE("CTrackingStatsLogger writeCsv produces valid CSV", "[core][stats]")
{
    CTrackingStatsLogger logger;
    logger.record({.frame_id = 0, .num_tracked = 100, .num_lost = 2,
                   .num_new = 10, .is_keyframe = true, .cumulative_features = 110});
    logger.record({.frame_id = 1, .num_tracked = 98, .num_lost = 3,
                   .num_new = 0, .is_keyframe = false, .cumulative_features = 110});

    std::string path = "/tmp/viztools_test_stats.csv";
    REQUIRE(logger.writeCsv(path) == true);

    // Read back and verify
    std::ifstream ifs(path);
    REQUIRE(ifs.is_open());

    std::string header;
    std::getline(ifs, header);
    REQUIRE(header == "frame_id,num_tracked,num_lost,num_new,is_keyframe,cumulative_features");

    std::string line1;
    std::getline(ifs, line1);
    REQUIRE(line1 == "0,100,2,10,1,110");

    std::string line2;
    std::getline(ifs, line2);
    REQUIRE(line2 == "1,98,3,0,0,110");

    // Clean up
    std::remove(path.c_str());
}

TEST_CASE("CTrackingStatsLogger writeCsv fails on invalid path", "[core][stats]")
{
    CTrackingStatsLogger logger;
    logger.record({.frame_id = 0});

    REQUIRE(logger.writeCsv("/nonexistent/directory/file.csv") == false);
}
