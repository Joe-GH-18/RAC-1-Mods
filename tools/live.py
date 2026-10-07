"""Helpers for reading a running game through tools/trace.py's command channel."""
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def peek(*cmds):
    out = subprocess.run([sys.executable, os.path.join(HERE, "peek.py"), ",".join(cmds)], capture_output=True, text=True).stdout
    res = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] != "written":
            res[int(parts[0], 16)] = bytes.fromhex(parts[1])
    return res


def read(addr, n):
    return peek(f"r {addr:x} {n}")[addr]


def u32(addr):
    return struct.unpack(">I", read(addr, 4))[0]


def write(addr, data):
    """Large writes do not fit on a command line, so the command file is written directly."""
    import time
    build = os.path.join(HERE, "..", "build")
    cmd, out = os.path.join(build, "cmd"), os.path.join(build, "cmd.out")
    if os.path.exists(out):
        os.remove(out)
    with open(cmd, "w") as f:
        f.write(f"w {addr:x} {data.hex()}\n")
    for _ in range(200):
        if os.path.exists(out) and open(out).read().endswith("done\n"):
            return
        time.sleep(0.05)
    raise RuntimeError("no answer from tools/trace.py")
