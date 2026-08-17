# CMAKE script containing utility functions for cmake configuration
include_guard(GLOBAL)
if(COMMAND add_examples AND COMMAND add_tests AND COMMAND filter_files_in_list)
    return()
endif()

# Function for entry exclusion in a list based on pattern matching
function(filter_files_in_list input_var output_var exclude_list)
    set(filtered_files "")
    set(exclude_entries ${${exclude_list}})
    foreach(testFile ${${input_var}})
        get_filename_component(fileName ${testFile} NAME)
        get_filename_component(fileNameNoExt ${testFile} NAME_WE)

        list(FIND exclude_entries "${fileName}" index_with_ext)
        list(FIND exclude_entries "${fileNameNoExt}" index_no_ext)
        if(index_with_ext EQUAL -1 AND index_no_ext EQUAL -1)
            list(APPEND filtered_files ${testFile})
        endif()
    endforeach()
    set(${output_var} ${filtered_files} PARENT_SCOPE)
endfunction()

# Function to fetch all source files (C++, CUDA, PTX) and set related variables for a project library target
function(collect_project_source_inventory)

    # Initialize arguments
    set(oneValueArgs
        ROOT_DIR
        COMPILED_SOURCES_OUT
        PTX_SOURCES_OUT
        HAS_COMPILED_SOURCES_OUT
        HAS_PTX_SOURCES_OUT)

    # CPSI: Collect Project Source Inventory
    cmake_parse_arguments(CPSI "" "${oneValueArgs}" "" ${ARGN})

    if(NOT CPSI_ROOT_DIR)
        message(FATAL_ERROR "collect_project_source_inventory requires ROOT_DIR.")
    endif()

    file(GLOB_RECURSE _compiled_sources CONFIGURE_DEPENDS
        "${CPSI_ROOT_DIR}/*.cpp"
        "${CPSI_ROOT_DIR}/*.cu")
    file(GLOB_RECURSE _ptx_sources CONFIGURE_DEPENDS
        "${CPSI_ROOT_DIR}/*.ptx.cu")

    if(_ptx_sources)
        list(REMOVE_ITEM _compiled_sources ${_ptx_sources})
    endif()

    set(_filtered_compiled_sources "")
    foreach(_source_file IN LISTS _compiled_sources)
        file(RELATIVE_PATH _source_rel_path "${CPSI_ROOT_DIR}" "${_source_file}")
        string(REPLACE "\\" "/" _source_rel_path "${_source_rel_path}")
        if(_source_rel_path MATCHES "^bin(/|$)")
            continue()
        endif()
        list(APPEND _filtered_compiled_sources "${_source_file}")
    endforeach()

    set(_filtered_ptx_sources "")
    foreach(_source_file IN LISTS _ptx_sources)
        file(RELATIVE_PATH _source_rel_path "${CPSI_ROOT_DIR}" "${_source_file}")
        string(REPLACE "\\" "/" _source_rel_path "${_source_rel_path}")
        if(_source_rel_path MATCHES "^bin(/|$)")
            continue()
        endif()
        list(APPEND _filtered_ptx_sources "${_source_file}")
    endforeach()

    list(REMOVE_DUPLICATES _filtered_compiled_sources)
    list(REMOVE_DUPLICATES _filtered_ptx_sources)

    if(CPSI_COMPILED_SOURCES_OUT)
        set(${CPSI_COMPILED_SOURCES_OUT} "${_filtered_compiled_sources}" PARENT_SCOPE)
    endif()
    if(CPSI_PTX_SOURCES_OUT)
        set(${CPSI_PTX_SOURCES_OUT} "${_filtered_ptx_sources}" PARENT_SCOPE)
    endif()
    if(CPSI_HAS_COMPILED_SOURCES_OUT)
        if(_filtered_compiled_sources)
            set(${CPSI_HAS_COMPILED_SOURCES_OUT} TRUE PARENT_SCOPE)
        else()
            set(${CPSI_HAS_COMPILED_SOURCES_OUT} FALSE PARENT_SCOPE)
        endif()
    endif()
    if(CPSI_HAS_PTX_SOURCES_OUT)
        if(_filtered_ptx_sources)
            set(${CPSI_HAS_PTX_SOURCES_OUT} TRUE PARENT_SCOPE)
        else()
            set(${CPSI_HAS_PTX_SOURCES_OUT} FALSE PARENT_SCOPE)
        endif()
    endif()
endfunction()

