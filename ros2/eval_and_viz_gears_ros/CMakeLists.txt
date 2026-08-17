cmake_minimum_required(VERSION 3.16)
project(eval_and_viz_gears_ros VERSION 0.2.0 LANGUAGES CXX)

option(EVAL_AND_VIZ_GEARS_ENABLE_CUDA
  "Accepted for workspace-wide build helper compatibility" OFF)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(slam_primitives_interfaces REQUIRED)
find_package(OpenCV REQUIRED COMPONENTS core imgproc imgcodecs)
find_package(EvalAndVizGears_for_ComputerVision CONFIG REQUIRED)

add_library(benchmark_bundle_processor STATIC
  src/CBenchmarkBundleProcessor.cpp)
target_compile_features(benchmark_bundle_processor PUBLIC cxx_std_20)
target_include_directories(benchmark_bundle_processor PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_link_libraries(benchmark_bundle_processor
  EvalAndVizGears_for_ComputerVision::EvalAndVizGears_for_ComputerVision
  opencv_core
  opencv_imgproc
  opencv_imgcodecs)
ament_target_dependencies(benchmark_bundle_processor
  sensor_msgs
  nav_msgs
  std_msgs
  slam_primitives_interfaces)

add_executable(timing_ros2_interfaces_recorder
  src/timing_ros2_interfaces_recorder.cpp)
target_compile_features(timing_ros2_interfaces_recorder PRIVATE cxx_std_20)
target_link_libraries(timing_ros2_interfaces_recorder
  benchmark_bundle_processor)
ament_target_dependencies(timing_ros2_interfaces_recorder
  rclcpp
  sensor_msgs
  nav_msgs
  std_msgs
  slam_primitives_interfaces)

install(
  TARGETS timing_ros2_interfaces_recorder
  RUNTIME DESTINATION lib/${PROJECT_NAME})

ament_package()
