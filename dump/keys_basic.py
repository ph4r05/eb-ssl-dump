import base64
import types
import struct
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Util.py3compat import *
from Crypto.Util.number import long_to_bytes, bytes_to_long, size, ceil_div


__author__ = 'dusanklinec'


def long_bit_size(x):
    return size(x)


def long_byte_size(x):
    return ceil_div(long_bit_size(x), 8)


def bytes_to_byte(byte, offset=0):
    return struct.unpack('>B', byte[offset:offset+1])[0]


def byte_to_bytes(byte):
    return struct.pack('>B', int(byte) & 0xFF)


def left_zero_pad(inp, ln):
    real_len = len(inp)
    if real_len >= ln:
        return inp
    return ('0'*(ln-real_len)) + inp


def compute_key_mask(n):
    """
    Computes public modulus key mask.
    2nd-7th most significant bit of modulus | 2nd least significant bit of modulus | modulus mod 3 | modulus_length_in_bits mod 2

    :param n:
    :return:
    """
    if not isinstance(n, types.LongType):
        raise ValueError('Long expected')
    mask = ''

    buff = long_to_bytes(n)

    msb = long(bytes_to_byte(buff[0]))
    bit_section = (msb >> 1) & 0x3f
    mask += left_zero_pad(bin(bit_section)[2:], 6)
    mask += '|'

    lsb = long(bytes_to_byte(buff[-1:]))
    mask += bin((lsb & 0x2) >> 1)[2:]
    mask += '|'

    mask += str(n % 3)
    mask += '|'

    mask += str(long_bit_size(n) % 2)
    return mask


if __name__ == "__main__":
    print compute_key_mask(888888888L)