# Function to add examples files to the build
function(add_examples project_lib_name excluded_list target_compile_settings)

    set(EXAMPLES_PATTERN "example_*.cpp; example_*.cu")
    file(GLOB srcExampleFiles RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} ${EXAMPLES_PATTERN})

    # Exclude files in excluded_list (filter_files_in_list is assumed to be a custom macro)
    filter_files_in_list(srcExampleFiles srcExampleFiles ${excluded_list})

    # Get current folder name
    get_filename_component(CURRENT_FOLDER_NAME ${CMAKE_CURRENT_SOURCE_DIR} NAME)
    message(STATUS "Example files found in ${CURRENT_FOLDER_NAME}: ${srcExampleFiles}")

    #message(STATUS "Project linked lib ${project_lib_name} to examples: ${srcExampleFiles}")
    #message(STATUS "Include directories of project lib: ${${project_lib_name}_INCLUDE_DIRS}")

    foreach(exampleFile ${srcExampleFiles})
        get_filename_component(exampleName ${exampleFile} NAME_WE)
        add_executable(${exampleName} ${exampleFile})
        target_link_libraries(${exampleName} PRIVATE ${project_lib_name} ${target_compile_settings})
        target_include_directories(${exampleName} PRIVATE ${${project_lib_name}_INCLUDE_DIRS})
    endforeach()

endfunction()

function(resolve_python_test_command output_var)
    if(NOT PYTHON_TEST_RUNNER STREQUAL "pytest")
        message(FATAL_ERROR "Unsupported PYTHON_TEST_RUNNER='${PYTHON_TEST_RUNNER}'")
    endif()
    if(NOT "${PYTHON_TEST_CONDA_ENV}" STREQUAL "" AND
       NOT "${PYTHON_TEST_CONDA_PREFIX}" STREQUAL "")
        message(FATAL_ERROR "Set only one of PYTHON_TEST_CONDA_ENV or PYTHON_TEST_CONDA_PREFIX")
    endif()

    if(NOT "${PYTHON_TEST_CONDA_ENV}" STREQUAL "" OR
       NOT "${PYTHON_TEST_CONDA_PREFIX}" STREQUAL "")
        set(_conda_executable "${PYTHON_TEST_CONDA_EXECUTABLE}")
        if(NOT IS_ABSOLUTE "${_conda_executable}")
            find_program(_conda_executable_resolved NAMES "${_conda_executable}")
            if(_conda_executable_resolved)
                set(_conda_executable "${_conda_executable_resolved}")
            endif()
        elseif(NOT EXISTS "${_conda_executable}")
            message(FATAL_ERROR "Conda executable does not exist: ${_conda_executable}")
        endif()
        if(NOT _conda_executable)
            message(FATAL_ERROR "Could not find conda executable '${PYTHON_TEST_CONDA_EXECUTABLE}'")
        endif()

        if(NOT "${PYTHON_TEST_CONDA_PREFIX}" STREQUAL "")
            if(NOT EXISTS "${PYTHON_TEST_CONDA_PREFIX}")
                message(FATAL_ERROR "Python test conda prefix does not exist: ${PYTHON_TEST_CONDA_PREFIX}")
            endif()
            set(_python_test_command "${_conda_executable}" run -p "${PYTHON_TEST_CONDA_PREFIX}" python)
        else()
            set(_python_test_command "${_conda_executable}" run -n "${PYTHON_TEST_CONDA_ENV}" python)
        endif()
    else()
        if(NOT "${PYTHON_TEST_EXECUTABLE}" STREQUAL "")
            set(_python_test_command "${PYTHON_TEST_EXECUTABLE}")
        else()
            if(DEFINED PROJECT_PYTHON_VERSION AND NOT "${PROJECT_PYTHON_VERSION}" STREQUAL "")
                find_package(Python3 ${PROJECT_PYTHON_VERSION} QUIET COMPONENTS Interpreter)
            else()
                find_package(Python3 QUIET COMPONENTS Interpreter)
            endif()
            if(Python3_FOUND)
                set(_python_test_command "${Python3_EXECUTABLE}")
            elseif(DEFINED Python_EXECUTABLE AND NOT "${Python_EXECUTABLE}" STREQUAL "")
                set(_python_test_command "${Python_EXECUTABLE}")
            else()
                find_program(_python_test_command NAMES python3 python)
            endif()
        endif()
        if(NOT _python_test_command)
            message(FATAL_ERROR "Could not resolve a Python executable for tests")
        endif()
    endif()

    execute_process(
        COMMAND ${_python_test_command} -m pytest --version
        RESULT_VARIABLE _pytest_result
        OUTPUT_VARIABLE _pytest_stdout
        ERROR_VARIABLE _pytest_stderr
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_STRIP_TRAILING_WHITESPACE
        TIMEOUT 30)
    if(NOT _pytest_result EQUAL 0)
        message(FATAL_ERROR
            "pytest is required for Python CTest registration but was unavailable.\n"
            "Command: ${_python_test_command} -m pytest --version\n"
            "stdout:\n${_pytest_stdout}\n"
            "stderr:\n${_pytest_stderr}")
    endif()
    set(${output_var} "${_python_test_command}" PARENT_SCOPE)
