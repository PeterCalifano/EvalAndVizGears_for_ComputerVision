"""Source-time pose comparison independent of middleware and rendering.

Time is integer nanoseconds on the estimator source clock. A reference is
matched exactly or interpolated inside one bracket, never extrapolated. The
attitude error is the right-local tangent at the estimate, while position and
velocity errors use world axes.
"""

from __future__ import annotations

import bisect
import csv
import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import SupportsFloat, SupportsIndex

import numpy as np
from scipy.spatial.transform import Rotation, Slerp

from .visualization_profile import JsonObject, comparison_configured, reference_input

NAVIGATION_CHART = "world_p_v_right_rotation_ba_bg"
POSE_CHART = "world_position_right_rotation"

DEFAULT_MAX_GAP_S = 0.1
DEFAULT_ANCHOR_WINDOW_S = 1.0
LIVE_RETENTION_NS = 60_000_000_000
LIVE_CAPACITY = 65_536
QUATERNION_TOLERANCE = 1e-3
# Audited calibrations may print mount rotations with reduced precision.
MOUNT_QUATERNION_TOLERANCE = 1e-2

# Calibration keys read from the audited JSON, including their audited aliases.
_CALIBRATION_KEYS = frozenset(
    {
        "clock_offset_ns",
        "time_offset_ns",
        "world_frame",
        "tracked_frame",
        "max_gap_s",
        "maximum_gap_s",
        "alignment",
        "anchor_estimator",
        "anchor_window_s",
        "alignment_window_s",
        "tracked_from_navigation",
    }
)
# A prepared CSV is already on the estimator clock at the estimate frame.
_PREPARED_EXCLUDED_KEYS = frozenset({"tracked_from_navigation", "time_offset_ns", "tracked_frame"})


@dataclass(frozen=True)
class PoseSample:
    """One pose or posterior at an integer source timestamp."""

    stamp_ns: int
    world: str
    tracked: str
    position: tuple[float, float, float]
    quaternion: tuple[float, float, float, float]
    velocity: tuple[float, float, float] | None = None
    covariance: tuple[float, ...] = ()
    chart: str = ""
    session: int = 0
    revision: int = 0


def posterior_sigmas(sample: PoseSample) -> dict[str, float]:
    """Return marginal standard deviations from a validated published chart.

    Args:
        sample: Estimate with its published covariance and chart.

    Returns:
        Sigma per chart block and axis, or an empty mapping when the chart is
        unknown or the covariance is not finite, symmetric and positive
        semi-definite.
    """
    if sample.chart == NAVIGATION_CHART:
        groups: tuple[str, ...] = (
            "position_m",
            "velocity_mps",
            "attitude_rad",
            "accel_bias_mps2",
            "gyro_bias_radps",
        )
    elif sample.chart == POSE_CHART:
        groups = ("position_m", "attitude_rad")
    else:
        return {}

    dimension = 3 * len(groups)
    if len(sample.covariance) != dimension**2:
        return {}
    covariance = np.asarray(sample.covariance).reshape(dimension, dimension)
    if not np.isfinite(covariance).all():
        return {}
    scale = float(np.max(np.abs(covariance)))
    if scale == 0 or not np.allclose(covariance, covariance.T, rtol=1e-9, atol=scale * 1e-12):
        return {}
    if np.linalg.eigvalsh((covariance + covariance.T) / 2)[0] < -scale * 1e-12:
        return {}

    sigmas = np.sqrt(np.maximum(covariance.diagonal(), 0)).reshape(len(groups), 3)
    return {
        f"{group}_{axis}": float(sigma)
        for group, values in zip(groups, sigmas, strict=True)
        for axis, sigma in zip("xyz", values, strict=True)
    }


