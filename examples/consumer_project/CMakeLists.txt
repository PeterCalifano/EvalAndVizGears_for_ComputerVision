cmake_minimum_required(VERSION 3.15 FATAL_ERROR)

project(eval_and_viz_consumer VERSION 0.1.0 LANGUAGES CXX)

find_package(EvalAndVizGears_for_ComputerVision CONFIG REQUIRED)

add_executable(eval_and_viz_consumer example_project.cpp)
target_link_libraries(
  eval_and_viz_consumer
  PRIVATE EvalAndVizGears_for_ComputerVision::EvalAndVizGears_for_ComputerVision)
