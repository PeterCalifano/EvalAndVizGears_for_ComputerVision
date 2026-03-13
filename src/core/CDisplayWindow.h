#pragma once
#include <cstdint>
#include <functional>
#include <string>

#include <opencv2/core.hpp>

namespace viztools
{

    /// @brief Keyboard action returned by CDisplayWindow::show().
    enum class EWindowAction : uint8_t
    {
        CONTINUE,  ///< Normal frame advance.
        PAUSE,     ///< Toggle pause/resume.
        STEP,      ///< Advance one frame (while paused).
        QUIT       ///< Exit the display loop.
    };

    /// @brief Configuration for the display window.
    struct SWindowConfig
    {
        /// @brief Window title.
        std::string window_name{"VizTools"};

        /// @brief Wait time in ms per frame (0 = wait for keypress).
        int wait_ms{30};

        /// @brief Scale factor for display (1.0 = original size).
        double display_scale{1.0};

        /// @brief Key code for quit (default: 'q' or ESC).
        int quit_key{27}; // ESC

        /// @brief Key code for pause toggle (default: space).
        int pause_key{32}; // SPACE

        /// @brief Key code for step-forward while paused (default: 'n').
        int step_key{'n'};
    };

    /// @brief OpenCV HighGUI window for live frame display with keyboard controls.
    ///
    /// Provides both a blocking display loop (for offline replay) and a
    /// non-blocking single-frame update (for integration into tracking pipelines).
    class CDisplayWindow
    {
      public:
        explicit CDisplayWindow(SWindowConfig config = {});
        ~CDisplayWindow();

        // Non-copyable, movable
        CDisplayWindow(const CDisplayWindow &) = delete;
        auto operator=(const CDisplayWindow &) -> CDisplayWindow & = delete;
        CDisplayWindow(CDisplayWindow &&) = default;
        auto operator=(CDisplayWindow &&) -> CDisplayWindow & = default;

        /// @brief Show a single frame and process keyboard input.
        ///
        /// Non-blocking: displays the image, waits for wait_ms, and returns
        /// the user action. Call this in your own loop.
        /// @param frame Image to display.
        /// @return Action based on keyboard input.
        auto show(const cv::Mat &frame) -> EWindowAction;

        /// @brief Run a blocking display loop fed by a frame callback.
        ///
        /// Calls frame_provider repeatedly until it returns an empty Mat or
        /// the user presses quit. Handles pause/step internally.
        /// @param frame_provider Callable returning the next frame. Return
        ///        empty cv::Mat to signal end of sequence.
        void runLoop(std::function<cv::Mat()> frame_provider);

        /// @brief Check if the window is paused.
        auto isPaused() const -> bool { return paused_; }

        /// @brief Close the window.
        void close();

        /// @brief Get mutable config reference.
        auto config() -> SWindowConfig & { return config_; }

      private:
        auto processKey(int key) -> EWindowAction;

        SWindowConfig config_;
        bool paused_{false};
        bool window_created_{false};
    };

} // namespace viztools