def compare(
    estimate: PoseSample, truth: PoseSample, sigmas: dict[str, float] | None = None
) -> dict[str, float]:
    """Compare matched poses and return errors and estimator-only bounds.

    Args:
        estimate: Estimate at the comparison stamp.
        truth: Reference at the same stamp, world and tracked frame.
        sigmas: Posterior sigmas already computed for `estimate`. When None,
            they are computed from its covariance.

    Returns:
        Error components and norms, ±3σ bounds and `covariance_valid`.

    Raises:
        ValueError: The stamps, worlds or tracked frames differ.
    """
    if (estimate.stamp_ns, estimate.world, estimate.tracked) != (
        truth.stamp_ns,
        truth.world,
        truth.tracked,
    ):
        raise ValueError("comparison requires the same source time, world and tracked frame")

    # Express the attitude error in the right-local tangent at the estimate.
    attitude = -(
        Rotation.from_quat(estimate.quaternion).inv() * Rotation.from_quat(truth.quaternion)
    ).as_rotvec()
    position = np.subtract(estimate.position, truth.position)
    vectors = {"position_m": position, "attitude_rad": attitude}
    if estimate.velocity is not None and truth.velocity is not None:
        vectors["velocity_mps"] = np.subtract(estimate.velocity, truth.velocity)

    result: dict[str, float] = {}
    for name, vector in vectors.items():
        for axis, component in zip("xyz", vector, strict=True):
            result[f"error_{name}_{axis}"] = float(component)
        result[f"error_{name}_norm"] = float(np.linalg.norm(vector))

    if sigmas is None:
        sigmas = posterior_sigmas(estimate)
    for name, sigma in sigmas.items():
        result[f"upper_{name}"] = 3 * sigma
        result[f"lower_{name}"] = -3 * sigma
    result["covariance_valid"] = float(bool(sigmas))
    return result


class ReferenceBuffer:
    """Store bounded or complete truth and sample within valid brackets."""

    def __init__(
        self, max_gap_ns: int, retention_ns: int | None = None, capacity: int | None = None
    ) -> None:
        """Create an empty buffer.

        Args:
            max_gap_ns: Largest bracket that may be interpolated.
            retention_ns: Source-time span kept behind the newest sample, or
                None to keep everything.
            capacity: Largest number of samples kept, or None for no limit.
        """
        self.max_gap_ns = max_gap_ns
        self.retention_ns = retention_ns
        self.capacity = capacity
        self.stamps: list[int] = []
        self.samples: dict[int, PoseSample] = {}

    @property
    def newest_ns(self) -> int | None:
        """Return the newest stored stamp, or None when empty."""
        return self.stamps[-1] if self.stamps else None

    def clear(self) -> None:
        """Remove every stored sample."""
        self.stamps.clear()
        self.samples.clear()

    def add(self, sample: PoseSample) -> None:
        """Insert a sample in source-time order, replacing a repeated time.

        Args:
            sample: Reference pose at an integer source-clock timestamp in nanoseconds.

        Returns:
            None. The buffer is trimmed by its configured capacity and retention.

        Raises:
            No exceptions are explicitly raised.
        """
        if sample.stamp_ns not in self.samples:
            bisect.insort(self.stamps, sample.stamp_ns)
        self.samples[sample.stamp_ns] = sample

        # Trim the live buffer by count and by source-time retention.
        cut = 0 if self.capacity is None else max(0, len(self.stamps) - self.capacity)
        if self.retention_ns is not None:
            cut = max(cut, bisect.bisect_left(self.stamps, self.stamps[-1] - self.retention_ns))
        if cut:
            for stamp in self.stamps[:cut]:
                del self.samples[stamp]
            del self.stamps[:cut]

    def at(self, stamp_ns: int) -> PoseSample | None:
        """Match exactly or interpolate inside one compatible bracket.

        Args:
            stamp_ns: Requested estimator source-clock timestamp in nanoseconds.

        Returns:
            The exact sample, or a pose interpolated in the common world and tracked
            frames. Position in metres and available velocity in metres per second are
            linear; orientation follows the shortest quaternion arc. Returns None outside
            the stored range, across incompatible frames, or beyond the maximum gap.

        Raises:
            ValueError: An interpolated bracket contains an invalid quaternion.
        """
        if stamp_ns in self.samples:
            return self.samples[stamp_ns]
        index = bisect.bisect_left(self.stamps, stamp_ns)
        if index == 0 or index == len(self.stamps):
            return None
        left, right = (self.samples[self.stamps[i]] for i in (index - 1, index))
        span = right.stamp_ns - left.stamp_ns
        if span > self.max_gap_ns or (left.world, left.tracked) != (right.world, right.tracked):
            return None

        # Interpolate position and velocity linearly and attitude on the shortest arc.
        fraction = (stamp_ns - left.stamp_ns) / span
        rotation = Slerp([0, 1], Rotation.from_quat([left.quaternion, right.quaternion]))(fraction)
        velocity = None
        if left.velocity is not None and right.velocity is not None:
            velocity = tuple(
                (1 - fraction) * np.asarray(left.velocity) + fraction * np.asarray(right.velocity)
            )
        return replace(
            left,
            stamp_ns=stamp_ns,
            position=tuple(
                (1 - fraction) * np.asarray(left.position) + fraction * np.asarray(right.position)
            ),
            quaternion=tuple(rotation.as_quat()),
            velocity=velocity,
        )


