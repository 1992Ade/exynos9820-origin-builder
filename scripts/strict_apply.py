#!/usr/bin/env python3
"""Apply a unified diff strictly, but tolerant to whitespace and blank-line differences.

GNU patch's --fuzz drops context lines and can land a hunk in the wrong place (seen on the
Samsung tree: a SuSFS hunk inserted inside an enum). Here every non-blank context/removed line
of a hunk must match (after collapsing whitespace) a contiguous run of non-blank lines of the
target file, and that run must be unique. Otherwise the hunk is reported as FAILED and nothing
is guessed. Blank lines are free: the target's own blank lines are kept.

Usage: strict_apply.py <kernel-root> <patch> [--dry-run]
Exit code: number of failed hunks (0 = everything applied).
"""
import re
import sys
from pathlib import Path


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def parse(patch_text):
    files, cur, hunk = [], None, None
    for line in patch_text.split("\n"):
        if line.startswith("diff --git "):
            cur = {"path": None, "hunks": [], "new": False}
            files.append(cur)
            hunk = None
        elif line.startswith("--- ") and cur is not None and hunk is None:
            cur["new"] = line.strip() == "--- /dev/null"
        elif line.startswith("+++ ") and cur is not None and hunk is None:
            p = line[4:].strip()
            cur["path"] = p[2:] if p.startswith("b/") else p
        elif line.startswith("@@") and cur is not None:
            m = re.match(r"@@ -(\d+)", line)
            hunk = {"old_start": int(m.group(1)), "lines": [], "header": line}
            cur["hunks"].append(hunk)
        elif hunk is not None and line[:1] in (" ", "+", "-"):
            hunk["lines"].append((line[0], line[1:]))
        elif hunk is not None and line == "":
            hunk["lines"].append((" ", ""))
        elif hunk is not None and line.startswith("\\"):
            pass
    return files


def apply_hunk(tlines, hunk, expect):
    """Return (new lines, start index) or None. Several exact matches: the one closest to
    `expect` (hunk's old line number + offset of the previous hunk) wins, like patch does."""
    old = [(op, t) for op, t in hunk["lines"] if op in (" ", "-") and norm(t)]
    if not old:
        return None
    nb = [i for i, l in enumerate(tlines) if norm(l)]  # non-blank target line indices
    nbn = [norm(tlines[i]) for i in nb]
    key = [norm(t) for _, t in old]
    hits = [k for k in range(len(nbn) - len(key) + 1) if nbn[k:k + len(key)] == key]
    if not hits:
        return None
    k = min(hits, key=lambda h: abs(nb[h] - expect))
    mapped = nb[k:k + len(key)]           # target index of each non-blank old line
    start, end = mapped[0], mapped[-1]
    out, oi, pos = [], 0, start
    for op, t in hunk["lines"]:
        if op == "+":
            out.append(t)
            continue
        if not norm(t):
            continue                      # blank context/removed line: target keeps its own
        ti = mapped[oi]
        out.extend(tlines[pos:ti])        # target blank lines in between
        if op == " ":
            out.append(tlines[ti])
        pos = ti + 1
        oi += 1
    return tlines[:start] + out + tlines[end + 1:], start


def main():
    root, patch = Path(sys.argv[1]), Path(sys.argv[2])
    dry = "--dry-run" in sys.argv
    failed = 0
    for f in parse(patch.read_text(errors="surrogateescape")):
        p = root / f["path"]
        if f["new"]:
            new = [t for h in f["hunks"] for op, t in h["lines"] if op == "+"]
            if p.exists():
                print(f"FAILED {f['path']}: new file already exists")
                failed += len(f["hunks"])
                continue
            if not dry:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("\n".join(new) + "\n", errors="surrogateescape")
            print(f"created {f['path']}")
            continue
        if not p.exists():
            print(f"FAILED {f['path']}: missing")
            failed += len(f["hunks"])
            continue
        text = p.read_text(errors="surrogateescape")
        tlines = text.split("\n")
        ok, offset = 0, 0
        for n, h in enumerate(f["hunks"], 1):
            r = apply_hunk(tlines, h, h["old_start"] - 1 + offset)
            if r is None:
                failed += 1
                print(f"FAILED {f['path']} hunk #{n} {h['header']}")
            else:
                tlines, start = r
                offset = start - (h["old_start"] - 1)
                ok += 1
        if ok and not dry:
            p.write_text("\n".join(tlines), errors="surrogateescape")
        print(f"{f['path']}: {ok}/{len(f['hunks'])} hunks applied")
    sys.exit(min(failed, 255))


if __name__ == "__main__":
    main()
