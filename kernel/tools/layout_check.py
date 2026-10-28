#!/usr/bin/env python3
"""Check the m20lte recovery-image layout and, when given files, their sizes.

The recovery partition is the port disk:

  0x0000000  4 MiB   Android boot image (BootShim + UEFI FD + XNUP)
  0x0400000  8 MiB   loader log ring
  0x0C00000 18 MiB   Mach-O kernel (koff=0xC00000, ksize=0x1200000)
  0x1E00000  4 MiB   root.apfs (layout A)
  0x2200000  4 MiB   spare
  0x2600000   --     end of the 38 MiB recovery partition

Run from kernel/ (build.sh does this): tools/layout_check.py m20lte
Optionally pass --embed/--kernel/--root to assert real artifact sizes.
"""
import argparse
import os
import subprocess

MB = 1 << 20
RECOVERY_SIZE = 38 * MB
FD_BASE = 0x8F000000
FD_SIZE = 0x200000
PAYLOAD_BASE = 0x8F100000
PAYLOAD_MAX = 0x80000
LOG_OFFSET = 0x400000
LOG_MAX = 8 * MB
KOFF = 0xC00000
KSIZE = 0x1200000
ROFF = 0x1E00000
RSIZE = 4 * MB


def profile(dev):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    root = os.path.join(root, "kernel")
    fmt = "FD_BASE=%s\nFD_SIZE=%s\nPAYLOAD_BASE=%s\n"
    out = subprocess.check_output(
        f"bash -c '. common/lib.sh; load_device {dev} >/dev/null; printf \"{fmt}\" \"$FD_BASE\" \"$FD_SIZE\" \"$PAYLOAD_BASE\"'",
        shell=True, cwd=root, text=True, stderr=subprocess.DEVNULL)
    env = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k] = v
    return env, root


def size_of(path):
    return os.path.getsize(path) if path else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("device")
    ap.add_argument("--ksize", type=lambda x: int(x, 0), default=KSIZE)
    ap.add_argument("--rsize", type=lambda x: int(x, 0), default=RSIZE)
    ap.add_argument("--embed", help="boot.img placed at recovery+0")
    ap.add_argument("--kernel", help="Mach-O kernel placed at recovery+koff")
    ap.add_argument("--root", help="root image placed at recovery+roff")
    args = ap.parse_args()

    env, root = profile(args.device)
    base = int(env["FD_BASE"], 16)
    fd_size = int(env["FD_SIZE"], 16)
    payload = int(env["PAYLOAD_BASE"], 16)

    ok = True
    msgs = []

    def bad(msg):
        nonlocal ok
        ok = False
        msgs.append(msg)

    if base != FD_BASE:
        bad(f"FD_BASE is {base:#x}, expected {FD_BASE:#x}")
    if fd_size != FD_SIZE:
        bad(f"FD_SIZE is {fd_size:#x}, expected {FD_SIZE:#x}")
    if payload != PAYLOAD_BASE:
        bad(f"PAYLOAD_BASE is {payload:#x}, expected {PAYLOAD_BASE:#x}")
    if payload < base or payload + PAYLOAD_MAX > base + fd_size:
        bad("XNUP region is outside the UEFI FD window")
    if LOG_OFFSET + LOG_MAX > KOFF:
        bad("log ring overlaps the kernel")
    if KOFF + args.ksize > ROFF:
        bad("kernel slot overlaps the root")
    if ROFF + args.rsize > RECOVERY_SIZE:
        bad("root slot exceeds the 38 MiB recovery partition")
    if args.rsize > 4 * MB:
        bad("root slot A exceeds 4 MiB; use layout B")
    if args.embed is not None:
        n = size_of(args.embed)
        if n > LOG_OFFSET:
            bad(f"embed {n:#x} exceeds the 4 MiB slot")
    if args.kernel is not None:
        n = size_of(args.kernel)
        if n > args.ksize:
            bad(f"kernel {n:#x} exceeds ksize {args.ksize:#x}")
    if args.root is not None:
        n = size_of(args.root)
        if n > args.rsize:
            bad(f"root {n:#x} exceeds rsize {args.rsize:#x}")

    print(f"layout {args.device}: FD={base:#x}+{fd_size:#x} payload={payload:#x}+{PAYLOAD_MAX:#x}")
    print(f"  log={LOG_OFFSET:#x}+{LOG_MAX:#x} kernel={KOFF:#x}+{args.ksize:#x} "
          f"root={ROFF:#x}+{args.rsize:#x} (image limit {RECOVERY_SIZE:#x})")
    for m in msgs:
        print("  FAIL:", m)
    print("  LAYOUT OK" if ok else "  LAYOUT FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
