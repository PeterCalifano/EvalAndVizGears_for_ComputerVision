"""Source-time admission, reference matching and alignment for live estimates.

The relay owns ROS decoding and publishing; this module owns which estimates
are admitted, when each one is compared, and when the shared alignment
freezes. Every hold is measured in source time, so a replay at any rate gives
the same result. Wall time only detects a stream that stopped delivering.
"""

from __future__ import annotations

import time
from collections import Counter, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from .estimate_decoding import DecodedEstimate
from .reference_comparison import (
    PoseSample,
    ReferenceBinding,
    ReferenceBuffer,
    WorldAlignment,
    compare,
    fit_initial_yaw,
    live_reference_buffer,
)

MAX_PENDING = 8192
MAX_ANCHOR_PAIRS = 8192
# A backward source step larger than this starts a new replay epoch.
REWIND_NS = 1_000_000_000
# Source-time allowance for a reference that arrives after its estimate.
REFERENCE_WAIT_NS = 300_000_000
# Wall time without receipts after which a stream's held entries are released.
STALL_S = 2.0


class MatchOutcome(StrEnum):
    """Why a comparison was or was not published as valid."""

    MATCHED = "matched"
    NO_REFERENCE_BRACKET = "no_reference_bracket"
    REFERENCE_NOT_RECEIVED = "reference_not_received"
    ALIGNMENT_NOT_FROZEN = "alignment_not_frozen"
    COMPARISON_REJECTED = "comparison_rejected"

    @property
    def message(self) -> str:
        """Return the outcome as diagnostic text."""
        return self.value.replace("_", " ")


@dataclass
class StreamState:
    """Current source generation, time bounds and counters for one estimate stream."""

    session: int | None = None
    last_stamp: int = -1
    last_revision: int = -1
    compared: int = -1
    received_at: float = 0.0
    error: str = ""
    counts: Counter[str] = field(default_factory=Counter)


@dataclass
class _Pending:
    """Estimate waiting for its reference, the alignment, or both."""

    estimate: DecodedEstimate
    reference: PoseSample | None = None
    outcome: MatchOutcome | None = None

    @property
    def stamp_ns(self) -> int:
        """Return the estimate source stamp."""
        return self.estimate.sample.stamp_ns


@dataclass
class _Queue:
    """Pending estimates of one stream in source order.

    `unresolved` entries still wait for a reference decision; `resolved`
    entries have one and precede every unresolved entry.
    """

    unresolved: deque[_Pending] = field(default_factory=deque)
    resolved: deque[_Pending] = field(default_factory=deque)

    def __len__(self) -> int:
        """Return the number of pending entries."""
        return len(self.unresolved) + len(self.resolved)

    def head(self) -> _Pending | None:
        """Return the oldest entry."""
        queue = self.resolved or self.unresolved
        return queue[0] if queue else None

    def tail(self) -> _Pending | None:
        """Return the newest entry."""
        queue = self.unresolved or self.resolved
        return queue[-1] if queue else None

    def pop_head(self) -> None:
        """Remove the oldest entry."""
        (self.resolved or self.unresolved).popleft()

    def clear(self) -> None:
        """Remove every entry."""
        self.unresolved.clear()
        self.resolved.clear()


@dataclass(frozen=True)
class ComparisonResult:
    """One comparison ready to publish at its estimate source stamp."""

    name: str
    sample: PoseSample
    values: dict[str, float | int]
    outcome: MatchOutcome


