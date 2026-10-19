"""Offline encoding of the CAN layout observed in the uploaded RY-H1 scripts.

Source: PCAN_ruiyan16_right_linux.py, lines 84-99, 144-166.
Values are raw protocol integers, not radians, degrees, amperes or newtons.
Encoding validates representation only; it does not establish device limits.
This module never opens a bus, loads a vendor library or transmits a frame.
"""
from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class LegacyCanFrame:
    arbitration_id: int
    data: bytes
    is_extended_id: bool = False
    is_fd: bool = False


def _integer_in_range(name, value, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f'{name} must be an integer')
    if not minimum <= value <= maximum:
        raise ValueError(f'{name} must be between {minimum} and {maximum}')
    return value


def encode_position_command(motor_id, position, speed, current_limit):
    """Return a 7-byte standard CAN frame; all inputs must be explicit.

    The source sends motor IDs 1..16 and opcode 0xAA followed by three
    little-endian unsigned 16-bit fields. Physical interpretation and allowed
    operating values still require the matching device protocol and setup.
    """
    motor_id = _integer_in_range('motor_id', motor_id, 1, 16)
    fields = [_integer_in_range(name, value, 0, 65535) for name, value in (
        ('position', position), ('speed', speed), ('current_limit', current_limit))]
    return LegacyCanFrame(motor_id, struct.pack('<BHHH', 0xAA, *fields))


def encode_legacy_clear_command(motor_id):
    """Encode source opcode 0xA5; this is not a confirmed emergency-stop command."""
    motor_id = _integer_in_range('motor_id', motor_id, 1, 16)
    return LegacyCanFrame(motor_id, bytes([0xA5]))
