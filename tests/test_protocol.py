import pytest

from connected_vehicle_validation.can.protocol import (
    decode_engine_status,
    decode_vehicle_speed,
    encode_engine_status,
    encode_vehicle_speed,
)


@pytest.mark.parametrize(
    ("ignition_on", "engine_running"),
    [(False, False), (True, False), (False, True), (True, True)],
)
def test_engine_status_round_trip(ignition_on: bool, engine_running: bool) -> None:
    payload = encode_engine_status(ignition_on, engine_running)
    assert decode_engine_status(payload) == (ignition_on, engine_running)


@pytest.mark.parametrize("speed", [0.0, 42.5, 123.4, 6553.5])
def test_vehicle_speed_round_trip(speed: float) -> None:
    assert decode_vehicle_speed(encode_vehicle_speed(speed)) == speed


@pytest.mark.parametrize("speed", [-0.1, 6553.6])
def test_vehicle_speed_rejects_out_of_range_values(speed: float) -> None:
    with pytest.raises(ValueError):
        encode_vehicle_speed(speed)


def test_decoders_reject_wrong_payload_lengths() -> None:
    with pytest.raises(ValueError):
        decode_engine_status(b"")
    with pytest.raises(ValueError):
        decode_vehicle_speed(b"\x00")
