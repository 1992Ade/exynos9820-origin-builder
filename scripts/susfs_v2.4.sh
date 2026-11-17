#!/usr/bin/env bash
# Replace the FreeRunner in-tree SuSFS (v2.3.0) by SuSFS v2.4.0 (JackA1ltman's 4.14 port).
#
#  1. strip_susfs.py      removes every #if CONFIG_KSU_SUSFS* block + fs/susfs.c and headers
#  2. strict_apply.py     applies the v2.4.0 patch hunk by hunk, only where ALL context matches
#                         (GNU patch --fuzz put hunks in wrong places on this Samsung tree)
#  3. susfs_v2.4_samsung_fixups.py   hand ports of the 20 hunks that can't match (Samsung APIs)
#
# The set of hunks strict_apply can't place must be exactly the one the fixups were written
# for: if FreeRunner's tree or the patch changes, the build stops here instead of guessing.
#
# Usage (kernel root, AFTER KernelSU-Next is removed, BEFORE OriginSU's setup.sh):
#   susfs_v2.4.sh <builder-scripts-dir>
set -euo pipefail
S="${1:?usage: susfs_v2.4.sh <builder-scripts-dir>}"
NONGKI_COMMIT="${SUSFS_PATCH_COMMIT:-bbe032eb06c50d24a9207bf2ece5e25cf2460bd0}"   # JackA1ltman, v2.4.0 (2026-11-15)
PATCH_URL="https://raw.githubusercontent.com/JackA1ltman/NonGKI_Kernel_Build_2nd/${NONGKI_COMMIT}/Patches/Patch/susfs_patch_to_4.14.patch"

[ -f include/linux/susfs.h ] || { echo "::error::no in-tree SuSFS found (expected FreeRunner v2.3.0)"; exit 1; }
[ -d KernelSU-Next ] && { echo "::error::remove KernelSU-Next before upgrading SuSFS"; exit 1; }
echo "-- in-tree: $(grep -m1 '#define SUSFS_VERSION' include/linux/susfs.h)"

# 1) strip
FILES=$(grep -rlE 'CONFIG_KSU_SUSFS|susfs' --include='*.c' --include='*.h' \
          arch block drivers fs include init ipc kernel lib mm net security 2>/dev/null \
        | grep -vxE 'fs/susfs\.c|include/linux/susfs(_def)?\.h' || true)
python3 -I "$S/strip_susfs.py" . $FILES | tee /tmp/strip.log
if grep -q 'leftover' /tmp/strip.log; then echo "::error::SuSFS references left after stripping"; exit 1; fi
rm -f fs/susfs.c include/linux/susfs.h include/linux/susfs_def.h
sed -i '/susfs\.o/d' fs/Makefile

# 2) strict apply of the v2.4.0 patch
if [ -n "${SUSFS_PATCH_FILE:-}" ]; then cp "$SUSFS_PATCH_FILE" /tmp/susfs_v2.4.patch; else curl -LSs --fail --retry 3 -o /tmp/susfs_v2.4.patch "$PATCH_URL"; fi
grep -q 'SUSFS_VERSION "v2.4.0"' /tmp/susfs_v2.4.patch || { echo "::error::downloaded patch is not v2.4.0"; exit 1; }
set +e
python3 -I "$S/strict_apply.py" . /tmp/susfs_v2.4.patch > /tmp/strict.log 2>&1
set -e
grep -E '^FAILED' /tmp/strict.log | awk '{print $2, $4}' | sort > /tmp/failed.txt
cat > /tmp/expected.txt <<'EOF'
fs/namei.c #1
fs/namei.c #21
fs/namespace.c #1
fs/namespace.c #10
fs/namespace.c #2
fs/namespace.c #3
fs/namespace.c #4
fs/namespace.c #5
fs/namespace.c #6
fs/namespace.c #8
fs/proc/base.c #1
fs/proc/task_mmu.c #1
fs/proc/task_mmu.c #2
fs/proc/task_mmu.c #4
fs/proc/task_mmu.c #5
fs/proc/task_mmu.c #6
fs/super.c #2
kernel/kallsyms.c #1
kernel/sys.c #4
mm/memory.c #1
EOF
sort -o /tmp/expected.txt /tmp/expected.txt
if ! diff -u /tmp/expected.txt /tmp/failed.txt; then
  echo "::error::SuSFS v2.4.0: the hunks that need hand-porting changed (tree or patch updated) — fixups must be reviewed"
  exit 1
fi
echo "-- strict apply: $(grep -c 'hunks applied' /tmp/strict.log) files, 20 hunks left for the Samsung fixups (expected)"

# 3) hand ports
python3 -I "$S/susfs_v2.4_samsung_fixups.py" .
grep -q '#define SUSFS_VERSION "v2.4.0"' include/linux/susfs.h
echo "-- SuSFS upgraded: $(grep -m1 '#define SUSFS_VERSION' include/linux/susfs.h)"
