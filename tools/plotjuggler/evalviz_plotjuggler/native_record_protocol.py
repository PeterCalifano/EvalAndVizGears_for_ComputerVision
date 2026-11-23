r"""Versioned JSON Lines records and a ROS-free producer for native estimator sources.

This module imports only the Python standard library, so a producer can use it
without ROS, NumPy or the profile tooling.

Wire contract, version 1:

* A Unix domain stream socket carries UTF-8 JSON objects, one per line, each
  terminated by ``\n``. A line holds at most ``MAX_RECORD_BYTES`` bytes
  without its terminator.
* Every object has ``version`` (integer 1), ``kind`` (``pose``, ``joints`` or
  ``transform``), the routed profile ``input`` name and ``stamp_ns``: the
  source time as a nonnegative JSON integer of nanoseconds. A float, string or
  boolean stamp is rejected, so a 19-digit epoch stamp is never rounded.
* Keys are exact: a missing required key, an unknown key, a duplicate key and
  the non-standard ``NaN`` and ``Infinity`` constants are rejected.
* ``pose``: ``world`` and ``tracked`` frame IDs; ``position_m`` of the tracked
  origin in world axes; ``quaternion_xyzw``, the Hamilton unit quaternion of
  the active rotation from tracked axes to world axes (the ROS
  ``geometry_msgs/Quaternion`` convention), scalar last; nonnegative integer
  ``session`` and ``revision``. Optional: ``velocity_world_mps`` in world axes,
  and ``covariance`` as 36 row-major values with its ``covariance_chart``.
  The chart orders the tangent as world position then attitude; the attitude
  block is right-local (``world_position_right_rotation``) or about the world
  axes (``world_position_fixed_rotation``).
* ``joints``: unique ``names`` and matching ``positions`` (radians or metres),
  optional matching ``velocities``.
* ``transform``: ``parent`` and ``child`` frames, ``translation_m`` of the
  child origin in parent axes and ``quaternion_xyzw`` from child to parent
  axes, as in ``geometry_msgs/TransformStamped``.

``encode_record`` writes a canonical line: sorted keys, no spaces, shortest
round-trip float text. Equal records always produce equal bytes.

Example:
    >>> record = PoseRecord("aerial", 1_763_856_000_123_456_789, "world", "base_link",
    ...                     (1.0, 2.0, 3.0), (0.0, 0.0, 0.0, 1.0))
    >>> decode_record(encode_record(record)) == record
    True
"""

from __future__ import annotations

import json
import math
import os
import re
import socket
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, fields
from enum import StrEnum
from types import TracebackType
from typing import Self, cast

PROTOCOL_VERSION = 1
# Profile encoding of a std_msgs/msg/String topic that carries one pose record per message.
POSE_ENCODING = "evalviz_jsonl_v1"
MAX_RECORD_BYTES = 65_536
# builtin_interfaces/Time holds signed 32-bit seconds, so later stamps cannot reach ROS.
MAX_STAMP_NS = 2**31 * 1_000_000_000 - 1
MAX_COUNTER = 2**63 - 1
MAX_JOINTS = 256
MAX_NAME_LENGTH = 256
QUATERNION_TOLERANCE = 1e-3
RIGHT_ROTATION_CHART = "world_position_right_rotation"
FIXED_ROTATION_CHART = "world_position_fixed_rotation"
COVARIANCE_CHARTS = frozenset({RIGHT_ROTATION_CHART, FIXED_ROTATION_CHART})
POSE_COVARIANCE_SIZE = 36

_INPUT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_FRAME = re.compile(r"[^/\s][^\s]*")
_JOINT_NAME = re.compile(r"[^\s]+")
_ENVELOPE_KEYS = frozenset({"version", "kind"})


class ProtocolError(ValueError):
    """A record violates the version 1 wire contract."""


class RecordKind(StrEnum):
    """Record type named by the ``kind`` key."""

    POSE = "pose"
    JOINTS = "joints"
    TRANSFORM = "transform"


# ---------------------------------------------------------------------------
# Field validation
# ---------------------------------------------------------------------------


def _set(record: object, name: str, value: object) -> None:
    """Store a normalized value on a frozen record during validation."""
    object.__setattr__(record, name, value)


