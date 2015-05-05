"""Handle encoding and decoding AIS strings.

character_lut: list, lookup table for decode to fetch characters faster.

character_bits: dict, lookup table for going from a single character to
  a 6 bit BitVector.
"""
import logging
import re


import binary
from BitVector import BitVector


character_lut = [
    '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L',
    'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y',
    'Z', '[', '\\', ']', '^', '-', ' ', '!', '"', '#', '$', '%', '&',
    '`', '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3',
    '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?'
]

# Fast lookup for the AIS int code for a character.
# TODO(schwehr): Remove duplicate character entry without breaking things.
# pylint: disable=duplicate-key
character_dict = {
    '@': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7,
    'H': 8, 'I': 9, 'J': 10, 'K': 11, 'L': 12, 'M': 13, 'N': 14, 'O': 15,
    'P': 16, 'Q': 17, 'R': 18, 'S': 19, 'T': 20, 'U': 21, 'V': 22,
    'W': 23, 'X': 24, 'Y': 25, 'Z': 26, '[': 27, '\\': 28, ']': 29,
    '^': 30, '-': 31, ' ': 32, '!': 33, '"': 34, '#': 35, '$': 36,
    '%': 37, '&': 38, '`': 39, '(': 40, ')': 41, '*': 42, '+': 43,
    ',': 44, '-': 45, '.': 46, '/': 47, '0': 48, '1': 49, '2': 50,
    '3': 51, '4': 52, '5': 53, '6': 54, '7': 55, '8': 56, '9': 57,
    ':': 58, ';': 59, '<': 60, '=': 61, '>': 62, '?': 63
}

character_bits = {}
character_bits['@'] = binary.setBitVectorSize(BitVector(intVal=0), 6)
character_bits['A'] = binary.setBitVectorSize(BitVector(intVal=1), 6)
character_bits['B'] = binary.setBitVectorSize(BitVector(intVal=2), 6)
character_bits['C'] = binary.setBitVectorSize(BitVector(intVal=3), 6)
character_bits['D'] = binary.setBitVectorSize(BitVector(intVal=4), 6)
character_bits['E'] = binary.setBitVectorSize(BitVector(intVal=5), 6)
character_bits['F'] = binary.setBitVectorSize(BitVector(intVal=6), 6)
character_bits['G'] = binary.setBitVectorSize(BitVector(intVal=7), 6)
character_bits['H'] = binary.setBitVectorSize(BitVector(intVal=8), 6)
character_bits['I'] = binary.setBitVectorSize(BitVector(intVal=9), 6)
character_bits['J'] = binary.setBitVectorSize(BitVector(intVal=10), 6)
character_bits['K'] = binary.setBitVectorSize(BitVector(intVal=11), 6)
character_bits['L'] = binary.setBitVectorSize(BitVector(intVal=12), 6)
character_bits['M'] = binary.setBitVectorSize(BitVector(intVal=13), 6)
character_bits['N'] = binary.setBitVectorSize(BitVector(intVal=14), 6)
character_bits['O'] = binary.setBitVectorSize(BitVector(intVal=15), 6)
character_bits['P'] = binary.setBitVectorSize(BitVector(intVal=16), 6)
character_bits['Q'] = binary.setBitVectorSize(BitVector(intVal=17), 6)
character_bits['R'] = binary.setBitVectorSize(BitVector(intVal=18), 6)
character_bits['S'] = binary.setBitVectorSize(BitVector(intVal=19), 6)
character_bits['T'] = binary.setBitVectorSize(BitVector(intVal=20), 6)
character_bits['U'] = binary.setBitVectorSize(BitVector(intVal=21), 6)
character_bits['V'] = binary.setBitVectorSize(BitVector(intVal=22), 6)
character_bits['W'] = binary.setBitVectorSize(BitVector(intVal=23), 6)
character_bits['X'] = binary.setBitVectorSize(BitVector(intVal=24), 6)
character_bits['Y'] = binary.setBitVectorSize(BitVector(intVal=25), 6)
character_bits['Z'] = binary.setBitVectorSize(BitVector(intVal=26), 6)
character_bits['['] = binary.setBitVectorSize(BitVector(intVal=27), 6)
character_bits['\\'] = binary.setBitVectorSize(BitVector(intVal=28), 6)
character_bits[']'] = binary.setBitVectorSize(BitVector(intVal=29), 6)
character_bits['^'] = binary.setBitVectorSize(BitVector(intVal=30), 6)
character_bits['-'] = binary.setBitVectorSize(BitVector(intVal=31), 6)
character_bits[' '] = binary.setBitVectorSize(BitVector(intVal=32), 6)
character_bits['!'] = binary.setBitVectorSize(BitVector(intVal=33), 6)
character_bits['"'] = binary.setBitVectorSize(BitVector(intVal=34), 6)
character_bits['#'] = binary.setBitVectorSize(BitVector(intVal=35), 6)
character_bits['$'] = binary.setBitVectorSize(BitVector(intVal=36), 6)
character_bits['%'] = binary.setBitVectorSize(BitVector(intVal=37), 6)
character_bits['&'] = binary.setBitVectorSize(BitVector(intVal=38), 6)
character_bits['`'] = binary.setBitVectorSize(BitVector(intVal=39), 6)
character_bits['('] = binary.setBitVectorSize(BitVector(intVal=40), 6)
character_bits[')'] = binary.setBitVectorSize(BitVector(intVal=41), 6)
character_bits['*'] = binary.setBitVectorSize(BitVector(intVal=42), 6)
character_bits['+'] = binary.setBitVectorSize(BitVector(intVal=43), 6)
character_bits[','] = binary.setBitVectorSize(BitVector(intVal=44), 6)
character_bits['-'] = binary.setBitVectorSize(BitVector(intVal=45), 6)
character_bits['.'] = binary.setBitVectorSize(BitVector(intVal=46), 6)
character_bits['/'] = binary.setBitVectorSize(BitVector(intVal=47), 6)
character_bits['0'] = binary.setBitVectorSize(BitVector(intVal=48), 6)
character_bits['1'] = binary.setBitVectorSize(BitVector(intVal=49), 6)
character_bits['2'] = binary.setBitVectorSize(BitVector(intVal=50), 6)
character_bits['3'] = binary.setBitVectorSize(BitVector(intVal=51), 6)
character_bits['4'] = binary.setBitVectorSize(BitVector(intVal=52), 6)
character_bits['5'] = binary.setBitVectorSize(BitVector(intVal=53), 6)
character_bits['6'] = binary.setBitVectorSize(BitVector(intVal=54), 6)
character_bits['7'] = binary.setBitVectorSize(BitVector(intVal=55), 6)
character_bits['8'] = binary.setBitVectorSize(BitVector(intVal=56), 6)
character_bits['9'] = binary.setBitVectorSize(BitVector(intVal=57), 6)
character_bits[':'] = binary.setBitVectorSize(BitVector(intVal=58), 6)
character_bits[';'] = binary.setBitVectorSize(BitVector(intVal=59), 6)
character_bits['<'] = binary.setBitVectorSize(BitVector(intVal=60), 6)
character_bits['='] = binary.setBitVectorSize(BitVector(intVal=61), 6)
character_bits['>'] = binary.setBitVectorSize(BitVector(intVal=62), 6)
character_bits['?'] = binary.setBitVectorSize(BitVector(intVal=63), 6)


