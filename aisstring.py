#!/usr/bin/env python

"""Handle encoding and decoding AIS strings.

@bug: Need more doctests.
@bug: needs to throw an exception if the character is not in the LUT.
@bug: what to do about string with trailing @@@ or "   " (white space).

character_lut: list, lookup table for decode to fetch characters faster.

character_bits: dict, lookup table for going from a single character to
  a 6 bit BitVector.
"""

import sys

from BitVector import BitVector

import binary

character_lut = [
    '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L',
    'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y',
    'Z', '[', '\\', ']', '^', '-', ' ', '!', '"', '#', '$', '%', '&',
    '`', '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3',
    '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?'
    ]

character_dict = {
    '@': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7,
    'H': 8, 'I': 9, 'J': 10, 'K': 11, 'L': 12, 'M': 13, 'N': 14, 'O':
    15, 'P': 16, 'Q': 17, 'R': 18, 'S': 19, 'T': 20, 'U': 21, 'V': 22,
    'W': 23, 'X': 24, 'Y': 25, 'Z': 26, '[': 27, '\\': 28, ']': 29,
    '^': 30, '-': 31, ' ': 32, '!': 33, '"': 34, '#': 35, '$': 36,
    '%': 37, '&': 38, '`': 39, '(': 40, ')': 41, '*': 42, '+': 43,
    ',': 44, '-': 45, '.': 46, '/': 47, '0': 48, '1': 49, '2': 50,
    '3': 51, '4': 52, '5': 53, '6': 54, '7': 55, '8': 56, '9': 57,
    ':': 58, ';': 59, '<': 60, '=': 61, '>': 62, '?': 63
}
"""Fast lookup for the AIS int code for a character """

character_bits = {}
character_bits['@'] = binary.setBitVectorSize(BitVector(intVal=0),6)
character_bits['A'] = binary.setBitVectorSize(BitVector(intVal=1),6)
character_bits['B'] = binary.setBitVectorSize(BitVector(intVal=2),6)
character_bits['C'] = binary.setBitVectorSize(BitVector(intVal=3),6)
character_bits['D'] = binary.setBitVectorSize(BitVector(intVal=4),6)
character_bits['E'] = binary.setBitVectorSize(BitVector(intVal=5),6)
character_bits['F'] = binary.setBitVectorSize(BitVector(intVal=6),6)
character_bits['G'] = binary.setBitVectorSize(BitVector(intVal=7),6)
character_bits['H'] = binary.setBitVectorSize(BitVector(intVal=8),6)
character_bits['I'] = binary.setBitVectorSize(BitVector(intVal=9),6)
character_bits['J'] = binary.setBitVectorSize(BitVector(intVal=10),6)
character_bits['K'] = binary.setBitVectorSize(BitVector(intVal=11),6)
character_bits['L'] = binary.setBitVectorSize(BitVector(intVal=12),6)
character_bits['M'] = binary.setBitVectorSize(BitVector(intVal=13),6)
character_bits['N'] = binary.setBitVectorSize(BitVector(intVal=14),6)
character_bits['O'] = binary.setBitVectorSize(BitVector(intVal=15),6)
character_bits['P'] = binary.setBitVectorSize(BitVector(intVal=16),6)
character_bits['Q'] = binary.setBitVectorSize(BitVector(intVal=17),6)
character_bits['R'] = binary.setBitVectorSize(BitVector(intVal=18),6)
character_bits['S'] = binary.setBitVectorSize(BitVector(intVal=19),6)
character_bits['T'] = binary.setBitVectorSize(BitVector(intVal=20),6)
character_bits['U'] = binary.setBitVectorSize(BitVector(intVal=21),6)
character_bits['V'] = binary.setBitVectorSize(BitVector(intVal=22),6)
character_bits['W'] = binary.setBitVectorSize(BitVector(intVal=23),6)
character_bits['X'] = binary.setBitVectorSize(BitVector(intVal=24),6)
character_bits['Y'] = binary.setBitVectorSize(BitVector(intVal=25),6)
character_bits['Z'] = binary.setBitVectorSize(BitVector(intVal=26),6)
character_bits['['] = binary.setBitVectorSize(BitVector(intVal=27),6)
character_bits['\\'] = binary.setBitVectorSize(BitVector(intVal=28),6)
character_bits[']'] = binary.setBitVectorSize(BitVector(intVal=29),6)
character_bits['^'] = binary.setBitVectorSize(BitVector(intVal=30),6)
character_bits['-'] = binary.setBitVectorSize(BitVector(intVal=31),6)
character_bits[' '] = binary.setBitVectorSize(BitVector(intVal=32),6)
character_bits['!'] = binary.setBitVectorSize(BitVector(intVal=33),6)
character_bits['"'] = binary.setBitVectorSize(BitVector(intVal=34),6)
character_bits['#'] = binary.setBitVectorSize(BitVector(intVal=35),6)
character_bits['$'] = binary.setBitVectorSize(BitVector(intVal=36),6)
character_bits['%'] = binary.setBitVectorSize(BitVector(intVal=37),6)
character_bits['&'] = binary.setBitVectorSize(BitVector(intVal=38),6)
character_bits['`'] = binary.setBitVectorSize(BitVector(intVal=39),6)
character_bits['('] = binary.setBitVectorSize(BitVector(intVal=40),6)
character_bits[')'] = binary.setBitVectorSize(BitVector(intVal=41),6)
character_bits['*'] = binary.setBitVectorSize(BitVector(intVal=42),6)
character_bits['+'] = binary.setBitVectorSize(BitVector(intVal=43),6)
character_bits[','] = binary.setBitVectorSize(BitVector(intVal=44),6)
character_bits['-'] = binary.setBitVectorSize(BitVector(intVal=45),6)
character_bits['.'] = binary.setBitVectorSize(BitVector(intVal=46),6)
character_bits['/'] = binary.setBitVectorSize(BitVector(intVal=47),6)
character_bits['0'] = binary.setBitVectorSize(BitVector(intVal=48),6)
character_bits['1'] = binary.setBitVectorSize(BitVector(intVal=49),6)
character_bits['2'] = binary.setBitVectorSize(BitVector(intVal=50),6)
character_bits['3'] = binary.setBitVectorSize(BitVector(intVal=51),6)
character_bits['4'] = binary.setBitVectorSize(BitVector(intVal=52),6)
character_bits['5'] = binary.setBitVectorSize(BitVector(intVal=53),6)
character_bits['6'] = binary.setBitVectorSize(BitVector(intVal=54),6)
character_bits['7'] = binary.setBitVectorSize(BitVector(intVal=55),6)
character_bits['8'] = binary.setBitVectorSize(BitVector(intVal=56),6)
character_bits['9'] = binary.setBitVectorSize(BitVector(intVal=57),6)
character_bits[':'] = binary.setBitVectorSize(BitVector(intVal=58),6)
character_bits[';'] = binary.setBitVectorSize(BitVector(intVal=59),6)
character_bits['<'] = binary.setBitVectorSize(BitVector(intVal=60),6)
character_bits['='] = binary.setBitVectorSize(BitVector(intVal=61),6)
character_bits['>'] = binary.setBitVectorSize(BitVector(intVal=62),6)
character_bits['?'] = binary.setBitVectorSize(BitVector(intVal=63),6)