def _integer(value: object, name: str, maximum: int) -> int:
    """Validate an exact nonnegative integer; booleans and floats are rejected."""
    if type(value) is not int or not 0 <= value <= maximum:
        raise ProtocolError(f"{name} must be an integer in [0, {maximum}], got {value!r}")
    return value


def _text(value: object, pattern: re.Pattern[str], name: str) -> str:
    """Validate a bounded identifier against its pattern."""
    if not isinstance(value, str) or len(value) > MAX_NAME_LENGTH or not pattern.fullmatch(value):
        raise ProtocolError(f"{name} {value!r} is not a valid identifier")
    return value


def _vector(value: object, size: int, name: str) -> tuple[float, ...]:
    """Validate a list of finite numbers with the given length."""
    if not isinstance(value, list | tuple) or len(value) != size:
        raise ProtocolError(f"{name} must hold {size} numbers")
    numbers = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int | float):
            raise ProtocolError(f"{name} must hold numbers, got {item!r}")
        try:
            number = float(item)
        except OverflowError as error:
            raise ProtocolError(f"{name} holds an out-of-range number") from error
        if not math.isfinite(number):
            raise ProtocolError(f"{name} must hold finite numbers")
        numbers.append(number)
    return tuple(numbers)


def _quaternion(value: object, name: str) -> tuple[float, float, float, float]:
    """Validate a unit xyzw quaternion within the shared tolerance, keeping its values."""
    x, y, z, w = _vector(value, 4, name)
    if abs(math.hypot(x, y, z, w) - 1.0) > QUATERNION_TOLERANCE:
        raise ProtocolError(f"{name} is not a unit quaternion")
    return x, y, z, w


def _three(value: object, name: str) -> tuple[float, float, float]:
    """Validate a finite three-vector."""
    x, y, z = _vector(value, 3, name)
    return x, y, z


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PoseRecord:
    """Estimate or reference pose of the tracked frame in the world frame.

    Attributes:
        input: Profile input with encoding ``evalviz_jsonl_v1`` that receives it.
        stamp_ns: Source time in integer nanoseconds.
        world: World frame ID.
        tracked: Tracked frame ID.
        position_m: Tracked origin in world axes.
        quaternion_xyzw: Unit rotation from tracked to world axes, scalar last.
        session: Producer session; a change resets live matching for the input.
        revision: Optimizer revision; a higher one replaces a published stamp.
        velocity_world_mps: Optional tracked-origin velocity in world axes.
        covariance_chart: Chart of ``covariance``; set exactly when it is.
        covariance: Optional 6x6 row-major pose covariance.
    """

    input: str
    stamp_ns: int
    world: str
    tracked: str
    position_m: tuple[float, float, float]
    quaternion_xyzw: tuple[float, float, float, float]
    session: int = 0
    revision: int = 0
    velocity_world_mps: tuple[float, float, float] | None = None
    covariance_chart: str | None = None
    covariance: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        """Validate every field and store sequences as float tuples.

        Raises:
            ProtocolError: A field is invalid.
        """
        _set(self, "input", _text(self.input, _INPUT_NAME, "input"))
        _set(self, "stamp_ns", _integer(self.stamp_ns, "stamp_ns", MAX_STAMP_NS))
        _set(self, "world", _text(self.world, _FRAME, "world"))
        _set(self, "tracked", _text(self.tracked, _FRAME, "tracked"))
        _set(self, "position_m", _three(self.position_m, "position_m"))
        _set(self, "quaternion_xyzw", _quaternion(self.quaternion_xyzw, "quaternion_xyzw"))
        _set(self, "session", _integer(self.session, "session", MAX_COUNTER))
        _set(self, "revision", _integer(self.revision, "revision", MAX_COUNTER))
        if self.velocity_world_mps is not None:
            _set(self, "velocity_world_mps", _three(self.velocity_world_mps, "velocity_world_mps"))
        if (self.covariance is None) != (self.covariance_chart is None):
            raise ProtocolError("covariance and covariance_chart must be given together")
        if self.covariance_chart is not None:
            if self.covariance_chart not in COVARIANCE_CHARTS:
                raise ProtocolError(
                    f"covariance_chart {self.covariance_chart!r} is not one of "
                    f"{sorted(COVARIANCE_CHARTS)}"
                )
            _set(self, "covariance", _vector(self.covariance, POSE_COVARIANCE_SIZE, "covariance"))