def Decode(bits, drop_after_first_at=False):
  """Decode bits as a string.

  Does not remove the end space or @@@@.  Must be an multiple of 6 bits.

  Args:
    bits: BitVector, n*6 bits that represent a string.
    drop_after_first_at: Strip trailing add.

  Returns:
    A string with pad spaces or @@@@.
  """
  numchar = len(bits) / 6
  s = []
  for i in range(numchar):
    start = 6 * i
    end = start + 6
    charbits = bits[start:end]
    val = int(charbits)
    if drop_after_first_at and val == 0:
      break  # 0 is the @ character which is used to pad strings.
    s.append(character_lut[val])

  return ''.join(s)


def Encode(string, bit_size=None):
  """Convert a string to a BitVector.

  TODO(schwehr): Pad with "@" to reach requested bitSize.

  Args:
    string: str to encode.
    bit_size: integer: multiple of 6 size of the resulting bits.

  Returns:
    String representing the bits encoded as an AIS VDM armored characters.
  """
  if bit_size:
    assert bit_size % 6 == 0
  bv = BitVector(size=0)
  for i in range(len(string)):
    bv += character_bits[string[i]]
  if bit_size:
    if bit_size < len(bv):
      logging.error('ERROR:  Too many bits in string: "%s %s %s"',
                    string, bit_size, len(bv))
      assert False
    extra = bit_size - len(bv)
    bv += BitVector(size=extra)

  return bv


def Strip(string, remove_blanks=True):
  """Remove AIS string padding @ characters and spaces on the right.

  Args:
    string: A string to cleanup.
    remove_blanks: Set to true to strip spaces on the right.

  Returns:
    A cleaned up string.
  """
  string = re.sub('@.*', '', string)
  if remove_blanks:
    return string.rstrip()
  return string


def Pad(string, length):
  """Pad string to length with @ characters.

  Args:
    string: String to pad out.
    length: Number of characters that the string must be.

  Returns:
    str of the require length that is right padded.
  """
  pad = length - len(string)
  if pad > 0:
    string += '@' * pad
  return string
