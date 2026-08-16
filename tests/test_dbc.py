import cantools
import pytest
from cantools.database.errors import EncodeError, UnsupportedDatabaseFormatError

from connected_vehicle_validation.can.protocol import (
    ENGINE_STATUS_CAN_ID,
    VEHICLE_SPEED_CAN_ID,
    decode_engine_status,
    decode_vehicle_speed,
    encode_engine_status,
    encode_vehicle_speed,
    load_database,
)


def test_packaged_dbc_loads_expected_fictional_messages() -> None:
    database = load_database()
    status = database.get_message_by_name("EngineStatus")
    speed = database.get_message_by_name("VehicleSpeed")

    assert (status.frame_id, status.length) == (ENGINE_STATUS_CAN_ID, 1)
    assert (speed.frame_id, speed.length) == (VEHICLE_SPEED_CAN_ID, 2)
    assert (ENGINE_STATUS_CAN_ID, VEHICLE_SPEED_CAN_ID) == (0x180, 0x181)


def test_dbc_defines_signal_layout_scaling_and_boundaries() -> None:
    database = load_database()
    status = database.get_message_by_name("EngineStatus")
    speed = database.get_message_by_name("VehicleSpeed").get_signal_by_name("VehicleSpeedKph")

    assert [(signal.name, signal.start, signal.length) for signal in status.signals] == [
        ("IgnitionOn", 0, 1),
        ("EngineRunning", 1, 1),
    ]
    assert speed.byte_order == "big_endian"
    assert speed.scale == 0.1
    assert (speed.minimum, speed.maximum, speed.unit) == (0, 6553.5, "km/h")


@pytest.mark.parametrize(
    ("ignition_on", "engine_running", "payload"),
    [
        (False, False, b"\x00"),
        (True, False, b"\x01"),
        (False, True, b"\x02"),
        (True, True, b"\x03"),
    ],
)
def test_dbc_engine_status_encoding_preserves_wire_payload(
    ignition_on: bool, engine_running: bool, payload: bytes
) -> None:
    assert encode_engine_status(ignition_on, engine_running) == payload
    assert decode_engine_status(payload) == (ignition_on, engine_running)


@pytest.mark.parametrize(
    ("speed_kph", "payload"),
    [(0.0, b"\x00\x00"), (42.5, b"\x01\xa9"), (6553.5, b"\xff\xff")],
)
def test_dbc_vehicle_speed_encoding_scaling_and_boundaries(
    speed_kph: float, payload: bytes
) -> None:
    assert encode_vehicle_speed(speed_kph) == payload
    assert decode_vehicle_speed(payload) == speed_kph


@pytest.mark.parametrize("speed_kph", [-0.1, 6553.6, float("nan"), float("inf")])
def test_dbc_vehicle_speed_rejects_unrepresentable_values(speed_kph: float) -> None:
    with pytest.raises(ValueError, match="vehicle speed must be between"):
        encode_vehicle_speed(speed_kph)


def test_dbc_strict_encoder_rejects_missing_and_unknown_signals() -> None:
    message = load_database().get_message_by_name("EngineStatus")
    with pytest.raises(EncodeError):
        message.encode({"IgnitionOn": 1}, strict=True)
    with pytest.raises(EncodeError):
        message.encode(
            {"IgnitionOn": 1, "EngineRunning": 1, "NotInTheFictionalDbc": 1},
            strict=True,
        )


@pytest.mark.parametrize("payload", [b"", b"\x00\x00", b"\x00\x00\x00"])
def test_dbc_decoders_reject_malformed_payload_lengths(payload: bytes) -> None:
    with pytest.raises(ValueError, match="payload must contain exactly"):
        if len(payload) == 2:
            decode_engine_status(payload)
        else:
            decode_vehicle_speed(payload)


def test_cantools_rejects_malformed_dbc_text() -> None:
    with pytest.raises(UnsupportedDatabaseFormatError):
        cantools.database.load_string("BO_ this is not a valid DBC", database_format="dbc")
