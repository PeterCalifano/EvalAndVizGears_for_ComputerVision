"""Check live admission, source-time holds and alignment freezing at any replay rate."""

from __future__ import annotations

import math

import pytest
from scipy.spatial.transform import Rotation

from evalviz_plotjuggler.estimate_decoding import DecodedEstimate
from evalviz_plotjuggler.live_reference_matcher import REWIND_NS, LiveMatcher, MatchOutcome
from evalviz_plotjuggler.reference_comparison import (
    PoseSample,
    ReferenceBinding,
    ReferenceBuffer,
    resolve_reference,
)
from evalviz_plotjuggler.visualization_profile import JsonObject

NATIVE = "legged_nav_system_ros/msg/NavigationEstimate"
SECOND_NS = 1_000_000_000
STEP_NS = 20_000_000  # 50 Hz source rate.
# Known reference-world to estimate-world transform.
ALIGNMENT_YAW_RAD = math.pi / 2
ALIGNMENT_TRANSLATION_M = (1.0, 2.0, 0.0)


class FakeWall:
    """Monotonic wall clock advanced explicitly by the test."""

    def __init__(self) -> None:
        """Initialize the controllable wall clock."""
        self.now_s = 100.0

    def __call__(self) -> float:
        """Return the current wall-clock time in seconds."""
        return self.now_s


def profile_with(reference: JsonObject) -> JsonObject:
    """Return a two-estimator profile with an Odometry reference input."""
    return {
        "clock": "source",
        "frames": {"world": "world", "tracked": "imu"},
        "inputs": {
            "filter": {"role": "estimate", "topic": "/filter", "message_type": NATIVE},
            "graph": {"role": "estimate", "topic": "/graph", "message_type": NATIVE},
            "truth": {
                "role": "reference",
                "topic": "/truth",
                "message_type": "nav_msgs/msg/Odometry",
            },
        },
        "reference": reference,
    }


def aligned_binding(**extra: object) -> ReferenceBinding:
    """Resolve a binding that freezes alignment from the filter over one second."""
    binding = resolve_reference(
        profile_with(
            {
                "input": "truth",
                "alignment": "initial_position_yaw",
                "anchor_estimator": "filter",
                "anchor_window_s": 1.0,
                "max_gap_s": 0.1,
                **extra,
            }
        )
    )
    assert binding is not None
    return binding


def reference_at(stamp_ns: int) -> PoseSample:
    """Return the analytic reference pose in the reference world."""
    t = stamp_ns / SECOND_NS
    rotation = Rotation.from_euler("z", 0.2 * t)
    return PoseSample(stamp_ns, "world", "imu", (0.3 * t, 0.1 * t, 0.0), tuple(rotation.as_quat()))


def estimate_at(
    stamp_ns: int, *, offset_x_m: float = 0.0, session: int = 1, revision: int = 0
) -> DecodedEstimate:
    """Return the reference expressed in the estimate world, plus an optional x error."""
    reference = reference_at(stamp_ns)
    world = Rotation.from_euler("z", ALIGNMENT_YAW_RAD)
    position = world.apply(reference.position) + ALIGNMENT_TRANSLATION_M
    position[0] += offset_x_m
    quaternion = (world * Rotation.from_quat(reference.quaternion)).as_quat()
    sample = PoseSample(
        stamp_ns,
        "world",
        "imu",
        tuple(position),
        tuple(quaternion),
        session=session,
        revision=revision,
    )
    return DecodedEstimate(sample, {}, {})


def matcher_for(
    binding: ReferenceBinding, wall: FakeWall, prepared: ReferenceBuffer | None = None
) -> LiveMatcher:
    """Create a matcher with the filter and graph streams."""
    matcher = LiveMatcher(binding, prepared, clock=wall)
    matcher.add_stream("filter")
    matcher.add_stream("graph")
    return matcher


