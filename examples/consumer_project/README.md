# Installed Package Consumer

This standalone CMake project demonstrates consumption of an installed
`EvalAndVizGears_for_ComputerVision` package and renders synthetic feature
locations into an OpenCV BGR image.

```bash
cmake -S . -B build -DCMAKE_PREFIX_PATH="/path/to/eval-and-viz/install;/path/to/slam-primitives/install"
cmake --build build --parallel 4
./build/eval_and_viz_consumer
```
