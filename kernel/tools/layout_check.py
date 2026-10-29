#!/usr/bin/env python3
import argparse, os, subprocess, sys

MB = 1 << 20

def profile(dev):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    root = os.path.join(root, "kernel")
    fmt = "FD_BASE=%s\nFD_SIZE=%s\nPAYLOAD_BASE=%s\n"
    out = subprocess.check_output(
        f"bash -c '. common/lib.sh; load_device {dev} >/dev/null; printf \"{fmt}\" \"$FD_BASE\" \"$FD_SIZE\" \"$PAYLOAD_BASE\"'", shell=True,
        cwd=root+"/", text=True, stderr=subprocess.DEVNULL)
    env = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k] = v
    return env, root

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("device")
    ap.add_argument("--ksize", type=lambda x: int(x, 0), default=0x1200000)
    ap.add_argument("--rsize", type=lambda x: int(x, 0), default=0x400000)
    args = ap.parse_args()
    env, root = profile(args.device)
    FD_BASE = int(env["FD_BASE"], 16)
    FD_SIZE = int(env["FD_SIZE"], 16)
    PAYLOAD_BASE = int(env["PAYLOAD_BASE"], 16)
    # m20lte recovery policy (layout A)
    LOG_OFFSET = 0x400000
    koff = 0xC00000
    roff = 0x1E00000
    msgs = []
    ok = True
    if FD_SIZE != 0x200000:
        ok = False; msgs.append("FD_SIZE should be 2 MiB")
    # profile PAYLOAD_BASE is the host-side staging window, not the in-FD NUC payload.
    if FD_BASE + FD_SIZE > 0x8F200000:
        ok = False; msgs.append("FD larger than its 2 MiB window")
    if LOG_OFFSET + 8 * MB > koff:
        ok = False; msgs.append("log and kernel overlap")
    if koff + args.ksize > roff:
        ok = False; msgs.append("kernel exceeds root offset")
    if roff + args.rsize > 38 * MB:
        ok = False; msgs.append("root exceeds the 38 MiB recovery image")
    if args.rsize > 4 * MB:
        ok = False; msgs.append("root slot A exceeds 4 MiB; use layout B")
    print(f"layout {args.device}: FD={FD_BASE:#x}+{FD_SIZE:#x} payload={PAYLOAD_BASE:#x} log={LOG_OFFSET:#x}")
    print(f"  kernel={koff:#x}+{args.ksize:#x} root={roff:#x}+{args.rsize:#x} (image limit {38*MB:#x})")
    for m in msgs:
        print("  FAIL:", m)
    print("  LAYOUT OK" if ok else "  LAYOUT FAILED")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
