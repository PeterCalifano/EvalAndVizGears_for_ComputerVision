cmake_minimum_required(VERSION 3.16)

project(eval_and_viz_gears_colcon_shim LANGUAGES NONE)

get_filename_component(EVAL_AND_VIZ_GEARS_REPOSITORY_ROOT
  "${CMAKE_CURRENT_LIST_DIR}/../.."
  ABSOLUTE)

option(EVAL_AND_VIZ_GEARS_ENABLE_CUDA
  "Enable CUDA support in the EvalAndVizGears core" OFF)

set(EvalAndVizGears_for_ComputerVision_ENABLE_CUDA
  "${EVAL_AND_VIZ_GEARS_ENABLE_CUDA}"
  CACHE BOOL "Enable CUDA support in the EvalAndVizGears core" FORCE)
set(ENABLE_TESTS OFF CACHE BOOL
  "Disable standalone tests in the ROS 2 overlay build" FORCE)
set(ENABLE_FETCH_CATCH2 OFF CACHE BOOL
  "Do not fetch Catch2 while building the ROS 2 overlay" FORCE)
set(EvalAndVizGears_for_ComputerVision_BUILD_PROGRAMS OFF CACHE BOOL
  "Disable standalone programs in the ROS 2 overlay build" FORCE)
set(EvalAndVizGears_for_ComputerVision_BUILD_EXAMPLES OFF CACHE BOOL
  "Disable standalone examples in the ROS 2 overlay build" FORCE)

# Root helpers must resolve against the owning repository when it is nested
# below this colcon shim.
list(PREPEND CMAKE_MODULE_PATH
  "${EVAL_AND_VIZ_GEARS_REPOSITORY_ROOT}/cmake")

add_subdirectory(
  "${EVAL_AND_VIZ_GEARS_REPOSITORY_ROOT}"
  "${CMAKE_CURRENT_BINARY_DIR}/eval_and_viz_gears_core")