endfunction()

function(resolve_catch2_test_properties output_var properties_arg)
    set(_resolved_properties)
    if(NOT "${properties_arg}" STREQUAL "")
        if("${properties_arg}" MATCHES ";")
            set(_resolved_properties ${properties_arg})
        elseif(DEFINED ${properties_arg})
            set(_resolved_properties ${${properties_arg}})
        else()
            set(_resolved_properties ${properties_arg})
        endif()
    endif()
    set(${output_var} "${_resolved_properties}" PARENT_SCOPE)
endfunction()

function(add_tests project_lib_name excluded_list tests_list_var target_compile_settings catch2_properties catch2_target)
    file(GLOB srcTestFiles RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}" CONFIGURE_DEPENDS
         "test*.cpp" "test*.cu")
    file(GLOB srcPythonTestFiles RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}" CONFIGURE_DEPENDS
         "test*.py")
    filter_files_in_list(srcTestFiles srcTestFiles ${excluded_list})
    filter_files_in_list(srcPythonTestFiles srcPythonTestFiles ${excluded_list})

    get_filename_component(_folder_name "${CMAKE_CURRENT_SOURCE_DIR}" NAME)
    string(REGEX REPLACE "[^A-Za-z0-9_]" "_" _safe_folder_name "${_folder_name}")
    set(_registered_tests ${${tests_list_var}})

    if(Catch2_FOUND)
        resolve_catch2_test_properties(_catch2_properties "${catch2_properties}")
        set(_discover_args)
        if(NOT "${CATCH2_TEST_REPORTER}" STREQUAL "")
            list(APPEND _discover_args REPORTER "${CATCH2_TEST_REPORTER}")
        endif()
        if(_catch2_properties)
            list(APPEND _discover_args PROPERTIES ${_catch2_properties})
        endif()

        foreach(testFile IN LISTS srcTestFiles)
            get_filename_component(testName "${testFile}" NAME_WE)
            add_executable(${testName} ${testFile})
            target_link_libraries(${testName} PRIVATE
                ${project_lib_name} ${target_compile_settings} ${catch2_target})
            catch_discover_tests(${testName} ${_discover_args})
            list(APPEND _registered_tests ${testName})
        endforeach()
    elseif(srcTestFiles)
        message(STATUS "Catch2 unavailable; skipping compiled tests in ${_folder_name}")
    endif()

    if(ENABLE_PYTHON_TESTS AND srcPythonTestFiles)
        resolve_python_test_command(_python_test_command)
        foreach(testFile IN LISTS srcPythonTestFiles)
            get_filename_component(_test_stem "${testFile}" NAME_WE)
            set(_test_name "${_safe_folder_name}_${_test_stem}_py")
            add_test(
                NAME ${_test_name}
                COMMAND ${CMAKE_COMMAND} -E env
                    "PYTHONPATH=${PROJECT_SOURCE_DIR}/python:${PROJECT_BINARY_DIR}/python:$ENV{PYTHONPATH}"
                    "LD_LIBRARY_PATH=${PROJECT_BINARY_DIR}/src:$ENV{LD_LIBRARY_PATH}"
                    ${_python_test_command} -m pytest -q "${CMAKE_CURRENT_SOURCE_DIR}/${testFile}")
            set_tests_properties(${_test_name} PROPERTIES
                LABELS "python;pytest"
                WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
                TIMEOUT 120)
            list(APPEND _registered_tests ${_test_name})
        endforeach()
    elseif(srcPythonTestFiles)
        message(STATUS "Python tests disabled in ${_folder_name}")
    endif()

    set(${tests_list_var} "${_registered_tests}" PARENT_SCOPE)
endfunction()
