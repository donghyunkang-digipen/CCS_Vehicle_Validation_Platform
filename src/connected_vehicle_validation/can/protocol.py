"""DBC-backed synthetic CAN protocol used by milestone v0.2."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
import math

import cantools
from cantools.database import Database, Message
from cantools.database.errors import DecodeError, EncodeError

DBC_RESOURCE = "synthetic_vehicle.dbc"
ENGINE_STATUS_MESSAGE = "EngineStatus"
VEHICLE_SPEED_MESSAGE = "VehicleSpeed"


@lru_cache(maxsize=1)
def load_database() -> Database:
    """Load and cache the packaged fictional CAN database."""
    dbc_text = resources.files(__package__).joinpath(DBC_RESOURCE).read_text(encoding="utf-8")
    return cantools.database.load_string(dbc_text, database_format="dbc", strict=True)


def _message(name: str) -> Message:
    return load_database().get_message_by_name(name)


ENGINE_STATUS_CAN_ID = _message(ENGINE_STATUS_MESSAGE).frame_id
VEHICLE_SPEED_CAN_ID = _message(VEHICLE_SPEED_MESSAGE).frame_id
_VEHICLE_SPEED_SIGNAL = _message(VEHICLE_SPEED_MESSAGE).get_signal_by_name("VehicleSpeedKph")
VEHICLE_SPEED_MIN_KPH = float(_VEHICLE_SPEED_SIGNAL.minimum)
VEHICLE_SPEED_MAX_KPH = float(_VEHICLE_SPEED_SIGNAL.maximum)


@dataclass(frozen=True)
class EngineState:
    """Synthetic state broadcast by the engine ECU."""

    ignition_on: bool
    engine_running: bool
    vehicle_speed_kph: float


def encode_engine_status(ignition_on: bool, engine_running: bool) -> bytes:
    """Encode ignition and running flags with the packaged DBC."""
    try:
        return _message(ENGINE_STATUS_MESSAGE).encode(
            {"IgnitionOn": int(ignition_on), "EngineRunning": int(engine_running)},
            strict=True,
        )
    except (EncodeError, TypeError, ValueError) as error:
        raise ValueError(f"invalid engine status signals: {error}") from error


def decode_engine_status(data: bytes | bytearray) -> tuple[bool, bool]:
    """Decode ignition and running flags with the packaged DBC."""
    message = _message(ENGINE_STATUS_MESSAGE)
    if len(data) != message.length:
        raise ValueError(f"engine status payload must contain exactly {message.length} byte")
    try:
        signals = message.decode(data, decode_choices=False)
    except (DecodeError, TypeError, ValueError) as error:
        raise ValueError(f"invalid engine status payload: {error}") from error
    return bool(signals["IgnitionOn"]), bool(signals["EngineRunning"])


def encode_vehicle_speed(speed_kph: float) -> bytes:
    """Encode vehicle speed with DBC-defined scaling and byte order."""
    if (
        not math.isfinite(speed_kph)
        or not VEHICLE_SPEED_MIN_KPH <= speed_kph <= VEHICLE_SPEED_MAX_KPH
    ):
        raise ValueError(
            f"vehicle speed must be between {VEHICLE_SPEED_MIN_KPH:.1f} and "
            f"{VEHICLE_SPEED_MAX_KPH:.1f} km/h"
        )
    try:
        return _message(VEHICLE_SPEED_MESSAGE).encode(
            {"VehicleSpeedKph": speed_kph}, strict=True
        )
    except (EncodeError, TypeError, ValueError) as error:
        raise ValueError(f"invalid vehicle speed signal: {error}") from error


def decode_vehicle_speed(data: bytes | bytearray) -> float:
    """Decode DBC-scaled vehicle speed in km/h."""
    message = _message(VEHICLE_SPEED_MESSAGE)
    if len(data) != message.length:
        raise ValueError(f"vehicle speed payload must contain exactly {message.length} bytes")
    try:
        signals = message.decode(data, decode_choices=False)
    except (DecodeError, TypeError, ValueError) as error:
        raise ValueError(f"invalid vehicle speed payload: {error}") from error
    return float(signals["VehicleSpeedKph"])
