#!/usr/bin/env python3
"""Update the project devcontainer while preserving unmanaged JSON fields."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

CUDA_FEATURE = "ghcr.io/devcontainers/features/nvidia-cuda:2"
CUDA_ENV = {
    "CUDA_HOME": "/usr/local/cuda",
    "PATH": "/usr/local/cuda/bin:${containerEnv:PATH}",
    "LD_LIBRARY_PATH": "/usr/local/cuda/lib64:${containerEnv:LD_LIBRARY_PATH}",
}
ROS_CONTAINER_ENV = {
    "ROS_DOMAIN_ID": "42",
    "ROS_LOCALHOST_ONLY": "1",
}
DEFAULT_EXTENSIONS = [
    "ms-vscode.cpptools",
    "ms-vscode.cmake-tools",
    "ms-python.python",
    "ms-python.vscode-pylance",
    "llvm-vs-code-extensions.vscode-clangd",
]


def strip_jsonc_comments(text: str) -> str:
    """Remove JSONC comments while preserving quoted string contents.

    Args:
        text: JSONC source text.

    Returns:
        Text with line and block comments removed.
    """

    output: list[str] = []
    in_string = False
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            index += 1
            continue
        if char == "/" and index + 1 < len(text):
            next_char = text[index + 1]
            if next_char == "/":
                index += 2
                while index < len(text) and text[index] not in "\r\n":
                    index += 1
                continue
            if next_char == "*":
                index += 2
                while index + 1 < len(text) and text[index : index + 2] != "*/":
                    index += 1
                index += 2
                continue
        output.append(char)
        index += 1
    return "".join(output)


def load_existing(path: Path) -> dict:
    """Load an existing devcontainer JSON object.

    Args:
        path: JSON or JSONC file to read when present.

    Returns:
        Parsed top-level object, or an empty object when the file is absent.

    Raises:
        ValueError: If the top-level value is not an object.
        json.JSONDecodeError: If the normalized input is malformed.
    """

    if not path.is_file():
        return {}
    text = strip_jsonc_comments(path.read_text(encoding="utf-8"))
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    parsed = json.loads(text) if text.strip() else {}
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return parsed


def strip_managed_gpu_args(arguments: list) -> list:
    """Remove GPU runtime arguments owned by this updater.

    Args:
        arguments: Existing devcontainer runtime arguments.

    Returns:
        Unmanaged arguments in their original order.
    """

    output = []
    index = 0
    managed_pairs = {
        ("--gpus", "all"),
        ("--device", "nvidia.com/gpu=all"),
        ("--security-opt", "label=disable"),
    }
    while index < len(arguments):
        pair = tuple(arguments[index : index + 2])
        if pair in managed_pairs:
            index += 2
            continue
        if arguments[index] in {
            "--gpus=all",
            "--device=nvidia.com/gpu=all",
            "--security-opt=label=disable",
        }:
            index += 1
            continue
        output.append(arguments[index])
        index += 1
    return output


def main() -> int:
    """Render the merged devcontainer object to standard output.

    Returns:
        Zero on success or two for invalid configuration/input JSON.
    """

    cuda_enabled = os.environ.get("CUDA", "off") == "on"
    cuda_version = os.environ.get("CUDA_VERSION", "12.9")
    gpu_runtime = os.environ.get("DEVCONTAINER_GPU_RUNTIME", "docker")
    ros_mode = os.environ.get("ROS_MODE", "none")
    ros_distro = os.environ.get("ROS_DISTRO", "")
    ros_profile = os.environ.get("ROS_PROFILE", "ros-base")
    if gpu_runtime not in {"docker", "podman"}:
        print("DEVCONTAINER_GPU_RUNTIME must be docker or podman", file=sys.stderr)
        return 2
    if ros_mode not in {"none", "ros2"}:
        print("ROS_MODE must be none or ros2", file=sys.stderr)
        return 2
    if ros_mode == "ros2" and ros_distro != "jazzy":
        print("ROS_DISTRO must be jazzy when ROS_MODE=ros2", file=sys.stderr)
        return 2
    if ros_profile not in {"ros-base", "desktop"}:
        print("ROS_PROFILE must be ros-base or desktop", file=sys.stderr)
        return 2

    default_path = Path(__file__).with_name("devcontainer.json")
    existing_path = Path(os.environ.get("DEVCONTAINER_JSON_PATH", default_path))
    try:
        data = load_existing(existing_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Cannot parse existing {existing_path}: {error}", file=sys.stderr)
        return 2

    data["name"] = "EvalAndVizGears_for_ComputerVision"
    build = data.get("build", {})
    if not isinstance(build, dict):
        build = {}
    build["dockerfile"] = "Dockerfile"
    build_arguments = build.get("args", {})
    if not isinstance(build_arguments, dict):
        build_arguments = {}
    for key in ("ROS_MODE", "ROS_DISTRO", "ROS_PROFILE"):
        build_arguments.pop(key, None)
    if ros_mode == "ros2":
        build_arguments.update(
            {
                "ROS_DISTRO": ros_distro,
                "ROS_MODE": ros_mode,
                "ROS_PROFILE": ros_profile,
            }
        )
    if build_arguments:
        build["args"] = dict(sorted(build_arguments.items()))
    else:
        build.pop("args", None)
    data["build"] = build

    features = data.get("features", {})
    if not isinstance(features, dict):
        features = {}
    features["ghcr.io/devcontainers/features/conda:1"] = {
        "addCondaForge": True,
        "version": "latest",
    }
    features["ghcr.io/devcontainers/features/python:1"] = {
        "enableShared": True,
        "installTools": True,
        "version": "3.12",
    }
    if cuda_enabled:
        features[CUDA_FEATURE] = {
            "cudaVersion": cuda_version,
            "installCudnn": True,
            "installCudnnDev": True,
            "installNvtx": True,
            "installToolkit": True,
        }
    else:
        features.pop(CUDA_FEATURE, None)
    data["features"] = dict(sorted(features.items()))

    existing_run_args = data.get("runArgs", [])
    if not isinstance(existing_run_args, list):
        existing_run_args = []
    run_args = strip_managed_gpu_args(existing_run_args)
    if cuda_enabled:
        managed_args = (
            ["--gpus", "all"]
            if gpu_runtime == "docker"
            else ["--device", "nvidia.com/gpu=all", "--security-opt", "label=disable"]
        )
        run_args = managed_args + run_args
    if run_args:
        data["runArgs"] = run_args
    else:
        data.pop("runArgs", None)

    remote_env = data.get("remoteEnv", {})
    if not isinstance(remote_env, dict):
        remote_env = {}
    if cuda_enabled:
        remote_env.update(CUDA_ENV)
    else:
        for key in CUDA_ENV:
            remote_env.pop(key, None)
    if remote_env:
        data["remoteEnv"] = remote_env
    else:
        data.pop("remoteEnv", None)

    container_env = data.get("containerEnv", {})
    if not isinstance(container_env, dict):
        container_env = {}
    if ros_mode == "ros2":
        container_env.update(ROS_CONTAINER_ENV)
    else:
        for key in ROS_CONTAINER_ENV:
            container_env.pop(key, None)
    if container_env:
        data["containerEnv"] = container_env
    else:
        data.pop("containerEnv", None)

    customizations = data.get("customizations", {})
    if not isinstance(customizations, dict):
        customizations = {}
    vscode = customizations.get("vscode", {})
    if not isinstance(vscode, dict):
        vscode = {}
    existing_extensions = vscode.get("extensions", [])
    if not isinstance(existing_extensions, list):
        existing_extensions = []
    extras = [item for item in existing_extensions if item not in DEFAULT_EXTENSIONS]
    vscode["extensions"] = DEFAULT_EXTENSIONS + extras
    customizations["vscode"] = vscode
    data["customizations"] = customizations

    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
