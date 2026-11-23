"""Test profile validation, resource resolution and installed example bindings."""

from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from evalviz_plotjuggler.visualization_profile import (
    comparison_configured,
    load_builtin_profile,
    load_profile,
    profile_schema,
    reference_input,
)

_MINIMAL_PROFILE = """\
schema_version: 1
name: Fixture
clock: robot_clock
inputs:
  primary:
    role: estimate
    adapter: ros2
    clock: estimate_clock
    topic: /navigation/estimate
    message_type: nav_msgs/msg/Odometry
    required: true
frames:
  world: map
  tracked: base_link
viewer:
  bridge_url: wss://example.org/bridge
  namespace: /fixture
  retention_s: 15
"""


def test_published_schema_matches_packaged_profiles() -> None:
    """Validate the package samples with the published schema."""
    schema = profile_schema()
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    g1 = load_builtin_profile("g1")
    assert validator.is_valid(g1)
    assert validator.is_valid(load_builtin_profile("template"))

    assert g1["frames"] == {"world": "world", "tracked": "imu_in_torso"}
    assert g1["robot"]["root_frame"] == "base_link"
    assert g1["robot"]["urdf"] == {
        "package": "legged_nav_system",
        "path": "profiles/g1/model.urdf",
    }
    assert g1["robot"]["joint_topic"] == "/nav/legged_nav/display/joint_states"
    assert g1["inputs"]["filter"]["topic"] == "/nav/legged_nav/filter/estimate"
    assert g1["inputs"]["graph"]["message_type"] == "legged_nav_system_ros/msg/NavigationEstimate"
    assert g1["inputs"]["graph_path"]["estimator"] == "graph"
    assert g1["inputs"]["graph_path"]["topic"] == "/nav/legged_nav/graph/trajectory"


@pytest.mark.parametrize("model_is_mapping", [False, True])
def test_relative_resources_are_anchored_at_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, model_is_mapping: bool
) -> None:
    """Resolve local model and reference resources from the YAML location."""
    config_dir = tmp_path / "configuration"
    config_dir.mkdir()
    monkeypatch.chdir(tmp_path)
    profile_path = config_dir / "robot.yml"
    urdf = "{path: robot/model.xacro}" if model_is_mapping else "robot/model.xacro"
    profile_path.write_text(
        _MINIMAL_PROFILE
        + f"robot: {{root_frame: base_link, urdf: {urdf}}}\n"
        + "reference:\n"
        + "  calibration_path: calibration/binding.json\n"
        + "  prepared_csv: ../reference.csv\n",
        encoding="utf-8",
    )

    profile = load_profile(profile_path.relative_to(tmp_path))
    expected_model = str(config_dir / "robot" / "model.xacro")
    expected_urdf = {"path": expected_model} if model_is_mapping else expected_model
    assert profile["robot"]["urdf"] == expected_urdf
    assert profile["reference"]["calibration_path"] == str(config_dir / "calibration/binding.json")
    assert profile["reference"]["prepared_csv"] == str(tmp_path / "reference.csv")
    assert profile["inputs"]["primary"]["clock"] == "estimate_clock"
    assert profile["viewer"]["namespace"] == "/fixture"


@pytest.mark.parametrize(
    ("addition", "message"),
    [
        ("name: Replacement\n", "duplicate key 'name'"),
        ("typo: false\n", "Additional properties are not allowed"),
        ("reference: {max_gap_s: 0.1, max_gap_s: 0.2}\n", "duplicate key 'max_gap_s'"),
        ("reference: {max_gap_s: .inf}\n", "Out of range float values"),
        ("reference: {input: primary}\n", "must name an input with role reference"),
        ("reference: {anchor_estimator: missing}\n", "must name an input with role estimate"),
        ("reference: {alignment: initial_position_yaw}\n", "needs anchor_estimator"),
        ("reference: {1: value}\n", "expected a string key"),
        ("capture: {topics: [/tf, /tf]}\n", "has non-unique elements"),
        (
            "robot: {root_frame: base_link, urdf: {package: test_robot, path: ../other.urdf}}\n",
            "robot.urdf",
        ),
        (
            "robot: {root_frame: base_link, urdf: {package: test_robot, path: /other.urdf}}\n",
            "robot.urdf",
        ),
    ],
)
def test_rejects_invalid_profile(tmp_path: Path, addition: str, message: str) -> None:
    """Fail before starting runtime work when a profile is invalid."""
    path = tmp_path / "invalid.yml"
    path.write_text(_MINIMAL_PROFILE + addition, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_profile(path)


def test_rejects_unknown_input_keys(tmp_path: Path) -> None:
    """Reject an input field typo and identify the faulty mapping."""
    path = tmp_path / "input_typo.yml"
    path.write_text(
        _MINIMAL_PROFILE.replace("    required: true", "    reuired: true"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"inputs\.primary.*reuired"):
        load_profile(path)


@pytest.mark.parametrize("role", ["estimate", "reference"])
def test_rejects_unsupported_pose_type(tmp_path: Path, role: str) -> None:
    """Reject a pose role bound to a type the decoder cannot read."""
    path = tmp_path / "imu.yml"
    path.write_text(
        _MINIMAL_PROFILE.replace("    role: estimate", f"    role: {role}").replace(
            "nav_msgs/msg/Odometry", "sensor_msgs/msg/Imu"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"inputs\.primary\.message_type.*not a supported"):
        load_profile(path)


def test_rejects_ambiguous_reference_input(tmp_path: Path) -> None:
    """Require reference.input when several reference inputs exist."""
    references = "".join(
        f"  {name}:\n    role: reference\n    topic: /{name}\n"
        "    message_type: nav_msgs/msg/Odometry\n"
        for name in ("vicon", "gnss")
    )
    path = tmp_path / "references.yml"
    path.write_text(
        _MINIMAL_PROFILE.replace("frames:\n", references + "frames:\n"), encoding="utf-8"
    )

    with pytest.raises(ValueError, match=r"reference.input must choose"):
        load_profile(path)
    path.write_text(path.read_text(encoding="utf-8") + "reference: {input: gnss}\n")
    profile = load_profile(path)
    assert reference_input(profile) == "gnss"
    assert comparison_configured(profile)


def test_comparison_predicate_for_packaged_profiles() -> None:
    """Compare in G1 through its reference input and not in the template."""
    g1 = load_builtin_profile("g1")
    assert reference_input(g1) == "reference"
    assert comparison_configured(g1)
    assert not comparison_configured(load_builtin_profile("template"))


def test_rejects_wrong_ros_type_syntax(tmp_path: Path) -> None:
    """Require a fully qualified ROS message type."""
    path = tmp_path / "type_typo.yml"
    path.write_text(
        _MINIMAL_PROFILE.replace("nav_msgs/msg/Odometry", "nav_msgs/Odometry"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"inputs\.primary\.message_type"):
        load_profile(path)