@dataclass(frozen=True)
class WorldAlignment:
    """Frozen rigid transform from reference world to comparison world."""

    rotation: Rotation
    translation: tuple[float, float, float]
    world: str

    def apply(self, truth: PoseSample) -> PoseSample:
        """Express reference positions, orientations and velocity in the estimate world.

        Args:
            truth: Reference pose in the reference world, at a source-clock timestamp.

        Returns:
            A copy in the comparison world, with position in metres, velocity in metres
            per second and orientation rotated into that world. The timestamp and tracked
            frame are unchanged.

        Raises:
            ValueError: The reference quaternion is invalid.
        """
        return replace(
            truth,
            world=self.world,
            position=tuple(self.rotation.apply(truth.position) + self.translation),
            quaternion=tuple((self.rotation * Rotation.from_quat(truth.quaternion)).as_quat()),
            velocity=None if truth.velocity is None else tuple(self.rotation.apply(truth.velocity)),
        )


def fit_initial_yaw(pairs: list[tuple[PoseSample, PoseSample]]) -> WorldAlignment:
    """Fit the existing G1 initial yaw and position convention on matched samples.

    Args:
        pairs: Matched estimate and reference samples from the anchor window.

    Returns:
        The yaw rotation and translation that best map the reference onto the estimate.
    """
    estimates, truth = zip(*pairs, strict=True)
    estimate_rotations = Rotation.from_quat([sample.quaternion for sample in estimates])
    truth_rotations = Rotation.from_quat([sample.quaternion for sample in truth])
    relative = (estimate_rotations * truth_rotations.inv()).as_matrix()
    heading = np.arctan2(relative[:, 1, 0], relative[:, 0, 0])
    yaw = float(np.arctan2(np.sin(heading).sum(), np.cos(heading).sum()))
    rotation = Rotation.from_rotvec([0, 0, yaw])
    truth_positions = rotation.apply([sample.position for sample in truth])
    translation = np.subtract([sample.position for sample in estimates], truth_positions).mean(
        axis=0
    )
    return WorldAlignment(rotation, tuple(translation), estimates[0].world)


@dataclass(frozen=True)
class SensorMount:
    """Rigid pose of the estimate frame expressed in the reference body frame."""

    position: tuple[float, float, float]
    quaternion: tuple[float, float, float, float]


@dataclass(frozen=True)
class ReferenceBinding:
    """Resolved clock, frame and alignment contract between reference and estimates.

    Both the live relay and the offline review use this one binding, so their
    defaults and audited aliases cannot drift apart.
    """

    world_frame: str
    tracked_frame: str
    reference_frame: str | None
    input: str | None
    prepared_csv: Path | None
    clock_offset_ns: int
    max_gap_ns: int
    alignment: bool
    anchor: str | None
    anchor_window_ns: int
    mount: SensorMount | None
    settings: JsonObject = field(compare=False, repr=False)


def _first(settings: JsonObject, names: tuple[str, ...], default: object) -> object:
    """Return the first configured value among a key and its audited aliases."""
    return next((settings[name] for name in names if name in settings), default)


