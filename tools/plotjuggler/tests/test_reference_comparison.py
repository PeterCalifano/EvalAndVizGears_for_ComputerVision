"""Check source-time matching, convention and sensor binding with analytic poses."""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

import pytest
from scipy.spatial.transform import Rotation

from evalviz_plotjuggler.reference_comparison import (
    NAVIGATION_CHART,
    POSE_CHART,
    PoseSample,
    ReferenceBuffer,
    compare,
    fit_initial_yaw,
    load_prepared_reference,
    posterior_sigmas,
    prepare_truth,
    resolve_reference,
)
from evalviz_plotjuggler.visualization_profile import JsonObject

_CSV_HEADER = (
    "timestamp_ns,position_0,position_1,position_2,"
    "quaternion_xyzw_0,quaternion_xyzw_1,quaternion_xyzw_2,quaternion_xyzw_3\n"
)


def sample(
    stamp: int = 100, position: tuple[float, float, float] = (0.0, 0.0, 0.0), yaw: float = 0.0
) -> PoseSample:
    """Create a world-frame pose with the requested source stamp and yaw."""
    orientation = tuple(Rotation.from_euler("z", yaw).as_quat())
    return PoseSample(stamp, "world", "body", position, orientation)


def profile_with(reference: JsonObject, **truth: object) -> JsonObject:
    """Build a profile with an estimator and configurable reference input."""
    return {
        "clock": "source",
        "frames": {"world": "world", "tracked": "body"},
        "inputs": {
            "filter": {
                "role": "estimate",
                "topic": "/filter",
                "message_type": "nav_msgs/msg/Odometry",
            },
            "truth": {
                "role": "reference",
                "topic": "/truth",
                "message_type": "nav_msgs/msg/Odometry",
                **truth,
            },
        },
        "reference": reference,
    }


def test_shortest_arc_and_no_extrapolation() -> None:
    """Interpolate along the shortest arc and never extrapolate or cross a large gap."""
    truth = ReferenceBuffer(40)
    truth.add(sample(140, (2.0, 4.0, 0.0), math.radians(-170)))
    truth.add(sample(100, yaw=math.radians(170)))
    middle = truth.at(120)
    assert middle is not None
    assert middle.position == pytest.approx((1.0, 2.0, 0.0))
    assert abs(middle.quaternion[2]) == pytest.approx(1.0)
    assert truth.at(98) is None
    assert truth.at(141) is None
    truth.add(sample(240))
    assert truth.at(180) is None


def test_posterior_bounds_follow_the_navigation_block_order() -> None:
    """Give each chart block its own variance so a block reorder is visible."""
    block_sigmas = (0.1, 0.2, 0.3, 0.4, 0.5)
    diagonal = [sigma**2 for sigma in block_sigmas for _ in range(3)]
    covariance = tuple(
        diagonal[row] if row == col else 0.0 for row in range(15) for col in range(15)
    )
    estimate = replace(
        sample(position=(1.0, 2.0, 0.0)), covariance=covariance, chart=NAVIGATION_CHART
    )
    errors = compare(estimate, sample())
    assert errors["error_position_m_norm"] == pytest.approx(math.sqrt(5))
    assert errors["upper_position_m_x"] == pytest.approx(0.3)
    assert errors["upper_velocity_mps_y"] == pytest.approx(0.6)
    assert errors["lower_attitude_rad_z"] == pytest.approx(-0.9)
    assert errors["upper_accel_bias_mps2_x"] == pytest.approx(1.2)
    assert errors["upper_gyro_bias_radps_z"] == pytest.approx(1.5)
    assert errors["covariance_valid"] == 1.0
    assert not posterior_sigmas(replace(estimate, covariance=()))
    assert not posterior_sigmas(replace(estimate, covariance=(-1.0, *covariance[1:])))
    with pytest.raises(ValueError, match="same source time"):
        compare(estimate, sample(101))


@pytest.mark.parametrize(
    ("diagonal", "upper_xy", "lower_xy"),
    [
        pytest.param(1.0, float("nan"), 0.0, id="nan"),
        pytest.param(1.0, float("inf"), 0.0, id="infinite"),
        pytest.param(1.0, 0.5, 0.0, id="asymmetric"),
        pytest.param(1.0, 2.0, 2.0, id="negative-eigenvalue"),
        pytest.param(0.0, 0.0, 0.0, id="all-zero"),
    ],
)
def test_unusable_covariance_has_no_posterior_sigmas(
    diagonal: float, upper_xy: float, lower_xy: float
) -> None:
    """Return no sigmas for invalid covariance or an all-zero missing posterior."""
    covariance = [diagonal if row == col else 0.0 for row in range(6) for col in range(6)]
    covariance[1], covariance[6] = upper_xy, lower_xy
    estimate = replace(sample(), covariance=tuple(covariance), chart=POSE_CHART)
    assert posterior_sigmas(estimate) == {}