@dataclass(frozen=True)
class JointRecord:
    """Named joint positions for Robot State Publisher.

    Attributes:
        input: Profile input with role ``joints`` that receives it.
        stamp_ns: Source time in integer nanoseconds.
        names: Unique joint names.
        positions: Positions in radians or metres, matching ``names``.
        velocities: Optional velocities matching ``names``.
    """

    input: str
    stamp_ns: int
    names: tuple[str, ...]
    positions: tuple[float, ...]
    velocities: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        """Validate names and matching value lengths.

        Raises:
            ProtocolError: A field is invalid.
        """
        _set(self, "input", _text(self.input, _INPUT_NAME, "input"))
        _set(self, "stamp_ns", _integer(self.stamp_ns, "stamp_ns", MAX_STAMP_NS))
        if not isinstance(self.names, list | tuple) or not 0 < len(self.names) <= MAX_JOINTS:
            raise ProtocolError(f"names must list 1 to {MAX_JOINTS} joints")
        names = tuple(_text(name, _JOINT_NAME, "joint name") for name in self.names)
        if len(set(names)) != len(names):
            raise ProtocolError("joint names must be unique")
        _set(self, "names", names)
        _set(self, "positions", _vector(self.positions, len(names), "positions"))
        if self.velocities is not None:
            _set(self, "velocities", _vector(self.velocities, len(names), "velocities"))


@dataclass(frozen=True)
class TransformRecord:
    """One dynamic transform, typically the robot root in the world frame.

    Attributes:
        input: Profile input with role ``tf`` that receives it.
        stamp_ns: Source time in integer nanoseconds.
        parent: Parent frame ID.
        child: Child frame ID.
        translation_m: Child origin in parent axes.
        quaternion_xyzw: Unit rotation from child to parent axes, scalar last.
    """

    input: str
    stamp_ns: int
    parent: str
    child: str
    translation_m: tuple[float, float, float]
    quaternion_xyzw: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        """Validate frames and the rigid transform.

        Raises:
            ProtocolError: A field is invalid.
        """
        _set(self, "input", _text(self.input, _INPUT_NAME, "input"))
        _set(self, "stamp_ns", _integer(self.stamp_ns, "stamp_ns", MAX_STAMP_NS))
        _set(self, "parent", _text(self.parent, _FRAME, "parent"))
        _set(self, "child", _text(self.child, _FRAME, "child"))
        if self.parent == self.child:
            raise ProtocolError("parent and child frames must differ")
        _set(self, "translation_m", _three(self.translation_m, "translation_m"))
        _set(self, "quaternion_xyzw", _quaternion(self.quaternion_xyzw, "quaternion_xyzw"))


type Record = PoseRecord | JointRecord | TransformRecord

_RECORD_TYPES: dict[RecordKind, type[PoseRecord] | type[JointRecord] | type[TransformRecord]] = {
    RecordKind.POSE: PoseRecord,
    RecordKind.JOINTS: JointRecord,
    RecordKind.TRANSFORM: TransformRecord,
}
# Keys a producer may omit; session and revision are required on the wire.
_OPTIONAL_KEYS = {
    RecordKind.POSE: frozenset({"velocity_world_mps", "covariance_chart", "covariance"}),
    RecordKind.JOINTS: frozenset({"velocities"}),
    RecordKind.TRANSFORM: frozenset(),
}


def record_kind(record: Record) -> RecordKind:
    """Return the wire kind of a record.

    Args:
        record: Validated record.

    Returns:
        Its ``kind`` value.

    Example:
        >>> record_kind(JointRecord("joints", 0, ("shoulder",), (0.5,)))
        <RecordKind.JOINTS: 'joints'>
    """
    return next(kind for kind, kind_type in _RECORD_TYPES.items() if type(record) is kind_type)


# ---------------------------------------------------------------------------
# Encoding and decoding
# ---------------------------------------------------------------------------


