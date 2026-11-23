cmake_minimum_required(VERSION 3.15 FATAL_ERROR)
if(POLICY CMP0144)
  cmake_policy(SET CMP0144 NEW)
endif()

set(PROJECT_PYTHON_VERSION 3.12)
set(MATLAB_DEFAULT_RELEASE "R2024b")

set(project_name "EvalAndVizGears_for_ComputerVision")
set(project_description
    "C++/CUDA computer-vision evaluation and visualization library with optional Python and MATLAB wrappers")
set(project_homepage_url "https://github.com/PeterCalifano/EvalAndVizGears_for_ComputerVision")
set(PROJECT_MAINTAINER_NAME "Pietro Califano" CACHE STRING "Project maintainer name")
set(PROJECT_MAINTAINER_EMAIL "petercalifano.gs@gmail.com" CACHE STRING "Project maintainer email")
set(PROJECT_LICENSE "MIT" CACHE STRING "Project SPDX license identifier")

# Resolve ownership before language and feature selection. Nested colcon builds
# must not consume unrelated generic cache options from their parent workspace.
set(BUILD_AS_MAIN_PROJECT OFF)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  set(BUILD_AS_MAIN_PROJECT ON)
endif()

if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "${CMAKE_SOURCE_DIR}/install" CACHE PATH "Install path" FORCE)
endif()

set(METADATA_ONLY_OPTION_NAME "${project_name}_METADATA_ONLY")
set(ENABLE_CUDA_OPTION_NAME "${project_name}_ENABLE_CUDA")

function(_eval_and_viz_migrate_top_level_bool_option_alias
         legacy_option canonical_option option_help)
  if(NOT BUILD_AS_MAIN_PROJECT)
    return()
  endif()

  get_property(_legacy_alias_is_cached
      CACHE "${legacy_option}" PROPERTY TYPE SET)
  if(NOT _legacy_alias_is_cached)
    return()
  endif()

  set("${canonical_option}" "${${legacy_option}}"
      CACHE BOOL "${option_help}" FORCE)
  unset("${legacy_option}" CACHE)
endfunction()

_eval_and_viz_migrate_top_level_bool_option_alias(
    PROJECT_METADATA_ONLY "${METADATA_ONLY_OPTION_NAME}"
    "Configure only project identity and version metadata")
_eval_and_viz_migrate_top_level_bool_option_alias(
    ENABLE_CUDA "${ENABLE_CUDA_OPTION_NAME}" "Enable CUDA")

option(${METADATA_ONLY_OPTION_NAME}
       "Configure only project identity and version metadata" OFF)
option(${ENABLE_CUDA_OPTION_NAME} "Enable CUDA" OFF)

# Retained modules use these directory-local spellings. They are deliberately
# not cache entries, so a parent project cannot select target features.
set(PROJECT_METADATA_ONLY "${${METADATA_ONLY_OPTION_NAME}}")
set(ENABLE_CUDA "${${ENABLE_CUDA_OPTION_NAME}}")

if(PROJECT_METADATA_ONLY)
  set(languages NONE)
else()
  set(languages CXX)
  if(ENABLE_CUDA)
    list(APPEND languages CUDA)
  endif()
endif()

include(cmake/HandleGitVersion.cmake)
set(PROJECT_VERSION_MAJOR 0)
set(PROJECT_VERSION_MINOR 0)
set(PROJECT_VERSION_PATCH 0)
set(PROJECT_VERSION_PRERELEASE "")
set(PROJECT_VERSION_METADATA "")
set(PROJECT_VERSION_CORE "${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}.${PROJECT_VERSION_PATCH}")
resolve_project_version()

project(${project_name}
        VERSION ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}.${PROJECT_VERSION_PATCH}
        DESCRIPTION "${project_description}"
        HOMEPAGE_URL "${project_homepage_url}"
        LANGUAGES ${languages})

if(PROJECT_METADATA_ONLY)
  return()
endif()