def test_posterior_sigmas_are_square_roots_of_covariance_diagonal() -> None:
    """Return one marginal sigma per pose axis for a valid correlated covariance."""
    diagonal = (1.0, 4.0, 9.0, 16.0, 25.0, 36.0)
    covariance = [diagonal[row] if row == col else 0.0 for row in range(6) for col in range(6)]
    covariance[1] = covariance[6] = 0.5
    estimate = replace(sample(), covariance=tuple(covariance), chart=POSE_CHART)
    assert posterior_sigmas(estimate) == {
        "position_m_x": 1.0,
        "position_m_y": 2.0,
        "position_m_z": 3.0,
        "attitude_rad_x": 4.0,
        "attitude_rad_y": 5.0,
        "attitude_rad_z": 6.0,
    }


def test_attitude_error_is_right_local_at_the_estimate() -> None:
    """Use non-commuting rotations, where right-local and world errors differ."""
    estimate_rotation = Rotation.from_euler("z", 90, degrees=True)
    truth_rotation = estimate_rotation * Rotation.from_rotvec([-0.1, 0.0, 0.0])
    estimate = replace(sample(), quaternion=tuple(estimate_rotation.as_quat()))
    truth = replace(sample(), quaternion=tuple(truth_rotation.as_quat()))
    errors = compare(estimate, truth)
    # A world-axis error would be (0, 0.1, 0) for this pair.
    assert (
        errors["error_attitude_rad_x"],
        errors["error_attitude_rad_y"],
        errors["error_attitude_rad_z"],
    ) == pytest.approx((0.1, 0.0, 0.0), abs=1e-12)


def test_precomputed_sigmas_replace_the_covariance() -> None:
    """Use supplied sigmas for bounds even when covariance is absent."""
    errors = compare(sample(), sample(), {"position_m_x": 0.5})
    assert errors["upper_position_m_x"] == pytest.approx(1.5)
    assert errors["covariance_valid"] == 1.0


def test_rotated_reference_mount_composes_on_the_right() -> None:
    """Mount at 1 m along the reference x axis with a 90° roll, reference yawed 90°."""
    binding = resolve_reference(
        profile_with(
            {
                "input": "truth",
                "tracked_frame": "vicon_body",
                "clock_offset_ns": 80,
                "tracked_from_navigation": {
                    "position": [1.0, 0.0, 0.0],
                    "quaternion_xyzw": list(Rotation.from_euler("x", 90, degrees=True).as_quat()),
                },
            }
        )
    )
    assert binding is not None
    truth = replace(sample(yaw=math.pi / 2), tracked="vicon_body", velocity=(1.0, 0.0, 0.0))
    mounted = prepare_truth(truth, binding)
    assert mounted.tracked == "body"
    assert mounted.stamp_ns == 180
    assert mounted.velocity is None
    assert mounted.position == pytest.approx((0.0, 1.0, 0.0), abs=1e-12)
    # World axes of the mounted frame: x stays along world y, y turns to world z.
    rotation = Rotation.from_quat(mounted.quaternion)
    assert rotation.apply([1.0, 0.0, 0.0]) == pytest.approx([0.0, 1.0, 0.0], abs=1e-12)
    assert rotation.apply([0.0, 1.0, 0.0]) == pytest.approx([0.0, 0.0, 1.0], abs=1e-12)
    with pytest.raises(ValueError, match="declared binding"):
        prepare_truth(sample(), binding)


def test_frozen_alignment_maps_reference_to_estimate_world() -> None:
    """Map reference positions into the estimate world with the fitted alignment."""
    estimates = [
        sample(100, (4.0, 2.0, 0.0), math.pi / 2),
        sample(140, (4.0, 3.0, 0.0), math.pi / 2),
    ]
    references = [sample(), sample(140, (1.0, 0.0, 0.0))]
    alignment = fit_initial_yaw(list(zip(estimates, references, strict=True)))
    assert alignment.apply(references[1]).position == pytest.approx((4.0, 3.0, 0.0))


def test_odometry_fixed_axes_are_rotated_to_right_tangent() -> None:
    """Rotate 120° about (1, 1, 1), which permutes the axes cyclically."""
    ros = pytest.importorskip("nav_msgs.msg")
    from evalviz_plotjuggler.estimate_decoding import decode_estimate

    message = ros.Odometry()
    message.header.frame_id = "world"
    message.child_frame_id = "body"
    message.pose.pose.orientation.x = 0.5
    message.pose.pose.orientation.y = 0.5
    message.pose.pose.orientation.z = 0.5
    message.pose.pose.orientation.w = 0.5
    message.twist.twist.linear.x = 3.0
    diagonal = (1.0, 1.0, 1.0, 0.01, 0.04, 0.09)
    message.pose.covariance = [
        diagonal[row] if row == col else 0.0 for row in range(6) for col in range(6)
    ]
    estimate = decode_estimate(
        message, "nav_msgs/msg/Odometry", "body", "world_position_fixed_rotation"
    )
    assert estimate.sample.velocity == pytest.approx((0.0, 3.0, 0.0))
    # The body x, y and z axes lie along world y, z and x.
    assert estimate.sigmas["attitude_rad_x"] == pytest.approx(0.2)
    assert estimate.sigmas["attitude_rad_y"] == pytest.approx(0.3)
    assert estimate.sigmas["attitude_rad_z"] == pytest.approx(0.1)
    assert estimate.sample.covariance == ()


