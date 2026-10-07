#!/usr/bin/env python3
"""Launch RPCS3 with the game and log hero state transitions by reading guest memory.

RPCS3 has to be our child: with kernel.yama.ptrace_scope=1 only descendants are readable.
"""
import os
import struct
import subprocess
import sys
import time

# The emulator: the environment variable RPCS3, or the first line of the file rpcs3.path next to
# build.py (not part of the repository), or "rpcs3" from the search path.
RPCS3 = os.environ.get("RPCS3") or "rpcs3"
try:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rpcs3.path")) as _f:
        RPCS3 = os.environ.get("RPCS3") or _f.readline().strip() or RPCS3
except OSError:
    pass
GAME = os.environ.get("RPCS3_EBOOT") or os.path.expanduser("~/.config/rpcs3/dev_hdd0/game/NPEA00385/USRDIR/EBOOT.BIN")
SIG_VA, SIG = 0x10200, bytes.fromhex("f821ff917c0802a6")
HERO = 0x969CE0
STATE, SPEED, STICK = HERO + 0x2084, HERO + 0x194, HERO + 0x229C
CHARGE = 0x1606320 + 8      # charge boots frame counter (see build.py)
RING_IDX = 0xA10954
PLANET = 0x969C70
PAD_HELD = 0x964A40 + 0xA0
TAP = 0x1606320 + 4


def descendants(pid):
    out, todo = [], [pid]
    while todo:
        p = todo.pop()
        out.append(p)
        try:
            for t in os.listdir(f"/proc/{p}/task"):
                todo += [int(c) for c in open(f"/proc/{p}/task/{t}/children").read().split()]
        except OSError:
            pass
    return out


def find_guest(root):
    for pid in descendants(root):
        try:
            maps = open(f"/proc/{pid}/maps").read().splitlines()
            mem = open(f"/proc/{pid}/mem", "rb", buffering=0)
        except OSError:
            continue
        for line in maps:
            start = int(line.split("-")[0], 16)
            if start & 0xFFFF or start >= 1 << 62:
                continue
            try:
                mem.seek(start + (SIG_VA & 0xFFFF))
                if mem.read(8) == SIG:
                    return pid, mem, start - (SIG_VA & ~0xFFFF)
            except (OSError, OverflowError, ValueError):
                pass
        mem.close()
    return None