def _positive_seconds_ns(value: object, name: str) -> int:
    """Convert a positive finite duration in seconds to integer nanoseconds."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not value > 0:
        raise ValueError(f"reference {name} must be a positive number of seconds")
    if not math.isfinite(value):
        raise ValueError(f"reference {name} must be finite")
    return round(float(value) * 1e9)


def _unit_quaternion(
    values: Iterable[str | SupportsFloat | SupportsIndex], tolerance: float
) -> tuple[float, float, float, float]:
    """Validate and normalize an xyzw quaternion."""
    quaternion = tuple(float(value) for value in values)
    if len(quaternion) != 4:
        raise ValueError("quaternion needs four components")
    norm = math.hypot(*quaternion)
    if not math.isfinite(norm) or abs(norm - 1.0) > tolerance:
        raise ValueError("quaternion is not a finite unit quaternion")
    x, y, z, w = (component / norm for component in quaternion)
    return x, y, z, w


def _finite_vector(
    values: Iterable[str | SupportsFloat | SupportsIndex],
) -> tuple[float, float, float]:
    """Validate a finite three-vector."""
    vector = tuple(float(value) for value in values)
    if len(vector) != 3 or not all(map(math.isfinite, vector)):
        raise ValueError("vector needs three finite components")
    x, y, z = vector
    return x, y, z


def _read_calibration(path: Path) -> JsonObject:
    """Read the known keys of an audited calibration JSON file."""

    def reject_constant(constant: str) -> None:
        """Reject a non-finite JSON numeric constant.

        Args:
            constant: The non-finite JSON token supplied by the decoder.

        Returns:
            Never returns normally.

        Raises:
            ValueError: Always, because the constant is non-finite.
        """
        raise ValueError(f"non-finite value {constant}")

    try:
        content = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)
    except (OSError, ValueError) as error:
        raise ValueError(f"{path}: {error}") from error
    if not isinstance(content, dict):
        raise ValueError(f"{path}: calibration must be a JSON object")
    # Ignore audit metadata; only the binding keys affect the comparison.
    return {key: value for key, value in content.items() if key in _CALIBRATION_KEYS}


def reference_settings(profile: JsonObject) -> JsonObject:
    """Merge the audited calibration with the profile, giving the profile precedence.

    Args:
        profile: Resolved profile dictionary.

    Returns:
        The merged reference settings, recorded verbatim in review summaries.

    Raises:
        ValueError: The calibration file cannot be read.
    """
    settings = dict(profile.get("reference", {}))
    if path := settings.get("calibration_path"):
        calibration = _read_calibration(Path(path))
        if settings.get("prepared_csv"):
            calibration = {
                key: value
                for key, value in calibration.items()
                if key not in _PREPARED_EXCLUDED_KEYS
            }
            calibration["tracked_frame"] = profile["frames"]["tracked"]
        settings = {**calibration, **settings}
    settings.setdefault("world_frame", profile["frames"]["world"])
    return settings


def _mount(
    value: Mapping[str, Iterable[str | SupportsFloat | SupportsIndex]] | None,
) -> SensorMount | None:
    """Validate the optional reference-to-estimate rigid mount."""
    if not value:
        return None
    try:
        return SensorMount(
            _finite_vector(value["position"]),
            _unit_quaternion(value["quaternion_xyzw"], MOUNT_QUATERNION_TOLERANCE),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"reference tracked_from_navigation is invalid: {error}") from error


def _clock_offset_ns(value: object) -> int:
    """Validate an integer clock offset, accepting an integral JSON float."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("reference clock offset must be an integer number of nanoseconds")
    return value


def resolve_reference(profile: JsonObject) -> ReferenceBinding | None:
    """Resolve and validate the reference binding shared by live and review.

    Args:
        profile: Resolved profile dictionary or capture snapshot.

    Returns:
        The binding, or None when no reference comparison is configured.

    Raises:
        ValueError: The calibration, alignment anchor, frames or reference
            clock are inconsistent.

    Example:
        >>> from evalviz_plotjuggler.visualization_profile import load_builtin_profile
        >>> resolve_reference(load_builtin_profile("g1")).max_gap_ns
        100000000
    """
    if not comparison_configured(profile):
        return None
    settings = reference_settings(profile)
    prepared = settings.get("prepared_csv")
    live_input = None if prepared else reference_input(profile)
    offset_names = ("clock_offset_ns", "time_offset_ns")

    # Require an explicit anchor that is one of the estimate inputs.
    alignment = settings.get("alignment", "none")
    if alignment not in {"none", "initial_position_yaw"}:
        raise ValueError(f"reference alignment {alignment!r} is not supported")
    anchor = settings.get("anchor_estimator")
    if alignment == "initial_position_yaw" and anchor is None:
        raise ValueError(
            "reference.alignment initial_position_yaw needs anchor_estimator; "
            "review older captures with --profile"
        )
    if anchor is not None and profile["inputs"].get(anchor, {}).get("role") != "estimate":
        raise ValueError("reference anchor_estimator must name an input with role estimate")

    # Accept a live reference on another clock only with a declared conversion.
    if live_input is not None:
        clock = profile.get("clock", "source")
        reference_clock = profile.get("reference", {}).get("clock") or (
            profile["inputs"][live_input].get("clock", clock)
        )
        if reference_clock != clock and not any(name in settings for name in offset_names):
            raise ValueError(
                f"reference clock {reference_clock!r} differs from {clock!r} "
                "without clock_offset_ns"
            )

    return ReferenceBinding(
        world_frame=str(settings["world_frame"]),
        tracked_frame=profile["frames"]["tracked"],
        reference_frame=settings.get("tracked_frame"),
        input=live_input,
        prepared_csv=Path(prepared) if prepared else None,
        clock_offset_ns=_clock_offset_ns(_first(settings, offset_names, 0)),
        max_gap_ns=_positive_seconds_ns(
            _first(settings, ("max_gap_s", "maximum_gap_s"), DEFAULT_MAX_GAP_S), "max_gap_s"
        ),
        alignment=alignment == "initial_position_yaw",
        anchor=anchor,
        anchor_window_ns=_positive_seconds_ns(
            _first(settings, ("anchor_window_s", "alignment_window_s"), DEFAULT_ANCHOR_WINDOW_S),
            "anchor_window_s",
        ),
        mount=_mount(settings.get("tracked_from_navigation")),
        settings=settings,
    )


