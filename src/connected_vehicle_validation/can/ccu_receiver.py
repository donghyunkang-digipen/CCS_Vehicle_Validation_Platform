"""CCU receiver that displays frames arriving on a SocketCAN bus."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence

import can

from .protocol import (
    ENGINE_STATUS_CAN_ID,
    VEHICLE_SPEED_CAN_ID,
    decode_engine_status,
    decode_vehicle_speed,
)

LOGGER = logging.getLogger(__name__)


def format_message(message: can.Message) -> str:
    """Return a human-readable representation of a received frame."""
    prefix = f"id=0x{message.arbitration_id:03X} dlc={message.dlc} data={message.data.hex(' ')}"
    try:
        if message.arbitration_id == ENGINE_STATUS_CAN_ID:
            ignition_on, engine_running = decode_engine_status(message.data)
            return f"{prefix} ignition_on={ignition_on} engine_running={engine_running}"
        if message.arbitration_id == VEHICLE_SPEED_CAN_ID:
            return f"{prefix} vehicle_speed_kph={decode_vehicle_speed(message.data):.1f}"
    except ValueError as error:
        return f"{prefix} invalid_payload={error}"
    return prefix


def receive_forever(bus: can.BusABC) -> None:
    """Print incoming frames until interrupted."""
    for message in bus:
        print(format_message(message), flush=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", default="vcan0", help="SocketCAN channel")
    return parser.parse_args(argv)


def main() -> None:
    """Run the CCU receiver command-line application."""
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(f"Listening on {args.channel}; press Ctrl+C to stop.")
    try:
        with can.Bus(interface="socketcan", channel=args.channel) as bus:
            receive_forever(bus)
    except KeyboardInterrupt:
        print("\nCCU receiver stopped.")
    except can.CanError as error:
        LOGGER.error("CAN communication failed: %s", error)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
