"""Validate viewer profiles and resolve their filesystem resources."""

from __future__ import annotations

import json
from collections.abc import Hashable
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode, Node

from .native_record_protocol import POSE_ENCODING

_RESOURCE_PACKAGE = "evalviz_plotjuggler"

# JSON Schema validates member types for each version of the public mapping.
type JsonObject = dict[str, Any]

NATIVE_ESTIMATE_TYPE = "legged_nav_system_ros/msg/NavigationEstimate"
# Message types the pose decoder supports for the estimate and reference roles.
POSE_MESSAGE_TYPES = frozenset(
    {"geometry_msgs/msg/PoseStamped", "nav_msgs/msg/Odometry", NATIVE_ESTIMATE_TYPE}
)
# A generic String is a pose only when the input declares the normalized encoding.
STRING_MESSAGE_TYPE = "std_msgs/msg/String"


def pose_input_supported(entry: JsonObject) -> bool:
    """Tell whether the pose decoder can read an estimate or reference input.

    Args:
        entry: Profile input.

    Returns:
        True for a supported pose message type without an encoding, or for
        ``std_msgs/msg/String`` with encoding ``evalviz_jsonl_v1``.

    Example:
        >>> pose_input_supported({"message_type": "std_msgs/msg/String"})
        False
    """
    if "encoding" in entry:
        return (entry["encoding"], entry["message_type"]) == (POSE_ENCODING, STRING_MESSAGE_TYPE)
    return entry["message_type"] in POSE_MESSAGE_TYPES


class _ProfileLoader(yaml.SafeLoader):
    """Read only mappings with unique, string-valued keys."""

    def construct_mapping(self, node: Node, deep: bool = False) -> dict[Hashable, object]:
        """Construct a YAML mapping, rejecting duplicate or non-string keys.

        Args:
            node: YAML node to construct as a mapping.
            deep: Whether to construct nested objects deeply.

        Returns:
            The constructed mapping with unique string keys.

        Raises:
            ConstructorError: The node is not a mapping, or a key is non-string or repeated.
        """
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None, "expected a mapping", node.start_mark)

        mapping: dict[Hashable, object] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ConstructorError(None, None, "expected a string key", key_node.start_mark)
            if key in mapping:
                raise ConstructorError(None, None, f"duplicate key {key!r}", key_node.start_mark)
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def profile_schema() -> JsonObject:
    """Read the same JSON Schema used by the runtime validator.

    Returns:
        An independently mutable JSON Schema dictionary.

    Example:
        >>> profile_schema()["title"]
        'EvalViz PlotJuggler profile'
    """
    schema: JsonObject = json.loads(
        files(_RESOURCE_PACKAGE)
        .joinpath("visualization_profile.schema.json")
        .read_text(encoding="utf-8")
    )
    return schema


def load_profile(path: Path) -> JsonObject:
    """Read, validate and resolve a YAML profile.

    Args:
        path: Profile YAML whose parent directory anchors relative local resources.

    Returns:
        A JSON-compatible dictionary with adapter, clock and viewer defaults
        applied. Local resource paths are absolute. A ROS package resource path
        remains relative to the package's share directory.

    Raises:
        ValueError: The file cannot be read, or its profile is invalid.

    Example:
        >>> from importlib.resources import files
        >>> resource = files("evalviz_plotjuggler").joinpath("profiles", "g1.yml")
        >>> with as_file(resource) as profile_path:
        ...     load_profile(profile_path)["frames"]["tracked"]
        'imu_in_torso'
    """
    schema = profile_schema()
    try:
        raw_profile: object = yaml.load(path.read_text(encoding="utf-8"), Loader=_ProfileLoader)
        json.dumps(raw_profile, allow_nan=False)
    except (OSError, TypeError, ValueError, yaml.YAMLError) as error:
        raise ValueError(f"{path}: {error}") from error

    # Report the most specific error, also inside oneOf alternatives.
    validation_error = best_match(Draft202012Validator(schema).iter_errors(raw_profile))
    if validation_error is not None:
        field = ".".join(str(part) for part in validation_error.absolute_path) or "profile"
        raise ValueError(f"{path}: {field}: {validation_error.message}")

    profile = cast(JsonObject, raw_profile)
    try:
        _resolve_profile(profile, schema, path.parent)
    except (OSError, ValueError) as error:
        raise ValueError(f"{path}: {error}") from error
    return profile


def load_builtin_profile(name: str) -> JsonObject:
    """Read one of the packaged profiles through the same validator.

    Args:
        name: Profile name, either `g1` or `template`.

    Returns:
        A resolved profile dictionary.

    Raises:
        ValueError: The profile name is unknown or the packaged profile is invalid.

    Example:
        >>> load_builtin_profile("g1")["frames"]["tracked"]
        'imu_in_torso'
    """
    if name not in {"g1", "template"}:
        raise ValueError(f"unknown built-in profile {name!r}; choose g1 or template")
    resource = files(_RESOURCE_PACKAGE).joinpath("profiles", f"{name}.yml")
    with as_file(resource) as path:
        return load_profile(path)