def check_estimate_clocks(profile: JsonObject) -> None:
    """Require every estimate input on the profile source clock.

    Args:
        profile: Resolved profile dictionary or capture snapshot.

    Raises:
        ValueError: An estimate input declares another clock.
    """
    clock = profile.get("clock", "source")
    for name, entry in profile["inputs"].items():
        if entry["role"] == "estimate" and entry.get("clock", clock) != clock:
            raise ValueError(f"inputs.{name}: estimate clock differs from the profile clock")


def prepare_truth(sample: PoseSample, binding: ReferenceBinding) -> PoseSample:
    """Apply the declared clock conversion and rigid sensor mount to a live reference.

    Args:
        sample: Decoded reference pose on its own clock and body frame.
        binding: Resolved reference binding.

    Returns:
        The reference at the estimate tracked frame on the source clock.

    Raises:
        ValueError: The reference frames disagree with the binding.
    """
    if sample.tracked != (binding.reference_frame or sample.tracked):
        raise ValueError(f"reference frame {sample.tracked!r} disagrees with its declared binding")
    if sample.world != binding.world_frame:
        raise ValueError(f"reference world {sample.world!r} disagrees with its declared binding")

    # Compose the mount on the right; the mounted frame has no measured velocity.
    if binding.mount is not None:
        world_from_reference = Rotation.from_quat(sample.quaternion)
        sample = replace(
            sample,
            tracked=binding.tracked_frame,
            velocity=None,
            position=tuple(
                np.asarray(sample.position) + world_from_reference.apply(binding.mount.position)
            ),
            quaternion=tuple(
                (world_from_reference * Rotation.from_quat(binding.mount.quaternion)).as_quat()
            ),
        )
    if sample.tracked != binding.tracked_frame:
        raise ValueError("reference and estimate use different physical tracked frames")
    return replace(sample, stamp_ns=sample.stamp_ns + binding.clock_offset_ns)


def live_reference_buffer(binding: ReferenceBinding) -> ReferenceBuffer:
    """Allocate the bounded buffer for reference poses received live.

    Args:
        binding: Resolved reference binding.

    Returns:
        An empty buffer with live retention and capacity limits.
    """
    return ReferenceBuffer(binding.max_gap_ns, LIVE_RETENTION_NS, LIVE_CAPACITY)


def _prepared_sample(row: dict[str, str], binding: ReferenceBinding) -> PoseSample:
    """Validate and decode one prepared reference CSV row."""
    position = _finite_vector(row[f"position_{axis}"] for axis in range(3))
    quaternion = _unit_quaternion(
        (row[f"quaternion_xyzw_{axis}"] for axis in range(4)), QUATERNION_TOLERANCE
    )
    velocity = (
        _finite_vector(row[f"velocity_world_{axis}"] for axis in range(3))
        if "velocity_world_0" in row
        else None
    )
    return PoseSample(
        int(row["timestamp_ns"]),
        binding.world_frame,
        binding.tracked_frame,
        position,
        quaternion,
        velocity,
    )


def load_prepared_reference(binding: ReferenceBinding) -> ReferenceBuffer:
    """Read and validate the complete prepared reference once.

    Args:
        binding: Resolved binding with a prepared CSV.

    Returns:
        An unbounded buffer with every prepared row.

    Raises:
        ValueError: The file is unreadable, empty, or a row has a missing,
            non-integer or non-finite value or a non-unit quaternion. The
            message names the file line.
    """
    if binding.prepared_csv is None:
        raise ValueError("the reference binding has no prepared CSV")
    path = binding.prepared_csv
    buffer = ReferenceBuffer(binding.max_gap_ns)
    try:
        with path.open(newline="", encoding="utf-8") as stream:
            table = csv.DictReader(stream)
            for row in table:
                try:
                    buffer.add(_prepared_sample(row, binding))
                except KeyError as error:
                    raise ValueError(f"{path}:{table.line_num}: missing column {error}") from error
                except (TypeError, ValueError) as error:
                    raise ValueError(f"{path}:{table.line_num}: {error}") from error
    except OSError as error:
        raise ValueError(f"{path}: {error}") from error
    if not buffer.stamps:
        raise ValueError(f"{path}: prepared reference has no rows")
    return buffer
