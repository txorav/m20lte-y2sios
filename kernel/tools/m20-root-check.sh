#!/bin/bash
# Host-side check for the M20_BRINGUP monolithic APFS root.
#
# Builds a synthetic root tree with the same paths the M20 image needs, packs it with
# kernel/tools/apfs/mkapfs.py, reads it back with kernel/tools/apfs/apfs.py, and checks the
# 4 MiB root slot of the recovery layout with kernel/tools/layout_check.py.
#
#   kernel/tools/m20-root-check.sh            # fast: mkapfs + apfs.py + layout
#   M20_CHECK_APFS=1 kernel/tools/m20-root-check.sh
#                                             # also run check-image.sh (apfsck + the kernel's
#                                             # apfs_lib; clones/builds apfsprogs on first use)
#
# No iOS tree, no cross toolchain and no phone are needed.
set -eu
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
WORK=${WORK:-$ROOT/apfs-work/m20-root-check}
APFS=$HERE/apfs

rm -rf "$WORK"
mkdir -p "$WORK/root/sbin" "$WORK/root/bin" "$WORK/root/etc" "$WORK/root/dev" \
	"$WORK/root/private/var"

# The programs themselves are built by userland/build.sh; their names and locations are what
# this check is about. Keep them small so the image stays in the 4 MiB root slot.
printf 'M20 launchd placeholder\n' > "$WORK/root/sbin/launchd"
printf 'M20 init placeholder\n' > "$WORK/root/sbin/init"
printf 'M20 hello placeholder\n' > "$WORK/root/bin/hello"
cp "$ROOT/userland/m20-rc" "$WORK/root/etc/rc"
: > "$WORK/root/etc/m20-bringup"
printf 'Darwin on m20lte: bring-up root\n' > "$WORK/root/etc/motd"
ln -s private/var/tmp "$WORK/root/tmp"

python3 "$APFS/mkapfs.py" -z -o "$WORK/root.apfs" redwood="$WORK/root" | tail -1
python3 "$APFS/apfs.py" tree "$WORK/root.apfs" / > "$WORK/tree.txt"
python3 "$APFS/apfs.py" ls "$WORK/root.apfs" / > "$WORK/ls.txt"
grep -q '/sbin/launchd' "$WORK/tree.txt"
grep -q '/etc/m20-bringup' "$WORK/tree.txt"
grep -q 'tmp -> private/var/tmp' "$WORK/ls.txt"
echo "m20-root-check: APFS tree OK ($(stat -c %s "$WORK/root.apfs") bytes)"

python3 "$HERE/layout_check.py" m20lte --root "$WORK/root.apfs"

if [ -n "${M20_CHECK_APFS:-}" ]; then
	"$APFS/check-image.sh" "$WORK/root.apfs" redwood="$WORK/root"
else
	echo "m20-root-check: check-image.sh skipped (set M20_CHECK_APFS=1 to run apfsck + apfs_lib)"
fi