def test_slow_replay_freezes_alignment_from_source_time() -> None:
    """Freeze at 0.5x replay, where a wall-clock hold could never span the window."""
    wall = FakeWall()
    matcher = matcher_for(aligned_binding(), wall)
    results = []
    for step in range(150):
        stamp = step * STEP_NS
        wall.now_s += 2 * STEP_NS / SECOND_NS
        matcher.admit("filter", estimate_at(stamp))
        matcher.admit("graph", estimate_at(stamp, offset_x_m=0.1))
        # The reference arrives one source step behind the estimates.
        if step:
            matcher.add_reference(reference_at(stamp - STEP_NS))
        results.extend(matcher.release())

    alignment = matcher.alignment
    assert alignment is not None, "alignment must freeze from source-time progress"
    assert alignment.rotation.as_euler("xyz")[2] == pytest.approx(ALIGNMENT_YAW_RAD)
    assert alignment.translation == pytest.approx(ALIGNMENT_TRANSLATION_M)

    # Every estimate except the newest, whose reference never arrived, is matched.
    for name, error_x in (("filter", 0.0), ("graph", 0.1)):
        released = [result for result in results if result.name == name]
        assert [result.sample.stamp_ns for result in released] == [
            step * STEP_NS for step in range(149)
        ]
        assert {result.outcome for result in released} == {MatchOutcome.MATCHED}
        for result in released:
            assert result.values["error_position_m_x"] == pytest.approx(error_x, abs=1e-9)
            assert result.values["error_position_m_y"] == pytest.approx(0.0, abs=1e-9)
            assert result.values["error_attitude_rad_norm"] == pytest.approx(0.0, abs=1e-9)


def test_live_reference_rewind_discards_pending_estimates_and_refits_alignment() -> None:
    """Discard a pending 2 s estimate on reference rewind and fit the new epoch."""
    from dataclasses import replace

    matcher = matcher_for(aligned_binding(), FakeWall())
    for step in range(100):
        stamp_ns = step * STEP_NS
        matcher.add_reference(reference_at(stamp_ns))
        assert matcher.admit("filter", estimate_at(stamp_ns))
        matcher.release()
    assert matcher.alignment is not None

    assert matcher.admit("filter", estimate_at(2 * SECOND_NS))
    assert matcher.release() == []

    new_references = []
    for step in range(152):
        reference = reference_at(step * STEP_NS)
        x, y, z = reference.position
        new_references.append(replace(reference, position=(x + 9.0, y, z)))
    for reference in new_references[:101]:
        matcher.add_reference(reference)

    released = matcher.release()
    assert released == [], [
        (result.sample.stamp_ns, result.outcome, result.values.get("error_position_m_norm"))
        for result in released
    ]
    assert matcher.alignment is None
    assert matcher.reference_counts["resets"] == 1

    # Continue past the last admitted stamp so an estimate rewind cannot reset the matcher.
    results = []
    for reference in new_references[101:]:
        matcher.add_reference(reference)
        assert matcher.admit("filter", estimate_at(reference.stamp_ns))
        results.extend(matcher.release())

    assert matcher.alignment is not None
    assert [result.sample.stamp_ns for result in results] == [
        reference.stamp_ns for reference in new_references[101:]
    ]
    assert {result.outcome for result in results} == {MatchOutcome.MATCHED}
    for result in results:
        assert result.values["error_position_m_norm"] == pytest.approx(0.0, abs=1e-9)


