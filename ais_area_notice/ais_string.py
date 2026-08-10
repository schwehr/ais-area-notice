"""Handle encoding and decoding AIS strings.

character_lut: list, lookup table for decode to fetch characters faster.

character_bits: dict, lookup table for going from a single character to
  a 6 bit BitVector.
"""

import re

from BitVector import BitVector


character_lut: list[str] = [
    "@",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "[",
    "\\",
    "]",
    "^",
    "-",
    " ",
    "!",
    '"',
    "#",
    "$",
    "%",
    "&",
    "`",
    "(",
    ")",
    "*",
    "+",
    ",",
    "-",
    ".",
    "/",
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    ":",
    ";",
    "<",
    "=",
    ">",
    "?",
]

# Fast lookup for the AIS int code for a character.
# Note: character_lut contains "-" at both index 31 and index 45. In dictionary
# comprehension, index 45 overwrites index 31 for "-", which matches previous
# manual dictionary behavior.
character_dict: dict[str, int] = {char: i for i, char in enumerate(character_lut)}

character_bits: dict[str, BitVector] = {
    char: BitVector.from_int(code, size=6) for char, code in character_dict.items()
}


def decode(bits: BitVector, drop_after_first_at: bool = False) -> str:
    """Decode bits as a string.

    Does not remove the end space or @@@@.  Must be an multiple of 6 bits.

    Args:
        bits: BitVector, n*6 bits that represent a string.
        drop_after_first_at: Strip trailing add.

    Returns:
        A string with pad spaces or @@@@.
    """
    numchar = len(bits) // 6
    s = []
    for i in range(numchar):
        start = 6 * i
        end = start + 6
        charbits = bits[start:end]
        val = int(charbits)
        if drop_after_first_at and val == 0:
            break  # 0 is the @ character which is used to pad strings.
        s.append(character_lut[val])

    return "".join(s)


# Backward compatibility alias
Decode = decode  # pylint: disable=invalid-name


def encode(string: str, bit_size: int | None = None) -> BitVector:
    """Convert a string to a BitVector.

    TODO(schwehr): Pad with "@" to reach requested bitSize.

    Args:
        string: str to encode.
        bit_size: Multiple of 6 size of the resulting bits.

    Returns:
        BitVector representing the string.
    """
    if bit_size:
        if bit_size % 6 != 0:
            raise ValueError(f"bit_size must be a multiple of 6, got {bit_size}")
    bv = BitVector(size=0)
    for char in string:
        bv += character_bits[char]
    if bit_size:
        if bit_size < len(bv):
            raise ValueError(
                f'Too many bits in string: "{string}" requires {len(bv)} bits,'
                f" max allowed is {bit_size}"
            )
        extra = bit_size - len(bv)
        bv += BitVector(size=extra)

    return bv


# Backward compatibility alias
Encode = encode  # pylint: disable=invalid-name


def strip(string: str, remove_blanks: bool = True) -> str:
    """Remove AIS string padding @ characters and spaces on the right.

    Args:
        string: A string to cleanup.
        remove_blanks: Set to true to strip spaces on the right.

    Returns:
        A cleaned up string.
    """
    string = re.sub("@.*", "", string)
    if remove_blanks:
        return string.rstrip()
    return string


# Backward compatibility alias
Strip = strip  # pylint: disable=invalid-name


def pad(string: str, length: int) -> str:
    """Pad string to length with @ characters.

    Args:
        string: String to pad out.
        length: Number of characters that the string must be.

    Returns:
        str of the require length that is right padded.
    """
    pad_len = length - len(string)
    if pad_len > 0:
        string += "@" * pad_len
    return string


# Backward compatibility alias
Pad = pad  # pylint: disable=invalid-name