option(BUILD_SHARED_LIBS "Build libraries as shared" ON)
include(cmake/HandleOpenMP.cmake)
list(APPEND CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake")

option(WRITE_SOURCE_VERSION_FILE "Write VERSION into the source tree during CMake configure" OFF)
if(WRITE_SOURCE_VERSION_FILE)
  write_source_VERSION_file()
endif()
write_build_VERSION_file()
install(FILES "${PROJECT_BINARY_DIR}/VERSION" DESTINATION ".")

set(LIB_NAMESPACE "${PROJECT_NAME}")
if(DEFINED LIB_NAMESPACE_OVERRIDE)
  set(LIB_NAMESPACE "${LIB_NAMESPACE_OVERRIDE}")
endif()
set(LIB_TARGET_NAME "${project_name}")
if(DEFINED LIB_TARGET_NAME_OVERRIDE)
  set(LIB_TARGET_NAME "${LIB_TARGET_NAME_OVERRIDE}")
endif()

set(CUDA_COMPILE_TARGET "${LIB_NAMESPACE}_cuda_compile_interface")
set(OPENGL_COMPILE_TARGET "${LIB_NAMESPACE}_opengl_compile_interface")
set(LIB_COMPILE_TARGET "${LIB_NAMESPACE}_lib_compile_interface")
set(SANITIZER_TARGET "${LIB_NAMESPACE}_sanitizer_target_interface")
set(PROFILING_COMPILE_TARGET "${LIB_NAMESPACE}_profiling_interface")
set(BUILD_PROGRAMS_OPTION_NAME "${LIB_NAMESPACE}_BUILD_PROGRAMS")
set(BUILD_EXAMPLES_OPTION_NAME "${LIB_NAMESPACE}_BUILD_EXAMPLES")

include(cmake/toolchains/HandleToolchain.cmake)
include(cmake/HandleCustomTargets.cmake)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE "RelWithDebInfo" CACHE STRING
      "Build type (Debug, Release, RelWithDebInfo, MinSizeRel, NOPTIM)" FORCE)
endif()
string(TOLOWER "${CMAKE_BUILD_TYPE}" CMAKE_BUILD_TYPE_LOWER)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_BINARY_DIR)
  message(FATAL_ERROR "In-source builds are not supported")
endif()

include(GNUInstallDirs)
include(ExternalProject)
include(cmake/HandleCUDA.cmake)
include(cmake/HandleTBB.cmake)
include(cmake/HandlePython.cmake)
if(BUILD_AS_MAIN_PROJECT)
  include(cmake/HandleWrapper.cmake)
endif()

option(ENABLE_TESTS "Build and run tests" ON)
option(ENABLE_PYTHON_TESTS "Discover and register Python pytest tests through CTest" ON)
option(ENABLE_FETCH_CATCH2 "Fetch Catch2 from GitHub if not found" ON)
option(${BUILD_PROGRAMS_OPTION_NAME} "Build project program targets when this project is the main project" ON)
option(${BUILD_EXAMPLES_OPTION_NAME} "Build project example targets when this project is the main project" ON)
option(VERBOSE "Enable verbose project diagnostics" OFF)

set(CATCH2_TEST_REPORTER "compact" CACHE STRING "Catch2 reporter; empty uses Catch2 defaults")
set(CATCH2_TEST_PROPERTIES "LABELS;catch2" CACHE STRING "CTest properties for discovered Catch2 tests")
set(PYTHON_TEST_RUNNER "pytest" CACHE STRING "Python test runner used for test*.py files")
set_property(CACHE PYTHON_TEST_RUNNER PROPERTY STRINGS pytest)
set(PYTHON_TEST_EXECUTABLE "" CACHE FILEPATH "Python executable used for tests outside conda")
set(PYTHON_TEST_CONDA_ENV "" CACHE STRING "Optional conda environment name used for Python tests")
set(PYTHON_TEST_CONDA_PREFIX "" CACHE PATH "Optional conda environment prefix used for Python tests")
set(PYTHON_TEST_CONDA_EXECUTABLE "conda" CACHE STRING "Conda executable used for Python tests")

if(BUILD_AS_MAIN_PROJECT AND ENABLE_TESTS)
  include(CTest)
endif()

if(NOT DEFINED GTWRAP_BUILD_PYTHON_DEFAULT)
  set(GTWRAP_BUILD_PYTHON_DEFAULT OFF CACHE BOOL "Default Python wrapper setting for subprojects")
endif()
if(NOT DEFINED GTWRAP_BUILD_MATLAB_DEFAULT)
  set(GTWRAP_BUILD_MATLAB_DEFAULT OFF CACHE BOOL "Default MATLAB wrapper setting for subprojects")
