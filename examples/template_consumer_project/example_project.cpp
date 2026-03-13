/// @file
/// @brief Consumer-project example demonstrating external linkage against the library.

#include "example_project.h"

/// @brief Runs the template consumer application entry point.
/// @return Process exit status compatible with the hosting shell.
int main()
{
    spdlog_utils::ConfigureDefaultLogging();
    auto objLogger_ = spdlog_utils::GetLogger("example_consumer_project");
    objLogger_->info("Hello, World! This is an example of project using the EvalAndVizGears_for_ComputerVision as library, integrating it through cmake.");

    // Call the placeholder function from the template_src library
    placeholder::placeholder_fcn();

    return 0;
}