def main():
    proc = subprocess.Popen([RPCS3, GAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    found = None
    while proc.poll() is None and not found:
        time.sleep(1)
        found = find_guest(proc.pid)
    if not found:
        sys.exit("emulator exited before the game was mapped")
    pid, mem, base = found
    print(f"guest memory of pid {pid} at {base:#x}", flush=True)

    def rd(va, fmt):
        mem.seek(base + va)
        return struct.unpack(">" + fmt, mem.read(struct.calcsize(fmt)))[0]

    # Command channel: lines in build/cmd are executed against guest memory and answered in
    # build/cmd.out. "r <addr> <len>" reads, "w <addr> <hex bytes>" writes (addresses in hex).
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build")
    cmd_path, out_path, cmd_seen = os.path.join(here, "cmd"), os.path.join(here, "cmd.out"), 0.0
    wmem = open(f"/proc/{pid}/mem", "r+b", buffering=0)

    def run_commands():
        nonlocal cmd_seen
        try:
            stamp = os.path.getmtime(cmd_path)
        except OSError:
            return
        if stamp <= cmd_seen:
            return
        cmd_seen = stamp
        with open(out_path, "w") as out:
            for line in open(cmd_path).read().splitlines():
                parts = line.split()
                try:
                    if parts and parts[0] == "r":
                        mem.seek(base + int(parts[1], 16))
                        out.write(f"{parts[1]} {mem.read(int(parts[2], 0)).hex()}\n")
                    elif parts and parts[0] == "w":
                        wmem.seek(base + int(parts[1], 16))
                        wmem.write(bytes.fromhex(parts[2]))
                        out.write(f"{parts[1]} written\n")
                except (OSError, ValueError, IndexError) as exc:
                    out.write(f"{line} failed: {exc}\n")
            out.write("done\n")

    t0, last, last_ring, hits, charging, top, last_btn = time.time(), None, None, 0, False, 0.0, 0
    sampled = 0.0
    other_last = None       # (hero type, animation, buttons) while the hero is not Ratchet
    dash_last = 0
    while proc.poll() is None:
        run_commands()
        try:
            st, ring, charge, speed = rd(STATE, "i"), rd(RING_IDX, "I"), rd(CHARGE, "i"), rd(SPEED, "f")
            now = time.time() - t0
            if last_ring is not None and ring != last_ring:
                hits += (ring - last_ring) % 64
            last_ring = ring
            btn = rd(PAD_HELD, "I") & 0xF
            if btn != last_btn:
                print(f"{now:8.2f}s shoulder buttons {btn:#x} (L2=1 R2=2 L1=4 R1=8)  tap_window={rd(TAP, 'i')} charge={charge}", flush=True)
                last_btn = btn
            if charge > 0:
                top = max(top, speed)
            if (charge > 0) != charging:
                charging = charge > 0
                print(f"{now:8.2f}s charge {'start' if charging else f'end, top speed {top * 60:.1f} units/s'}"
                      f"  state={st:#x} bank={rd(0x1606320 + 0x18, 'i'):#x} loop_voice={rd(0x1606320 + 0x1c, 'i') - 1}"
                      f" z-ground={rd(HERO + 0x88, 'f') - rd(HERO + 0x2D8, 'f'):.2f}"
                      f" foot_item={rd(HERO + 0x1108, 'i'):#x}"
                      f" wall={rd(HERO + 0x257, 'B')} magnetic={rd(HERO + 0x308, 'H')} override_anim={rd(HERO + 0x20A8, 'B')}", flush=True)
                top = 0.0 if not charging else top
            if charge > 0 and now - sampled >= 0.1:        # ten lines a second while charging
                sampled = now
                vel = [rd(HERO + 0xE0 + 4 * i, "f") * 60 for i in range(3)]
                moved = [rd(HERO + 0x100 + 4 * i, "f") * 60 for i in range(3)]
                print(f"{now:8.2f}s   charge={charge} state={st:#x} speed={speed * 60:.1f} target={rd(HERO + 0x190, 'f') * 60:.1f}"
                      f" velocity=({vel[0]:.1f}, {vel[1]:.1f}, {vel[2]:.1f}) moved=({moved[0]:.1f}, {moved[1]:.1f}, {moved[2]:.1f})"
                      f" z={rd(HERO + 0x88, 'f'):.2f} ground={rd(HERO + 0x2D8, 'f'):.2f} distance={rd(HERO + 0x2DC, 'f'):.2f}"
                      f" wall={rd(HERO + 0x257, 'B')} on_crate={rd(HERO + 0x30A, 'H')} ground_moby={rd(HERO + 0x2FC, 'I'):#x}"
                      f" slope={rd(HERO + 0x2E0, 'f'):.2f}/{rd(HERO + 0x2E4, 'f'):.2f} frames_on_ground={rd(HERO + 0x300, 'i')}", flush=True)
            strafe = rd(0x1606320 + 0x50, "i")    # strafing timer (see build.py)
            if strafe and rd(STICK, "f") > 0.1 and now - sampled >= 0.1:      # ten lines a second while strafing
                sampled = now
                vel = [rd(HERO + 0xE0 + 4 * i, "f") * 60 for i in range(2)]
                print(f"{now:8.2f}s   strafe state={st:#x} stick=({rd(HERO + 0x1D20, 'f'):+.2f}, {rd(HERO + 0x1D24, 'f'):+.2f})"
                      f" magnitude={rd(STICK, 'f'):.2f} direction={rd(0x1606320 + 0x58, 'i')}"
                      f" target={rd(HERO + 0x190, 'f') * 60:.2f} speed={speed * 60:.2f}"
                      f" measured={rd(HERO + 0x164, 'f') * 60:.2f} forward={rd(HERO + 0x168, 'f') * 60:.2f}"
                      f" velocity=({vel[0]:+.2f}, {vel[1]:+.2f}) |v|={(vel[0] ** 2 + vel[1] ** 2) ** 0.5:.2f}"
                      f" yaw={rd(HERO + 0x98, 'f'):+.2f} heading={rd(0x1606320 + 0x60, 'f'):+.2f}"
                      f" camera_yaw={rd(0x9513C0 + 0x158, 'f'):+.2f}"
                      f" reversal={rd(0x1606320 + 0x68, 'i')}/{rd(0x1606320 + 0x6C, 'i')}"
                      f" flags={rd(HERO + 0x3B8, 'H')}/{rd(HERO + 0x3BE, 'H')} gait={rd(HERO + 0x2088, 'i')}"
                      f" wall={rd(HERO + 0x257, 'B')} slope={rd(HERO + 0x2E4, 'f'):+.2f}"
                      f" xy=({rd(HERO + 0x80, 'f'):.2f}, {rd(HERO + 0x84, 'f'):.2f})"
                      f" anim={rd(rd(HERO + 0x2080, 'I') + 0x53, 'B'):#x}", flush=True)
            hit = ""                           # what the hero's collision last touched (result struct 0xa10940)
            if rd(HERO + 0x257, "B"):
                other = rd(0xA10940 + 0x18, "I")
                hit = (f" hit_moby={other:#x} hit_class={rd(other + 0xA6, 'H') if 0x10000 < other < 0xD0000000 else 0:#x}"
                       f" hit_normal=({rd(0xA10940 + 0x40, 'f'):.2f}, {rd(0xA10940 + 0x44, 'f'):.2f}, {rd(0xA10940 + 0x48, 'f'):.2f})"
                       f" hit_count={rd(0xA10940 + 0x1C, 'i')}")
            kind = rd(HERO + 0x20A4, "B")     # 0 Ratchet, 1 Clank, 2 Giant Clank, 3
            if kind or other_last:
                moby = rd(HERO + 0x2080, "I")
                seen = (kind, rd(moby + 0x53, "B"), rd(PAD_HELD, "I")) if kind else None
                if seen != other_last:
                    other_last = seen
                    print(f"{now:8.2f}s hero type={kind} state={st:#x} moby={moby:#x} class={rd(moby + 0xA6, 'H'):#x}"
                          f" anim={rd(moby + 0x53, 'B')} buttons={rd(PAD_HELD, 'I'):#x} stick={rd(STICK, 'f'):.2f}"
                          f" speed={speed * 60:.1f} vz={rd(HERO + 0xE8, 'f') * 60:.1f}"
                          f" z-ground={rd(HERO + 0x88, 'f') - rd(HERO + 0x2D8, 'f'):.2f}"
                          f" euler=({rd(HERO + 0x90, 'f'):.2f}, {rd(HERO + 0x94, 'f'):.2f}, {rd(HERO + 0x98, 'f'):.2f})"
                          f" wall={rd(HERO + 0x257, 'B')} off_ground={rd(HERO + 0x30E, 'H')} moby_z-hero_z={rd(moby + 0x18, 'f') - rd(HERO + 0x88, 'f'):.2f}"
                          f" moby_euler=({rd(moby + 0x40, 'f'):.2f}, {rd(moby + 0x44, 'f'):.2f}, {rd(moby + 0x48, 'f'):.2f})" + hit,
                          flush=True)
            dash = rd(0x1606320 + 0x90, "i")      # Clank's dash frame counter (see build.py)
            if dash > 0 or dash_last > 0:
                print(f"{now:8.2f}s   dash={dash} state={st:#x} speed={speed * 60:.1f}"
                      f" vz={rd(HERO + 0xE8, 'f') * 60:.1f} z-ground={rd(HERO + 0x88, 'f') - rd(HERO + 0x2D8, 'f'):.2f}"
                      f" off_ground_frames={rd(HERO + 0x30E, 'H')} yaw={rd(HERO + 0x98, 'f'):.2f}"
                      f" target_yaw={rd(HERO + 0x180, 'f'):.2f} wall={rd(HERO + 0x257, 'B')}"
                      f" pitch={rd(HERO + 0x94, 'f'):.2f} anim={rd(rd(HERO + 0x2080, 'I') + 0x53, 'B')}"
                      f" wings={rd(0x1606320 + 0x9C, 'I'):#x} bump={rd(0x1606320 + 0xD4, 'i')} settle={rd(0x1606320 + 0xD8, 'i')}{hit}"
                      f" xy=({rd(HERO + 0x80, 'f'):.2f}, {rd(HERO + 0x84, 'f'):.2f})"
                      f" camera_distance={((rd(0x9513C0 + 0x140, 'f') - rd(HERO + 0x80, 'f')) ** 2 + (rd(0x9513C0 + 0x144, 'f') - rd(HERO + 0x84, 'f')) ** 2) ** 0.5:.2f}",
                      flush=True) if dash != dash_last else None
            dash_last = dash
            if st != last:
                print(f"{now:8.2f}s state {last if last is None else hex(last)} -> {st:#x}"
                      f"  speed={speed * 60:.1f} units/s stick={rd(STICK, 'f'):.2f}"
                      f" z={rd(HERO + 0x88, 'f'):.2f} z-ground={rd(HERO + 0x88, 'f') - rd(HERO + 0x2D8, 'f'):.2f}"
                      f" damage_events_since_last={hits} anim={rd(rd(HERO + 0x2080, 'I') + 0x53, 'B'):#x}"
                      f" strafing={rd(0x1606320 + 0x50, 'i')}", flush=True)
                last, hits = st, 0
        except (OSError, struct.error):
            pass
        time.sleep(0.002)
    print("emulator exited", flush=True)


if __name__ == "__main__":
    main()
