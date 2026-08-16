import can
import pytest

from connected_vehicle_validation.can.engine_ecu import (
    build_messages,
    parse_args,
    run,
    transmit_cycle,
)
from connected_vehicle_validation.can.protocol import EngineState


class RecordingBus:
    def __init__(self) -> None:
        self.messages: list[can.Message] = []

    def send(self, message: can.Message) -> None:
        self.messages.append(message)


def test_build_messages_uses_standard_fictional_ids() -> None:
    status, speed = build_messages(EngineState(True, True, 42.5))
    assert status.arbitration_id == 0x180
    assert status.data == bytearray(b"\x03")
    assert not status.is_extended_id
    assert speed.arbitration_id == 0x181
    assert speed.data == bytearray(b"\x01\xa9")


def test_transmit_cycle_sends_both_messages() -> None:
    bus = RecordingBus()
    transmit_cycle(bus, EngineState(True, False, 0.0))
    assert [message.arbitration_id for message in bus.messages] == [0x180, 0x181]


@pytest.mark.parametrize("period", [0.0, -1.0, float("nan"), float("inf")])
def test_run_rejects_invalid_period_before_transmitting(period: float) -> None:
    bus = RecordingBus()
    with pytest.raises(ValueError, match="finite number greater than zero"):
        run(bus, EngineState(True, True, 42.5), period)
    assert bus.messages == []


@pytest.mark.parametrize(
    "arguments",
    [["--period", "0"], ["--period", "nan"], ["--period", "inf"], ["--speed", "-1"]],
)
def test_cli_rejects_invalid_numeric_values(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as error:
        parse_args(arguments)
    assert error.value.code == 2