endif()
set(GTWRAP_PYTHON_OPTION_NAME "${LIB_NAMESPACE}_BUILD_PYTHON_WRAPPER")
set(GTWRAP_MATLAB_OPTION_NAME "${LIB_NAMESPACE}_BUILD_MATLAB_WRAPPER")
set(GTWRAP_INTERFACE_OPTION_NAME "${LIB_NAMESPACE}_WRAPPER_INTERFACE_FILES")
set(GTWRAP_TOP_NAMESPACE_OPTION_NAME "${LIB_NAMESPACE}_GTWRAP_TOP_NAMESPACE")
set(GTWRAP_DEPENDENCIES_OPTION_NAME "${LIB_NAMESPACE}_GTWRAP_DEPENDENCY_TARGETS")
set(GTWRAP_RUNTIME_DEPENDENCIES_OPTION_NAME
    "${LIB_NAMESPACE}_GTWRAP_RUNTIME_DEPENDENCY_TARGETS")
set(GTWRAP_ROOT_OPTION_NAME "${LIB_NAMESPACE}_GTWRAP_ROOT_DIR")
option(${GTWRAP_PYTHON_OPTION_NAME} "Build Python wrapper" ${GTWRAP_BUILD_PYTHON_DEFAULT})
option(${GTWRAP_MATLAB_OPTION_NAME} "Build MATLAB wrapper" ${GTWRAP_BUILD_MATLAB_DEFAULT})

if(NOT DEFINED ${GTWRAP_INTERFACE_OPTION_NAME})
  set(${GTWRAP_INTERFACE_OPTION_NAME} "${PROJECT_SOURCE_DIR}/src/wrap_interface.i"
      CACHE STRING "Ordered gtwrap interface files" FORCE)
endif()
if(NOT DEFINED ${GTWRAP_TOP_NAMESPACE_OPTION_NAME})
  set(${GTWRAP_TOP_NAMESPACE_OPTION_NAME} "viztools"
      CACHE STRING "Top namespace used for gtwrap code generation" FORCE)
endif()
if(NOT DEFINED ${GTWRAP_DEPENDENCIES_OPTION_NAME})
  set(${GTWRAP_DEPENDENCIES_OPTION_NAME} ""
      CACHE STRING "Additional dependency targets required before wrapping" FORCE)
endif()
if(NOT DEFINED ${GTWRAP_RUNTIME_DEPENDENCIES_OPTION_NAME})
  set(${GTWRAP_RUNTIME_DEPENDENCIES_OPTION_NAME} ""
      CACHE STRING
      "Direct project-owned shared runtime targets packaged beside the Python wrapper"
      FORCE)
endif()
if(NOT DEFINED ${GTWRAP_ROOT_OPTION_NAME})
  set(${GTWRAP_ROOT_OPTION_NAME} ""
      CACHE PATH "Optional path to a local gtwrap checkout" FORCE)
endif()

option(NO_OPTIMIZATION "Disable optimization flags" OFF)
option(WARNINGS_ARE_ERRORS "Treat warnings as errors" OFF)
option(SANITIZE_BUILD "Enable sanitizers in build" OFF)
set(SANITIZERS "address,undefined,leak" CACHE STRING "Sanitizers enabled by SANITIZE_BUILD")
option(ENABLE_TBB "Enable Intel oneTBB support" OFF)
option(CPU_ENABLE_NATIVE_TUNING "Enable host-native CPU tuning" ON)
option(CPU_ENABLE_FMA "Enable CPU FMA instructions" OFF)
option(CPU_ENABLE_SIMD "Enable explicit SIMD ISA flags" OFF)
set(CPU_SIMD_LEVEL "native" CACHE STRING "SIMD ISA: native,sse4.2,avx,avx2,avx512f")
set_property(CACHE CPU_SIMD_LEVEL PROPERTY STRINGS native sse4.2 avx avx2 avx512f)
set(CPU_EXTRA_OPT_FLAGS "" CACHE STRING "Additional CPU optimization flags")
option(CUDA_ENABLE_FMAD "Enable fused multiply-add contraction in NVCC" ON)
option(CUDA_ENABLE_EXTRA_DEVICE_VECTORIZATION "Enable NVCC extra device vectorization" OFF)
option(CUDA_USE_FAST_MATH "Enable NVCC fast math" OFF)
set(CUDA_NVCC_EXTRA_FLAGS "" CACHE STRING "Additional NVCC flags")
set(EXTRA_C_FLAGS "" CACHE STRING "Additional C compiler flags")
set(EXTRA_CXX_FLAGS "" CACHE STRING "Additional C++ compiler flags")
set(PYTHON_EXECUTABLE "python3" CACHE STRING "Python executable used by wrapper tooling")