def test_unsupported_message_type_is_rejected_before_access() -> None:
    """Reject an unsupported message type before reading its fields."""
    from evalviz_plotjuggler.estimate_decoding import decode_pose

    with pytest.raises(ValueError, match="unsupported estimate type"):
        decode_pose(object(), "sensor_msgs/msg/Imu", "body")


def test_audited_calibration_aliases_resolve(tmp_path: Path) -> None:
    """Read the audited key aliases and ignore audit metadata."""
    calibration = tmp_path / "binding.json"
    calibration.write_text(
        json.dumps(
            {
                "time_offset_ns": 5_000_000_000,
                "maximum_gap_s": 0.2,
                "alignment_window_s": 2.0,
                "tracked_frame": "vicon_body",
                "tracked_from_navigation": {
                    "position": [0.1, 0.0, 0.0],
                    "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
                },
                "audit": {"take": "fixture"},
            }
        ),
        encoding="utf-8",
    )
    binding = resolve_reference(
        profile_with(
            {
                "input": "truth",
                "calibration_path": str(calibration),
                "alignment": "initial_position_yaw",
                "anchor_estimator": "filter",
            },
            clock="vicon",
        )
    )
    assert binding is not None
    assert binding.clock_offset_ns == 5_000_000_000
    assert binding.max_gap_ns == 200_000_000
    assert binding.anchor_window_ns == 2_000_000_000
    assert binding.reference_frame == "vicon_body"
    assert binding.mount is not None
    assert binding.mount.position == (0.1, 0.0, 0.0)
    assert "audit" not in binding.settings

    # A prepared CSV is already on the source clock at the estimate frame.
    prepared = resolve_reference(
        profile_with(
            {"prepared_csv": "reference.csv", "calibration_path": str(calibration)},
            clock="vicon",
        )
    )
    assert prepared is not None
    assert (prepared.clock_offset_ns, prepared.mount, prepared.input) == (0, None, None)
    assert prepared.max_gap_ns == 200_000_000


def test_offset_reference_clock_matches_source_time() -> None:
    """Convert a reference on another clock with the declared offset only."""
    binding = resolve_reference(
        profile_with({"input": "truth", "clock_offset_ns": 7_000}, clock="vicon")
    )
    assert binding is not None
    truth = ReferenceBuffer(binding.max_gap_ns)
    truth.add(prepare_truth(sample(1_000), binding))
    assert truth.at(8_000) is not None
    assert truth.at(1_000) is None
    with pytest.raises(ValueError, match="without clock_offset_ns"):
        resolve_reference(profile_with({"input": "truth"}, clock="vicon"))


def test_alignment_needs_an_explicit_anchor() -> None:
    """Require an explicit anchor estimator for initial alignment."""
    with pytest.raises(ValueError, match="needs anchor_estimator"):
        resolve_reference(profile_with({"input": "truth", "alignment": "initial_position_yaw"}))


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ("1.5,0,0,0,0,0,0,1", "invalid literal"),
        ("10,nan,0,0,0,0,0,1", "finite"),
        ("10,0,0,0,0,0,0,0", "unit quaternion"),
        ("10,0,0,0,0,0,0", "NoneType"),
    ],
)
def test_prepared_reference_rows_are_validated(tmp_path: Path, row: str, message: str) -> None:
    """Name the failing line before any comparison runs."""
    path = tmp_path / "reference.csv"
    path.write_text(_CSV_HEADER + "0,0,0,0,0,0,0,1\n" + row + "\n", encoding="utf-8")
    binding = resolve_reference(profile_with({"prepared_csv": str(path)}))
    assert binding is not None
    with pytest.raises(ValueError, match=rf"reference\.csv:3: .*{message}"):
        load_prepared_reference(binding)


def test_prepared_reference_loads_every_row(tmp_path: Path) -> None:
    """Load all prepared reference rows for interpolation in the configured frames."""
    path = tmp_path / "reference.csv"
    path.write_text(_CSV_HEADER + "0,0,0,0,0,0,0,1\n100,1,0,0,0,0,0,1\n", encoding="utf-8")
    binding = resolve_reference(profile_with({"prepared_csv": str(path)}))
    assert binding is not None
    truth = load_prepared_reference(binding)
    middle = truth.at(50)
    assert middle is not None
    assert (middle.world, middle.tracked) == ("world", "body")
    assert middle.position == pytest.approx((0.5, 0.0, 0.0))
