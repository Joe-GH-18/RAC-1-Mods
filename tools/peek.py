#!/usr/bin/env python3
"""Send read/write commands to a running tools/trace.py and print the answers.

peek.py r 96bd64 4        read 4 bytes at guest address 0x96bd64
peek.py w 96bd64 00000002 write bytes
Several commands can be given, separated by commas.
"""
import os
import sys
import time

build = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build")
cmd, out = os.path.join(build, "cmd"), os.path.join(build, "cmd.out")
if os.path.exists(out):
    os.remove(out)
with open(cmd, "w") as f:
    f.write("\n".join(" ".join(c.split()) for c in " ".join(sys.argv[1:]).split(",")) + "\n")
for _ in range(100):
    if os.path.exists(out) and open(out).read().endswith("done\n"):
        print(open(out).read(), end="")
        break
    time.sleep(0.05)
else:
    sys.exit("no answer: is tools/trace.py attached to a running game?")