def Decode(bits,dropAfterFirstAt=False):
    """Decode bits as a string.

    Does not remove the end space or @@@@.  Must be an multiple of 6 bits.

    @param bits: n*6 bits that represent a string.
    @type bits: BitVector
    @return: string with pad spaces or @@@@
    @rtype: str
    """
    numchar=len(bits)/6
    s = []
    for i in range(numchar):
        start = 6 * i
        end = start+6
        charbits=bits[start:end]
        val = int(charbits)
        if dropAfterFirstAt and val==0:
            break  # 0 is the @ character which is used to pad strings.
        s.append(character_lut[val])

    return ''.join(s)


def Encode(string, bitSize=None):
    """Convert a string to a BitVector.
    @param string: python ascii string to encode.
    @type string: str
    @param bitSize: how many bits should this take.  must be a multiple of 6
    @type bitSize: int
    @return: enocded bits for the string
    @rtype: BitVector
    @bug: force to upper case
    @bug: building this in reverse may be faster
    @bug: check that bitSize is a multple of 6
    @bug: pad with "@" to reach requested bitSize
    """
    if bitSize:
        assert(bitSize%6==0)
    bv = BitVector(size=0)
    for i in range(len(string)):
        bv = bv+character_bits[string[i]]
    if bitSize:
        if bitSize < len(bv):
            print 'ERROR:  Too many bits in string: "'+string+'"',
            print '  ', bitSize, len(bv)
            assert False
        extra = bitSize - len(bv)
        bv = bv+BitVector(size=extra)
    return bv


def unpad(string,removeBlanks=True):
    """
    Remove AIS string padding

    >>> unpad('@')
    ''
    >>> unpad('A@')
    'A'
    >>> unpad('ABCDEF1234@@@@@')
    'ABCDEF1234'

    FIX: is this the correct response?

    >>> unpad('A@B')
    'A@B'

    This is non standard behavior, but some AIS systems space pad the right

    >>> unpad(' ')
    ''
    >>> unpad('MY SHIP NAME    ')
    'MY SHIP NAME'

    The standard implies this behavior with is less fun

    >>> unpad('MY SHIP NAME    ',removeBlanks=False)
    'MY SHIP NAME    '

    @bug: use a faster algorithm for truncating the string
    @param string: string to cleanup
    @type string: str
    @param removeBlanks: set to true to strip spaces on the right
    @type removeBlanks: bool
    @return: cleaned up string
    @rtype: str
    """
    while len(string)>0 and string[-1]=='@':
        string=string[:-1]
    if removeBlanks:
        while len(string)>0 and string[-1]==' ':
            string=string[:-1]
    return string

def pad(string,length):
    """Pad string to length with @ characters.

    >>> pad('',0)
    ''
    >>> pad('',1)
    '@'
    >>> pad('A',1)
    'A'
    >>> pad('A',2)
    'A@'
    >>> pad('MY SHIP NAME',20)
    'MY SHIP NAME@@@@@@@@'

    @param string: string to pad out
    @type string: str
    @param length: number of characters that the string must be
    @type length: int
    @return: str of len length
    @rtype: str

    @bug: Use a list and join to make the string building faster
    """
    while len(string)<length: string += '@'
    return string


if __name__ == '__main__':
    from optparse import OptionParser
    myparser = OptionParser(usage="%prog [options]")
    myparser.add_option('--test', '--doc-test', dest='doctest',
                        default=False, action='store_true',
                        help='run the documentation tests')

    (options,args) = myparser.parse_args()

    if options.doctest:
        import os; print os.path.basename(sys.argv[0]), 'doctests ...',
        sys.argv= [sys.argv[0]]
        import doctest
        numfail,numtests=doctest.testmod()
        if numfail==0: print 'ok'
        else:
            sys.exit('Something Failed')