def reference_input(profile: JsonObject) -> str | None:
    """Name the input that supplies live reference poses.

    Args:
        profile: Profile dictionary, validated or loaded from a capture snapshot.

    Returns:
        `reference.input` when set, otherwise the only input with role
        `reference`, or None when the profile has no reference input.

    Raises:
        ValueError: Several reference inputs exist and `reference.input` does
            not choose one.

    Example:
        >>> reference_input(load_builtin_profile("g1"))
        'reference'
    """
    if chosen := profile.get("reference", {}).get("input"):
        return str(chosen)
    names = [name for name, entry in profile["inputs"].items() if entry["role"] == "reference"]
    if len(names) > 1:
        raise ValueError(f"reference.input must choose one of the reference inputs {names}")
    return names[0] if names else None


def comparison_configured(profile: JsonObject) -> bool:
    """Tell whether the relay and review compare estimates with a reference.

    Args:
        profile: Profile dictionary, validated or loaded from a capture snapshot.

    Returns:
        True when a prepared reference CSV or a reference input is configured.

    Raises:
        ValueError: The reference input is ambiguous.

    Example:
        >>> comparison_configured(load_builtin_profile("template"))
        False
    """
    if profile.get("reference", {}).get("prepared_csv"):
        return True
    return reference_input(profile) is not None


def model_path(robot: JsonObject) -> Path:
    """Resolve a configured URDF from disk or the installed ROS package.

    Args:
        robot: Validated robot configuration.

    Returns:
        Absolute path to the configured model.

    Raises:
        FileNotFoundError: The configured model file is missing.
    """
    description = robot["urdf"]
    if isinstance(description, str):
        return Path(description).resolve(strict=True)
    if package := description.get("package"):
        from ament_index_python.packages import get_package_share_path

        share_path: Path = get_package_share_path(package)
        relative_path: str = description["path"]
        return (share_path / relative_path).resolve(strict=True)
    return Path(description["path"]).resolve(strict=True)


def _resolve_profile(profile: JsonObject, schema: JsonObject, directory: Path) -> None:
    """Apply defaults, validate input associations and resolve resource paths."""
    profile.setdefault("clock", schema["properties"]["clock"]["default"])
    inputs = profile["inputs"]
    input_properties = schema["$defs"]["input"]["properties"]
    for name, entry in inputs.items():
        entry.setdefault("adapter", input_properties["adapter"]["default"])
        entry.setdefault("required", input_properties["required"]["default"])
        entry.setdefault("clock", profile["clock"])
        if "estimator" in entry and inputs.get(entry["estimator"], {}).get("role") != "estimate":
            raise ValueError(f"inputs.{name}.estimator must name an input with role estimate")
        # Reject a pose type the decoder cannot read before any runtime starts.
        if entry["role"] in {"estimate", "reference"} and not pose_input_supported(entry):
            raise ValueError(
                f"inputs.{name}.message_type {entry['message_type']!r} is not a supported "
                f"pose type; choose one of {sorted(POSE_MESSAGE_TYPES)}, or "
                f"{STRING_MESSAGE_TYPE} with encoding {POSE_ENCODING}"
            )

    viewer = profile["viewer"]
    viewer_properties = schema["$defs"]["viewer"]["properties"]
    viewer.setdefault("namespace", viewer_properties["namespace"]["default"])
    viewer.setdefault("retention_s", viewer_properties["retention_s"]["default"])

    if "robot" in profile:
        robot = profile["robot"]
        urdf = robot["urdf"]
        if isinstance(urdf, str):
            robot["urdf"] = str((directory / urdf).resolve())
        elif "package" not in urdf:
            urdf["path"] = str((directory / urdf["path"]).resolve())

    reference_input(profile)
    if "reference" in profile:
        reference = profile["reference"]
        for field, role in (("input", "reference"), ("anchor_estimator", "estimate")):
            if field in reference and inputs.get(reference[field], {}).get("role") != role:
                raise ValueError(f"reference.{field} must name an input with role {role}")
        # Alignment is frozen from one named estimator; no robot-specific default applies.
        if reference.get("alignment") == "initial_position_yaw" and (
            "anchor_estimator" not in reference
        ):
            raise ValueError("reference.alignment initial_position_yaw needs anchor_estimator")
        for field in ("calibration_path", "prepared_csv"):
            if field in reference:
                reference[field] = str((directory / reference[field]).resolve())