def encode_record(record: Record) -> bytes:
    """Encode a validated record as one canonical newline-terminated line.

    Args:
        record: Record to send.

    Returns:
        ASCII JSON with sorted keys and a trailing newline. Absent optional
        fields are omitted.

    Raises:
        ProtocolError: The line would exceed ``MAX_RECORD_BYTES``.

    Example:
        >>> encode_record(JointRecord("j", 7, ("a",), (0.5,)))[:45]
        b'{"input":"j","kind":"joints","names":["a"],"p'
    """
    document: dict[str, object] = {"version": PROTOCOL_VERSION, "kind": str(record_kind(record))}
    for item in fields(record):
        value = getattr(record, item.name)
        if value is not None:
            document[item.name] = list(value) if isinstance(value, tuple) else value
    line = json.dumps(document, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
    if len(line) > MAX_RECORD_BYTES:
        raise ProtocolError(f"record of {len(line)} bytes exceeds {MAX_RECORD_BYTES} bytes")
    return line + b"\n"


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Build a JSON object, rejecting a repeated key."""
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise ProtocolError(f"duplicate key {key!r}")
        document[key] = value
    return document


def _reject_constant(constant: str) -> None:
    """Reject the non-standard NaN and Infinity JSON constants."""
    raise ProtocolError(f"non-finite constant {constant}")


def decode_record(line: bytes | str) -> Record:
    """Validate one line without its terminator and return its record.

    Args:
        line: UTF-8 bytes or text of one JSON object.

    Returns:
        The validated record.

    Raises:
        ProtocolError: The line is too long, not UTF-8 JSON, has another
            version or kind, misses or adds keys, or holds an invalid field.
    """
    raw = line if isinstance(line, bytes) else line.encode("utf-8", errors="surrogatepass")
    if len(raw) > MAX_RECORD_BYTES:
        raise ProtocolError(f"record of {len(raw)} bytes exceeds {MAX_RECORD_BYTES} bytes")
    try:
        document = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
    except ProtocolError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise ProtocolError(f"malformed JSON record: {error}") from error
    if not isinstance(document, dict):
        raise ProtocolError("a record must be a JSON object")

    # Check the version before any other field so a newer producer is named clearly.
    version = document.get("version")
    if type(version) is not int or version != PROTOCOL_VERSION:
        raise ProtocolError(
            f"unsupported protocol version {version!r}; expected {PROTOCOL_VERSION}"
        )
    try:
        kind = RecordKind(cast(str, document.get("kind")))
    except ValueError as error:
        raise ProtocolError(f"unknown record kind {document.get('kind')!r}") from error

    record_type = _RECORD_TYPES[kind]
    body = {key: value for key, value in document.items() if key not in _ENVELOPE_KEYS}
    allowed = {item.name for item in fields(record_type)}
    missing = sorted(allowed - _OPTIONAL_KEYS[kind] - body.keys())
    unknown = sorted(body.keys() - allowed)
    if missing or unknown:
        raise ProtocolError(f"{kind} record keys: missing {missing}, unknown {unknown}")
    return record_type(**body)


class LineFramer:
    """Split a byte stream into bounded newline-terminated records.

    The framer keeps at most one partial record. A record longer than the
    bound loses the stream's record boundaries, so the framer stops and sets
    ``error``; the owner must close the connection.
    """

    def __init__(self, max_record_bytes: int = MAX_RECORD_BYTES) -> None:
        """Create an empty framer.

        Args:
            max_record_bytes: Largest record without its terminator.
        """
        self.max_record_bytes = max_record_bytes
        self.error: str | None = None
        self._buffer = bytearray()

    @property
    def pending_bytes(self) -> int:
        """Return the size of the partial record waiting for its newline."""
        return len(self._buffer)

    def feed(self, data: bytes) -> list[bytes]:
        """Append received bytes and return every completed record.

        Args:
            data: Bytes received from the stream.

        Returns:
            Completed records without terminators, in stream order. Records
            completed before a framing error are still returned.

        Raises:
            ProtocolError: The framer already failed.
        """
        if self.error is not None:
            raise ProtocolError(self.error)
        # Search only the new bytes: the retained partial record has no newline.
        search = len(self._buffer)
        self._buffer += data
        start = 0
        records = []
        while (end := self._buffer.find(b"\n", search)) >= 0:
            if end - start > self.max_record_bytes:
                self.error = f"record exceeds {self.max_record_bytes} bytes"
                break
            records.append(bytes(self._buffer[start:end]))
            start = search = end + 1
        if self.error is None:
            del self._buffer[:start]
            if len(self._buffer) > self.max_record_bytes:
                self.error = f"record exceeds {self.max_record_bytes} bytes without a newline"
        if self.error is not None:
            self._buffer.clear()
        return records


# ---------------------------------------------------------------------------
# Producer
# ---------------------------------------------------------------------------


@dataclass
class ProducerStats:
    """Delivery counters of one producer.

    Attributes:
        sent: Records fully written to the socket.
        dropped: Records not written because no connection was usable.
        connects: Successful connections, including reconnects.
        last_error: Latest connection or send failure.
    """

    sent: int = 0
    dropped: int = 0
    connects: int = 0
    last_error: str = ""


class NativeProducer:
    """Send records to a native ingress over a Unix domain stream socket.

    A send never blocks longer than ``send_timeout_s``. When the ingress is
    absent, slow beyond that timeout, or gone, the record is dropped and
    counted, the connection is closed, and the next send reconnects after at
    most ``retry_interval_s``. A send that timed out may have written part of
    a line; closing the connection makes the ingress discard and count it.
    Records are never queued, so the producer's memory and CPU stay bounded
    and a stalled viewer cannot delay the estimator. The class is not
    thread-safe.

    Example:
        >>> with NativeProducer("/nonexistent/evalviz.sock") as producer:
        ...     producer.send(JointRecord("joints", 0, ("shoulder",), (0.0,)))
        False
    """

    def __init__(
        self,
        socket_path: str | os.PathLike[str],
        *,
        send_timeout_s: float = 1.0,
        retry_interval_s: float = 0.5,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Create a disconnected producer.

        Args:
            socket_path: Socket created by the ingress.
            send_timeout_s: Longest blocking connect or send.
            retry_interval_s: Shortest interval between connection attempts.
            clock: Monotonic clock in seconds, replaceable in tests.

        Raises:
            ValueError: A duration is not positive and finite.
        """
        durations = {"send_timeout_s": send_timeout_s, "retry_interval_s": retry_interval_s}
        for name, value in durations.items():
            if not 0 < value < math.inf:
                raise ValueError(f"{name} must be a positive finite number of seconds")
        self.socket_path = os.fspath(socket_path)
        self.send_timeout_s = send_timeout_s
        self.retry_interval_s = retry_interval_s
        self.stats = ProducerStats()
        self._clock = clock
        self._socket: socket.socket | None = None
        self._next_attempt = -math.inf

    @property
    def connected(self) -> bool:
        """Tell whether the producer holds an open connection."""
        return self._socket is not None

    def connect(self) -> bool:
        """Connect unless connected, at most once per retry interval.

        Returns:
            True when a connection is open afterwards.
        """
        if self._socket is not None:
            return True
        now = self._clock()
        if now < self._next_attempt:
            return False
        self._next_attempt = now + self.retry_interval_s
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(self.send_timeout_s)
        try:
            connection.connect(self.socket_path)
        except OSError as error:
            connection.close()
            self.stats.last_error = f"connect: {error}"
            return False
        self._socket = connection
        self.stats.connects += 1
        return True

    def send(self, record: Record) -> bool:
        """Write one record, or drop and count it.

        Args:
            record: Validated record.

        Returns:
            True when the whole line was written.

        Raises:
            ProtocolError: The record cannot be encoded; this is a caller error
                and is not counted as a drop.
        """
        line = encode_record(record)
        if not self.connect():
            self.stats.dropped += 1
            return False
        assert self._socket is not None
        try:
            self._socket.sendall(line)
        except OSError as error:
            self._disconnect(f"send: {error}")
            self.stats.dropped += 1
            return False
        self.stats.sent += 1
        return True

    def send_all(self, records: Sequence[Record]) -> int:
        """Send records in order.

        Args:
            records: Records of one source step.

        Returns:
            The number of records written.
        """
        return sum(self.send(record) for record in records)

    def _disconnect(self, reason: str) -> None:
        """Close a failed connection and wait one retry interval before reconnecting."""
        self.stats.last_error = reason
        self._next_attempt = self._clock() + self.retry_interval_s
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def close(self) -> None:
        """Close the connection; the ingress still reads every completed line."""
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def __enter__(self) -> Self:
        """Return the producer; connection is deferred to the first send."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the connection on every exit path."""
        self.close()
