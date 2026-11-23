"""Decode the supported ROS estimate messages into the shared pose contract.

Decoding is the only middleware-aware step. A `DecodedEstimate` carries
everything the relay and the review need afterwards, so another transport can
build one directly. A `std_msgs/msg/String` is decoded only when its input
declares the normalized JSON Lines encoding, and then through the same
validator as the native socket.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, cast

import numpy as np
from numpy.typing import ArrayLike
from scipy.spatial.transform import Rotation

from .native_record_protocol import FIXED_ROTATION_CHART, POSE_ENCODING, PoseRecord, decode_record
from .reference_comparison import POSE_CHART, PoseSample, posterior_sigmas
from .visualization_profile import NATIVE_ESTIMATE_TYPE, POSE_MESSAGE_TYPES, STRING_MESSAGE_TYPE

if TYPE_CHECKING:
    from geometry_msgs.msg import Point, Pose, Vector3
    from std_msgs.msg import Header

# ROS types are loaded by name, and the message type string selects their fields.
type _RosMessage = Any

ESTIMATE_TYPES = POSE_MESSAGE_TYPES
ODOMETRY_TYPE = "nav_msgs/msg/Odometry"
_NATIVE_EXTRA_FIELDS = ("accelerometer_bias", "gyroscope_bias")
_NATIVE_RATE_FIELD = "angular_velocity_navigation"


@dataclass(frozen=True)
class DecodedEstimate:
    """Validated estimate with its plot-ready source fields.

    Attributes:
        sample: Pose, velocity and identity. Its covariance is dropped after
            the sigmas are computed.
        sigmas: Posterior marginal sigmas, empty when unavailable.
        extras: Additional finite source fields such as biases, by name.
    """

    sample: PoseSample
    sigmas: dict[str, float]
    extras: dict[str, float]


def stamp_ns(header: Header) -> int:
    """Read integer source time from a ROS Header.

    Args:
        header: ROS `std_msgs/Header`.

    Returns:
        The stamp in integer nanoseconds.
    """
    return int(header.stamp.sec) * 1_000_000_000 + int(header.stamp.nanosec)


def vector(message: Point | Vector3) -> tuple[float, float, float]:
    """Read a finite ROS three-vector.

    Args:
        message: ROS `Vector3` or `Point`.

    Returns:
        The components as floats.

    Raises:
        ValueError: A component is not finite.
    """
    values = float(message.x), float(message.y), float(message.z)
    if not all(map(math.isfinite, values)):
        raise ValueError("non-finite vector")
    return values


def source_pose(message: _RosMessage, message_type: str) -> Pose | None:
    """Return the ROS `Pose` carried by a supported pose message.

    Args:
        message: Supported pose message.
        message_type: Its ROS type name.

    Returns:
        The unmodified source pose, or None for a normalized JSON Lines
        envelope, which carries no ROS pose; build one from the decoded sample.
    """
    if message_type == STRING_MESSAGE_TYPE:
        return None
    return cast("Pose", message.pose.pose if message_type == ODOMETRY_TYPE else message.pose)


def _right_pose_covariance(rotation: Rotation, covariance: ArrayLike) -> tuple[float, ...]:
    """Re-express a fixed-axis 6x6 pose covariance in the right-local attitude chart."""
    jacobian = np.eye(6)
    jacobian[3:, 3:] = rotation.as_matrix().T
    expressed = jacobian @ np.asarray(covariance, dtype=float).reshape(6, 6) @ jacobian.T
    return tuple(float(value) for value in expressed.ravel())


def _decode_envelope(text: str, covariance_chart: str | None) -> PoseSample:
    """Decode a normalized JSON Lines pose carried in a String message.

    A record covariance is used only under the declared chart, as for
    Odometry; a record chart that contradicts the declaration is rejected.
    """
    record = decode_record(text)
    if not isinstance(record, PoseRecord):
        raise ValueError(f"expected a pose record, got {type(record).__name__}")
    norm = math.hypot(*record.quaternion_xyzw)
    x, y, z, w = (component / norm for component in record.quaternion_xyzw)
    quaternion = (x, y, z, w)
    chart = ""
    covariance: tuple[float, ...] = ()
    if record.covariance is not None and covariance_chart is not None:
        if record.covariance_chart != covariance_chart:
            raise ValueError(
                f"covariance chart {record.covariance_chart!r} differs from the declared "
                f"{covariance_chart!r}"
            )
        chart, covariance = POSE_CHART, record.covariance
        if covariance_chart == FIXED_ROTATION_CHART:
            covariance = _right_pose_covariance(Rotation.from_quat(quaternion), covariance)
    return PoseSample(
        record.stamp_ns,
        record.world,
        record.tracked,
        record.position_m,
        quaternion,
        record.velocity_world_mps,
        covariance,
        chart,
        record.session,
        record.revision,
    )


def decode_pose(
    message: _RosMessage,
    message_type: str,
    tracked: str,
    covariance_chart: str | None = None,
    encoding: str | None = None,
) -> PoseSample:
    """Decode pose, source frames, and published posterior metadata.

    Args:
        message: Supported pose message.
        message_type: Its ROS type name.
        tracked: Tracked frame for types without a child frame.
        covariance_chart: Declared Odometry or JSON Lines pose covariance convention.
        encoding: Declared input encoding; `evalviz_jsonl_v1` for a String envelope.

    Returns:
        A pose sample with a normalized quaternion and world-axis velocity.

    Raises:
        ValueError: The type or encoding is unsupported, or the pose, frames,
            velocity or envelope are invalid.
    """
    if encoding is not None or message_type == STRING_MESSAGE_TYPE:
        if (encoding, message_type) != (POSE_ENCODING, STRING_MESSAGE_TYPE):
            raise ValueError(f"unsupported pose encoding {encoding!r} for {message_type}")
        return _decode_envelope(message.data, covariance_chart)
    if message_type not in ESTIMATE_TYPES:
        raise ValueError(f"unsupported estimate type {message_type}")

    # Extract the type-specific frame, velocity and posterior fields.
    pose = cast("Pose", source_pose(message, message_type))
    velocity = None
    covariance: tuple[float, ...] = ()
    chart = ""
    session = revision = 0
    if message_type == ODOMETRY_TYPE:
        tracked = message.child_frame_id
    elif message_type == NATIVE_ESTIMATE_TYPE:
        tracked = message.child_frame_id
        velocity = vector(message.velocity_world)
        chart = message.covariance_chart
        covariance = tuple(message.covariance) if message.error_state_dimension == 15 else ()
        session, revision = int(message.session), int(message.optimizer_update)

    # Validate the pose and frames shared by every type.
    position = vector(pose.position)
    raw = pose.orientation
    quaternion = float(raw.x), float(raw.y), float(raw.z), float(raw.w)
    norm = math.hypot(*quaternion)
    if not math.isfinite(norm) or abs(norm - 1.0) > 1e-3:
        raise ValueError("invalid pose quaternion")
    if not message.header.frame_id or not tracked:
        raise ValueError("pose frame and tracked frame must be set")
    x, y, z, w = (component / norm for component in quaternion)

    # Rotate the child-frame twist to world and re-express a fixed-axis covariance.
    if message_type == ODOMETRY_TYPE:
        rotation = Rotation.from_quat((x, y, z, w))
        velocity = tuple(rotation.apply(vector(message.twist.twist.linear)))
        if covariance_chart == POSE_CHART:
            chart, covariance = POSE_CHART, tuple(message.pose.covariance)
        elif covariance_chart == FIXED_ROTATION_CHART:
            chart = POSE_CHART
            covariance = _right_pose_covariance(rotation, message.pose.covariance)

    return PoseSample(
        stamp_ns(message.header),
        message.header.frame_id,
        tracked,
        position,
        (x, y, z, w),
        velocity,
        covariance,
        chart,
        session,
        revision,
    )


def estimate_extras(message: _RosMessage, message_type: str) -> dict[str, float]:
    """Read finite bias and angular-rate fields of the native estimate.

    Args:
        message: Supported pose message.
        message_type: Its ROS type name.

    Returns:
        Fields by `<name>_<axis>`; empty for generic types. A non-finite or
        invalid vector is omitted.
    """
    if message_type != NATIVE_ESTIMATE_TYPE:
        return {}
    fields = list(_NATIVE_EXTRA_FIELDS)
    if message.angular_velocity_valid:
        fields.append(_NATIVE_RATE_FIELD)
    values: dict[str, float] = {}
    for name in fields:
        try:
            components = vector(getattr(message, name))
        except ValueError:
            continue
        values.update(
            {f"{name}_{axis}": value for axis, value in zip("xyz", components, strict=True)}
        )
    return values


def decode_estimate(
    message: _RosMessage,
    message_type: str,
    tracked: str,
    covariance_chart: str | None = None,
    encoding: str | None = None,
) -> DecodedEstimate:
    """Decode an estimate and compute its posterior sigmas once.

    Args:
        message: Supported pose message.
        message_type: Its ROS type name.
        tracked: Tracked frame for types without a child frame.
        covariance_chart: Declared Odometry or JSON Lines pose covariance convention.
        encoding: Declared input encoding; see `decode_pose`.

    Returns:
        The decoded estimate.

    Raises:
        ValueError: The message is invalid; see `decode_pose`.
    """
    sample = decode_pose(message, message_type, tracked, covariance_chart, encoding)
    sigmas = posterior_sigmas(sample)
    return DecodedEstimate(
        replace(sample, covariance=()), sigmas, estimate_extras(message, message_type)
    )


def state_values(estimate: DecodedEstimate) -> dict[str, float | int]:
    """Flatten plot-ready, source-derived estimate fields.

    Args:
        estimate: Decoded estimate.

    Returns:
        Position, rotation vector, velocity, extras, sigmas, covariance
        validity and revision, in that order.
    """
    sample = estimate.sample
    values: dict[str, float | int] = {
        f"position_m_{axis}": value for axis, value in zip("xyz", sample.position, strict=False)
    }
    rotation = Rotation.from_quat(sample.quaternion).as_rotvec()
    values.update(
        {f"rotation_vector_rad_{axis}": float(v) for axis, v in zip("xyz", rotation, strict=False)}
    )
    if sample.velocity is not None:
        values.update(
            {f"velocity_mps_{axis}": v for axis, v in zip("xyz", sample.velocity, strict=False)}
        )
    values.update(estimate.extras)
    values.update({f"sigma_{key}": value for key, value in estimate.sigmas.items()})
    values["covariance_valid"] = int(bool(estimate.sigmas))
    values["revision"] = sample.revision
    return values
