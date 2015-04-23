"""AIS binary helper functions.

Code to convert AIS messages between binary BitVectors and strings.
AIS messages are usually encoded with ASCII 6-bit packing within NMEA
!AIVDM/!AIVDO messages.  This module provides tools to transform between VDM
characters, BitVectors and integer values.  The encoding is similar to base64,
but with a different mapping of characters to bits.

ASCII character 48 (character "0") starts the sequence with a bit
representation of 0 (binary 000000) and continues with ASCII 49 (character
"1") representing 1 (binary 000001) through ASCII 87 (character 'W')
representing 39 (binary 100111).

The sequence then skips 8 characters and starts up again with
ASCII 96 (character "`") representing 40 (binary 101000) through ASCII 119
(character "w") finishing the sequence representing 63 (binary 111111).

See also:
  NMEA strings at http://gpsd.berlios.de/NMEA.txt
  http://en.wikipedia.org/wiki/Automatic_Identification_System
  IEC-PAS 61162-100 Ed.1 IEC Page 26, Annex C, Table C-1
  http://catb.org/gpsd/AIVDM.html#_aivdm_aivdo_payload_armoring
  man ascii
  Base 64: https://tools.ietf.org/html/rfc3548#section-3

Attributes:
    decode: Dictionary based cache of character to BitVector lookup.
    encode: A list cache of AIS int value to character.
"""


from BitVector import BitVector

# 6 bits are encoded in each NMEA VDM character
BITS_PER_VDM_CHARACTER = 6
BGN_ASCII_BLOCK_1 = 48  # '0'
END_ASCII_BLOCK_1 = 87  # 'W'
SIZE_ASCII_BLOCK_1 = END_ASCII_BLOCK_1 + 1 - BGN_ASCII_BLOCK_1
BGN_ASCII_BLOCK_2 = 96  # '`'
END_ASCII_BLOCK_2 = 119  # 'w'
GAP_SIZE = BGN_ASCII_BLOCK_2 - (END_ASCII_BLOCK_1 + 1)


def setBitVectorSize(bv, size=8):
  """Pad a BitVector with 0's on the left until it is the specified size.

  Args:
    bv: BitVector that needs to meet a minimim size.  Defaults to 1 byte.
    size: Positive integer that is the minimum number of bits to make the
        new BitVector.

  Returns:
    BitVector that is size bits or larger.
  """
  pad = BitVector(bitlist=[0])
  while len(bv) < size:
    bv = pad + bv
  return bv


def _Ais6ToBitvecSlow(str6):
  """Convert an ITU AIS VDM 6 bit string into a bit vector.

  Args:
    str6: string, ASCII as it appears in the NMEA VDM string.

  Returns:
    BitVector of decoded bits.  Pad bits not removed.
  """
  bvtotal = BitVector(size=0)

  for c in str6:
    c = ord(c)
    val = c - BGN_ASCII_BLOCK_1
    if val >= SIZE_ASCII_BLOCK_1:
      val -= GAP_SIZE
    if val == 0:
      bv = BitVector(size=BITS_PER_VDM_CHARACTER)
    else:
      bv = setBitVectorSize(BitVector(intVal=val), BITS_PER_VDM_CHARACTER)

    bvtotal += bv
  return bvtotal


def _BuildLookupTable():
  """Create a dict of character keys with the BitVector repr as the value."""
  key_nums = (list(range(BGN_ASCII_BLOCK_1, END_ASCII_BLOCK_1 + 1)) +
              list(range(BGN_ASCII_BLOCK_2, END_ASCII_BLOCK_2 + 1)))
  assert len(key_nums) == 64
  key_chars = [chr(key) for key in key_nums]
  return {key_char: _Ais6ToBitvecSlow(key_char) for key_char in key_chars}


decode = _BuildLookupTable()

# Lookup the character representation for an AIS AIVDM message from the 6-bit
# integer value.
encode = (
    [chr(encode_count + BGN_ASCII_BLOCK_1)
     for encode_count in range(END_ASCII_BLOCK_1 + 1 - BGN_ASCII_BLOCK_1)]
    + [chr(encode_count + BGN_ASCII_BLOCK_2)
       for encode_count in range(END_ASCII_BLOCK_2 + 1 - BGN_ASCII_BLOCK_2)])


def joinBV(bvSeq):
  """Combined a sequence of bit vectors into one large BitVector.

  TODO(schwehr): Check performance and see if this can be done faster.

  Args:
    bvSeq: sequence of bitvectors.

  Returns:
    An aggregated BitVector.
  """
  bv_total = BitVector(size=0)
  for bv in bvSeq:
    bv_total += bv
  return bv_total