include(cmake/HandleCompilerFlags.cmake)
handle_compiler_flags(CXX_STANDARD 20)
handle_openmp()
include(cmake/HandleSanitizers.cmake)
handle_sanitizers()
include(cmake/HandleProfiling.cmake)
option(PROFILING_PROPAGATES_TO_CONSUMERS
       "Propagate profiling usage requirements to consumers" OFF)
handle_profiling(TARGET ${PROFILING_COMPILE_TARGET})

if(WARNINGS_ARE_ERRORS)
  add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Werror>)
endif()

message(STATUS "==============================================================")
message(STATUS "====================  Dependencies ===========================")
find_package(Eigen3 3.4 REQUIRED)
find_package(OpenCV REQUIRED COMPONENTS core imgproc highgui imgcodecs)
find_package(slam-primitives CONFIG REQUIRED)
find_package(Doxygen QUIET)

include(cmake/HandleCatch2.cmake)
include(cmake/cmake_utils.cmake)
handle_cuda(TARGET ${CUDA_COMPILE_TARGET} MIN_VERSION 12.0)
include(cmake/HandleOpenGL.cmake)
handle_opengl(TARGET ${OPENGL_COMPILE_TARGET})
include(cmake/HandleSubmodules.cmake)
handle_submodules()

set(EXPORT_TARGET_DEPS Eigen3 OpenCV slam-primitives)
if(ENABLE_CUDA)
  list(APPEND EXPORT_TARGET_DEPS CUDAToolkit)
endif()
if(ENABLE_OPENGL)
  list(APPEND EXPORT_TARGET_DEPS OpenGL)
endif()
if(ENABLE_TBB)
  list(APPEND EXPORT_TARGET_DEPS TBB)
endif()

add_library(${LIB_COMPILE_TARGET} INTERFACE)
handle_toolchain(TARGET ${LIB_COMPILE_TARGET})
handle_tbb(TARGET ${LIB_COMPILE_TARGET})
handle_compiler_flags_interface(TARGET ${LIB_COMPILE_TARGET})

set(installable_targets)
add_library(${project_name}_include INTERFACE)
target_include_directories(${project_name}_include INTERFACE
    $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/src>
    $<INSTALL_INTERFACE:include/${project_name}>)
target_link_options(${project_name}_include INTERFACE
    $<$<PLATFORM_ID:Linux>:-Wl,-rpath,\$ORIGIN/../lib>)
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH ON)
include_directories(lib/header_only)

message(STATUS "==============================================================")
message(STATUS "====================  Library composition ====================")
add_subdirectory(src)

if(BUILD_AS_MAIN_PROJECT AND ${${BUILD_EXAMPLES_OPTION_NAME}})
  add_subdirectory(examples)
endif()
if(ENABLE_TESTS AND BUILD_AS_MAIN_PROJECT)
  add_subdirectory(tests)
endif()
if(BUILD_AS_MAIN_PROJECT AND DOXYGEN_FOUND)
  add_subdirectory(doc)
endif()

set(ANY_WRAPPER_ENABLED OFF)
if(BUILD_AS_MAIN_PROJECT)
  set(LIBNAME_WRAP_TARGET ${LIB_TARGET_NAME})
  handle_gtwrappers()
  if(${GTWRAP_PYTHON_OPTION_NAME} OR ${GTWRAP_MATLAB_OPTION_NAME})
    set(ANY_WRAPPER_ENABLED ON)
  endif()
endif()

message(STATUS "==============================================================")
message(STATUS "================ Configuration Summary =======================")
message(STATUS "Project                                    : ${PROJECT_NAME} ${FULL_VERSION}")
message(STATUS "Library target                             : ${LIB_TARGET_NAME} (${PROJECT_LIBRARY_KIND})")
message(STATUS "Build programs                             : ${${BUILD_PROGRAMS_OPTION_NAME}}")
message(STATUS "Build examples                             : ${${BUILD_EXAMPLES_OPTION_NAME}}")
message(STATUS "Python tests                               : ${ENABLE_PYTHON_TESTS}")
message(STATUS "CUDA                                       : ${ENABLE_CUDA}")
message(STATUS "OpenCV                                     : ${OpenCV_VERSION}")
message(STATUS "TBB                                        : ${ENABLE_TBB}")
message(STATUS "Install prefix                             : ${CMAKE_INSTALL_PREFIX}")
print_compiler_flags_summary()
message(STATUS "==============================================================")

