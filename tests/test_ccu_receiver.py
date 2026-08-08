import can

from connected_vehicle_validation.can.ccu_receiver import format_message


def test_formats_known_status_frame() -> None:
    message = can.Message(arbitration_id=0x180, data=[0x03], is_extended_id=False)
    rendered = format_message(message)
    assert "ignition_on=True" in rendered
    assert "engine_running=True" in rendered


def test_formats_known_speed_frame() -> None:
    message = can.Message(arbitration_id=0x181, data=[0x01, 0xA9], is_extended_id=False)
    assert "vehicle_speed_kph=42.5" in format_message(message)


def test_unknown_frame_is_still_displayed() -> None:
    message = can.Message(arbitration_id=0x222, data=[0xAA], is_extended_id=False)
    assert format_message(message) == "id=0x222 dlc=1 data=aa"


def test_malformed_known_frame_is_reported_without_stopping_receiver() -> None:
    message = can.Message(arbitration_id=0x181, data=[0x01], is_extended_id=False)
    assert "invalid_payload=vehicle speed payload must contain exactly 2 bytes" in format_message(message)
