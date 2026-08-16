"""Synthetic engine ECU that periodically publishes SocketCAN frames."""

from __future__ import annotations

import argparse
import logging
import math
import time
from collections.abc import Callable
from collections.abc import Sequence

import can

from .protocol import (
    ENGINE_STATUS_CAN_ID,
    VEHICLE_SPEED_MAX_KPH,
    VEHICLE_SPEED_MIN_KPH,
    VEHICLE_SPEED_CAN_ID,
    EngineState,
    encode_engine_status,
    encode_vehicle_speed,
)

LOGGER = logging.getLogger(__name__)


def build_messages(state: EngineState) -> tuple[can.Message, can.Message]:
    """Build the two synthetic CAN messages for one transmit cycle."""
    return (
        can.Message(
            arbitration_id=ENGINE_STATUS_CAN_ID,
            data=encode_engine_status(state.ignition_on, state.engine_running),
            is_extended_id=False,
        ),
        can.Message(
            arbitration_id=VEHICLE_SPEED_CAN_ID,
            data=encode_vehicle_speed(state.vehicle_speed_kph),
            is_extended_id=False,
        ),
    )


def transmit_cycle(bus: can.BusABC, state: EngineState) -> None:
    """Transmit one status frame and one speed frame."""
    for message in build_messages(state):
        bus.send(message)
        LOGGER.info("sent id=0x%03X data=%s", message.arbitration_id, message.data.hex(" "))


def run(
    bus: can.BusABC,
    state: EngineState,
    period_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Transmit frames continuously until interrupted."""
    if period_seconds <= 0:
        raise ValueError("period must be greater than zero")
    while True:
        transmit_cycle(bus, state)
        sleep(period_seconds)


def positive_float(value: str) -> float:
    """Parse a command-line value that must be greater than zero."""
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a finite number greater than zero")
    return parsed


def valid_speed(value: str) -> float:
    """Parse a speed within the range defined by the synthetic DBC."""
    parsed = float(value)
    if not math.isfinite(parsed) or not VEHICLE_SPEED_MIN_KPH <= parsed <= VEHICLE_SPEED_MAX_KPH:
        raise argparse.ArgumentTypeError(
            f"speed must be between {VEHICLE_SPEED_MIN_KPH:.1f} and "
            f"{VEHICLE_SPEED_MAX_KPH:.1f} km/h"
        )
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", default="vcan0", help="SocketCAN channel")
    parser.add_argument("--period", type=positive_float, default=0.5, help="transmit period in seconds")
    parser.add_argument("--speed", type=valid_speed, default=42.5, help="synthetic vehicle speed in km/h")
    parser.add_argument("--ignition-off", action="store_true", help="broadcast ignition off")
    parser.add_argument("--engine-off", action="store_true", help="broadcast engine stopped")
    return parser.parse_args(argv)


def main() -> None:
    """Run the engine ECU command-line application."""
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    state = EngineState(
        ignition_on=not args.ignition_off,
        engine_running=not args.engine_off,
        vehicle_speed_kph=args.speed,
    )
    try:
        with can.Bus(interface="socketcan", channel=args.channel) as bus:
            run(bus, state, args.period)
    except KeyboardInterrupt:
        LOGGER.info("engine ECU stopped")
    except can.CanError as error:
        LOGGER.error("CAN communication failed: %s", error)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
