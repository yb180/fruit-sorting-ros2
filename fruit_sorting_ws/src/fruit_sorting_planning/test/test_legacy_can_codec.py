import struct

import pytest

from fruit_sorting_planning.legacy_can_codec import (
    encode_legacy_clear_command, encode_position_command,
)


def test_observed_wire_order_and_standard_can_flags():
    # Synthetic byte-pattern values exercise endianness; not hardware setpoints.
    frame = encode_position_command(3, 0x1234, 0x5678, 0x09AB)
    assert frame.arbitration_id == 3
    assert frame.data == bytes.fromhex('aa 34 12 78 56 ab 09')
    assert len(frame.data) == 7
    assert not frame.is_extended_id
    assert not frame.is_fd


@pytest.mark.parametrize('motor_id', [1, 16])
def test_clear_command_is_separate_from_motion(motor_id):
    frame = encode_legacy_clear_command(motor_id)
    assert frame.arbitration_id == motor_id
    assert frame.data == b'\xa5'


@pytest.mark.parametrize('motor_id', [0, 17, -1, True, 1.0, '1', None])
def test_invalid_motor_id_is_rejected(motor_id):
    with pytest.raises(ValueError):
        encode_position_command(motor_id, 0, 0, 0)
    with pytest.raises(ValueError):
        encode_legacy_clear_command(motor_id)


@pytest.mark.parametrize('field', ['position', 'speed', 'current_limit'])
@pytest.mark.parametrize('value', [-1, 65536, 1.5, True, None])
def test_invalid_raw_fields_are_not_silently_wrapped(field, value):
    values = {'position': 0, 'speed': 0, 'current_limit': 0}
    values[field] = value
    with pytest.raises(ValueError):
        encode_position_command(1, **values)


@pytest.mark.parametrize('value', [0, 65535])
def test_raw_representation_boundaries_round_trip(value):
    frame = encode_position_command(16, value, value, value)
    assert struct.unpack('<BHHH', frame.data) == (0xAA, value, value, value)