class LiveMatcher:
    """Admit estimates and release reference comparisons in source-time order.

    The fit keeps the first 8,192 matched anchor stamps in the anchor window.
    Additional in-window pairs increment the anchor stream's
    `anchor_pair_drops` counter. A matched stamp at or past the window end
    can still trigger the fit when the store is full.
    """

    def __init__(
        self,
        binding: ReferenceBinding | None,
        prepared: ReferenceBuffer | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_pending: int = MAX_PENDING,
    ) -> None:
        """Create a matcher without streams.

        Args:
            binding: Resolved reference binding, or None to only admit estimates.
            prepared: Complete prepared reference, read once by the caller and
                kept across every reset.
            clock: Monotonic wall clock in seconds, used for receipt ages and
                stall detection only.
            max_pending: Largest number of estimates held across all streams.
        """
        self.binding = binding
        self.prepared = prepared
        self.clock = clock
        self.max_pending = max_pending
        self.truth = prepared
        if binding is not None and prepared is None:
            self.truth = live_reference_buffer(binding)
        self.states: dict[str, StreamState] = {}
        self.queues: dict[str, _Queue] = {}
        self.pending = 0
        self.pairs: list[tuple[PoseSample, PoseSample]] = []
        self.alignment: WorldAlignment | None = None
        self.reference_counts: Counter[str] = Counter()
        self.reference_received_at = 0.0
        self.reference_error = ""

    # -- Inputs ------------------------------------------------------------

    def add_stream(self, name: str) -> None:
        """Register an estimate stream.

        Args:
            name: Estimate input name.
        """
        self.states[name] = StreamState()
        self.queues[name] = _Queue()

    def reject_estimate(self, name: str, error: str) -> None:
        """Count an estimate that failed decoding or frame validation.

        Args:
            name: Estimate input name.
            error: Reason reported in health.
        """
        state = self.states[name]
        state.counts["invalid"] += 1
        state.error = error

    def reject_reference(self, error: str) -> None:
        """Count a reference that failed decoding or binding validation.

        Args:
            error: Reason reported in health.
        """
        self.reference_counts["invalid"] += 1
        self.reference_error = error

    def admit(self, name: str, estimate: DecodedEstimate) -> bool:
        """Admit a newer estimate or revision and queue it for comparison.

        A source step back by more than `REWIND_NS` starts a new epoch unless
        it carries an optimizer revision at least as new as the last one. A
        session change of the anchor, or any rewind, resets the shared
        comparison; another stream's session change resets only that stream.
        A same-stamp revision eligible for comparison also updates its
        retained anchor pair until the alignment freezes.

        Args:
            name: Estimate input name.
            estimate: Decoded estimate.

        Returns:
            True when the estimate should be published.
        """
        state = self.states[name]
        sample = estimate.sample
        stamp = sample.stamp_ns

        # Detect a restarted producer or a replay rewind.
        session_changed = state.session is not None and sample.session != state.session
        rewound = stamp + REWIND_NS < state.last_stamp and (
            sample.revision == 0 or sample.revision < state.last_revision
        )
        if session_changed or rewound:
            if rewound or (self.binding is not None and name == self.binding.anchor):
                self._reset_shared(stamp)
            else:
                self._reset_stream(name)
            state.last_stamp = state.last_revision = -1
            state.counts["resets"] += 1

        # Keep one stamp order per stream; a same-stamp revision must be newer.
        if stamp < state.last_stamp or (
            stamp == state.last_stamp and sample.revision <= state.last_revision
        ):
            state.counts["stale_or_duplicate"] += 1
            return False
        if stamp == state.last_stamp:
            state.counts["same_stamp_revision"] += 1
        state.session, state.last_stamp, state.last_revision = (
            sample.session,
            stamp,
            sample.revision,
        )
        state.received_at = self.clock()
        state.counts["admitted"] += 1

        if self.truth is not None:
            if stamp <= state.compared:
                state.counts["comparison_late"] += 1
            else:
                self._enqueue(name, estimate)
        return True

    def add_reference(self, sample: PoseSample) -> None:
        """Store a live reference already on the source clock and estimate frame.

        A rewind discards the previous live reference samples, pending comparisons,
        anchor pairs and alignment before storing the first sample of the new epoch.

        Args:
            sample: Prepared reference sample.
        """
        if self.truth is None or self.prepared is not None:
            return
        newest = self.truth.newest_ns
        if newest is not None and sample.stamp_ns + REWIND_NS < newest:
            self._reset_shared(sample.stamp_ns)
            self.reference_counts["resets"] += 1
        self.truth.add(sample)
        self.reference_counts["received"] += 1
        self.reference_received_at = self.clock()

    # -- Release -----------------------------------------------------------

    def release(self) -> list[ComparisonResult]:
        """Return every comparison whose reference and alignment are decided.

        Returns:
            Results in source order per stream.
        """
        if self.truth is None:
            return []
        now = self.clock()
        # Resolve every stream first so a freshly frozen alignment applies to all.
        for name in self.queues:
            self._resolve(name, now)
        results: list[ComparisonResult] = []
        for name in self.queues:
            results.extend(self._release(name, now))
        return results

    def _stalled(self, state: StreamState, now: float) -> bool:
        """Tell whether a stream has stopped delivering estimates."""
        return now - state.received_at > STALL_S

    def _resolve(self, name: str, now: float) -> None:
        """Look up references for the oldest undecided entries, at most once each."""
        assert self.truth is not None
        state = self.states[name]
        queue = self.queues[name]
        newest = self.truth.newest_ns
        while queue.unresolved:
            entry = queue.unresolved[0]
            stamp = entry.stamp_ns
            reference = self.truth.at(stamp)
            if reference is None:
                # A live bracket can still complete until the reference passes this stamp.
                covered = self.prepared is not None or (newest is not None and newest >= stamp)
                waited = state.last_stamp - stamp > REFERENCE_WAIT_NS or self._stalled(state, now)
                if not covered and not waited:
                    break
                entry.outcome = (
                    MatchOutcome.NO_REFERENCE_BRACKET
                    if covered
                    else MatchOutcome.REFERENCE_NOT_RECEIVED
                )
            entry.reference = reference
            queue.unresolved.popleft()
            queue.resolved.append(entry)
            if reference is not None:
                self._add_anchor_pair(name, entry.estimate.sample, reference)

    def _add_anchor_pair(self, name: str, estimate: PoseSample, reference: PoseSample) -> None:
        """Store or revise a fit pair and freeze at the anchor-window boundary."""
        binding = self.binding
        assert binding is not None
        if not binding.alignment or self.alignment is not None or name != binding.anchor:
            return
        if self.pairs and self.pairs[-1][0].stamp_ns == estimate.stamp_ns:
            self.pairs[-1] = (estimate, reference)
            return
        elapsed = estimate.stamp_ns - self.pairs[0][0].stamp_ns if self.pairs else 0
        if elapsed <= binding.anchor_window_ns:
            if len(self.pairs) < MAX_ANCHOR_PAIRS:
                self.pairs.append((estimate, reference))
            else:
                self.states[name].counts["anchor_pair_drops"] += 1
        if elapsed >= binding.anchor_window_ns and len(self.pairs) >= 2:
            self.alignment = fit_initial_yaw(self.pairs)

    def _release(self, name: str, now: float) -> list[ComparisonResult]:
        """Publish decided entries, holding matched ones until alignment freezes."""
        binding = self.binding
        assert binding is not None
        state = self.states[name]
        queue = self.queues[name]
        hold_ns = binding.anchor_window_ns + binding.max_gap_ns + REFERENCE_WAIT_NS
        results: list[ComparisonResult] = []
        while queue.resolved:
            entry = queue.resolved[0]
            unaligned = binding.alignment and self.alignment is None and entry.reference is not None
            expired = state.last_stamp - entry.stamp_ns > hold_ns or self._stalled(state, now)
            if unaligned and not expired:
                break
            queue.resolved.popleft()
            self.pending -= 1
            results.append(self._finish(name, entry, unaligned=unaligned))
        return results

    def _finish(self, name: str, entry: _Pending, *, unaligned: bool) -> ComparisonResult:
        """Compare one decided entry and update the stream counters."""
        state = self.states[name]
        sample = entry.estimate.sample
        state.compared = sample.stamp_ns
        values: dict[str, float | int] = {"reference_valid": 0}
        if entry.reference is None:
            outcome = entry.outcome or MatchOutcome.NO_REFERENCE_BRACKET
        elif unaligned:
            outcome = MatchOutcome.ALIGNMENT_NOT_FROZEN
        else:
            reference = self.alignment.apply(entry.reference) if self.alignment else entry.reference
            try:
                values.update(compare(sample, reference, entry.estimate.sigmas))
                values["reference_valid"] = 1
                outcome = MatchOutcome.MATCHED
            except ValueError as error:
                outcome = MatchOutcome.COMPARISON_REJECTED
                state.error = str(error)
        state.counts[outcome.value] += 1
        if outcome is not MatchOutcome.MATCHED:
            state.counts["unmatched"] += 1
        return ComparisonResult(name, sample, values, outcome)

    # -- Pending and resets ------------------------------------------------

    def _enqueue(self, name: str, estimate: DecodedEstimate) -> None:
        """Queue an estimate, replacing a pending one at the same stamp."""
        sample = estimate.sample
        if self.pairs and self.pairs[-1][0].stamp_ns == sample.stamp_ns:
            self._add_anchor_pair(name, sample, self.pairs[-1][1])
        queue = self.queues[name]
        tail = queue.tail()
        if tail is not None and tail.stamp_ns == sample.stamp_ns:
            tail.estimate = estimate
            return
        queue.unresolved.append(_Pending(estimate))
        self.pending += 1
        if self.pending > self.max_pending:
            self._drop_oldest()

    def _drop_oldest(self) -> None:
        """Drop the oldest pending estimate across streams to respect the bound."""
        candidates = [
            (head.stamp_ns, name)
            for name, queue in self.queues.items()
            if (head := queue.head()) is not None
        ]
        _, name = min(candidates)
        self.queues[name].pop_head()
        self.pending -= 1
        self.states[name].counts["pending_drops"] += 1

    def _reset_stream(self, name: str) -> None:
        """Forget one stream's pending comparisons."""
        self.pending -= len(self.queues[name])
        self.queues[name].clear()
        self.states[name].compared = -1

    def _reset_shared(self, stamp_ns: int) -> None:
        """Forget pending comparisons and the alignment, keeping the prepared reference.

        A live reference that already rewound to the new epoch is kept; one
        still ahead of the new stamp belongs to the previous epoch.
        """
        for name in self.queues:
            self._reset_stream(name)
        self.pairs.clear()
        self.alignment = None
        if self.prepared is None and self.truth is not None:
            newest = self.truth.newest_ns
            if newest is not None and newest > stamp_ns + REWIND_NS:
                self.truth.clear()
