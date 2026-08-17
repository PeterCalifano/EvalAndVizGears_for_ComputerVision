set(TESTS_LIST "")

# Register tests for this repository's runtime/library behavior.
add_subdirectory(core)

message(STATUS "List of test targets: ${TESTS_LIST}")
