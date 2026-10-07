#!/usr/bin/env python3
"""show.py <rc1|rc2> <start> [end]: disassemble a range (hex addresses), annotating float-table loads."""
import sys

from match import RC2_ELF
from ppu import RC1_ELF, Elf, show

elf = Elf(RC2_ELF if sys.argv[1] == "rc2" else RC1_ELF)
start = int(sys.argv[2], 16)
show(elf, start, int(sys.argv[3], 16) if len(sys.argv) > 3 else None)
