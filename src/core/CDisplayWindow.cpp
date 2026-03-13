/// @file
/// @brief Implements the interactive OpenCV display window utilities.

#include "CDisplayWindow.h"
#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>

namespace viztools
{

/// @brief Stores the display configuration used by the window instance.
/// @param config Runtime configuration for window title, timing, and hotkeys.
CDisplayWindow::CDisplayWindow(SWindowConfig config)
    : config_(std::move(config))
{
}

/// @brief Ensures the OpenCV window is closed before the object is destroyed.
CDisplayWindow::~CDisplayWindow()
{
    close();
}

/// @copydoc viztools::CDisplayWindow::show
auto CDisplayWindow::show(const cv::Mat &frame) -> EWindowAction
{
    if (frame.empty())
        return EWindowAction::QUIT;

    if (!window_created_)
    {
        cv::namedWindow(config_.window_name, cv::WINDOW_AUTOSIZE);
        window_created_ = true;
    }

    cv::Mat display_frame;
    if (std::abs(config_.display_scale - 1.0) > 1e-6)
    {
        cv::resize(frame, display_frame, cv::Size(),
                   config_.display_scale, config_.display_scale,
                   cv::INTER_LINEAR);
    }
    else
    {
        display_frame = frame;
    }

    cv::imshow(config_.window_name, display_frame);

    int key = cv::waitKey(config_.wait_ms);
    return processKey(key);
}

/// @copydoc viztools::CDisplayWindow::runLoop
void CDisplayWindow::runLoop(std::function<cv::Mat()> frame_provider)
{
    while (true)
    {
        cv::Mat frame;
        if (!paused_)
        {
            frame = frame_provider();
            if (frame.empty())
                break;
        }

        EWindowAction action = EWindowAction::CONTINUE;
        if (!frame.empty())
        {
            action = show(frame);
        }
        else
        {
            // Paused with no new frame — just wait for input
            int key = cv::waitKey(config_.wait_ms);
            action = processKey(key);
        }

        if (action == EWindowAction::QUIT)
            break;

        if (action == EWindowAction::PAUSE)
        {
            paused_ = !paused_;
        }

        if (action == EWindowAction::STEP && paused_)
        {
            // Force one frame advance on next iteration
            cv::Mat step_frame = frame_provider();
            if (step_frame.empty())
                break;
            show(step_frame);
        }
    }

    close();
}

/// @copydoc viztools::CDisplayWindow::close
void CDisplayWindow::close()
{
    if (window_created_)
    {
        cv::destroyWindow(config_.window_name);
        window_created_ = false;
    }
}

/// @brief Maps a raw HighGUI key code to a window action.
/// @param key Key value returned by `cv::waitKey()`.
/// @return The semantic action that should be applied to the window loop.
auto CDisplayWindow::processKey(int key) -> EWindowAction
{
    if (key < 0)
        return EWindowAction::CONTINUE;

    key &= 0xFF; // Mask to handle platform differences

    if (key == config_.quit_key || key == 'q' || key == 'Q')
        return EWindowAction::QUIT;

    if (key == config_.pause_key)
        return EWindowAction::PAUSE;

    if (key == config_.step_key)
        return EWindowAction::STEP;

    return EWindowAction::CONTINUE;
}

} // namespace viztools
