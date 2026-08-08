"""Small synthetic CAN protocol used by milestone v0.1.

The identifiers and payload layouts in this module are entirely fictional.
No DBC is used in this milestone.
"""

from __future__ import annotations

from dataclasses import dataclass

ENGINE_STATUS_CAN_ID = 0x180
VEHICLE_SPEED_CAN_ID = 0x181


@dataclass(frozen=True)
class EngineState:
    """Synthetic state broadcast by the engine ECU."""

    ignition_on: bool
    engine_running: bool
    vehicle_speed_kph: float


def encode_engine_status(ignition_on: bool, engine_running: bool) -> bytes:
    """Encode ignition and running flags into a one-byte payload."""
    flags = int(ignition_on) | (int(engine_running) << 1)
    return bytes((flags,))


def decode_engine_status(data: bytes | bytearray) -> tuple[bool, bool]:
    """Decode ignition and running flags from a status payload."""
    if len(data) != 1:
        raise ValueError("engine status payload must contain exactly 1 byte")
    return bool(data[0] & 0x01), bool(data[0] & 0x02)


def encode_vehicle_speed(speed_kph: float) -> bytes:
    """Encode speed as an unsigned big-endian value in 0.1 km/h units."""
    if not 0.0 <= speed_kph <= 6553.5:
        raise ValueError("vehicle speed must be between 0.0 and 6553.5 km/h")
    raw_speed = round(speed_kph * 10)
    return raw_speed.to_bytes(2, byteorder="big", signed=False)


def decode_vehicle_speed(data: bytes | bytearray) -> float:
    """Decode a two-byte vehicle-speed payload to km/h."""
    if len(data) != 2:
        raise ValueError("vehicle speed payload must contain exactly 2 bytes")
    return int.from_bytes(data, byteorder="big", signed=False) / 10.0
