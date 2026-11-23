"""Check the native wire contract, framing, socket bounds, ownership and reconnects without ROS."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from evalviz_plotjuggler.native_record_protocol import (
    RIGHT_ROTATION_CHART,
    JointRecord,
    LineFramer,
    PoseRecord,
    ProtocolError,
    Record,
    TransformRecord,
    decode_record,
    encode_record,
)

# A current epoch stamp whose nanoseconds a binary64 float cannot hold.
EPOCH_NS = 1_763_856_000_123_456_789


def _joints(stamp_ns: int) -> JointRecord:
    """Create a joint record at the requested source timestamp."""
    return JointRecord("joints", stamp_ns, ("shoulder",), (0.25,))


def _pose_document() -> dict[str, object]:
    """Return a valid pose record document."""
    return {
        "version": 1,
        "kind": "pose",
        "input": "aerial",
        "stamp_ns": EPOCH_NS,
        "world": "world",
        "tracked": "base_link",
        "position_m": [1.0, 2.0, 3.0],
        "quaternion_xyzw": [0.0, 0.0, 0.6, 0.8],
        "session": 1,
        "revision": 0,
    }


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


def test_pose_round_trip_keeps_exact_epoch_stamp_covariance_and_floats() -> None:
    """Carry a 19-digit stamp as an integer and every float bit-exactly."""
    assert float(EPOCH_NS) != EPOCH_NS, "the fixture stamp must not fit a float exactly"
    covariance = tuple((row + 1) * 0.001 + column * 1e-7 for row in range(6) for column in range(6))
    record = PoseRecord(
        "aerial",
        EPOCH_NS,
        "world",
        "base_link",
        (0.1 + 0.2, -2.5, 1e-300),
        (0.0, 0.0, 0.6, 0.8),
        session=3,
        revision=7,
        velocity_world_mps=(0.1, 0.2, 0.3),
        covariance_chart=RIGHT_ROTATION_CHART,
        covariance=covariance,
    )
    line = encode_record(record)
    assert line.endswith(b"\n")
    assert line.count(b"\n") == 1
    assert b'"stamp_ns":1763856000123456789,' in line

    decoded = decode_record(line[:-1])
    assert decoded == record
    assert type(decoded.stamp_ns) is int
    assert decoded.stamp_ns == EPOCH_NS
    assert isinstance(decoded, PoseRecord)
    assert decoded.covariance == covariance
    assert decoded.position_m[0] == 0.30000000000000004
    # Canonical text: decoding and re-encoding reproduces the same bytes.
    assert encode_record(decoded) == line


def test_encoding_is_canonical_for_equal_records() -> None:
    """Produce identical bytes for records built from lists or tuples."""
    from_lists = JointRecord("joints", 5, ["b", "a"], [1, 2.5])  # type: ignore[arg-type]
    from_tuples = JointRecord("joints", 5, ("b", "a"), (1.0, 2.5))
    assert encode_record(from_lists) == encode_record(from_tuples)
    assert json.loads(encode_record(from_tuples))["names"] == ["b", "a"]


def test_stamp_range_matches_ros_time() -> None:
    """Accept the last stamp a ROS Time holds and reject the next one."""
    last_ros_stamp_ns = 2_147_483_647_999_999_999  # int32 seconds plus 999,999,999 ns.
    assert _joints(last_ros_stamp_ns).stamp_ns == last_ros_stamp_ns
    with pytest.raises(ProtocolError, match="stamp_ns"):
        _joints(last_ros_stamp_ns + 1)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"stamp_ns": float(EPOCH_NS)}, "stamp_ns must be an integer"),
        ({"stamp_ns": str(EPOCH_NS)}, "stamp_ns must be an integer"),
        ({"stamp_ns": -1}, "stamp_ns must be an integer"),
        ({"stamp_ns": True}, "stamp_ns must be an integer"),
        ({"version": 2}, "unsupported protocol version 2"),
        ({"version": "1"}, "unsupported protocol version"),
        ({"version": True}, "unsupported protocol version"),
        ({"kind": "odometry"}, "unknown record kind"),
        ({"extra": 1}, r"unknown \['extra'\]"),
        ({"session": None}, "session must be an integer"),
        ({"revision": 1.0}, "revision must be an integer"),
        ({"world": "/world"}, "world '/world' is not a valid identifier"),
        ({"input": "1st"}, "input '1st' is not a valid identifier"),
        ({"quaternion_xyzw": [0, 0, 0, 2]}, "not a unit quaternion"),
        ({"position_m": [0, 0]}, "position_m must hold 3 numbers"),
        ({"position_m": [0, 0, True]}, "position_m must hold numbers"),
        ({"covariance": [0.0] * 36}, "given together"),
        (
            {"covariance": [0.0] * 35, "covariance_chart": RIGHT_ROTATION_CHART},
            "covariance must hold 36 numbers",
        ),
        ({"covariance": [0.0] * 36, "covariance_chart": "body"}, "covariance_chart 'body'"),
    ],
)
def test_malformed_pose_fields_are_rejected(change: dict[str, object], message: str) -> None:
    """Reject every documented wire violation with its reason."""
    document = _pose_document() | change
    with pytest.raises(ProtocolError, match=message):
        decode_record(json.dumps(document))


@pytest.mark.parametrize(
    "document",
    [
        pytest.param(
            _pose_document()
            | {
                "velocity_world_mps": [0.1, 0.2, 0.3],
                "covariance_chart": RIGHT_ROTATION_CHART,
                "covariance": [0.0] * 36,
            },
            id="pose",
        ),
        pytest.param(
            {
                "version": 1,
                "kind": "joints",
                "input": "joints",
                "stamp_ns": 0,
                "names": ["shoulder"],
                "positions": [0.25],
                "velocities": [0.5],
            },
            id="joints",
        ),
        pytest.param(
            {
                "version": 1,
                "kind": "transform",
                "input": "tf",
                "stamp_ns": 0,
                "parent": "world",
                "child": "base_link",
                "translation_m": [1.0, 2.0, 3.0],
                "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
            },
            id="transform",
        ),
    ],
)
@pytest.mark.parametrize(
    "value",
    [None, True, 1, 1.0, "x", ["x"], {"x": 1}],
    ids=["null", "bool", "integer", "float", "string", "list", "object"],
)
def test_wrong_wire_field_types_raise_protocol_error(
    document: dict[str, object], value: object
) -> None:
    """Reject wrong JSON types in each wire field and array element.

    Args:
        document: Valid wire record with every optional field populated.
        value: JSON value to substitute wherever its type is invalid.
    """
    decode_record(json.dumps(document).encode())
    for field, valid_value in document.items():
        nullable = field in {"velocity_world_mps", "velocities"}
        if type(value) is not type(valid_value) and (value is not None or not nullable):
            with pytest.raises(ProtocolError, match=field):
                decode_record(json.dumps(document | {field: value}).encode())

        if isinstance(valid_value, list):
            element_types = (str,) if field == "names" else (int, float)
            if type(value) not in element_types:
                message = "joint name" if field == "names" else field
                with pytest.raises(ProtocolError, match=message):
                    decode_record(
                        json.dumps(document | {field: [value, *valid_value[1:]]}).encode()
                    )


def test_missing_wire_key_is_rejected() -> None:
    """Require session on the wire even though the Python record defaults it."""
    document = _pose_document()
    del document["session"]
    with pytest.raises(ProtocolError, match=r"missing \['session'\]"):
        decode_record(json.dumps(document))


@pytest.mark.parametrize(
    ("line", "message"),
    [
        (b"\xff\xfe", "malformed JSON"),
        (b'{"version": 1, "kind": "pose"', "malformed JSON"),
        (b"[1, 2]", "must be a JSON object"),
        (b"", "malformed JSON"),
        (b'{"version":1,"version":1}', "duplicate key 'version'"),
        (b'{"version":1,"kind":"pose","position_m":[NaN,0,0]}', "non-finite constant NaN"),
        (b"[" * 70_000, "exceeds"),
    ],
)
def test_malformed_lines_are_rejected(line: bytes, message: str) -> None:
    """Reject invalid text, non-objects, duplicates, constants and over-long lines."""
    with pytest.raises(ProtocolError, match=message):
        decode_record(line)


def test_overflowing_number_is_not_finite() -> None:
    """Reject 1e400, which JSON parsing turns into infinity."""
    text = json.dumps(_pose_document()).replace("[1.0, 2.0, 3.0]", "[1e400, 2.0, 3.0]")
    with pytest.raises(ProtocolError, match="finite"):
        decode_record(text)


@pytest.mark.parametrize(
    ("build", "message"),
    [
        (lambda: JointRecord("joints", 0, ("a", "a"), (0.0, 0.0)), "unique"),
        (lambda: JointRecord("joints", 0, ("a", "b"), (0.0,)), "positions must hold 2 numbers"),
        (lambda: JointRecord("joints", 0, (), ()), "names must list"),
        (lambda: JointRecord("joints", 0, ("a b",), (0.0,)), "joint name"),
        (
            lambda: TransformRecord("tf", 0, "world", "world", (0, 0, 0), (0, 0, 0, 1)),
            "must differ",
        ),
    ],
)
def test_joint_and_transform_records_are_validated(
    build: Callable[[], Record], message: str
) -> None:
    """Validate the Python API with the same rules as the decoder."""
    with pytest.raises(ProtocolError, match=message):
        build()


# ---------------------------------------------------------------------------
# Framing
# ---------------------------------------------------------------------------


def test_framer_joins_split_records_and_keeps_order() -> None:
    """Return each record once, whatever the read boundaries are."""
    framer = LineFramer(max_record_bytes=8)
    assert framer.feed(b"abc\nde") == [b"abc"]
    assert framer.pending_bytes == 2
    assert framer.feed(b"f\n\ngh\n") == [b"def", b"", b"gh"]
    assert framer.pending_bytes == 0
    assert framer.feed(b"12345678\n") == [b"12345678"], "a record at the bound is accepted"


@pytest.mark.parametrize("stream", [b"ok\n123456789", b"ok\n123456789\nlater\n"])
def test_framer_stops_after_an_oversize_record(stream: bytes) -> None:
    """Keep records before an over-long one and refuse further input."""
    framer = LineFramer(max_record_bytes=8)
    assert framer.feed(stream) == [b"ok"]
    assert framer.error is not None
    assert "exceeds 8 bytes" in framer.error
    assert framer.pending_bytes == 0
    with pytest.raises(ProtocolError):
        framer.feed(b"\n")