set(CTEST_PROJECT_NAME ${project_name})
set(CTEST_NIGHTLY_START_TIME "00:00:00 CET")

include(InstallRequiredSystemLibraries)
set(CPACK_RESOURCE_FILE_LICENSE "${PROJECT_SOURCE_DIR}/LICENSE")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "${PROJECT_DESCRIPTION}")
set(CPACK_PACKAGE_HOMEPAGE_URL "${PROJECT_HOMEPAGE_URL}")
set(CPACK_PACKAGE_VENDOR "${PROJECT_MAINTAINER_NAME}")
set(CPACK_PACKAGE_CONTACT "${PROJECT_MAINTAINER_NAME} <${PROJECT_MAINTAINER_EMAIL}>")
set(CPACK_PACKAGE_VERSION_MAJOR "${PROJECT_VERSION_MAJOR}")
set(CPACK_PACKAGE_VERSION_MINOR "${PROJECT_VERSION_MINOR}")
set(CPACK_PACKAGE_VERSION_PATCH "${PROJECT_VERSION_PATCH}")
if(DEFINED FULL_VERSION AND NOT "${FULL_VERSION}" STREQUAL "")
  set(CPACK_PACKAGE_FILE_NAME "${project_name}-${FULL_VERSION}")
  set(CPACK_SOURCE_PACKAGE_FILE_NAME "${project_name}-${FULL_VERSION}-source")
endif()
set(CPACK_GENERATOR "TGZ")
set(CPACK_SOURCE_GENERATOR "TGZ")
set(CPACK_VERBATIM_VARIABLES YES)
set(_cpack_source_root_regex "${PROJECT_SOURCE_DIR}")
string(
  REGEX REPLACE "([][+.*^$()|?\\\\])" "\\\\\\1"
  _cpack_source_root_regex "${_cpack_source_root_regex}")
set(_cpack_binary_root_regex "${CMAKE_BINARY_DIR}")
string(
  REGEX REPLACE "([][+.*^$()|?\\\\])" "\\\\\\1"
  _cpack_binary_root_regex "${_cpack_binary_root_regex}")
list(APPEND CPACK_SOURCE_IGNORE_FILES
    "^${_cpack_source_root_regex}/(.*/)?\\.git(/|$)"
    "^${_cpack_source_root_regex}/(.*/)?\\.codex(/|$)"
    "^${_cpack_source_root_regex}/\\.vscode(/|$)"
    "^${_cpack_source_root_regex}/(.*/)?\\.mypy_cache/"
    "^${_cpack_source_root_regex}/(.*/)?\\.pytest_cache/"
    "^${_cpack_source_root_regex}/(.*/)?\\.ruff_cache(/|$)"
    "^${_cpack_source_root_regex}/(.*/)?__pycache__/"
    "^${_cpack_source_root_regex}/build[^/]*/"
    "^${_cpack_source_root_regex}/(.*/)?build(/|$)"
    "^${_cpack_source_root_regex}/(.*/)?install[^/]*/"
    "^${_cpack_source_root_regex}/(.*/)?log(/|$)"
    "^${_cpack_source_root_regex}/output_data/"
    "^${_cpack_source_root_regex}/ros2/(build|install|log)/"
    "^${_cpack_source_root_regex}/(.*/)?codegen/"
    "^${_cpack_source_root_regex}/(.*/)?slprj/"
    "^${_cpack_source_root_regex}/(.*/)?[^/]+_ert_rtw(/|$)"
    "^${_cpack_source_root_regex}/matlab/mex/"
    "^${_cpack_source_root_regex}/.*\\.(mexa64|mexw64|mexmaci64)$"
    "^${_cpack_source_root_regex}/.*\\.code-workspace$"
    "^${_cpack_source_root_regex}/.*\\.py[cod]$"
    "^${_cpack_source_root_regex}/python/(build|dist)/"
    "^${_cpack_source_root_regex}/python/[^/]+\\.egg-info/"
    "^${_cpack_source_root_regex}/tools/plotjuggler/(dist|[^/]+\\.egg-info)(/|$)"
    "^${_cpack_source_root_regex}/python/(setup\\.py|pyproject\\.toml)$"
    "^${_cpack_source_root_regex}/python/[^/]+/_wrapper_build\\.py$"
    "^${_cpack_source_root_regex}/python/.*\\.(so(\\..*)?|pyd|dylib|dll)$"
    "^${_cpack_binary_root_regex}(/|$)")
include(CPack)