def test_missing_reference_is_reported_after_source_wait_without_polling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Release unmatched estimates by source progress and look up only the queue head."""
    binding = resolve_reference(profile_with({"input": "truth", "max_gap_s": 0.1}))
    assert binding is not None
    wall = FakeWall()
    matcher = matcher_for(binding, wall)
    assert matcher.truth is not None
    lookups = 0
    lookup = matcher.truth.at

    def counted(stamp_ns: int) -> PoseSample | None:
        """Count reference lookups while forwarding them to the buffer."""
        nonlocal lookups
        lookups += 1
        return lookup(stamp_ns)

    monkeypatch.setattr(matcher.truth, "at", counted)
    for step in range(100):
        matcher.admit("filter", estimate_at(step * STEP_NS))
    released = matcher.release()

    # 2 s of source progress releases everything older than the 0.3 s allowance.
    assert [result.sample.stamp_ns for result in released] == [step * STEP_NS for step in range(84)]
    assert {result.outcome for result in released} == {MatchOutcome.REFERENCE_NOT_RECEIVED}
    assert all(result.values == {"reference_valid": 0} for result in released)
    assert matcher.states["filter"].counts["reference_not_received"] == 84

    lookups = 0
    for _ in range(10):
        assert matcher.release() == []
    assert lookups == 10, "a waiting stream must look up only its oldest entry per release"


def test_pending_estimates_respect_the_fixed_bound() -> None:
    """Drop the oldest held estimates instead of growing without a limit."""
    wall = FakeWall()
    matcher = LiveMatcher(aligned_binding(), clock=wall, max_pending=5)
    matcher.add_stream("filter")
    for step in range(12):
        matcher.admit("filter", estimate_at(step * STEP_NS))
        matcher.release()
    assert matcher.pending == 5
    assert sum(len(queue) for queue in matcher.queues.values()) == 5
    assert matcher.states["filter"].counts["pending_drops"] == 7


def test_same_stamp_revision_replaces_the_pending_estimate() -> None:
    """Compare the newest revision published before the reference arrived."""
    binding = resolve_reference(profile_with({"input": "truth", "max_gap_s": 0.1}))
    assert binding is not None
    matcher = matcher_for(binding, FakeWall())
    assert matcher.admit("graph", estimate_at(0, offset_x_m=0.5, revision=1))
    assert matcher.admit("graph", estimate_at(0, offset_x_m=0.2, revision=2))
    assert not matcher.admit("graph", estimate_at(0, offset_x_m=0.9, revision=2))
    matcher.add_reference(reference_at(0))
    (result,) = matcher.release()
    # Without alignment the error keeps the 1 m world translation plus the revision's 0.2 m.
    assert result.values["error_position_m_x"] == pytest.approx(1.2)
    assert matcher.states["graph"].counts["same_stamp_revision"] == 1
    assert matcher.states["graph"].counts["stale_or_duplicate"] == 1


def test_native_loop_restarts_with_prepared_reference_kept() -> None:
    """Admit a repeated native session after a rewind and freeze again on kept truth."""
    binding = resolve_reference(
        profile_with(
            {
                "prepared_csv": "unused.csv",
                "alignment": "initial_position_yaw",
                "anchor_estimator": "filter",
                "anchor_window_s": 1.0,
            }
        )
    )
    assert binding is not None
    prepared = ReferenceBuffer(binding.max_gap_ns)
    for step in range(200):
        prepared.add(reference_at(step * STEP_NS))
    wall = FakeWall()
    matcher = matcher_for(binding, wall, prepared)

    passes = []
    for _ in range(2):
        results = []
        for step in range(100):
            wall.now_s += 0.01
            matcher.admit("filter", estimate_at(step * STEP_NS))
            results.extend(matcher.release())
        passes.append(results)
        assert matcher.alignment is not None

    state = matcher.states["filter"]
    assert state.counts["resets"] == 1
    assert state.counts["admitted"] == 200
    assert state.counts["stale_or_duplicate"] == 0
    assert matcher.truth is prepared
    assert len(prepared.stamps) == 200
    for results in passes:
        assert len(results) > 50
        assert {result.outcome for result in results} == {MatchOutcome.MATCHED}


def test_graph_revision_of_an_older_stamp_is_not_a_rewind() -> None:
    """Keep the epoch when an older stamp carries a newer optimizer revision."""
    binding = resolve_reference(profile_with({"input": "truth"}))
    assert binding is not None
    matcher = matcher_for(binding, FakeWall())
    late = 5 * SECOND_NS
    assert matcher.admit("graph", estimate_at(late, revision=10))
    assert not matcher.admit("graph", estimate_at(late - REWIND_NS - STEP_NS, revision=11))
    assert matcher.states["graph"].counts["resets"] == 0
    assert matcher.admit("graph", estimate_at(0, revision=1))
    assert matcher.states["graph"].counts["resets"] == 1


def test_live_reference_rewind_drops_the_previous_epoch() -> None:
    """Clear old-epoch truth so a looped estimate cannot match it."""
    binding = resolve_reference(profile_with({"input": "truth", "max_gap_s": 0.1}))
    assert binding is not None
    matcher = matcher_for(binding, FakeWall())
    for step in range(200):
        matcher.add_reference(reference_at(step * STEP_NS))
    matcher.add_reference(reference_at(0))
    assert matcher.truth is not None
    assert matcher.truth.stamps == [0]
    assert matcher.reference_counts["resets"] == 1