def AddOne(bv):
  """Add one bit to a bit vector.

  Overflows are silently dropped.

  Args:
    bv: BitVector to add one to its bits.

  Returns:
    BitVector with one added.
  """
  new = bv
  r = range(1, len(bv) + 1)
  for i in r:
    index = len(bv) - i
    if 0 == bv[index]:
      new[index] = 1
      break
    new[index] = 0
  return new


def SubOne(bv):
  """Subtract one bit from a bit vector."""
  new = bv
  r = range(1, len(bv) + 1)
  for i in r:
    index = len(bv) - i
    if 1 == bv[index]:
      new[index] = 0
      break
    new[index] = 1
  return new


def bvFromSignedInt(intVal, bitSize=None):
  """Create a two's complement BitVector from a signed integer.

  Note that 110 and 10 are both -2.  Positives must have a '0' in the
  left hand position.  Negative numbers must have a '1' in the left most
  position.

  Args:
    intVal: integer value to turn into a bit vector.
    bitSize: optional size to flush out the number of bits.

  Returns:
    A BitVector flushed out to the correct size.

  Raises:
    ValueError: If the bit size does not make sense.
  """
  bv = None
  if not bitSize:
    bv = BitVector(intVal=abs(intVal))
  else:
    bv = setBitVectorSize(BitVector(intVal=abs(intVal)), bitSize - 1)
    if bitSize - 1 != len(bv) and bv[0] != 1 and bv[-1] != 0:
      raise ValueError('incorrect bit size')
    if len(bv) == bitSize and bv[0] == 1:
      return bv
  if intVal >= 0:
    bv = BitVector(intVal=0) + bv
  else:
    bv = SubOne(bv)
    bv = ~bv
    bv = BitVector(intVal=1) + bv
  return bv


def signedIntFromBV(bv):
  """Interpret a bit vector as an signed integer.

  int(BitVector) defaults to treating the bits as an unsigned int.
  Assumes two's complement representation.

  Args:
    bv: BitVector to treat as an signed int.

  Returns:
    Signed integer.
  """
  if 0 == bv[0]:
    # Positive.
    return int(bv)
  # Negative.
  val = int(AddOne(~(bv[1:])))
  if 0 != val:
    return -val
  return -int(bv)


def ais6tobitvec(str6):
  """Convert an ITU AIS 6 bit string into a bit vector.

  Each character represents 6 bits.  This is the NMEA !AIVD[MO]
  message payload.

  If the original BitVector had ((len(bitvector) % 6 > 0),
  then there will be pad bits in the str6.  This function has no way
  to know how many pad bits there are.

  Args:
    str6: String that as it appears in the NMEA string.

  Returns:
    A BitVector of decoded bits .  There may be pad bits at the tail to make
    this 6 bit aligned.
  """
  bvtotal = BitVector(size=BITS_PER_VDM_CHARACTER * len(str6))

  for pos in range(len(str6)):
    bv = decode[str6[pos]]
    start = pos * BITS_PER_VDM_CHARACTER
    for i in range(BITS_PER_VDM_CHARACTER):
      bvtotal[i + start] = bv[i]
  return bvtotal


def bitvectoais6(bv, doPadding=True):
  """Convert bit vector int an ITU AIS 6 bit string.

  Each character represents 6 bits.

  Args:
    bv: BitVector, Message bits.
    doPadding: bool, True if the BitVector should be padded to a multiple of 6.

  Returns:
    A str6 string as represented in a NMEA AIS VDM message and the number of
    pad bits needed.

  Raises:
    ValueError: The results are not 6-bit aligned.
  """
  pad = BITS_PER_VDM_CHARACTER - (len(bv) % BITS_PER_VDM_CHARACTER)
  if pad == BITS_PER_VDM_CHARACTER:
    pad = 0
  str_len = len(bv) / BITS_PER_VDM_CHARACTER
  if pad > 0:
    str_len += 1

  if pad != 0:
    if doPadding:
      bv += BitVector(size=pad)
    else:
      raise ValueError('Results would not be 6-bit aligned.')

  ais_chars = []
  for i in range(str_len):
    start = i * BITS_PER_VDM_CHARACTER
    end = (i + 1) * BITS_PER_VDM_CHARACTER
    val = int(bv[start:end])
    c = encode[val]
    ais_chars.append(c)

  ais_str = ''.join(ais_chars)

  return ais_str, pad
